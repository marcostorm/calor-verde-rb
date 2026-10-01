"""Gera rasters e bairros sintéticos para testar analyze.py sem Earth Engine."""
import os

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box

import config as C

os.makedirs(C.DATA_DIR, exist_ok=True)
rng = np.random.default_rng(0)
x0, y0 = 620000, 8900000  # canto NW aprox. de Rio Branco em UTM 19S
W = H = 1000  # 10 km a 10 m


def write(name, arr, res, dtype, nodata):
    tr = from_origin(x0, y0, res, res)
    with rasterio.open(os.path.join(C.DATA_DIR, name), "w", driver="GTiff", height=arr.shape[0],
                       width=arr.shape[1], count=1, dtype=dtype, crs=C.CRS, transform=tr,
                       nodata=nodata) as dst:
        dst.write(arr.astype(dtype), 1)


yy, xx = np.mgrid[0:H, 0:W] / W
ndvi_base = 0.3 + 0.5 * xx + rng.normal(0, 0.05, (H, W))          # mais verde a leste
ndvi_now = ndvi_base.copy()
ndvi_now[300:500, 600:800] -= 0.4                                   # desmatamento simulado
ndvi_now[:50, :50] = -9999                                          # nuvem
loss = ((ndvi_base >= C.NDVI_LOSS_BASE_MIN) & (ndvi_now - ndvi_base <= C.NDVI_LOSS_DELTA)).astype("uint8")
loss[:50, :50] = 255
lst_small = 42 - 8 * xx[::3, ::3] + rng.normal(0, 0.5, (334, 334))  # mais quente a oeste
lst_small[-20:, -20:] = -9999

write(f"ndvi_{C.YEAR_BASE}.tif", ndvi_base, 10, "float32", -9999)
write(f"ndvi_{C.YEAR_NOW}.tif", ndvi_now, 10, "float32", -9999)
write(f"perda_{C.YEAR_BASE}_{C.YEAR_NOW}.tif", loss, 10, "uint8", 255)
write(f"lst_{C.YEAR_NOW}.tif", lst_small, 30, "float32", -9999)

cells = [box(x0 + i * 2000, y0 - (j + 1) * 2000, x0 + (i + 1) * 2000, y0 - j * 2000)
         for i in range(5) for j in range(5)]
gpd.GeoDataFrame({"NM_BAIRRO": [f"Bairro {k:02d}" for k in range(25)]}, geometry=cells,
                 crs=C.CRS).to_file(os.path.join(C.DATA_DIR, "bairros_fake.geojson"))
print("dados sintéticos prontos")
