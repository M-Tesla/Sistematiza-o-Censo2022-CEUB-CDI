# Relatório de pré-processamento: Censo Escolar 2022 (INEP)

Fonte oficial: [Microdados do Censo Escolar da Educação Básica 2022](https://download.inep.gov.br/dados_abertos/microdados_censo_escolar_2022.zip)  
Arquivo principal: `microdados_ed_basica_2022.csv` (224.649 escolas, 385 variáveis, `;`, Latin-1).  
Coordenadas municipais: [Municípios Brasileiros / IBGE](https://github.com/kelvins/Municipios-Brasileiros) (`codigo_ibge`, latitude, longitude).

## Base escolhida e por quê

Foi usada a base **escola** do Censo Escolar 2022, e não os microdados de aluno/docente linha a linha. Essa tabela já consolida, por escola:

- quantidade de escolas, matrículas e docentes
- etapa (infantil, fundamental, médio, EJA, educação especial)
- dependência administrativa e localização
- infraestrutura (água, energia, esgoto, biblioteca, laboratório)
- tecnologia (internet, banda larga, computadores)
- inclusão e acessibilidade

Isso cobre todos os indicadores pedidos na atividade sem os 10+ GB de matrícula individual, e mantém o recorte nacional exigido pelo ODS 4.

## Objetivos da análise

1. Mapear desigualdades de oferta e de condições de ensino na Educação Básica.
2. Medir inclusão (matrículas de educação especial) contra **condições reais** de acessibilidade.
3. Apoiar decisão de gestores com recortes por região, UF, município e rede.

## Decisões de tratamento

| Problema | Decisão | Justificativa |
|---|---|---|
| Escolas paralisadas/extintas (40.317) | Mantidas em `fato_escola` com `escola_ativa=0`; análises usam `v_escola_ativa` | Contar extinta inflaria o denominador de escolas e zera infraestrutura |
| Flags `IN_*` fora de {0,1} | Viram nulo | Código 9/branco = “não se aplica”; imputar 0 fabricaria “não tem internet” |
| Quantidades negativas | Removidas (nulo) | Inconsistência física |
| Banda larga = 1 e internet = 0 | Banda larga corrigida para 0 | Impossível ter banda larga sem internet |
| “Acessibilidade inexistente” + rampa/banheiro PNE etc. (12.604 casos) | Flag `inexistente` corrigida para 0 | Contradição do questionário; prevalece a presença do recurso |
| Nulos de internet (~2,3% nas ativas) e matrícula (~3,2%) | Conservados | Não imputar; KPIs usam soma/média ignorando nulos |
| Variáveis das 385 originais | 66 mantidas + derivadas | Só o necessário para ODS 4, inclusão, infra e mapa |
| Mapa | `CO_MUNICIPIO` ligado ao centróide IBGE | O CSV de 2022 não traz lat/lon da escola |
| Razão alunos/docente extrema (máx. 8.950) | Conservada, mas tratada como outlier na leitura | Provável subdeclaração de docentes; não apagar o registro |

Códigos padronizados:

- Dependência: 1 Federal, 2 Estadual, 3 Municipal, 4 Privada
- Localização: 1 Urbana, 2 Rural
- Situação: 1 Em atividade, 2 Paralisada, 3 Extinta

## Indicador inovador (não está no enunciado)

**Inclusão sem acessibilidade (EISA)**  
Escola **ativa** com matrícula de educação especial (`qt_mat_esp > 0`) e **nenhum** recurso de acessibilidade (rampa, corrimão, elevador, piso tátil, vão livre, banheiro PNE, dependências PNE ou sala de atendimento especial).

Métrica irmã: `qt_mat_esp_sem_acessibilidade` = número de matrículas PCD nessa condição.

Por que isso resolve um problema real: dashboards clássicos mostram “% de escolas com rampa” e “matrículas de educação especial” em gráficos separados. A interseção é o que a LBI e o ODS 4.5 pedem: criança com deficiência **já matriculada** em prédio que não a recebe com dignidade. No Brasil, em 2022:

- 25.911 escolas nessa situação
- 153.726 matrículas de educação especial em escolas sem acessibilidade
- SP, BA, RS, MG e RJ concentram o volume absoluto; PA e MA têm taxa alta

Também foi criado `flag_deserto_digital`: escola ativa com matrícula e sem internet (nem de aprendizagem).

## Tabelas no PostgreSQL (`censo_escolar`)

- `fato_escola`: 224.649 linhas (grão: escola)
- `v_escola_ativa`: somente em funcionamento (184.332)
- `agg_municipio`: 5.570 municípios, com lat/lon para mapa
- `agg_uf`: 27 UFs
- `agg_dependencia`: Federal/Estadual/Municipal/Privada
- `qualidade_etl`: contagens do processo

## Estatísticas descritivas (escolas ativas)

- Matrículas na educação básica: **47.382.074**
- Docentes: **2.924.306**
- Mediana de matrículas por escola: 160
- Mediana de alunos por docente: 14,5
- Média do índice de infra básica (água + energia + esgoto): 0,94
- Média de prontidão digital (internet de aprendizagem + banda larga + lab. informática): 0,54

Neste repositório ficam só os resumos `data/processed/estatisticas_descritivas.csv`, `qualidade_etl.json` e `agg_dependencia.csv`. O parquet da fato_escola e os microdados do INEP não são versionados (arquivo grande); gere de novo com `etl/load_censo.py`.
