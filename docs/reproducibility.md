# Guia de reprodutibilidade — Blocos 1 a 4

## 1. Objetivo

Este documento descreve como reproduzir os Blocos 1 a 4
do projeto Credit Risk Monitoring.

O Bloco 1 contempla preparação, particionamento,
treinamento, avaliação e persistência do baseline.

O Bloco 2 acrescenta contratos Pandera, preparação
de lotes sem TARGET, validação bloqueante e
inferência operacional com o modelo persistido.

O Bloco 3 acrescenta simulação de produção,
detecção estatística de drift com Evidently
e relatórios operacionais JSON e HTML.

O Bloco 4 acrescenta eventos operacionais em SQLite,
exporter HTTP, coleta Prometheus e dashboards Grafana.

Os resultados históricos do baseline são preservados.
O Bloco 2 não realiza retreinamento nem reajusta
o threshold selecionado na validação.

Escopo reproduzido:

- Inspeção do Home Credit Default Risk.
- Preparação e particionamento determinísticos.
- Verificação de integridade dos dados.
- Treinamento do baseline Logistic Regression.
- Seleção do threshold por maximização do F1.
- Avaliação independente no teste.
- Persistência do pipeline e dos resultados.
- Inferência sobre a referência não rotulada.

Os contratos Pandera e a inferência bloqueante
foram implementados no Bloco 2.

O projeto implementa detecção de drift por lotes e
observabilidade com Prometheus/Grafana, mas ainda não
agenda automaticamente execuções de scoring e drift.
A coleta contínua de métricas não equivale à execução
contínua dos pipelines de negócio.

## 2. Ambiente

Ambiente utilizado na execução de referência:

- Sistema operacional: Windows.
- Terminal: Git Bash.
- Python: 3.12.2.
- pandas: 2.3.3.
- numpy: 2.5.4.
- scikit-learn: 1.9.1.
- joblib: 1.6.0.
- Pandera: 0.35.0.

O projeto utiliza ambiente virtual local `.venv`.

As dependências estão declaradas no `pyproject.toml`.
Algumas utilizam intervalos de versões; Evidently 0.7.23
e Litestar 2.22.0 possuem versões explicitamente fixadas.
O projeto não utiliza um lockfile completo.

Consequentemente, uma instalação futura pode utilizar
versões compatíveis, mas diferentes das registradas
na execução original.

### 2.1. Preparação do ambiente

Na raiz do repositório:

```bash
py -3.12 -m venv .venv
source .venv/Scripts/activate
python -m pip install -e ".[dev]"
python -m pip check
```

O comando `py -3.12` pressupõe a disponibilidade
do Python Launcher no Windows.

Confirmar o ambiente:

```bash
python --version
python -m pip --version
python -m pip show credit-risk-monitoring
```

As bibliotecas devem ser instaladas exclusivamente
na `.venv`, nunca no Python global.

## 3. Dataset

Dataset: Home Credit Default Risk.

Arquivo original esperado:

`data/raw/application_train.csv`

A obtenção dos dados está descrita no README,
na seção de dataset.

O arquivo original não é armazenado no Git.

Na execução de referência foram utilizados
307.511 registros e 122 colunas originais.

A variável TARGET indica inadimplência segundo
a definição do dataset.

SK_ID_CURR identifica a operação e não é utilizado
como variável preditiva.

O projeto utiliza 17 features preditivas:

- 11 numéricas.
- 5 categóricas.
- 1 indicador derivado de sentinela.

O valor especial DAYS_EMPLOYED = 365243 é tratado
pela preparação, com indicador específico.

Os contratos e nomes das features estão definidos
em `credit_risk_monitoring.data.preparation`.

## 4. Inspeção e preparação

### 4.1. Inspeção

```bash
python scripts/inspect_dataset.py
```

O processo realiza a inspeção exploratória prevista
para o dataset original.

### 4.2. Preparação

```bash
python scripts/prepare_dataset.py
```

A preparação utiliza particionamento aleatório
estratificado, com seed padrão 42.
A seed efetivamente utilizada na geração histórica
dos CSVs locais não foi comprovada nesta revisão.

Distribuição:

| Partição | Registros | Proporção |
|---|---:|---:|
| Train | 184.506 | 60% |
| Validation | 46.127 | 15% |
| Test | 46.127 | 15% |
| Reference | 30.751 | 10% |

As proporções são aproximadas após arredondamento
para números inteiros de registros.

Os arquivos são armazenados em `data/processed/`.

Train, validation e test possuem TARGET.

Reference não possui TARGET.

As partições são disjuntas em SK_ID_CURR.

A referência é uma amostra histórica aleatória
e não um lote temporal de produção.

## 5. Integridade

Executar:

```bash
python scripts/verify_dataset.py
```

O verificador compara os arquivos preparados com
o manifesto de dados.

Manifesto:

`artifacts/data_manifest.json`

Na execução validada, os quatro arquivos passaram
pela verificação de integridade.

Os prefixos dos hashes SHA256 observados foram:

| Partição | Prefixo SHA256 |
|---|---|
| Train | 508e938eafe20416 |
| Validation | d4a2437ceaa76628 |
| Test | edfa3747a8e9796f |
| Reference | e0fd6a0f3933de29 |

Os valores acima são prefixos para conferência;
o manifesto contém os hashes completos.

A reprodução dos mesmos hashes pressupõe
os mesmos dados de origem, lógica de preparação
e comportamento compatível das dependências.

## 6. Modelo baseline

Modelo: Logistic Regression do Scikit-Learn.

Configuração:

- solver: lbfgs.
- max_iter: 1000.
- class_weight: None.
- random_state: 42.

Preprocessamento:

- Numéricas: imputação pela mediana e StandardScaler.
- Categóricas: imputação pela moda e OneHotEncoder.
- Indicador derivado: passthrough, sem normalização.

O preprocessamento é ajustado somente no treino.

A implementação utiliza Pipeline para manter
o preprocessamento e o classificador integrados.

A variável TARGET e o identificador SK_ID_CURR
não são utilizados como preditores.

## 7. Treinamento e seleção do threshold

Para realizar o diagnóstico na validação:

```bash
python scripts/train_baseline.py
```

A estratégia oficial de seleção do threshold
é a maximização do F1-score na validação.

Threshold selecionado:

`0.1406724340221902`

A motivação, limitações e alternativas econômicas
estão documentadas em:

`docs/decisions/ADR-001-threshold-selection.md`

O threshold padrão de 0,50 é mantido apenas
como benchmark comparativo.

## 8. Avaliação final e persistência

O procedimento de avaliação utiliza:

1. Train para ajustar o pipeline.
2. Validation para selecionar o threshold.
3. Test para avaliar a política já fixada.

O conjunto de teste não é utilizado para selecionar
features, hiperparâmetros ou threshold.

Com o modelo e a política congelados, executar:

```bash
python scripts/verify_dataset.py
python scripts/finalize_baseline.py
```

A execução gera:

- `artifacts/baseline_model.joblib`
- `artifacts/baseline_metrics.json`

O primeiro arquivo contém o pipeline treinado
e os metadados da execução.

O segundo contém os resultados de validação,
teste e diagnósticos de treinamento.

O comando de finalização pode reproduzir a
avaliação original, mas os resultados do teste
não devem ser utilizados para novos ajustes
retrospectivos da política.

### 8.1. Resultados de referência

| Métrica | Validação | Teste |
|---|---:|---:|
| ROC-AUC | 0.734523 | 0.736332 |
| Average Precision | 0.218251 | 0.214999 |
| Precision | 0.226404 | 0.223766 |
| Recall | 0.407089 | 0.397959 |
| F1 | 0.290979 | 0.286460 |

Matriz de confusão no teste:

- TN: 37.262.
- FP: 5.141.
- FN: 2.242.
- TP: 1.482.

O modelo convergiu em 34 iterações, sem warnings
de convergência.

Esses valores são resultados offline de uma
divisão aleatória, não métricas de produção.

## 9. Inferência com referência não rotulada

O conjunto de referência contém 30.751 registros.

O pipeline persistido foi recarregado e utilizado
para gerar probabilidades com as 17 features.

Verificações realizadas:

- Ausência de TARGET.
- Unicidade de SK_ID_CURR.
- Ordem e conjunto das features.
- Consistência dos metadados.
- Scores finitos e entre zero e um.
- Aplicação do threshold persistido.

Resultados registrados:

- Score mínimo: 0.002295.
- Score mediano: 0.058838.
- Score médio: 0.080922.
- Score máximo: 0.672701.
- Taxa de positivos previstos: 14,45%.

A referência serve como base inicial de comparação
para os componentes futuros de monitoramento.

Não representa observações posteriores no tempo.

Arquivos joblib devem ser carregados somente
de fontes confiáveis, pois a desserialização
pode executar código.

## 10. Testes e qualidade

Executar na raiz do repositório:

```bash
python -m pytest -v
python -m ruff check .
python -m ruff format --check .
python -m pip check
git diff --check
```

Ao encerramento da implementação do baseline,
a suíte possuía 42 testes aprovados.

A cobertura contempla:

- Preparação e validações essenciais de entrada.
- Reprodutibilidade e integridade das partições.
- Ausência de sobreposição entre conjuntos.
- Imputação, encoding e preprocessamento.
- Prevenção de leakage de TARGET e SK_ID_CURR.
- Treinamento e seleção de threshold.
- Rejeição de parâmetros inválidos.
- Avaliação final com dados sintéticos.
- Serialização e consistência dos metadados.

Os testes automatizados não substituem validação
de desempenho temporal ou monitoramento em produção.

## 11. Segurança e versionamento

Os seguintes diretórios são mantidos fora do Git:

- `data/raw/`
- `data/processed/`
- `artifacts/`
- `.venv/`

Os dados e os artefatos são reconstruídos localmente.

Antes de publicar alterações, conferir:

```bash
git status --short --branch
git ls-files
git diff --check
```

Não versionar dados originais, partições preparadas,
artefatos joblib ou resultados locais com informações
potencialmente sensíveis.

## 12. Limitações conhecidas

- Baseline utiliza 17 features selecionadas.
- Não há tuning avançado de hiperparâmetros.
- Threshold maximiza F1, não retorno econômico.
- Probabilidades não foram formalmente calibradas.
- Particionamento é aleatório, não temporal.
- Referência foi extraída da mesma população.
- Há contratos Pandera implementados, mas ainda não existe monitoramento temporal da qualidade ou das distribuições.
- Não há detecção contínua de drift.
- Não há métricas operacionais instrumentadas.
- Não há pipeline de produção implantado.

Essas limitações são compatíveis com o escopo
definido para o Bloco 1.

## 13. Continuidade

Bloco 2: contratos Pandera e inferência bloqueante
implementados; evidências documentadas na seção 14.

Bloco 3: simulação de produção e monitoramento
de drift com Evidently.

Bloco 4: instrumentação SQLite, métricas, Prometheus e
Grafana implementados; reprodução na seção 16.

Bloco 5: governança e privacidade.

Bloco 6: integração, demonstração e entrega final.

O baseline não deve ser ajustado retroativamente
com base no resultado do conjunto de teste.

Mudanças futuras de política ou modelagem
devem ter protocolo de avaliação próprio
e rastreabilidade explícita.

## 14. Reprodução dos contratos e da inferência — Bloco 2

### 14.1. Pré-requisitos

A reprodução do Bloco 2 pressupõe:

- Python 3.12.
- Ambiente virtual `.venv` ativado.
- Dependências instaladas com `pip install -e ".[dev]"`.
- Partições preparadas pelo Bloco 1.
- Modelo baseline persistido.

Arquivos necessários:

- `data/processed/reference.csv`
- `artifacts/baseline_model.joblib`

Os arquivos são produzidos localmente pelo Bloco 1
e não estão versionados no repositório.

Antes da demonstração, verificar:

```bash
python scripts/verify_dataset.py
python -m pip check
```

O primeiro comando verifica a integridade das
partições em relação ao manifesto de dados.

### 14.2. Contratos implementados

Os contratos são definidos em:

`src/credit_risk_monitoring/quality/contracts.py`

Estágios:

1. `raw_inference`: recebe identificador e
   16 features originais.
2. `prepared_inference`: recebe identificador e
   17 features preditivas preparadas.

Os contratos verificam estrutura, tipos,
unicidade, nulidades e regras semânticas.

A documentação completa está em:

`docs/quality-contracts.md`

O serviço de validação está em:

`src/credit_risk_monitoring/quality/validation.py`

### 14.3. Particularidade da referência histórica

O arquivo `reference.csv` foi criado pelo Bloco 1
com as features já preparadas.

Ele contém:

- `SK_ID_CURR`.
- As 17 features preditivas.
- Nenhuma coluna TARGET.

Portanto, não pode ser enviado diretamente
ao contrato `raw_inference`.

Para demonstrar o fluxo operacional completo,
o procedimento a seguir constrói um lote de
entrada compatível a partir de cinco registros
da referência histórica.

A construção:

1. Seleciona cinco linhas.
2. Remove a feature derivada da entrada.
3. Restaura o código bruto `365243` nos casos
   identificados pelo indicador de sentinela.
4. Preserva as demais features originais.
5. Produz um lote válido.
6. Produz uma cópia com crédito negativo,
   simulando uma violação de qualidade.

Esse procedimento cria uma entrada de demonstração.
Não recupera integralmente os dados brutos originais,
nem representa um lote temporal de produção.

### 14.4. Gerar lotes de demonstração

Executar na raiz do projeto, com a `.venv` ativada:

```bash
python - <<'PY'
from pathlib import Path

import pandas as pd

from credit_risk_monitoring.data.preparation import MODEL_FEATURES

reference_path = Path("data/processed/reference.csv")
output_dir = Path("data/processed/quality_demo/docs_run")

if output_dir.exists():
    raise FileExistsError(
        "Diretorio de demonstracao ja existe. "
        "Escolha outro nome para uma nova execucao."
    )

reference = pd.read_csv(reference_path, low_memory=False)
prepared = reference.head(5).copy()

assert len(prepared) == 5
assert "TARGET" not in prepared.columns

indicator = "DAYS_EMPLOYED_SENTINEL"

raw_columns = [
    "SK_ID_CURR",
    *[feature for feature in MODEL_FEATURES if feature != indicator],
]

raw = prepared.loc[:, raw_columns].copy()

sentinel_mask = prepared[indicator].eq(1)
raw.loc[sentinel_mask, "DAYS_EMPLOYED"] = 365243

invalid = raw.copy()
invalid.loc[invalid.index[0], "AMT_CREDIT"] = -1.0

output_dir.mkdir(parents=True, exist_ok=False)

raw.to_csv(output_dir / "valid_batch.csv", index=False)
invalid.to_csv(output_dir / "invalid_batch.csv", index=False)

print("Diretorio:", output_dir)
print("Registros:", len(raw))
print("Colunas:", len(raw.columns))
print("TARGET presente:", "TARGET" in raw.columns)
print("Lotes validos e invalidos gerados.")
PY
```

Saídas esperadas:

```text
Registros: 5
Colunas: 17
TARGET presente: False
Lotes validos e invalidos gerados.
```

Os arquivos gerados são:

- `data/processed/quality_demo/docs_run/valid_batch.csv`
- `data/processed/quality_demo/docs_run/invalid_batch.csv`

Esses arquivos são locais e ignorados pelo Git.

O procedimento utiliza cinco registros históricos
apenas para demonstração funcional.

### 14.5. Executar lote válido

```bash
python scripts/score_batch.py \
  --input data/processed/quality_demo/docs_run/valid_batch.csv \
  --batch-id docs-valid \
  --model artifacts/baseline_model.joblib \
  --report-output data/processed/quality_demo/docs_run/valid_report.json \
  --scores-output data/processed/quality_demo/docs_run/valid_scores.csv

echo "Exit code: $?"
```

Resultado esperado:

- Código de saída `0`.
- Status `approved`.
- Dois estágios de validação aprovados.
- Cinco registros pontuados.
- Relatório JSON gerado.
- CSV de scores gerado.

O threshold é carregado dos metadados do
baseline persistido.

O CSV de scores contém:

- `row_index`
- `probability_default`
- `prediction`

As probabilidades são calculadas pelo pipeline
persistido; o código não realiza retreinamento.

### 14.6. Executar lote inválido

```bash
python scripts/score_batch.py \
  --input data/processed/quality_demo/docs_run/invalid_batch.csv \
  --batch-id docs-invalid \
  --model artifacts/baseline_model.joblib \
  --report-output data/processed/quality_demo/docs_run/invalid_report.json \
  --scores-output data/processed/quality_demo/docs_run/invalid_scores.csv

echo "Exit code: $?"
```

Resultado esperado:

- Código de saída `2`.
- Status `rejected`.
- Violação da regra `positive_credit`.
- Nenhum registro pontuado.
- Relatório JSON gerado.
- Nenhum CSV de scores gerado.

A rejeição ocorre antes do carregamento do
modelo e antes da chamada a `predict_proba()`.

### 14.7. Conferir os resultados

```bash
python - <<'PY'
import json
from pathlib import Path

import pandas as pd

base = Path("data/processed/quality_demo/docs_run")

valid = json.loads(
    (base / "valid_report.json").read_text(encoding="utf-8")
)
invalid = json.loads(
    (base / "invalid_report.json").read_text(encoding="utf-8")
)

scores = pd.read_csv(base / "valid_scores.csv")

assert valid["status"] == "approved"
assert invalid["status"] == "rejected"
assert len(scores) == 5
assert scores["probability_default"].between(0, 1).all()
assert not (base / "invalid_scores.csv").exists()

print("Lote valido:", valid["status"])
print("Lote invalido:", invalid["status"])
print("Scores validos:", len(scores))
print("Relatorio rejeitado sem scores: confirmado")
print("Verificacao da demonstracao aprovada.")
PY
```

Essa verificação confirma o comportamento
operacional dos arquivos produzidos.

A estrutura detalhada dos relatórios é definida
pelos objetos de resultado em:

- `quality/results.py`
- `modeling/inference.py`

### 14.8. Códigos de saída e persistência

O entrypoint possui três códigos de saída:

| Código | Significado |
|---|---|
| 0 | Aprovação e scoring concluído |
| 2 | Rejeição por violação de qualidade |
| 1 | Erro operacional |

O script não sobrescreve arquivos existentes.

O relatório JSON é criado após o CSV de scores,
quando este foi solicitado.

Falhas de escrita capturadas acionam limpeza
dos arquivos recém-criados, em melhor esforço.

A persistência não fornece garantias completas
de transação ou atomicidade entre arquivos.

### 14.9. Testes automatizados

Executar:

```bash
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m pip check
git diff --check
```

Após a integração da implementação funcional
do Bloco 2 à `main`, foram aprovados:

**114 testes automatizados.**

Os testes de integração incluem:

- Scoring com o modelo baseline persistido.
- Comparação de probabilidades com o pipeline oficial.
- Lote inválido rejeitado sem scores.
- Agregação de múltiplas violações.
- Proteção contra sobrescrita.
- Falha de carregamento do modelo.
- Execução sem arquivo opcional de scores.
- Limpeza de arquivos após falhas simuladas de escrita.

### 14.10. Integridade dos artefatos

Na validação realizada após a implementação
funcional do Bloco 2, foram observados:

| Artefato | SHA-256 |
|---|---|
| baseline_model.joblib | `8107f7111a4da92e69533a3e8e90e5ded561833964e7c9f06a71ba33bd66cf20` |
| baseline_metrics.json | `467cf4a6b29ea4b02721b2bc47f375c271830d6d30fc98c472ac5b142285fd9c` |

O threshold persistido verificado foi:

`0.1406724340221902`

Quantidade de features:

`17`

Os hashes acima são referências observadas
após a implementação, não evidência isolada
de comparação com hashes anteriores ao Bloco 2.

A verificação das partições com o manifesto
também foi aprovada.

### 14.11. Segurança e privacidade

Os relatórios de qualidade registram violações
agregadas, sem expor valores individuais de
features nem identificadores de clientes.

O campo `batch_id` deve ser operacional,
sem informações pessoais.

O CSV de scores é opcional e deve permanecer
em diretório protegido.

O projeto ignora no Git:

- `data/raw/`
- `data/processed/`
- `artifacts/`

Não publicar lotes, relatórios com conteúdo
potencialmente sensível ou artefatos do modelo.

O arquivo joblib deve ser carregado somente
de fonte confiável.

### 14.12. Limitações

A implementação demonstra uma barreira funcional
de qualidade, mas não constitui um serviço de
produção implantado.

Limitações:

- A referência é histórica e não temporal.
- Os lotes de demonstração são simulados.
- Os contratos não detectam drift estatístico.
- Não há armazenamento centralizado de execuções.
- Não há Prometheus, Grafana ou alertas operacionais.
- Não há garantias de transação durável entre arquivos.
- A validação não substitui análise de viés,
  privacidade ou avaliação regulatória.

O Bloco 3 reutilizou o baseline e os contratos
existentes para implementar a simulação de produção
e a detecção de drift. A reprodução está na seção 15.

O Bloco 4 implementará a observabilidade.

## 15. Reprodução da simulação e do drift — Bloco 3

### 15.1. Objetivo

Esta seção apresenta os procedimentos
para reproduzir o monitoramento estatístico
do Bloco 3, utilizando os componentes
implementados nos blocos anteriores.

O processo reutiliza:

- Dados preparados já verificados.
- Referência histórica não rotulada.
- Modelo baseline persistido.
- Contratos Pandera de qualidade.
- Inferência protegida pelo quality gate.
- Detector Evidently.

Nenhum dos comandos de monitoramento
exige retreinamento do baseline.

A documentação técnica completa está em
`docs/drift-monitoring.md`.

### 15.2. Pré-requisitos

Executar os comandos a partir da raiz
do repositório, com a `.venv` ativa.

Arquivos locais necessários:

- `data/processed/reference.csv`
- `data/processed/test.csv`
- `artifacts/baseline_model.joblib`

Instalar as dependências declaradas
no `pyproject.toml`, quando necessário:

```bash
python -m pip install -e ".[dev]"
python -m pip check
```

Essa instalação deve ocorrer exclusivamente
dentro do ambiente virtual do projeto.

O Bloco 3 foi validado com:

- Python 3.12.2.
- Evidently 0.7.23.
- Litestar 2.22.0.
- pandas 2.3.3.
- NumPy 2.5.4.
- scikit-learn 1.9.1.
- Pandera 0.35.0.

As versões de Evidently e Litestar
estão explicitamente fixadas
no `pyproject.toml`.

### 15.3. Dados de referência

A execução de referência utiliza:

| Conjunto | Registros |
|---|---:|
| Referência | 30.751 |
| Produção simulada | 46.127 |

Os conjuntos devem possuir valores
disjuntos de `SK_ID_CURR`.

A referência é histórica e não representa
uma janela cronológica de produção real.

As 16 features originais são comparadas
estatisticamente; o atributo derivado
`DAYS_EMPLOYED_SENTINEL` permanece
reservado ao pipeline preditivo.

### 15.4. Executar cenário controle

```bash
python scripts/monitor_drift.py \
  --reference data/processed/reference.csv \
  --model artifacts/baseline_model.joblib \
  --batch-id reproduce-control-642 \
  --json-output artifacts/reproduce-control-642.json \
  --html-output artifacts/reproduce-control-642.html \
  simulate \
  --production-prepared data/processed/test.csv \
  --scenario control \
  --seed 642
```

Resultado de referência:

- 46.127 registros pontuados.
- Nenhuma linha modificada.
- Nenhuma das 16 features sinalizada.
- 6.623 classificações positivas.

### 15.5. Executar cenário moderado

```bash
python scripts/monitor_drift.py \
  --reference data/processed/reference.csv \
  --model artifacts/baseline_model.joblib \
  --batch-id reproduce-moderate-642 \
  --json-output artifacts/reproduce-moderate-642.json \
  --html-output artifacts/reproduce-moderate-642.html \
  simulate \
  --production-prepared data/processed/test.csv \
  --scenario moderate \
  --seed 642
```

Resultado de referência:

- 46.127 registros pontuados.
- 23.063 registros modificados.
- Nenhuma das 16 features sinalizada.
- 7.376 classificações positivas.

As distribuições foram alteradas,
mas os limiares estatísticos utilizados
não foram ultrapassados.

### 15.6. Executar cenário forte

```bash
python scripts/monitor_drift.py \
  --reference data/processed/reference.csv \
  --model artifacts/baseline_model.joblib \
  --batch-id reproduce-strong-642 \
  --json-output artifacts/reproduce-strong-642.json \
  --html-output artifacts/reproduce-strong-642.html \
  simulate \
  --production-prepared data/processed/test.csv \
  --scenario strong \
  --seed 642
```

Resultado de referência:

- 46.127 registros pontuados.
- 46.127 registros modificados.
- 2 das 16 features sinalizadas.
- 11.141 classificações positivas.

As features sinalizadas foram
`AMT_CREDIT` e `AMT_INCOME_TOTAL`.

Os resultados estatísticos detalhados
estão em `docs/drift-monitoring.md`.

### 15.7. Arquivos de saída

Cada execução aprovada produz:

- Um relatório JSON agregado.
- Um relatório HTML do Evidently.

Os relatórios são gravados somente
quando o quality gate é aprovado.

Os destinos de saída devem ser inéditos,
pois a ferramenta impede sobrescrita
de arquivos já existentes.

Antes de repetir um experimento,
utilizar novos nomes de `batch-id`
e de arquivos de relatório.

Não apagar automaticamente artefatos
anteriores durante a reprodução.

### 15.8. Monitorar lote externo

O subcomando `monitor` recebe
um CSV no contrato bruto de inferência.

Exemplo:

```bash
python scripts/monitor_drift.py \
  --reference data/processed/reference.csv \
  --model artifacts/baseline_model.joblib \
  --batch-id reproduce-external \
  --json-output artifacts/reproduce-external.json \
  --html-output artifacts/reproduce-external.html \
  monitor \
  --production-raw caminho/para/lote-bruto.csv
```

O arquivo informado deve existir,
conter as colunas obrigatórias
e respeitar os contratos de qualidade.

A detecção de drift não é executada
quando a validação bloqueante rejeita
o lote de produção.

### 15.9. Códigos de saída

| Código | Interpretação |
|---|---|
| `0` | Execução bem-sucedida |
| `1` | Erro operacional |
| `2` | Rejeição pelo quality gate |

O código `0` não significa
ausência de data drift.

Drift estatístico pode ser observado
mesmo em lotes aprovados pelo
contrato de qualidade.

### 15.10. Testes e verificações

Executar:

```bash
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m pip check
git diff --check
```

Após o merge funcional do Bloco 3,
a suíte completa apresentou:

- 211 testes aprovados.
- Nenhuma falha.
- Nenhum warning exibido no pytest.
- Ruff aprovado.
- `pip check` sem conflitos.

Os testes de drift incluem:

- Métodos estatísticos e thresholds.
- Simulação determinística.
- Agregação dos resultados.
- Integração do quality gate.
- Rejeição antes da inferência e do drift.
- Execução real com dados preparados.
- CLI e códigos de saída.
- Relatórios e falhas de persistência.

### 15.11. Integridade e privacidade

Os arquivos de entrada e os relatórios
permanecem no ambiente local.

Não versionar:

- Dados brutos ou preparados.
- Modelos persistidos.
- Relatórios derivados dos datasets.
- Scores individuais.

Os relatórios JSON de monitoramento
não incluem vetores de scores individuais.

Os relatórios HTML devem permanecer
restritos ao ambiente autorizado,
pois podem expor distribuições de dados.

A exclusão de identificadores da análise
estatística não constitui garantia
integral de anonimização.

### 15.12. Limitações

Os experimentos utilizam dados
sinteticamente modificados.

Não são demonstrados:

- Mudanças temporais reais.
- Desempenho preditivo após observação
  de novos rótulos.
- Concept drift comprovado.
- Retreinamento automático.
- Agendamento ou monitoramento contínuo.
- Exportação de métricas para Prometheus.
- Dashboards do Grafana.

A reprodutibilidade depende dos mesmos
dados preparados, modelo persistido,
versões de biblioteca e parâmetros
utilizados na execução de referência.

A seed padrão do particionamento é 42,
mas sua utilização efetiva na geração
dos arquivos históricos locais não
foi comprovada nesta etapa documental.

A seed da simulação de drift é 642
nas execuções aqui reproduzidas.

A documentação dos próximos blocos
deverá distinguir monitoramento de
distribuições, observabilidade
operacional e governança de modelos.

As limitações acima correspondem ao escopo histórico
do Bloco 3. O Bloco 4 acrescentou a exposição de métricas
e dashboards, documentados na seção 16.

## 16. Reprodução da instrumentação e observabilidade — Bloco 4

### 16.1. Objetivo e limites

Este procedimento reproduz a camada de observabilidade
integrada à `main` no commit `fc48d95`, sem retreinar
o baseline nem alterar os contratos Pandera ou o detector
Evidently. As CLIs registram eventos em SQLite; o exporter
lê o histórico operacional; o Prometheus consulta `/metrics`
a cada 15 segundos; o Grafana apresenta o dashboard
versionado de oito painéis.

**Importante:** a coleta periódica de métricas não agenda
novas execuções de scoring ou monitoramento. Os exemplos
de lotes dos Blocos 2 e 3 permanecem válidos, desde que
seus caminhos de saída e identificadores sejam inéditos.

### 16.2. Ambiente e arquivos locais

Pré-requisitos:

- Python 3.12 com a `.venv` ativa e dependências do projeto.
- Docker Desktop com Linux Engine em execução e Docker Compose.
- Banco SQLite local em `artifacts/observability/events.sqlite3`,
  gerado por execuções instrumentadas, fora do Git.
- Arquivo `.env` local, ignorado pelo Git, com a variável
  `GRAFANA_ADMIN_PASSWORD` configurada para uma senha forte.

O Docker Compose pressupõe a existência do diretório
`artifacts/observability/` e do banco de eventos; não cria
eventos operacionais automaticamente. Não incluir dados,
modelos, SQLite ou credenciais em commits.

### 16.3. Registrar eventos nas execuções de negócio

As interfaces `scripts/score_batch.py` e
`scripts/monitor_drift.py` aceitam `--events-db` para
habilitar a persistência operacional. Para reproduzir
os cenários, reutilizar os comandos das seções 14.5,
14.6 e 15.4–15.6, acrescentando este argumento **antes
do subcomando `simulate` ou `monitor`, quando houver**:

```bash
--events-db artifacts/observability/events.sqlite3
```

Por exemplo, uma execução de scoring instrumentada,
pressupondo que o lote bruto de demonstração já exista:

```bash
python scripts/score_batch.py \
  --input data/processed/quality_demo/docs_run/valid_batch.csv \
  --batch-id observability-valid-example \
  --model artifacts/baseline_model.joblib \
  --events-db artifacts/observability/events.sqlite3 \
  --report-output artifacts/observability-valid-example.json
```

Os argumentos de relatórios devem apontar para arquivos
**ainda inexistentes**, pois as CLIs evitam sobrescrita.
Lotes aprovados e rejeitados produzem resultados distintos:
rejeição de qualidade pode retornar código `2` sem gerar
scores, enquanto uma execução aprovada com drift pode
retornar `0`. Falha operacional e detecção de drift não
são equivalentes. O identificador `batch_id` não deve
conter dados pessoais.

### 16.4. Iniciar a stack

Na raiz do repositório, com o Docker Engine disponível:

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

A topologia utiliza os serviços `exporter`, `prometheus`
e `grafana`. O exporter está disponível apenas na rede
Docker pela porta `8000`. As interfaces de Prometheus e
Grafana são publicadas exclusivamente em loopback:

- Prometheus: `http://127.0.0.1:9090/targets`.
- Grafana: `http://127.0.0.1:3000`.
- Dashboard: `http://127.0.0.1:3000/d/credit-risk-operations`.

O Grafana utiliza o usuário local `admin` e a senha
configurada em `.env`; seu datasource provisionado aponta
para `http://prometheus:9090` dentro da rede Docker.

### 16.5. Validar a coleta por PromQL

Em um terminal com a `.venv` ativa, execute:

```bash
python - <<'PY'
import httpx

base = "http://127.0.0.1:9090"
queries = {
    "exporter_up": 'up{job="credit-risk-exporter"}',
    "executions": "sum(credit_risk_executions_count)",
    "quality_violations": "sum(credit_risk_quality_violations_count)",
    "drift_detected": "sum(credit_risk_drift_detected_count)",
}
with httpx.Client(timeout=15) as client:
    for name, expression in queries.items():
        response = client.get(
            f"{base}/api/v1/query", params={"query": expression}
        )
        response.raise_for_status()
        payload = response.json()
        assert payload["status"] == "success", payload
        series = payload["data"]["result"]
        print(name, [item["value"][1] for item in series])
        assert series, f"Sem series para {name}"
PY
```

Se o exporter ainda não tiver eventos, primeiro executar
um lote instrumentado. Não comparar rigidamente os totais
com um snapshot histórico: novas execuções alteram as métricas.

### 16.6. Conferir o dashboard provisionado

No navegador, abrir o dashboard
`http://127.0.0.1:3000/d/credit-risk-operations`.
Conferir os oito painéis: execuções registradas,
falhas, violações de qualidade, drift, execuções por
status/pipeline, duração média, execuções em andamento
e disponibilidade do exporter.

O datasource possui UID `credit-risk-prometheus` e o
dashboard possui UID `credit-risk-operations`. A presença
do dashboard pode ser confirmada pela API Grafana com
autenticação, sem expor a senha em logs compartilhados.

### 16.7. Resultado observado e interpretação

Na validação local de **15/11/2026**, com seis eventos
preexistentes no SQLite, foram observados:

| Indicador | Resultado observado |
|---|---:|
| Execuções registradas | 6 |
| Falhas operacionais | 1 |
| Violações de qualidade agregadas | 2 |
| Execuções com drift | 1 |
| Execuções em andamento | 0 |
| Duração média monitoring | ~7,947 s |
| Duração média scoring | ~0,103 s |
| Disponibilidade do exporter (`up`) | 1 |

Esses valores são apenas uma evidência de demonstração.
O total poderá aumentar caso novos lotes sejam executados.
As métricas de contagem são **gauges agregados do SQLite**;
o Prometheus registra as amostras no instante do *scrape*,
sem reconstruir a cronologia original dos eventos. Portanto,
não interpretar essas séries como counters nativos nem aplicar
`rate()` automaticamente às contagens históricas.

### 16.8. Validação técnica e encerramento

```bash
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m pip check
docker compose config --quiet
git diff --check
```

Após o merge `fc48d95`, a suíte apresentou **349 testes
aprovados**, Ruff lint aprovado, 73 arquivos Python
formatados, `pip check` sem conflitos e Docker Compose
válido. Foram observadas sete famílias métricas,
18 amostras no exporter e oito painéis no Grafana.

A configuração do exporter foi validada em container com
`uid=10001` e montagem do SQLite somente para leitura.
Prometheus e Grafana utilizam volumes persistentes próprios.
Para desligar sem excluir esses volumes:

```bash
docker compose down
```

**Não usar `docker compose down -v`** quando for necessário
preservar o histórico das ferramentas.

### 16.9. Segurança e limitações

A stack foi validada para uso **local**, não para exposição
pública. A senha administrativa do Grafana fica em `.env`
ignorado pelo Git; as métricas não utilizam identificadores
de clientes ou lotes como labels; modelos, datasets e o
banco SQLite não são versionados.

Não foram implementados agendamento automático de scoring
ou drift, notificações de alertas, reconstrução temporal
retroativa, TLS, autenticação completa para acesso externo,
backups automatizados ou alta disponibilidade. O estado
`running` pode permanecer obsoleto quando um processo é
interrompido antes de registrar sua conclusão. A retenção
do Prometheus não elimina automaticamente eventos SQLite.

A arquitetura, o catálogo completo das sete métricas,
a configuração do exporter e as decisões de segurança
estão detalhados em [`docs/observability.md`](observability.md).
