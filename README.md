# Calor & Verde Rio Branco (MVP, pipeline de dados)

Cruza temperatura de superfície, perda de vegetação e arborização do IBGE por bairro/setor
censitário e gera um ranking de **prioridade de plantio**.

**Visualizador público:** <https://marcostorm.github.io/calor-verde-rb/>
(publicado via GitHub Pages a cada push na `main` que altere `data/out/`; workflow em
`.github/workflows/pages.yml`).

## Instalação
```bash
pip install -r requirements.txt
earthengine authenticate
export GEE_PROJECT=seu-projeto-gcp   # projeto com Earth Engine API ativada (grátis p/ uso não comercial)
```

## 1. Extrair camadas de satélite
```bash
python extract_gee.py           # baixa GeoTIFFs para data/
python extract_gee.py --drive   # se a área for grande e o download direto falhar (limite ~50 MB)
```
Gera `lst_2025.tif` (°C, 30 m), `ndvi_2019.tif`, `ndvi_2025.tif`, `perda_2019_2025.tif` (10 m).
Nodata: `-9999` (float) e `255` (máscara de perda).

## 2. Unidades de análise
Baixe a **malha de setores censitários 2022** do Acre no site do IBGE (Geociências → Malhas
territoriais) e filtre Rio Branco (`CD_MUN = 1200401`). Salve como `data/setores_rb.gpkg`.

Opcional: CSV de arborização do Censo 2022 (tabela "Características urbanísticas do entorno
dos domicílios", via SIDRA) com colunas `nome` e `pct_arborizacao`.

## 3. Rodar a análise
```bash
# por setor censitário
python analyze.py --unidades data/setores_rb.gpkg

# agregando por bairro + dados de arborização
python analyze.py --unidades data/setores_rb.gpkg --dissolver NM_BAIRRO \
  --arborizacao data/arborizacao.csv --chave nome --col-arbor pct_arborizacao
```
Saídas em `data/out/`:
- `unidades_prioridade.geojson` — pronto para MapLibre/Leaflet
- `ranking.csv`
- `pois_calor.geojson` — escolas, saúde e pontos de ônibus (OpenStreetMap) com temperatura
- `resumo.json` — números para a home do site

## Índice de prioridade (0–100)
`0,5 × calor + 0,3 × falta de verde + 0,2 × perda recente` (cada termo normalizado min–max
entre as unidades). Pesos em `config.py`. Unidades com menos de 50% de pixels válidos de calor
ficam fora do ranking (`--min-cobertura`).

## Testar sem Earth Engine
```bash
python make_fake_data.py
python analyze.py --unidades data/bairros_fake.geojson --dissolver NM_BAIRRO --sem-pois
```

## Limitações (deixe claro no site)
- Landsat mede **temperatura da superfície**, não do ar; valores ao meio-dia (~10h30 local).
- 10 m não capta toda árvore isolada de calçada; o dado do IBGE complementa isso.
- NDVI cai também por seca/queimada, não só por corte. Valide pontos de perda com imagem de alta resolução.
- POIs dependem da completude do OpenStreetMap em Rio Branco.

## Licenciamento

Este projeto é publicado sob **[licença proprietária](LICENSE)** com direitos reservados. Resumo:

**Permitido sem autorização** (com atribuição):
- Estudo pessoal, pesquisa acadêmica, uso educacional, jornalismo
- Rodar o pipeline localmente para esses fins
- Citar trechos (até 15%) em trabalhos acadêmicos, reportagens e artigos

**Proibido sem licença escrita e paga do autor:**
- Qualquer uso comercial (venda, consultoria, prestação de serviço, SaaS, implantação em cliente, concorrência pública)
- Redistribuição sob outra licença
- Obra derivada publicada ou distribuída

**Dados-fonte** (Landsat, Sentinel-2, IBGE, INPE, OSM) seguem as licenças originais de seus provedores; ver `CITATION.md`.

**Para licença comercial**: abra uma issue no repositório ou entre em contato pelo canal público listado no perfil do autor. Termos (valor, escopo, duração) são negociados caso a caso.

Autor: **Marcos Henrique Melo de Araújo** · Rio Branco, Acre · Alias de código: `marcostorm`.
