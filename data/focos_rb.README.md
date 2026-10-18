# `focos_rb.csv`

Focos de queimada detectados em Rio Branco (AC) na estação seca atual, baixados do Programa Queimadas / INPE.

## Colunas

- `id` — identificador único do foco (UUID gerado pelo INPE)
- `lat`, `lon` — coordenadas em WGS84 (EPSG:4326)
- `data_hora_gmt` — momento da detecção, GMT (UTC)
- `satelite` — sempre `AQUA_M-T` (ver filtro abaixo)
- `bioma` — bioma onde o foco caiu (sempre `Amazônia` em RB)
- `frp` — Fire Radiative Power em MW (potência radiativa, proxy de intensidade)

## Origem

- Arquivo-fonte: `focos_mensal_br_YYYYMM.csv` (um por mês)
- URL: <https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/mensal/Brasil/>
- Programa: Programa Queimadas, DGI/INPE
- Licença: dados abertos (Lei 12.527/2011)

## Filtros aplicados

Script `scripts/fetch_focos_inpe.py` baixa os CSVs mensais (um por mês da janela) e aplica em sequência:

1. **`estado == ACRE`** linha-a-linha durante o streaming (cada CSV mensal tem ~100 MB; filtrar aqui evita carregar tudo em memória).
2. **`satelite == AQUA_M-T`**. Esse é o satélite de referência histórica do INPE desde 2002: duas passagens diárias (manhã e tarde) e critério padrão pra comparação temporal. Outros satélites presentes nos arquivos (NOAA-20, NPP-375, GOES-19) detectam mais focos, mas um mesmo fogo é visto 3–4 vezes e o dedup exigiria clustering espaço-temporal. AQUA_M-T evita isso e segue a convenção do próprio INPE pra séries históricas.
3. **Clip pelo município**: ponto-em-polígono contra `data/setores_rb.gpkg` (union_all dos 669 setores). Elimina focos que caíram em outros municípios do AC.

## Janela temporal

Padrão: **jun–set/2026** (estação seca da Amazônia ocidental, mesmo período do LST). Configurável via `--inicio YYYY-MM --fim YYYY-MM`.

## Cobertura observada (rodada 2026-10-18)

- jun/2026: 20 focos AC + AQUA_M-T, após clip no município: parte caiu em RB
- jul/2026: 56
- ago/2026: 487
- set/2026: 877
- **Rio Branco (jun-set): 119 focos** (de 1.440 no AC total)

Essa concentração em ago-set é esperada: pico de seca na Amazônia ocidental.

## Uso no pipeline

```bash
python analyze.py --focos data/focos_rb.csv
```

O `analyze.py` faz spatial join point-in-polygon pra contar focos por setor censitário. Resultado vai pra coluna `focos_estacao` no ranking e no geojson. **Não entra no índice de prioridade** — é camada de contexto expositivo, não um ingrediente da nota.

## Limitações assumidas

- **Foco ≠ área queimada.** O satélite detecta assinatura térmica num pixel de ~1 km. Um foco pode corresponder a um fogo de poucos metros ou a um incêndio de centenas de hectares; a métrica não distingue. Pra inferência de área queimada, dado complementar seria MapBiomas Fogo (polígonos de cicatriz) ou produto MOD64A1 (área queimada do MODIS).
- **AQUA_M-T é subamostra.** Dois overpasses por dia; fogo noturno curto ou fogo diurno de baixa intensidade pode passar despercebido. Pra inventário operacional (combate em tempo real), consolidar com GOES-19 e NOAA-20 faz sentido. Aqui o uso é analítico-comparativo, então AQUA_M-T basta.
- **Precisão de localização**: ~1 km (resolução do pixel MODIS); foco pode ser atribuído ao setor vizinho perto da borda.
- **Confusão com outras fontes de calor**: refinaria, flare de gás, aço fundido podem gerar falso positivo. Em RB (sem indústria pesada), o risco é residual mas existente.
