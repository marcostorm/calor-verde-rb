# Catálogo de espécies para arborização urbana em Rio Branco

**Versão 0.1 — rascunho (2026-10-18)**
**Status: idea pausada em 2026-10-18 — não validado para uso urbano.** Fica guardado como ponto de partida pra retomada futura; a lógica de integração no viewer existiu em `data/out/viewer.html` por algumas horas e foi removida.

## Por que a ideia foi pausada

Depois de ver o catálogo rodando no viewer local (com match por `area_ha` + `indice_prioridade`), a dúvida ficou óbvia: a **fonte principal do catálogo (Embrapa Acre — Guia Arbopasto Cap. 4) descreve espécies pra sistemas silvipastoris**, ou seja, arborização de pastagens em propriedade rural. Mesmo que vários atributos (porte, copa, raiz, crescimento) sejam transferíveis, **nenhuma dessas espécies foi avaliada especificamente pra uso em calçada urbana**. Sugerir "plante taperebá no setor Vila da Amizade" só com base nisso é meia-verdade.

As demais fontes também são frágeis pra esse fim:
- REVSBAU 2010: diz o que **já** está plantado em RB, não o que **deveria** estar.
- SEMEIA NT 005/2023: só diz quais são imunes ao corte, não quais plantar.
- Projeto estrada do aeroporto: 6 espécies escolhidas por projeto específico, sem metodologia pública.
- Embrapa Miranda & Valentim: dados de crescimento são da Estação Experimental (ambiente controlado), não de calçada.

## Retomar quando

Quando pelo menos **uma** destas condições for atendida:
1. A SEMA-AC publicar o Programa Estadual de Arborização Urbana (hoje "em elaboração") — serve como base oficial.
2. O PMAU-RB (PL do vereador Eber Machado) for aprovado e a SEMA-RB produzir sua lista oficial.
3. O manual "Programa de Arborização Urbana do Estado do Acre" (SEMA-AC, 2012) for recuperado em formato digital.
4. Um engenheiro florestal / agrônomo da UFAC / Embrapa Acre / SEMEIA revisar e assinar a lista.
5. PlaNAU (Portaria MMA 1.639/2026) publicar o documento técnico detalhado com recomendações nacionais.

## Objetivo

Primeira versão de um catálogo de espécies arbóreas candidatas à arborização urbana em Rio Branco (AC), cruzando as melhores fontes técnicas disponíveis para a Amazônia ocidental, o inventário acadêmico local e as normas municipais em vigor.

O catálogo é **insumo complementar** ao projeto Calor & Verde — pretende responder, em versões futuras, perguntas do tipo "qual espécie plantar neste setor, dado o contexto (porte da via, proximidade a escola, etc.) e quanto tempo até dar sombra útil".

## O que esse catálogo **não** é

- **Não é a lista oficial de Rio Branco**. O Plano Municipal de Arborização Urbana (PMAU-RB) ainda não existe — foi apenas proposto por projeto de lei do vereador Eber Machado em abril de 2025 e aguarda tramitação na Câmara. Quando aprovado, a SEMA-RB terá 12 meses para elaborar o plano, que deverá conter a lista oficial.
- **Não é a lista oficial do Estado do Acre**. A SEMA-AC informa estar "elaborando o Programa Estadual de Arborização Urbana" (fonte: sema.ac.gov.br/arborizacao, consultado em 2026-10-18). O documento histórico "Programa de Arborização Urbana do Estado do Acre" (SEMA, 2012, 51 p.) é citado em bibliografias de outras capitais mas não aparece em arquivo online — pode estar apenas em acervo físico.
- **Não substitui parecer técnico**. Qualquer plantio em espaço público em RB passa por licenciamento da SEMEIA (Secretaria Municipal de Meio Ambiente e Infraestrutura Agrária). Qualquer plantio em escala exige acompanhamento de engenheiro agrônomo ou florestal.
- **Não contém estimativa quantitativa de "retorno" por setor** (°C evitados, kg CO₂ sequestrados, L evapotranspirados). Isso depende de modelos como o i-Tree calibrados localmente — fica para versões futuras com validação acadêmica.

## Fontes consultadas (ordem de confiabilidade/pertinência)

Todas as URLs e autoria completa estão no bloco `fontes` do `catalogo.json`.

### Técnicas (dados primários da Amazônia ocidental)

1. **Embrapa Acre — Guia de espécies, Capítulo 4 do livro Arbopasto** (Andrade et al.). 51 espécies arbóreas da Amazônia ocidental caracterizadas por 15 atributos biológicos (velocidade de crescimento, porte, forma e densidade da copa, raízes superficiais, fixação de nitrogênio, qualidade do fuste, potencial tóxico de frutos, etc.). Dados coletados em experimentos no Acre e Rondônia. **Limitação importante**: o escopo original é arborização de pastagens (sistemas silvipastoris), não ruas urbanas. Vários atributos são diretamente transferíveis (porte, copa, raiz, crescimento); outros, não (ex: fixação de N interessa pouco no contexto urbano; interação com pastagem não se aplica).

2. **Miranda & Valentim — "Desempenho de doze espécies arbóreas nativas e introduzidas com potencial de uso múltiplo no estado do Acre"** (Embrapa Acre). Experimento de 4,5 anos na Estação Experimental da Embrapa Acre em Rio Branco. Fornece dados primários de **sobrevivência e taxas de crescimento (altura, diâmetro basal e diâmetro de copa) por ano**. É a única fonte com números medidos *em Rio Branco* no catálogo.

### Diagnóstico e normas locais

3. **REVSBAU 2010 — "Inventário e diagnóstico da arborização urbana viária de Rio Branco, AC"**. Levantamento acadêmico de 292 indivíduos em calçadas de RB, totalizando 39 espécies (11 nativas, 28 exóticas). Fonte do "estado atual" — mostra o que já está plantado e cita as espécies mais frequentes (falsa-murta, ligustro, oiti).

4. **SEMEIA Nota Técnica Nº 005/2023** (Prefeitura de Rio Branco). Declara **castanheira, mogno e seringueira** imunes ao corte na área urbana. Confere status implícito de "espécies estratégicas pro município".

5. **Projeto de arborização da estrada do Aeroporto de Rio Branco (2023)**. Reportagem do Portal Amazônia cita as espécies escolhidas pelo projeto público executado em RB: ipês, seringueira, açaí, castanheira, jacarandá, copaíba.

### Contexto regulatório

6. **PL do PMAU-RB (2025)** — Vereador Eber Machado. Proposta de criação do Plano Municipal. Diretriz textual: "priorizar o uso de espécies nativas da região amazônica, garantindo diversidade, segurança e adaptação climática" (Art. 3º, II). Essa diretriz orienta a priorização adotada neste catálogo.

7. **SEMA-AC — Programa Estadual de Arborização Urbana (em elaboração)**. Página oficial informa que o Governo do Estado está elaborando o programa, sem documento disponibilizado.

### Fontes **não** consultadas (lacunas conhecidas)

- O "Programa de Arborização Urbana do Estado do Acre" (SEMA, 2012) — não localizado em formato digital. Caminhos para obtê-lo: solicitar à Divisão de Educação Ambiental da SEMA-AC por e-mail, consultar o acervo físico da Embrapa Acre (CPAF-AC) ou buscar em biblioteca da UFAC.
- O PlaNAU (Plano Nacional de Arborização Urbana) — Portaria MMA 1.639 de março/2026 — gerará documento técnico detalhado no site do MMA. Quando publicado, incorporar as recomendações nacionais ao catálogo.
- Parecer local de engenheiro florestal ou agrônomo da UFAC / Embrapa Acre / SEMEIA. Prioridade antes de qualquer uso prático do catálogo.

## Metodologia de montagem desta v0.1

1. **Seleção das espécies**: 20 espécies no total, distribuídas em três grupos:
   - **12 nativas da Amazônia ocidental** com registro na Embrapa Arbopasto Cap. 4 ou em projeto público local.
   - **5 nativas de outras regiões do Brasil** amplamente usadas em arborização urbana em RB (ipê-roxo, oiti, jatobá, etc.).
   - **3 exóticas** com forte presença histórica em RB (REVSBAU 2010) — incluídas por transparência: falsa-murta e mangueira com ressalvas, fícus marcada explicitamente como `recomendado: false`.

2. **Atributos preenchidos**: foram preenchidos apenas atributos sustentados por pelo menos uma das fontes citadas. Faixas (ex: altura adulta, anos até porte útil) são aproximações da literatura, não medições. Quando a fonte era específica para RB (Miranda & Valentim), isso está marcado em `crescimento_medido_rb_m_ano`.

3. **Contextos adequados**: cruzamento de três fatores — porte adulto, tipo de raiz, características do fruto. Regras simples:
   - Porte muito grande ou raiz agressiva → `parque` apenas (ex: samaúma, fícus).
   - Porte grande sem raiz agressiva, sem fruto perigoso → `praca`, `canteiro_central`, `calcada_larga`.
   - Porte médio sem restrições → inclui `calcada_media`.
   - Porte pequeno sem restrições → inclui `calcada_estreita`.
   - Fruto pesado ou atrativo pra fauna → remover `calcada` dos contextos.

4. **Restrições e observações**: redigidas em linguagem direta, baseadas na literatura. Incluem riscos físicos (queda de ouriço/vagem, raízes), biológicos (vetores de doenças, broca-do-mogno), estéticos (frutos que mancham) e culturais (uso tradicional da espécie).

5. **Status em RB**: três marcadores:
   - `imune_ao_corte_semeia_nt005_2023`: castanheira, mogno, seringueira.
   - `documentada_em_uso_rb`: encontrada em inventários ou projetos públicos na cidade.
   - `incluida_em_obra_publica_rb`: nomeada em projeto público específico (ex: estrada do aeroporto).

## Formato dos dados (`catalogo.json`)

Cada espécie é um objeto com os seguintes campos. Nem todos aparecem em todas as entradas — campos nulos ou ausentes significam "não documentado nesta versão", não "não tem".

| Campo | Descrição |
|---|---|
| `id` | slug único (ex: `castanheira`) |
| `nome_popular` | lista de nomes populares aceitos |
| `nome_cientifico` | binomial em formato padrão (gênero capitalizado + epíteto) |
| `familia` | família botânica |
| `origem` | `nativa_amazonia_ocidental` \| `nativa_brasil` \| `exotica` |
| `porte` | `pequeno` (até 6 m) \| `medio` (6–12 m) \| `grande` (12–25 m) \| `muito_grande` (> 25 m) |
| `altura_adulta_m` | [min, max] em metros |
| `diametro_copa_m` | [min, max] em metros |
| `crescimento` | `lento` (< 0,8 m/ano) \| `medio` (0,8–1,5) \| `rapido` (> 1,5) |
| `crescimento_medido_rb_m_ano` | valor numérico específico, se vier do Miranda & Valentim |
| `anos_ate_porte_util_sombra` | [min, max] anos até ~50% do porte adulto (sombra útil) |
| `anos_ate_porte_adulto` | [min, max] anos até porte adulto |
| `raiz` | `pivotante` \| `superficial_leve` \| `superficial_agressiva` \| `mista` \| `fasciculada_leve` |
| `fruto` | descrição curta (ex: `drupa_media_comestivel`, `ouriço_pesado_perigoso`) |
| `flor_ornamental` | descrição se houver apelo estético |
| `fixacao_nitrogenio` | `true` se fixa N biológico (relevante para enriquecer solo) |
| `contextos_adequados` | lista — ver `legenda_campos.contextos_adequados` |
| `restricoes` | lista de restrições em linguagem direta |
| `status_rb` | objeto com marcadores de status municipal |
| `recomendado` | `false` quando a espécie está no catálogo apenas como alerta (ex: fícus) |
| `fontes` | lista de ids no bloco `fontes` do topo do JSON |
| `observacao` | texto livre com contexto histórico, cultural ou técnico |

Todos os ids de fonte usados em `fontes` correspondem a entradas no bloco `fontes` no topo do mesmo JSON — ao ler programaticamente, basta dereferenciar.

## Como pode ser usado no viewer (versões futuras)

Isso **não vai pro viewer agora**. Mas, pensando em integração futura:

1. **Painel "Espécies recomendadas pra este setor"** no popup. Lógica de match:
   - `SITUACAO = Urbana` + `area_ha < 15` → contexto urbano denso → preferir espécies com `calcada_media` ou `calcada_estreita` nos `contextos_adequados`.
   - `SITUACAO = Urbana` + `area_ha ≥ 15` → urbano com espaço → inclui porte grande se `praca`/`canteiro_central`.
   - `SITUACAO = Rural` → inclui porte muito grande e espécies de parque.
   - Proximidade a POI (`educacao`, `saude`) → excluir espécies com fruto pesado ou alérgeno.
   - Setor na zona de calor extremo → priorizar `crescimento = rapido` + `anos_ate_porte_util_sombra ≤ 7`.

2. **Página `especies.html`** com o catálogo completo tipo "biblioteca de referência" (modelo do `ranking.html`): filtro por origem, porte, contexto; ordenação por crescimento, tempo até sombra; detalhe inline com fonte.

3. **Marcador honesto** em todas as peças: "sugestões técnicas baseadas em [fontes]; antes de plantar, consultar SEMEIA e aguardar o PMAU-RB em elaboração".

## Próximos passos para evoluir pra v0.2

Em ordem de impacto:

1. **Validação com especialista local** — enviar o `catalogo.json` para um engenheiro florestal/agrônomo da UFAC, Embrapa Acre ou SEMEIA, pedindo revisão de omissões, erros e ajustes. Esse é o passo mais importante antes de usar publicamente.
2. **Buscar o PDF SEMA-AC 2012** (ligar/escrever à SEMA-AC) e integrar o que trouxer de diferente.
3. **Expandir pra 40–50 espécies** incluindo as demais entradas do Guia Embrapa que fizerem sentido urbano.
4. **Preencher atributos ausentes** (anos_ate_porte_adulto quando null, diâmetro de copa quando null) a partir da leitura completa das descrições do Guia Embrapa — cada espécie tem bloco próprio no PDF original.
5. **Integrar o PlaNAU** quando o documento técnico do MMA for publicado.
6. **Adicionar modelo de retorno simplificado**: por árvore adulta, estimativas de literatura de kg CO₂/ano, L evapotranspiração/dia, m² de sombra ao meio-dia. Multiplicar por nº sugerido no setor. Marcar explicitamente as incertezas em cada número.

## Fontes consultadas e não consultadas (resumo)

Ver bloco `fontes` dentro de `catalogo.json` com URLs completas.

- ✓ Embrapa Acre — Guia de espécies Arbopasto Cap. 4 (baixado e lido parcialmente)
- ✓ Embrapa Acre — Miranda & Valentim (baixado e lido)
- ✓ REVSBAU 2010 — Inventário de RB (referenciado em várias buscas; artigo acessado via ResearchGate)
- ✓ SEMEIA Nota Técnica 005/2023 (link oficial da Prefeitura de RB)
- ✓ Portal Amazônia — projeto estrada do aeroporto (2023)
- ✓ PL PMAU-RB — Vereador Eber Machado (texto integral do SAPL)
- ✓ Página oficial SEMA-AC — arborização urbana
- ✗ Programa de Arborização Urbana do Estado do Acre (SEMA, 2012) — citado em bibliografias, não acessado
- ✗ PlaNAU — Portaria MMA 1.639/2026 — ainda a publicar
- ✗ Parecer de engenheiro florestal / agrônomo local
