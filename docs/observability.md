# Observabilidade operacional — Bloco 4

## 1. Objetivo e escopo

O Bloco 4 do **Credit Risk Monitoring**, desenvolvido para o Tech Challenge — Fase 4 da Pós-Tech FIAP em Machine Learning Engineering, adiciona rastreabilidade operacional às execuções de scoring e monitoramento de drift. O objetivo é registrar o ciclo de vida das execuções, expor métricas agregadas, coletá-las periodicamente e disponibilizar indicadores para inspeção.

A implementação utiliza **eventos persistidos em SQLite**, **exporter HTTP com Litestar/Uvicorn**, **Prometheus** e **Grafana**, coordenados localmente por **Docker Compose**. Trata-se de uma infraestrutura de observabilidade para demonstração acadêmica, não de uma plataforma de execução contínua ou de monitoramento regulatório em produção.

O Bloco 4 não altera o modelo LogisticRegression, suas 17 features, o threshold oficial `0.1406724340221902`, os contratos Pandera ou o detector Evidently desenvolvidos nos blocos anteriores.

## 2. Arquitetura implementada

```text
CLI de scoring                   CLI de monitoramento de drift
scripts/score_batch.py           scripts/monitor_drift.py
          |                                  |
          +--------------+-------------------+
                         |
              eventos operacionais
                         |
                         v
       artifacts/observability/events.sqlite3
                    (SQLite local)
                         |
                         | consulta de leitura
                         v
            Metrics Exporter (Litestar)
              GET /metrics :8000
                         |
                   scrape a cada 15 s
                         v
                  Prometheus :9090
                         |
                    consultas PromQL
                         v
                   Grafana :3000
         Operations Overview — 8 painéis
```

O registro de eventos ocorre quando as CLIs são executadas com persistência operacional habilitada por `--events-db`. O exporter **não executa scoring ou drift**: consulta os eventos existentes e reconstrói as métricas. A coleta periódica é responsabilidade do Prometheus; não existe agendamento automático das execuções de negócio.

### 2.1. Componentes relevantes

| Componente | Responsabilidade |
|---|---|
| `src/credit_risk_monitoring/observability/events.py` | Contrato do evento operacional e transições de execução |
| `src/credit_risk_monitoring/observability/store.py` | Persistência e leitura de eventos SQLite |
| `src/credit_risk_monitoring/observability/metrics_catalog.py` | Catálogo de famílias métricas e rótulos autorizados |
| `src/credit_risk_monitoring/observability/metrics_aggregation.py` | Agregação dos eventos persistidos |
| `src/credit_risk_monitoring/observability/metrics_exposition.py` | Serialização compatível com o formato texto Prometheus |
| `src/credit_risk_monitoring/observability/metrics_http.py` | Endpoint `GET /metrics` |
| `scripts/serve_metrics.py` | Inicialização local ou em container do exporter |
| `infra/Dockerfile.exporter` | Imagem Python do exporter |
| `compose.yaml` | Serviços e isolamento da stack |
| `infra/prometheus/prometheus.yml` | Scrape, avaliação e carregamento das alert rules |
| `infra/prometheus/alert_rules.yml` | Três alertas automáticos Prometheus |
| `infra/prometheus/alert_rules.test.yml` | Testes temporais com promtool |
| `tests/unit/test_observability_alert_rules.py` | Testes Python de contratos e configuração dos alertas |
| `infra/grafana/provisioning/` | Provisionamento do datasource e do dashboard |
| `infra/grafana/dashboards/operations-overview.json` | Dashboard versionado |

## 3. Registro de eventos operacionais

### 3.1. Persistência e identificação

Os eventos são armazenados no arquivo local:

`artifacts/observability/events.sqlite3`

A persistência é implementada por `SQLiteEventStore`. O histórico pode ser percorrido por `iter_events(chunk_size=500)`, em lotes limitados, preservando a validação de cada evento e uma visão consistente durante a leitura. O SQLite não é versionado pelo Git.

Os eventos registram informações operacionais agregadas, incluindo tipo de pipeline, estado da execução, início, término, duração, resultado de qualidade, resultado de drift quando aplicável, código de saída e contagens relevantes. A rastreabilidade por identificador de execução pertence ao armazenamento operacional; identificadores individuais **não são labels das métricas Prometheus**.

### 3.2. Estados e resultados

Os estados de execução considerados pelo exporter são `running`, `completed` e `failed`. Os resultados de qualidade e drift são dimensões distintas da situação operacional:

- Uma rejeição de qualidade pode encerrar normalmente o processamento da CLI, sem gerar scores, com código de saída `2`.
- Uma execução de monitoramento aprovada pode detectar drift e concluir com código `0`; detectar drift não significa falha operacional.
- Falhas operacionais são registradas como `failed`, com código de saída `1`, quando tratadas pela instrumentação.

O registro operacional não substitui os relatórios JSON/HTML, nem os resultados de validação Pandera.

### 3.3. Execução com registro habilitado

As duas interfaces aceitam a opção `--events-db` para apontar o SQLite de eventos. Ela deve ser utilizada em conjunto com os demais argumentos exigidos por cada CLI. Exemplos completos de scoring e drift, com arquivos e parâmetros de entrada, estão documentados em `docs/reproducibility.md`, `docs/quality-contracts.md` e `docs/drift-monitoring.md`.

Os arquivos de relatório e os identificadores de lote devem ser únicos quando a CLI recusar sobrescrita. Não utilizar dados pessoais em `batch_id`.

## 4. Métricas Prometheus

O exporter oferece **sete famílias métricas**, todas expostas como `gauge`, calculadas a partir do histórico atual do SQLite. Os sufixos `_sum` e `_count` das métricas de duração representam agregados de execução, **não** um objeto `summary` ou `histogram` do Prometheus.

| Família | Labels | Interpretação |
|---|---|---|
| `credit_risk_executions_count` | `pipeline`, `execution_status` | Execuções registradas por pipeline e estado |
| `credit_risk_quality_violations_count` | `pipeline` | Ocorrências agregadas de violações de qualidade |
| `credit_risk_drift_detected_count` | `pipeline` | Execuções que registraram detecção de drift |
| `credit_risk_execution_duration_seconds_sum` | `pipeline` | Soma das durações registradas, em segundos |
| `credit_risk_execution_duration_seconds_count` | `pipeline` | Quantidade de durações registradas |
| `credit_risk_running_executions` | `pipeline` | Execuções ainda registradas como em andamento |
| `credit_risk_last_success_timestamp_seconds` | `pipeline` | Timestamp Unix da última execução concluída com sucesso |

Os pipelines observados são `scoring` e `monitoring`. A duração é agregada para execuções terminadas com duração registrada, incluindo falhas operacionais, mas não execuções ainda em andamento. A família de último sucesso pode não produzir amostra para um pipeline que ainda não tenha uma execução bem-sucedida.

### 4.1. Semântica e limites das métricas

- As contagens são **fotografias cumulativas do histórico persistido**, não contadores incrementados por instrumentação em memória. Por isso, foram definidas como `gauge`.
- Não interpretar as séries temporais do Prometheus como os instantes originais dos eventos. Cada amostra recebe o instante do *scrape*, e eventos anteriores ao início da coleta não são retroativamente reconstruídos como séries históricas.
- A contagem de violações representa **ocorrências de regras violadas**, não necessariamente clientes, linhas ou lotes distintos.
- `running` representa o estado persistido; uma execução interrompida sem transição terminal pode permanecer registrada como em andamento.
- O timestamp de último sucesso não substitui monitoramento de frescor ou disponibilidade com políticas de alerta.
- O exporter evita alta cardinalidade ao não expor `batch_id`, `execution_id`, `SK_ID_CURR`, valores individuais das features ou scores como labels.
- Um erro de leitura do SQLite não deve ser transformado em uma resposta de métricas zeradas: o endpoint retorna erro HTTP, preservando a possibilidade de detectar indisponibilidade pelo `up` do Prometheus.

### 4.2. Consultas PromQL utilizadas

```promql
sum(credit_risk_executions_count)
```

```promql
sum(credit_risk_executions_count{execution_status="failed"})
```

```promql
sum(credit_risk_quality_violations_count)
```

```promql
sum(credit_risk_drift_detected_count)
```

```promql
sum by (pipeline, execution_status) (credit_risk_executions_count)
```

```promql
sum by (pipeline) (credit_risk_execution_duration_seconds_sum)
/
sum by (pipeline) (credit_risk_execution_duration_seconds_count)
```

```promql
credit_risk_running_executions
```

```promql
up{job="credit-risk-exporter"}
```

A média de duração é calculada por quociente de soma de segundos por quantidade de durações. Não aplicar indiscriminadamente `rate()` às contagens históricas do SQLite.

## 5. Exporter HTTP

### 5.1. Execução local

Pré-requisitos: Python 3.12, ambiente virtual do projeto ativado, dependências instaladas e banco SQLite operacional existente.

```bash
python scripts/serve_metrics.py \
  --events-db artifacts/observability/events.sqlite3 \
  --port 8000
```

Por padrão, o serviço escuta somente em `127.0.0.1`. A opção `--host 0.0.0.0` precisa ser informada explicitamente e é utilizada no container para permitir comunicação pela rede interna do Compose. A CLI aceita exclusivamente os dois hosts configurados pelo contrato, evitando endereços arbitrários.

Testar em outro terminal:

```bash
python - <<'PY'
import httpx
r = httpx.get('http://127.0.0.1:8000/metrics', timeout=15)
print(r.status_code)
print(r.text)
r.raise_for_status()
PY
```

O endpoint é apenas de leitura. O conteúdo publicado utiliza o formato texto Prometheus; a compatibilidade foi verificada também com o parser independente de `prometheus-client`.

### 5.2. Falhas de leitura

Se o arquivo SQLite estiver ausente ou não puder ser lido corretamente, `GET /metrics` retorna HTTP `500` em vez de transmitir amostras aparentemente válidas. Não confundir falha do exporter com ausência de eventos; são condições diferentes.

## 6. Stack Docker Compose

### 6.1. Pré-requisitos

- Docker Desktop com Engine Linux acessível (ou ambiente Docker equivalente).
- `docker compose` disponível.
- Diretório local `artifacts/observability/` existente, contendo `events.sqlite3`, para o bind mount do exporter.
- Arquivo local `.env` contendo `GRAFANA_ADMIN_PASSWORD`, não versionado no Git.

O `.dockerignore` exclui datasets, artefatos operacionais, modelos, `.venv` e demais arquivos não necessários à construção. A imagem Python instala dependências **dentro do container**, sem modificar o Python global do Windows.

### 6.2. Serviços e segurança

| Serviço | Imagem/configuração verificada | Acesso |
|---|---|---|
| `exporter` | `infra/Dockerfile.exporter`, Python 3.12 | Somente rede interna, porta `8000/tcp` |
| `prometheus` | `prom/prometheus:v3.16.0` | `127.0.0.1:9090` no host |
| `grafana` | `grafana/grafana:12.2.0` | `127.0.0.1:3000` no host |

O container do exporter executa com `uid=10001`, seu filesystem raiz é configurado como somente leitura e o diretório `artifacts/observability` é montado com `RW=false`. Prometheus e Grafana utilizam volumes nomeados próprios. A retenção do Prometheus está configurada para sete dias.

O Grafana recebe por provisionamento um datasource Prometheus com UID `credit-risk-prometheus` e URL interna `http://prometheus:9090`. O dashboard possui UID `credit-risk-operations`, é versionado em JSON e não requer importação manual.

### 6.3. Inicialização e inspeção

Na raiz do repositório, com o Docker Engine ativo:

```bash
docker compose config --quiet
docker compose config --services
docker compose up --build -d
docker compose ps
docker compose logs --tail=50 exporter
docker compose logs --tail=50 prometheus
docker compose logs --tail=50 grafana
```

A construção da imagem do exporter pode envolver download de dependências Linux. O Docker Compose não gera automaticamente eventos operacionais: o SQLite precisa existir e ser alimentado pelas CLIs instrumentadas.

Interfaces locais:

- Prometheus: `http://127.0.0.1:9090`
- Targets Prometheus: `http://127.0.0.1:9090/targets`
- Grafana: `http://127.0.0.1:3000`
- Dashboard: `http://127.0.0.1:3000/d/credit-risk-operations`

Para interromper a stack sem excluir volumes persistentes:

```bash
docker compose down
```

**Não executar `docker compose down -v`** quando houver interesse em preservar o histórico coletado pelo Prometheus e o banco do Grafana.

### 6.4. Validação do Prometheus no Git Bash/Windows

O Git Bash pode converter incorretamente caminhos internos Linux utilizados pelo Docker. A configuração de scrape pode ser validada com:

```bash
MSYS_NO_PATHCONV=1 docker run --rm \
  --entrypoint /bin/promtool \
  --mount "type=bind,source=$(pwd -W)/infra/prometheus/prometheus.yml,target=/etc/prometheus/prometheus.yml,readonly" \
  prom/prometheus:v3.16.0 \
  check config /etc/prometheus/prometheus.yml
```

O job `credit-risk-exporter` consulta `exporter:8000/metrics` a cada 15 segundos. A configuração inclui `fallback_scrape_protocol: PrometheusText0.0.4` para interoperabilidade com o `Content-Type` retornado pelo endpoint atual.

### 6.5. Credenciais

O arquivo `.env` deve conter `GRAFANA_ADMIN_PASSWORD` com valor forte e exclusivo. Ele é ignorado pelo Git. Não incluir credenciais nos arquivos YAML, screenshots, comandos de depuração compartilhados ou relatórios. A configuração atual é **local**, não uma política completa de autenticação, transporte seguro e gestão de segredos para implantação externa.

## 7. Dashboard Grafana

**Título:** Credit Risk Monitoring - Operations Overview
**UID:** `credit-risk-operations`
**Arquivo:** `infra/grafana/dashboards/operations-overview.json`

O dashboard possui oito painéis:

| Painel | Finalidade |
|---|---|
| Execuções registradas | Total de eventos operacionais por estado |
| Execuções com falha | Execuções em estado `failed` |
| Violações de qualidade | Ocorrências agregadas dos contratos |
| Execuções com drift | Quantidade de eventos que detectaram drift |
| Execuções por status e pipeline | Distribuição temporal dos agregados coletados |
| Duração média por pipeline | Média histórica das durações registradas |
| Execuções em andamento | Estados `running` ainda persistidos |
| Disponibilidade do exporter | Série `up` do job do Prometheus |

Os arquivos de datasource e dashboard são montados em modo somente leitura. A presença do dashboard pode ser verificada por `GET /api/dashboards/uid/credit-risk-operations` na API do Grafana, mediante autenticação local.

## 8. Evidências funcionais observadas

As evidências abaixo foram coletadas em **15/11/2026**, durante o desenvolvimento local da Branch 3, sobre o SQLite operacional com seis eventos. Esses valores não devem ser tratados como invariantes ou métricas de produção.

| Verificação | Resultado observado |
|---|---|
| Eventos persistidos no SQLite | 6 |
| Requisição interna `GET /metrics` | HTTP 200 |
| Amostras expostas pelo exporter | 18 |
| Famílias métricas | 7 |
| Target Prometheus | `health=up`, sem erro de scrape |
| Execuções de scoring concluídas | 3 |
| Execuções de scoring com falha | 1 |
| Execuções de monitoring concluídas | 2 |
| Execuções em andamento | 0 |
| Violações de qualidade | 2 |
| Execuções com drift | 1 |
| Média histórica de duração — monitoring | Aproximadamente 7,947 s |
| Média histórica de duração — scoring | Aproximadamente 0,103 s |
| Disponibilidade Prometheus `up` | 1 |
| Grafana `/api/health` | HTTP 200, banco interno `ok` |
| Datasource provisionado | HTTP 200, UID `credit-risk-prometheus` |
| Dashboard provisionado | HTTP 200, 8 painéis, `provisioned=true` |
| Usuário do exporter | `uid=10001` |
| Bind mount do SQLite | `RW=false` |

Foram observadas execuções instrumentadas de scoring válido e rejeitado, monitoramento controle e forte, além de falha operacional. Uma primeira tentativa de scoring com dados de entrada inadequados foi rejeitada pelo contrato, o que também demonstra a importância de não confundir rejeição de qualidade com falha de infraestrutura.

O Grafana apresentou os indicadores esperados a partir das consultas PromQL. A transição inicial do target `unknown` para `up` ocorreu após o primeiro scrape e não foi tratada como falha.

## 9. Testes automatizados e qualidade

A suíte inclui testes relativos a:

- Contratos de eventos e persistência SQLite.
- Percurso integral do histórico, validação de eventos e tratamento de falhas.
- Catálogo, agregação e serialização de métricas.
- Compatibilidade de exposição com parser independente do Prometheus.
- Endpoint HTTP, atualização entre requisições e falhas do banco.
- Inicialização da CLI do exporter e seleção explícita do host.
- Identidade, datasource, expressões PromQL e segurança do JSON do dashboard.

Comandos de validação, a partir da raiz do repositório e com `.venv` ativa:

```bash
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m pip check
docker compose config --quiet
git diff --check
```

**Resultado consolidado após o merge da Branch 3:** 349 testes aprovados; Ruff lint aprovado; 73 arquivos Python formatados; `pip check` sem conflitos; Docker Compose válido. Commit de integração: `fc48d95` (`merge: complete monitoring infrastructure`). A `main` foi publicada em `origin/main` e a branch funcional local excluída.

### 9.1. Histórico de integração do Bloco 4

| Entrega | Commit de integração |
|---|---|
| Eventos e persistência operacional | `b498bfb` |
| Prometheus Metrics Exporter | `697e60e` |
| Prometheus + Grafana Monitoring Stack | `fc48d95` |

### 9.2. Correção P0 — regras automáticas de alerta (15/11/2026)

**Situação:** funcionamento demonstrado na branch `fix/observability-alert-rules`,
pendente de integração à `main` no momento desta atualização documental.

O Prometheus avalia três regras versionadas em `infra/prometheus/alert_rules.yml`,
referenciadas por `rule_files` em `infra/prometheus/prometheus.yml` e montadas em
modo somente leitura pelo `compose.yaml`. O intervalo de scrape e avaliação é
15 segundos. As regras não definem `for` nem `keep_firing_for`: disparam assim
que a expressão é verdadeira numa avaliação e deixam de disparar quando ela
passa a falsa. A janela de demonstração é de três minutos.

| Regra | Expressão PromQL | Severidade |
|---|---|---|
| `CreditRiskDriftDetected` | `delta(credit_risk_drift_detected_count{pipeline="monitoring"}[3m]) > 0` | warning |
| `CreditRiskOperationalFailure` | `delta(credit_risk_executions_count{execution_status="failed"}[3m]) > 0` | critical |
| `CreditRiskQualityViolation` | `delta(credit_risk_quality_violations_count[3m]) > 0` | warning |

`delta()` foi escolhido para detectar aumento recente nos **gauges de totais
históricos SQLite**, não para estimar a quantidade exata de eventos. As regras
preservam as labels operacionais de baixa cardinalidade (pipeline e, quando
existente, execution_status) e acrescentam `severity` e `category`. Não há
labels com dados pessoais, identificadores de lote ou mensagens de erro.

### Evidências reais da correção

As consultas à API `/api/v1/rules?type=alert` confirmaram as três regras
com `health=ok`; o job `credit-risk-exporter` apresentou `health=up` e
`up=1`. Foram executadas as CLIs instrumentadas com o SQLite local, sem
injeção manual de métricas:

| Situação | Evidência observada em 15/11/2026 (UTC) |
|---|---|
| Controle, sem drift | 46.127 linhas aprovadas; `drift_detected=False`; drift total permaneceu 1; `delta=0`; regra `inactive` |
| Drift forte | Execução aprovada e drift detectado; total 1 → 2; `CreditRiskDriftDetected` em `firing` às 22:55:38 |
| Falha operacional | Duas tentativas reais com `FileExistsError`, `exit_code=1`; `CreditRiskOperationalFailure` em `firing` às 22:56:38 |
| Qualidade | Scoring rejeitado, cinco linhas, `exit_code=2`; violações 2 → 3; `CreditRiskQualityViolation` em `firing` às 23:32:17 |
| Resolução de drift e falha | Ambas as regras `inactive` às 23:30:14 |
| Resolução de qualidade | `firing` às 23:33:23 e `inactive` às 23:35:34; zero alertas ativos |

O histórico do Prometheus forneceu amostras `ALERTS{alertstate="firing"}`
para os três casos. Os horários de resolução exatos não foram determinados:
as consultas comprovam a transição entre observações, não seu segundo preciso.
Os totais são snapshots locais e crescerão em novas demonstrações.

### Testes e inspeção

- `promtool check rules`: `SUCCESS: 3 rules found`.
- `promtool test rules`: `SUCCESS` para séries temporais e estados esperados.
- Testes de contratos de configuração em pytest: **15 aprovados**.
- Regressão integral antes da atualização documental: **364 aprovados**;
  Ruff check, Ruff format, pip check, Docker Compose config e diff check aprovados.
- Endpoints úteis: `/api/v1/targets`, `/api/v1/rules?type=alert`,
  `/api/v1/alerts` e `/api/v1/query_range` em `http://127.0.0.1:9090`.

No Git Bash/Windows, validar as regras sem converter os caminhos do container:

```bash
MSYS_NO_PATHCONV=1 docker run --rm \
  --entrypoint promtool \
  -v "$(pwd -W)/infra/prometheus:/etc/prometheus:ro" \
  prom/prometheus:v3.16.0 \
  check rules /etc/prometheus/alert_rules.yml

MSYS_NO_PATHCONV=1 docker run --rm \
  --entrypoint promtool \
  -v "$(pwd -W)/infra/prometheus:/etc/prometheus:ro" \
  prom/prometheus:v3.16.0 \
  test rules /etc/prometheus/alert_rules.test.yml
```

**Limitações:** a detecção depende de scrapes suficientemente frequentes:
uma mudança que ocorra e seja revertida entre scrapes pode passar despercebida.
As séries refletem o instante da coleta, não o timestamp original dos eventos.
Alterações ou reinicialização do SQLite podem fazer gauges diminuírem; `delta()`
pode ser afetado por lacunas de amostragem e não modela resets como counters.
O primeiro valor histórico após iniciar o Prometheus não constitui, sozinho,
evidência de evento novo. A janela de três minutos foi escolhida para
reprodução local; seu uso em produção exigiria outra política operacional.
Não foram configurados Alertmanager, canais de notificação nem agendamento
das CLIs; o dashboard Grafana existente permanece com oito painéis, sem
provisionamento adicional de alertas no Grafana.

## 10. Segurança, privacidade e limitações

### 10.1. Controles demonstrados

- Dados originais, partições, modelos persistidos, relatórios operacionais e banco SQLite não são versionados no Git.
- O build do exporter exclui diretórios de dados e artefatos pelo `.dockerignore`.
- O exporter no Compose não publica a porta `8000` no host e executa com usuário não privilegiado.
- O volume operacional é montado em somente leitura; Prometheus e Grafana têm volumes próprios.
- Prometheus e Grafana publicam portas somente em `127.0.0.1` no Windows.
- As labels Prometheus são agregadas e não contêm identificadores de clientes ou lotes.
- O Grafana é provisionado a partir de arquivos versionados; a senha fica em `.env` local, ignorado pelo Git.

Esses controles foram demonstrados no cenário local. Não representam, isoladamente, conformidade integral com a LGPD.

### 10.2. Limitações conhecidas

1. **Não existe orquestração contínua de scoring ou drift:** o Prometheus coleta métricas continuamente enquanto a stack está ativa, mas as CLIs de negócio são executadas sob demanda.
2. **Métricas não são eventos históricos retroativos:** a série temporal reflete o instante de coleta; valores já acumulados podem permanecer constantes entre scrapes.
3. **Gauges derivados do SQLite:** contagens podem variar caso o histórico seja alterado; `rate()` e funções destinadas a counters não são automaticamente apropriadas.
4. **Risco de estado `running` obsoleto:** um processo interrompido sem encerramento registrado pode permanecer com estado não terminal.
5. **Alertas sem notificações externas:** três regras de alerta são avaliadas pelo Prometheus e tiveram disparos e resoluções demonstrados localmente; não há Alertmanager, Slack, e-mail ou entrega automática de notificações.
6. **Escopo local:** não foram implementados TLS, autenticação de rede do Prometheus, gestão centralizada de segredos, backup automatizado, alta disponibilidade ou execução multi-host.
7. **Modelo e referência históricos:** resultados de drift referem-se a cenários simulados, sem comprovar concept drift ou degradação de desempenho com novos rótulos.
8. **Retenção assimétrica:** a retenção de sete dias do Prometheus não implica eliminação automática de eventos do SQLite, nem estabelece uma política institucional de retenção.
9. **Dependências sem lockfile integral:** versões dentro das faixas permitidas no `pyproject.toml` podem variar entre instalações; preservar evidências e versões do ambiente em reproduções formais.

A discussão de bases legais, finalidade, retenção, vieses, equidade, causalidade e governança deve ser aprofundada no Bloco 5. A integração de cenários demonstráveis e apresentação final pertence ao Bloco 6.

## 11. Referências internas

- `README.md`: visão geral e roadmap.
- `docs/architecture.md`: decisões arquiteturais e evolução do projeto.
- `docs/reproducibility.md`: preparação, baseline, quality gate e drift.
- `docs/quality-contracts.md`: regras Pandera e rejeição bloqueante.
- `docs/drift-monitoring.md`: simulação, estatísticas e relatórios Evidently.
- `infra/prometheus/prometheus.yml`: coleta das métricas.
- `infra/grafana/dashboards/operations-overview.json`: visualização versionada.
