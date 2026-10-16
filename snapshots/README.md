# snapshots/

Histórico oficial do pipeline, uma pasta por ano. **Imutável depois de commitado** —
é o que permite responder a perguntas como "o setor X esquentou nos últimos 3 anos?"
sem precisar rerodar nada.

Cada subdir carrega os 3 outputs da versão conservadora (`--min-cobertura 0.5`),
que é a que vai pro público:

- `resumo.json` — métricas da cidade + top-5
- `ranking.csv` — ranking completo com colunas (`rank`, `nome`, `bairro`,
  `indice_prioridade`, `lst_mean`, ...)
- `unidades_prioridade.geojson` — polígonos dos setores com todas as propriedades

A versão **ampla** (`--min-cobertura 0.2`) não entra no snapshot — é exploratória.

## Como criar um snapshot (ao estabilizar uma rodada)

```bash
# 1. Rode a versão conservadora e confira que a QA passa
.venv/bin/python analyze.py --unidades data/setores_rb.gpkg --min-cobertura 0.5

# 2. Compare com o último snapshot pra validar que a mudança é esperada
.venv/bin/python scripts/compare_runs.py snapshots/<ultimo> data/out

# 3. Se OK, copie e commite
year=2027
mkdir -p snapshots/$year
cp data/out/resumo.json data/out/ranking.csv data/out/unidades_prioridade.geojson \
   snapshots/$year/
git add snapshots/$year
git commit -m "snapshot: $year"
```

## Convenção de nome

- Ano simples (`2026`, `2027`): snapshot anual da estação seca
- `YYYY-MM` (`2026-09`): snapshot de rodada intermediária, por mês
- `YYYY-MM-DD` (`2026-10-16`): snapshot de rodada específica (ex. publicação pra terceiro)

A granularidade fica a critério da rodada; `compare_runs.py` aceita qualquer
subpasta de `snapshots/` como `dir_antigo`.
