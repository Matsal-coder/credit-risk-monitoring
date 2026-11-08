# Guia de reprodutibilidade — Bloco 1

## 1. Objetivo

Este documento descreve como reproduzir o Bloco 1
do projeto Credit Risk Monitoring, desde a preparação
dos dados até a avaliação e persistência do baseline.

Escopo reproduzido:

- Inspeção do Home Credit Default Risk.
- Preparação e particionamento determinísticos.
- Verificação de integridade dos dados.
- Treinamento do baseline Logistic Regression.
- Seleção do threshold por maximização do F1.
- Avaliação independente no teste.
- Persistência do pipeline e dos resultados.
- Inferência sobre a referência não rotulada.

O projeto ainda não implementa monitoramento contínuo
de drift, qualidade com Pandera ou observabilidade
com Prometheus/Grafana.

## 2. Ambiente

Ambiente utilizado na execução de referência:

- Sistema operacional: Windows.
- Terminal: Git Bash.
- Python: 3.12.2.
- pandas: 2.3.3.
- numpy: 2.5.4.
- scikit-learn: 1.9.1.
- joblib: 1.6.0.

O projeto utiliza ambiente virtual local `.venv`.

As dependências estão declaradas no `pyproject.toml`
por intervalos de versões, não por um lockfile.

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

A preparação utiliza seed 42 e particionamento
aleatório estratificado.

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
- Não há validação de schema com Pandera.
- Não há detecção contínua de drift.
- Não há métricas operacionais instrumentadas.
- Não há pipeline de produção implantado.

Essas limitações são compatíveis com o escopo
definido para o Bloco 1.

## 13. Continuidade

Bloco 2: contratos e qualidade de dados com Pandera.

Bloco 3: simulação de produção e monitoramento
de drift com Evidently.

Bloco 4: observabilidade com Prometheus/Grafana.

Bloco 5: governança e privacidade.

Bloco 6: integração, demonstração e entrega final.

O baseline não deve ser ajustado retroativamente
com base no resultado do conjunto de teste.

Mudanças futuras de política ou modelagem
devem ter protocolo de avaliação próprio
e rastreabilidade explícita.
