# Operação

Como instalar, autenticar, rodar o pipeline e usar o visualizador.

## Pré-requisitos

- Linux (testado em Ubuntu 24.04).
- Python 3.12 com `python3.12-venv` instalado.
- Conta Google com projeto GCP e Earth Engine API ativada (gratuito para uso não-comercial): https://console.cloud.google.com

## Instalação (uma vez)

```bash
cd /home/marcos/workspace/calor-verde-rb

# venv (se ainda não existir)
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

# autenticação do Earth Engine (abre navegador)
.venv/bin/activate                 # ou: source .venv/bin/activate
earthengine authenticate

# variável de ambiente com o ID do projeto GCP
export GEE_PROJECT=seu-projeto-gcp
```

Para não exportar toda sessão, adicione ao `~/.bashrc` ou crie um `.envrc` com `direnv`.

## Setor censitário de Rio Branco

Já salvo em `data/setores_rb.gpkg`. Foi gerado assim (uma vez):

```bash
# baixar a malha do Acre
curl -L -o data/AC_setores_CD2022.gpkg \
  "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_de_setores_censitarios__divisoes_intramunicipais/censo_2022/setores/gpkg/UF/AC/AC_setores_CD2022.gpkg"

# filtrar Rio Branco (CD_MUN = 1200401)
.venv/bin/python -c "
import geopandas as gpd
g = gpd.read_file('data/AC_setores_CD2022.gpkg')
g[g['CD_MUN']=='1200401'].to_file('data/setores_rb.gpkg', driver='GPKG')
"
```

## Rodar o pipeline

Com `GEE_PROJECT` exportado e venv ativo:

```bash
# 1. baixar rasters (LST + NDVI atual + NDVI base + perda)
python extract_gee.py

# 1b. se o download direto falhar (área grande, limite ~50 MB), use Google Drive
python extract_gee.py --drive
```

Para alterar os anos, edite `config.py:YEAR_NOW` e `YEAR_BASE`.

```bash
# 2. análise + ranking (versão conservadora, min-cobertura 50%)
python analyze.py --unidades data/setores_rb.gpkg

# 2b. análise ampla (min-cobertura 20%)
python analyze.py --unidades data/setores_rb.gpkg --min-cobertura 0.2
```

## Salvar as duas versões lado a lado

```bash
python analyze.py --unidades data/setores_rb.gpkg --min-cobertura 0.5
cp data/out/unidades_prioridade.geojson data/out/unidades_prioridade_conservador.geojson
cp data/out/ranking.csv                 data/out/ranking_conservador.csv
cp data/out/resumo.json                 data/out/resumo_conservador.json

python analyze.py --unidades data/setores_rb.gpkg --min-cobertura 0.2
cp data/out/unidades_prioridade.geojson data/out/unidades_prioridade_amplo.geojson
cp data/out/ranking.csv                 data/out/ranking_amplo.csv
cp data/out/resumo.json                 data/out/resumo_amplo.json
```

## Abrir o visualizador

```bash
cd data/out
python3 -m http.server 8787
```

Depois abra `http://localhost:8787/viewer.html` no navegador. Para parar o server: `Ctrl+C` ou `pkill -f 'http.server 8787'`.

O visualizador carrega sozinho os três resumos, as duas versões do choropleth e os POIs. Switch de versão (rádio no topo do painel direito) recarrega sem precisar reload da página.

## Congelar uma rodada em `snapshots/`

Depois que a QA passa e `compare_runs.py` não mostra surpresas, promova a rodada
conservadora como marco histórico:

```bash
# 1. Compare com o último snapshot (ex. ano anterior)
.venv/bin/python scripts/compare_runs.py snapshots/2026 data/out

# 2. Se OK, copie os 3 arquivos oficiais pra pasta datada
year=2027
mkdir -p snapshots/$year
cp data/out/resumo.json data/out/ranking.csv data/out/unidades_prioridade.geojson \
   snapshots/$year/
# opcional: README com parâmetros, métricas e top-5 (ver snapshots/2026/README.md)

# 3. Commit
git add snapshots/$year
git commit -m "snapshot: $year"
```

A pasta `snapshots/` **nunca é sobrescrita**; cada ano/rodada entra num subdir
próprio. Granularidade a critério: `2026`, `2026-09`, `2026-10-16` são todos
válidos. `compare_runs.py` aceita qualquer um como `dir_antigo`.

## Atualizar série temporal (`scripts/trends.py`)

Depois de congelar um snapshot novo, atualize a série temporal:

```bash
.venv/bin/python scripts/trends.py
```

Varre `snapshots/YYYY/ranking.csv` e grava `data/out/trends/setor_lst.csv`
com uma coluna por ano, `delta_total`, `delta_anual_media` e `alerta` (setores
cuja variação total está acima de `média_cidade + 1σ_cidade` — "esquentando
acima do normal da cidade").

Com só 1 ano disponível, o script roda, escreve o CSV com só uma coluna e
avisa que tendências precisam de ≥2 anos.

Flags úteis:

- `--col lst_percentile_90` segue outra coluna (default: `lst_mean`)
- `--snapshots dir` e `--out dir` para rodar fora dos defaults

## Gerar relatório PDF (`scripts/relatorio.py`)

Depois de qualquer rodada do `analyze.py` (e opcionalmente do `trends.py`),
gera um PDF estático de 6-7 páginas com capa, sumário em 5 números, mapa de
prioridade, top-10 setores, mapa de variação ano a ano, metodologia e
limitações.

```bash
.venv/bin/python scripts/relatorio.py
```

Grava em `relatorios/calor-verde-rb_YYYY-MM-DD.pdf`. Lê automaticamente:
- `data/out/resumo_conservador.json` (ou `resumo.json`)
- `data/out/ranking_conservador.csv` (ou `ranking.csv`)
- `data/out/trends/setor_lst.csv` se existir (habilita manchete "+Δ°C"
  e segunda página de mapa divergente)

Flags úteis:

- `--saida path.pdf` sobrescreve o caminho default
- `--out-dir dir` lê outputs de outro diretório

Pré-requisito: `pip install -r requirements.txt` traz `weasyprint` e
`matplotlib`. Pango + Cairo (runtime, não dev) já vem com Ubuntu desktop
padrão; em servidor headless pode precisar `apt install libpango-1.0-0
libpangoft2-1.0-0`.

Rodar após congelar um snapshot anual pra ter um relatório datado por
versão: `cp relatorios/calor-verde-rb_YYYY-MM-DD.pdf snapshots/YYYY/`.

## Rodada mensal automática (`.github/workflows/mensal.yml`)

Workflow do GitHub Actions que roda o pipeline inteiro no dia 5 de cada
mês, 10h UTC (= 7h BRT), e commita snapshot + PDF novo. Também aceita
trigger manual (`workflow_dispatch`) com opção `skip_extract` pra reusar
TIFs commitados sem rebaixar do GEE.

**Setup único** (feito uma vez pela mantenedora do repo):

1. **Criar service account no Google Cloud Console**:
   - Projeto do GEE (ex.: `meu-projeto-301501`) → IAM & Admin → Service Accounts → Create
   - Nome sugerido: `calor-verde-ci@...iam.gserviceaccount.com`
   - Permissão mínima: Earth Engine Resource Admin (role `roles/earthengine.resourceAdmin`)
2. **Gerar chave JSON** da service account (botão "Keys" → "Add Key" → JSON) e baixar
3. **Registrar essa service account no Earth Engine**:
   - Acessar <https://console.cloud.google.com/earth-engine> e aprovar o email dela
   - OU rodar localmente: `earthengine --project=SEU-PROJETO authenticate --service_account_file=key.json`
4. **GitHub Secrets** (Settings → Secrets → Actions do repo):
   - `GEE_PROJECT` = id do projeto GCP (ex.: `meu-projeto-301501`)
   - `GEE_SERVICE_ACCOUNT_KEY_JSON` = conteúdo completo do JSON (abre o arquivo, cola o conteúdo inteiro no secret)

Depois disso, o workflow roda sozinho mensalmente. Pra testar antes do
primeiro cron, dispare manual: Actions tab → "Rodada mensal" → "Run workflow".

**Produto da rodada**:
- `snapshots/YYYY-MM/` com `ranking.csv`, `resumo.json`, `unidades_prioridade.geojson`
- `relatorios/calor-verde-rb_YYYY-MM-DD.pdf` (atualizado) + `calor-verde-rb_latest.pdf`
- Opcional: `data/out/trends/mensal/setor_lst.csv` com série mensal
- Commit automático pelo `github-actions[bot]`

**Falhas comuns**:
- Overpass fora do ar → `fetch_focos_inpe.py` falha mas `continue-on-error: true` no yml deixa a rodada seguir sem focos no mês
- Service account sem permissão GEE → mensagem "not registered to use Earth Engine" no extract. Fix: registrar no console.cloud.google.com/earth-engine
- Timeout de 60 min atingido → rodada pesada; aumentar `timeout-minutes` no yml

## Atualizar dependências

As versões em `requirements.txt` estão pinadas. Para atualizar com segurança:

```bash
# 1. Backup do snapshot atual (comparar depois)
cp -r data/out /tmp/out_before_upgrade

# 2. Testar nova versão em ambiente isolado
python3 -m venv .venv-test
.venv-test/bin/pip install -r requirements.txt
.venv-test/bin/pip install --upgrade geopandas  # ou lib específica
.venv-test/bin/pip freeze > requirements.new.txt

# 3. Rodar pipeline com venv de teste
.venv-test/bin/python analyze.py --unidades data/setores_rb.gpkg --min-cobertura 0.5 --sem-pois

# 4. Comparar saídas (QA deve passar, compare_runs sem surpresas)
.venv-test/bin/python scripts/compare_runs.py /tmp/out_before_upgrade data/out

# 5. Se OK, promover: substituir requirements.txt pela .new.txt e commitar
```

Nunca atualize libs em produção sem rodar o compare_runs — mudanças de rasterio ou rasterstats podem alterar sutilmente a leitura de nodata e distorcer resultados em silêncio.

## Comparar duas rodadas (`scripts/compare_runs.py`)

Diff estruturado entre dois diretórios de output.

```bash
python scripts/compare_runs.py <dir_antigo> <dir_novo>
# ex. comparar snapshot do mês passado com a rodada de hoje:
python scripts/compare_runs.py snapshots/2026-09 data/out
```

Imprime:
- Deltas em `lst_media_cidade`, `lst_p75_cidade`, `perda_total_ha` (valor absoluto e %)
- Top-5 que entrou/saiu/permaneceu
- 10 maiores saltos de índice pra cima e 10 pra baixo (filtra |Δ| ≥ 0,5)
- Quantos setores mudaram de bin de cor e as transições mais comuns
- Interpolação: quantos viraram ou deixaram de ser interpolados

Útil pra validar impacto de uma mudança de parâmetro (ex. buffer, min-cobertura) antes de aceitar o novo snapshot como oficial.

## Validação pós-pipeline (QA)

Ao fim de `analyze.py` roda um bloco `=== QA ===` com checks de sanidade:

**HARD (sai com exit 2 se falhar):**
- Pelo menos 50% dos setores têm rank
- `lst_media_cidade` entre 20 e 50 °C
- `lst_p75` ≥ `lst_media`
- Top-5 tem 5 entradas e nenhum campo nulo
- Arquivos de saída existem e não estão vazios

**SOFT (só alerta, continua):**
- Cobertura do mapa ≥ 85%
- `lst_media_cidade` na faixa típica 30–40 °C
- `perda_total_ha` entre 100 e 10.000 ha
- Interpolados ≤ 6× cinzas remanescentes

Se um HARD falhar, scripts que encadeiam o pipeline (ex. `scripts/pipeline-full.sh` planejado) devem parar e investigar. Rodar `storm-rag` ou publicar outputs com HARD-fail é bug no script chamador, não no analyze.

## Troubleshooting

### `pip install -r requirements.txt` falha com "externally-managed-environment"
Use o venv. Ubuntu 24.04 bloqueia instalação global via PEP 668.

### `ensurepip is not available` ao criar venv
`sudo apt install python3.12-venv`.

### `extract_gee.py` falha com HTTP 403 ou "User project not specified"
`GEE_PROJECT` não está exportado, ou o projeto não tem a Earth Engine API habilitada.

### `extract_gee.py` falha com "File size exceeded"
A área ficou grande demais para download direto. Use `python extract_gee.py --drive` e baixe os `.tif` da pasta `calor_verde_rb/` do seu Google Drive para `data/`.

### `analyze.py` falha com `HTTPError: 406` no Overpass
A API do OpenStreetMap exige `User-Agent`. Já corrigido em `analyze.py:92` — se refizer o repo do zero, aplicar o mesmo patch:

```python
headers = {"User-Agent": "calor-verde-rb/0.1 (contact: seu-email)"}
r = requests.post(OVERPASS, data={"data": q}, headers=headers, timeout=120)
```

### Muitos setores urbanos ficam cinza no mapa
Pode ser:
1. **AOI pequena demais** — ver `config.py:AOI_BBOX`. Deve cobrir o bbox dos setores urbanos com buffer. Para Rio Branco: `[-67.939, -10.117, -67.652, -9.886]`.
2. **Nuvem persistente** na estação seca — baixe `--min-cobertura` para 0,2, amplie `DRY_MONTHS`, ou aumente `--buffer-interp` (ex. `--buffer-interp 1000`) para a interpolação alcançar vizinhos mais distantes.
3. **Interpolação desativada** — a interpolação por buffer é default-ON; só fica fora se você passar `--sem-interpolar`.

### Dissolve por `NM_BAIRRO` retorna 0 unidades
Rio Branco **não tem** bairros oficializados no IBGE 2022 (campo `NM_BAIRRO` é nulo em 100% dos setores). Use ranking por setor (sem `--dissolver`), ou importe uma camada de bairros da Prefeitura/OSM e faça spatial-join antes.

### Visualizador abre em branco / não mostra o choropleth
Abra DevTools (F12) → Console. Verifique se `fetch` dos geojsons retornou 200. Se abrir o `viewer.html` direto como `file://`, o fetch é bloqueado — tem que servir via `http.server`.
