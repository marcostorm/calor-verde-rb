"""Baixa MODIS LST do Google Earth Engine como camada secundária (Fase 7.1).

Rationale: Landsat 8/9 tem 30 m de resolução mas revisita a cada 16 dias; em
nuvem persistente, setores ficam sem dado mesmo com a interpolação por buffer
de 3,5 km. MODIS (Terra MOD11A2 + Aqua MYD11A2) tem 1 km de resolução mas
revisita quase diária, com dois composites de 8 dias por sensor na janela
jun-set. Serve como fallback só pros setores que continuam cinzas após
Landsat + interpolação — não substitui o Landsat na análise principal.

Gera em data/:
  lst_modis_{ANO}.tif    temperatura de superfície (°C), MODIS Terra+Aqua,
                         mediana da estação seca, 1 km, filtrado por QC

Uso:
  earthengine authenticate
  GEE_PROJECT=meu-projeto python scripts/extract_modis.py
  GEE_PROJECT=meu-projeto CALOR_VERDE_YEAR_NOW=2025 python scripts/extract_modis.py
"""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import ee  # noqa: E402
import requests  # noqa: E402

import config as C  # noqa: E402


def init():
    if not C.GEE_PROJECT:
        sys.exit("Defina GEE_PROJECT com o ID do seu projeto Google Cloud.")
    ee.Initialize(project=C.GEE_PROJECT)


def aoi():
    if C.AOI_GEOJSON:
        with open(C.AOI_GEOJSON) as f:
            gj = json.load(f)
        feats = gj["features"] if gj.get("type") == "FeatureCollection" else [gj]
        return ee.FeatureCollection(
            [ee.Feature(ee.Geometry(ft["geometry"])) for ft in feats]
        ).geometry()
    return ee.Geometry.Rectangle(C.AOI_BBOX)


def dry_season(year):
    m0, m1 = C.DRY_MONTHS
    return ee.Date.fromYMD(year, m0, 1), ee.Date.fromYMD(year, m1, 1).advance(1, "month")


def modis_lst(region, year):
    """Combina MOD11A2 (Terra) + MYD11A2 (Aqua), filtra por QC e devolve mediana em °C.

    Variável: LST_Day_1km (temperatura às ~10h30 Terra / ~13h30 Aqua local).
    Scale: 0.02 (Kelvin). Convertemos pra °C.
    QC_Day bits 0-1: 00 = boa qualidade, 01 = qualidade aceitável, 10/11 = ruim.
    """
    terra = ee.ImageCollection("MODIS/061/MOD11A2").filterBounds(region).filterDate(*dry_season(year))
    aqua = ee.ImageCollection("MODIS/061/MYD11A2").filterBounds(region).filterDate(*dry_season(year))
    col = terra.merge(aqua)

    def prep(img):
        qa_ok = img.select("QC_Day").bitwiseAnd(0b11).lte(1)  # bits 0-1 ≤ 1
        lst_c = img.select("LST_Day_1km").multiply(0.02).subtract(273.15)
        return lst_c.rename("lst").updateMask(qa_ok)

    col = col.map(prep)
    return col.median().clip(region).toFloat(), col.size()


def with_nodata(img):
    """Pixels mascarados viram -9999 para o GeoTIFF baixado ter nodata explícito."""
    return img.unmask(-9999).toFloat()


def download(img, name, scale, region):
    path = os.path.join(C.DATA_DIR, f"{name}.tif")
    url = img.getDownloadURL(
        {"region": region, "scale": scale, "crs": C.CRS, "format": "GEO_TIFF"}
    )
    r = requests.get(url, timeout=600)
    r.raise_for_status()
    with open(path, "wb") as f:
        f.write(r.content)
    print(f"  ✔ {path} ({len(r.content) / 1e6:.2f} MB)")


def to_drive(img, name, scale, region):
    task = ee.batch.Export.image.toDrive(
        image=img, description=name, folder="calor_verde_rb", fileNamePrefix=name,
        region=region, scale=scale, crs=C.CRS, maxPixels=1e9,
        formatOptions={"cloudOptimized": True},
    )
    task.start()
    print(f"  ↗ exportando {name} para o Drive (task {task.id})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--drive", action="store_true", help="exporta pro Google Drive em vez de baixar")
    args = ap.parse_args()

    init()
    os.makedirs(C.DATA_DIR, exist_ok=True)
    region = aoi()
    save = to_drive if args.drive else download

    print(f"MODIS LST (Terra + Aqua, estação seca de {C.YEAR_NOW})...")
    lst, n_cenas = modis_lst(region, C.YEAR_NOW)
    print(f"  composites 8-dias usados: {n_cenas.getInfo()}")
    save(with_nodata(lst), f"lst_modis_{C.YEAR_NOW}", 1000, region)


if __name__ == "__main__":
    main()
