# Calor & Verde — Rio Branco

Documentação do pipeline de dados que cruza **temperatura de superfície (LST)**, **vegetação (NDVI)** e **perda de verde** por setor censitário de Rio Branco (AC) e produz um ranking de **prioridade de plantio**.

Repositório do código: `/home/marcos/workspace/calor-verde-rb`
Esta documentação: `/home/marcos/Documentos/calor-verde-rb`

## Estrutura destes documentos

| Arquivo | Para quê |
|---|---|
| [metodologia.md](metodologia.md) | Como as camadas são geradas, como o índice é calculado, limitações. |
| [glossario.md](glossario.md) | Termos técnicos em linguagem simples (LST, NDVI, p75, perda, zona quente, …). |
| [operacao.md](operacao.md) | Como instalar, autenticar, rodar o pipeline e abrir o visualizador. |
| [decisoes.md](decisoes.md) | Decisões feitas durante o setup (AOI, min-cobertura, paleta de cores, versão de dados). |
| [resultados-2026.md](resultados-2026.md) | Snapshot do estado atual: números-chave, top-10 e observações. |
| [roadmap.md](roadmap.md) | Fases planejadas de evolução (hardening, deploy, nomes de bairros, longitudinal, fontes complementares). |

## Resumo em uma página

- **Fonte do calor:** Landsat 8/9, banda termal (LST), 30 m, mediana da estação seca (jun–set).
- **Fonte do verde:** Sentinel-2 L2A, NDVI 10 m, mediana da estação seca.
- **Unidades de análise:** 669 setores censitários (IBGE Censo 2022) de Rio Branco (`CD_MUN = 1200401`), sendo 593 urbanos e 76 rurais. O IBGE **não oficializou divisão por bairros** em Rio Branco, por isso o ranking é por setor.
- **Dados atuais:** 2026 (atual) vs 2019 (base).
- **AOI:** bbox `[-67.939, -10.117, -67.652, -9.886]` (~31 × 26 km), cobre todos os setores urbanos + buffer de 2 km.
- **Índice de prioridade (0–100):** `0,5 × calor + 0,3 × falta de verde + 0,2 × perda` (cada termo min-max entre as unidades).
- **Duas versões salvas:** `conservador` (cobertura ≥ 50% — mais robusto) e `amplo` (≥ 20% — mais setores no mapa).

## Visualizador

Abrir após rodar o pipeline:

```bash
cd /home/marcos/workspace/calor-verde-rb/data/out
python3 -m http.server 8787
# navegador: http://localhost:8787/viewer.html
```

O visualizador tem: choropleth por prioridade (paleta YlOrRd), pontos de escolas/saúde/ônibus do OSM, Top-10 clicável, resumo da cidade com tooltips e glossário embutido.

## Entradas e saídas

**Entradas:**
- `data/setores_rb.gpkg` — malha IBGE 2022 filtrada para Rio Branco (gerado uma vez, a partir do pacote `AC_setores_CD2022.gpkg`).
- `data/lst_*.tif`, `data/ndvi_*.tif`, `data/perda_*.tif` — rasters do Earth Engine.

**Saídas em `data/out/`:**
- `unidades_prioridade.geojson` / `unidades_prioridade_conservador.geojson` / `unidades_prioridade_amplo.geojson` — polígonos coloridos para o mapa.
- `ranking.csv` + versões `_conservador` e `_amplo` — tabela ordenada.
- `pois_calor.geojson` — escolas, saúde e pontos de ônibus com LST amostrado.
- `resumo.json` + versões `_conservador` e `_amplo` — números para a home.
- `viewer.html` — página autocontida com Leaflet.
