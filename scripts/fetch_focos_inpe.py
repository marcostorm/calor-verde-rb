"""Baixa focos de queimada do INPE pra Rio Branco em uma janela temporal.

Fonte: Programa Queimadas / INPE, arquivos mensais abertos em
  https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/mensal/Brasil/

Satélite usado: AQUA_M-T (tarde), o satélite de referência do INPE desde 2002.
Permite comparação consistente ao longo da série histórica. Outros satélites
(NOAA-20, NPP-375, GOES-19) detectam mais focos mas causam overcounting
(mesmo fogo visto 3-4 vezes) e exigem clustering espaço-temporal pra dedup.

Fluxo:
  1. Pra cada mês da janela, baixa focos_mensal_br_YYYYMM.csv (streaming).
  2. Filtra por estado=ACRE e satelite=AQUA_M-T linha-a-linha, sem carregar
     o CSV inteiro em memória (cada mês tem ~100 MB).
  3. Clip final por polígono dissolvido do município (setores_rb.gpkg).
  4. Salva data/focos_rb.csv com id, lat, lon, data_hora_gmt, bioma, frp.

Uso:
  python scripts/fetch_focos_inpe.py                    # jun-set/2026 (padrao)
  python scripts/fetch_focos_inpe.py --inicio 2025-06 --fim 2025-09
"""
import argparse
import csv
import io
import sys
from pathlib import Path

import geopandas as gpd
import requests
from shapely.geometry import Point

BASE_URL = "https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/mensal/Brasil"
SATELITE_REF = "AQUA_M-T"
ESTADO = "ACRE"


def meses_entre(inicio: str, fim: str):
    """Gera YYYYMM entre inicio e fim (inclusivos). Formato: 'YYYY-MM'."""
    ai, mi = map(int, inicio.split("-"))
    af, mf = map(int, fim.split("-"))
    y, m = ai, mi
    while (y, m) <= (af, mf):
        yield f"{y:04d}{m:02d}"
        m += 1
        if m > 12:
            m = 1
            y += 1


def baixa_mes_filtrado(yyyymm: str, timeout=120):
    """Baixa o CSV mensal do INPE e retorna só os focos AQUA_M-T de ACRE.

    Faz streaming linha-a-linha pra não carregar ~100 MB em memória por mês.
    """
    url = f"{BASE_URL}/focos_mensal_br_{yyyymm}.csv"
    r = requests.get(url, stream=True, timeout=timeout)
    r.raise_for_status()
    r.encoding = r.encoding or "utf-8"
    buf = io.StringIO()
    for chunk in r.iter_content(chunk_size=1 << 20, decode_unicode=True):
        if chunk:
            buf.write(chunk)
    buf.seek(0)
    reader = csv.DictReader(buf)
    rows = []
    for row in reader:
        if row.get("estado", "").strip() == ESTADO and row.get("satelite", "").strip() == SATELITE_REF:
            rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inicio", default="2026-06", help="mes inicial YYYY-MM (default: 2026-06)")
    ap.add_argument("--fim", default="2026-09", help="mes final YYYY-MM (default: 2026-09)")
    ap.add_argument("--setores", default="data/setores_rb.gpkg", help="geopackage de setores pra clip")
    ap.add_argument("--saida", default="data/focos_rb.csv")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    setores = gpd.read_file(args.setores)
    if setores.crs is None or setores.crs.to_epsg() != 4326:
        setores = setores.to_crs(4326)
    municipio = setores.geometry.union_all()
    print(f"[fetch_focos_inpe] municipio bbox = {municipio.bounds}")

    todos_rows = []
    for m in meses_entre(args.inicio, args.fim):
        print(f"[fetch_focos_inpe] baixando {m}...", end=" ", flush=True)
        try:
            rows = baixa_mes_filtrado(m)
        except Exception as e:
            print(f"ERRO: {e}", file=sys.stderr)
            sys.exit(2)
        print(f"{len(rows)} focos AC+AQUA_M-T")
        todos_rows.extend(rows)

    print(f"[fetch_focos_inpe] clipando pelo municipio...")
    dentro = []
    for row in todos_rows:
        try:
            lat = float(row["lat"])
            lon = float(row["lon"])
        except (KeyError, ValueError):
            continue
        if municipio.contains(Point(lon, lat)):
            dentro.append(row)
    print(f"[fetch_focos_inpe] {len(dentro)}/{len(todos_rows)} focos dentro de Rio Branco")

    saida = Path(args.saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    campos = ["id", "lat", "lon", "data_hora_gmt", "satelite", "bioma", "frp"]
    with saida.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        for row in dentro:
            w.writerow({k: row.get(k, "") for k in campos})
    print(f"[fetch_focos_inpe] gravado {saida} ({len(dentro)} linhas)")


if __name__ == "__main__":
    main()
