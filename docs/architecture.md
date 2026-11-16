# Arquitetura — Credit Risk Monitoring

## 1. Objetivo

Este documento registra as decisões arquiteturais do projeto Credit Risk Monitoring, desenvolvido para o Tech Challenge da Fase 4 da Pós-Tech FIAP em Machine Learning Engineering.

O projeto simula o monitoramento de um modelo de classificação de risco de crédito utilizado por uma fintech.

O foco principal não é desenvolver um modelo de crédito sofisticado, mas demonstrar a capacidade de validar dados, identificar alterações de distribuição, observar execuções e documentar aspectos de governança.

A arquitetura será implementada incrementalmente, respeitando os limites de cada bloco.

## 2. Princípios arquiteturais

As seguintes diretrizes orientam o desenvolvimento:

1. **Simplicidade:** priorizar uma solução acadêmica funcional, evitando complexidade sem benefício demonstrável.
2. **Separação de responsabilidades:** manter preparação, validação, inferência, drift e observabilidade como responsabilidades distintas.
3. **Validação antes da inferência:** impedir que lotes inválidos sejam processados pelo modelo.
4. **Reprodutibilidade:** permitir que os procedimentos sejam executados novamente de maneira controlada.
5. **Rastreabilidade:** relacionar os resultados de cada execução aos seus respectivos registros operacionais.
6. **Testabilidade:** implementar verificações automatizadas para comportamentos relevantes.
7. **Privacidade:** considerar minimização de dados, tratamento de informações pessoais e requisitos da LGPD durante o desenvolvimento.
8. **Implementação incremental:** não criar componentes dos próximos blocos antes de sua necessidade.

Esses princípios são diretrizes de projeto. Sua aplicação funcional será demonstrada ao longo dos próximos blocos.

## 3. Estado atual da implementação

O projeto é desenvolvido incrementalmente, com componentes
funcionais integrados à `main` após testes e revisão.

### Bloco 0 — Fundação e arquitetura

**Estado: concluído.**

Componentes implementados:

- Pacote Python com layout `src/`.
- Empacotamento com setuptools e `pyproject.toml`.
- Ambiente virtual `.venv`.
- Instalação editável.
- pytest e Ruff.
- Estrutura de documentação.
- Fluxo Git com branches locais.

### Bloco 1 — Dados e modelo baseline

**Estado: concluído.**

Componentes implementados:

- Inspeção do Home Credit Default Risk.
- Preparação determinística das features.
- Tratamento da sentinela `DAYS_EMPLOYED=365243`.
- Particionamento estratificado com seed 42.
- Verificação de integridade com manifesto e hashes.
- Pipeline Scikit-Learn com LogisticRegression.
- Seleção de threshold por F1 na validação.
- Avaliação independente no teste.
- Persistência do modelo e seus metadados.

O modelo utiliza 17 features preditivas.

Threshold oficial:

`0.1406724340221902`

Resultados de teste:

- ROC-AUC: 0.736332.
- Average Precision: 0.214999.
- Precision: 0.223766.
- Recall: 0.397959.
- F1: 0.286460.

A implementação foi concluída com 42 testes aprovados.

### Bloco 2 — Contratos e inferência bloqueante

**Estado: implementação funcional concluída.**

Componentes implementados:

- Contratos Pandera para entrada bruta e preparada.
- Regras rígidas de qualidade.
- Tratamento explícito de nulidades.
- Resultados estruturados de validação.
- Preparação de lotes sem TARGET.
- Reutilização da transformação de sentinela.
- Inferência com barreira bloqueante.
- Carregamento do baseline persistido.
- Interface operacional `scripts/score_batch.py`.
- Relatórios JSON de aprovação e rejeição.
- CSV opcional com probabilidades individuais.
- Testes unitários e de integração.

A barreira impede que lotes rejeitados cheguem
ao modelo.

A validação ocorre antes do carregamento do
artefato e antes de `predict_proba()`.

Os resultados são estruturados para permitir
instrumentação futura.

As implementações funcionais foram integradas
à `main` nos seguintes commits:

- Contratos Pandera: `e265a12`.
- Inferência bloqueante: `9141612`.

Após a integração funcional:

- 114 testes automatizados aprovados.
- Ruff lint e formatação aprovados.
- Dependências verificadas com pip check.
- Demonstrações de aprovação e rejeição executadas.
- Integridade dos dados preparados verificada.

A documentação do Bloco 2 foi consolidada
em `docs/quality-contracts.md` e integrada à `main`.

### Bloco 3 — Simulação e detecção de drift

**Estado: implementação funcional concluída e integrada à `main`.**

Componentes implementados:

- Simulação determinística de lotes de produção.
- Cenários `control`, `moderate` e `strong`.
- Reutilização do quality gate Pandera.
- Inferência com o baseline persistido.
- Detecção estatística com Evidently AI.
- Monitoramento de 16 features originais.
- Resultados estruturados por feature e por lote.
- Relatórios agregados JSON e HTML Evidently.
- CLI `scripts/monitor_drift.py`.
- Testes unitários e de integração.

A integração funcional foi concluída no
commit de merge `54581c2`.

Após a integração dos Blocos 0 a 3,
foram aprovados 211 testes automatizados.

A metodologia e os resultados estão
documentados em `docs/drift-monitoring.md`.

### Bloco 4 — Instrumentação e observabilidade

**Estado: concluído e integrado à `main`, incluindo a correção P0 das regras de alerta Prometheus.**

Componentes implementados:

- Registro estruturado de eventos de scoring e monitoramento, com persistência SQLite.
- Agregação de sete famílias métricas, expostas como gauges Prometheus.
- Exporter HTTP com Litestar/Uvicorn, endpoint `GET /metrics`.
- Docker Compose com exporter, Prometheus 3.16.0 e Grafana 12.2.0.
- Datasource e dashboard de oito painéis provisionados por arquivos.
- Testes de eventos, armazenamento, métricas, endpoint e contratos do dashboard.
- Três regras Prometheus para drift, falhas operacionais e violações de qualidade, testadas temporalmente e demonstradas em `firing` e `inactive`.

O merge funcional da infraestrutura foi registrado em `fc48d95`.
A regressão após esse merge aprovou **349 testes**. O protocolo,
as evidências e as limitações estão em `docs/observability.md`.

A correção P0 das regras de alerta foi posteriormente integrada à `main`,
com merge `b453d3f`. A regressão consolidada do Bloco 4 aprovou
**364 testes automatizados**, incluindo os novos testes de alertas.
Os três alertas foram demonstrados nos estados `firing` e `inactive`.

### Bloco 5 — Governança, privacidade, fairness e causalidade

**Estado: concluído e integrado à `main`, incluindo a consolidação documental final.**

Componentes entregues:

- Inventário e classificação das categorias de dados.
- Documentação de finalidade, privacidade, LGPD e responsabilidades.
- Avaliação de riscos, controles existentes e medidas recomendadas.
- Análise quantitativa agregada de fairness na partição de teste.
- Avaliação por idade, escolaridade e tipo de renda.
- Supressão consolidada de categorias com menos de 100 registros.
- Tratamento explícito de métricas com denominadores insuficientes.
- Discussão metodológica de vieses, associações e causalidade.
- Quatorze testes unitários específicos de fairness.

O baseline foi preservado: 46.127 observações, threshold
`0.1406724340221902` e matriz de confusão oficial reproduzida
exatamente pela análise quantitativa.

Entregas integradas:

- Governança e privacidade: merge `9be0c6d`.
- Fairness e causalidade: merge `47ef5e4`.
- Consolidação documental e arquitetural: merge `f632b53`.

Documentação detalhada:

- [Governança e privacidade](governance.md).
- [Fairness e causalidade](fairness-causality.md).

A análise identifica disparidades descritivas, sem demonstrar
discriminação ou relações causais. A documentação de LGPD não
constitui certificação de conformidade regulatória.

### Bloco 6 — Integração e demonstração

**Estado: integração técnica e documentação concluídas; vídeo STAR e submissão acadêmica pendentes.**

O Bloco 6 consolidou a demonstração integrada dos contratos
Pandera, da inferência bloqueante, da detecção de drift com
Evidently e da observabilidade com SQLite, exporter HTTP,
Prometheus e Grafana.

Foram reproduzidos cinco cenários operacionais:

- Scoring válido: 5 registros pontuados, exit code 0.
- Scoring inválido: rejeição Pandera, 0 registros pontuados,
  exit code 2.
- Drift controle: 0/16 features sinalizadas.
- Drift moderado: 0/16 features sinalizadas.
- Drift forte: 2/16 features sinalizadas.

No cenário forte, as features `AMT_CREDIT` e
`AMT_INCOME_TOTAL` apresentaram drift estatístico.
A regra Prometheus `CreditRiskDriftDetected` foi observada
em estado `firing`, e o Grafana apresentou oito painéis.

Os resultados, comandos e limites estão consolidados em
[Evidências end-to-end](end-to-end-evidence.md).

O checklist de submissão acadêmica está em
[Entrega final](final-delivery.md).

A entrega acadêmica prevista consiste no link do
repositório GitHub e no link do vídeo STAR publicado.
A produção do vídeo e a submissão ainda não foram
confirmadas.

A arquitetura não implementa agendamento automático
de scoring/drift nem notificações externas de alertas.
A demonstração utiliza dados históricos e cenários
simulados, sem constituir operação real de crédito.

## 4. Decisões técnicas aprovadas

| Área | Decisão | Justificativa |
|---|---|---|
| Dataset | Home Credit Default Risk | Cenário de classificação de risco de crédito |
| Arquivo inicial | `application_train.csv` | Ponto de partida para preparação e treinamento |
| Baseline | Scikit-Learn | Simplicidade e facilidade de reprodução |
| Primeiro modelo candidato | Logistic Regression | Baseline interpretável e relativamente simples |
| Validação de dados | Pandera | Contratos de dados integrados ao ecossistema Python |
| Drift | Evidently AI e testes estatísticos | Monitoramento de mudanças de distribuição |
| Execução | Pipeline Python local em lotes | Menor complexidade operacional inicial |
| Observabilidade | SQLite, Litestar/Uvicorn, Prometheus e Grafana | Persistência, exposição, coleta e visualização de métricas operacionais |
| Infraestrutura | Docker Compose | Orquestração local dos serviços implementados |
| Testes | pytest | Verificações automatizadas |
| Lint e formatação | Ruff | Padronização e análise estática |
| Governança e LGPD | Documentação transversal em `docs/governance.md` | Registrar inventário de dados, controles existentes, riscos e medidas propostas |
| Fairness | Script Python offline com pandas, NumPy e scikit-learn | Reutilizar baseline persistido e produzir métricas agregadas sem retreinamento |
| Causalidade | Análise metodológica documentada | Evitar interpretar diferenças preditivas ou cenários sintéticos de drift como efeitos causais demonstrados |

As tecnologias de observabilidade foram executadas e verificadas
localmente no Bloco 4. A análise quantitativa de fairness foi executada
no Bloco 5 sobre a partição histórica de teste, com reprodução do baseline.

Os controles de governança devem distinguir mecanismos implementados,
recomendações documentais e requisitos adicionais para eventual uso
produtivo. Não há demonstração de conformidade integral com a LGPD,
ausência de vieses ou identificação causal.

## 5. Arquitetura lógica e evolução

O fluxo abaixo registra a arquitetura conceitual original que orientou a implementação:

```text
HOME CREDIT
    |
    v
PREPARAÇÃO E TREINAMENTO DO BASELINE
    |
    v
MODELO TREINADO
    |
    v
LOTE DE PRODUÇÃO SIMULADO
    |
    v
VALIDAÇÃO DE CONTRATOS (PANDERA)
    |
    +---- LOTE INVÁLIDO ---> BLOQUEIO E REGISTRO DE FALHA
    |
    v
INFERÊNCIA
    |
    +----------------------+
    |                      |
    v                      v
PREDIÇÕES             ANÁLISE DE DRIFT
    |                      |
    +----------+-----------+
               |
               v
       EVENTOS E MÉTRICAS
               |
               v
       EXPORTADOR DE MÉTRICAS
               |
               v
           PROMETHEUS
               |
               v
            GRAFANA
```

Este diagrama é conceitual e preservado como referência histórica de planejamento.
A arquitetura física e os contratos de observabilidade efetivamente implementados
estão descritos na seção 17 e em `docs/observability.md`.
Uma rejeição pelo quality gate não equivale necessariamente a falha operacional.

## 6. Responsabilidades dos componentes por bloco

### 6.1 Preparação e treinamento

Responsável por:

- Carregar os dados do Home Credit.
- Realizar verificações iniciais.
- Definir a estratégia de preparação das variáveis.
- Separar dados de treino e avaliação.
- Treinar o baseline.
- Avaliar o desempenho do modelo.
- Produzir os artefatos necessários à inferência futura.

**Bloco responsável:** 1.

### 6.2 Validação e contratos de dados

Responsável por:

- Definir contratos com Pandera.
- Verificar tipos, restrições e regras de qualidade.
- Bloquear lotes que violem regras rígidas.
- Registrar os resultados de validação.
- Permitir cenários demonstráveis de dados válidos e inválidos.

A inferência não deverá ocorrer quando o lote for bloqueado.

**Bloco responsável:** 2.

### 6.3 Simulação de produção e drift

Responsável por:

- Separar dados de referência e dados de análise.
- Simular lotes de produção.
- Introduzir alterações controladas em pelo menos duas variáveis.
- Executar verificações estatísticas de drift.
- Produzir relatórios ou resultados interpretáveis.
- Diferenciar alterações de distribuição de evidências efetivas de degradação do modelo.

A escolha definitiva dos testes estatísticos e dos respectivos limiares ocorrerá durante a implementação.

**Bloco responsável:** 3.

### 6.4 Observabilidade operacional

Responsável por:

- Instrumentar a execução do pipeline.
- Registrar eventos e falhas relevantes.
- Expor métricas adequadas ao monitoramento.
- Permitir a coleta pelo Prometheus.
- Disponibilizar visualizações no Grafana.
- Implementar alertas pertinentes ao cenário demonstrado.

Não será criada uma API de negócio apenas para hospedar métricas, salvo necessidade arquitetural justificada.

**Bloco responsável:** 4.

### 6.5 Governança e privacidade

Responsável por documentar:

- Finalidade do tratamento de dados.
- Base legal e responsabilidades de tratamento.
- Minimização e tratamento de dados pessoais.
- Políticas de retenção e descarte.
- Riscos de vieses.
- Limitações de interpretação e causalidade.
- Medidas de privacidade por design e por padrão.

A documentação deverá distinguir práticas realmente implementadas de recomendações e controles planejados.

**Bloco responsável:** 5.

### 6.6 Integração e demonstração

Responsável por:

- Integrar os componentes desenvolvidos.
- Construir cenários reproduzíveis.
- Demonstrar bloqueio de lote inválido.
- Demonstrar detecção de drift.
- Demonstrar observabilidade e alertas.
- Preparar as evidências para a apresentação final.

**Bloco responsável:** 6.

## 7. Contratos arquiteturais e sua evolução

Esta seção preserva contratos originalmente planejados e sua motivação.
As interfaces efetivamente implementadas até o Bloco 4 estão descritas
nas seções de implementação e em `docs/observability.md`.

### 7.1 Contrato de entrada

Um lote de produção deverá:

- Apresentar estrutura compatível com as variáveis necessárias ao modelo.
- Passar pelas validações obrigatórias.
- Permitir a identificação da execução a que pertence.

Os tipos, nomes de campos e esquemas definitivos serão definidos nos blocos correspondentes.

### 7.2 Contrato de bloqueio

Quando uma regra rígida de validação falhar:

1. O lote deverá ser classificado como inválido.
2. A falha deverá ser registrada.
3. A inferência deverá ser interrompida para aquele lote.
4. O resultado deverá permitir identificar o motivo do bloqueio.

O formato dos registros será definido posteriormente.

### 7.3 Contrato de rastreabilidade

As execuções deverão possuir um identificador que permita correlacionar:

- Resultado da validação.
- Resultado da inferência, quando realizada.
- Resultado da análise de drift.
- Logs e eventos operacionais.
- Métricas e alertas associados.

O Bloco 2 adotou `batch_id` como identificador operacional das validações e inferências.
O Bloco 3 reutilizou esse identificador no monitoramento de drift.
Sua utilização nos alertas e nas métricas de observabilidade será definida no Bloco 4.

### 7.4 Contrato de separação de dados

Os dados utilizados como referência para monitoramento deverão permanecer logicamente separados dos lotes simulados de produção.

Essa separação deverá ser verificável durante os testes e demonstrações.

### 7.5 Contrato de observabilidade

A instrumentação futura deverá permitir identificar, quando aplicável:

- Execuções iniciadas e concluídas.
- Falhas operacionais.
- Lotes bloqueados.
- Resultados relevantes de drift.
- Duração das execuções.
- Alertas configurados.

A especificação das métricas e seus nomes ficará para o Bloco 4.

## 8. Organização do repositório

O pacote utiliza layout `src/`.

A estrutura implementada contém módulos de preparação, modelagem, qualidade e drift, com testes unitários e de integração.

Novos diretórios serão criados somente quando houver uma responsabilidade concreta associada a eles.

Não serão adicionados antecipadamente módulos vazios para treinamento, validação, drift ou observabilidade.

### Gerenciamento de dependências

O projeto utiliza:

- Ambiente virtual `.venv`.
- pip.
- setuptools.
- Dependências declaradas no `pyproject.toml`.

As dependências de desenvolvimento são separadas das dependências funcionais.

### Qualidade

As verificações atuais são:

```bash
python -m pytest -v
python -m ruff check .
python -m ruff format --check .
python -m pip check
```

## 9. Estratégia de versionamento

O desenvolvimento ocorrerá em branches locais de escopo limitado.

Cada branch será:

1. Criada a partir da `main`.
2. Desenvolvida e validada.
3. Registrada por commit semântico.
4. Integrada à `main`.
5. Validada novamente após o merge.
6. Publicada por meio do push da `main`.
7. Excluída localmente após confirmação da integração.

As branches de desenvolvimento não serão publicadas no remoto.

## 10. Limites de escopo

O Bloco 0 estabelece a fundação técnica e documenta decisões arquiteturais.

Ele não implementa regras de crédito, contratos Pandera, simulação de produção, drift ou monitoramento operacional.

Cada bloco futuro deverá preservar os contratos aprovados ou justificar formalmente eventuais alterações.

Mudanças arquiteturais relevantes deverão ser discutidas com o Chat Arquiteto antes de sua implementação.

## 11. Histórico de desenvolvimento dos blocos anteriores


> **Nota histórica:** esta seção preserva o planejamento
> incremental registrado durante o Bloco 1. As referências
> a branches em desenvolvimento ou planejadas representam
> o estado da época, não o estado atual do repositório.
> Para o estado consolidado, consultar a seção 3.

O Bloco 1 está organizado em branches incrementais.

### Branch 1 — `chore/data-safety`

Concluída e integrada à `main`.

Entregas:

- Proteção de datasets e artefatos pelo `.gitignore`.
- Atualização do README após o Bloco 0.
- Documentação de obtenção do Home Credit.

Commit de implementação: `9711076`.

Commit de merge: `5cb487d`.

### Branch 2 — `feature/data-preparation`

Em desenvolvimento.

Responsável por:

- Inspeção e carregamento dos dados.
- Seleção inicial de features.
- Tratamento determinístico da sentinela.
- Particionamento estratificado.
- Persistência dos conjuntos e metadados.
- Testes de preparação e integridade.

### Branch 3 — `feature/credit-baseline`

Planejada.

Responsável por:

- Pipeline Scikit-Learn.
- Imputação, encoding e scaling.
- Regressão logística.
- Avaliação e seleção de threshold.
- Serialização do modelo e metadados.

Ajustes estatísticos deverão utilizar exclusivamente
os dados autorizados para cada finalidade.

### Branch 4 — `docs/baseline-reproducibility`

Planejada.

Responsável por consolidar documentação, comandos
de reprodução, evidências e contratos finais do Bloco 1.

O Bloco 2 deverá receber o contrato de entrada dos dados,
enquanto o Bloco 3 utilizará a referência de monitoramento
e o pipeline treinado para produzir scores.

## 12. Contratos implementados de preparação

**Contexto histórico:** esta seção documenta os contratos de preparação desenvolvidos durante o Bloco 1.
As referências a funcionalidades ainda não implementadas refletem aquele estágio.
Para os contratos de inferência implementados no Bloco 2, consultar a seção 15 e docs/quality-contracts.md.

### 12.1 Dataset de origem

Fonte: Home Credit Default Risk, Kaggle.

Arquivo: `data/raw/application_train.csv`.

Dimensões verificadas: 307.511 linhas e 122 colunas.

Identificador: `SK_ID_CURR`.

Alvo: `TARGET`, com valores 0 e 1.

Prevalência positiva observada: aproximadamente 8,07%.

Dados brutos não são versionados no Git.

### 12.2 Features do baseline

São utilizadas 16 features originais:

Numéricas:

- `AMT_CREDIT`
- `AMT_INCOME_TOTAL`
- `AMT_ANNUITY`
- `AMT_GOODS_PRICE`
- `EXT_SOURCE_2`
- `EXT_SOURCE_3`
- `DAYS_BIRTH`
- `DAYS_EMPLOYED`
- `DAYS_REGISTRATION`
- `CNT_CHILDREN`
- `CNT_FAM_MEMBERS`

Categóricas:

- `NAME_INCOME_TYPE`
- `NAME_EDUCATION_TYPE`
- `FLAG_OWN_CAR`
- `FLAG_OWN_REALTY`
- `NAME_CONTRACT_TYPE`

Feature derivada:

- `DAYS_EMPLOYED_SENTINEL`

Total: 17 features preditivas.

`SK_ID_CURR` e `TARGET` não são features do modelo.

A ordem oficial das features é definida pela constante
`MODEL_FEATURES` em `data/preparation.py`.

### 12.3 Tratamento da sentinela

O valor `365243` em `DAYS_EMPLOYED` representa
um código especial e não uma duração válida.

A preparação:

1. Identifica registros com esse valor.
2. Cria `DAYS_EMPLOYED_SENTINEL` com valores 0 ou 1.
3. Substitui a sentinela por NaN em `DAYS_EMPLOYED`.

A imputação estatística ainda não é realizada.

### 12.4 Particionamento

Estratégia: divisão aleatória estratificada por TARGET.

Seed padrão: 42.

| Partição | Percentual | Registros |
|---|---:|---:|
| train | 60% | 184.506 |
| validation | 15% | 46.127 |
| test | 15% | 46.127 |
| reference | 10% | 30.751 |

As quantidades correspondem ao dataset real inspecionado.

As partições são disjuntas e cobrem todos os registros.

O particionamento não representa uma divisão temporal.

### 12.5 Persistência

Arquivos de saída:

- `data/processed/train.csv`
- `data/processed/validation.csv`
- `data/processed/test.csv`
- `data/processed/reference.csv`
- `artifacts/data_manifest.json`

Treino, validação e teste possuem 19 colunas:
identificador, TARGET e 17 features.

A referência possui 18 colunas:
identificador e 17 features, sem TARGET.

O manifesto registra:

- Nome, hash e dimensões do dataset de origem.
- Seed e proporções dos splits.
- Lista ordenada de features.
- Tratamento de sentinela.
- Versões das bibliotecas.
- Quantidade de registros por partição.
- Colunas presentes nos arquivos.
- Prevalência original de TARGET por partição.
- Hash SHA-256 de cada CSV.

A prevalência da referência consta somente nos metadados
offline, não no CSV disponibilizado para monitoramento.

### 12.6 Interfaces Python

Módulo:

`credit_risk_monitoring.data.preparation`

Funções:

- `load_dataset(path)`: lê e verifica o CSV.
- `validate_source(df)`: aplica verificações estruturais.
- `prepare_features(df)`: seleciona e transforma features.
- `split_dataset(df, random_state=42)`: gera quatro partições.
- `validate_partitions(partitions, expected_size)`: verifica
  cobertura e ausência de sobreposição.

Os entrypoints locais são:

- `scripts/inspect_dataset.py`
- `scripts/prepare_dataset.py`

### 12.7 Limitações e próximas evoluções

As verificações existentes não substituem contratos Pandera.

O carregamento não executa validação semântica completa
de intervalos, infinitos ou categorias inesperadas.

Os CSVs contêm informações derivadas de dados cadastrais
e devem permanecer protegidos contra publicação indevida.

A persistência atual não é transacional. Uma execução
interrompida pode exigir a regeneração dos arquivos.

O Bloco 2 deverá validar a entrada antes de qualquer
transformação que possa mascarar problemas de qualidade.

O Bloco 3 deverá utilizar a referência para monitoramento
de distribuições, sem interpretá-la como produção temporal.

A disponibilidade real e a semântica das variáveis
EXT_SOURCE deverão ser verificadas em qualquer aplicação
fora do cenário acadêmico.

O uso de atributos como idade e educação exige avaliação
posterior de governança, equidade e conformidade.

## 13. Estratégia de seleção do threshold

O baseline utiliza inicialmente a maximização do F1-score
no conjunto de validação para selecionar o threshold.

Essa decisão foi tomada para manter simplicidade,
reprodutibilidade e foco nos critérios centrais
do Tech Challenge.

O F1 não representa uma função de perda econômica
ou rentabilidade de concessão de crédito.

Uma futura evolução poderá substituir a função objetivo
por custo de classificação ou utilidade econômica,
preservando o pipeline preditivo quando apropriado.

A justificativa, as alternativas e o plano de evolução
estão registrados em:

`docs/decisions/ADR-001-threshold-selection.md`

## 14. Baseline de classificação implementado

### 14.1. Pipeline de modelagem

O baseline utiliza LogisticRegression do Scikit-Learn,
integrada ao preprocessamento por um Pipeline.

As 17 features são divididas em:

- 11 numéricas: imputação pela mediana e StandardScaler.
- 5 categóricas: imputação pela moda e OneHotEncoder.
- 1 indicador binário: preservado sem scaling.

O preprocessamento é ajustado somente no treino.

Configuração do classificador:

- Solver: lbfgs.
- max_iter: 1000.
- class_weight: None.
- random_state: 42.

Na execução real, o modelo convergiu em 34 iterações,
sem ConvergenceWarning.

### 14.2. Protocolo de avaliação

Partições utilizadas:

- Treino: 184.506 registros.
- Validação: 46.127 registros.
- Teste: 46.127 registros.

Procedimento:

1. Ajustar o modelo exclusivamente no treino.
2. Selecionar o threshold pelo F1 na validação.
3. Fixar o threshold.
4. Avaliar o modelo no teste independente.
5. Salvar o pipeline e os metadados.

O threshold selecionado foi:

0.1406724340221902

A justificativa dessa escolha está documentada
em `docs/decisions/ADR-001-threshold-selection.md`.

### 14.3. Resultados oficiais

| Métrica | Validação | Teste |
|---|---:|---:|
| ROC-AUC | 0.734523 | 0.736332 |
| Average Precision | 0.218251 | 0.214999 |
| Precision | 0.226404 | 0.223766 |
| Recall | 0.407089 | 0.397959 |
| F1-score | 0.290979 | 0.286460 |

Matriz de confusão no teste:

- TN: 37.262.
- FP: 5.141.
- FN: 2.242.
- TP: 1.482.

Esses resultados representam avaliação offline
em partição aleatória do Home Credit.

Não representam validação temporal, performance
em produção ou resultado econômico de uma política
real de concessão de crédito.

### 14.4. Artefatos

Modelo:

`artifacts/baseline_model.joblib`

Métricas:

`artifacts/baseline_metrics.json`

O arquivo joblib contém um dicionário com:

- `pipeline`: Pipeline Scikit-Learn ajustado.
- `metadata`: configurações, features, threshold,
  versões das bibliotecas e hashes de proveniência.

O JSON registra:

- Metadados do modelo.
- Estratégia de seleção do threshold.
- Métricas da validação e do teste.
- Diagnósticos de treinamento.

Os arquivos são locais e ignorados pelo Git.

Arquivos joblib devem ser carregados somente
quando sua origem for confiável.

### 14.5. Contrato de inferência

O pipeline recebe as 17 features definidas em
`MODEL_FEATURES`, já submetidas às transformações
determinísticas de preparação.

Não recebe TARGET ou SK_ID_CURR como preditores.

A inferência foi validada nos 30.751 registros
de `data/processed/reference.csv`, sem TARGET.

Resultados observados:

- Score mínimo: 0.002295.
- Score mediano: 0.058838.
- Score médio: 0.080922.
- Score máximo: 0.672701.
- Taxa de positivos previstos: 14.45%.

O modelo persistido gerou probabilidades válidas,
com os metadados consistentes com o JSON.

Essa referência foi obtida por divisão aleatória
da mesma população histórica. Ela não comprova
ausência de drift em produção.

### 14.6. Interfaces implementadas

Módulos:

- `credit_risk_monitoring.modeling.pipeline`
- `credit_risk_monitoring.modeling.training`
- `credit_risk_monitoring.modeling.finalization`

Funções principais:

- `build_preprocessor()`
- `build_baseline_pipeline()`
- `train_baseline()`
- `evaluate_probabilities()`
- `select_threshold_by_f1()`
- `evaluate_final_model()`
- `save_final_model()`

Entrypoints:

- `scripts/train_baseline.py`
- `scripts/finalize_baseline.py`

### 14.7. Continuidade

Bloco 2 — Pandera:

Foram implementados contratos para entrada bruta
e preparada, regras de nulidade e consistência,
resultados estruturados e inferência bloqueante.

Os detalhes estão registrados na seção 15 e
em docs/quality-contracts.md.

Bloco 3 — Evidently:

Utilizar a referência não rotulada e o pipeline
persistido para avaliar distribuições de features
e scores em lotes de produção simulados.

A comparação de distribuições deverá considerar
a natureza histórica e aleatória da referência.

Bloco 4 — Observabilidade:

Instrumentar execução, resultados de validação,
inferência, falhas e métricas operacionais.

Não reajustar automaticamente o modelo ou o
threshold como consequência de um alerta de drift.

## 15. Arquitetura implementada — Bloco 2

### 15.1. Objetivo

O Bloco 2 implementa uma camada de validação
bloqueante antes da inferência do baseline de crédito.

A solução utiliza Pandera para validar lotes
em dois estágios distintos, preservando a
preparação e o modelo do Bloco 1.

### 15.2. Fluxo operacional

```text id="i3g23o"
LOTE BRUTO SEM TARGET
         |
         v
VALIDAÇÃO PANDERA — RAW
         |
         +---- REJEITADO ----> RELATÓRIO SEM SCORES
         |
         v
PREPARAÇÃO DETERMINÍSTICA
         |
         v
VALIDAÇÃO PANDERA — PREPARED
         |
         +---- REJEITADO ----> RELATÓRIO SEM SCORES
         |
         v
CARREGAMENTO DO MODELO PERSISTIDO
         |
         v
PREDICT_PROBA
         |
         v
THRESHOLD OFICIAL
         |
         v
RESULTADO OPERACIONAL
```

O modelo somente é carregado após a aprovação
dos dois contratos.

### 15.3. Componentes implementados

| Componente | Responsabilidade |
|---|---|
| `data/preparation.py` | Preparação histórica e transformação compartilhada da sentinela |
| `data/inference.py` | Preparação de lotes sem TARGET |
| `quality/contracts.py` | Definição dos schemas Pandera |
| `quality/results.py` | Estruturas de resultados de qualidade |
| `quality/validation.py` | Execução e agregação das validações |
| `modeling/inference.py` | Inferência com barreira bloqueante |
| `scripts/score_batch.py` | Interface operacional de scoring |

Os contratos detalhados, nomes das regras e
políticas de nulidade estão documentados em:

`docs/quality-contracts.md`

### 15.4. Contrato de entrada

A entrada bruta possui:

- `SK_ID_CURR`.
- 11 features numéricas originais.
- 5 features categóricas originais.

Não possui TARGET nem indicador derivado.

O contrato utiliza validação rígida de
estrutura e regras semânticas.

O arquivo de referência produzido pelo Bloco 1
já contém features preparadas e não deve ser
passado diretamente ao contrato bruto.

### 15.5. Contrato preparado

A preparação cria a feature:

`DAYS_EMPLOYED_SENTINEL`

O estágio preparado possui identificador
e 17 features preditivas.

O indicador derivado é verificado quanto
ao domínio binário e à consistência com
os valores tratados de DAYS_EMPLOYED.

### 15.6. Resultado de validação

Interface:

`validate_batch(df, stage, batch_id)`

Retorno:

`ValidationResult`

Campos principais:

- batch_id.
- stage.
- status.
- total_rows.
- violations.

Cada violação contém coluna, regra,
contagem e severidade.

Valores individuais dos clientes não
são incluídos nesses resultados.

### 15.7. Inferência protegida

Interface:

`run_quality_gated_inference(df, batch_id, model_path=...)`

Retorno:

`InferenceResult`

O serviço:

1. Executa o contrato bruto.
2. Rejeita imediatamente violações.
3. Prepara as features de maneira determinística.
4. Executa o contrato preparado.
5. Rejeita violações antes do modelo.
6. Carrega o baseline persistido.
7. Executa predict_proba.
8. Aplica o threshold oficial.
9. Retorna resultado estruturado.

O identificador SK_ID_CURR não é utilizado
como variável preditiva.

O serviço não executa fit, retreinamento
ou seleção de novo threshold.

### 15.8. Interface operacional

O script `scripts/score_batch.py` recebe
um CSV bruto e produz um relatório JSON.

Opcionalmente, pode produzir um CSV com:

- row_index.
- probability_default.
- prediction.

Códigos de saída:

- 0: aprovação e scoring concluído.
- 2: rejeição por qualidade.
- 1: erro operacional.

Arquivos existentes não são sobrescritos.

A persistência possui limpeza de melhor esforço
para falhas de gravação capturadas.

### 15.9. Evidências de funcionamento

O serviço foi testado com o modelo persistido.

Na demonstração operacional:

- Lote válido: cinco scores e relatório de aprovação.
- Lote inválido: zero scores e relatório de rejeição.
- Regra demonstrada: positive_credit.
- Threshold preservado: 0.1406724340221902.

Os testes automatizados também comprovam
que a rejeição impede o carregamento do modelo
e a chamada a predict_proba.

Após o merge funcional, 114 testes foram aprovados.

### 15.10. Contratos preservados

O Bloco 2 preserva:

- Dataset original.
- Particionamento e seed.
- Seleção de 17 features.
- Tratamento histórico da sentinela.
- Pipeline Scikit-Learn.
- Modelo persistido.
- Threshold oficial.
- Protocolo de avaliação do Bloco 1.

A transformação da sentinela foi extraída
para uma função compartilhada, com testes
de regressão de compatibilidade.

### 15.11. Continuidade

Bloco 3:

Utilizar os contratos e a inferência
como componentes de entrada para a
simulação de produção e o monitoramento
estatístico de drift.

Bloco 4:

Consumir os resultados estruturados
de validação e inferência para construir
métricas e observabilidade.

Bloco 5:

Consolidar controles de privacidade,
retenção, governança e avaliação de vieses.

Bloco 6:

Integrar as entregas e preparar a
demonstração final do Tech Challenge.

Não há monitoramento contínuo, alertas
operacionais ou detecção de drift
implementados pelo Bloco 2.

## 16. Arquitetura implementada — Bloco 3

### 16.1. Objetivo

O Bloco 3 implementa simulação de produção,
detecção estatística de data drift e
geração de relatórios de monitoramento.

A arquitetura reutiliza:

- Preparação dos dados do Bloco 1.
- Pipeline Logistic Regression persistido.
- Threshold oficial do baseline.
- Contratos Pandera do Bloco 2.
- Inferência protegida pelo quality gate.

Não há retreinamento ou recalibração
durante a execução do monitoramento.

### 16.2. Fluxo operacional

O processamento segue estas etapas:

1. Carregamento da referência preparada.
2. Reconstrução e validação de sua
   representação bruta de inferência.
3. Recebimento ou simulação do lote de produção.
4. Verificação de separação entre
   identificadores de referência e produção.
5. Validação do lote pelo quality gate.
6. Inferência sobre o lote aprovado.
7. Comparação estatística entre referência
   e produção com Evidently.
8. Consolidação de resultados por feature.
9. Geração de métricas agregadas por lote.
10. Exportação de relatórios JSON e HTML.

A rejeição pelo quality gate interrompe
o processamento antes do scoring e
da execução do detector de drift.

Um lote aprovado pode apresentar
drift estatístico sem ser rejeitado.

### 16.3. Componentes e responsabilidades

| Componente | Responsabilidade |
|---|---|
| `drift/simulation.py` | Reconstrução e simulação de lotes |
| `drift/detection.py` | Evidently e estatísticas por feature |
| `drift/results.py` | Resumos estruturados de drift |
| `drift/monitoring.py` | Orquestração do monitoramento |
| `drift/reporting.py` | Geração dos relatórios |
| `scripts/monitor_drift.py` | Interface operacional |

Esses componentes permanecem separados
dos módulos de preparação, qualidade
e modelagem dos blocos anteriores.

### 16.4. Contrato estatístico

São monitoradas 16 features originais:

- 11 numéricas.
- 5 categóricas.

`SK_ID_CURR` e `TARGET` não integram
as features enviadas ao detector.

`DAYS_EMPLOYED_SENTINEL` permanece como
feature derivada do baseline, mas não
é monitorada entre as 16 originais.

O Evidently seleciona métodos estatísticos
adequados aos tipos de variáveis e ao
volume de dados comparados.

A camada de detecção registra método,
estatística, limiar e decisão por feature.

O resumo agregado do projeto sinaliza
drift quando pelo menos uma feature
ultrapassa seu critério individual.

### 16.5. Resultados de referência

Execuções com referência de 30.751
registros e produção simulada de
46.127 registros:

| Cenário | Registros modificados | Features com drift |
|---|---:|---:|
| `control` | 0 | 0/16 |
| `moderate` | 23.063 | 0/16 |
| `strong` | 46.127 | 2/16 |

No cenário forte, foram sinalizadas:

- `AMT_CREDIT`.
- `AMT_INCOME_TOTAL`.

A seed padrão da simulação é 642.

O baseline permaneceu congelado, com
threshold `0.1406724340221902`.

Esses resultados demonstram mudanças
estatísticas nas entradas, sem comprovar
degradação real do desempenho do modelo.

### 16.6. Relatórios e operação

A interface `scripts/monitor_drift.py`
disponibiliza os subcomandos:

- `simulate`: produção sintética.
- `monitor`: produção bruta externa.

Códigos de saída:

| Código | Significado |
|---|---|
| `0` | Monitoramento concluído |
| `1` | Erro operacional |
| `2` | Rejeição pelo quality gate |

O código `0` não implica ausência de drift.

Os relatórios incluem informações
estatísticas por feature e indicadores
agregados de inferência.

A escrita utiliza proteção contra
sobrescrita e mecanismos de limpeza
de saídas parciais em falhas tratadas.

Esses mecanismos não constituem
transação durável entre múltiplos arquivos.

### 16.7. Limites arquiteturais

O Bloco 3 implementa monitoramento
estatístico por lotes, não um serviço
contínuo de produção.

Ainda não contempla:

- Coleta contínua de métricas.
- Prometheus e Grafana.
- Alertas operacionais persistentes.
- Agendamento de monitoramento.
- Retreinamento automático.
- Avaliação de concept drift com
  novos rótulos observados.
- Auditoria regulatória completa.

O Bloco 4 deverá utilizar os resultados
estruturados como base para observabilidade.

### 16.8. Documentação de referência

A metodologia estatística, os cenários,
as evidências, as decisões de dependências
e as limitações estão detalhadas em:

`docs/drift-monitoring.md`

Os contratos de entrada e o quality gate
permanecem documentados em:

`docs/quality-contracts.md`


## 17. Arquitetura implementada — Bloco 4

### 17.1. Objetivo e fronteiras

O Bloco 4 acrescenta **observabilidade operacional** às CLIs de scoring
e monitoramento estatístico de drift já existentes, sem alterar o
baseline, suas 17 features, o threshold `0.1406724340221902`, os
contratos Pandera ou as regras de detecção do Evidently.

A instrumentação registra eventos de execução em banco SQLite local;
um exporter HTTP agrega os eventos persistidos em métricas Prometheus;
o Prometheus realiza scrapes periódicos; e o Grafana consulta as
séries temporais para visualização. O pipeline de negócio continua
sendo executado por acionamento explícito, não por agendamento da stack.

### 17.2. Fluxo de dados e componentes

```text
scripts/score_batch.py        scripts/monitor_drift.py
         |                             |
         +----------+------------------+
                    |
             eventos operacionais
                    |
                    v
   artifacts/observability/events.sqlite3
               (SQLite local)
                    |
              leitura pelo exporter
                    v
         Litestar GET /metrics :8000
                    |
            scrape a cada 15 s
                    v
              Prometheus :9090
                    |
                  PromQL
                    v
               Grafana :3000
       Operations Overview (8 painéis)
```

| Módulo ou arquivo | Papel na arquitetura |
|---|---|
| `observability/events.py` | Contrato e validação dos eventos de execução |
| `observability/store.py` | Persistência e leitura estruturada em SQLite |
| `observability/metrics_catalog.py` | Definição das famílias e labels permitidos |
| `observability/metrics_aggregation.py` | Consolidação das métricas a partir dos eventos |
| `observability/metrics_exposition.py` | Exposição no formato texto Prometheus |
| `observability/metrics_http.py` | Aplicação HTTP e rota `/metrics` |
| `scripts/serve_metrics.py` | CLI de inicialização do exporter |
| `infra/Dockerfile.exporter` | Imagem Linux do exporter |
| `compose.yaml` | Serviços, rede, volumes e portas locais |
| `infra/prometheus/prometheus.yml` | Job de scrape `credit-risk-exporter` e carregamento de alert rules |
| `infra/prometheus/alert_rules.yml` | Regras PromQL de drift, falha e qualidade |
| `infra/prometheus/alert_rules.test.yml` | Cenários temporais do promtool |
| `infra/grafana/provisioning/` | Datasource e provider de dashboards |
| `infra/grafana/dashboards/operations-overview.json` | Dashboard versionado |

As referências abreviadas `observability/*.py` correspondem ao pacote
`src/credit_risk_monitoring/observability/`.

### 17.3. Contrato dos eventos operacionais

As CLIs instrumentadas utilizam a opção `--events-db` para apontar
o armazenamento operacional. O histórico é persistido em
`artifacts/observability/events.sqlite3`, ignorado pelo Git.
O componente `SQLiteEventStore` fornece leitura sequencial em lotes
por `iter_events(chunk_size=500)`.

Os estados considerados são `running`, `completed` e `failed`.
**Status de execução, resultado de qualidade e resultado de drift são
informações distintas**: a rejeição bloqueante de um lote pode produzir
código de saída `2` sem gerar scores; um monitoramento com drift pode
terminar normalmente com código `0`; falhas operacionais tratadas podem
retornar `1` e ser registradas como `failed`.

O armazenamento de eventos complementa os relatórios existentes e
não transforma a execução local por lotes em um serviço contínuo.

### 17.4. Contrato das métricas

O exporter expõe sete famílias do tipo `gauge`, reconstruídas a partir
do histórico persistido. Os labels autorizados são agregados e não
incluem identificadores individuais, `batch_id`, scores ou features.

| Família | Labels | Semântica |
|---|---|---|
| `credit_risk_executions_count` | `pipeline`, `execution_status` | Quantidade de execuções por estado |
| `credit_risk_quality_violations_count` | `pipeline` | Ocorrências agregadas de violações |
| `credit_risk_drift_detected_count` | `pipeline` | Execuções com drift detectado |
| `credit_risk_execution_duration_seconds_sum` | `pipeline` | Soma das durações registradas |
| `credit_risk_execution_duration_seconds_count` | `pipeline` | Número de durações registradas |
| `credit_risk_running_executions` | `pipeline` | Estados `running` persistidos |
| `credit_risk_last_success_timestamp_seconds` | `pipeline` | Timestamp da última conclusão bem-sucedida |

Os pipelines demonstrados são `scoring` e `monitoring`. Os sufixos
`_sum` e `_count` de duração são nomes de gauges agregados, **não**
constituem um `summary` ou `histogram` nativo.

A média histórica da duração por pipeline é calculada por:

```promql
sum by (pipeline) (credit_risk_execution_duration_seconds_sum)
/
sum by (pipeline) (credit_risk_execution_duration_seconds_count)
```

As contagens são instantâneos acumulados do SQLite observados no
instante de scrape, não counters de incremento contínuo; `rate()`
não deve ser aplicado indiscriminadamente. O Prometheus não reconstrói
a data original dos eventos anteriores ao primeiro scrape.

### 17.5. Interface HTTP e armazenamento

O endpoint `GET /metrics` usa Litestar/Uvicorn. A CLI
`scripts/serve_metrics.py` utiliza `127.0.0.1` como host padrão e
permite `0.0.0.0` somente quando configurado explicitamente, como
ocorre no Docker Compose. Falhas na leitura do SQLite são tratadas
como falhas de exposição HTTP, não como métricas aparentemente zeradas.

No Compose, o exporter utiliza usuário não privilegiado (`uid=10001`),
filesystem raiz em somente leitura e bind mount de
`artifacts/observability` com `RW=false`. A porta 8000 não é publicada
no host. Os acessos locais externos ao Compose são restritos a
`127.0.0.1:9090` (Prometheus) e `127.0.0.1:3000` (Grafana).
Prometheus e Grafana utilizam volumes nomeados de persistência próprios.

### 17.6. Provisionamento e visualização

O serviço Prometheus utiliza `prom/prometheus:v3.16.0`, scrape de
`exporter:8000/metrics` a cada 15 segundos e retenção configurada
de sete dias. O Grafana utiliza `grafana/grafana:12.2.0`, recebe
um datasource com UID `credit-risk-prometheus` e disponibiliza o
dashboard de UID `credit-risk-operations`.

O dashboard possui oito painéis: execuções totais, falhas, violações
de qualidade, drift, execuções por status/pipeline, duração média por
pipeline, execuções em andamento e disponibilidade do exporter.
Seus arquivos são versionados e provisionados sem importação manual.

A senha administrativa é fornecida por `GRAFANA_ADMIN_PASSWORD` em
`.env` local, ignorado pelo Git. O provisionamento não representa
uma solução de gestão centralizada de segredos.

### 17.7. Evidências e reprodutibilidade

Na execução local observada em 15/11/2026:

- Histórico SQLite com seis eventos: quatro de scoring e dois de monitoring.
- Exporter com `GET /metrics` HTTP 200 e 18 amostras.
- Target Prometheus `up`, sem erro de scrape, com `up=1`.
- Três execuções de scoring concluídas e uma com falha operacional.
- Duas execuções de monitoring concluídas; nenhuma execução em andamento.
- Duas ocorrências agregadas de violação de qualidade e uma execução com drift.
- Duração média histórica aproximada: 7,947 s para monitoring e 0,103 s para scoring.
- Grafana com datasource e dashboard provisionados, oito painéis e API HTTP 200.
- Verificação do container do exporter com `uid=10001` e bind mount `RW=false`.

O merge de infraestrutura `fc48d95` foi validado com **349 testes
aprovados**, Ruff lint e formatação aprovados, `pip check` sem
conflitos e `docker compose config --quiet` válido. A `main` foi
publicada em `origin/main` e a branch funcional excluída localmente.
Esses valores são evidências de demonstração, não indicadores
representativos de operação produtiva.

O roteiro detalhado de reprodução, os comandos de verificação e o
catálogo das métricas estão em `docs/observability.md`.

#### 17.7.1. Alertas automáticos — complemento da correção P0

Além dos scrapes e das consultas do Grafana, o Prometheus avalia três regras
versionadas (`infra/prometheus/alert_rules.yml`): `CreditRiskDriftDetected`,
`CreditRiskOperationalFailure` e `CreditRiskQualityViolation`. Os gauges
históricos do SQLite são examinados por `delta(...[3m]) > 0`, com avaliação
a cada 15 segundos; o alerta reflete mudança observada durante os scrapes,
não um registro individual de evento com timestamp original.

A implementação preserva os módulos de preparação, Pandera, modelo,
Evidently, SQLite e exporter. Não adiciona Alertmanager, notificações
externas nem novos painéis no Grafana. Em 15/11/2026, os três alertas
registraram amostras `firing` reais, com posterior estado `inactive`.
A regressão ampliada passou de 349 testes históricos para 364 testes na
branch antes da consolidação documental. Procedimentos e horários
observados constam de `docs/observability.md`.

### 17.8. Limitações e continuidade

A arquitetura atual **não** implementa agendamento contínuo de
scoring/drift, notificações automáticas de alerta, reconstrução
retroativa do histórico de eventos como séries temporais, retreinamento
automático, implantação em nuvem, autenticação de rede completa, TLS,
backups automatizados ou alta disponibilidade.

O estado persistido `running` pode permanecer obsoleto caso uma
execução seja interrompida antes da transição terminal. A retenção
de sete dias no Prometheus não elimina automaticamente os eventos
armazenados no SQLite. Os dados de referência e os lotes de drift
são históricos ou simulados, sem demonstração de concept drift nem
degradação preditiva em produção.

O Bloco 5 deverá aprofundar governança, privacidade, retenção,
vieses e responsabilidades; o Bloco 6 deverá consolidar a
demonstração integrada e as evidências finais.

## 18. Arquitetura implementada — Bloco 5

### 18.1. Objetivo e fronteiras

O Bloco 5 acrescenta documentação de governança, privacidade e LGPD, juntamente com uma avaliação quantitativa offline de disparidades preditivas do baseline de crédito.

A implementação preserva:

- Dataset original e partições determinísticas.
- Baseline LogisticRegression persistido.
- As 17 features oficiais.
- Threshold `0.1406724340221902`.
- Contratos Pandera e inferência bloqueante.
- Monitoramento de drift com Evidently.
- Observabilidade operacional e alertas Prometheus.

O Bloco 5 não modifica as decisões de classificação do baseline, não retreina modelos e não altera a infraestrutura operacional.

A avaliação de fairness é diagnóstica e retrospectiva. Não integra automaticamente o fluxo das CLIs de scoring e monitoramento.

### 18.2. Fluxo da análise quantitativa

```text
data/processed/test.csv
          |
          v
Validação estrutural do conjunto rotulado
          |
          +-------------------------------+
          |                               |
          v                               v
Features oficiais                TARGET histórico
          |
          v
Carregamento do baseline persistido
          |
          v
predict_proba()
          |
          v
Threshold oficial congelado
          |
          v
Previsões binárias
          |
          +-------------------------------+
                                          |
                                          v
                      Métricas globais e por grupo
                                          |
                                          v
                         Supressão de grupos raros
                                          |
                                          v
                       Relatório JSON agregado local
```

O processamento ocorre em memória, utilizando o dataset histórico de teste.

A etapa de validação utiliza `validate_model_data()`. O modelo e seu threshold são carregados pela função `load_baseline_model()`, que verifica a estrutura do artefato e a compatibilidade dos metadados.

O script utiliza diretamente `predict_proba()` do pipeline persistido. Não executa `fit()` nem seleciona novamente o threshold.

### 18.3. Componentes e responsabilidades

| Arquivo | Responsabilidade |
|---|---|
| `docs/governance.md` | Inventário de dados, finalidades, privacidade, LGPD, riscos e medidas de governança |
| `scripts/analyze_fairness.py` | Avaliação offline e exportação de métricas agregadas |
| `tests/unit/test_fairness_analysis.py` | Testes de métricas, grupos, validações e minimização de dados |
| `docs/fairness-causality.md` | Metodologia, resultados, limitações, vieses e interpretação causal |
| `artifacts/fairness_test_aggregated.json` | Resultado agregado gerado localmente, não versionado |

A avaliação utiliza componentes já existentes em:

- `credit_risk_monitoring.data.preparation`
- `credit_risk_monitoring.modeling.inference`
- `credit_risk_monitoring.modeling.training`

Não foi criado um serviço HTTP de fairness, um novo modelo preditivo ou um processo de execução contínua.

### 18.4. Contrato de entrada

A análise utiliza a partição `data/processed/test.csv`, que contém:

- `SK_ID_CURR`, utilizado para validação estrutural, mas não exportado.
- `TARGET`, utilizado exclusivamente como rótulo histórico de avaliação.
- As 17 features preditivas definidas em `MODEL_FEATURES`.

O baseline é carregado de `artifacts/baseline_model.joblib`.

A análise utiliza exclusivamente o threshold persistido no artefato. O conjunto de teste não é empregado para selecionar parâmetros do modelo.

As dimensões diagnósticas são:

1. Faixas etárias derivadas de `DAYS_BIRTH`.
2. Escolaridade, conforme `NAME_EDUCATION_TYPE`.
3. Tipo de renda, conforme `NAME_INCOME_TYPE`.

### 18.5. Contrato de saída e métricas

O script gera um JSON com:

- Identificação da análise e partição.
- Identificação genérica do baseline.
- Threshold utilizado.
- Limites metodológicos de suporte amostral.
- Métricas globais.
- Métricas por dimensão e grupo elegível.
- Limitações de interpretação.

As métricas incluem:

- Quantidade de registros.
- Quantidade de positivos e negativos observados.
- Quantidade de classificações positivas.
- Prevalência histórica de inadimplência.
- Taxa de classificação positiva.
- Precision.
- Recall/TPR.
- FPR.
- Matriz de confusão.

A classe positiva representa inadimplência, não aprovação de crédito.

Métricas condicionais com denominadores inferiores a 20 são representadas como `null`.

### 18.6. Minimização e supressão

A implementação não exporta identificadores individuais, linhas de clientes ou vetores de probabilidades individuais.

Grupos com menos de 100 registros não têm suas métricas individuais publicadas. Suas contagens são consolidadas em uma categoria técnica denominada `SUPPRESSED_GROUPS`.

A consolidação preserva a soma dos registros por dimensão, mas não divulga os nomes das categorias raras.

O JSON é salvo dentro de `artifacts/`, diretório ignorado pelo Git. A escrita recusa sobrescrever um arquivo existente.

Esses mecanismos reduzem exposição, mas não representam anonimização formal, controle de acesso completo, criptografia ou implementação automática de políticas de retenção.

O relatório também não substitui a documentação de privacidade em `docs/governance.md`.

### 18.7. Evidências quantitativas

A análise foi executada na partição histórica de teste, com 46.127 registros.

O threshold preservado foi `0.1406724340221902`.

A matriz de confusão reproduziu exatamente os resultados oficiais:

| Resultado | Quantidade |
|---|---:|
| TN | 37.262 |
| FP | 5.141 |
| FN | 2.242 |
| TP | 1.482 |

As três dimensões de agrupamento apresentaram cobertura integral dos 46.127 registros.

Na dimensão etária, a soma das matrizes de confusão por grupo reproduziu integralmente a matriz global.

Na dimensão de escolaridade, 27 registros foram consolidados por supressão. Na dimensão de tipo de renda, foram consolidados oito registros.

As avaliações identificaram disparidades descritivas nas taxas de classificação positiva, recall e FPR. Os resultados detalhados constam de `docs/fairness-causality.md`.

Essas diferenças não demonstram, isoladamente, discriminação ou efeitos causais.

### 18.8. Governança, LGPD e responsabilidades

A governança foi documentada em `docs/governance.md`, distinguindo controles existentes, recomendações e lacunas.

Os temas abordados incluem:

- Finalidade e categorias de dados.
- Minimização e exposição de dados pessoais.
- Riscos associados aos artefatos locais.
- Possíveis bases legais, dependentes do contexto de tratamento.
- Retenção e descarte propostos.
- Segurança e responsabilidades organizacionais hipotéticas.
- Direitos dos titulares e limitações do cenário acadêmico.
- Riscos de vieses e necessidade de supervisão humana.

O projeto não demonstra implantação organizacional desses controles nem certifica conformidade integral com a LGPD.

### 18.9. Causalidade e relação com drift

O Bloco 3 implementa mudanças sintéticas controladas nas distribuições de variáveis e detecção estatística de drift.

O Bloco 5 documenta a distinção entre:

- Associação estatística.
- Sensibilidade das previsões a alterações nas entradas.
- Mudança de distribuição.
- Efeito causal sobre inadimplência real.

As simulações não demonstram que alterações em renda ou crédito produziriam efeitos causais sobre a inadimplência observada.

A identificação causal exigiria hipóteses adicionais, conhecimento do domínio, tratamento de fatores de confusão e um desenho apropriado de estudo.

Nenhuma estimativa causal foi implementada nesta etapa.

### 18.10. Testes e validações

A implementação quantitativa foi validada com 14 testes unitários direcionados, incluindo:

- Cálculo de taxas e matriz de confusão.
- Tratamento de denominadores insuficientes.
- Definição das faixas etárias.
- Consolidação e ocultação de categorias raras.
- Verificação de dimensões.
- Rejeição de probabilidades e thresholds inválidos.
- Restrição de exportação à pasta `artifacts/`.
- Proteção contra sobrescrita.
- Verificação do contrato de agregação.

O Ruff lint e a formatação foram aprovados.

A reprodução do baseline e a consistência dos agrupamentos também foram verificadas com os dados reais.

A regressão completa executada durante a consolidação documental do Bloco 5 aprovou **378 testes automatizados** em 152,53 segundos. Ruff lint e formatação foram aprovados, com 79 arquivos Python formatados; `pip check` não encontrou incompatibilidades e `docker compose config --quiet` foi validado. O comando `git diff --check` não apresentou erros.

### 18.11. Limitações e continuidade

O Bloco 5 não implementa:

- Auditoria regulatória completa.
- Anonimização formal.
- Exclusão automática de dados por prazo de retenção.
- Controle de acesso centralizado.
- Avaliação temporal de fairness.
- Intervalos de confiança para as disparidades.
- Estimativa de efeitos causais.
- Mitigação automática de vieses.
- Retreinamento ou alteração de threshold.
- Monitoramento contínuo de fairness em produção.

A análise utiliza dados históricos e grupos com diferentes prevalências e tamanhos amostrais.

O Bloco 6 poderá utilizar a documentação e os resultados agregados como evidências da entrega, mas permanece responsável por sua própria integração demonstrativa e apresentação final.
