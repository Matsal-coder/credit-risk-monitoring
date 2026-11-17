# Credit Risk Monitoring

Projeto desenvolvido para o **Tech Challenge — Fase 4 da Pós-Tech FIAP em Machine Learning Engineering**, com foco em monitoramento contínuo, qualidade de dados, detecção de drift, observabilidade e governança de modelos de Machine Learning.

## 1. Contexto

O projeto simula um cenário de uma fintech que utiliza um modelo de classificação de risco de crédito.

O objetivo é desenvolver uma solução capaz de identificar problemas de qualidade nos dados recebidos, alterações nas distribuições das variáveis e possíveis sinais de degradação do modelo em produção.

A implementação será incremental, com validação dos componentes antes de sua integração.

## 2. Escopo funcional do projeto

A solução deverá contemplar:

- Treinamento de um modelo baseline de classificação.
- Validação dos dados de entrada utilizando contratos.
- Bloqueio de lotes que violem regras rígidas de qualidade.
- Simulação de dados de produção com alterações controladas.
- Detecção estatística de data drift.
- Geração de relatórios de monitoramento.
- Registro de eventos, métricas e alertas operacionais.
- Monitoramento de infraestrutura e execução.
- Documentação de privacidade, LGPD e governança.

**Estado atual:** os Blocos 0 a 4 estão concluídos e integrados à `main`, incluindo a correção P0 das três regras de alerta Prometheus. O Bloco 5 está concluído, incluindo governança, privacidade, fairness agregado e limitações de causalidade. O Bloco 6 concluiu a integração demonstrativa e consolidou suas evidências técnicas; a publicação do vídeo STAR e o envio dos links de entrega permanecem pendentes. O sistema não executa automaticamente as CLIs de scoring/drift, não possui notificações externas de alertas e não representa um ambiente produtivo de concessão de crédito.

## 3. Tecnologias

### Implementadas

- Python 3.12.
- pandas e NumPy — manipulação e preparação dos dados.
- Scikit-Learn — preprocessamento e modelo baseline.
- joblib — persistência do pipeline treinado.
- Pandera — contratos e validação bloqueante de dados.
- Evidently AI — detecção estatística de data drift e relatórios HTML.
- SQLite — persistência de eventos operacionais.
- Litestar e Uvicorn — disponibilização HTTP de métricas.
- Prometheus 3.16.0 — coleta e armazenamento temporal das métricas.
- Grafana 12.2.0 — dashboards operacionais provisionados.
- Docker Compose — orquestração local da infraestrutura de observabilidade.
- setuptools — empacotamento.
- pytest — testes unitários e de integração.
- Ruff — lint e formatação.
- Git e GitHub — controle de versões.

### Governança e avaliação diagnóstica implementadas

- Bloco 5 — documentação de governança, privacidade e LGPD; avaliação quantitativa agregada de fairness, testes automatizados e discussão de causalidade.

### Etapa de integração em andamento

- Bloco 6 — integração demonstrativa, evidências finais e preparação da entrega.

Os contratos Pandera e a inferência bloqueante pertencem ao Bloco 2; simulação de produção e detecção estatística de drift, ao Bloco 3. O Bloco 4 adiciona eventos operacionais persistidos, endpoint de métricas e visualização com Prometheus/Grafana. Os serviços são executados localmente; o processamento de lotes continua sob acionamento explícito.

## 4. Dataset

O dataset escolhido é o **Home Credit Default Risk**, disponibilizado no Kaggle.

A implementação começará pelo arquivo `application_train.csv`.

O arquivo application_train.csv foi obtido e inspecionado no Bloco 1. A preparação determinística e a geração das partições foram implementadas e validadas com os 307.511 registros reais. Os dados brutos e processados permanecem locais e ignorados pelo Git.

Os dados não serão incluídos no repositório Git.

### 4.1. Obtenção dos dados

Fonte: Home Credit Default Risk (Kaggle).

https://www.kaggle.com/competitions/home-credit-default-risk/data

O dataset será obtido manualmente pelo usuário,
respeitando os termos de uso e as condições
de acesso disponibilizados pelo Kaggle.

Arquivo inicial utilizado:

- `application_train.csv`

Local esperado:

- `data/raw/application_train.csv`

Procedimento:

1. Acessar a página da competição no Kaggle.
2. Autenticar-se e aceitar os termos aplicáveis, se exigidos.
3. Baixar os dados disponibilizados.
4. Extrair `application_train.csv`.
5. Salvar o arquivo em `data/raw/`, na raiz do projeto.

Os diretórios e arquivos de dados são ignorados pelo Git.

Não incluir credenciais, tokens, datasets brutos,
dados processados ou modelos treinados nos commits.

A integridade, estrutura, volume, tipos e distribuição
do dataset serão verificados na etapa de preparação
dos dados, antes do treinamento do baseline.

## 5. Estrutura atual

A estrutura abaixo representa os componentes versionados após a conclusão dos Blocos 0 a 5. A árvore foi consolidada a partir do inventário de arquivos Git, preservando a separação entre preparação, modelagem, qualidade, drift, observabilidade e governança.

```text
credit-risk-monitoring/
├── docs/
│   ├── decisions/
│   │   └── ADR-001-threshold-selection.md
│   ├── architecture.md
│   ├── drift-monitoring.md
│   ├── fairness-causality.md
│   ├── governance.md
│   ├── observability.md
│   ├── quality-contracts.md
│   └── reproducibility.md
├── infra/
│   ├── grafana/
│   │   ├── dashboards/
│   │   │   └── operations-overview.json
│   │   └── provisioning/
│   │       ├── dashboards/
│   │       │   └── dashboards.yml
│   │       └── datasources/
│   │           └── prometheus.yml
│   ├── prometheus/
│   │   ├── alert_rules.test.yml
│   │   ├── alert_rules.yml
│   │   └── prometheus.yml
│   └── Dockerfile.exporter
├── scripts/
│   ├── analyze_fairness.py
│   ├── finalize_baseline.py
│   ├── inspect_dataset.py
│   ├── monitor_drift.py
│   ├── prepare_dataset.py
│   ├── score_batch.py
│   ├── serve_metrics.py
│   ├── train_baseline.py
│   └── verify_dataset.py
├── src/
│   └── credit_risk_monitoring/
│       ├── data/
│       ├── drift/
│       ├── modeling/
│       ├── observability/
│       ├── quality/
│       └── __init__.py
├── tests/
│   ├── integration/
│   └── unit/
├── .dockerignore
├── .gitignore
├── compose.yaml
├── pyproject.toml
└── README.md
```

Os diretórios `src/credit_risk_monitoring/` e `tests/` estão resumidos por responsabilidade. Os módulos Python e testes completos podem ser consultados diretamente no repositório.

**Arquivos e diretórios locais não versionados:**

| Caminho | Finalidade |
|---|---|
| `data/raw/` | Dataset histórico original |
| `data/processed/` | Partições e lotes utilizados nas execuções |
| `artifacts/` | Modelo, relatórios JSON/HTML e resultados locais |
| `artifacts/observability/events.sqlite3` | Persistência de eventos operacionais |
| `.env` | Configuração local de credenciais |
| `.venv/` | Ambiente Python isolado |

Esses caminhos não fazem parte da árvore versionada. Alguns arquivos são gerados durante a execução dos scripts, e sua existência depende da preparação local do ambiente.

Dados individuais, scores, credenciais, banco SQLite e modelo persistido não devem ser publicados no GitHub.

## 6. Configuração do ambiente

### Pré-requisitos

- Python 3.12
- Git
- Acesso à internet para instalação das dependências

### Clonar o repositório

```bash
git clone https://github.com/Matsal-coder/credit-risk-monitoring.git

cd credit-risk-monitoring
```

### Criar o ambiente virtual

No Git Bash, em Windows:

```bash
python -m venv .venv

source .venv/Scripts/activate
```

### Instalar as dependências de desenvolvimento

```bash
python -m pip install -e ".[dev]"
```

As bibliotecas serão instaladas no ambiente virtual, sem modificar o Python global.

## 7. Testes e verificações

Executar os testes:

```bash
python -m pytest -v
```

Verificar problemas de código:

```bash
python -m ruff check .
```

Verificar formatação:

```bash
python -m ruff format --check .
```

Verificar consistência das dependências:

```bash
python -m pip check
```

A suíte inclui testes unitários e de integração dos Blocos 0 a 5. A regressão completa realizada no encerramento técnico do Bloco 5 aprovou **378 testes automatizados**, incluindo os **14 testes de fairness** adicionados nesta fase. Ruff lint e formatação foram aprovados, com 79 arquivos Python formatados; `pip check` não identificou conflitos e `docker compose config --quiet` foi executado sem erros. Os números apresentados nas seções históricas correspondem aos marcos de cada etapa.

## 8. Roadmap de desenvolvimento

| Bloco | Objetivo |
|---|---|
| 0 | Fundação e arquitetura executável |
| 1 | Dataset, preparação e treinamento do baseline |
| 2 | Qualidade de dados e contratos Pandera |
| 3 | Simulação de produção e detecção de drift |
| 4 | Instrumentação, métricas, Prometheus e Grafana |
| 5 | Governança, privacidade, causalidade e vieses |
| 6 | Integração, cenários demonstráveis e preparação da entrega |

Após os blocos de implementação, o projeto passará por auditoria técnica independente e revisão dos critérios de avaliação.

## 9. Organização do desenvolvimento

O desenvolvimento utiliza branches locais por funcionalidade.

Cada branch passa por:

1. Implementação incremental.
2. Validação dos arquivos e funcionalidades.
3. Execução das verificações disponíveis.
4. Commit semântico.
5. Merge na `main`.
6. Nova validação.
7. Push da `main`.
8. Exclusão da branch local integrada.

As branches de desenvolvimento não são enviadas ao repositório remoto.

## 10. Arquitetura

As decisões arquiteturais, os contratos implementados e seus registros históricos estão documentados em [Arquitetura do Projeto](docs/architecture.md), criada durante o Bloco 0 e atualizada ao longo do desenvolvimento.

O projeto utiliza uma abordagem incremental, evitando antecipar dependências e infraestrutura que ainda não possuem utilização prática.

## 11. Estado atual

### Resumo consolidado

Estado consolidado do projeto após o merge `f632b53`, correspondente à conclusão documental do Bloco 5, e verificação inicial do Bloco 6 em 15/11/2026:

| Bloco | Estado |
|---|---|
| 0 — Fundação e arquitetura | Concluído |
| 1 — Dados e baseline | Concluído |
| 2 — Contratos e inferência bloqueante | Concluído |
| 3 — Simulação e detecção de drift | Concluído |
| 4 — Observabilidade e alertas | Concluído, incluindo correção P0 |
| 5 — Governança, privacidade e fairness | Concluído e integrado à `main` |
| 6 — Integração e demonstração | Evidências técnicas concluídas; entrega audiovisual pendente |

O Bloco 5 foi integrado à `main` em três entregas:

1. Governança, privacidade e LGPD — merge `9be0c6d`.
2. Fairness quantitativo e causalidade — merge `47ef5e4`.
3. Consolidação documental e arquitetural — merge `f632b53`.

Na verificação inicial do Bloco 6, executada em 15/11/2026 sobre `f632b53`, foram aprovados **378 testes automatizados em 112,44 segundos**. Ruff lint e formatação foram aprovados, com 79 arquivos Python formatados; `pip check` não identificou conflitos; `docker compose config --quiet` e `git diff --check` não apresentaram erros.

A solução mantém o baseline e os contratos funcionais congelados. O Bloco 6 concentra-se em integração demonstrativa, documentação de evidências e preparação do roteiro STAR, sem representar implantação em produção.

Referências técnicas:

- [Arquitetura](docs/architecture.md).
- [Contratos de qualidade](docs/quality-contracts.md).
- [Reprodutibilidade](docs/reproducibility.md).
- [Monitoramento de drift](docs/drift-monitoring.md).
- [Observabilidade](docs/observability.md).
- [Governança e privacidade](docs/governance.md).
- [Fairness, vieses e causalidade](docs/fairness-causality.md).

O baseline utiliza LogisticRegression com 17 features,
e o threshold oficial é `0.1406724340221902`.

O Bloco 2 implementou contratos Pandera para dados
brutos e preparados, validação estruturada de lotes,
preparação sem TARGET, inferência bloqueante e
interface operacional de scoring.

Na regressão pós-merge da infraestrutura do Bloco 4:

- **349 testes automatizados aprovados**.
- Ruff lint e formatação aprovados (73 arquivos Python formatados).
- `pip check` sem conflitos.
- Docker Compose válido, com exporter, Prometheus e Grafana em execução.
- Coleta de métricas confirmada (`up=1`) e oito painéis carregados no Grafana.
- Quality gate e demais contratos anteriores preservados.

Referências técnicas:

- [Arquitetura](docs/architecture.md).
- [Contratos de qualidade](docs/quality-contracts.md).
- [Reprodutibilidade](docs/reproducibility.md).
- [Monitoramento de drift](docs/drift-monitoring.md).
- [Observabilidade](docs/observability.md).
- [Governança e privacidade](docs/governance.md).
- [Fairness, vieses e causalidade](docs/fairness-causality.md).

As seções históricas abaixo registram a evolução
incremental do projeto. Os estados intermediários
nelas descritos não substituem o resumo consolidado.

**Bloco 0 — Fundação e Arquitetura: concluído em 07/11/2026.**

Componentes implementados e validados:

- Estrutura de pacote Python com layout `src/`.
- Instalação editável em ambiente virtual isolado.
- Configuração de pytest.
- Configuração de Ruff.
- Smoke test de importação do pacote.
- Documentação inicial de arquitetura.
- Versionamento Git com commits semânticos.
- Branches do Bloco 0 integradas à `main`.

Validações registradas no encerramento do Bloco 0:

- pytest: 1 teste aprovado.
- Ruff check: aprovado.
- Ruff format --check: aprovado.
- pip check: aprovado.
- Git: `main` sincronizada com `origin/main`, sem alterações pendentes.

**Bloco 1 — Dados e Modelo Baseline: concluído.**

A branch `chore/data-safety` foi concluída e integrada à `main`.

A branch `feature/data-preparation` implementou:

- Inspeção exploratória do Home Credit.
- Carregamento e verificações estruturais.
- Seleção de 16 features originais.
- Tratamento da sentinela `DAYS_EMPLOYED=365243`.
- Criação de uma feature indicadora, totalizando 17.
- Divisão determinística e estratificada dos dados.
- Persistência de quatro partições em CSV.
- Manifesto JSON com hashes e metadados.
- Verificação de integridade dos artefatos.
- Testes unitários e de integração.

A execução real gerou 184.506 registros de treino,
46.127 de validação, 46.127 de teste e 30.751
de referência.

O treinamento, a avaliação e a serialização do modelo
foram implementados posteriormente na continuidade do Bloco 1,
conforme detalhado na subseção Baseline de classificação.

### Baseline de classificação

O baseline foi implementado com LogisticRegression
e Pipeline do Scikit-Learn.

O modelo foi treinado com 184.506 registros e
avaliado em 46.127 registros de teste independente.

Resultados no teste:

- ROC-AUC: 0,7363.
- Average Precision: 0,2150.
- Precision: 22,38%.
- Recall: 39,80%.
- F1-score: 0,2865.

O threshold de 0,140672434 foi selecionado
exclusivamente na validação, pela maximização do F1.

O pipeline completo foi salvo em
`artifacts/baseline_model.joblib`, e as métricas
em `artifacts/baseline_metrics.json`.

A inferência com o modelo persistido foi validada
nos 30.751 registros não rotulados da referência.

A justificativa da seleção do threshold está
em `docs/decisions/ADR-001-threshold-selection.md`.

A consolidação da reprodutibilidade do Bloco 1
será realizada na branch documental seguinte.


## 12. Reprodução da preparação dos dados

### 12.1. Pré-requisitos

- Python 3.12.
- Ambiente virtual `.venv` ativado.
- Dependências instaladas com `pip install -e ".[dev]"`.
- Arquivo `data/raw/application_train.csv` disponível.

Todos os comandos devem ser executados na raiz do projeto.

### 12.2. Inspeção exploratória

```bash
python scripts/inspect_dataset.py
```

Saída:

`artifacts/inspection_summary.json`

Contém dimensões, perfil das colunas, distribuição
do TARGET, nulos, identificadores e sentinelas.

### 12.3. Preparação e particionamento

```bash
python scripts/prepare_dataset.py
```

Parâmetros opcionais:

- `--input`: arquivo CSV de origem.
- `--output-dir`: diretório dos conjuntos processados.
- `--manifest`: caminho do manifesto JSON.
- `--seed`: seed do particionamento; padrão 42.

Saídas:

```text
data/processed/
├── train.csv
├── validation.csv
├── test.csv
└── reference.csv

artifacts/
├── inspection_summary.json
└── data_manifest.json
```

Os conjuntos são estratificados pelo TARGET.

Proporções:

- Treino: 60%.
- Validação: 15%.
- Teste: 15%.
- Referência: 10%.

Treino, validação e teste contêm `SK_ID_CURR`,
`TARGET` e 17 features preditivas.

A referência contém `SK_ID_CURR` e 17 features,
sem TARGET.

Nenhum dos arquivos de dados é versionado no Git.

### 12.4. Verificação de integridade

```bash
python scripts/verify_dataset.py
```

O verificador compara os arquivos com o manifesto,
incluindo hashes SHA-256, estrutura, quantidade
de registros e identificadores.

A validação retorna código de saída diferente de
zero quando encontra uma inconsistência tratada.

O manifesto é uma referência local de integridade,
não uma assinatura digital autenticada.

### 12.5. Testes e qualidade

```bash
python -m pytest -v
python -m ruff check .
python -m ruff format --check .
python -m pip check
```

### 12.6. Decisões e limitações

As 17 features são definidas pela constante
`MODEL_FEATURES` do módulo de preparação.

`SK_ID_CURR` e `TARGET` não devem entrar como
variáveis preditivas.

A sentinela `365243` de `DAYS_EMPLOYED` é
substituída por NaN e acompanhada de um indicador.

A imputação estatística, o encoding e o scaling
foram implementados no pipeline do baseline,
com ajuste restrito aos dados de treino.

As partições são aleatórias e não representam
uma separação cronológica de produção.

O conjunto de referência foi reservado para
monitoramento e não deve ser utilizado para
treinamento ou escolha de threshold.

A validação estrutural inicialmente desenvolvida no Bloco 1
foi complementada, no Bloco 2, por contratos Pandera para inferência,
 com regras semânticas e bloqueio de lotes inválidos.

Os CSVs podem conter informações cadastrais
e devem permanecer protegidos.

A persistência não é transacional; uma execução
interrompida pode exigir regeneração e nova
verificação dos artefatos.

A arquitetura e os contratos detalhados estão
documentados em `docs/architecture.md`.

### 12.7. Treinamento e avaliação do baseline

Para executar o diagnóstico na validação:

```bash
python scripts/train_baseline.py
```

Para executar o protocolo completo de treinamento,
seleção de threshold, avaliação final e persistência:

```bash
python scripts/verify_dataset.py
python scripts/finalize_baseline.py
```

O segundo procedimento acessa o conjunto de teste.
Seus resultados devem ser tratados como avaliação
final, não como oportunidade para reajustar o modelo.

O modelo e os resultados são armazenados localmente
no diretório `artifacts/`, ignorado pelo Git.

### 12.8. Guia completo de reprodutibilidade

O procedimento ponta a ponta para reproduzir a
preparação, o treinamento, a avaliação e a
persistência do baseline está documentado em:

[Guia de reprodutibilidade](docs/reproducibility.md)

O guia registra o ambiente de referência, as
partições, os hashes, as métricas oficiais,
as verificações de integridade e as limitações
conhecidas do Bloco 1.

## 13. Validação de qualidade e inferência — Bloco 2

### 13.1. Objetivo

O Bloco 2 adiciona uma barreira de qualidade antes
da inferência do modelo de crédito.

O fluxo implementado é:

```text
Lote CSV bruto
    |
    v
Contrato Pandera raw_inference
    |
    +-- Rejeitado --> Relatório sem scores
    |
    v
Preparação determinística
    |
    v
Contrato Pandera prepared_inference
    |
    +-- Rejeitado --> Relatório sem scores
    |
    v
Baseline persistido
    |
    v
Probabilidades e classificações
```

O modelo somente é carregado após a aprovação
dos dois contratos de qualidade.

### 13.2. Contratos

Os contratos são definidos em:

`src/credit_risk_monitoring/quality/contracts.py`

O serviço de validação está em:

`src/credit_risk_monitoring/quality/validation.py`

Foram implementadas regras de presença de colunas,
tipos, unicidade dentro do lote, intervalos numéricos,
domínios categóricos e consistência da sentinela
`DAYS_EMPLOYED`.

As regras e políticas de nulidade estão detalhadas em:

[Catálogo de contratos](docs/quality-contracts.md).

### 13.3. Entrada esperada

O script de scoring recebe um CSV bruto com:

- `SK_ID_CURR`.
- As 16 features originais selecionadas.
- Nenhuma coluna TARGET.
- Nenhuma coluna DAYS_EMPLOYED_SENTINEL.

O contrato utiliza `strict=True`, portanto
colunas adicionais não previstas são rejeitadas.

O arquivo `data/processed/reference.csv` já contém
features preparadas e não deve ser enviado diretamente
ao contrato bruto.

### 13.4. Executar scoring

Com a `.venv` ativada, na raiz do projeto:

```bash
python scripts/score_batch.py \
  --input data/processed/quality_demo/valid_batch.csv \
  --batch-id demo-valid-readme \
  --report-output data/processed/quality_demo/readme_valid_report.json \
  --scores-output data/processed/quality_demo/readme_valid_scores.csv
```

O exemplo pressupõe que `valid_batch.csv` já tenha
sido gerado localmente conforme o guia de
reprodutibilidade do Bloco 2.

Os caminhos de saída precisam ser novos. O script
recusa sobrescrever arquivos existentes.

O parâmetro `--scores-output` é opcional.

O modelo padrão é:

`artifacts/baseline_model.joblib`

### 13.5. Códigos de saída

| Código | Resultado |
|---|---|
| 0 | Lote aprovado e scoring concluído |
| 2 | Lote rejeitado por qualidade |
| 1 | Erro operacional |

Um lote rejeitado não produz scores.

Os relatórios incluem identificador do lote,
status, quantidade de registros e resultados
agregados dos contratos.

Scores individuais somente são gravados quando
solicitados explicitamente.

### 13.6. Evidências funcionais

Na demonstração validada do Bloco 2:

| Evidência | Válido | Inválido |
|---|---|---|
| Registros recebidos | 5 | 5 |
| Registros pontuados | 5 | 0 |
| Status | approved | rejected |
| Código de saída | 0 | 2 |
| Relatório JSON | Gerado | Gerado |
| CSV de scores | Gerado | Não gerado |

O lote inválido apresentou violação da regra
`positive_credit`, provocada por uma alteração
sintética em AMT_CREDIT.

O threshold oficial permaneceu inalterado:

`0.1406724340221902`

### 13.7. Testes

Executar:

```bash
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m pip check
```

Após a integração funcional do Bloco 2,
114 testes foram aprovados.

Os testes incluem cenários de rejeição antes
de predict_proba, comparação com o modelo
persistido e validação dos arquivos gerados
pela interface operacional.

### 13.8. Privacidade e limitações

Os datasets, artefatos e scores individuais
permanecem locais e ignorados pelo Git.

O campo batch_id deve ser operacional e não
deve conter dados pessoais.

A validação de qualidade não substitui
monitoramento estatístico, análise de drift
ou governança completa de dados.

O Bloco 3 reutilizou a referência histórica
e os mecanismos de inferência do Bloco 2
para construir cenários de produção simulada.

## 14. Simulação de produção e detecção de drift — Bloco 3

O Bloco 3 implementa monitoramento estatístico
por lotes, reutilizando o baseline persistido
e o quality gate do Bloco 2.

Componentes principais:

- `drift/simulation.py`: simulação determinística.
- `drift/detection.py`: detecção com Evidently.
- `drift/results.py`: resultados estruturados.
- `drift/monitoring.py`: orquestração do fluxo.
- `drift/reporting.py`: relatórios JSON e HTML.
- `scripts/monitor_drift.py`: interface operacional.

### 14.1. Cenários de simulação

| Cenário | Registros afetados | Renda | Crédito |
|---|---:|---:|---:|
| `control` | 0% | Sem alteração | Sem alteração |
| `moderate` | 50% | -10% | +10% |
| `strong` | 100% | -20% | +25% |

A simulação utiliza seed 642 por padrão.

Na execução de referência, foram utilizados
30.751 registros históricos e 46.127 registros
de produção simulada.

### 14.2. Executar o monitoramento

Com a `.venv` ativa, na raiz do repositório:

```bash
python scripts/monitor_drift.py \
  --reference data/processed/reference.csv \
  --model artifacts/baseline_model.joblib \
  --batch-id readme-strong-642 \
  --json-output artifacts/readme-strong.json \
  --html-output artifacts/readme-strong.html \
  simulate \
  --production-prepared data/processed/test.csv \
  --scenario strong \
  --seed 642
```

Os arquivos de entrada e o modelo precisam
estar disponíveis localmente.

Os destinos de relatório devem ser novos:
a CLI não sobrescreve arquivos existentes.

Também é possível monitorar um lote bruto
externo com o subcomando `monitor` e
o argumento `--production-raw`.

### 14.3. Resultados de referência

| Cenário | Features com drift | Classificações positivas |
|---|---:|---:|
| `control` | 0/16 | 6.623 |
| `moderate` | 0/16 | 7.376 |
| `strong` | 2/16 | 11.141 |

O cenário forte sinalizou drift em:

- `AMT_CREDIT`.
- `AMT_INCOME_TOTAL`.

O threshold do modelo permaneceu fixo em
`0.1406724340221902`.

Esses resultados representam previsões
de um modelo congelado sobre dados simulados,
não inadimplências efetivamente observadas.

### 14.4. Códigos de saída

| Código | Significado |
|---|---|
| `0` | Execução concluída e qualidade aprovada |
| `1` | Erro operacional |
| `2` | Lote rejeitado pelo quality gate |

O código `0` não indica ausência de drift.

Um lote válido pode apresentar alterações
estatísticas e continuar sendo processado.

### 14.5. Testes e documentação

Após o merge funcional do Bloco 3:

- 211 testes automatizados aprovados.
- Ruff lint e formatação aprovados.
- `pip check` sem conflitos.
- Nenhum warning exibido na execução final do pytest.

Para reproduzir as verificações:

```bash
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m pip check
```

A metodologia, os métodos estatísticos,
os resultados e as limitações estão
documentados em:

`docs/drift-monitoring.md`

O monitoramento de infraestrutura com Prometheus/Grafana
foi implementado posteriormente no Bloco 4. Esta seção
preserva os resultados históricos do Bloco 3.


## 15. Instrumentação e observabilidade — Bloco 4

O Bloco 4 acrescenta instrumentação operacional aos fluxos por lote de scoring e monitoramento de drift. Os eventos são registrados localmente em SQLite; o exporter agrega eventos existentes e expõe métricas no endpoint `/metrics`, coletadas pelo Prometheus e apresentadas no Grafana.

### 15.1. Componentes e contratos

- **Eventos SQLite:** registro de execuções, status e resultados operacionais; banco local em `artifacts/observability/events.sqlite3`.
- **Exporter:** `scripts/serve_metrics.py`, com interface de rede local `127.0.0.1` por padrão e `0.0.0.0` apenas quando explicitamente solicitado para o container.
- **Prometheus:** serviço Docker `prometheus`, coleta de `exporter:8000/metrics` a cada 15 segundos e retenção configurada de sete dias.
- **Grafana:** serviço Docker `grafana`, datasource provisionado e dashboard `Credit Risk Monitoring - Operations Overview` com oito painéis.
- **Alertas:** três regras Prometheus versionadas para novo drift, falha operacional e violação de qualidade; avaliação a cada 15 s, janela de detecção de 3 min.

As métricas de contagem são **gauges agregados sobre o histórico SQLite**. O Prometheus registra seus valores ao longo dos scrapes, sem reconstruir automaticamente os timestamps originais dos eventos. Não se deve aplicar `rate()` indiscriminadamente a essas séries nem interpretá-las como counters monotônicos nativos.

### 15.2. Executar a infraestrutura local

Pré-requisitos: Docker Desktop com engine Linux ativo; Git Bash no Windows; repositório clonado; arquivo `.env` local contendo `GRAFANA_ADMIN_PASSWORD` forte. Não versionar a senha. O exporter utiliza o diretório `artifacts/observability/` somente para leitura e pressupõe um banco operacional SQLite já criado.

Na raiz do repositório:

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

Serviços acessíveis no host:

- Prometheus: <http://127.0.0.1:9090/targets>.
- Grafana: <http://127.0.0.1:3000/d/credit-risk-operations>.
- Exporter: acessível somente pela rede interna Docker na porta 8000, sem publicação no host.

A autenticação inicial do Grafana utiliza o usuário `admin` e a senha configurada em `.env`. O datasource aponta internamente para `http://prometheus:9090`.

Para interromper os serviços sem excluir volumes:

```bash
docker compose down
```

**Não** executar `docker compose down -v` se houver dados persistentes a preservar.

### 15.3. Evidências de validação

Na validação operacional do Bloco 4, a base SQLite continha seis eventos (duas execuções de monitoramento e quatro de scoring). As consultas retornaram seis execuções no total, uma falha operacional, duas ocorrências agregadas de violação de qualidade e uma execução com drift. O Prometheus identificou o exporter como `UP`, e os oito painéis foram disponibilizados pelo provisionamento do Grafana. Esses números descrevem um snapshot de demonstração, não uma amostra estatística de produção.

Na regressão pós-merge da infraestrutura (`fc48d95`): **349 testes aprovados**, Ruff e `pip check` aprovados, Docker Compose validado e serviços em execução. O exporter foi verificado com `uid=10001` e volume SQLite montado com `RW=false`.

### 15.4. Alertas automáticos — correção P0

As regras em `infra/prometheus/alert_rules.yml` são carregadas pelo
Prometheus a partir de `infra/prometheus/prometheus.yml` e disponibilizadas
por bind mount somente leitura em `compose.yaml`. As expressões utilizam
`delta(gauge[3m]) > 0`, evitando disparos simplesmente por totais
históricos maiores que zero. O dashboard Grafana permanece com oito painéis;
não há Alertmanager ou notificações por e-mail/Slack.

Na demonstração real de 15/11/2026 (UTC), o alerta de drift disparou às
22:55:38, o alerta de falha operacional às 22:56:38 e o alerta de qualidade
às 23:32:17. Os três retornaram posteriormente a `inactive` (a última
consulta de qualidade registrou zero alertas ativos às 23:35:34).
O cenário controle aprovado não disparou drift. As regras passaram em
`promtool check rules` e `promtool test rules`; 15 testes Python novos
aprovados, com regressão geral de **364 testes aprovados** antes da revisão
documental. O procedimento e as limitações constam de `docs/observability.md`.

### 15.5. Limitações e documentação

A solução não agenda automaticamente os lotes de scoring/drift; o Prometheus realiza coleta periódica de métricas, não execução contínua do modelo. Não há alertas automáticos com notificações configurados, reconstrução de histórico temporal de eventos no Prometheus, retreinamento automático, implantação em nuvem ou garantias de conformidade regulatória integral.

Consulte [Observabilidade — Bloco 4](docs/observability.md) para os contratos, catálogo de métricas, procedimentos de validação, segurança e limitações detalhadas.

## 16. Governança e Causalidade — Bloco 5

O Bloco 5 consolida a avaliação de governança, privacidade, LGPD, possíveis vieses e limitações causais do Credit Risk Monitoring. O projeto utiliza dados históricos do Home Credit Default Risk, disponibilizados no Kaggle, exclusivamente para uma demonstração acadêmica. Não realiza concessão ou recusa real de crédito, não opera com solicitações reais de clientes e não constitui um sistema produtivo de decisão financeira.

A avaliação combina documentação dos controles existentes com uma análise quantitativa offline de fairness na partição de teste, preservando o baseline e seus contratos.

### 16.1. Inventário de dados e minimização

O dataset original contém 307.511 registros e 122 colunas. Após a preparação, o baseline utiliza 17 features preditivas: 16 variáveis originais e um indicador derivado para o tratamento da sentinela `DAYS_EMPLOYED=365243`.

As informações incluem atributos financeiros, cadastrais e familiares, como renda, valor de crédito, idade aproximada, escolaridade e tipo de renda. O identificador `SK_ID_CURR` permanece nos arquivos de dados para verificações estruturais, mas não é utilizado como variável preditiva.

**Controles implementados:**

- Dados brutos, partições processadas, modelo e artefatos locais excluídos do versionamento Git.
- Separação de `SK_ID_CURR` e `TARGET` das features enviadas ao modelo.
- Validação bloqueante de qualidade antes da inferência.
- Relatórios operacionais predominantemente agregados, com scores individuais exportados apenas quando explicitamente solicitados.
- Eventos SQLite e métricas Prometheus sem identificadores individuais de clientes nos labels.
- Interface de observabilidade restrita ao ambiente local, com controles de isolamento do exporter.

**Limitações:** a exclusão do Git não equivale a anonimização, criptografia ou controle de acesso aos arquivos locais. O dataset publicamente disponibilizado também não deve ser considerado automaticamente anônimo ou livre de restrições de tratamento.

### 16.2. LGPD, bases legais e decisões automatizadas

A documentação considera os princípios da Lei nº 13.709/2018, especialmente finalidade, adequação, necessidade, transparência, segurança, prevenção e não discriminação.

Para uma fintech hipotética, possíveis hipóteses legais a avaliar incluiriam proteção do crédito (art. 7º, X), execução de contrato ou procedimentos preliminares (art. 7º, V), cumprimento de obrigação legal ou regulatória (art. 7º, II) e legítimo interesse (art. 7º, IX), conforme a finalidade e as condições concretas do tratamento.

A definição da base legal dependeria de uma avaliação jurídica específica. O caráter acadêmico do projeto ou a disponibilidade pública dos dados não determinam automaticamente a hipótese aplicável.

O artigo 20 da LGPD prevê o direito de solicitar revisão de decisões tomadas unicamente com base em tratamento automatizado de dados pessoais que afetem interesses do titular, incluindo determinadas decisões relacionadas a perfil de crédito.

O baseline deste projeto gera classificações experimentais de inadimplência. Seu threshold não representa uma política real de aprovação ou rejeição de crédito, e não existe um processo implementado de atendimento a solicitações de titulares.

**Status:** princípios, hipóteses jurídicas e responsabilidades documentados; conformidade jurídica integral não certificada.

### 16.3. Retenção e descarte de dados

A governança distingue explicitamente a retenção técnica atualmente configurada das políticas propostas para uma eventual operação controlada.

| Categoria | Situação atual | Política acadêmica proposta |
|---|---|---|
| Dados brutos e partições | Armazenamento local, sem expurgo automático | Até 30 dias após encerramento e aceite |
| Lotes simulados e scores individuais | Arquivos locais, sem expurgo automático | Até 30 dias após execução |
| Relatórios JSON/HTML | Arquivos locais, sem expurgo automático | Até 90 dias após execução |
| Eventos SQLite | Persistência local, sem TTL automático | Até 90 dias após execução |
| Séries Prometheus | Retenção configurada de 7 dias | Manter o prazo configurado |
| Grafana | Volume persistente | Remoção controlada após encerramento e aceite |
| Modelo e metadados | Artefatos locais | Até 90 dias após encerramento e aceite |

Os prazos de 30 e 90 dias são propostas internas do exercício, não exigências legais universais. Não foi implementado expurgo automático, e a retenção do Prometheus não elimina registros persistidos no SQLite, relatórios ou datasets.

### 16.4. Fairness e avaliação quantitativa de vieses

A avaliação de fairness é executada offline por `scripts/analyze_fairness.py`, utilizando os 46.127 registros rotulados da partição de teste e o baseline persistido.

O threshold permanece fixado em `0.1406724340221902`, sem retreinamento ou ajustes por grupo. A análise reproduziu a matriz de confusão oficial:

| Métrica | Registros |
|---|---:|
| Verdadeiros negativos (TN) | 37.262 |
| Falsos positivos (FP) | 5.141 |
| Falsos negativos (FN) | 2.242 |
| Verdadeiros positivos (TP) | 1.482 |

Foram avaliadas três dimensões: faixas etárias, escolaridade e tipo de renda. Para cada grupo elegível, a análise considera prevalência histórica, taxa de classificação positiva, precision, recall/TPR, FPR e matriz de confusão.

**Exemplos de disparidades descritivas observadas:**

- **Faixa etária:** taxa de classificação positiva de 30,09% para menores de 30 anos, contra 3,90% para pessoas de 60 anos ou mais.
- **Escolaridade:** 24,01% em `Lower secondary`, contra 5,75% em `Higher education`.
- **Tipo de renda:** foram observadas disparidades nas classificações e nas taxas de erro entre os grupos avaliados. As métricas dos grupos elegíveis estão disponíveis no relatório agregado, respeitando a supressão primária e complementar para impedir a reconstrução direta das contagens de categorias raras.

A classe positiva corresponde à previsão de inadimplência (`TARGET=1`), não à aprovação de crédito.

Essas diferenças são descritivas e coexistem com diferenças de prevalência, composição e tamanho amostral entre os grupos. Não comprovam, isoladamente, discriminação, injustiça algorítmica ou efeitos causais.

Para reduzir a divulgação de informações, o relatório JSON agrega grupos com menos de 100 observações em `SUPPRESSED_GROUPS`, sem identificar individualmente suas categorias. Métricas condicionais com denominadores inferiores a 20 são registradas como `null`. Essas medidas não constituem garantia formal de anonimização.

O arquivo `artifacts/fairness_test_aggregated.json` permanece local e não versionado.

### 16.5. Data drift, concept drift e causalidade

O projeto distingue três fenômenos:

- **Data drift:** alteração estatística na distribuição das variáveis de entrada, monitorada pelo Evidently.
- **Concept drift:** alteração na relação entre as variáveis preditoras e o resultado real, que exigiria evidências adicionais, incluindo novos rótulos observados.
- **Causalidade:** identificação do efeito de uma intervenção sobre um resultado, dependente de hipóteses e métodos específicos de inferência causal.

Na simulação forte do Bloco 3, o Evidently detectou drift em `AMT_CREDIT` e `AMT_INCOME_TOTAL`, totalizando 2 das 16 features monitoradas. A taxa de classificações positivas também variou entre os cenários simulados.

Essas evidências demonstram mudanças nas distribuições de entrada e na resposta preditiva do modelo congelado. Não demonstram aumento real da inadimplência, degradação comprovada em produção, concept drift ou efeito causal das variáveis modificadas.

Da mesma forma, as disparidades observadas entre grupos na avaliação de fairness são associações descritivas. Sua interpretação requer considerar fatores de confusão, proxies, composição populacional e limitações dos rótulos históricos.

### 16.6. Controles, limites e documentação complementar

**Implementado e verificado:** contratos de qualidade, inferência bloqueante, monitoramento estatístico por lotes, eventos operacionais, métricas agregadas, alertas Prometheus e diagnóstico offline de fairness.

**Documentado ou proposto:** hipóteses jurídicas, políticas de retenção e descarte, procedimentos de atendimento aos titulares, controles organizacionais e medidas futuras de mitigação de vieses.

**Não implementado ou não comprovado:** anonimização formal, expurgo automatizado, auditoria jurídica, certificação LGPD, avaliação temporal de fairness, mitigação automática de vieses, inferência causal e validação de desempenho em produção real.

Documentação complementar:

- [Governança de Dados, Privacidade e LGPD](docs/governance.md).
- [Fairness, Vieses e Causalidade](docs/fairness-causality.md).
- [Arquitetura do Projeto](docs/architecture.md).
- [Monitoramento de Drift](docs/drift-monitoring.md).
- [Observabilidade e Alertas](docs/observability.md).

A governança apresentada é uma avaliação acadêmica dos controles e riscos da arquitetura desenvolvida, sem constituir parecer jurídico ou declaração de conformidade regulatória integral.

## 17. Integração e Entrega Final — Bloco 6

O Bloco 6 concluiu a integração demonstrativa dos componentes
desenvolvidos nos blocos anteriores, sem modificar o baseline,
os contratos de qualidade ou a arquitetura operacional.

### 17.1. Evidências de integração

Foram executados cinco cenários end-to-end:

| Cenário | Resultado |
|---|---|
| Scoring válido | Pandera aprovado; 5 registros pontuados; exit 0 |
| Scoring inválido | Rejeição por `positive_credit`; 0 registros pontuados; exit 2 |
| Drift controle | 0/16 features com drift |
| Drift moderado | 0/16 features com drift |
| Drift forte | 2/16 features com drift |

No cenário forte, o Evidently sinalizou `AMT_CREDIT` e
`AMT_INCOME_TOTAL`, utilizando Wasserstein distance
(normed) com threshold estatístico de 0,1.

Os três cenários de drift processaram 46.127 registros
cada, com quality gate aprovado.

### 17.2. Observabilidade integrada

A demonstração confirmou o fluxo:

`Pipeline → SQLite → Exporter → Prometheus → Grafana`

Foram verificados:

- Persistência dos cinco eventos operacionais no SQLite.
- Exportação HTTP de métricas agregadas.
- Target Prometheus `credit-risk-exporter` com estado `up`.
- Três regras de alerta válidas e saudáveis.
- Alerta `CreditRiskDriftDetected` observado em `firing`.
- Dashboard Grafana com oito painéis.
- Testes sintáticos e comportamentais das regras Prometheus.

Os totais do dashboard incluem execuções históricas e não
representam exclusivamente os cinco cenários do Bloco 6.

### 17.3. Fairness, governança e limitações

A avaliação offline de fairness utilizou 46.127 registros
rotulados e o threshold fixo do baseline.

Foram avaliadas dimensões de faixa etária, escolaridade
e tipo de renda, com tamanho mínimo de 100 registros por
grupo e denominador condicional mínimo de 20.

Categorias pequenas foram combinadas e tiveram suas
métricas omitidas no relatório agregado.

Essas verificações não demonstram causalidade,
ausência de vieses ou conformidade integral com a LGPD.

A solução permanece acadêmica e não constitui um
sistema produtivo de decisão de crédito.

### 17.4. Documentação da entrega

- [Evidências end-to-end](docs/end-to-end-evidence.md):
  cenários, resultados e reprodução.
- [Guia de entrega final](docs/final-delivery.md):
  matriz FIAP, checklist e pendências.
- [Arquitetura](docs/architecture.md):
  componentes e decisões técnicas.
- [Governança](docs/governance.md):
  privacidade e responsabilidades.
- [Fairness e causalidade](docs/fairness-causality.md):
  auditoria descritiva e limites interpretativos.

### 17.5. Formato da entrega acadêmica

A entrega será realizada mediante dois links:

1. Repositório GitHub:
   https://github.com/Matsal-coder/credit-risk-monitoring
2. Vídeo de apresentação STAR:
   link a fornecer após gravação e publicação.

O roteiro é material auxiliar de produção do vídeo
e não integra os arquivos versionados do projeto.

A integração técnica e documental está concluída.
A produção do vídeo, a auditoria independente final e
a submissão acadêmica permanecem atividades posteriores.

A regressão pós-merge da documentação de evidências
aprovou 378 testes automatizados, além de Ruff,
`pip check` e `docker compose config --quiet`.
