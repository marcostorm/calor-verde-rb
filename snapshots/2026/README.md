# snapshot 2026

Rodada congelada em **2026-10-16** com o estado do pipeline no commit
que criou este snapshot (ver `git log -- snapshots/2026/`).

## Parâmetros

- `--min-cobertura 0.5` (versão conservadora)
- `--buffer-interp 3500` (interpolação por buffer de 3,5 km)
- `--min-pixels-interp 50`
- `--bairro-max-m 3000` (nearest-join OSM)

## Dados-fonte

- **LST:** Landsat 8/9 jun–set 2026
- **NDVI atual:** Sentinel-2 2026
- **NDVI base:** Sentinel-2 2019
- **Perda de vegetação:** diff NDVI 2019→2026 com threshold de C.config
- **Unidades:** setores censitários IBGE 2022 (669 em RB; `CD_MUN=1200401`)
- **Bairros:** OSM via Overpass em 2026-10-16 (134 pontos; ver `data/README.md`)

## Métricas da cidade

- `lst_media_cidade` = 34,83 °C
- `lst_p75_cidade` = 36,51 °C
- `perda_total_ha` = 2.037,7 ha

## Cobertura do ranking

- 629 de 669 setores (94,0%) com rank
- 40 setores cinzas (sem cobertura LST suficiente mesmo com interpolação)
- 175 setores interpolados por buffer

## Top-5

| rank | setor         | bairro          | índice | LST (°C) |
|-----:|---------------|-----------------|-------:|---------:|
| 1    | ...000000314  | Vila da Amizade | 96,57  | 45,84    |
| 2    | ...000000098  | João Eduardo I  | 94,77  | 45,41    |
| 3    | ...000000062  | Aeroporto Velho | 89,69  | 44,38    |
| 4    | ...000000655  | João Eduardo I  | 89,17  | 44,54    |
| 5    | ...000000061  | Aeroporto Velho | 89,04  | 43,76    |

Para o ranking completo veja `ranking.csv` nesta pasta.
