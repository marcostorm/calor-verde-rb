"""Etapa 1: extrai camadas de satélite do Google Earth Engine.

Gera em data/:
  lst_{ANO}.tif            temperatura de superfície (°C), Landsat 8/9, mediana da estação seca, 30 m
  ndvi_{ANO}.tif           NDVI Sentinel-2, mediana da estação seca, 10 m (ano base e ano atual)
  perda_{BASE}_{ATUAL}.tif 1 = pixel que era verde e perdeu vegetação, 0 = não, 10 m

Uso:
  earthengine authenticate
  GEE_PROJECT=meu-projeto python extract_gee.py            # download direto
  GEE_PROJECT=meu-projeto python extract_gee.py --drive    # exporta para o Google Drive
"""
import argparse
import json
import os
import sys

import ee
import requests

import config as C


def init():
    if not C.GEE_PROJECT:
        sys.exit("Defina GEE_PROJECT com o ID do seu projeto Google Cloud.")
    ee.Initialize(project=C.GEE_PROJECT)


def aoi():
    if C.AOI_GEOJSON:
        with open(C.AOI_GEOJSON) as f:
            gj = json.load(f)
        feats = gj["features"] if gj.get("type") == "FeatureCollection" else [gj]
        return ee.FeatureCollection([ee.Feature(ee.Geometry(ft["geometry"])) for ft in feats]).geometry()
    return ee.Geometry.Rectangle(C.AOI_BBOX)


def dry_season(year):
    m0, m1 = C.DRY_MONTHS
    return ee.Date.fromYMD(year, m0, 1), ee.Date.fromYMD(year, m1, 1).advance(1, "month")


def landsat_lst(region, year):
    col = (
        ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
        .merge(ee.ImageCollection("LANDSAT/LC09/C02/T1_L2"))
        .filterBounds(region)
        .filterDate(*dry_season(year))
        .filter(ee.Filter.lt("CLOUD_COVER", 70))
    )

    def prep(img):
        # QA_PIXEL bits 1-4: nuvem dilatada, cirrus, nuvem, sombra de nuvem
        clear = img.select("QA_PIXEL").bitwiseAnd(0b11110).eq(0)
        lst = img.select("ST_B10").multiply(0.00341802).add(149.0).subtract(273.15)
        return lst.rename("lst").updateMask(clear)

    col = col.map(prep)
    return col.median().clip(region).toFloat(), col.size()


def s2_ndvi(region, year):
    cs = ee.ImageCollection("GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED")
    col = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(region)
        .filterDate(*dry_season(year))
        .linkCollection(cs, ["cs_cdf"])
    )

    def prep(img):
        ndvi = img.normalizedDifference(["B8", "B4"]).rename("ndvi")
        return ndvi.updateMask(img.select("cs_cdf").gte(C.CS_THRESHOLD))

    col = col.map(prep)
    return col.median().clip(region).toFloat(), col.size()


def vegetation_loss(ndvi_base, ndvi_now):
    delta = ndvi_now.subtract(ndvi_base)
    loss = ndvi_base.gte(C.NDVI_LOSS_BASE_MIN).And(delta.lte(C.NDVI_LOSS_DELTA))
    # 255 = sem dado válido (nuvem em algum dos anos)
    return loss.rename("perda").unmask(255).toUint8()


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
    print(f"  ✔ {path} ({len(r.content) / 1e6:.1f} MB)")


def to_drive(img, name, scale, region):
    task = ee.batch.Export.image.toDrive(
        image=img, description=name, folder="calor_verde_rb", fileNamePrefix=name,
        region=region, scale=scale, crs=C.CRS, maxPixels=1e10,
        formatOptions={"cloudOptimized": True},
    )
    task.start()
    print(f"  ↗ exportando {name} para o Drive (task {task.id})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drive", action="store_true", help="exporta para o Google Drive em vez de baixar")
    args = ap.parse_args()

    init()
    os.makedirs(C.DATA_DIR, exist_ok=True)
    region = aoi()
    save = to_drive if args.drive else download

    print(f"Calor (Landsat) {C.YEAR_NOW}...")
    lst, n_lst = landsat_lst(region, C.YEAR_NOW)
    print(f"  cenas usadas: {n_lst.getInfo()}")

    print(f"NDVI (Sentinel-2) {C.YEAR_BASE} e {C.YEAR_NOW}...")
    ndvi_base, n_b = s2_ndvi(region, C.YEAR_BASE)
    ndvi_now, n_n = s2_ndvi(region, C.YEAR_NOW)
    print(f"  cenas usadas: base={n_b.getInfo()} atual={n_n.getInfo()}")

    loss = vegetation_loss(ndvi_base, ndvi_now)

    save(with_nodata(lst), f"lst_{C.YEAR_NOW}", 30, region)
    save(with_nodata(ndvi_base), f"ndvi_{C.YEAR_BASE}", 10, region)
    save(with_nodata(ndvi_now), f"ndvi_{C.YEAR_NOW}", 10, region)
    save(loss, f"perda_{C.YEAR_BASE}_{C.YEAR_NOW}", 10, region)


if __name__ == "__main__":
    main()
