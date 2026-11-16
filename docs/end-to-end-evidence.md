# Evidências End-to-End — Credit Risk Monitoring

## 1. Objetivo e escopo

Este documento consolida a demonstração integrada do projeto **Credit Risk Monitoring**, desenvolvido para o Tech Challenge da Fase 4 da Pós-Tech em Machine Learning Engineering da FIAP.

A demonstração abrange:

1. Contratos de qualidade com Pandera e bloqueio da inferência.
2. Simulação e detecção de *data drift* com Evidently.
3. Eventos operacionais persistidos em SQLite.
4. Exportação de métricas, coleta Prometheus e visualização Grafana.
5. Regras de alerta para drift, falha operacional e qualidade.
6. Governança, fairness agregado, privacidade e limitações.
7. Rastreabilidade dos critérios acadêmicos e reprodutibilidade.

O objetivo é comprovar a integração de componentes existentes. Não foram introduzidas novas funcionalidades nesta etapa.

Os resultados descritos como **observados no Bloco 6** foram obtidos por execuções e consultas locais efetivamente realizadas. Resultados históricos são identificados separadamente.

## 2. Arquitetura integrada

Fluxo funcional:

```text
                 CSV de entrada
                       |
                       v
             Contrato Pandera RAW
                       |
             +---------+---------+
             |                   |
          Aprovado            Rejeitado
             |                   |
             v                   v
       Preparação          Sem inferência
             |              Exit code 2
             v                   |
       Contrato Pandera         |
          PREPARED              |
             |                  |
             v                  |
      Baseline de crédito       |
             |                  |
             +---------+--------+
                       |
                       v
            Evento operacional SQLite
                       |
                       v
                 Exporter
                 GET /metrics
                       |
                       v
                  Prometheus
                       |
              +--------+---------+
              |                  |
              v                  v
         Alert rules           Grafana
```

O monitoramento de drift utiliza referência histórica, produção simulada e Evidently:

```text
Referência histórica + lote de produção simulado
                       |
                       v
                Quality gate
                       |
                       v
              Inferência baseline
                       |
                       v
               Evidently drift
                       |
              +--------+--------+
              |                 |
              v                 v
        JSON / HTML       Evento SQLite
                                |
                                v
                         Observabilidade
```

A detecção de drift, a rejeição por qualidade e a falha operacional possuem semânticas distintas.

## 3. Dados, modelo e reprodutibilidade

Dataset: **Home Credit Default Risk**.

Arquivo principal de origem: `application_train.csv`.

Dimensões historicamente verificadas:

| Partição | Registros |
|---|---:|
| Dataset original | 307.511 |
| Treino | 184.506 |
| Validação | 46.127 |
| Teste | 46.127 |
| Referência | 30.751 |

O pipeline utiliza um baseline `LogisticRegression`, com 17 features de entrada e threshold persistido de `0.1406724340221902`.

A simulação de drift utiliza seed `642`. Nos cenários de drift, foram analisadas 16 features.

A coluna `TARGET` representa o desfecho histórico. Predições positivas não devem ser interpretadas como defaults efetivamente ocorridos.

Detalhes adicionais de preparação, splits, hashes e reprodutibilidade estão em:

- [Reprodutibilidade](reproducibility.md)
- [Arquitetura](architecture.md)
- [Decisão sobre threshold](decisions/ADR-001-threshold-selection.md)

Os CSVs processados, modelos e relatórios locais são artefatos ignorados pelo Git, não arquivos de distribuição do repositório.

## 4. Matriz de rastreabilidade FIAP

| Critério | Peso | Evidências principais | Referências |
|---|---:|---|---|
| Validação e qualidade de dados | 25% | Contratos Pandera RAW/PREPARED, aprovação e rejeição, bloqueio de inferência | `docs/quality-contracts.md`; seção 5 |
| Data drift | 25% | Evidently, três cenários, resultados por feature, JSON e HTML | `docs/drift-monitoring.md`; seção 6 |
| Observabilidade e alertas | 20% | SQLite, exporter, Prometheus, Grafana, regras de alerta | `docs/observability.md`; seções 7 e 8 |
| Governança, privacidade e fairness | 15% | Fairness agregado, supressão, documentação de governança | `docs/governance.md`; `docs/fairness-causality.md`; seção 9 |
| Apresentação e vídeo STAR | 15% | Roteiro e entrega audiovisual planejados para etapa posterior | Seção 12 |

Esta matriz organiza a evidência disponível. Não representa uma nota atribuída pela FIAP nem confirma a aceitação acadêmica da entrega.

## 5. Validação de dados e gate de inferência

### 5.1. Lote válido

Execução reproduzida no Bloco 6:

- Batch ID: `block6-scoring-valid-01`.
- Arquivo: `data/processed/quality_demo/docs_run/valid_batch.csv`.
- Registros recebidos: 5.
- Registros pontuados: 5.
- Status: `approved`.
- Exit code: `0`.
- Validação RAW: `approved`, zero violações.
- Validação PREPARED: `approved`, zero violações.
- Threshold: `0.1406724340221902`.

Relatório local: `artifacts/block6_evidence/scoring_valid_report.json`.

O processamento foi registrado em SQLite com:

- `pipeline=scoring`;
- `execution_status=completed`;
- `quality_status=approved`;
- `quality_violations=0`;
- `scored_rows=5`;
- `exit_code=0`;
- `drift_status=not_evaluated`.

### 5.2. Lote inválido

Execução reproduzida no Bloco 6:

- Batch ID: `block6-scoring-invalid-01`.
- Arquivo: `data/processed/quality_demo/docs_run/invalid_batch.csv`.
- Registros recebidos: 5.
- Registros pontuados: 0.
- Status: `rejected`.
- Exit code: `2`.
- Estágio de rejeição: `raw_inference`.
- Coluna: `AMT_CREDIT`.
- Regra: `positive_credit`.
- Ocorrências: 1.
- Severidade: `error`.

Relatório local: `artifacts/block6_evidence/scoring_invalid_report.json`.

O evento SQLite confirmou:

- `pipeline=scoring`;
- `execution_status=completed`;
- `quality_status=rejected`;
- `quality_violations=1`;
- `scored_rows=0`;
- `exit_code=2`;
- `drift_status=not_evaluated`.

A rejeição por qualidade foi uma execução operacionalmente concluída, e não uma falha de infraestrutura.

### 5.3. Cobertura dos contratos

O catálogo completo dos contratos RAW e PREPARED, suas regras e testes está documentado em [Contratos de qualidade](quality-contracts.md).

Entre os controles implementados estão:

- `AMT_CREDIT > 0`: `positive_credit`;
- `CNT_CHILDREN >= 0`: `nonnegative_children`;
- `EXT_SOURCE_2` e `EXT_SOURCE_3` dentro de `[0,1]`: `external_score_range`;
- obrigatoriedade de colunas;
- validação do indicador derivado `DAYS_EMPLOYED_SENTINEL`.

A demonstração manual acima comprova especificamente a regra `positive_credit`. As demais regras possuem cobertura documentada e testes automatizados; não foram todas reexecutadas manualmente nesta etapa.

## 6. Simulação e detecção de drift

As execuções utilizaram:

- Referência: `data/processed/reference.csv`.
- Produção simulada: `data/processed/test.csv`.
- Baseline: `artifacts/baseline_model.joblib`.
- Seed: `642`.
- Total por lote: 46.127 registros.
- Features analisadas: 16.
- Quality gate aprovado nos três cenários.
- Persistência de eventos habilitada em SQLite.

### 6.1. Resultados reproduzidos

| Cenário | Batch ID | Registros alterados | Pontuados | Features com drift | Drift share | Exit |
|---|---|---:|---:|---:|---:|---:|
| Controle | `block6-drift-control-01` | 0 | 46.127 | 0/16 | 0.0 | 0 |
| Moderado | `block6-drift-moderate-01` | 23.063 | 46.127 | 0/16 | 0.0 | 0 |
| Forte | `block6-drift-strong-01` | 46.127 | 46.127 | 2/16 | 0.125 | 0 |

Todos os três cenários foram executados no Bloco 6. A existência dos arquivos JSON e HTML foi confirmada posteriormente em cada cenário.

Os três eventos operacionais também foram encontrados individualmente no SQLite, com `execution_status=completed` e `exit_code=0`.

### 6.2. Alterações simuladas

Cenário controle:

- Nenhuma alteração artificial.

Cenário moderado:

- Redução de 10% em `AMT_INCOME_TOTAL`.
- Aumento de 10% em `AMT_CREDIT`.
- Alterações aplicadas a aproximadamente 50% do lote.
- Resultado observado: nenhuma feature sinalizada.

Cenário forte:

- Redução de 20% em `AMT_INCOME_TOTAL`.
- Aumento de 25% em `AMT_CREDIT`.
- Alterações aplicadas a 100% do lote.
- Resultado observado: duas features sinalizadas.

### 6.3. Features sinalizadas no cenário forte

| Feature | Drift detectado | Método estatístico | Threshold |
|---|---|---|---:|
| `AMT_CREDIT` | Sim | Wasserstein distance (normed) | 0.1 |
| `AMT_INCOME_TOTAL` | Sim | Wasserstein distance (normed) | 0.1 |

O JSON do cenário forte confirmou:

- `drift_detected=true`;
- `drift_share=0.125`;
- `features_analyzed=16`;
- `features_drifted=2`;
- 16 resultados individuais de features.

O evento SQLite confirmou `drift_status=detected`.

### 6.4. Artefatos locais

| Cenário | JSON | HTML |
|---|---|---|
| Controle | `artifacts/block6_evidence/drift_control.json` | `artifacts/block6_evidence/drift_control.html` |
| Moderado | `artifacts/block6_evidence/drift_moderate.json` | `artifacts/block6_evidence/drift_moderate.html` |
| Forte | `artifacts/block6_evidence/drift_strong.json` | `artifacts/block6_evidence/drift_strong.html` |

Os relatórios não estão versionados e devem ser regenerados localmente para reprodução independente.

### 6.5. Interpretação e limites

Alteração artificial de dados não implica necessariamente drift estatístico detectado.

O cenário moderado alterou 23.063 registros e apresentou zero features sinalizadas pelos critérios configurados.

O cenário forte apresentou duas features sinalizadas. Isso não comprova deterioração de performance preditiva nem mudança causal do risco de crédito.

A demonstração utiliza dados históricos particionados e cenários sintéticos, não tráfego real de produção.

Detalhes: [Monitoramento de drift](drift-monitoring.md).

## 7. Eventos operacionais e observabilidade

### 7.1. Persistência SQLite

Banco local: `artifacts/observability/events.sqlite3`.

Tabela inspecionada: `operational_events`.

Colunas identificadas:

- `execution_id`;
- `batch_id`;
- `execution_status`;
- `started_at`;
- `finished_at`;
- `payload`.

Foram encontrados os cinco eventos dos batch IDs exclusivos desta demonstração, um para cada identificador consultado:

- `block6-scoring-valid-01`;
- `block6-scoring-invalid-01`;
- `block6-drift-control-01`;
- `block6-drift-moderate-01`;
- `block6-drift-strong-01`.

As consultas foram feitas em modo somente leitura, sem expor linhas individuais de crédito.

### 7.2. Serviços

A consulta `docker compose ps` confirmou ativos:

- `exporter`;
- `prometheus`;
- `grafana`.

Versões observadas:

- Prometheus `3.16.0`;
- Grafana `12.2.0`.

A composição versionada está em `compose.yaml`.

### 7.3. Exporter

Endpoint interno consultado: `http://exporter:8000/metrics`.

Métricas observadas:

- `credit_risk_executions_count`;
- `credit_risk_quality_violations_count`;
- `credit_risk_drift_detected_count`;
- `credit_risk_execution_duration_seconds_sum`;
- `credit_risk_execution_duration_seconds_count`;
- `credit_risk_running_executions`;
- `credit_risk_last_success_timestamp_seconds`.

Totais observados na consulta integrada:

| Indicador | Monitoring | Scoring |
|---|---:|---:|
| Execuções concluídas | 7 | 6 |
| Execuções com falha | 2 | 1 |
| Execuções em andamento | 0 | 0 |
| Violações de qualidade | 0 | 4 |
| Execuções com drift detectado | 3 | 0 |
| Durações registradas | 9 | 7 |

Os números representam o histórico acumulado do SQLite, incluindo execuções anteriores ao Bloco 6.

`credit_risk_drift_detected_count` conta execuções com drift detectado, não features individuais.

As métricas de contagem expostas nesta implementação possuem tipo Prometheus `gauge`.

### 7.4. Prometheus

API consultada: `http://127.0.0.1:9090/api/v1/targets`.

Resultado observado:

- Job: `credit-risk-exporter`;
- Health: `up`;
- Last error: vazio;
- Scrape URL: `http://exporter:8000/metrics`;
- Targets ativos: 1.

Isso comprova a disponibilidade do exporter para o Prometheus no instante da verificação.

## 8. Alertas Prometheus e Grafana

### 8.1. Regras de alerta

API consultada: `http://127.0.0.1:9090/api/v1/rules`.

Estados observados no Bloco 6:

| Regra | Estado | Health | Alertas ativos |
|---|---|---|---:|
| `CreditRiskDriftDetected` | firing | ok | 1 |
| `CreditRiskOperationalFailure` | inactive | ok | 0 |
| `CreditRiskQualityViolation` | inactive | ok | 0 |

A verificação ocorreu após as simulações de drift.

O estado `firing` da regra de drift foi observado diretamente na API Prometheus.

As regras utilizam janelas temporais, incluindo `delta(gauge[3m]) > 0`, de modo que seus estados mudam com a evolução das amostras coletadas.

A evidência representa um instante de observação, não garantia de disparo permanente.

As regras de falha operacional e qualidade estavam carregadas e saudáveis, mas inativas nessa consulta.

O projeto não comprova notificações externas via Alertmanager, e-mail ou outros canais.

### 8.2. Falhas operacionais históricas

Consulta read-only ao SQLite encontrou três eventos históricos com:

- `execution_status=failed`;
- `exit_code=1`.

Dois eventos de monitoring:

- Batch ID `alert-strong-20261115`;
- Erro `FileExistsError`.

Um evento de scoring:

- Batch ID `obs-operational-failure-001`;
- Erro `FileNotFoundError`.

Os dois eventos com o mesmo batch ID são ocorrências distintas, não dois lotes exclusivos.

Essas falhas foram consultadas como evidência histórica; não foram reproduzidas novamente no Bloco 6.

### 8.3. Grafana

API `/api/health`:

- `database=ok`;
- `version=12.2.0`.

Consulta anônima a `/api/search?type=dash-db` retornou HTTP 401, por exigir autenticação.

A interface autenticada foi posteriormente acessada e foram visualizados oito painéis:

1. Execuções registradas.
2. Execuções com falha.
3. Violações de qualidade.
4. Execuções com drift.
5. Execuções por status e pipeline.
6. Duração média por pipeline.
7. Execuções em andamento.
8. Disponibilidade do exporter.

Indicadores apresentados na captura da interface:

- Execuções registradas: 16.
- Execuções com falha: 3.
- Violações de qualidade: 4.
- Execuções com drift: 3.
- Disponibilidade do exporter: série em 1.

Os valores incluem eventos históricos e não devem ser atribuídos exclusivamente às cinco execuções do Bloco 6.

A captura foi verificada na sessão do executor. Este documento não embute imagem nem publica credenciais.

Documentação de referência: [Observabilidade](observability.md).

## 9. Fairness, privacidade e governança

### 9.1. Artefato agregado

Arquivo local: `artifacts/fairness_test_aggregated.json`.

Sua existência, leitura como JSON e exclusão do versionamento Git foram confirmadas.

Indicadores observados:

- Base de teste: 46.127 registros.
- Threshold: `0.1406724340221902`.
- Classificações positivas previstas: 6.623.
- Tamanho mínimo para avaliar um grupo: 100.
- Denominador condicional mínimo: 20.
- Limitações documentadas: 6.

As 6.623 classificações positivas representam predições do baseline, não defaults observados.

### 9.2. Dimensões e supressão

| Dimensão | Grupos avaliados | Grupos pequenos combinados |
|---|---:|---:|
| Faixa etária | 4 | 0 |
| Escolaridade | 4 | 1 |
| Tipo de renda | 4 | 1 |

O agrupamento de escolaridade possui 27 registros, e o agrupamento de tipo de renda possui 8 registros.

Em ambos os casos:

- `status=small_groups_combined`;
- `metrics=None`.

Logo, não foram publicadas métricas individuais para esses agrupamentos no artefato inspecionado.

Os menores tamanhos entre grupos avaliados foram:

- Faixa etária: 5.306;
- Escolaridade: 558;
- Tipo de renda: 3.264.

Para os grupos com `status=evaluated`, não foram encontrados valores nulos de `precision`, `recall_tpr` ou `fpr` na inspeção realizada.

O relatório contempla métricas agregadas de classificação, inclusive prevalência, taxa de classificação positiva, precision, recall/TPR e FPR.

### 9.3. Limites interpretativos

A análise é descritiva e condicionada ao dataset, ao modelo, ao threshold e aos grupos definidos.

Não demonstra:

- ausência de viés;
- equidade causal;
- ausência de discriminação em produção;
- anonimato garantido;
- conformidade automática com a LGPD.

A presença de regras de supressão é um controle de redução de exposição, não certificação completa de privacidade.

Referências:

- [Governança](governance.md)
- [Fairness e causalidade](fairness-causality.md)

## 10. Semântica de resultados operacionais

| Situação | Exit code | Estado operacional | Efeito |
|---|---:|---|---|
| Lote válido | 0 | completed | Inferência permitida |
| Drift detectado | 0 | completed | Sinalização estatística |
| Rejeição por qualidade | 2 | completed | Inferência bloqueada |
| Falha operacional | 1 | failed | Erro registrado |

A correspondência foi verificada por execuções atuais dos códigos 0 e 2 e por eventos históricos do código 1.

Nenhum desses estados deve ser confundido com a ocorrência efetiva de default financeiro.

## 11. Procedimento de reprodução

### 11.1. Pré-requisitos

- Repositório clonado e ambiente Python configurado.
- Dependências instaladas no ambiente virtual local.
- Dados processados disponíveis.
- Modelo baseline disponível.
- Docker Desktop operacional para observabilidade.

Arquivos locais utilizados:

```text
data/processed/reference.csv
data/processed/test.csv
data/processed/quality_demo/docs_run/valid_batch.csv
data/processed/quality_demo/docs_run/invalid_batch.csv
artifacts/baseline_model.joblib
artifacts/observability/events.sqlite3
```

Esses arquivos não são publicados no repositório Git.

Para reconstruir os pré-requisitos, seguir o README e [Reprodutibilidade](reproducibility.md).

### 11.2. Subir a observabilidade

```bash
docker compose up -d
docker compose ps
```

A configuração efetiva pode ser verificada com:

```bash
docker compose config --quiet
```

### 11.3. Executar scoring válido

```bash
mkdir -p artifacts/block6_evidence

python scripts/score_batch.py \
  --input data/processed/quality_demo/docs_run/valid_batch.csv \
  --batch-id block6-scoring-valid-01 \
  --model artifacts/baseline_model.joblib \
  --events-db artifacts/observability/events.sqlite3 \
  --report-output artifacts/block6_evidence/scoring_valid_report.json
```

Resultado observado: exit 0, lote aprovado e 5 registros pontuados.

### 11.4. Executar scoring inválido

```bash
python scripts/score_batch.py \
  --input data/processed/quality_demo/docs_run/invalid_batch.csv \
  --batch-id block6-scoring-invalid-01 \
  --model artifacts/baseline_model.joblib \
  --events-db artifacts/observability/events.sqlite3 \
  --report-output artifacts/block6_evidence/scoring_invalid_report.json
```

Resultado observado: exit 2, lote rejeitado e 0 registros pontuados.

### 11.5. Executar simulações de drift

Exemplo do cenário forte:

```bash
python scripts/monitor_drift.py \
  --reference data/processed/reference.csv \
  --model artifacts/baseline_model.joblib \
  --batch-id block6-drift-strong-01 \
  --json-output artifacts/block6_evidence/drift_strong.json \
  --html-output artifacts/block6_evidence/drift_strong.html \
  --events-db artifacts/observability/events.sqlite3 \
  simulate \
  --production-prepared data/processed/test.csv \
  --scenario strong \
  --seed 642
```

Para reproduzir controle e moderado, utilizar `--scenario control` ou `--scenario moderate` e adaptar batch ID e caminhos de relatório.

Os resultados observados constam da seção 6.

**Atenção:** estes comandos documentam as execuções efetivamente realizadas. Para uma nova reprodução, usar batch IDs e destinos de saída novos, evitando sobrescrita de artefatos existentes e ambiguidades na identificação dos eventos.

### 11.6. Consultar observabilidade

```bash
docker compose ps
```

Acessar localmente:

- Prometheus: `http://127.0.0.1:9090`;
- Grafana: `http://127.0.0.1:3000`.

API Prometheus:

- `/api/v1/targets`;
- `/api/v1/rules`.

O Grafana exige a autenticação configurada no ambiente.

### 11.7. Verificações automatizadas

A regressão completa deve ser executada antes do merge final da branch:

```bash
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m pip check
docker compose config --quiet
git diff --check
```

Prometheus deve ser validado também com os comandos `promtool` estabelecidos em [Observabilidade](observability.md).

As evidências da regressão final desta branch serão registradas na entrega depois de executadas. Este documento não antecipa resultados ainda não obtidos.

## 12. Entrega acadêmica e vídeo STAR

A demonstração integrada fornece uma base factual para o roteiro do vídeo STAR.

Estrutura prevista:

- **Situation:** necessidade de monitorar a confiabilidade de um pipeline de risco de crédito.
- **Task:** implementar qualidade, drift, observabilidade e controles de governança.
- **Action:** demonstrar validação Pandera, simulações Evidently, métricas, alertas e fairness agregado.
- **Result:** apresentar resultados observados, reprodutibilidade e limitações.

O roteiro detalhado será elaborado em etapa específica da entrega final.

A gravação, edição e publicação do vídeo serão realizadas fora deste chat executor.

Nenhum link de vídeo publicado foi confirmado durante a preparação desta evidência.

## 13. Limites e pendências

1. Os dados utilizados são históricos; os cenários de drift são simulados.
2. Não existe comprovação de monitoramento contínuo de um sistema real de crédito em produção.
3. O alerta de drift foi observado em `firing` em um instante específico, não continuamente.
4. Não foi comprovado envio externo de notificações.
5. Os totais do SQLite e Grafana incluem eventos anteriores ao Bloco 6.
6. As falhas operacionais foram verificadas em eventos históricos; não foram recriadas nesta etapa.
7. Fairness é analisado por métricas agregadas, sem inferência causal nem certificação LGPD.
8. Os artefatos locais ignorados pelo Git precisam ser gerados ou disponibilizados no ambiente de reprodução.
9. O vídeo STAR permanece pendente de roteiro, produção e publicação em etapa posterior.
10. O resultado da regressão final desta branch ainda precisa ser anexado ao relatório de entrega.

## 14. Documentação relacionada

- [README](../README.md)
- [Arquitetura](architecture.md)
- [Reprodutibilidade](reproducibility.md)
- [Contratos Pandera](quality-contracts.md)
- [Monitoramento de drift](drift-monitoring.md)
- [Observabilidade](observability.md)
- [Governança](governance.md)
- [Fairness e causalidade](fairness-causality.md)
- [ADR-001: seleção de threshold](decisions/ADR-001-threshold-selection.md)

---

Documento de consolidação das evidências de integração do Bloco 6. Os resultados representam observações realizadas no ambiente local do projeto.
