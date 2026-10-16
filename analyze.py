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
        arr = src.read(1).astype("float64")
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
    perda_ha_buf = perda_buf["perda_sum"].fillna(0).values * px_area / 1e4
    ndvi_delta_buf = ndvi_buf["ndvi_atual_mean"].values - base_buf["ndvi_base_mean"].values

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
        g.at[row, "perda_ha"] = float(perda_ha_buf[i])
        g.at[row, "interpolado"] = True
    return g


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
    ap.add_argument("--buffer-interp", type=float, default=1500,
                    help="raio (m) do buffer usado pra amostrar pixels dos setores cinzas")
    ap.add_argument("--min-pixels-interp", type=int, default=50,
                    help="mínimo de pixels LST válidos no buffer para aceitar a interpolação")
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
        gdf = interpolate_by_buffer(gdf, ok, rasters,
                                    buffer_m=args.buffer_interp,
                                    min_cobertura=args.min_cobertura,
                                    lst_px=lst_px, px_area=px_area,
                                    min_pixels=args.min_pixels_interp)
        gdf["anomalia_calor"] = gdf["lst_mean"] - lst_mean
        n_interp = int(gdf["interpolado"].sum())
        print(f"interpoladas: {n_interp} unidades (buffer {args.buffer_interp:.0f} m)")
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

    cols = ["rank", "nome", "indice_prioridade", "lst_mean", "lst_percentile_90", "anomalia_calor",
            "ndvi_atual_mean", "ndvi_delta", "perda_ha", "perda_pct", "area_ha", "cobertura_calor",
            "interpolado"]
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
        "top5_prioridade": g.sort_values("rank").head(5)[["nome", "indice_prioridade", "lst_mean"]]
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


if __name__ == "__main__":
    main()
