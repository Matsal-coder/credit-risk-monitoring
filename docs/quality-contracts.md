# Contratos de qualidade de dados — Bloco 2

## 1. Objetivo

Este documento descreve os contratos de qualidade implementados no Bloco 2 do projeto Credit Risk Monitoring, desenvolvido para o Tech Challenge da Fase 4 da Pós-Tech FIAP.

A validação utiliza **Pandera** e possui caráter bloqueante: um lote que viole qualquer regra rígida não pode ser submetido ao modelo de classificação de crédito.

Os contratos foram desenvolvidos para o dataset Home Credit Default Risk e para as 17 features utilizadas pelo baseline LogisticRegression.

A solução implementa:

- Dois contratos Pandera para estágios distintos.
- Verificações estruturais e regras semânticas.
- Tratamento de nulidades compatível com o baseline.
- Resultados estruturados de aprovação ou rejeição.
- Bloqueio da inferência antes de `predict_proba()`.
- Testes unitários e de integração.
- Execução operacional por interface de linha de comando.

A detecção estatística de drift não pertence a esses contratos. Ela foi implementada no Bloco 3 e documentada em `docs/drift-monitoring.md`. A instrumentação operacional foi acrescentada posteriormente no Bloco 4 e está descrita na seção 13 deste documento.

## 2. Ambiente e dependências

Ambiente utilizado na validação do Bloco 2:

| Componente | Versão |
|---|---|
| Python | 3.12.2 |
| Pandera | 0.35.0 |
| pandas | 2.3.3 |
| NumPy | 2.5.4 |
| scikit-learn | 1.9.1 |
| joblib | 1.6.0 |

O projeto utiliza Windows, Git Bash e ambiente virtual `.venv`.

A dependência está declarada no `pyproject.toml`:

```toml
"pandera[pandas]>=0.25,<1"
```

Essa declaração estabelece uma faixa de compatibilidade, não uma versão fixa. A implementação e os testes foram verificados com Pandera 0.35.0.

Os contratos utilizam a API `pandera.pandas`.

## 3. Fronteiras de validação

Foram implementadas duas fronteiras distintas.

### 3.1. Raw inference

Contrato: `RAW_INFERENCE_SCHEMA`

Estágio: `raw_inference`

Recebe um DataFrame com 17 colunas:

- `SK_ID_CURR`.
- 11 features numéricas originais.
- 5 features categóricas originais.

O lote não deve conter `TARGET` nem `DAYS_EMPLOYED_SENTINEL`.

Essa validação ocorre antes da preparação determinística.

### 3.2. Prepared inference

Contrato: `PREPARED_INFERENCE_SCHEMA`

Estágio: `prepared_inference`

Recebe um DataFrame com 18 colunas:

- `SK_ID_CURR`.
- As 17 features preditivas do baseline.

Nesse estágio, `DAYS_EMPLOYED_SENTINEL` já deve existir e o valor especial `365243` deve ter sido tratado.

A validação ocorre depois da preparação e antes do carregamento do modelo.

### 3.3. Restrições estruturais comuns

Ambos os contratos utilizam:

- `strict=True`: rejeição de colunas adicionais não previstas.
- `unique_column_names=True`: rejeição de nomes de colunas duplicados.
- `coerce=False`: ausência de conversão automática de tipos.
- Verificação de colunas obrigatórias.
- Rejeição de lote vazio.
- Identificador não nulo e único dentro do lote.

A unicidade de `SK_ID_CURR` é exigida dentro de cada lote. Não existe, neste bloco, uma base de controle global de identificadores entre execuções.

### 3.4. Tipos esperados

Os contratos exigem tipos compatíveis com os schemas,
sem coerção automática de dados.

- SK_ID_CURR: inteiro, obrigatório e único no lote.
- DAYS_BIRTH: inteiro, não nulo.
- CNT_CHILDREN: inteiro, não nulo.
- Demais features numéricas originais: ponto flutuante.
- Features categóricas: string, com nulidade permitida.
- DAYS_EMPLOYED_SENTINEL: indicador inteiro,
  não nulo e pertencente a {0, 1}, exclusivamente
  no estágio prepared_inference.

A ausência de coerção automática impede que
a validação converta silenciosamente valores
incompatíveis com os tipos esperados.

## 4. Catálogo das regras semânticas

As regras abaixo são bloqueantes quando aplicáveis.

| Campo | Regra | Condição |
|---|---|---|
| `AMT_CREDIT` | `positive_credit` | Valor maior que zero |
| `AMT_INCOME_TOTAL` | `positive_income` | Valor maior que zero |
| `AMT_ANNUITY` | `positive_annuity` | Valor maior que zero, quando presente |
| `AMT_GOODS_PRICE` | `positive_goods_price` | Valor maior que zero, quando presente |
| `EXT_SOURCE_2` | `external_score_range` | Entre 0 e 1, quando presente |
| `EXT_SOURCE_3` | `external_score_range` | Entre 0 e 1, quando presente |
| `DAYS_BIRTH` | `negative_birth_days` | Valor negativo |
| `DAYS_REGISTRATION` | `nonpositive_registration_days` | Valor menor ou igual a zero, quando presente |
| `CNT_CHILDREN` | `nonnegative_children` | Valor maior ou igual a zero |
| `CNT_FAM_MEMBERS` | `positive_family_members` | Valor maior ou igual a um, quando presente |
| `FLAG_OWN_CAR` | `ownership_flag_domain` | `Y` ou `N`, quando presente |
| `FLAG_OWN_REALTY` | `ownership_flag_domain` | `Y` ou `N`, quando presente |
| `NAME_CONTRACT_TYPE` | `contract_type_domain` | `Cash loans` ou `Revolving loans`, quando presente |

As regras foram selecionadas para identificar inconsistências semânticas no contexto do Home Credit.

Não foram introduzidos limites superiores baseados simplesmente nos valores máximos observados na referência histórica. Valores extremos não representam necessariamente erros de qualidade.

As features `NAME_INCOME_TYPE` e `NAME_EDUCATION_TYPE` não possuem bloqueio rígido de domínio categórico. Essa decisão preserva a compatibilidade com o tratamento de categorias desconhecidas pelo `OneHotEncoder(handle_unknown="ignore")`.

## 5. Regras de emprego e sentinela

A variável `DAYS_EMPLOYED` utiliza uma representação específica no Home Credit.

O valor `365243` é uma sentinela e não representa uma duração válida de emprego.

### 5.1. Contrato bruto

Regra: `raw_employment_days`

São aceitos:

- Valores não positivos.
- Valor especial `365243`.
- Nulidades permitidas pelo contrato.

A sentinela não deve ser rejeitada antes da preparação.

### 5.2. Transformação determinística

A função `transform_employment_sentinel()` é compartilhada pelos caminhos de treinamento e inferência.

A transformação:

1. Identifica `DAYS_EMPLOYED == 365243`.
2. Cria `DAYS_EMPLOYED_SENTINEL` com valores 0 ou 1.
3. Substitui a sentinela por `NaN`.
4. Preserva os nulos originalmente existentes.
5. Não modifica o DataFrame original.

A função `prepare_inference_features()` utiliza essa transformação para preparar lotes sem `TARGET`.

### 5.3. Contrato preparado

Regras:

- `prepared_employment_days`: valores não positivos quando presentes.
- `valid_employment_indicator`: indicador inteiro pertencente a `{0, 1}`.
- `sentinel_consistency`: indicador igual a 1 exige `DAYS_EMPLOYED` ausente.

O inverso não é obrigatório: `DAYS_EMPLOYED` originalmente nulo pode possuir indicador igual a zero.

## 6. Política de nulidades

O contrato não exige ausência universal de nulos.

O baseline possui:

- Imputação numérica pela mediana.
- Imputação categórica pela moda.
- Codificação One-Hot com tratamento de categorias desconhecidas.

Por isso, a validação diferencia nulidades proibidas de nulidades legítimas.

| Grupo | Política |
|---|---|
| `SK_ID_CURR` | Nulos proibidos |
| `AMT_CREDIT` | Nulos permitidos pelo schema; valores presentes devem ser positivos |
| `AMT_INCOME_TOTAL` | Nulos permitidos pelo schema; valores presentes devem ser positivos |
| `DAYS_BIRTH` | Nulos proibidos |
| `CNT_CHILDREN` | Nulos proibidos |
| Demais features numéricas originais | Nulos permitidos |
| Features categóricas | Nulos permitidos |
| `DAYS_EMPLOYED_SENTINEL` | Nulos proibidos |

A política apresentada corresponde aos schemas efetivamente implementados.

Permitir nulos não equivale a afirmar que qualquer volume de ausência seja estatisticamente aceitável. O monitoramento das proporções de nulos ao longo do tempo pertence às etapas posteriores de monitoramento.

## 7. Serviço de validação

Módulo:

`credit_risk_monitoring.quality.validation`

Interface:

```python
validate_batch(
    df: pd.DataFrame,
    stage: ValidationStage,
    batch_id: str,
) -> ValidationResult
```

Estágios permitidos:

- `raw_inference`
- `prepared_inference`

O serviço aplica o contrato correspondente e retorna um resultado estruturado.

Estados possíveis:

- `approved`: lote aprovado.
- `rejected`: pelo menos uma violação bloqueante.

Entradas inválidas para a própria interface e erros operacionais inesperados geram exceções, em vez de aprovação silenciosa.

### 7.1. Estrutura do resultado

O objeto `ValidationResult` contém:

- `batch_id`: identificador operacional do lote.
- `stage`: estágio da validação.
- `status`: aprovação ou rejeição.
- `total_rows`: quantidade de registros recebidos.
- `violations`: violações agregadas.

Cada `QualityViolation` contém:

- `column`
- `rule`
- `count`
- `severity`

A severidade utilizada atualmente é `error`.

O resultado possui propriedades auxiliares `approved` e `violation_count`, além do método `to_dict()`.

As estruturas QualityViolation e ValidationResult
utilizam dataclasses imutáveis (frozen=True).

O método to_dict() converte o resultado para uma
representação serializável em JSON, preservando
os campos definidos nas estruturas.

A imutabilidade impede a reatribuição direta dos
campos após a criação dos objetos, contribuindo
para a consistência dos resultados operacionais.

### 7.2. Exemplo de rejeição

Exemplo ilustrativo de um resultado de validação rejeitado, com quatro registros fictícios e múltiplas violações:

```json
{
  "batch_id": "multiple-violations",
  "stage": "prepared_inference",
  "status": "rejected",
  "total_rows": 4,
  "violations": [
    {
      "column": "AMT_CREDIT",
      "rule": "positive_credit",
      "count": 2,
      "severity": "error"
    },
    {
      "column": "CNT_CHILDREN",
      "rule": "nonnegative_children",
      "count": 1,
      "severity": "error"
    },
    {
      "column": "EXT_SOURCE_2",
      "rule": "external_score_range",
      "count": 1,
      "severity": "error"
    }
  ]
}
```

Este exemplo demonstra o formato conceitual da agregação de violações. As contagens são fictícias e não devem ser interpretadas como resultado de uma execução real. As evidências operacionais verificadas estão registradas na seção 10.

`violation_count` representa a soma das ocorrências reportadas, não necessariamente a quantidade de clientes distintos com problemas.

Algumas falhas estruturais podem utilizar identificadores genéricos, como `_schema` e `schema_violation`. Uma coluna obrigatória ausente pode ser reportada por `column_in_dataframe`.

## 8. Barreira de qualidade e inferência

Módulo:

`credit_risk_monitoring.modeling.inference`

Interface principal:

```python
run_quality_gated_inference(
    df: pd.DataFrame,
    batch_id: str,
    *,
    model_path: Path = DEFAULT_MODEL_PATH,
) -> InferenceResult
```

O fluxo implementado é:

```text
LOTE BRUTO
    |
    v
VALIDAÇÃO RAW
    |
    +-- REJEITADO --> SEM INFERÊNCIA
    |
    v
PREPARAÇÃO DETERMINÍSTICA
    |
    v
VALIDAÇÃO PREPARED
    |
    +-- REJEITADO --> SEM INFERÊNCIA
    |
    v
CARREGAMENTO DO BASELINE
    |
    v
PREDICT_PROBA
    |
    v
CLASSIFICAÇÃO COM THRESHOLD PERSISTIDO
```

O modelo somente é carregado após a aprovação dos dois contratos.

O serviço utiliza o pipeline persistido em:

`artifacts/baseline_model.joblib`

São verificados metadados, features, classes do classificador, estado fitted e validade do threshold.

O serviço não executa:

- `fit()`
- Retreinamento.
- Reajuste de imputadores.
- Recalibração do modelo.
- Nova seleção de threshold.

O threshold oficial utilizado é:

`0.1406724340221902`

O resultado de inferência contém o status, as validações realizadas, a quantidade de registros pontuados e, quando aprovado, probabilidades e classificações.

O método `InferenceResult.to_dict()` omite probabilidades individuais por padrão.

## 9. Interface operacional

Script:

`scripts/score_batch.py`

Parâmetros:

| Parâmetro | Finalidade |
|---|---|
| `--input` | CSV bruto sem TARGET |
| `--batch-id` | Identificador operacional |
| `--model` | Caminho do modelo persistido |
| `--report-output` | Destino do relatório JSON |
| `--scores-output` | CSV opcional de probabilidades |

Códigos de saída:

| Código | Significado |
|---|---|
| `0` | Lote aprovado e processamento concluído |
| `2` | Lote rejeitado por qualidade |
| `1` | Falha operacional tratada pelo entrypoint |

Um lote rejeitado produz relatório de qualidade, mas não produz CSV de scores.

O script recusa sobrescrita de arquivos existentes e utiliza criação exclusiva dos arquivos de saída.

Quando scores individuais são solicitados, o CSV é gravado antes do relatório de aprovação.

Em falhas de persistência capturadas, o script tenta remover os arquivos recém-criados.

Essa limpeza é uma proteção de melhor esforço, não uma transação durável contra encerramento abrupto do processo ou falha de energia.

## 10. Evidências verificadas

### 10.1. Compatibilidade com a referência

O contrato preparado foi aplicado aos 30.751 registros de:

`data/processed/reference.csv`

Resultado observado:

`APROVADO — 30.751 linhas`

A referência é histórica e obtida por particionamento aleatório. Não representa produção temporal real.

### 10.2. Demonstração operacional

Foi realizada uma demonstração com dois lotes locais de cinco registros, derivados de uma amostra da referência.

**Lote válido:**

- Código de saída: 0.
- Status: `approved`.
- Cinco registros pontuados.
- Dois contratos aprovados.
- Relatório JSON gerado.
- CSV de scores gerado.
- Threshold oficial preservado.

**Lote inválido:**

- Código de saída: 2.
- Status: `rejected`.
- Nenhum registro pontuado.
- Regra `positive_credit` identificada.
- Relatório JSON gerado.
- Nenhum arquivo de scores gerado.

A alteração inválida foi simulada por meio de crédito negativo.

Os arquivos de demonstração foram mantidos em:

`data/processed/quality_demo/`

Esse diretório é ignorado pelo Git.

### 10.3. Testes automatizados

Após a integração da segunda branch na `main`, foram aprovados 114 testes.

A cobertura inclui:

- Contratos válidos e inválidos.
- Nulidades legítimas.
- Rejeição de colunas ausentes.
- Regras semânticas independentes.
- Tratamento da sentinela.
- Consistência entre preparação histórica e inferência.
- Agregação de violações.
- Proteção contra exposição de valores individuais nos resultados.
- Bloqueio anterior ao carregamento do modelo.
- Bloqueio anterior a `predict_proba()`.
- Inferência com baseline real.
- Comparação de probabilidades com o pipeline persistido.
- Preservação do threshold.
- Execução CLI válida e inválida.
- Proteção contra sobrescrita.
- Limpeza de arquivos em falhas de persistência.

As verificações de Ruff e dependências também foram aprovadas.

## 11. Privacidade e proteção dos artefatos

Os relatórios estruturados de qualidade não incluem valores individuais das features nem identificadores de clientes.

O campo `batch_id` é operacional e deve ser escolhido sem incluir informações pessoais.

O CSV de scores individuais é opcional e não é gerado automaticamente em todas as execuções.

Os seguintes diretórios permanecem fora do Git:

- `data/raw/`
- `data/processed/`
- `artifacts/`

O arquivo joblib deve ser carregado exclusivamente de origem confiável, pois a desserialização pode executar código.

Essas medidas são controles técnicos implementados no Bloco 2. Não representam, isoladamente, conformidade integral com a LGPD.

A análise completa de governança, retenção, bases legais, vieses e privacidade será consolidada no Bloco 5.

## 12. Limitações e continuidade

Limitações atuais:

- Os contratos foram desenvolvidos para o Home Credit e para as features selecionadas.
- A validação não garante qualidade estatística ou estabilidade temporal.
- O identificador é verificado quanto à unicidade apenas dentro de cada lote.
- Na implementação original do Bloco 2, o serviço não possuía armazenamento operacional de eventos; ele foi acrescentado posteriormente no Bloco 4.
- A contagem de violações não equivale necessariamente à contagem de clientes afetados.
- Algumas falhas estruturais possuem classificação genérica.
- A persistência em arquivos oferece limpeza de melhor esforço, sem atomicidade entre múltiplos arquivos.
- Não há inferência implantada como serviço de produção.
- Não há detecção de drift implementada neste bloco.

Continuidade planejada:

**Bloco 3:** simulação de produção e detecção de drift, utilizando a referência histórica e os resultados de inferência.

**Bloco 4:** instrumentação operacional, métricas, Prometheus e Grafana — implementados posteriormente, conforme seção 13.

**Bloco 5:** documentação consolidada de governança e privacidade.

**Bloco 6:** integração, demonstração e preparação da entrega final.

Os contratos e a barreira de qualidade deverão ser preservados durante essas evoluções. Alterações futuras deverão ser justificadas e acompanhadas de testes de regressão.


## 13. Integração posterior com a observabilidade — Bloco 4

Esta seção descreve a instrumentação **adicionada após a conclusão do
Bloco 2**. As regras Pandera, a política de nulidades, a preparação,
o threshold do baseline e a barreira de qualidade permanecem inalterados.
O armazenamento de eventos não substitui `ValidationResult`, os
relatórios JSON ou os testes dos contratos originais.

### 13.1. Registro operacional do quality gate

A interface `scripts/score_batch.py` passou a aceitar o argumento
opcional `--events-db` para persistir eventos operacionais em SQLite.
O armazenamento local utilizado na demonstração foi:

`artifacts/observability/events.sqlite3`

Com a opção habilitada, o ciclo operacional registra informações
agregadas da execução de scoring, incluindo seu estado, resultados
de qualidade e ocorrências de violações quando aplicável. Sem essa
opção, a finalidade original da CLI de scoring é preservada.

É importante diferenciar três resultados:

- **Lote aprovado:** os dois contratos passam, e o modelo pode gerar
  scores; código de saída `0` quando o processamento é concluído.
- **Lote rejeitado:** o quality gate impede a inferência; código de
  saída `2`, sem scores; a execução pode ser registrada como
  operacionalmente `completed`, pois o bloqueio foi executado conforme
  a regra de negócio.
- **Falha operacional:** um erro tratado na execução pode produzir
  código de saída `1` e estado operacional `failed`. Não equivale
  necessariamente a uma rejeição pelo contrato Pandera.

O campo `batch_id` permanece um identificador operacional, e não
deve conter dados pessoais. Nenhum `SK_ID_CURR` ou valor individual de
feature é incluído como label de métrica.

### 13.2. Exportação de métricas agregadas

O fluxo instrumentado é:

```text
scripts/score_batch.py --events-db ...
           |
           v
SQLite — eventos operacionais
           |
           v
Metrics Exporter — GET /metrics
           |
           v
Prometheus — scrape periódico
           |
           v
Grafana — Operations Overview
```

O exporter lê os eventos persistidos: ele **não executa** Pandera,
não pontua lotes e não substitui o quality gate.

As famílias métricas particularmente relevantes para qualidade são:

| Métrica | Significado operacional |
|---|---|
| `credit_risk_executions_count{pipeline="scoring",execution_status="..."}` | Quantidade de execuções de scoring por estado operacional |
| `credit_risk_quality_violations_count{pipeline="scoring"}` | Soma das ocorrências de violações de qualidade registradas no histórico |
| `credit_risk_execution_duration_seconds_sum` e `_count` | Agregados utilizados para calcular a duração média por pipeline |
| `credit_risk_running_executions{pipeline="scoring"}` | Execuções que permanecem registradas como em andamento |

As métricas de contagem são **gauges derivados do histórico SQLite**.
O Prometheus coleta fotografias dessas contagens ao longo do tempo,
sem reconstruir retroativamente os horários originais dos eventos.
A quantidade de ocorrências de violações não corresponde
necessariamente ao número de clientes, linhas ou lotes distintos.

### 13.3. Exemplo de scoring instrumentado

Com a `.venv` ativa, modelo disponível e lote bruto de demonstração
previamente gerado conforme `docs/reproducibility.md`, executar na
raiz do projeto, escolhendo novos nomes para evitar sobrescrita:

```bash
python scripts/score_batch.py \
  --input data/processed/quality_demo/docs_run/invalid_batch.csv \
  --batch-id quality-observability-example \
  --model artifacts/baseline_model.joblib \
  --events-db artifacts/observability/events.sqlite3 \
  --report-output artifacts/quality-observability-example.json
```

O lote de exemplo contém uma violação sintética de `positive_credit`.
A expectativa é rejeição pelo quality gate, código de saída `2`,
relatório de qualidade e ausência de scores. Uma execução instrumentada
adiciona dados ao histórico e pode alterar os totais do dashboard.
O exemplo pressupõe que o banco e seu diretório operacional existam.

### 13.4. Evidências e limites

Na demonstração local do Bloco 4, o SQLite continha quatro execuções
de scoring: três `completed` e uma `failed`. As consultas PromQL
retornaram **duas ocorrências agregadas de violações de qualidade**
no histórico da stack e duração média de scoring de aproximadamente
**0,103 segundo**. Esses valores representam um snapshot de teste,
não indicadores de operação produtiva nem contagem de clientes afetados.

A implementação mantém a distinção entre qualidade de dados,
resultado do modelo e observabilidade operacional. Não foram
implementados agendamento contínuo de scoring, notificações
automáticas de alertas, integração com concessão real de crédito,
política institucional de retenção ou conformidade integral com a LGPD.

Para o catálogo completo das sete famílias métricas, a segurança
da stack, as evidências de funcionamento e os comandos de validação,
consultar `docs/observability.md`. Para reproduzir o pipeline e os
cenários de demonstração, consultar `docs/reproducibility.md`.
