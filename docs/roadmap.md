# Roadmap — Calor & Verde Rio Branco

Ordem sugerida de evolução do projeto. Cada fase é independente e entregável em sessões de 2 a 4 horas.

## Fase 0: Estado atual (concluído)

- Pipeline determinístico: `extract_gee.py` (Earth Engine) → `analyze.py` (zonal stats + índice) → `viewer.html` (Leaflet).
- Interpolação por buffer de 3,5 km recupera 94% dos setores que ficariam cinza por nuvem persistente.
- Duas versões salvas (conservador min=0,5 e ampla min=0,2) com interpolação ativa.
- Viewer com toggle entre choropleth por prioridade (0–100) e por temperatura (°C). Top-10 acompanha o modo.
- Documentação: README, metodologia, glossário, operação, decisões, resultados-2026.
- Robustez a Overpass: retry em 4 mirrors (principal, kumi, OSM-RU, OSM-FR).

---

## Fase 1: Hardening (prioridade máxima)

**Problema:** o pipeline pode completar com sucesso aparente mesmo se os números vierem errados (raster corrompido do GEE, schema do IBGE mudado, bug silencioso em refactor).

**Entregáveis:**

✅ 1.1 **Validação pós-pipeline** no final do `analyze.py` (feito em 2026-10-15, commit eeabb77). Bloco de assertions soft (alerta, não falha) e hard (falha com exit 2). Imediatamente detectou e levou a corrigir um bug real na interpolação de `perda_ha` (valores inflados por 14x+). Lista mínima:
   - `com_rank / total ≥ 0,85` → senão alerta
   - `len(cinzas rurais) / len(cinzas) ≥ 0,7` → senão algo mudou no AOI
   - `25 ≤ lst_media_cidade ≤ 45` → senão unidade/raster errado
   - `interpolados ≤ 3 × (cinzas restantes)` → razão razoável
   - Top-5 do run atual sobrepõe o do último snapshot em ≥ 3 setores → senão investigar
   - Arquivos de saída existem, geojson tem o nº esperado de features, resumo.json tem todos os campos

✅ 1.2 **Script `compare_runs.py`** (feito em 2026-10-15). Lê dois diretórios de output e imprime diff estruturado:
   - top-5 que entrou/saiu
   - maior salto de índice (positivo e negativo) com nome do setor
   - variação de `lst_media_cidade`, `lst_p75_cidade`, `perda_total_ha`
   - % de setores que mudaram de bin de cor
   - contagem de interpolados que viraram originais (ou vice-versa)
   - Filtra ruído: só reporta saltos com |Δ| ≥ 0,5

✅ 1.3 **Pin de versões** em `requirements.txt` (feito em 2026-10-15):
   - Todas as 7 libs com `==` (earthengine-api 1.7.46, geopandas 1.2.0, rasterio 1.5.2, rasterstats 0.21.0, numpy 2.5.3, pandas 3.0.6, requests 2.34.2)
   - operacao.md ganhou seção "Atualizar dependências" com fluxo seguro (venv teste → pipeline → compare_runs → promover)

**Esforço:** 1-2 sessões. **Dependência:** nenhuma.

---

## Fase 2: Nomes legíveis + deploy público

**Problema:** setores identificados só por código IBGE (`120040105000314`) e viewer só acessível localmente.

**Entregáveis:**

✅ 2.1 **Camada auxiliar de bairros não-oficiais** em `data/bairros_rb.gpkg` (feito em 2026-10-16, commit f6b819b). Fetcher em `scripts/fetch_bairros_osm.py` com retry em 4 mirrors Overpass; bbox do município extraído dinamicamente de `data/setores_rb.gpkg`. Resultado: 134 pontos (126 suburb + 6 neighbourhood + 2 quarter; nenhum admin_level=9|10 em RB). Nearest-join com setores cobre 100% dos 669 setores; mediana 401 m, zero setor urbano a >2 km. `data/README.md` documenta origem, método e 4 limitações conhecidas (pontos em vez de polígonos, 4 nomes duplicados, cobertura periférica em zona rural, dependência de atualização OSM).

✅ 2.2 **Spatial-join no `analyze.py`** (feito em 2026-10-16, commit 1f6db76). Como OSM mapeia bairros de RB como pontos (não polígonos), usamos `sjoin_nearest` em CRS métrico (SIRGAS 2000 / UTM 19S, EPSG:31979). Função `join_bairro_osm(gdf, path, max_m)` chamada logo após `load_units()`. Setor cujo centróide esteja a mais de `--bairro-max-m` (default 3000) metros do ponto mais próximo recebe `bairro=None` — comum em setor rural. Resultado: 573/669 setores (85,6%) com bairro atribuído, mediana 398 m. QA pós-pipeline passou sem regressão (lst_media_cidade e perda_total_ha idênticos ao estado pré-join). Flags: `--bairros-gpkg`, `--bairro-max-m`, `--sem-bairros`.

✅ 2.3 **Enriquecimento dos outputs** (feito em 2026-10-16, commit 916f11b). ranking.csv e geojson já ganharam `bairro` na Fase 2.2. Nesta etapa, atualizado o viewer: (a) popup do setor passa a mostrar "Setor 314 · Vila da Amizade"; (b) tabela Top-10 ganhou coluna "bairro" (com código do setor abreviado para 3 dígitos pra caber na sidebar); (c) glossário tem agora entrada "Bairro" explicando origem OSM, método nearest e limitação de pontos+repetições; (d) de brinde, corrigido texto de "buffer de 500 m" para "3,5 km" na entrada "Setor interpolado" (estava desatualizado desde a Fase 1).

✅ 2.4 **Deploy público do viewer** (feito em 2026-10-16, commit cea6686). Workflow `.github/workflows/pages.yml` empacota `data/out/` (copia pra `_site/`, usa `viewer.html` como `index.html`) e publica via `actions/deploy-pages@v4` a cada push em `main` que altere `data/out/**`. Trigger também aceita `workflow_dispatch`. URL: <https://marcostorm.github.io/calor-verde-rb/>. Repositório tornado público nesta etapa (plano Free não permite Pages em privado); documentado no README. Alternativas consideradas e descartadas no momento: Cloudflare Pages (ok mas adicionaria dep de serviço externo) e deploy no VPS Hostinger (adicionaria sobrecarga de ops sem ganho sobre GH Pages).

**Esforço:** 2-3 sessões. **Dependência:** Fase 1 recomendada antes (deploy multiplica consequência de bug).

---

## Fase 3: Qualidade de dados dos interpolados

**Problema:** interpolação atual com buffer de 3,5 km não distingue uso do solo. Setor urbano cercado por mata pode interpolar com pixels de mata (baixa LST, pouco representativa).

**Entregáveis:**

✅ 3.3 **Cross-validation da interpolação** (feito em 2026-10-16, commit b90995a). `scripts/qa_interpolacao.py` sorteia 10% (seed 42) dos setores com cobertura ≥ 0,5, guarda `lst_mean` como truth, roda `interpolate_by_buffer` fingindo que não têm dado e compara. Reporta MAE, bias, p50/p90 do erro absoluto, R² e breakdown por SITUACAO. Baseline antes da Fase 3.1: **MAE 2,55 °C, bias -1,74 °C, R² -0,03** — o interpolador era pior que a média em setores urbanos (sintoma do viés de contaminação por vegetação). Escreve `data/out/qa_interpolacao.json`, consumido pelo painel do viewer (Fase 3.2).

✅ 3.1 **Interpolação consciente de contexto** (feito em 2026-10-16, commit aa88271). `_mask_lst_by_situacao` rasteriza máscara urbano/rural na grade nativa do LST; `interpolate_consciente_sit` faz um passe por grupo de SITUACAO com LST restrito; `zonal` estendido pra aceitar `(array, affine)` além de path. Default do analyze passa a ser consciente; flag `--interpolacao-ingenua` volta pra versão da Fase 1. **Impacto medido (seed 42, N=45): MAE 2,55→2,18 °C (-14%), R² -0,03→0,21, MAE rural -39%.** Compare_runs com snapshot anterior: top-5 preservado, 10 setores urbanos subiram até +5,94 pts (eram subestimados por contaminação do buffer). Snapshot 2026 atualizado pra refletir a metodologia atual; versão ingênua preservada no git history. Pendente: NDVI e perda ainda não mascarados por contexto (iteração futura se o MAE residual importar).

✅ 3.2 **Dashboard de QA embutido no viewer** (feito em 2026-10-16, commit 67d3f60). Painel `<details>#qa-panel` com (a) métricas da cross-validation lidas de `qa_interpolacao.json`; (b) contagem de setores originais / interpolados / cinzas; (c) histograma SVG do LST (bins de 2 °C entre 26-50); (d) histograma de cobertura (0-100% em 10 bins); (e) toggle "mostrar só interpolados" filtrando o choropleth; (f) botão "imprimir / salvar PDF" com CSS `@media print` que estática o map+painel e esconde controles. Painel atualiza ao trocar de versão (conservador/amplo).

**Esforço:** 2-3 sessões. **Dependência:** Fases 1 e 2.

---

## Fase 4: Comunicação pública

**Problema:** viewer é bom pra uso interno mas não é um "produto" apresentável.

**Entregáveis:**

4.1 **Export PDF/PNG** a partir do viewer:
   - Botão "Baixar visão atual" que gera PNG da home com mapa + resumo + legenda
   - PDF de uma página com índice, top-10, metodologia resumida

4.2 **Página standalone "O método em uma página"** (`metodo.html`) acessível pelo viewer:
   - Reduz a metodologia pra visão de prefeito/jornalista (não de engenheiro)
   - Linka pros docs técnicos

4.3 **Formato citacional:**
   - Adicionar `CITATION.md` no repo com DOI (via Zenodo, gratuito) ou formato ABNT/APA
   - Facilita menção em relatórios de prefeitura ou MP

**Esforço:** 1-2 sessões. **Dependência:** Fase 2.

---

## Fase 5: Comparação longitudinal (ongoing anual)

**Problema:** a cada ano o `data/out/` sobrescreve o anterior. Impossível responder "setor X esquentou nos últimos 3 anos?" sem rodar manualmente.

**Entregáveis:**

✅ 5.1 **Estrutura `snapshots/{ano}/`** (feito em 2026-10-16, commit 4816a74). Snapshot inaugural em `snapshots/2026/` com os 3 arquivos oficiais da versão conservadora (resumo, ranking, geojson); `snapshots/README.md` documenta a convenção de nomes (ano / YYYY-MM / YYYY-MM-DD) e `snapshots/2026/README.md` registra parâmetros, dados-fonte, métricas da cidade e top-5. `operacao.md` ganhou seção "Congelar uma rodada em `snapshots/`" com o fluxo (compare_runs → cp → commit). A partir desta pasta é possível responder a perguntas longitudinais (ex.: setor X esquentou nos últimos 3 anos?) sem rerodar nada.

5.2 **`trends.py`:** série temporal por setor
   - Para cada setor, plotar LST ao longo dos anos disponíveis
   - CSV `trends/setor_lst.csv` com colunas por ano
   - Alertar setores com variação acima de 1 desvio padrão

5.3 **Viewer com toggle de ano:**
   - Novo radio "Ano: 2024 | 2025 | 2026" carrega snapshots específicos
   - Modo comparação "lado a lado" ou "diff com ano anterior"

**Esforço:** 1 sessão por ano (5.1 e 5.2), 2-3 sessões (5.3). **Dependência:** Fase 2 recomendada.

---

## Fase 6: Robustez técnica

**Problema:** zero teste automatizado. Mudança no `analyze.py` ou atualização de biblioteca pode quebrar silenciosamente.

**Entregáveis:**

✅ 6.1 **Fixture mínima + teste de integração** (feito em 2026-10-16, commit b681da8). `tests/conftest.py` gera em `tmp_path` 10 setores sintéticos (grade 5x2 em EPSG:31979) + rasters 50x50 (LST com gradiente oeste-leste 42→30 °C, NDVI base/now com perda localizada 0,4 num bloco central). `tests/test_integration.py` tem dois casos: (a) end-to-end roda `analyze.py` via subprocess com `--sem-pois --sem-bairros --sem-interpolar` e confere exit 0, existência dos 3 outputs (ranking, geojson, resumo), nº de linhas = 10, `indice_prioridade ∈ [0,100]`, `lst_media_cidade ∈ [25,45]`; (b) anti-regressão de `read_raster` dtype == float32 (fecha o loop com o fix OOM do commit ec5c364). `config.py` ganhou override via env (`CALOR_VERDE_DATA_DIR` / `CALOR_VERDE_OUT_DIR`) pra o teste isolar sem tocar em `data/`. Pytest 9.1.1 em `requirements-dev.txt`. Rodada medida: **1,53 s** pra 2 testes — bem dentro do limite de 5 s do roadmap. Viabiliza Fase 6.4 (CI).

6.2 **Logging estruturado:**
   - Trocar `print` por `logging` + handler JSON
   - Cada rodada escreve `logs/run-{timestamp}.json` com métricas (n unidades, n interpolados, tempo por etapa, versões de libs)
   - Útil pra debugar incidentes retroativos

6.3 **Idempotência:**
   - `analyze.py` escreve em arquivos temporários e renomeia atomicamente no final
   - Se falhar no meio, outputs anteriores ficam intactos (hoje ficam parciais e consistentes com um estado quebrado)

6.4 **GitHub Actions:**
   - Workflow que roda o teste de integração a cada PR
   - Workflow mensal que roda o pipeline completo com os rasters do mês e abre PR com os outputs atualizados

**Esforço:** 2-3 sessões. **Dependência:** nenhuma (pode rodar paralelo às outras).

---

## Fase 7: Fontes de dados complementares

**Problema:** 40 setores remanescentes com cinza real (sem pixels em nenhum raio); dependência total do Landsat (satélite óptico, bloqueado por nuvem).

**Entregáveis:**

7.1 **MODIS LST como camada secundária:**
   - Resolução 1 km (vs. 30 m do Landsat), revisita quase diária
   - Melhor pra preencher nuvem persistente, pior pra análise fina
   - Novo módulo `extract_modis.py` + fallback em `analyze.py` quando buffer Landsat insuficiente

7.2 **Arborização IBGE:** usar `--arborizacao` já previsto no analyze
   - Dataset: tabela IBGE por setor com % de arborização em logradouros
   - Melhora o termo `falta_verde` do índice

7.3 **Focos INPE (BDQueimadas):**
   - Classificar perdas: "verde que virou nada por queimada" vs. "verde que caiu por outra razão (seca, corte)"
   - Cruzar `perda_pct` com nº de focos registrados no setor no período

**Esforço:** 3-4 sessões por fonte. **Dependência:** Fases 1 e 2.

---

## Priorização sugerida

### Caminho recomendado (ordem)

1. **Fase 1** (hardening) — base pra tudo mais, impede regressões silenciosas
2. **Fase 2** (deploy + nomes) — multiplica alcance do projeto, torna demonstrável
3. **Fase 3** (qualidade de interpolação) — robustez metodológica, defensável tecnicamente
4. **Fase 5.1** (snapshot do 2026) — simples arquivamento, custa 10 min, permite trend futuro
5. **Fase 4** (comunicação) — se houver público-alvo definido (prefeitura, MP, jornalista)
6. **Fase 6** (testes) — quando o custo de uma regressão superar o custo de montar teste
7. **Fase 7** (MODIS/INPE) — só se os cinzas remanescentes incomodarem na prática

### Caminhos alternativos

- **"Quero publicar logo":** 1 → 2 → 4 → 5.1
- **"Quero cientificamente defensável":** 1 → 3 → 6 → 7
- **"Quero histórico multi-ano":** 1 → 5 → 2 → 3

### O que não entra no roadmap (por decisão)

- Reescrever o viewer em React/Vue: Leaflet puro resolve, acréscimo de complexidade sem ganho pro usuário
- Backend/API: hoje tudo é estático, serve melhor assim pra audiência pública
- Mobile app: viewer é responsivo via Leaflet, cobre o caso

---

## Como manter esse roadmap vivo

- Atualizar após cada fase entregue (marcar como ✅ no cabeçalho da seção)
- Reavaliar prioridades a cada 3 meses ou quando contexto mudar (ex. abertura de edital municipal)
- Novos itens entram na Fase 7+ e são repriorizados no próximo ciclo
