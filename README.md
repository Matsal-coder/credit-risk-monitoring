# Credit Risk Monitoring

Projeto desenvolvido para o **Tech Challenge — Fase 4 da Pós-Tech FIAP em Machine Learning Engineering**, com foco em monitoramento contínuo, qualidade de dados, detecção de drift, observabilidade e governança de modelos de Machine Learning.

## 1. Contexto

O projeto simula um cenário de uma fintech que utiliza um modelo de classificação de risco de crédito.

O objetivo é desenvolver uma solução capaz de identificar problemas de qualidade nos dados recebidos, alterações nas distribuições das variáveis e possíveis sinais de degradação do modelo em produção.

A implementação será incremental, com validação dos componentes antes de sua integração.

## 2. Escopo funcional planejado

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

**Importante:** esta lista representa o escopo global do projeto. Os Blocos 0 e 1 estão concluídos, e os componentes funcionais do Bloco 2 já foram implementados. Drift, observabilidade, governança consolidada e integração final permanecem planejados.
## 3. Tecnologias

### Implementadas

- Python 3.12.
- pandas e NumPy — manipulação e preparação dos dados.
- Scikit-Learn — preprocessamento e modelo baseline.
- joblib — persistência do pipeline treinado.
- Pandera — contratos e validação bloqueante de dados.
- setuptools — empacotamento.
- pytest — testes unitários e de integração.
- Ruff — lint e formatação.
- Git e GitHub — controle de versões.

### Planejadas para os próximos blocos

- Evidently AI e testes estatísticos — detecção de drift.
- Prometheus — coleta de métricas.
- Grafana — visualização de indicadores.
- Docker Compose — infraestrutura local de observabilidade.

A inclusão de uma tecnologia no planejamento não significa
que ela já esteja instalada ou operacional.

Os contratos Pandera e a inferência bloqueante foram
implementados no Bloco 2. A observabilidade e a
detecção de drift permanecem fora do escopo concluído.

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

```text
TechChallenge - Fase 4/
├── docs/
│   └── architecture.md
├── src/
│   └── credit_risk_monitoring/
│       └── __init__.py
├── tests/
│   └── unit/
│       └── test_package.py
├── .gitignore
├── pyproject.toml
└── README.md
```

Esta estrutura corresponde ao estado versionado após a conclusão do Bloco 0. Os diretórios de dados e artefatos serão criados conforme as etapas do Bloco 1 forem implementadas.

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

A suíte inclui testes unitários e de integração de preparação, treinamento, contratos de qualidade e inferência. Após a integração funcional do Bloco 2, foram aprovados 114 testes automatizados.

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

As decisões arquiteturais e os contratos planejados estão documentados em docs/architecture.md, criado durante o Bloco 0 e atualizado conforme a evolução do projeto.

O projeto utiliza uma abordagem incremental, evitando antecipar dependências e infraestrutura que ainda não possuem utilização prática.

## 11. Estado atual

### Resumo consolidado

Estado verificado após a integração funcional do Bloco 2:

| Bloco | Estado |
|---|---|
| 0 — Fundação e arquitetura | Concluído |
| 1 — Dados e baseline | Concluído |
| 2 — Contratos e inferência bloqueante | Implementação concluída; documentação em andamento |
| 3 — Simulação e detecção de drift | Não iniciado |
| 4 — Observabilidade | Não iniciado |
| 5 — Governança e privacidade | Não iniciado |
| 6 — Integração e demonstração | Não iniciado |

O baseline utiliza LogisticRegression com 17 features,
e o threshold oficial é `0.1406724340221902`.

O Bloco 2 implementou contratos Pandera para dados
brutos e preparados, validação estruturada de lotes,
preparação sem TARGET, inferência bloqueante e
interface operacional de scoring.

Na última validação funcional integrada à main:

- 114 testes automatizados foram aprovados.
- Ruff lint e formatação foram aprovados.
- pip check não identificou conflitos.
- O modelo persistido produziu scores consistentes.
- Lotes inválidos foram rejeitados sem produzir scores.

Referências técnicas:

- [Arquitetura](docs/architecture.md).
- [Contratos de qualidade](docs/quality-contracts.md).
- [Reprodutibilidade](docs/reproducibility.md).

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
ainda não foram implementados.

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
serão implementados no pipeline do modelo,
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

O Bloco 3 utilizará a referência histórica
e os mecanismos de inferência já implementados
para construir cenários de produção simulada.
