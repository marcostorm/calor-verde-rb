# Glossário

Termos em ordem alfabética, com explicação em linguagem simples e definição técnica quando pertinente.

## Anomalia de calor

LST do setor **menos** LST média da cidade. Valor positivo = mais quente que a média urbana.
Exemplo: anomalia +4,8 °C = esse setor é quase 5 graus mais quente que a média de Rio Branco.

## AOI (Area of Interest)

Caixa delimitadora que define o recorte espacial do download de dados de satélite. Em `config.py:AOI_BBOX` (coordenadas lon/lat).

## Cobertura de calor

Fração dos pixels de LST do setor que ficaram válidos após máscara de nuvem/sombra do Landsat. Vai de 0 a 1 (0% a 100%). Setores abaixo do limiar (`--min-cobertura`) **saem do ranking** porque a estatística fica frágil.

## Estação seca

Jun–set na Amazônia. Período com menos nuvens, mais cenas aproveitáveis dos satélites, e também pico de calor — por isso é a janela usada para o LST.

## GEE (Google Earth Engine)

Plataforma gratuita (uso não-comercial) da Google que hospeda petabytes de imagens de satélite e permite processamento na nuvem. É quem rastreia os pixels Landsat e Sentinel-2 que o pipeline consome.

## Índice de prioridade

Score de 0 a 100 que combina calor, falta de verde e perda de vegetação:

```
0,5 × calor + 0,3 × falta_verde + 0,2 × perda
```

Cada termo normalizado min-max entre as unidades. **100 = o pior caso dessa rodada** (mais quente, menos verde, mais perda). Pesos em `config.py:WEIGHTS`.

## Landsat

Família de satélites da NASA/USGS. O pipeline usa Landsat 8 e 9 (bandas termais, resolução 30 m) para medir LST.

## LST (Land Surface Temperature)

Temperatura da superfície medida pelo sensor termal do Landsat. Mede o quanto o chão (asfalto, telhado, mato, água) irradia calor. **Não é** a temperatura do ar. Útil para comparar áreas entre si no mesmo horário.

## min-cobertura

Parâmetro `--min-cobertura` do `analyze.py`. Fração mínima de pixels válidos de LST que um setor precisa ter para entrar no ranking. Padrão: 0,5 (50%). Alternativa salva: 0,2 (20%).

## NDVI (Normalized Difference Vegetation Index)

Índice de vegetação derivado do Sentinel-2: `(NIR − Vermelho) / (NIR + Vermelho)`. Varia de −1 a 1:
- `> 0,5` ≈ vegetação densa
- `0,2–0,5` ≈ gramado/vegetação esparsa
- próximo a 0 ≈ solo nu, asfalto, telhado
- negativo ≈ água

## NDVI Δ (delta)

NDVI atual (2026) menos NDVI base (2019). Negativo = perdeu verde no período.

## p75 / p90

Percentis.
- **p75 da cidade** = temperatura abaixo da qual estão 75% das áreas; os 25% mais quentes formam a **zona quente**.
- **p90 do setor** = temperatura típica dos 10% mais quentes dentro dele (quente localizado, útil pra detectar laje escaldante).

## Perda (ha e %)

Área onde pixels verdes em 2019 (NDVI ≥ 0,5) caíram pelo menos 0,2 pontos até 2026.
- **Perda_ha** = hectares nesse estado.
- **Perda_%** = fração dos pixels classificáveis do setor que entraram no critério.

Captura corte, queimada **e** seca severa — não distingue entre eles. Cruzar com focos INPE para rotular como desmatamento.

## POI (Point of Interest)

Pontos geográficos de interesse: escolas, unidades de saúde, pontos de ônibus. Fonte: OpenStreetMap (completude varia conforme mapeadores locais).

## Rank

Posição no ranking de prioridade. 1 = plantar primeiro.

## Sentinel-2

Família de satélites da ESA. O pipeline usa Sentinel-2 L2A (resolução 10 m) para medir NDVI.

## Setor censitário

Menor unidade da divisão territorial do IBGE para o Censo. Em Rio Branco, 669 setores (593 urbanos + 76 rurais). Como o IBGE **não oficializou divisão por bairros** em Rio Branco, o ranking é por setor.

## Versão conservadora / Versão ampla

Dois recortes salvos do ranking:
- **Conservador** (min-cobertura 0,5): só setores com ≥50% de pixels de LST válidos. Melhor para decisão pública — números mais defensáveis.
- **Ampla** (min-cobertura 0,2): inclui setores com ≥20%. Mapa mais completo visualmente, mas ruidoso nas bordas.

## Zona quente

Área com LST ≥ p75 da cidade. É onde pessoas estão expostas ao calor mais extremo. Usada para contar quantas escolas/unidades de saúde/pontos de ônibus estão em exposição crítica.
