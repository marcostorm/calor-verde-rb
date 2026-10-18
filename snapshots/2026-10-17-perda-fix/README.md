# Snapshot 2026-10-17 — correção de `perda_pct`

Rodada da versão conservadora (`--min-cobertura 0.5`) após corrigir o bug em
que `perda_pct` ficava 100% em todos os setores.

**Causa do bug:** o GeoTIFF `data/perda_2019_2026.tif` foi escrito pelo
`extract_gee.py` com `nodata=0` nos metadados, mas 0 é um valor legítimo
("pixel avaliado que não perdeu vegetação"). O `analyze.py` lia o raster via
`read_raster()` genérico, que respeita `src.nodata` — descartando todos os
zeros. Sobravam só os 1s, dando `perda_sum == perda_count` e portanto
`perda_pct = 100%`.

**Correção:** nova função `read_loss_raster()` que ignora `src.nodata` do
TIF e trata apenas 255 (unmask do GEE) como nodata. O TIF em si não foi
regenerado; o fix fica no `analyze.py`.

**Impacto:**
- `perda_pct` agora varia 0 a 19% (média 2,75%).
- `perda_ha` e `perda_total_ha` continuam iguais (não dependiam do bug).
- `indice_prioridade` reorganiza o ranking porque o termo da perda (20% do
  índice) agora contribui de verdade; antes era constante após o minmax.
  Top-5 muda: Floresta 037 sai; João Eduardo I 099 entra. Notas caem porque
  o bônus constante de +20 pontos some.

Comparação com o snapshot anterior (`snapshots/2026/`):

```bash
.venv/bin/python scripts/compare_runs.py snapshots/2026 snapshots/2026-10-17-perda-fix
```
