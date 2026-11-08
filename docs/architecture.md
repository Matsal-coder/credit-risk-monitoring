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

### Bloco 0 — Fundação e arquitetura

Concluído em 07/11/2026.

Componentes implementados:

- Pacote Python `credit_risk_monitoring` com layout `src/`.
- Configuração de empacotamento pelo `pyproject.toml`.
- Ambiente virtual `.venv` e instalação editável.
- pytest e Ruff.
- Smoke test de importação.
- Documentação inicial de arquitetura.
- Versionamento Git com branches locais.

### Bloco 1 — Dados e modelo baseline

Em desenvolvimento.

Componentes implementados na branch `feature/data-preparation`:

- Inspeção exploratória reproduzível do Home Credit.
- Carregamento do arquivo `application_train.csv`.
- Verificações estruturais mínimas de entrada.
- Seleção de 16 variáveis originais.
- Criação de indicador para `DAYS_EMPLOYED=365243`.
- Preparação de 17 features preditivas.
- Particionamento aleatório estratificado e determinístico.
- Separação entre treino, validação, teste e referência.
- Persistência local em CSV.
- Manifesto JSON com hashes e metadados.
- Testes unitários e de integração.

Validações realizadas:

- 307.511 registros reais processados.
- 17 testes automatizados aprovados.
- Ruff check e Ruff format aprovados.
- Dependências verificadas com pip check.
- Determinismo das sequências de IDs confirmado em duas
  execuções com o dataset real.
- Arquivos processados e artefatos ignorados pelo Git.

Os componentes desta branch ainda não foram integrados
à `main`.

### Componentes ainda não implementados

- Pipeline Scikit-Learn de preprocessamento aprendido.
- Treinamento e avaliação do baseline.
- Modelo treinado e serializado.
- Contratos Pandera e bloqueio de lotes.
- Pipeline de inferência operacional.
- Simulação e detecção de drift.
- Instrumentação Prometheus e Grafana.
- Infraestrutura Docker Compose.
- Rotinas de monitoramento de produção.

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
| Observabilidade | Prometheus e Grafana | Coleta e visualização de métricas |
| Infraestrutura | Docker Compose | Orquestração local dos serviços futuros |
| Testes | pytest | Verificações automatizadas |
| Lint e formatação | Ruff | Padronização e análise estática |
| Governança | Documentação transversal | Privacidade e responsabilidade sobre os dados |

As escolhas de tecnologias futuras não implicam que suas dependências estejam instaladas.

## 5. Arquitetura lógica planejada

O fluxo principal previsto é:

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

Este diagrama é conceitual. Ele não define classes, APIs ou estruturas de arquivos definitivas.

Os componentes deverão evoluir conforme seus respectivos blocos forem implementados.

## 6. Responsabilidades dos componentes futuros

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

## 7. Contratos arquiteturais planejados

Os contratos abaixo representam comportamentos esperados, não interfaces Python já implementadas.

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

O nome e a implementação desse identificador ainda não foram definidos.

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

A estrutura atual contém o código mínimo do pacote e a suíte inicial de testes.

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

## 11. Continuidade

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

Validar as features antes do preprocessamento.
Distinguir entradas obrigatórias, nulos permitidos,
tipos, sentinelas e regras semânticas de qualidade.

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
