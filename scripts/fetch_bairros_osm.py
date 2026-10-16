"""Baixa bairros não-oficiais de Rio Branco (OSM via Overpass) para data/bairros_rb.gpkg.

Rio Branco não tem bairros oficializados no IBGE 2022 (campo NM_BAIRRO nulo em
100% dos setores). Usamos OSM como camada auxiliar: cada setor censitário recebe
um `bairro_osm` por spatial-join (etapa 2.2 do roadmap).

Fontes buscadas, em ordem de preferência de uso:
  - admin_level=10  (sub-bairros formais, relation)
  - admin_level=9   (bairros formais, relation)
  - place=suburb    (bairros, mais comum no Brasil)
  - place=neighbourhood (sub-bairros)
  - place=quarter

Fluxo:
  1. Lê o bbox do municipio a partir de data/setores_rb.gpkg.
  2. Query Overpass por bbox (retry em 4 mirrors).
  3. Filtra feições que caem dentro do contorno do municipio (dissolve dos setores).
  4. Normaliza para EPSG:4326 e salva em data/bairros_rb.gpkg.

Uso:
  python scripts/fetch_bairros_osm.py
  python scripts/fetch_bairros_osm.py --saida data/bairros_rb.gpkg \
      --mirror https://overpass.kumi.systems/api/interpreter --debug
"""
import argparse
import os
import sys
from pathlib import Path

import geopandas as gpd
import requests
from shapely.geometry import LineString, MultiPolygon, Point, Polygon

MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
    "https://overpass.openstreetmap.fr/api/interpreter",
]

HEADERS = {"User-Agent": "calor-verde-rb/0.1 (contact: mhstorms@gmail.com)"}

PLACE_TYPES = ("suburb", "neighbourhood", "quarter")
ADMIN_LEVELS = ("9", "10")


def build_query(bbox):
    s, w, n, e = bbox[1], bbox[0], bbox[3], bbox[2]  # overpass usa (s,w,n,e)
    places = "|".join(PLACE_TYPES)
    levels = "|".join(ADMIN_LEVELS)
    return f"""
[out:json][timeout:180];
(
  node["place"~"^({places})$"]({s},{w},{n},{e});
  way["place"~"^({places})$"]({s},{w},{n},{e});
  rel["place"~"^({places})$"]({s},{w},{n},{e});
  rel["boundary"="administrative"]["admin_level"~"^({levels})$"]({s},{w},{n},{e});
);
out geom tags;
""".strip()


def fetch(mirror, query, debug=False):
    if debug:
        print(f"query:\n{query}\n")
    r = requests.post(mirror, data={"data": query}, headers=HEADERS, timeout=200)
    r.raise_for_status()
    return r.json()


def _stitch_segments(segments):
    """Costura segmentos de linha em anéis fechados (Polygon).

    Usado pra reconstruir multipolygons de relations OSM a partir dos ways 'outer'.
    """
    segs = [list(s) for s in segments if len(s) >= 2]
    rings = []
    while segs:
        cur = segs.pop()
        changed = True
        while changed and cur[0] != cur[-1]:
            changed = False
            for i, s in enumerate(segs):
                if cur[-1] == s[0]:
                    cur.extend(s[1:]); segs.pop(i); changed = True; break
                if cur[-1] == s[-1]:
                    cur.extend(reversed(s[:-1])); segs.pop(i); changed = True; break
                if cur[0] == s[-1]:
                    cur = s[:-1] + cur; segs.pop(i); changed = True; break
                if cur[0] == s[0]:
                    cur = list(reversed(s[1:])) + cur; segs.pop(i); changed = True; break
        if cur[0] == cur[-1] and len(cur) >= 4:
            rings.append(Polygon(cur))
    return rings


def element_to_geom(el):
    t = el["type"]
    if t == "node":
        return Point(el["lon"], el["lat"])
    if t == "way":
        coords = [(p["lon"], p["lat"]) for p in el.get("geometry", [])]
        if len(coords) < 2:
            return None
        if coords[0] == coords[-1] and len(coords) >= 4:
            return Polygon(coords)
        return LineString(coords)
    if t == "relation":
        outer_segs = []
        for m in el.get("members", []):
            if m.get("type") != "way" or m.get("role") not in ("outer", ""):
                continue
            coords = [(p["lon"], p["lat"]) for p in m.get("geometry", [])]
            if len(coords) >= 2:
                outer_segs.append(coords)
        polys = _stitch_segments(outer_segs)
        if not polys:
            # relation só com node members (place=suburb como ponto) — usa centroid dos nodes
            pts = []
            for m in el.get("members", []):
                if m.get("type") == "node":
                    pts.append((m.get("lon"), m.get("lat")))
            if pts:
                return Point(sum(p[0] for p in pts) / len(pts),
                             sum(p[1] for p in pts) / len(pts))
            return None
        if len(polys) == 1:
            return polys[0]
        return MultiPolygon(polys)
    return None


def to_gdf(data):
    rows = []
    for el in data.get("elements", []):
        tags = el.get("tags") or {}
        place = tags.get("place")
        admin = tags.get("admin_level")
        is_place = place in PLACE_TYPES
        is_admin = (
            admin in ADMIN_LEVELS and tags.get("boundary") == "administrative"
        )
        if not (is_place or is_admin):
            continue
        geom = element_to_geom(el)
        if geom is None or geom.is_empty:
            continue
        tipo = f"admin_level={admin}" if is_admin else place
        rows.append({
            "osm_id": f"{el['type']}/{el['id']}",
            "nome": tags.get("name") or tags.get("name:pt") or "",
            "tipo": tipo,
            "admin_level": admin,
            "place": place,
            "geometry": geom,
        })
    return gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--setores", default="data/setores_rb.gpkg",
                    help="GPKG do municipio pra definir bbox e filtro geo")
    ap.add_argument("--saida", default="data/bairros_rb.gpkg")
    ap.add_argument("--mirror", help="força um mirror; sem isso, tenta a lista")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    if not os.path.isfile(args.setores):
        sys.exit(f"setores não encontrados: {args.setores}")

    setores = gpd.read_file(args.setores).to_crs("EPSG:4326")
    bbox = setores.total_bounds.tolist()  # [w, s, e, n]
    municipio = setores.geometry.union_all()
    # Buffer pequeno pra tolerar imprecisões de borda OSM × IBGE
    municipio_buf = municipio.buffer(0.005)  # ~500 m em RB
    print(f"municipio bbox: {bbox}")

    query = build_query(bbox)
    mirrors = [args.mirror] if args.mirror else MIRRORS
    data = None
    for m in mirrors:
        print(f"trying {m}…")
        try:
            data = fetch(m, query, debug=args.debug)
            print(f"  OK: {len(data.get('elements', []))} elementos")
            break
        except Exception as e:
            print(f"  failed: {e}")
    if data is None:
        sys.exit("todos os mirrors falharam")

    gdf = to_gdf(data)
    print(f"geometrias válidas: {len(gdf)}")
    if gdf.empty:
        sys.exit("nada retornado — veja debug da query")

    # Filtra feições que ao menos intersectam o municipio (bbox pode pegar cidades vizinhas)
    gdf = gdf[gdf.geometry.intersects(municipio_buf)].reset_index(drop=True)
    print(f"após filtro geo: {len(gdf)}")

    # Resumo
    print("\ntipos:")
    for k, v in gdf["tipo"].value_counts().items():
        print(f"  {k:20s} {v}")
    print("formatos:")
    for k, v in gdf.geom_type.value_counts().items():
        print(f"  {k:20s} {v}")
    sem_nome = int((gdf["nome"] == "").sum())
    if sem_nome:
        print(f"atenção: {sem_nome} bairro(s) sem nome")
    duplic = gdf["nome"].value_counts()
    duplic = duplic[duplic > 1]
    if not duplic.empty:
        print(f"nomes duplicados: {dict(duplic)}")

    out = Path(args.saida)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    gdf.to_file(out, driver="GPKG")
    print(f"\n→ {out} ({len(gdf)} feições)")


if __name__ == "__main__":
    main()
