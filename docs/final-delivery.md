# Entrega final — Credit Risk Monitoring | Tech Challenge FIAP — Fase 4

**Tipo:** guia de entrega e checklist de evidências
**Status deste documento:** preparado para validação na branch `docs/final-delivery-star`
**Escopo:** integração e documentação de uma demonstração acadêmica, não implantação produtiva

> **Estado de aceite:** a integração técnica dos Blocos 0–5 e as evidências operacionais do Bloco 6 foram verificadas nas sessões registradas. O vídeo STAR ainda precisa ser gravado, editado e publicado; a auditoria independente prevista pelo Chat Arquiteto ainda não foi realizada. Não declarar entrega acadêmica integralmente concluída até comprovação desses itens e revisão final.

## 1. Como navegar pela entrega

| Objetivo de quem avalia | Onde encontrar |
|---|---|
| Contexto, setup, comandos e panorama | [README](../README.md) |
| Arquitetura e decisões | [Arquitetura](architecture.md) |
| Reprodução do dataset, baseline e thresholds | [Reprodutibilidade](reproducibility.md) e [ADR-001](decisions/ADR-001-threshold-selection.md) |
| Contratos Pandera, regras e testes | [Contratos de qualidade](quality-contracts.md) |
| Simulações control/moderate/strong e Evidently | [Monitoramento de drift](drift-monitoring.md) |
| SQLite, exporter, Prometheus, alertas e Grafana | [Observabilidade](observability.md) |
| LGPD, minimização e retenção | [Governança](governance.md) |
| Fairness e limitações causais | [Fairness e causalidade](fairness-causality.md) |
| Evidências integradas reproduzidas no Bloco 6 | [Evidências end-to-end](end-to-end-evidence.md) |
| Roteiro audiovisual e plano de captação | roteiro STAR externo ao repositório |

Repositório: <https://github.com/Matsal-coder/credit-risk-monitoring>.

## 2. Matriz de rastreabilidade da rubrica FIAP

| Critério | Peso | Implementação/evidência verificável | Status documental |
|---|---:|---|---|
| Validação de dados | **25%** | Pandera RAW e PREPARED; lote válido (5/5 pontuados, exit 0); lote inválido (`AMT_CREDIT`, regra `positive_credit`, 0/5 pontuados, exit 2); catálogo adicional de regras e testes | Evidência técnica obtida |
| Detecção de drift | **25%** | Evidently; 46.127 registros por cenário; controle **0/16**, moderado **0/16** com 23.063 linhas alteradas, forte **2/16**, 46.127 linhas alteradas; relatórios JSON/HTML locais | Evidência técnica obtida |
| Observabilidade e logs | **20%** | Cinco eventos exclusivos do Bloco 6 no SQLite; exporter `/metrics`; target Prometheus `up`; três regras saudáveis; `CreditRiskDriftDetected` observado em `firing`; oito painéis Grafana | Evidência técnica obtida |
| Governança, LGPD e vieses | **15%** | README com seção autônoma de governança; políticas e limites; fairness offline em 46.127 linhas; agregação e supressão de grupos pequenos | Evidência técnica/documental obtida; sem certificação legal |
| Vídeo STAR e demonstração do impacto | **15%** | roteiro STAR externo ao repositório cronometrado; montagem e publicação dependem de execução externa | **PENDENTE: vídeo real e URL** |

Esta tabela **não representa pontuação atribuída pela FIAP**. A avaliação e os requisitos finais de submissão continuam sujeitos às instruções acadêmicas aplicáveis.

## 3. Evidências reais da integração

### 3.1. Qualidade e inferência

| Batch ID | Resultado | Exit | Linhas pontuadas | Persistência |
|---|---|---:|---:|---|
| `block6-scoring-valid-01` | Pandera RAW/PREPARED `approved` | 0 | 5 | SQLite `completed`, `quality_violations=0` |
| `block6-scoring-invalid-01` | Pandera RAW `rejected` — `AMT_CREDIT`, `positive_credit`, 1 violação | 2 | 0 | SQLite `completed`, `quality_violations=1` |

A rejeição por qualidade **não** é falha operacional; ela bloqueia a inferência. As outras regras constam em [Contratos de qualidade](quality-contracts.md), sem alegar que cada uma tenha sido demonstrada manualmente no Bloco 6.

### 3.2. Drift com seed 642

| Cenário | Registros alterados | Registros pontuados | Features com drift | Estado no SQLite |
|---|---:|---:|---:|---|
| Controle (`block6-drift-control-01`) | 0 | 46.127 | 0/16 | `not_detected`, exit 0 |
| Moderado (`block6-drift-moderate-01`) | 23.063 | 46.127 | 0/16 | `not_detected`, exit 0 |
| Forte (`block6-drift-strong-01`) | 46.127 | 46.127 | **2/16** | `detected`, exit 0 |

No cenário forte, `AMT_CREDIT` e `AMT_INCOME_TOTAL` foram sinalizadas por **Wasserstein distance (normed)**, com limiar **0,1**; `drift_share=0.125` (12,5%). A detecção não prova concept drift, inadimplência futura nem degradação preditiva em ambiente real.

### 3.3. Observabilidade

- Containers `exporter`, `prometheus` e `grafana` observados em execução.
- `GET /metrics` consultado; os sete nomes de métricas agregadas documentados foram expostos.
- API de targets do Prometheus: job `credit-risk-exporter`, `health=up`, sem erro de scrape.
- API de regras: `CreditRiskDriftDetected=firing`, `CreditRiskOperationalFailure=inactive`, `CreditRiskQualityViolation=inactive`; as três com `health=ok` **no instante observado**.
- Dashboard Grafana 12.2.0 acessado por sessão autenticada, com **oito painéis**; valores exibidos incluíam 16 execuções registradas, 3 falhas, 4 violações e 3 execuções com drift.
- Testes Promtool: sintaxe **3 rules found**, testes comportamentais **SUCCESS**. No Git Bash, usar `MSYS_NO_PATHCONV=1` e montar arquivos em modo somente leitura.
- Três falhas operacionais foram consultadas no SQLite como **eventos históricos**, todas `exit_code=1`; não foram reproduzidas novamente no Bloco 6.

**Cuidado com contagens:** os totais do exporter e do dashboard incluem execuções anteriores às cinco novas demonstrações. Não atribuir 16 execuções apenas ao Bloco 6. As regras são baseadas em janela temporal (`delta(gauge[3m]) > 0`); alertas podem estar inativos numa consulta posterior. Não existem notificações externas comprovadas.

### 3.4. Governança e fairness

- Modelo: LogisticRegression, 17 features, threshold persistido **`0.1406724340221902`**.
- Fairness descritiva offline sobre **46.127** registros do teste; **6.623 previsões positivas** (não defaults observados).
- Três dimensões agregadas: faixa etária (4 grupos avaliados), escolaridade (4 avaliados e 1 agrupamento suprimido), tipo de renda (4 avaliados e 1 agrupamento suprimido).
- Grupos pequenos combinados: 27 observações em escolaridade e 8 em tipo de renda, ambos com `metrics=None`. Limiar de grupo: **100**; denominador condicional mínimo: **20**.
- Seis limitações estão no JSON local; análise não estabelece discriminação causal, anonimização formal ou conformidade automática com a LGPD.

## 4. Roteiro de reprodução para avaliador

**Pré-requisitos:** ambiente virtual Python local; dataset e partições processadas; modelo baseline e artefatos locais obtidos pelo fluxo do [README](../README.md) e da [Reprodutibilidade](reproducibility.md); Docker disponível. Nenhum dado, modelo ou evento local é versionado.

### 4.1. Gates do repositório

```bash
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m pip check
docker compose config --quiet
git diff --check
```

**Último resultado observado antes da criação deste documento:** pós-merge `456f6c4`, **378 testes aprovados**, Ruff e pip check aprovados, Compose válido, working tree limpa; `main` publicada e sincronizada com `origin/main`. Uma nova regressão será necessária **após o merge final** da branch `docs/final-delivery-star`.

### 4.2. Subir e verificar infraestrutura

```bash
docker compose up -d
docker compose ps
```

O serviço Prometheus é exposto localmente em `http://127.0.0.1:9090`, e o Grafana em `http://127.0.0.1:3000` (acesso autenticado). A configuração versionada é `compose.yaml`.

### 4.3. Simulações e validação bloqueante

Os comandos completos, com opções e caminhos utilizados, estão em [Evidências end-to-end — seção 11](end-to-end-evidence.md). Para **novas** execuções, atribuir novos `--batch-id` e nomes de saída, porque a CLI pode recusar sobrescritas. Exemplo para simulação forte:

```bash
python scripts/monitor_drift.py \
  --reference data/processed/reference.csv \
  --model artifacts/baseline_model.joblib \
  --batch-id demo-final-strong-unique \
  --json-output artifacts/block6_evidence/demo_final_strong_unique.json \
  --html-output artifacts/block6_evidence/demo_final_strong_unique.html \
  --events-db artifacts/observability/events.sqlite3 \
  simulate \
  --production-prepared data/processed/test.csv \
  --scenario strong \
  --seed 642
```

**Antes de rodar:** verificar se os dois destinos e o batch ID ainda não existem. Não apagar artefatos ou registros para reaproveitar nomes. O cenário forte deve gerar detecção de drift sem falha operacional, conforme a evidência reproduzida nesta sessão.

### 4.4. Promtool compatível com Git Bash/Windows

```bash
MSYS_NO_PATHCONV=1 docker run --rm \
  --mount "type=bind,source=$(pwd -W)/infra/prometheus,target=/workspace,readonly" \
  --entrypoint promtool \
  prom/prometheus:v3.16.0 \
  check rules /workspace/alert_rules.yml

MSYS_NO_PATHCONV=1 docker run --rm \
  --mount "type=bind,source=$(pwd -W)/infra/prometheus,target=/workspace,readonly" \
  --entrypoint promtool \
  prom/prometheus:v3.16.0 \
  test rules /workspace/alert_rules.test.yml
```

Esses comandos usam um container temporário, sem modificar o stack em execução.

## 5. Checklist de publicação e aceite

Legenda: `[x]` comprovado; `[ ]` pendente; `[N/A]` não se aplica ao protótipo acadêmico, sem substituir requisito oficial.

### 5.1. Parte técnica e documental

- [x] Repositório GitHub com histórico de commits semânticos.
- [x] Modelo baseline e partições reproduzíveis documentados.
- [x] Quality gate Pandera RAW/PREPARED e rejeição `exit 2` comprovados.
- [x] Simulações Evidently controle/moderado/forte comprovadas, relatórios JSON/HTML locais existentes.
- [x] Evento SQLite consultado para cada um dos cinco batches exclusivos do Bloco 6.
- [x] Exporter, target Prometheus `up`, regras Promtool válidas.
- [x] Alerta de drift em `firing` observado diretamente; regras de falha/qualidade saudáveis porém inativas naquela consulta.
- [x] Oito painéis Grafana observados em interface autenticada.
- [x] Fairness agregado, limiares de supressão e limitações documentados.
- [x] Seção própria de Governança e Causalidade no README.
- [x] `docs/end-to-end-evidence.md` publicado na `main` no merge `456f6c4`.
- [ ] `docs/final-delivery.md` e referências finais de README/arquitetura integrados à `main` e publicados (a validar nesta branch).
- [ ] Regressão completa e integridade Git após o **último** merge final.

### 5.2. Vídeo e submissão

- [ ] Vídeo STAR **realmente gravado**, duração medida **≤ 5:00**.
- [ ] Imagens/telas utilizadas são capturas reais, com números legíveis e sem alteração que simule resultados.
- [ ] Revisão de privacidade de terminal, abas, HTML e dashboard.
- [ ] Vídeo editado e publicado em URL acessível ao avaliador.
- [ ] Links finais do repositório GitHub e do vídeo publicado verificados e preparados para envio à FIAP.
- [ ] Materiais submetidos pelo usuário no canal/plataforma acadêmica exigido.
- [ ] Auditoria independente read-only por Codex coordenada pelo Chat Arquiteto, se mantida no fluxo de aceite do projeto.

## 6. Segurança na entrega

Não incluir no Git, em screenshots ou no vídeo: dados individuais do Home Credit (`SK_ID_CURR`, `TARGET` por linha, scores individuais), `application_train.csv`, splits, `.env`, senhas/tokens, `kaggle.json`, SQLite integral, modelo `.joblib`, JSON antigo de fairness ou relatórios HTML sem revisão de privacidade. Evitar exibir pastas pessoais, navegador com sessões privadas e credenciais Grafana. Preferir **sumários agregados** e recortes de terminal sem dados pessoais.

A exclusão do Git não garante anonimização nem criptografia. A política de retenção de 30/90 dias é **proposta documental**, sem expurgo automático implementado; o Prometheus possui retenção própria de sete dias, independente do SQLite e do Grafana. A análise de bases legais é contextual, não certificação jurídica.

## 7. Limitações e decisões fora do escopo

- Execução das CLIs de scoring/drift por lotes, **sem agendamento automático**.
- Simulação baseada em partições históricas, sem produção real nem rótulos futuros.
- Ausência de comprovação de concept drift ou deterioração efetiva do modelo em produção.
- Ausência de retreinamento ou mitigação automática de vieses.
- Sem notificações externas de alertas/Alertmanager.
- Fairness é diagnóstico descritivo, não inferência causal nem decisão real de crédito.
- Dados, modelos e artefatos locais devem ser gerados ou obtidos no ambiente de reprodução; não fazem parte dos arquivos públicos versionados.

## 8. Estado de entrega e próximos responsáveis

| Responsabilidade | Estado |
|---|---|
| Desenvolvimento e evidências operacionais do Bloco 6 | Verificados |
| Documentação desta branch e atualização do README | Em preparação/validação |
| Roteiro STAR | Disponibilizado em arquivo separado; produção pendente |
| Gravação/edição/publicação e URL | **Pendente; conduzido fora deste chat** |
| Regressão e publicação pós-merge final | Pendente |
| Relatório final `relatorio_bloco_6.txt` para o Chat Arquiteto | Pendente de consolidação após o merge |
| Auditoria independente final | A cargo do Chat Arquiteto; não realizada neste bloco |

**Critério de comunicação:** após conclusão da documentação técnica, a expressão adequada é **“pronto para gravação”**. Não declarar “vídeo entregue” nem “Tech Challenge totalmente concluído” sem comprovação do vídeo publicado e dos demais passos acadêmicos.
