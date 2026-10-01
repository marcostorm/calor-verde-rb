# Operação

Como instalar, autenticar, rodar o pipeline e usar o visualizador.

## Pré-requisitos

- Linux (testado em Ubuntu 24.04).
- Python 3.12 com `python3.12-venv` instalado.
- Conta Google com projeto GCP e Earth Engine API ativada (gratuito para uso não-comercial): https://console.cloud.google.com

## Instalação (uma vez)

```bash
cd /home/marcos/workspace/calor-verde-rb

# venv (se ainda não existir)
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

# autenticação do Earth Engine (abre navegador)
.venv/bin/activate                 # ou: source .venv/bin/activate
earthengine authenticate

# variável de ambiente com o ID do projeto GCP
export GEE_PROJECT=seu-projeto-gcp
```

Para não exportar toda sessão, adicione ao `~/.bashrc` ou crie um `.envrc` com `direnv`.

## Setor censitário de Rio Branco

Já salvo em `data/setores_rb.gpkg`. Foi gerado assim (uma vez):

```bash
# baixar a malha do Acre
curl -L -o data/AC_setores_CD2022.gpkg \
  "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_de_setores_censitarios__divisoes_intramunicipais/censo_2022/setores/gpkg/UF/AC/AC_setores_CD2022.gpkg"

# filtrar Rio Branco (CD_MUN = 1200401)
.venv/bin/python -c "
import geopandas as gpd
g = gpd.read_file('data/AC_setores_CD2022.gpkg')
g[g['CD_MUN']=='1200401'].to_file('data/setores_rb.gpkg', driver='GPKG')
"
```

## Rodar o pipeline

Com `GEE_PROJECT` exportado e venv ativo:

```bash
# 1. baixar rasters (LST + NDVI atual + NDVI base + perda)
python extract_gee.py

# 1b. se o download direto falhar (área grande, limite ~50 MB), use Google Drive
python extract_gee.py --drive
```

Para alterar os anos, edite `config.py:YEAR_NOW` e `YEAR_BASE`.

```bash
# 2. análise + ranking (versão conservadora, min-cobertura 50%)
python analyze.py --unidades data/setores_rb.gpkg

# 2b. análise ampla (min-cobertura 20%)
python analyze.py --unidades data/setores_rb.gpkg --min-cobertura 0.2
```

## Salvar as duas versões lado a lado

```bash
python analyze.py --unidades data/setores_rb.gpkg --min-cobertura 0.5
cp data/out/unidades_prioridade.geojson data/out/unidades_prioridade_conservador.geojson
cp data/out/ranking.csv                 data/out/ranking_conservador.csv
cp data/out/resumo.json                 data/out/resumo_conservador.json

python analyze.py --unidades data/setores_rb.gpkg --min-cobertura 0.2
cp data/out/unidades_prioridade.geojson data/out/unidades_prioridade_amplo.geojson
cp data/out/ranking.csv                 data/out/ranking_amplo.csv
cp data/out/resumo.json                 data/out/resumo_amplo.json
```

## Abrir o visualizador

```bash
cd data/out
python3 -m http.server 8787
```

Depois abra `http://localhost:8787/viewer.html` no navegador. Para parar o server: `Ctrl+C` ou `pkill -f 'http.server 8787'`.

O visualizador carrega sozinho os três resumos, as duas versões do choropleth e os POIs. Switch de versão (rádio no topo do painel direito) recarrega sem precisar reload da página.

## Troubleshooting

### `pip install -r requirements.txt` falha com "externally-managed-environment"
Use o venv. Ubuntu 24.04 bloqueia instalação global via PEP 668.

### `ensurepip is not available` ao criar venv
`sudo apt install python3.12-venv`.

### `extract_gee.py` falha com HTTP 403 ou "User project not specified"
`GEE_PROJECT` não está exportado, ou o projeto não tem a Earth Engine API habilitada.

### `extract_gee.py` falha com "File size exceeded"
A área ficou grande demais para download direto. Use `python extract_gee.py --drive` e baixe os `.tif` da pasta `calor_verde_rb/` do seu Google Drive para `data/`.

### `analyze.py` falha com `HTTPError: 406` no Overpass
A API do OpenStreetMap exige `User-Agent`. Já corrigido em `analyze.py:92` — se refizer o repo do zero, aplicar o mesmo patch:

```python
headers = {"User-Agent": "calor-verde-rb/0.1 (contact: seu-email)"}
r = requests.post(OVERPASS, data={"data": q}, headers=headers, timeout=120)
```

### Muitos setores urbanos ficam cinza no mapa
Pode ser:
1. **AOI pequena demais** — ver `config.py:AOI_BBOX`. Deve cobrir o bbox dos setores urbanos com buffer. Para Rio Branco: `[-67.939, -10.117, -67.652, -9.886]`.
2. **Nuvem persistente** na estação seca — baixe `--min-cobertura` para 0,2 ou amplie `DRY_MONTHS`.

### Dissolve por `NM_BAIRRO` retorna 0 unidades
Rio Branco **não tem** bairros oficializados no IBGE 2022 (campo `NM_BAIRRO` é nulo em 100% dos setores). Use ranking por setor (sem `--dissolver`), ou importe uma camada de bairros da Prefeitura/OSM e faça spatial-join antes.

### Visualizador abre em branco / não mostra o choropleth
Abra DevTools (F12) → Console. Verifique se `fetch` dos geojsons retornou 200. Se abrir o `viewer.html` direto como `file://`, o fetch é bloqueado — tem que servir via `http.server`.
