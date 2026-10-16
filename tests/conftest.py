"""Fixture sintética para o teste de integração do pipeline.

Gera, em um diretório temporário, 10 setores sintéticos e rasters 50x50 com
padrões conhecidos (gradiente leste-oeste de LST, perda localizada em um
único setor). Permite rodar analyze.py end-to-end em ~1-2s, sem Earth Engine.

Padrões:
- LST: 42 °C no oeste, 30 °C no leste (gradiente horizontal).
- NDVI base: 0,2 no oeste, 0,8 no leste.
- NDVI now: igual ao base, exceto num bloco 10x10 no centro-norte que cai 0,4.
- Perda: 1 (perdeu) nos pixels do bloco acima, 0 no resto.
- Setores: grade 5 colunas x 2 linhas, cobrindo todo o raster.
"""
import os

import geopandas as gpd
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box

CRS = "EPSG:31979"
X0, Y0 = 620000.0, 8900000.0  # canto NW, UTM 19S aproximado de Rio Branco
LST_RES = 30.0
LST_W = LST_H = 50
RASTER_SIDE_M = LST_W * LST_RES  # 1500 m
NDVI_RES = 10.0
NDVI_W = NDVI_H = int(RASTER_SIDE_M / NDVI_RES)  # 150


def _write_tif(path, arr, res, dtype, nodata):
    tr = from_origin(X0, Y0, res, res)
    with rasterio.open(
        path, "w", driver="GTiff",
        height=arr.shape[0], width=arr.shape[1],
        count=1, dtype=dtype, crs=CRS, transform=tr, nodata=nodata,
    ) as dst:
        dst.write(arr.astype(dtype), 1)


@pytest.fixture(scope="session")
def fixture_dir(tmp_path_factory):
    base = tmp_path_factory.mktemp("calor_verde_fixture")
    data = base / "data"
    out = data / "out"
    data.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(42)

    xx_lst = np.linspace(0, 1, LST_W)
    lst = 42.0 - 12.0 * xx_lst[np.newaxis, :] + rng.normal(0, 0.3, (LST_H, LST_W))
    lst = lst.astype("float32")

    xx_ndvi = np.linspace(0, 1, NDVI_W)
    ndvi_base = 0.2 + 0.6 * xx_ndvi[np.newaxis, :] + rng.normal(0, 0.02, (NDVI_H, NDVI_W))
    ndvi_base = ndvi_base.astype("float32")

    ndvi_now = ndvi_base.copy()
    loss_block = slice(30, 60), slice(60, 90)
    ndvi_now[loss_block] -= 0.4

    loss = np.zeros((NDVI_H, NDVI_W), dtype="uint8")
    loss[loss_block] = 1

    _write_tif(data / "lst_2026.tif", lst, LST_RES, "float32", -9999)
    _write_tif(data / "ndvi_2019.tif", ndvi_base, NDVI_RES, "float32", -9999)
    _write_tif(data / "ndvi_2026.tif", ndvi_now, NDVI_RES, "float32", -9999)
    _write_tif(data / "perda_2019_2026.tif", loss, NDVI_RES, "uint8", 255)

    cols, rows = 5, 2
    cell_w = RASTER_SIDE_M / cols
    cell_h = RASTER_SIDE_M / rows
    polys, names = [], []
    for i in range(cols):
        for j in range(rows):
            minx = X0 + i * cell_w
            maxx = X0 + (i + 1) * cell_w
            maxy = Y0 - j * cell_h
            miny = Y0 - (j + 1) * cell_h
            polys.append(box(minx, miny, maxx, maxy))
            names.append(f"setor_{i:02d}_{j:02d}")
    gdf = gpd.GeoDataFrame({"CD_SETOR": names, "SITUACAO": ["1"] * len(polys)},
                           geometry=polys, crs=CRS)
    unidades = data / "unidades.gpkg"
    gdf.to_file(unidades, driver="GPKG")

    return {
        "data_dir": str(data),
        "out_dir": str(out),
        "unidades": str(unidades),
        "n_setores": len(polys),
    }
