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

**Importante:** esses componentes representam o escopo global planejado e ainda não estão implementados.

## 3. Tecnologias

### Implementadas na fundação

- Python 3.12
- setuptools
- pytest
- Ruff
- Git e GitHub

### Planejadas para os próximos blocos

- Scikit-Learn — baseline de classificação.
- Pandera — contratos e validação de dados.
- Evidently AI — detecção e relatórios de drift.
- Prometheus — coleta e armazenamento de métricas.
- Grafana — visualização e monitoramento.
- Docker Compose — orquestração local da infraestrutura.

A utilização dessas tecnologias será introduzida conforme a necessidade de cada bloco.

## 4. Dataset

O dataset escolhido é o **Home Credit Default Risk**, disponibilizado no Kaggle.

A implementação começará pelo arquivo `application_train.csv`.

O download, a análise e o tratamento dos dados fazem parte do Bloco 1 e ainda não foram realizados.

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

Atualmente, a suíte contém um smoke test de importação do pacote. Os testes funcionais serão acrescentados conforme as funcionalidades forem implementadas.

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

**Bloco 1 — Dados e Modelo Baseline: em desenvolvimento.**

A primeira etapa do Bloco 1 consiste em proteger datasets e
artefatos locais antes da obtenção dos dados.

O dataset selecionado é Home Credit Default Risk (Kaggle),
iniciando pelo arquivo `application_train.csv`.

Ainda não existe pipeline funcional de treinamento, inferência
ou monitoramento.
