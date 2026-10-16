# data/

Camadas de entrada do pipeline.

## Arquivos versionados

### `setores_rb.gpkg`

Malha de setores censitários IBGE 2022 recortada para o município de Rio Branco
(CD_MUN = 1200401). Gerada a partir de `AC_setores_CD2022.gpkg` conforme
descrito em `operacao.md` → "Setor censitário de Rio Branco".

- CRS: EPSG:4674 (SIRGAS 2000)
- 669 feições (593 urbanos + 76 rurais)
- Campo `NM_BAIRRO` é **nulo em 100%** dos setores — IBGE 2022 não registra
  bairros oficiais em Rio Branco. Por isso usamos a camada auxiliar `bairros_rb.gpkg`.

### `bairros_rb.gpkg`

Camada auxiliar de bairros não-oficiais de Rio Branco, extraída do OpenStreetMap
via Overpass API. Gerada por `scripts/fetch_bairros_osm.py`.

- CRS: EPSG:4326 (WGS 84)
- Feições: 134 pontos (nenhum polígono — OSM não mapeia contornos de bairro em RB)
- Composição:
  - 126 `place=suburb`
  - 6  `place=neighbourhood`
  - 2  `place=quarter`
  - 0  `admin_level=9|10` (bairros formais ausentes no OSM para RB)
- Colunas: `osm_id`, `nome`, `tipo`, `admin_level`, `place`, `geometry`
- Primeiro fetch: 2026-10-16

**Como foi obtido:** query Overpass por bbox do município, filtrada depois
geometricamente para descartar pontos que caíam fora do contorno (buffer 500 m).
Fonte secundária considerada e descartada: cadastro oficial da SEMPLA
(prefeitura não publica em formato aberto).

**Limitações conhecidas:**

- **Pontos, não polígonos.** O spatial-join com setores (etapa 2.2 do roadmap)
  usa vizinho mais próximo. Setor rural distante ganha bairro do mais próximo —
  pode ser enganoso para setores rurais a >5 km do bairro mais próximo.
- **Nomes duplicados.** Quatro nomes aparecem em dois pontos distintos: `Centro`,
  `Sobral`, `Nova Esperança`, `Waldemar Maciel`. São bairros reais com mesmo nome
  em partes diferentes da cidade — ao propagar o nome para o setor, pode haver
  ambiguidade visual no viewer.
- **Cobertura periférica.** Mediana de distância do setor ao bairro mais próximo
  é 401 m (ótimo pra zona urbana), mas setores rurais chegam a 150 km.
- **Sem revisão oficial.** OSM é colaborativo; omissões e desvios de posição são
  esperados. Reexecute o fetcher periodicamente para capturar atualizações.

**Como atualizar:**

```bash
# Com venv do projeto ativo:
python scripts/fetch_bairros_osm.py
# Opcional: forçar um mirror específico
python scripts/fetch_bairros_osm.py --mirror https://overpass.kumi.systems/api/interpreter
```

O script tenta 4 mirrors Overpass em sequência. Se todos falharem (resposta 5xx),
tente novamente após 30 min; o principal (`overpass-api.de`) costuma estabilizar.

## Arquivos não versionados (gerados pelo pipeline)

- `lst_YYYY.tif`, `ndvi_YYYY.tif`, `perda_*.tif` — rasters Landsat/Sentinel
  baixados por `extract_gee.py`.
- `AC_setores_CD2022.gpkg` — fonte do IBGE (14 MB; baixado uma vez).
- `out/` — outputs do analyze.py (ranking, geojson, resumo, visualizador).
