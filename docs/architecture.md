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

Ao final das etapas de fundação e qualidade do Bloco 0, existem:

- Um pacote Python denominado `credit_risk_monitoring`, organizado sob `src/`.
- Configuração de empacotamento pelo `pyproject.toml`.
- Ambiente virtual Python local `.venv`.
- Instalação editável do pacote.
- pytest configurado.
- Ruff configurado para lint e formatação.
- Um smoke test de importação.
- Versionamento Git com commits semânticos.

Ainda não existem:

- Dataset processado.
- Pipeline de treinamento.
- Modelo treinado ou serializado.
- Contratos Pandera.
- Pipeline de inferência.
- Detecção de drift.
- Exportador de métricas.
- Serviços Prometheus ou Grafana.
- Infraestrutura Docker Compose.
- Rotinas de monitoramento em produção.

A descrição dos próximos componentes não representa sua implementação.

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

O próximo bloco será responsável por introduzir o dataset Home Credit, realizar sua preparação e construir o primeiro baseline de classificação.

O Bloco 1 deverá utilizar a fundação existente e evitar alterações desnecessárias nas decisões de empacotamento, testes e fluxo Git.

As interfaces e os caminhos dos novos componentes deverão ser definidos durante sua implementação e registrados na documentação.
