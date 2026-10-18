# `arborizacao_rb.csv`

Percentual de arborização em logradouros por setor censitário de Rio Branco (AC), derivado da Pesquisa Urbanística do Entorno dos Domicílios do Censo Demográfico 2022 do IBGE.

## Colunas

- `nome` — código IBGE do setor censitário (15 dígitos, string). Chave de junção com `data/setores_rb.gpkg`.
- `pct_arborizacao` — percentual de **moradores em domicílios de face com arborização** (face com 1+ árvores). Faixa 0–100. Calculado como `100 - (% de moradores em face sem árvores)`.

## Origem

- Arquivo-fonte: `br_setores_entorno_cd2022(in).csv` do IBGE
- URL: https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Dados_percentuais_das_Caracteristicas_urbanisticas_do_entorno_dos_domicilios/
- Dicionário: `dicionario_entorno_pessoas.xlsx` (variáveis V05200–V05234)
- Pesquisa: Censo Demográfico 2022 — Resultados do Universo, Pesquisa Urbanística do Entorno dos Domicílios

## Derivação

A variável original disponibilizada é `v05200_v05230_perc` = % de moradores (sobre o total de moradores em domicílios com entorno aplicado) que vivem em face **sem árvores** (V05230 ÷ V05200 × 100).

Como o `analyze.py` espera uma métrica positiva (quanto maior, mais arborizada), convertemos:

```
pct_arborizacao = 100 - v05200_v05230_perc
```

Isso representa o % de moradores em domicílios com face que tem **pelo menos uma árvore** (categorias V05231 + V05232 + V05233 = 1-2 / 3-4 / 5+ árvores agregadas).

## Cobertura em Rio Branco

- Total de setores no pipeline (`data/setores_rb.gpkg`): 669
- Setores com dado de arborização: **582** (87%)
- Setores sem dado: 87 (rurais sem domicílios ocupados ou que não foram selecionados pra pesquisa do entorno)
- Faixa de valores: 0,0% (nenhum morador tem face com árvore) a 100,0% (todos têm)
- Média: 59,2% | Mediana: 60,8%

## Uso no pipeline

```bash
python analyze.py --unidades data/setores_rb.gpkg --arborizacao data/arborizacao_rb.csv
```

O `analyze.py` faz merge por `nome` (coluna configurável via `--chave`) e integra o valor no termo `falta_verde` do índice de prioridade:

```python
falta_verde = (falta_verde + (1 - minmax(pct_arborizacao))) / 2
```

Ou seja: o termo "falta de verde" vira a **média entre** a falta de clorofila via satélite (NDVI invertido) e a falta de arborização via IBGE. Peso efetivo de cada: 15% da nota final (metade dos 30% originais de `falta_verde`).

Setores sem dado de arborização mantêm o `falta_verde` original (só NDVI).

## Limitações assumidas

- A pesquisa IBGE é **por domicílio ocupado**, não cobre todas as áreas urbanizadas. Setor industrial, setor vazio ou setor rural sem domicílios ocupados fica sem valor.
- A métrica é **binária por face** (sem árvore vs. com pelo menos uma árvore), não captura densidade (uma face com 1 árvore conta igual a uma com 10).
- O numerador é **moradores**, não extensão linear de calçada: setor com domicílios adensados num trecho arborizado tem valor alto, mesmo que outras ruas do setor não tenham árvores.
- Dado é **de 2022**, pode já estar defasado em áreas de expansão urbana recente de Rio Branco.
