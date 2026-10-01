# Resultados — estação seca 2026

Snapshot da rodada atual. Dados: Landsat/Sentinel-2 jun–set 2026 (atual) vs jun–set 2019 (base). Malha IBGE Censo 2022.

## Números-chave da cidade

| Métrica | Valor |
|---|---|
| LST média da mancha urbana | **34,83 °C** |
| LST p75 (limiar de "zona quente") | **36,51 °C** |
| Perda de verde acumulada 2019→2026 | **2.037,7 ha** |
| Setores censitários totais | 669 (593 urbanos + 76 rurais) |
| Setores no ranking (conservador, min-cob 50%) | 454 |
| Setores no ranking (ampla, min-cob 20%) | 491 |

## POIs expostos ao calor extremo (LST ≥ p75)

| Categoria | Em zona quente | Total mapeado (OSM) |
|---|---|---|
| Escolas | 142 | 254 |
| Unidades de saúde | 30 | 43 |
| Pontos de ônibus | 55 | 57 |

**Interpretação cuidadosa:** OSM pode subestimar o universo real de equipamentos públicos. Cruzar com cadastros oficiais da Semed/Sesacre antes de usar como contagem definitiva. Mas a **proporção** (56% das escolas em zona quente, 70% da saúde, 96% dos pontos de ônibus) é indicativa.

## Top 10 setores — versão conservadora (min-cob 50%)

| Rank | Setor | Prioridade | LST média |
|---|---|---|---|
| 1 | 120040105000314 | 96,6 | 45,8 °C |
| 2 | 120040105000098 | 94,8 | 45,4 °C |
| 3 | 120040105000062 | 89,7 | 44,4 °C |
| 4 | 120040105000655 | 89,2 | 44,5 °C |
| 5 | 120040105000061 | 89,0 | 43,8 °C |

Os top-3 são os mesmos entre as versões conservadora e ampla, e **os mesmos top-2 que apareciam em 2025**, com LST +3 °C maior — sinal de que o ranking identifica problemas estruturais, não ruído de ano.

## Comparação com rodada 2025 (mesma AOI, antes da expansão)

| Métrica | 2025 | 2026 | Δ |
|---|---|---|---|
| LST média cidade | 33,45 °C | 35,56 °C ¹ | **+2,1 °C** |
| LST p75 | 35,29 °C | 37,42 °C ¹ | **+2,1 °C** |
| Top-1 setor (120040105000314) | 42,56 °C | 45,84 °C | **+3,3 °C** |
| Escolas em zona quente | 123/254 | 135/254 | +12 |

¹ Valores da rodada 2026 com AOI antiga. Com AOI expandida (atual), a média cai para 34,83 °C porque entra mais área verde periférica no cálculo.

## Observações para comunicação

1. **A cidade está ~2 °C mais quente** na seca de 2026 vs. 2025. Compatível com o padrão regional de secas severas na Amazônia. Antes de divulgar como "aquecimento", cruzar com focos de calor do INPE para separar efeito climático de queimadas.
2. **O Top-3 é estável** entre anos e entre versões (conservador vs ampla). São problemas reais e persistentes do centro urbano denso.
3. **A APA Lago do Amapá e setores rurais** aparecem com prioridade baixa (correto — já têm mata).
4. **1.572 → 2.038 ha de perda** entre as rodadas (AOI pequena vs AOI nova) é efeito de expansão da área analisada, não aumento real.
5. **56–70% dos equipamentos públicos de educação e saúde** estão em zona quente. Candidato forte a lead do material de comunicação.

## Arquivos desta rodada

Em `/home/marcos/workspace/calor-verde-rb/data/out/`:

- `unidades_prioridade_conservador.geojson` + `ranking_conservador.csv` + `resumo_conservador.json`
- `unidades_prioridade_amplo.geojson` + `ranking_amplo.csv` + `resumo_amplo.json`
- `pois_calor.geojson` — igual nas duas versões
- `viewer.html` — visualizador local
