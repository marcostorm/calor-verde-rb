# Snapshot 2025 — rodada retroativa (Fase 5.3)

Primeira rodada retroativa pra fechar o primeiro Δ anual real. Foi possível porque os rasters de 2025 já estavam em `data/` (lst_2025.tif, ndvi_2025.tif, perda_2019_2025.tif) de uma extração GEE anterior.

## Rodada

```bash
CALOR_VERDE_YEAR_NOW=2025 python analyze.py \
  --unidades data/setores_rb.gpkg \
  --min-cobertura 0.5 \
  --arborizacao data/arborizacao_rb.csv \
  --sem-pois
```

**Observação**: `--sem-pois` nessa rodada porque POIs são extraídos ao vivo do OSM e refletem o estado atual, não o estado de 2025. Pra análise temporal de setores, LST/NDVI/perda são o que importa.

## Parâmetros

- `YEAR_NOW`: **2025** (via env var `CALOR_VERDE_YEAR_NOW`)
- `YEAR_BASE`: 2019 (continua base S2 L2A)
- `--min-cobertura 0.5`: versão conservadora
- Interpolação consciente de SITUACAO (default desde Fase 3.1)

## Top 5 (versão conservadora, 2025)

| rank | setor | bairro | prioridade | LST °C |
|---:|---:|---|---:|---:|
| 1 | ? | Jardim Manoel Julião | 67,91 | 37,43 |
| 2 | ? | LBA Vila Betel II | 67,13 | 40,67 |
| 3 | ? | Aeroporto Velho | 65,89 | 40,66 |

(top 1 e 2 omitidos — ver ranking.csv)

## Comparação com 2026

Ver `data/out/trends/setor_lst.csv` (gerado por `scripts/trends.py`) pra Δ anual por setor.

**Panorama imediato**: 2026 parece mais quente que 2025. Top-5 de 2026 (Vila da Amizade 45,8°C, Habitar Brasil 43,7°C, Aeroporto Velho 44,4°C) tem LST 3-5°C acima do que o top-5 de 2025 (37-41°C). Setores também mudaram de identidade.

Confirmar com trends.py antes de narrar.

## Infra adicionada

- `config.py`: `YEAR_NOW` e `YEAR_BASE` passam a ler env vars `CALOR_VERDE_YEAR_NOW` / `CALOR_VERDE_YEAR_BASE` (default 2026 / 2019). Rodadas de ano específico são `CALOR_VERDE_YEAR_NOW=YYYY python analyze.py ...`.
- `analyze.py`: `find("lst_*.tif")` virou `find(f"lst_{C.YEAR_NOW}.tif")` (idem perda) — era um bug latente que sempre pegaria o último TIF ordenado alfabeticamente. Agora é determinístico por ano.
