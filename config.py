"""Configuração central do pipeline. Ajuste aqui antes de rodar."""
import os

# Área de interesse: bbox da mancha urbana de Rio Branco (lon_min, lat_min, lon_max, lat_max).
# Para usar o perímetro exato, aponte AOI_GEOJSON para um arquivo GeoJSON (EPSG:4326).
AOI_BBOX = [-67.939, -10.117, -67.652, -9.886]
AOI_GEOJSON = os.environ.get("AOI_GEOJSON")  # ex.: "data/perimetro_urbano.geojson"

# SIRGAS 2000 / UTM 19S: projeção métrica que cobre Rio Branco
CRS = "EPSG:31979"

# Estação seca (menos nuvens na Amazônia): junho a setembro
DRY_MONTHS = (6, 9)
YEAR_NOW = 2026
YEAR_BASE = 2019  # Sentinel-2 L2A tem boa cobertura no Brasil a partir de 2019

# Critério de perda de vegetação: era verde (NDVI >= base_min) e caiu pelo menos |delta|
NDVI_LOSS_BASE_MIN = 0.5
NDVI_LOSS_DELTA = -0.2

# Limiar de nuvem do Cloud Score+ (0-1; maior = mais rigoroso)
CS_THRESHOLD = 0.6

# Pesos do índice de prioridade (somam 1)
WEIGHTS = {"calor": 0.5, "falta_verde": 0.3, "perda": 0.2}

GEE_PROJECT = os.environ.get("GEE_PROJECT")  # ID do seu projeto Google Cloud
DATA_DIR = os.environ.get("CALOR_VERDE_DATA_DIR", "data")
OUT_DIR = os.environ.get("CALOR_VERDE_OUT_DIR", os.path.join(DATA_DIR, "out"))
LOGS_DIR = os.environ.get("CALOR_VERDE_LOGS_DIR", "logs")
