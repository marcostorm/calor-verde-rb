# Snapshot 2026-10-18 — Focos INPE no viewer (Fase 7.3)

Primeira rodada com a camada de focos de queimada do INPE integrada ao viewer e ao ranking.

## Rodada

```bash
python scripts/fetch_focos_inpe.py --inicio 2026-06 --fim 2026-09
python analyze.py \
  --unidades data/setores_rb.gpkg \
  --min-cobertura 0.5 \
  --arborizacao data/arborizacao_rb.csv \
  --focos data/focos_rb.csv
```

- Satélite: AQUA_M-T (referência INPE desde 2002)
- Janela: jun–set/2026 (estação seca)
- Área: Rio Branco (clip via union_all dos setores)

## Totais

- 119 focos AQUA_M-T em Rio Branco entre jun-set/2026
- Distribuição por mês: jun=parte dos 20, jul=parte dos 56, ago=parte dos 487, set=parte dos 877 (totais no estado inteiro antes do clip)
- 20 setores com ≥1 foco

## Observação importante

Dos 20 setores com focos, só **4** entram no ranking confiável (cobertura LST ≥ 50%):

| rank | setor | bairro | prioridade | focos |
|---:|---:|---|---:|---:|
| 501 | 612 | Belo Jardim I | 26,6 | 1 |
| 596 | 553 | — | 10,6 | 2 |
| 604 | 254 | — | 8,4 | 5 |
| 612 | 683 | — | 6,4 | 1 |

Os outros 16 setores com focos são **periféricos/rurais** sem rank (nuvem persistente ou poucos pixels urbanos). Isso bate com a geografia esperada: em Rio Branco, fogo = frontier agrícola/rural; calor urbano = asfalto adensado. O índice de prioridade mede o segundo; a camada de focos acrescenta o primeiro como contexto expositivo.

## Impacto no índice de prioridade

**Zero.** A coluna `focos_estacao` entra no CSV e no popup como camada de contexto, não como ingrediente da nota. Decisão deliberada: fogo em RB se concentra em zona rural onde o índice (focado em urbano quente+desarborizado) tem pouco a dizer. Cruzar os dois dá leitura narrativa, não aritmética.

## Arquivos deste snapshot

- `focos_rb.csv` — fonte canônica dos focos (119 linhas, 7 colunas)
- `focos.geojson` — pontos derivados pra consumo do viewer
- `ranking_conservador.csv` — ranking completo com nova coluna `focos_estacao`
- `unidades_prioridade_conservador.geojson` — geojson com `focos_estacao` por setor
- `resumo_conservador.json` — resumo da cidade (não mudou vs. snapshot anterior)

## Pra retomar

Pra atualizar focos: `python scripts/fetch_focos_inpe.py` (default jun-set/2026). Pra outro ano: `--inicio YYYY-06 --fim YYYY-09`. Pra re-rodar análise com focos: incluir `--focos data/focos_rb.csv` em qualquer invocação de `analyze.py`.
