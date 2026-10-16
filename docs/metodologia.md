# Metodologia

Como as camadas são produzidas e combinadas no índice de prioridade.

## 1. Área de interesse (AOI)

Caixa delimitadora em WGS84: `[-67.939, -10.117, -67.652, -9.886]` (~31 × 26 km), definida para cobrir o bbox dos 593 setores urbanos do IBGE + buffer de ~2 km. Configurada em `config.py:AOI_BBOX`.

Alternativa: definir `AOI_GEOJSON=caminho/perimetro.geojson` para usar um polígono exato (ex. perímetro urbano oficial da prefeitura).

## 2. Temperatura de superfície — LST

- Fonte: `LANDSAT/LC08/C02/T1_L2` + `LANDSAT/LC09/C02/T1_L2` (Collection 2, Level-2, atmosfericamente corrigido).
- Janela: estação seca (jun–set) do ano atual (`YEAR_NOW` em `config.py`).
- Filtro de cena: `CLOUD_COVER < 70`.
- Máscara de pixel: `QA_PIXEL` bits 1–4 (nuvem dilatada, cirrus, nuvem, sombra).
- Conversão: `ST_B10 × 0.00341802 + 149.0 − 273.15` → °C.
- Composição: **mediana** da coleção.
- Resolução de saída: 30 m.
- Projeção: EPSG:31979 (SIRGAS 2000 / UTM 19S).

LST mede o **que o chão irradia** (asfalto, telhado, mata, água), não o ar que a pessoa respira. É excelente para **comparar áreas entre si** no mesmo horário, mas valores absolutos não equivalem à "temperatura ambiente".

## 3. Vegetação — NDVI

- Fonte: `COPERNICUS/S2_SR_HARMONIZED` (Sentinel-2 L2A).
- Máscara de nuvem: `GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED`, `cs_cdf ≥ 0.6`.
- NDVI = `(B8 − B4) / (B8 + B4)`.
- Janela: estação seca (jun–set) do ano atual e do ano base (`YEAR_BASE = 2019`).
- Composição: **mediana** da coleção.
- Resolução de saída: 10 m.

## 4. Perda de vegetação

- Critério: pixel que **era verde em 2019** (NDVI_base ≥ 0,5) **e caiu pelo menos 0,2 pontos** até o ano atual (ΔNDVI ≤ −0,2).
- Saída: raster binário 10 m (1 = perda, 0 = não, 255 = sem dado em algum dos anos).

**Importante:** o NDVI cai por corte, por queimada **e** por seca severa. Em anos de seca forte na Amazônia esse número infla por estresse hídrico, não por desmatamento. Para comunicação pública séria, cruze com focos de calor do INPE antes de rotular como "perda de árvores".

## 5. Agregação por setor

Para cada setor censitário (`data/setores_rb.gpkg`, filtrado por `CD_MUN = 1200401`):

| Variável | Cálculo |
|---|---|
| `lst_mean` / `lst_percentile_90` | média e p90 de LST dos pixels dentro do setor |
| `lst_count` | nº de pixels válidos de LST |
| `cobertura_calor` | `lst_count × área_pixel / área_setor`, clip a [0,1] |
| `ndvi_atual_mean`, `ndvi_base_mean` | médias de NDVI |
| `ndvi_delta` | diferença atual − base |
| `perda_sum`, `perda_count` | nº de pixels perdidos e nº de pixels classificáveis |
| `perda_ha` | `perda_sum × área_pixel / 10 000` |
| `perda_pct` | `100 × perda_sum / perda_count` |
| `anomalia_calor` | `lst_mean − média LST da cidade` |

Setores com `cobertura_calor < min-cobertura` **não entram no ranking direto**. Threshold padrão: 0,5. Alternativa salva: 0,2.

## 5a. Interpolação por buffer (preenche setores sem cobertura)

Para setores que ficariam fora do ranking por falta de pixels LST válidos (nuvem persistente), uma etapa de recuperação roda **antes** do índice:

1. Expande a geometria do setor com um buffer de `buffer-interp` metros (padrão **3500 m**).
2. Recalcula zonal stats de LST, NDVI atual, NDVI base e perda dentro do buffer.
3. Aceita a interpolação se **duas** condições forem atendidas:
   - cobertura LST do buffer ≥ `min-cobertura / 5` (10% no conservador, 4% no amplo), e
   - pelo menos **50 pixels LST válidos** no buffer (≈ 4,5 ha de dado real, independente do tamanho do setor — evita que setores pequenos aceitem interpolações baseadas em pouquíssimos pixels).
4. Marca `interpolado = true` no setor. O ranking usa esses valores normalmente.

**Por que buffer e não vizinhos (IDW)?** IDW copia valores do setor mais próximo, criando clusters artificiais quando vários setores cinza compartilham o mesmo vizinho dominante (top-N viram todos iguais). Buffer amostra pixels reais da vizinhança imediata — cada setor recebe uma combinação diferente de pixels, preservando a diversidade do ranking.

**O que ainda fica cinza:** setores sem pixels LST válidos suficientes num raio de 3,5 km — tipicamente rurais isolados fora do AOI urbano. Setores em manchas grandes de nuvem persistente (2º Distrito, Belo Jardim/Santo Afonso) costumam ser alcançados por esse raio.

Flags:
- `--sem-interpolar` desativa (default: ON).
- `--buffer-interp N` ajusta o raio em metros (default 3500).
- `--min-pixels-interp N` ajusta o mínimo de pixels no buffer (default 50).

## 6. Índice de prioridade

Para os setores que passaram no filtro de cobertura:

```
índice = 100 × [ 0,5 × norm(LST)
               + 0,3 × norm(1 − NDVI_atual)
               + 0,2 × norm(perda_pct) ]
```

- `norm(x)` = normalização min-max entre as unidades (0 = menor valor, 1 = maior).
- Pesos em `config.py:WEIGHTS`.
- Se houver arborização IBGE (`--arborizacao`), o termo `falta_verde` é a média entre `(1 − norm(NDVI))` e `(1 − norm(pct_arborizacao))`.

O índice é **relativo** entre as unidades daquela rodada. Comparar valores entre rodadas de anos diferentes é válido para o rank (quem é o pior), mas não para o valor absoluto do índice.

## 7. POIs

Via Overpass API (OpenStreetMap, estado atual):

- Educação: `amenity ∈ {school, kindergarten, college, university}`
- Saúde: `amenity ∈ {clinic, hospital, doctors}` ou `healthcare=*`
- Ônibus: `highway=bus_stop` ou `public_transport=platform`

Para cada POI, LST é amostrado no raster. "Zona quente" = LST ≥ p75 da cidade.

## 8. Resumo da cidade (`resumo.json`)

- `lst_media_cidade`, `lst_p75_cidade`: estatísticas sobre **todos** os pixels válidos do raster LST (não restrito aos setores que passaram no filtro).
- `perda_total_ha`: soma de `perda_ha` entre todos os setores com dado.
- `top5_prioridade`: 5 primeiros do ranking.
- `pois_em_zona_quente` / `pois_total`: contagens por categoria.

## Limitações a declarar em qualquer comunicação pública

1. **LST não é temperatura do ar.** É quanto a superfície irradia ao meio-dia local (~10h30 em Rio Branco).
2. **NDVI cai por seca e queimada**, não só por corte. Validar perdas com imagem de alta resolução ou focos INPE.
3. **Cobertura de nuvem** descarta setores com `< min-cobertura` sem fallback direto. A interpolação por buffer (seção 5a) recupera a maioria usando pixels de um raio de 3,5 km, mas setores sem dado nenhum nesse raio permanecem cinzas no mapa (tipicamente rurais isolados). Setores interpolados aparecem com borda tracejada dourada e são tratados como estimativa (não medição direta no polígono do setor).
4. **OSM pode ter completude variável** em POIs — a contagem de escolas/saúde reflete o que está mapeado, não a realidade oficial da Semed/Sesacre.
5. **O ranking é relativo**: num ano em que a cidade inteira está mais quente, os valores absolutos sobem, mas as posições relativas são estáveis (confirmado empiricamente — Top-3 idêntico entre 2025 e 2026).
