# Fairness, vieses e causalidade — Credit Risk Monitoring

## 1. Objetivo e escopo

Este documento apresenta uma avaliação diagnóstica de possíveis disparidades preditivas do baseline de risco de crédito, utilizando o conjunto de teste do projeto Credit Risk Monitoring, desenvolvido para o Tech Challenge da Fase 4 da Pós-Tech FIAP.

A análise busca identificar diferenças nas previsões e no desempenho do modelo entre grupos observáveis, documentar limitações metodológicas e propor medidas de monitoramento e governança.

**Esta avaliação não constitui auditoria de conformidade legal, comprovação de ausência de discriminação nem demonstração de relações causais.**

O estudo é retrospectivo e acadêmico. Não há evidência de utilização do modelo para decisões reais de concessão de crédito.

## 2. Arquitetura e reprodutibilidade

### 2.1 Componentes utilizados

- Dataset: `data/processed/test.csv`.
- Modelo: `artifacts/baseline_model.joblib`.
- Script: `scripts/analyze_fairness.py`.
- Testes: `tests/unit/test_fairness_analysis.py`.
- Relatório agregado: `artifacts/fairness_test_aggregated.json`.

O script reutiliza `load_baseline_model()` para carregar o pipeline treinado e o threshold persistido.

Não realiza treinamento, seleção de features, otimização de threshold, calibração ou modificação do baseline.

### 2.2 Protocolo de avaliação

1. Carregar a partição de teste.
2. Validar o conjunto rotulado com `validate_model_data()`.
3. Carregar e verificar o baseline persistido.
4. Gerar probabilidades com `predict_proba()`.
5. Aplicar o threshold armazenado no artefato.
6. Calcular métricas globais e por grupo.
7. Consolidar grupos com tamanho insuficiente.
8. Exportar somente resultados agregados.

A partição de teste não foi utilizada para selecionar um novo threshold ou retreinar o modelo.

### 2.3 Execução

```bash
python scripts/analyze_fairness.py
```

O comando gera um JSON local na pasta `artifacts/`. A função de gravação não sobrescreve um arquivo existente, exigindo tratamento explícito antes de nova execução.

## 3. Reprodução do baseline

A análise foi realizada sobre 46.127 observações.

O threshold persistido foi:

`0.1406724340221902`

A matriz de confusão observada foi:

| Resultado | Quantidade |
|---|---:|
| Verdadeiros negativos (TN) | 37.262 |
| Falsos positivos (FP) | 5.141 |
| Falsos negativos (FN) | 2.242 |
| Verdadeiros positivos (TP) | 1.482 |

Essas quatro contagens reproduziram exatamente os resultados esperados do baseline.

Portanto, a análise de fairness não introduziu diferenças nas classificações globais do modelo.

## 4. Dimensões avaliadas

Foram selecionadas três dimensões presentes ou deriváveis das features do modelo:

| Dimensão | Origem | Tratamento |
|---|---|---|
| Faixa etária | `DAYS_BIRTH` | Idade aproximada, agrupada em faixas |
| Escolaridade | `NAME_EDUCATION_TYPE` | Categorias originais |
| Tipo de renda | `NAME_INCOME_TYPE` | Categorias originais |

As faixas etárias adotadas foram: abaixo de 30 anos, 30–44 anos, 45–59 anos e 60 anos ou mais.

A idade foi estimada por `-DAYS_BIRTH / 365.25`. Valores ausentes ou implausíveis são encaminhados à categoria técnica `MISSING`.

As dimensões analisadas não representam um inventário completo de atributos protegidos, nem permitem substituir uma avaliação jurídica e contextual de discriminação.

## 5. Métricas

Para cada grupo elegível, o script calcula:

- **N:** quantidade de observações.
- **Prevalência:** proporção observada de `TARGET=1`.
- **Taxa de classificação positiva:** proporção de previsões `TARGET=1`.
- **Precision:** TP / (TP + FP).
- **Recall ou TPR:** TP / (TP + FN).
- **FPR:** FP / (FP + TN).
- **Matriz de confusão:** TN, FP, FN e TP.

Neste projeto, a classe positiva corresponde à inadimplência. Portanto, a taxa de classificação positiva indica a frequência de classificações como inadimplente, não a taxa de aprovação de crédito.

O script define `null` para métricas condicionais com denominadores inferiores a 20. Grupos com menos de 100 observações não têm suas métricas divulgadas individualmente.

Os limites de 20 e 100 são convenções diagnósticas do projeto. Não garantem significância estatística, precisão ou anonimização.

## 6. Resultados observados

### 6.1 Faixa etária

| Faixa | N | Prevalência | Classificação positiva | Recall | FPR |
|---|---:|---:|---:|---:|---:|
| Abaixo de 30 anos | 6.701 | 11,25% | 30,09% | 55,84% | 26,82% |
| 30–44 anos | 18.435 | 8,99% | 16,38% | 42,52% | 13,80% |
| 45–59 anos | 15.685 | 6,67% | 8,80% | 29,83% | 7,30% |
| 60 anos ou mais | 5.306 | 5,01% | 3,90% | 16,54% | 3,23% |

Observou-se uma associação descritiva entre menor idade e maiores taxas de classificação positiva, recall e FPR.

A taxa de classificação positiva é de aproximadamente 30,09% para menores de 30 anos, ante 3,90% para o grupo de 60 anos ou mais.

Também existem diferenças expressivas na prevalência observada de inadimplência entre as faixas etárias.

Esses resultados justificam investigação adicional, mas não permitem concluir que a idade seja a causa das diferenças nas previsões.

### 6.2 Escolaridade

| Grupo | N | Prevalência | Classificação positiva | Recall | FPR |
|---|---:|---:|---:|---:|---:|
| Higher education | 11.379 | 5,40% | 5,75% | 22,93% | 4,77% |
| Incomplete higher | 1.489 | 8,53% | 14,24% | 37,01% | 12,11% |
| Lower secondary | 558 | 10,75% | 24,01% | 55,00% | 20,28% |
| Secondary / secondary special | 32.674 | 8,94% | 17,19% | 43,16% | 14,64% |

Há diferenças nas métricas entre os níveis de escolaridade.

O grupo `Lower secondary` apresenta classificação positiva de aproximadamente 24,01%, contra 5,75% em `Higher education`.

A comparação exige cautela, especialmente pela diferença de tamanho amostral e composição entre os grupos.

Uma categoria rara, contendo 27 observações, teve suas métricas consolidadas e suprimidas do detalhamento.

### 6.3 Tipo de renda

| Grupo | N | Prevalência | Classificação positiva | Recall | FPR |
|---|---:|---:|---:|---:|---:|
| Commercial associate | 10.718 | 7,56% | 12,95% | 36,91% | 10,99% |
| Pensioner | 8.358 | 5,16% | 4,31% | 19,03% | 3,51% |
| State servant | 3.264 | 5,42% | 7,23% | 26,55% | 6,12% |
| Working | 23.779 | 9,69% | 19,50% | 45,70% | 16,69% |

Observam-se diferenças na classificação positiva e nas taxas de erro.

O grupo `Working` apresenta taxa de classificação positiva de 19,50%, em comparação a 4,31% para `Pensioner`.

Esses grupos também apresentam prevalências distintas de inadimplência, o que limita interpretações diretas das diferenças de classificação.

Três categorias raras, somando oito observações, foram consolidadas em um agrupamento técnico sem exposição dos nomes individuais.

## 7. Consistência e controle de qualidade

Foram verificadas as seguintes propriedades:

1. Cada uma das três dimensões representa as 46.127 observações do conjunto de teste.
2. A matriz de confusão global reproduz exatamente o baseline.
3. A soma das matrizes de confusão por idade reproduz a matriz global.
4. O relatório preserva o threshold oficial.
5. As categorias raras são consolidadas em `SUPPRESSED_GROUPS`.
6. O JSON não contém identificadores individuais nem vetores de scores.
7. O script não retreina o modelo.

Nas dimensões de escolaridade e tipo de renda, a matriz completa não pode ser reconstruída somente a partir do JSON publicado, pois os resultados dos grupos pequenos são intencionalmente suprimidos.

## 8. Interpretação de fairness

### 8.1 Disparidade não equivale a discriminação

As diferenças nas métricas são fatos descritivos observados nesta partição e neste modelo.

Não se pode concluir, apenas com essas medidas, que o sistema discrimina determinado grupo.

Uma avaliação de discriminação exigiria contexto sobre a decisão de crédito, critérios normativos aplicáveis, qualidade dos rótulos, variáveis utilizadas, potenciais fatores de confusão e consequências das classificações.

### 8.2 Critérios de fairness

A taxa de classificação positiva é relevante para avaliações de paridade demográfica.

O recall/TPR e o FPR são relevantes para investigações relacionadas à igualdade de oportunidades e a critérios de taxas de erro.

Esses critérios não são universalmente equivalentes ou simultaneamente alcançáveis, sobretudo quando as prevalências diferem entre grupos.

Nenhum critério isolado foi escolhido como condição suficiente de justiça algorítmica.

### 8.3 Riscos identificados

Os principais riscos diagnósticos são:

- Diferenças relevantes na frequência de previsões positivas.
- Diferenças nas taxas de falsos positivos e falsos negativos.
- Grupos com representatividade muito desigual.
- Categorias raras com métricas instáveis.
- Possíveis efeitos de proxies e variáveis correlacionadas.
- Dependência de rótulos históricos potencialmente influenciados por processos anteriores.
- Ausência de validação temporal e prospectiva de fairness.

Esses riscos devem ser tratados como hipóteses de investigação, não como violações comprovadas.

## 9. Privacidade e minimização

O relatório exporta resultados agregados, sem incluir `SK_ID_CURR`, linhas individuais ou probabilidades por cliente.

Como mecanismo adicional de minimização, categorias com menos de 100 observações são consolidadas em `SUPPRESSED_GROUPS`, sem exposição individual de seus nomes ou matrizes de confusão.

O agrupamento consolidado mantém a contagem total necessária à consistência do relatório.

Essa técnica reduz a divulgação de detalhes de grupos raros, mas **não garante anonimização formal** nem elimina todos os riscos de inferência.

Os arquivos locais de dados, modelos e relatórios devem seguir as medidas de governança, retenção e controle de acesso descritas em `docs/governance.md`.

## 10. Causalidade: escopo e limitações

### 10.1 Associação, previsão e efeito causal

Uma associação estatística entre uma variável e uma previsão não implica que alterar essa variável causaria a mesma mudança na inadimplência real.

O modelo estima probabilidades de inadimplência a partir de padrões históricos. Essa operação não equivale à identificação de efeitos causais.

Também é necessário distinguir:

- Mudança na distribuição dos dados de entrada.
- Mudança nas probabilidades geradas pelo modelo.
- Mudança nas classificações após aplicação do threshold.
- Mudança real no comportamento de inadimplência.

Os três primeiros elementos podem ser estudados por simulação de dados e inferência. O quarto requer evidência adicional sobre resultados reais.

### 10.2 Relação com os cenários de drift

O Bloco 3 implementou simulações de mudanças em variáveis e mecanismos de detecção de drift.

Esses cenários são úteis para avaliar sensibilidade operacional e alterações nas distribuições observadas.

Entretanto, não constituem experimentos causais controlados sobre inadimplência real.

Uma alteração sintética em `AMT_CREDIT` ou `AMT_INCOME_TOTAL`, por exemplo, não demonstra que uma intervenção econômica nessas variáveis produziria determinado efeito causal sobre o TARGET.

### 10.3 Possíveis fatores de confusão

Idade, escolaridade, renda, composição familiar, histórico socioeconômico e condições de crédito podem apresentar associações entre si.

Consequentemente, diferenças observadas entre grupos podem refletir combinações de fatores, e não efeitos isolados das variáveis utilizadas para segmentação.

A análise realizada não identifica nem ajusta formalmente todos os potenciais fatores de confusão.

### 10.4 Requisitos para uma investigação causal futura

Uma investigação causal demandaria, entre outros elementos:

1. Uma pergunta causal explícita e uma intervenção bem definida.
2. Um diagrama causal fundamentado em conhecimento do domínio.
3. Identificação de possíveis confundidores, mediadores e colisores.
4. Hipóteses de identificação causal verificáveis quando possível.
5. Dados adequados e avaliação de viés de seleção.
6. Métodos de estimação compatíveis com o desenho do estudo.
7. Testes de sensibilidade e documentação das limitações.

Essas atividades não fazem parte da implementação quantitativa atual.

## 11. Recomendações de mitigação e monitoramento

Recomenda-se, para eventual evolução do projeto:

- Monitorar periodicamente métricas por grupo, utilizando denominadores e tamanhos amostrais.
- Investigar disparidades persistentes de TPR, FPR e classificação positiva.
- Avaliar intervalos de confiança e incerteza estatística antes de definir limites operacionais.
- Examinar qualidade dos rótulos e possíveis vieses históricos.
- Investigar proxies e correlações entre variáveis.
- Realizar análises interseccionais apenas quando houver suporte amostral e controles de privacidade adequados.
- Avaliar mudanças por período e por população, distinguindo drift de alterações de desempenho.
- Submeter mudanças de política, variáveis ou threshold à revisão técnica e de governança.
- Documentar decisões de mitigação e seus possíveis efeitos colaterais.

Não é recomendada a alteração automática do threshold por grupo com base somente nas diferenças observadas. Tal medida exigiria avaliação adicional de critérios técnicos, jurídicos e de impacto.

## 12. Testes e evidências

A implementação foi validada com 14 testes unitários específicos, abrangendo:

- Cálculo de taxas e matriz de confusão.
- Denominadores insuficientes.
- Limites das faixas etárias.
- Consolidação de grupos pequenos.
- Ocultação dos nomes de categorias raras.
- Validação das dimensões dos vetores.
- Rejeição de probabilidades e thresholds inválidos.
- Ausência de identificadores e scores individuais no relatório sintético.
- Restrição da exportação à pasta `artifacts/`.
- Proteção contra sobrescrita acidental.

O Ruff check foi aprovado e os arquivos foram formatados.

A execução real confirmou a reprodução da matriz de confusão global e a consistência das contagens entre dimensões.

## 13. Limitações e conclusão

A análise apresenta limitações importantes:

- Dataset histórico, sem demonstração de representatividade de produção.
- Partição aleatória de teste, não validação temporal.
- Ausência de dados suficientes para uma avaliação abrangente de atributos protegidos.
- Ausência de intervalos de confiança ou testes formais de significância.
- Possibilidade de proxies, confundimento e viés nos rótulos.
- Grupos pequenos não avaliados individualmente.
- Ausência de demonstração causal.
- Ausência de avaliação de decisões reais de crédito.

**Conclusão:** o projeto passou a dispor de uma avaliação quantitativa, reproduzível e agregada de disparidades preditivas, preservando o baseline original e incorporando mecanismos de minimização de dados.

Foram observadas diferenças relevantes entre grupos etários, níveis de escolaridade e tipos de renda. Essas diferenças justificam investigação e monitoramento, mas não estabelecem discriminação ou causalidade.

A contribuição desta etapa é tornar essas limitações e riscos identificáveis, mensuráveis e documentados dentro da governança do modelo.
