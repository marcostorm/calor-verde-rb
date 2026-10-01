# Decisões de projeto

Decisões feitas durante o setup inicial (set/2026) e por quê. Serve de registro para rodadas futuras.

## 1. Ambiente Python

**Decisão:** venv local em `.venv/` com `python3.12-venv`.
**Por quê:** Ubuntu 24.04 bloqueia `pip install` global (PEP 668). Alternativas descartadas: `--break-system-packages` (risco de conflitar com pacotes do apt) e `uv` (mais uma dependência).

## 2. AOI (Area of Interest)

**Decisão:** bbox `[-67.939, -10.117, -67.652, -9.886]` (~31 × 26 km).
**Por quê:** o bbox original do `config.py` (`[-67.90, -10.06, -67.72, -9.90]`, ~20 × 18 km) deixava **171 setores urbanos sem cobertura de LST** — áreas inteiras do sul e sudeste da cidade (Belo Jardim, Rosa Linda, Cidade do Povo, Santa Helena) ficavam fora do raster.

O novo bbox foi calculado como `envelope(setores urbanos) + 2 km de buffer`:

```python
import geopandas as gpd
g = gpd.read_file('data/setores_rb.gpkg').to_crs('EPSG:4326')
urb = g[g['SITUACAO'] == 'Urbana']
b = urb.total_bounds
pad = 0.02   # ~2 km
AOI = [b[0]-pad, b[1]-pad, b[2]+pad, b[3]+pad]
```

**Para outros municípios:** usar o mesmo cálculo com a malha IBGE da UF correspondente.

## 3. Anos

**Decisão:** `YEAR_NOW = 2026`, `YEAR_BASE = 2019`.
**Por quê:**
- 2026: dado mais recente disponível (estação seca jun–set/2026 terminou em 30/09/2026).
- 2019: primeiro ano com cobertura decente do Sentinel-2 L2A no Brasil, e ponto de partida razoável para "antes" na série histórica. Mantido mesmo após atualizar para 2026 para preservar a janela de 7 anos de perda.

**Trade-off:** janela mais longa capta mais mudança, mas inclui também mais ruído (secas intermediárias). Para análise ano-a-ano, mudar `YEAR_BASE = 2025` daria uma leitura de "mudança no último ciclo" — vale fazer uma rodada paralela quando precisar.

## 4. Agregação

**Decisão:** por **setor censitário**, sem dissolver por bairro.
**Por quê:** o IBGE 2022 tem `NM_BAIRRO = NULL` em 100% dos 669 setores de Rio Branco — o município não oficializou divisão por bairros. Dissolver por bairro zerava o GDF.

**Alternativa não implementada:** cruzar com uma camada da Prefeitura ou do OpenStreetMap (`admin_level=10`) via spatial-join. Pedido para o futuro se houver demanda por agregação por bairro.

## 5. min-cobertura

**Decisão:** salvar duas versões — `conservador` (0,5) e `amplo` (0,2).
**Por quê:**
- Threshold 0,5 é mais defensável para comunicação pública (cada setor tem pelo menos metade dos pixels válidos), mas descarta 158 setores urbanos no mapa de 2026 (cobertura de nuvem persistente).
- Threshold 0,2 recupera 31 setores urbanos extras, útil visualmente para o mapa não parecer "esburacado", mas com números mais ruidosos.

Deixar as duas versões salvas evita re-rodar o pipeline para ver cada uma; o visualizador alterna via rádio.

## 6. Paleta de cores

**Decisão:** YlOrRd (ColorBrewer, 7 níveis).
**Por quê:**
- Semântica alinhada com o tema calor (amarelo → vermelho → bordô = urgência crescente).
- Leitura imediata para público leigo — "vermelho = urgente" é código universal.
- Padrão em mapas de intensidade/risco climático.

**Alternativa testada e descartada:** viridis (roxo → amarelo). Mais acessível a daltônicos e padrão em dataviz científica, mas semanticamente neutra — para audiência não-técnica, YlOrRd comunica melhor.

Se o produto for publicado para grande público, validar acessibilidade (daltonismo) com simulador tipo Coblis. Caso necessário, trocar por `Reds` do ColorBrewer com 5 níveis + rótulos textuais no popup.

## 7. User-Agent no Overpass

**Decisão:** patch em `analyze.py:92-93` adicionando `User-Agent` no POST para a Overpass API.
**Por quê:** sem UA explícito, a Overpass passou a responder HTTP 406. Patch mínimo que não altera comportamento do pipeline.

## 8. Visualizador local

**Decisão:** `viewer.html` autocontido em `data/out/`, servido por `python3 -m http.server`.
**Por quê:**
- Zero dependência de build (JS puro + Leaflet via CDN).
- `fetch()` precisa de HTTP (file:// é bloqueado), por isso o `http.server`.
- Serve como protótipo direto para integrar no site do projeto quando houver — basta copiar HTML/JS e trocar os caminhos.

## 9. Documentação separada do código

**Decisão:** documentos em `/home/marcos/Documentos/calor-verde-rb/`, código em `/home/marcos/workspace/calor-verde-rb/`.
**Por quê:** pedido explícito do dono do projeto. O repo de código tem seu próprio `README.md` curto (quickstart); esta pasta é a referência estendida.

## Pendências / melhorias futuras

- [ ] Camada de bairros da Prefeitura ou do OSM para agregação por bairro.
- [ ] Cruzar perda de verde com focos de calor do INPE (BDQueimadas) para separar desmatamento vs. queimada vs. seca.
- [ ] Validar daltonismo da paleta se o produto virar público.
- [ ] Rodada paralela com `YEAR_BASE = 2025` para análise de mudança no último ciclo.
- [ ] Inicializar repositório git (`git init`) e versionar `config.py`, `extract_gee.py`, `analyze.py`, `viewer.html` — hoje é tudo arquivo solto.
