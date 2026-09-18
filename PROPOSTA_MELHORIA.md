# Proposta de melhoria da Educação Básica

Trabalho de Sistematização, Ciência de Dados I. Fonte: Censo Escolar 2022 (INEP), escolas em atividade.

## Problema identificado

O censo registra matrícula de educação especial em escolas que não declaram nenhum recurso de acessibilidade. A criança com deficiência está na lista. O prédio não a recebe. Isso contraria a LDB (Lei 9.394/96), a Lei Brasileira de Inclusão e o ODS 4 (educação inclusiva, equitativa e de qualidade).

## Evidências encontradas nos dados

Indicador EISA (inclusão sem acessibilidade): escola ativa, com `qt_mat_esp > 0`, e nenhum de rampa, corrimão, elevador, piso tátil, vão livre, banheiro PNE, dependências PNE ou sala de AEE.

- 25.911 escolas nessa condição
- 153.726 matrículas de educação especial nessas escolas
- São Paulo: cerca de 21% das escolas ativas em EISA; 4,99 PCD sem acessibilidade a cada mil matrículas
- Distrito Federal: 1,6% das escolas; 0,53 a cada mil
- Comparar volume absoluto esconde o DF e infla SP e MG só pelo tamanho. A taxa é o recorte justo entre UFs.

Houve ainda 12.604 questionários em que a escola marcou "acessibilidade inexistente" e ao mesmo tempo declarou rampa ou banheiro PNE. O dado de inclusão no prédio precisa de auditoria, não só de obra.

Infraestrutura digital (aba 4), usada como evidência da mesma proposta:

- 22.500 escolas ativas com aluno e sem nenhuma internet (deserto digital)
- Norte: 43,4% das escolas nessa condição; Sul: 1,7%
- Rural: 36,1%; urbana: 2,6%
- Interseção com EISA: 4.891 escolas (cerca de 19% das EISA) e 12.644 matrículas PCD sem acessibilidade e sem rede
- 85,4% das escolas declaram alguma internet; só 73,9% têm banda larga. "Ter sinal" não é condição de aula nem de AEE digital.

## Diagnóstico

A gestão conta "inclusão" como matrícula e "qualidade digital" como qualquer acesso. O estoque de prédios e de rede não acompanhou. Recurso diluído por volume favorece quem já é grande. A escola EISA que ainda é deserto digital é o pior caso: o aluno não entra no prédio e não alcança material acessível à distância. A rede municipal e o Norte rural concentram os dois passivos.

## Solução proposta

1. Publicar, no ciclo do Censo, um ranking de municípios e UFs por taxa EISA e por PCD sem acessibilidade a cada mil matrículas, não por contagem bruta.
2. Condicionar cota de infraestrutura (FUNDEB, emenda, PDDE, Educação Conectada) às escolas EISA, com prioridade máxima para as 4.891 que também são deserto digital: rampa, banheiro PNE, sala de AEE e banda larga no mesmo pacote.
3. Checklist único rede municipal mais estadual, com visita nas escolas da cauda alta da taxa, não nas que só têm mais aluno.
4. Corrigir o questionário do INEP nas flags contraditórias de acessibilidade, para o próximo censo não repetir o viés.

Ação de curto prazo (um ano letivo), sem esperar lei nova: o aluno já está matriculado.

## Benefícios esperados

- Cumprimento da LBI no prédio em que a criança já estuda
- Fila de obras guiada por taxa, o que reduz desigualdade entre UFs pequenas e grandes
- Melhor uso do recurso público (reforma pontual versus prédio novo)
- Dado de acessibilidade mais confiável no censo seguinte

## Relação com o ODS 4

- Inclusiva: o aluno com deficiência deixa de ser só linha no censo
- Equitativa: Norte e rural entram na fila na frente de quem já tem rampa e fibra
- Baseada em evidências: prioridade sai da interseção EISA e deserto digital
- Qualidade: acessibilidade física e conexão são condição de ensino, não item opcional
