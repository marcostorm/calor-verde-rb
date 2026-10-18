# Snapshot 2026-10-18 — MODIS fallback (Fase 7.1)

Primeira rodada com MODIS LST como camada secundária pra recuperar setores que continuavam cinzas após a interpolação por buffer de 3,5 km.

## Rodada

```bash
GEE_PROJECT=meu-projeto-301501 python scripts/extract_modis.py
python analyze.py \
  --unidades data/setores_rb.gpkg \
  --min-cobertura 0.5 \
  --arborizacao data/arborizacao_rb.csv \
  --focos data/focos_rb.csv \
  --modis-fallback data/lst_modis_2026.tif \
  --sem-pois
```

## Resultado (versão conservadora)

Distribuição de `fonte_lst` após rodada:

| Fonte | Setores | % | Resolução efetiva |
|---|---:|---:|---|
| **Landsat 30 m** (dado próprio) | 454 | 68% | 30 m |
| **Buffer 3,5 km** (interpolado consciente urbano/rural) | 168 | 25% | ~3,5 km |
| **MODIS 1 km** (fallback) | **11** | 2% | 1 km |
| **Cinza remanescente** | 36 | 5% | — |

Antes da Fase 7.1: 622 setores com rank (454 + 168), 47 cinzas.
Depois: **633 setores com rank** (+11), 36 cinzas (−11).

Dos 47 cinzas remanescentes depois do buffer, 11 foram recuperados pelo MODIS. Os 36 restantes são setores onde nem MODIS tinha pixel válido na janela — provavelmente rurais extremos com nuvem persistente em todo o período.

## Composite MODIS usado

- Produto: `MODIS/061/MOD11A2` (Terra) + `MODIS/061/MYD11A2` (Aqua)
- Variável: `LST_Day_1km` (temperatura às ~10h30 Terra / ~13h30 Aqua local)
- Composites 8 dias na estação seca jun-set/2026: **32 cenas combinadas**
- Scale 0.02 pra Kelvin, convertido pra °C, filtrado por `QC_Day` bits 0-1 ≤ 1 (qualidade boa ou aceitável)
- Agregação final: mediana da estação

## Caveat importante (documentado no viewer e ranking)

**MODIS 1 km não é comparável 1:1 com Landsat 30 m.** Um pixel MODIS cobre vários setores urbanos ao mesmo tempo; o `lst_mean` do MODIS é a média da cena bruta na área, mais suave e mais fria que a média dos pixels Landsat (que capturam asfalto quente num pixel só).

Observado na rodada: LST MODIS médio 28,5°C vs Landsat médio 34,8°C na AOI. Diferença esperada por três motivos:
1. MOD/MYD11A2 é composite 8 dias (média suaviza extremos)
2. MODIS Day inclui todos os overpasses (não só o mais quente)
3. Pixel 1 km mistura asfalto + telhado + vegetação, suavizando

Portanto: **comparação direta de °C entre setor Landsat e setor MODIS tem viés sistemático de ~5-6°C**. No viewer, setores MODIS aparecem com borda tracejada roxa pra sinalizar. No popup e na expansão do ranking, o campo "Origem dos dados" nomeia explicitamente.

## Infra adicionada

- `scripts/extract_modis.py`: baixa MODIS LST do GEE via Terra+Aqua filtrado por QC. Padrão de uso igual ao `extract_gee.py`.
- `analyze.py`: nova flag `--modis-fallback <path>`. Após `interpolate_consciente_sit`, pros setores ainda cinzas (`~ok`), roda `zonal_stats` com `all_touched=True` no raster MODIS; pixels tocando o setor contribuem pro `lst_mean`. Nova coluna `fonte_lst` (`landsat` / `buffer` / `modis` / vazio).
- `viewer.html`: setores MODIS pintados com borda tracejada roxa (`#6b4e9e`), linha "temperatura via MODIS 1 km (fallback)" no popup, nova entrada no glossário.
- `ranking.html`: campo "Origem dos dados" na expansão passa a diferenciar Landsat / buffer / MODIS.
