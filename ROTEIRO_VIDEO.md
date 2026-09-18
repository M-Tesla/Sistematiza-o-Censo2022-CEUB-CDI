# Roteiro do vídeo (máximo 5 minutos)

Ciência de Dados I, Prof. Everson Reis. Sistematização: solução de análise para o ODS 4.

O enunciado pede quatro blocos, nesta ordem:

1. Contextualização do problema
2. Processo de tratamento dos dados
3. Demonstração do dashboard
4. Explicação da proposta de melhoria

Fala em ritmo de apresentação (cerca de 140 palavras por minuto). Texto falado em itálico. Entre colchetes: o que mostrar.

Antes de gravar: http://localhost:8088/superset/dashboard/ods4-educacao-qualidade/ , aba **1. Visão geral**, filtros limpos, zoom 90% ou 100%.

## 0:00 a 0:40. Contextualização

[Tela: título do dashboard]

*Olá. Fui contratado, neste exercício, como cientista de dados para apoiar gestores escolares e órgãos públicos com dados do INEP. O recorte é o ODS 4 da ONU: educação inclusiva, equitativa e de qualidade.*

*A Educação Básica brasileira é grande e desigual. O Censo Escolar descreve escolas, matrículas, docentes, inclusão e infraestrutura. O problema prático é este: o censo conta o aluno com deficiência na matrícula, mas o prédio muitas vezes não tem rampa, banheiro acessível nem sala de AEE. Inclusão no formulário não é inclusão no espaço. O painel transforma o Censo 2022 nessa evidência, para priorizar obra e fiscalização.*

## 0:40 a 1:35. Tratamento dos dados

[Tela: KPIs da aba 1]

*A base escolhida é a tabela de escolas do Censo Escolar 2022, não o microdado aluno a aluno. Ela já junta matrícula, docente, rede, município, educação especial e infraestrutura: 224.649 escolas, 385 variáveis. Mantive 66 campos mais as métricas derivadas.*

*Só escola em atividade entra no painel: 184.332 ativas. Paralisada ou extinta inflaria o denominador. Flag inválida virou nulo, não zero. Havia 12.604 escolas dizendo acessibilidade inexistente e ao mesmo tempo rampa ou banheiro PNE: prevaleceu o recurso presente. Nulo não foi imputado. Códigos de rede, localização e situação foram padronizados.*

*Resultado: 47,4 milhões de matrículas e 2,9 milhões de docentes. Mediana de 160 alunos por escola e 14,5 alunos por docente.*

## 1:35 a 3:20. Demonstração do dashboard

[Tela: aba 1. Filtros à esquerda, KPIs, donuts, barras empilhadas]

*O painel está no Apache Superset, com a lógica OLAP do enunciado: KPIs, cinco tipos de gráfico, filtros, mapa, matriz e navegação por abas. Os segmentadores cortam UF, região, rede e localização urbana ou rural.*

*A visão geral mostra o tamanho do sistema e onde está o aluno. A matrícula se concentra no Sudeste. Rede municipal e estadual carregam o público. Embaixo, cada barra é uma região com o nome inteiro; cada cor é uma UF. Sudeste é uma barra longa porque junta São Paulo, Minas e Rio. Nordeste se parte em mais estados.*

[Tela: aba 2. Mapa e barras de matrículas por escola]

*Geografia. Se eu somar matrícula bruta, São Paulo vira o país e o Distrito Federal some. Isso mede tamanho, não condição. Por isso o mapa compara matrículas por escola. O DF tem cerca de 461 alunos por escola; São Paulo, 329. Estado pequeno não é "1% de São Paulo": ele é 100% dele mesmo.*

[Tela: aba 3. KPIs 25.911 e 153.726, barras de percentual]

*Inclusão. Criei o EISA, inclusão sem acessibilidade, que não estava na lista sugerida. Escola ativa, com matrícula de educação especial, e nenhum recurso: rampa, corrimão, elevador, piso tátil, vão livre, banheiro PNE, dependência acessível ou sala de AEE.*

*Em 2022: 25.911 escolas e 153.726 matrículas nessa condição. As barras por UF são taxa, não volume. São Paulo perto de 21% das escolas em EISA; o DF, 1,6%.*

[Tela: aba 4. KPIs de internet, deserto digital, banda larga; barras por região]

*A aba 4 alimenta a proposta. 22,5 mil escolas com aluno e zero internet. Norte 43%, Sul menos de 2%. Rural 36%, urbano 2,6%. Equidade do ODS 4 é isso.*

*Cruze com o EISA: quase 4.900 escolas têm aluno de educação especial, zero acessibilidade e zero rede. 12,6 mil matrículas PCD nessa interseção. Sem rampa o aluno não entra; sem internet o AEE digital e o leitor de tela também não. A fila começa nessas escolas, não nas que já têm os dois.*

[Tela: aba 5, poucos segundos]

*A última aba trata cada UF como 100%: composição da rede e taxas, para não confundir porte com condição.*

## 3:20 a 4:50. Proposta de melhoria

[Tela: voltar à aba 3 e deixar os KPIs visíveis]

*Problema identificado: o aluno com deficiência já está matriculado em dezenas de milhares de escolas que não têm nenhum item de acessibilidade. Isso fere a LDB, a Lei Brasileira de Inclusão e a meta 4.5 do ODS 4.*

*Evidência: 25.911 EISA e quase 4.900 também sem internet. Diagnóstico: inclusão virando matrícula, qualidade digital virando "qualquer sinal".*

*Solução: ranking por taxa; FUNDEB e Educação Conectada no mesmo pacote para a interseção (rampa mais banda larga); checklist municipal; auditoria das 12 mil contradições do censo.*

*Benefício: o real cai onde a criança já está e hoje não entra nem pelo portão nem pela tela. ODS 4: inclusão, equidade Norte-Sul e rural-urbano, evidência.*

## 4:50 a 5:00. Encerramento

[Tela: aba 1]

*Censo oficial, tratamento documentado, painel com filtro, mapa e comparação justa. A recomendação: parar de tratar inclusão como matrícula e passar a tratar como prédio e como conexão. Obrigado.*

## Como gravar

Ferramentas do enunciado: OBS, Loom, Teams, Meet ou celular. Publicar no YouTube (não listado), Drive ou OneDrive, com acesso ao professor.

1. 1920x1080. Se o rótulo da região cortar, zoom 90%.
2. Não inventar número que não está na tela.
3. Na aba 3, abrir o tooltip de uma UF (percentual).
4. Se estourar 5 minutos, encurtar a aba 5. Não corte a proposta nem o EISA.
5. Título sugerido: `ODS 4 e Censo Escolar 2022: painel, EISA e proposta de melhoria`.
