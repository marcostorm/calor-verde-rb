"""Etapa 2: cruza as camadas por setor censitário/bairro e gera o ranking de prioridade.

Entradas:
  data/lst_*.tif, data/ndvi_*.tif, data/perda_*.tif  (gerados por extract_gee.py)
  --unidades  GeoJSON/Shapefile/GPKG de setores censitários ou bairros (malha IBGE 2022)
  --dissolver coluna para agregar setores em bairros (ex.: NM_BAIRRO)
  --arborizacao CSV opcional com % de arborização do IBGE por unidade (--chave, --col-arbor)

Saídas em data/out/:
  unidades_prioridade.geojson  unidades com métricas e índice (EPSG:4326, pronto para o mapa)
  ranking.csv                  ranking de prioridade
  pois_calor.geojson           escolas, saúde e pontos de ônibus com temperatura (OSM)
  resumo.json                  números-chave para a home do site
"""
import argparse
import glob
import json
import os
import sys

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import requests
from rasterstats import zonal_stats

import config as C

OVERPASS = "https://overpass-api.de/api/interpreter"


def find(pattern):
    hits = sorted(glob.glob(os.path.join(C.DATA_DIR, pattern)))
    if not hits:
        raise FileNotFoundError(f"Nada em {C.DATA_DIR}/{pattern}. Rode extract_gee.py antes.")
    return hits[-1]


def minmax(s):
    lo, hi = s.min(), s.max()
    return (s - lo) / (hi - lo) if hi > lo else s * 0


NODATA = (-9999, 255)


def read_raster(path):
    """Lê a banda 1 como float com NaN no lugar de nodata."""
    with rasterio.open(path) as src:
        arr = src.read(1).astype("float32")
        if src.nodata is not None:
            arr[arr == src.nodata] = np.nan
        transform, res = src.transform, src.res
    for v in NODATA:
        arr[arr == v] = np.nan
    return arr, transform, abs(res[0] * res[1])


def load_units(path, dissolve, crs):
    gdf = gpd.read_file(path).to_crs(crs)
    if dissolve:
        gdf = gdf.dissolve(by=dissolve, as_index=False)[[dissolve, "geometry"]]
        gdf = gdf.rename(columns={dissolve: "nome"})
    else:
        id_col = next((c for c in ("CD_SETOR", "nome", "name", "NM_BAIRRO") if c in gdf.columns), None)
        gdf["nome"] = gdf[id_col].astype(str) if id_col else gdf.index.astype(str)
        if gdf["nome"].duplicated().any():
            gdf["nome"] = gdf["nome"] + "_" + gdf.index.astype(str)
    return gdf.reset_index(drop=True)


def zonal(gdf, raster, stats, prefix):
    """`raster` pode ser um path ou uma tupla (array, affine) pré-carregada."""
    if isinstance(raster, tuple):
        arr, transform = raster
    else:
        arr, transform, _ = read_raster(raster)
    res = zonal_stats(gdf, arr, affine=transform, stats=stats, nodata=-1e30)
    return pd.DataFrame(res).add_prefix(prefix)


def fetch_pois(bbox):
    w, s, e, n = bbox
    q = f"""
    [out:json][timeout:90];
    (
      nwr["amenity"~"^(school|kindergarten|college|university)$"]({s},{w},{n},{e});
      nwr["amenity"~"^(clinic|hospital|doctors)$"]({s},{w},{n},{e});
      nwr["healthcare"]({s},{w},{n},{e});
      node["highway"="bus_stop"]({s},{w},{n},{e});
      node["public_transport"="platform"]({s},{w},{n},{e});
    );
    out center tags;
    """
    headers = {"User-Agent": "calor-verde-rb/0.1 (contact: mhstorms@gmail.com)"}
    r = requests.post(OVERPASS, data={"data": q}, headers=headers, timeout=120)
    r.raise_for_status()
    rows = []
    for el in r.json()["elements"]:
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        if lat is None:
            continue
        t = el.get("tags", {})
        if t.get("highway") == "bus_stop" or t.get("public_transport") == "platform":
            cat = "ponto_onibus"
        elif t.get("amenity") in ("school", "kindergarten", "college", "university"):
            cat = "educacao"
        else:
            cat = "saude"
        rows.append({"osm_id": f"{el['type']}/{el['id']}", "nome": t.get("name", ""),
                     "categoria": cat, "lon": lon, "lat": lat})
    df = pd.DataFrame(rows).drop_duplicates("osm_id")
    return gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4326")


def sample_raster(points, raster):
    with rasterio.open(raster) as src:
        pts = points.to_crs(src.crs)
        vals = np.array([v[0] for v in src.sample([(g.x, g.y) for g in pts.geometry])], dtype=float)
    vals[np.isin(vals, NODATA)] = np.nan
    return vals


def interpolate_by_buffer(gdf, ok_mask, rasters, buffer_m, min_cobertura, lst_px,
                          px_area, min_pixels=50):
    """Preenche setores sem cobertura amostrando pixels dentro de um buffer da geometria.

    Para cada setor com ok=False, calcula zonal stats numa versão da geometria
    expandida por buffer_m metros. Critério de aceitação:
      - cobertura LST do buffer >= min_cobertura / 5  (relaxado, pois o buffer é
        justamente usado onde o setor em si não tem pixels bons), **e**
      - pelo menos min_pixels pixels LST válidos (default 50 ≈ 4,5 ha), pra
        garantir que a média não seja estatisticamente frágil demais mesmo em
        buffers de setores pequenos.
    Setores isolados (sem pixels válidos nem no buffer) ficam cinzas.

    gdf: GeoDataFrame em CRS métrico (buffer é em metros).
    rasters: dict com paths de lst, ndvi_now, ndvi_base, loss.
    """
    g = gdf.copy()
    g["interpolado"] = False
    needy_pos = np.where(~np.asarray(ok_mask))[0]
    if len(needy_pos) == 0:
        return g

    needy = g.iloc[needy_pos].copy()
    needy["geometry"] = needy.geometry.buffer(buffer_m)
    buf_area = needy.geometry.area.values

    lst_buf = zonal(needy, rasters["lst"], ["mean", "percentile_90", "count"], "lst_")
    ndvi_buf = zonal(needy, rasters["ndvi_now"], ["mean"], "ndvi_atual_")
    base_buf = zonal(needy, rasters["ndvi_base"], ["mean"], "ndvi_base_")
    perda_buf = zonal(needy, rasters["loss"], ["sum", "count"], "perda_")

    cob = (lst_buf["lst_count"].values * lst_px / buf_area).clip(0, 1)
    perda_pct_buf = 100 * perda_buf["perda_sum"].values / perda_buf["perda_count"].replace(0, np.nan).values
    ndvi_delta_buf = ndvi_buf["ndvi_atual_mean"].values - base_buf["ndvi_base_mean"].values

    # Nota: perda_ha (hectares absolutos) NÃO é interpolado porque multiplicar
    # perda_pct do buffer pela área do setor cria valores enganosos em setores
    # grandes (rurais), inflando perda_total_ha da cidade. perda_pct é
    # defensável (percentual), perda_ha fica como estava no zonal original.

    thresh = min_cobertura / 5
    counts = lst_buf["lst_count"].values
    for i, pos in enumerate(needy_pos):
        if cob[i] < thresh or counts[i] < min_pixels or np.isnan(lst_buf["lst_mean"].iat[i]):
            continue
        row = g.index[pos]
        g.at[row, "lst_mean"] = float(lst_buf["lst_mean"].iat[i])
        g.at[row, "lst_percentile_90"] = float(lst_buf["lst_percentile_90"].iat[i])
        g.at[row, "ndvi_atual_mean"] = float(ndvi_buf["ndvi_atual_mean"].iat[i])
        if not np.isnan(ndvi_delta_buf[i]):
            g.at[row, "ndvi_delta"] = float(ndvi_delta_buf[i])
        if not np.isnan(perda_pct_buf[i]):
            g.at[row, "perda_pct"] = float(perda_pct_buf[i])
        g.at[row, "interpolado"] = True
    return g


def _mask_lst_by_situacao(lst_tif, gdf, grupo_val, situacao_col):
    """Retorna (array, affine) do LST com NaN em todos os pixels fora dos
    polígonos de `gdf` cuja `situacao_col` seja igual a `grupo_val`.

    Usado por `interpolate_consciente_sit` pra restringir o buffer da
    interpolação a pixels de contexto compatível (urbano amostra urbano,
    rural amostra rural).
    """
    from rasterio.features import rasterize
    with rasterio.open(lst_tif) as src:
        arr = src.read(1).astype("float32")
        if src.nodata is not None:
            arr[arr == src.nodata] = np.nan
        transform = src.transform
        raster_crs = src.crs
    gdf_r = gdf.to_crs(raster_crs) if gdf.crs != raster_crs else gdf
    shapes = (
        (geom, 1) for geom, s in zip(gdf_r.geometry, gdf_r[situacao_col])
        if str(s) == str(grupo_val)
    )
    mask = rasterize(shapes, out_shape=arr.shape, transform=transform,
                     fill=0, dtype="uint8")
    for v in NODATA:
        arr[arr == v] = np.nan
    arr[mask == 0] = np.nan
    return arr, transform


def interpolate_consciente_sit(gdf, ok_mask, rasters, buffer_m, min_cobertura,
                               lst_px, px_area, min_pixels=50,
                               situacao_col="SITUACAO"):
    """Interpolação por buffer onde o LST amostrado é restrito a pixels da
    mesma SITUACAO do setor-alvo (urbano amostra urbano; rural amostra rural).

    Resolve o problema identificado na Fase 3.3 (QA): o buffer de 3,5 km em
    setor urbano típico de RB puxa muitos pixels menos quentes de vegetação
    ao redor, enviesando a temperatura estimada pra baixo.

    Faz um passe por grupo distinto de SITUACAO, mascarando o LST na grade
    nativa, e usa `interpolate_by_buffer` por baixo. NDVI, perda e NDVI base
    seguem com raster original (não mascarado por contexto); isso vai ser
    iteração futura se necessário.
    """
    out = gdf.copy()
    out["interpolado"] = False
    ok_arr = np.asarray(ok_mask)
    situ = gdf[situacao_col].astype(str).to_numpy()
    for grupo in np.unique(situ):
        is_grp = situ == grupo
        needy_this = (~ok_arr) & is_grp
        if not needy_this.any():
            continue
        lst_arr, lst_tr = _mask_lst_by_situacao(
            rasters["lst"], gdf, grupo, situacao_col)
        rasters_g = dict(rasters)
        rasters_g["lst"] = (lst_arr, lst_tr)
        ok_g = ~needy_this
        step = interpolate_by_buffer(gdf, ok_g, rasters_g, buffer_m,
                                     min_cobertura, lst_px, px_area,
                                     min_pixels=min_pixels)
        got = step["interpolado"].to_numpy()
        n = int(got.sum())
        if n == 0:
            continue
        print(f"[consciente/{grupo}] {n} setor(es) interpolado(s) com LST "
              f"restrito a pixels '{grupo}'")
        for col in ("lst_mean", "lst_percentile_90", "ndvi_atual_mean",
                    "ndvi_delta", "perda_pct"):
            if col in step.columns:
                out.loc[got, col] = step.loc[got, col]
        out.loc[got, "interpolado"] = True
    return out


def join_bairro_osm(gdf, bairros_path, max_m=3000, epsg_metrico=31979):
    """Atribui `bairro` a cada unidade pelo ponto OSM mais próximo (nearest-neighbor).

    OSM mapeia bairros de Rio Branco como pontos, não polígonos (ver data/README.md).
    Centróide da unidade em CRS métrico (SIRGAS 2000 / UTM 19S, EPSG:31979) e
    sjoin_nearest contra a camada de bairros. Unidade cujo bairro mais próximo
    esteja a mais de `max_m` metros fica com `bairro=None` (ex. setor rural
    distante do núcleo urbano).
    """
    if not os.path.isfile(bairros_path):
        print(f"[bairros] {bairros_path} não encontrado — coluna bairro ficará nula")
        gdf["bairro"] = None
        return gdf
    bairros = gpd.read_file(bairros_path).to_crs(epsg=epsg_metrico)
    bairros = bairros[bairros["nome"].notna() & (bairros["nome"] != "")]
    if bairros.empty:
        print("[bairros] camada vazia — coluna bairro ficará nula")
        gdf["bairro"] = None
        return gdf
    bairros = (bairros[["nome", "geometry"]]
               .rename(columns={"nome": "bairro"})
               .reset_index(drop=True))

    u = gdf[["geometry"]].to_crs(epsg=epsg_metrico).copy()
    u["geometry"] = u.geometry.centroid
    u = u.reset_index().rename(columns={"index": "_i"})

    j = gpd.sjoin_nearest(u, bairros, how="left", distance_col="_dist")
    j = j.sort_values("_dist").drop_duplicates("_i", keep="first")
    j = j.set_index("_i").sort_index()

    gdf = gdf.copy()
    gdf["bairro"] = j["bairro"]
    dist = j["_dist"].round(0)
    gdf.loc[dist > max_m, "bairro"] = None

    n_atrib = int(gdf["bairro"].notna().sum())
    print(f"[bairros] atribuídos {n_atrib}/{len(gdf)} setores "
          f"(cutoff {max_m:.0f} m, mediana_dist={dist.median():.0f} m)")
    return gdf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--unidades", required=True)
    ap.add_argument("--dissolver", help="coluna para agregar setores (ex.: NM_BAIRRO)")
    ap.add_argument("--arborizacao", help="CSV com % de arborização IBGE por unidade")
    ap.add_argument("--chave", default="nome", help="coluna de junção do CSV")
    ap.add_argument("--col-arbor", default="pct_arborizacao")
    ap.add_argument("--min-cobertura", type=float, default=0.5,
                    help="fração mínima de pixels válidos de calor para a unidade entrar no ranking")
    ap.add_argument("--sem-pois", action="store_true")
    ap.add_argument("--sem-interpolar", action="store_true",
                    help="desativa interpolação por buffer dos setores sem cobertura LST")
    ap.add_argument("--buffer-interp", type=float, default=3500,
                    help="raio (m) do buffer usado pra amostrar pixels dos setores cinzas")
    ap.add_argument("--min-pixels-interp", type=int, default=50,
                    help="mínimo de pixels LST válidos no buffer para aceitar a interpolação")
    ap.add_argument("--interpolacao-ingenua", action="store_true",
                    help="desliga a interpolação consciente de SITUACAO (urb/rural) "
                         "e volta à versão da Fase 1 (buffer mistura todos os contextos)")
    ap.add_argument("--bairros-gpkg", default="data/bairros_rb.gpkg",
                    help="camada de pontos de bairro OSM (ver scripts/fetch_bairros_osm.py)")
    ap.add_argument("--bairro-max-m", type=float, default=3000,
                    help="distância máxima (m) do centróide do setor ao ponto de bairro mais próximo")
    ap.add_argument("--sem-bairros", action="store_true",
                    help="pula o nearest-join com bairros_rb.gpkg")
    args = ap.parse_args()
    os.makedirs(C.OUT_DIR, exist_ok=True)

    lst_tif = find("lst_*.tif")
    ndvi_now_tif = find(f"ndvi_{C.YEAR_NOW}.tif")
    ndvi_base_tif = find(f"ndvi_{C.YEAR_BASE}.tif")
    loss_tif = find("perda_*.tif")

    with rasterio.open(loss_tif) as src:
        crs = src.crs
    _, _, px_area = read_raster(loss_tif)
    lst_arr, _, lst_px = read_raster(lst_tif)
    lst_all = lst_arr[~np.isnan(lst_arr)]
    lst_p75 = float(np.percentile(lst_all, 75))
    lst_mean = float(lst_all.mean())

    gdf = load_units(args.unidades, args.dissolver, crs)
    print(f"{len(gdf)} unidades")

    if args.sem_bairros:
        gdf["bairro"] = None
    else:
        gdf = join_bairro_osm(gdf, args.bairros_gpkg, max_m=args.bairro_max_m)

    parts = [
        zonal(gdf, lst_tif, ["mean", "percentile_90", "count"], "lst_"),
        zonal(gdf, ndvi_now_tif, ["mean"], "ndvi_atual_"),
        zonal(gdf, ndvi_base_tif, ["mean"], "ndvi_base_"),
        zonal(gdf, loss_tif, ["sum", "count"], "perda_"),
    ]
    gdf = gpd.GeoDataFrame(pd.concat([gdf] + parts, axis=1), geometry="geometry", crs=crs)

    gdf["area_ha"] = gdf.geometry.area / 1e4
    gdf["cobertura_calor"] = (gdf["lst_count"] * lst_px / gdf.geometry.area).clip(upper=1)
    gdf["perda_ha"] = gdf["perda_sum"].fillna(0) * px_area / 1e4
    gdf["perda_pct"] = 100 * gdf["perda_sum"] / gdf["perda_count"]
    gdf["ndvi_delta"] = gdf["ndvi_atual_mean"] - gdf["ndvi_base_mean"]
    gdf["anomalia_calor"] = gdf["lst_mean"] - lst_mean

    if args.arborizacao:
        arb = pd.read_csv(args.arborizacao, dtype={args.chave: str})
        gdf = gdf.merge(arb[[args.chave, args.col_arbor]], how="left",
                        left_on="nome", right_on=args.chave)

    ok = gdf["cobertura_calor"] >= args.min_cobertura
    gdf["interpolado"] = False
    if not args.sem_interpolar:
        rasters = {"lst": lst_tif, "ndvi_now": ndvi_now_tif,
                   "ndvi_base": ndvi_base_tif, "loss": loss_tif}
        if args.interpolacao_ingenua or "SITUACAO" not in gdf.columns:
            gdf = interpolate_by_buffer(gdf, ok, rasters,
                                        buffer_m=args.buffer_interp,
                                        min_cobertura=args.min_cobertura,
                                        lst_px=lst_px, px_area=px_area,
                                        min_pixels=args.min_pixels_interp)
            modo = "ingênua"
        else:
            gdf = interpolate_consciente_sit(gdf, ok, rasters,
                                             buffer_m=args.buffer_interp,
                                             min_cobertura=args.min_cobertura,
                                             lst_px=lst_px, px_area=px_area,
                                             min_pixels=args.min_pixels_interp)
            modo = "consciente de SITUACAO"
        gdf["anomalia_calor"] = gdf["lst_mean"] - lst_mean
        n_interp = int(gdf["interpolado"].sum())
        print(f"interpoladas: {n_interp} unidades (buffer {args.buffer_interp:.0f} m, {modo})")
        ok = ok | gdf["interpolado"]
    g = gdf[ok].copy()
    falta_verde = 1 - minmax(g["ndvi_atual_mean"])
    if args.arborizacao and g[args.col_arbor].notna().any():
        falta_verde = (falta_verde + (1 - minmax(g[args.col_arbor]))) / 2
    w = C.WEIGHTS
    g["indice_prioridade"] = 100 * (
        w["calor"] * minmax(g["lst_mean"])
        + w["falta_verde"] * falta_verde.fillna(0)
        + w["perda"] * minmax(g["perda_pct"].fillna(0))
    )
    g["rank"] = g["indice_prioridade"].rank(ascending=False, method="min").astype(int)
    gdf.loc[g.index, "indice_prioridade"] = g["indice_prioridade"]
    gdf.loc[g.index, "rank"] = g["rank"]
    gdf["rank"] = gdf["rank"].astype("Int64")

    cols = ["rank", "nome", "bairro", "indice_prioridade", "lst_mean", "lst_percentile_90",
            "anomalia_calor", "ndvi_atual_mean", "ndvi_delta", "perda_ha", "perda_pct",
            "area_ha", "cobertura_calor", "interpolado"]
    if args.arborizacao:
        cols.append(args.col_arbor)
    gdf = gdf.sort_values("rank", na_position="last")
    gdf[cols].round(3).to_csv(os.path.join(C.OUT_DIR, "ranking.csv"), index=False)
    gdf[cols + ["geometry"]].round(3).to_crs("EPSG:4326").to_file(
        os.path.join(C.OUT_DIR, "unidades_prioridade.geojson"), driver="GeoJSON")

    resumo = {
        "ano_atual": C.YEAR_NOW, "ano_base": C.YEAR_BASE,
        "lst_media_cidade": round(lst_mean, 2), "lst_p75_cidade": round(lst_p75, 2),
        "perda_total_ha": round(float(gdf["perda_ha"].sum()), 1),
        "top5_prioridade": g.sort_values("rank").head(5)[["nome", "bairro", "indice_prioridade", "lst_mean"]]
                            .round(2).to_dict("records"),
    }

    if not args.sem_pois:
        bbox = tuple(C.AOI_BBOX)
        pois = fetch_pois(bbox)
        pois["lst"] = sample_raster(pois, lst_tif)
        pois["zona_quente"] = pois["lst"] >= lst_p75
        pois.drop(columns=["lon", "lat"]).to_file(os.path.join(C.OUT_DIR, "pois_calor.geojson"),
                                                  driver="GeoJSON")
        resumo["pois_em_zona_quente"] = (
            pois[pois.zona_quente].groupby("categoria").size().to_dict())
        resumo["pois_total"] = pois.groupby("categoria").size().to_dict()

    with open(os.path.join(C.OUT_DIR, "resumo.json"), "w") as f:
        json.dump(resumo, f, ensure_ascii=False, indent=2, default=int)
    print(json.dumps(resumo, ensure_ascii=False, indent=2, default=int))

    validate_outputs(gdf, resumo, C.OUT_DIR, args.sem_pois)


def validate_outputs(gdf, resumo, out_dir, sem_pois):
    """Checks de sanidade pós-pipeline. Fail-hard em HARD, só WARN em SOFT."""
    hard_fails, soft_warns = [], []

    def hard(cond, msg):
        if not cond:
            hard_fails.append(msg)

    def soft(cond, msg):
        if not cond:
            soft_warns.append(msg)

    total = len(gdf)
    com_rank = int(gdf["rank"].notna().sum())
    cinzas = total - com_rank
    interp = int(gdf["interpolado"].fillna(False).sum()) if "interpolado" in gdf.columns else 0
    lst_media = resumo.get("lst_media_cidade")
    lst_p75 = resumo.get("lst_p75_cidade")
    perda = resumo.get("perda_total_ha")
    top5 = resumo.get("top5_prioridade", [])

    hard(total > 0, "zero unidades no gdf de saída")
    hard(com_rank / max(total, 1) >= 0.50,
         f"menos de 50% dos setores têm rank ({com_rank}/{total})")
    hard(lst_media is not None and 20 <= lst_media <= 50,
         f"lst_media_cidade fora da faixa 20-50°C: {lst_media}")
    hard(lst_p75 is not None and lst_p75 >= lst_media,
         f"lst_p75 ({lst_p75}) deveria ser >= lst_media ({lst_media})")
    hard(len(top5) == 5, f"top5 tem {len(top5)} entradas, esperado 5")
    hard(all(t.get("indice_prioridade") is not None and
             t.get("lst_mean") is not None for t in top5),
         "top5 tem campos nulos")

    for f in ["ranking.csv", "unidades_prioridade.geojson", "resumo.json"]:
        p = os.path.join(out_dir, f)
        hard(os.path.exists(p) and os.path.getsize(p) > 0,
             f"arquivo de saída ausente ou vazio: {f}")
    if not sem_pois:
        p = os.path.join(out_dir, "pois_calor.geojson")
        hard(os.path.exists(p) and os.path.getsize(p) > 0,
             "pois_calor.geojson ausente ou vazio")

    soft(com_rank / max(total, 1) >= 0.85,
         f"cobertura do mapa abaixo de 85% (atual {100*com_rank/total:.1f}%)")
    soft(lst_media is None or 30 <= lst_media <= 40,
         f"lst_media_cidade fora da faixa típica 30-40°C: {lst_media}")
    soft(perda is None or 100 <= perda <= 10000,
         f"perda_total_ha fora da faixa típica 100-10000: {perda}")
    soft(interp <= 6 * max(cinzas, 1),
         f"muitos interpolados vs. cinzas ({interp} interpolados para {cinzas} cinzas)")

    print("\n=== QA ===")
    print(f"total={total}  com_rank={com_rank} ({100*com_rank/total:.1f}%)  "
          f"cinzas={cinzas}  interpolados={interp}")
    print(f"lst_media={lst_media}°C  lst_p75={lst_p75}°C  perda_total={perda}ha")
    if soft_warns:
        print("⚠ SOFT:")
        for w in soft_warns:
            print(f"  - {w}")
    if hard_fails:
        print("✗ HARD:")
        for f in hard_fails:
            print(f"  - {f}")
        sys.exit(2)
    if not soft_warns:
        print("✓ todos os checks passaram")


if __name__ == "__main__":
    main()
