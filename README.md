# Sistematização: Censo Escolar 2022 e ODS 4

Trabalho de Ciência de Dados I (CEUB). Painel OLAP da Educação Básica brasileira, com o indicador extra EISA (inclusão sem acessibilidade).

## O que este repositório contém

- Scripts de ETL e de montagem do painel (`etl/`)
- Relatório de pré-processamento, roteiro do vídeo e proposta de melhoria
- Resumos agregados de qualidade do ETL (não são microdados)
- Tema Catppuccin Macchiato usado no Apache Superset
- Enunciado da atividade em `docs/SISTEMATIZACAO.pdf`

## O que não está neste repositório

- Código-fonte do Apache Superset
- Microdados do Censo Escolar (arquivo grande; baixe na fonte oficial)
- Banco PostgreSQL e o painel já publicado (rodam localmente)

## Fontes e ferramentas usadas

### Dados

- [Microdados do Censo Escolar da Educação Básica 2022 (INEP)](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-escolar)
- Zip oficial: [microdados_censo_escolar_2022.zip](https://download.inep.gov.br/dados_abertos/microdados_censo_escolar_2022.zip)
- Arquivo usado: `microdados_ed_basica_2022.csv` (224.649 escolas, 385 variáveis)
- [Municípios brasileiros com latitude e longitude](https://github.com/kelvins/Municipios-Brasileiros)

### Software

- [Apache Superset](https://github.com/apache/superset) 6.1.0-dev (painel OLAP)
- [Documentação do Superset](https://superset.apache.org/)
- [Theming no Superset](https://superset.apache.org/docs/configuration/theming/)
- PostgreSQL 17 e Redis 7
- Python 3.11, pandas, SQLAlchemy e psycopg2
- [FastMCP](https://github.com/jlowin/fastmcp) (serviço MCP opcional do stack local)
- Podman (execução local dos containers)

### Tema

- Paleta [Catppuccin Macchiato](https://github.com/catppuccin/catppuccin), convertida para tokens Ant Design do Superset
- Arquivo no repositório: `themes/catppuccin-macchiato.json`
- [Editor de tema Ant Design](https://ant.design/theme-editor)

### Referências da proposta

- [ODS 4 da ONU](https://brasil.un.org/pt-br/sdgs/4): educação inclusiva, equitativa e de qualidade
- LDB (Lei 9.394/1996)
- Lei Brasileira de Inclusão (Lei 13.146/2015)

## Painel

Slug local: `ods4-educacao-qualidade`

URL local após subir o Superset: http://127.0.0.1:8088/superset/dashboard/ods4-educacao-qualidade/

Abas:

1. Visão geral
2. Geografia
3. Inclusão sem acessibilidade
4. Infraestrutura digital
5. Comparação justa entre UFs

Fórmula da taxa de PCD no painel (não é volume em milhares):

`(alunos PCD em escola sem acessibilidade ÷ matrículas totais) × 1.000`

Exemplo do município de São Paulo: 10.667 ÷ 2.693.361 × 1.000 = 3,96 (são 10.667 alunos).

Exemplo do estado de São Paulo: 50.086 ÷ 10.029.069 × 1.000 = 4,99 (são 50.086 alunos).

## Como reproduzir o ETL

1. Baixe o zip do INEP e extraia `microdados_ed_basica_2022.csv` em `data/raw/extracted/`.
2. Coloque o CSV de municípios (colunas `codigo_ibge`, latitude, longitude) em `data/raw/ibge/municipios.csv`.
3. Suba o PostgreSQL (no stack local do Superset a porta 5432 fica publicada).
4. Instale `requirements-etl.txt` e rode `python etl/load_censo.py`.
5. Com o Superset no ar: `python etl/register_superset_db.py`, depois `python etl/build_dashboard.py` e `python etl/update_rates.py`.

Caminhos e conexão padrão estão em `etl/load_censo.py` (`CENSO_ROOT` e `CENSO_DB_URL`).

## Entregas da disciplina

- `docs/RELATORIO_PREPROCESSAMENTO.md`
- `ROTEIRO_VIDEO.md` (fala de até 5 minutos)
- `PROPOSTA_MELHORIA.md`

## Indicador extra (EISA)

Escola ativa, com matrícula de educação especial (`qt_mat_esp > 0`) e nenhum recurso de acessibilidade: rampa, corrimão, elevador, piso tátil, vão livre, banheiro PNE, dependências PNE ou sala de AEE.

Brasil 2022, escolas ativas:

- 25.911 escolas EISA
- 153.726 matrículas de educação especial nessas escolas
- 4.891 escolas na interseção EISA e deserto digital (sem internet)
