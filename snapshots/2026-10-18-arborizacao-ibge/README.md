# Snapshot 2026-10-18 — Fase 7.2 arborização IBGE

Primeira rodada com o termo `falta_verde` do índice de prioridade incorporando a
% de arborização em logradouros do Censo 2022 (IBGE), além do NDVI do Sentinel-2.

## Fonte

- `data/arborizacao_rb.csv` — derivado do IBGE 2022, Pesquisa Urbanística do Entorno dos Domicílios
- Variável: `100 - v05200_v05230_perc` (% moradores em face com pelo menos 1 árvore)
- 582 setores de 669 cobertos (87%). Setores rurais sem domicílios ocupados ficam sem valor.
- Documentação detalhada: `data/arborizacao_rb.README.md`

## Fórmula do índice (atualizada)

```
indice = 0,5 × calor + 0,3 × falta_verde + 0,2 × perda
onde:
  falta_verde = média de (1 - minmax(NDVI))  e  (1 - minmax(pct_arborizacao))
```

Setores sem `pct_arborizacao` mantêm `falta_verde` só com NDVI.

## Comando usado

```bash
.venv/bin/python analyze.py --unidades data/setores_rb.gpkg \
  --min-cobertura 0.5 --arborizacao data/arborizacao_rb.csv
```

## Impacto no ranking

Top-5 reorganizou. Vila da Amizade segue #1, mas Habitar Brasil entrou (bairro
de expansão com baixa arborização nas vias). Aeroporto Velho ganhou peso.

| # | Antes (só NDVI) | Agora (NDVI + IBGE) |
|---|---|---|
| 1 | Vila da Amizade (79,66) | Vila da Amizade (74,85) |
| 2 | João Eduardo I 099 (77,55) | **Habitar Brasil 424 (69,97)** novo |
| 3 | João Eduardo I 098 (75,46) | Aeroporto Velho 062 (68,65) |
| 4 | João Eduardo I 655 (71,21) | João Eduardo I 099 (68,53) |
| 5 | Aeroporto Velho 062 (70,00) | Aeroporto Velho 061 (67,57) |

Notas máximas caem ~5 pontos porque `falta_verde` agora é média de dois termos
em vez de só NDVI — valor extremo em um termo é suavizado pelo outro.

## Compare com snapshot anterior

```bash
.venv/bin/python scripts/compare_runs.py snapshots/2026-10-17-perda-fix snapshots/2026-10-18-arborizacao-ibge
```
