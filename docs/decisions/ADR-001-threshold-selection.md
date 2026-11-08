# ADR-001 — Estratégia de seleção do threshold

**Status:** Aceita

**Projeto:** Credit Risk Monitoring

**Bloco:** 1 — Dados e Modelo Baseline

**Data:** 08/11/2026

## 1. Contexto

O projeto utiliza um classificador de risco de crédito
baseado inicialmente em Logistic Regression.

O dataset Home Credit Default Risk apresenta desbalanceamento
entre as classes, com aproximadamente 8,07% de registros
positivos (TARGET = 1).

A utilização do threshold padrão de 0,50 produz um recall
muito baixo, embora o modelo apresente capacidade de
discriminação medida por ROC-AUC.

Portanto, é necessário selecionar um threshold de
classificação adequado ao objetivo técnico do baseline.

O propósito principal do Tech Challenge é demonstrar
monitoramento, qualidade, drift e observabilidade, e não
desenvolver uma política econômica completa de concessão
de crédito.

## 2. Decisão

O threshold do baseline será selecionado pela maximização
do F1-score no conjunto de validação.

O procedimento consiste em:

1. Treinar o modelo exclusivamente com os dados de treino.
2. Gerar probabilidades no conjunto de validação.
3. Avaliar os thresholds candidatos.
4. Selecionar aquele que maximiza o F1-score.
5. Em empates numéricos, escolher o maior threshold.
6. Fixar o threshold antes da avaliação no conjunto de teste.
7. Avaliar o modelo no teste sem reajustar o threshold.

O conjunto de teste não participa da escolha do threshold.

A implementação inicial utiliza a função
`select_threshold_by_f1`, no módulo
`credit_risk_monitoring.modeling.training`.

## 3. Justificativa

A escolha pelo F1-score foi motivada por:

- Simplicidade de implementação e interpretação.
- Reprodutibilidade do procedimento de seleção.
- Adequação como benchmark técnico de classificação.
- Consideração conjunta de precision e recall.
- Ausência de necessidade de parâmetros econômicos externos.
- Priorização dos componentes centrais do Tech Challenge.

A escolha permite estabelecer uma regra de decisão
determinística sem ampliar significativamente o escopo.

O F1-score é utilizado como critério de engenharia
do baseline, não como métrica de retorno econômico.

## 4. Evidências da validação

Dataset: Home Credit Default Risk.

Modelo: Logistic Regression.

Registros de treino: 184.506.

Registros de validação: 46.127.

ROC-AUC: aproximadamente 0,7345.

Average Precision: aproximadamente 0,2183.

### Threshold padrão

Threshold: 0,50.

Precision: 0,578947.

Recall: 0,005908.

F1-score: 0,011696.

### Threshold selecionado

Threshold: 0,1406724340221902.

Precision: 0,226404.

Recall: 0,407089.

F1-score: 0,290979.

Esses resultados foram obtidos exclusivamente no conjunto
de validação.

Não constituem evidência de desempenho no teste final ou
em produção.

## 5. Alternativas consideradas

### 5.1. Threshold fixo de 0,50

Vantagens:

- Implementação simples.
- Critério convencional de classificação binária.

Desvantagens:

- Recall extremamente baixo na validação.
- Desconsidera o comportamento dos scores no problema.

Decisão: não utilizar como threshold operacional principal.
Manter como benchmark comparativo.

### 5.2. Otimização por custo de classificação

Função simplificada:

L(t) = FN(t) * C_FN + FP(t) * C_FP

Onde:

- C_FN: custo de um falso negativo.
- C_FP: custo de um falso positivo.
- t: threshold de classificação.

Vantagens:

- Considera assimetria econômica dos erros.
- Permite adaptar a decisão a diferentes políticas.

Limitações:

- Exige definição dos custos.
- Os custos não foram estimados a partir de dados
  econômicos observados neste projeto.
- Custos constantes não representam necessariamente
  a heterogeneidade das operações de crédito.

Decisão: não implementar nesta etapa.

### 5.3. Otimização por utilidade econômica

Uma evolução mais completa poderia considerar:

- Probabilidade de inadimplência calibrada.
- Exposição no momento do default (EAD).
- Perda dada a inadimplência (LGD).
- Margem e receita esperada da operação.
- Custos operacionais e de capital.
- Custo de oportunidade de rejeitar bons clientes.
- Restrições de política e capacidade operacional.

A perda esperada de crédito pode ser representada
de forma simplificada por:

EL = PD * LGD * EAD

Entretanto, minimizar somente a perda esperada
não é equivalente a maximizar a rentabilidade
econômica de uma carteira de crédito.

A política econômica deverá considerar simultaneamente
receitas, perdas, custos e restrições.

Decisão: fora do escopo atual.

## 6. Consequências da decisão

### Positivas

- Baseline simples e auditável.
- Seleção de threshold reproduzível.
- Menor número de dependências e parâmetros.
- Separação clara entre treinamento e decisão.
- Facilidade de integração com monitoramento futuro.

### Limitações

- O F1-score não representa custos econômicos.
- Precision e recall recebem importância segundo
  a formulação matemática do F1, não segundo uma
  função de utilidade do negócio.
- O threshold pode não ser adequado para concessão
  real de crédito.
- A escolha é dependente da distribuição da validação.
- A maximização do F1 na própria validação pode produzir
  desempenho otimista nessa amostra.
- Mudanças de prevalência, distribuição ou calibração
  podem justificar revisão futura da política.

O threshold não deverá ser reajustado automaticamente
em produção apenas porque houve detecção de drift.

## 7. Caminho de evolução arquitetural

A arquitetura atual já separa:

- Construção do pipeline.
- Treinamento do classificador.
- Geração de probabilidades.
- Avaliação com threshold.
- Seleção do threshold.

Essa separação permite substituir a função de
seleção sem modificar necessariamente o modelo.

### 7.1. Generalizar a seleção de threshold

Criar uma interface com estratégia explícita, por exemplo:

select_threshold(
    y_true,
    probabilities,
    strategy,
    cost_config=None
)

Estratégias futuras possíveis:

- `max_f1`
- `min_classification_cost`
- `max_expected_utility`

A função deverá retornar o threshold escolhido,
o valor da função objetivo e metadados da seleção.

Não é necessário implementar Strategy Pattern
ou classes abstratas enquanto existir somente
uma estratégia concreta.

### 7.2. Implementar custo por classe

Para uma estratégia simples de classificação:

L(t) = FN(t) * C_FN + FP(t) * C_FP

Implementar:

1. Configuração explícita de C_FN e C_FP.
2. Cálculo da matriz de confusão por threshold.
3. Seleção do threshold de menor custo.
4. Critério determinístico de desempate.
5. Registro dos custos utilizados.
6. Testes de sensibilidade.
7. Seleção exclusivamente na validação.

A matriz de custos precisa ter origem e finalidade
documentadas. Custos hipotéticos devem ser
identificados como simulação.

### 7.3. Evoluir para decisão por operação

Uma estratégia econômica mais avançada exigirá:

1. Avaliar a calibração das probabilidades.
2. Estimar ou receber PD, LGD e EAD adequadas.
3. Definir receita e custos esperados por operação.
4. Calcular utilidade esperada de aprovar ou rejeitar.
5. Considerar restrições operacionais e de política.
6. Otimizar a decisão na validação.
7. Avaliar a política fixada em dados independentes.

Nesse estágio, uma regra única de threshold poderá
ser insuficiente, pois operações diferentes podem
apresentar exposições, margens e custos distintos.

### 7.4. Componentes que precisariam mudar

- `modeling/training.py`:
  generalizar a seleção da função objetivo.

- Script de treinamento:
  aceitar a estratégia e seus parâmetros.

- Artefatos de métricas:
  registrar a estratégia, os custos e o threshold.

- Testes:
  validar o cálculo de custos e o procedimento
  de seleção sem vazamento de dados.

- Monitoramento futuro:
  acompanhar os resultados da política,
  diferenciando métricas técnicas e econômicas.

O preprocessador e a regressão logística poderão
permanecer inalterados se a evolução envolver
apenas a regra de decisão.

## 8. Critérios para reconsiderar esta ADR

Reavaliar a estratégia quando:

- Houver custos econômicos confiáveis.
- O projeto passar a simular decisões de concessão.
- A calibração das probabilidades se tornar requisito.
- Existirem diferentes exposições ou produtos de crédito.
- Houver necessidade de comparar políticas econômicas.
- O monitoramento exigir indicadores de resultado
  financeiro e não apenas métricas estatísticas.

## 9. Conclusão

A maximização do F1-score é adotada como critério
técnico simplificado, coerente com o objetivo
acadêmico do projeto.

Ela não representa uma política economicamente ótima
de concessão de crédito.

A arquitetura preservará a separação entre o modelo
preditivo e a regra de decisão, permitindo evolução
futura para funções de custo ou utilidade econômica
sem necessidade de reconstruir o pipeline.
