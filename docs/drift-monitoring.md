# Simulação de produção e monitoramento de data drift — Bloco 3

## 1. Objetivo

O Bloco 3 do Credit Risk Monitoring implementa uma simulação
controlada de lotes de produção e um mecanismo de detecção
estatística de mudanças nas distribuições das variáveis
utilizadas pelo modelo de risco de crédito.

O projeto integra:

- Simulação determinística de cenários de produção.
- Validação dos lotes pelos contratos Pandera do Bloco 2.
- Inferência protegida pelo quality gate.
- Detecção de data drift com Evidently AI.
- Consolidação de resultados estruturados.
- Exportação de relatórios JSON e HTML.
- Interface operacional por linha de comando.

O objetivo é identificar alterações de distribuição e
acompanhar seus efeitos sobre as previsões do baseline.

A detecção de data drift não demonstra, isoladamente,
degradação de desempenho, concept drift ou alterações
efetivas na inadimplência observada.

## 2. Arquitetura implementada

O monitoramento reutiliza o baseline e os contratos de
qualidade já desenvolvidos nos Blocos 1 e 2.

Fluxo lógico:

1. Carregar a referência histórica preparada.
2. Reconstruir sua representação bruta de inferência.
3. Validar a referência com Pandera.
4. Receber um lote bruto ou simular um lote de produção.
5. Verificar a separação dos identificadores entre
   referência e produção.
6. Executar a inferência protegida pelo quality gate.
7. Interromper o processamento quando o lote é rejeitado.
8. Para lotes aprovados, comparar as distribuições
   utilizando Evidently.
9. Consolidar os resultados estatísticos por feature.
10. Exportar os relatórios JSON e HTML.

O baseline persistido não é retreinado e seu threshold
não é recalibrado durante o monitoramento.

### 2.1. Componentes

| Componente | Responsabilidade |
|---|---|
| `drift/simulation.py` | Reconstrução de lotes e simulação de cenários |
| `drift/detection.py` | Execução do Evidently e extração das estatísticas |
| `drift/results.py` | Consolidação dos resultados de drift |
| `drift/monitoring.py` | Orquestração de qualidade, inferência e drift |
| `drift/reporting.py` | Exportação de JSON agregado e HTML |
| `scripts/monitor_drift.py` | Interface operacional de monitoramento |

A implementação mantém separadas as responsabilidades
de simulação, validação, inferência, estatística e
persistência.

## 3. Dados utilizados

O projeto utiliza o Home Credit Default Risk.

A base original `application_train.csv` contém
307.511 registros e 122 colunas.

Na execução de referência do Bloco 3:

| Conjunto | Registros | Utilização |
|---|---:|---|
| Referência | 30.751 | Distribuições históricas |
| Teste | 46.127 | Base dos lotes de produção simulados |

Arquivos locais:

- `data/processed/reference.csv`
- `data/processed/test.csv`

Os dois conjuntos possuem identificadores
`SK_ID_CURR` disjuntos, conforme verificações
de integração realizadas no projeto.

A referência não inclui o rótulo `TARGET`.

O conjunto de teste preparado pode conter `TARGET`,
mas essa coluna é removida na reconstrução dos lotes
brutos utilizados na inferência e no monitoramento.

A referência é uma amostra histórica separada
deterministicamente, e não uma janela temporal real
de produção.

### 3.1. Seeds e reprodutibilidade

As operações aleatórias possuem responsabilidades
diferentes:

| Operação | Seed | Situação |
|---|---:|---|
| Particionamento | 42 | Padrão definido em `data/preparation.py` |
| Treinamento do baseline | 42 | Registrada nos metadados históricos |
| Simulação de drift | 642 | Padrão de `drift/simulation.py` |

O script `scripts/prepare_dataset.py` permite alterar
a seed do particionamento por `--seed`.

A seed efetivamente utilizada na geração histórica
dos CSVs locais ainda não foi comprovada por um
manifesto de particionamento recuperado nesta etapa.

Os resultados documentados neste Bloco 3 utilizam
os CSVs locais previamente verificados, sem
regenerar suas partições.

## 4. Simulação dos cenários de produção

A simulação utiliza a função
`simulate_production_batch()`.

A função recebe um DataFrame preparado, um
identificador de cenário e uma seed.

O resultado contém o lote bruto simulado
e a quantidade de registros modificados.

### 4.1. Cenários disponíveis

| Cenário | Fração afetada | Multiplicador da renda | Multiplicador do crédito |
|---|---:|---:|---:|
| `control` | 0% | 1,00 | 1,00 |
| `moderate` | 50% | 0,90 | 1,10 |
| `strong` | 100% | 0,80 | 1,25 |

As transformações atuam sobre:

- `AMT_INCOME_TOTAL`: renda total.
- `AMT_CREDIT`: valor do crédito.

No cenário moderado, uma fração determinística
dos registros é selecionada para alteração.

No cenário forte, todos os registros são afetados.

O cenário controle preserva os valores originais.

### 4.2. Quantidades observadas

Para o conjunto de teste com 46.127 registros:

| Cenário | Registros modificados |
|---|---:|
| `control` | 0 |
| `moderate` | 23.063 |
| `strong` | 46.127 |

A execução foi realizada com seed 642.

As alterações são artificiais e não devem ser
interpretadas como eventos econômicos observados
ou mudanças reais no comportamento dos clientes.

### 4.3. Reconstrução dos lotes brutos

A função `reconstruct_raw_batch()` converte a
representação preparada para o contrato bruto
de inferência.

Entre suas responsabilidades:

- Remover `TARGET`, quando presente.
- Remover o indicador derivado da representação bruta.
- Restaurar o valor sentinela de `DAYS_EMPLOYED`
  quando indicado pelo atributo derivado.
- Preservar as features originais necessárias
  para validação e inferência.

A reconstrução permite que os lotes simulados
percorram o mesmo quality gate utilizado para
lotes brutos externos.

## 5. Features monitoradas

O baseline utiliza 17 features preditivas:
11 numéricas, 5 categóricas e um indicador derivado.

O monitoramento estatístico compara as distribuições
das 16 features originais.

### 5.1. Numéricas

1. `AMT_CREDIT`
2. `AMT_INCOME_TOTAL`
3. `AMT_ANNUITY`
4. `AMT_GOODS_PRICE`
5. `EXT_SOURCE_2`
6. `EXT_SOURCE_3`
7. `DAYS_BIRTH`
8. `DAYS_EMPLOYED`
9. `DAYS_REGISTRATION`
10. `CNT_CHILDREN`
11. `CNT_FAM_MEMBERS`

### 5.2. Categóricas

1. `NAME_INCOME_TYPE`
2. `NAME_EDUCATION_TYPE`
3. `FLAG_OWN_CAR`
4. `FLAG_OWN_REALTY`
5. `NAME_CONTRACT_TYPE`

### 5.3. Atributos excluídos

- `SK_ID_CURR`: identificador operacional.
- `TARGET`: rótulo, indisponível em inferência.
- `DAYS_EMPLOYED_SENTINEL`: indicador derivado
  utilizado pelo baseline, não monitorado como
  uma das 16 features originais.

O identificador e o rótulo não são enviados como
colunas para a análise estatística do Evidently.

## 6. Quality gate e execução condicionada

A referência deve atender ao contrato de qualidade
antes de ser utilizada no monitoramento.

A produção também deve passar pelas validações
de inferência bruta e preparada.

Se o lote de produção for rejeitado:

- Nenhuma linha é pontuada.
- O detector de drift não é executado.
- Não é emitido relatório JSON ou HTML de sucesso
  pela CLI de monitoramento.
- A execução retorna o código operacional 2.

Se o lote for aprovado, o modelo persistido
produz as previsões e o Evidently realiza as
comparações entre referência e produção.

A rejeição pelo quality gate e a detecção de drift
representam condições distintas: um lote pode
ser válido estruturalmente e apresentar drift.

O threshold do baseline permanece fixo em:

`0.1406724340221902`

O Bloco 3 não modifica os pesos do modelo
nem o critério de classificação.

## 7. Metodologia estatística de detecção

A implementação utiliza Evidently AI 0.7.23, com
o preset `DataDriftPreset`, para comparar as
distribuições da referência e dos lotes de produção.

A função `run_evidently_drift()` executa o relatório
e extrai os resultados correspondentes às 16
features monitoradas.

Cada resultado por feature registra:

- Nome da variável.
- Método estatístico efetivamente aplicado.
- Estatística ou distância observada.
- Limiar de decisão.
- Indicador booleano de drift.

### 7.1. Seleção dos métodos

O Evidently pode selecionar métodos diferentes
de acordo com o tipo da variável e as
características dos dados comparados.

Nos testes do projeto foram identificados:

| Método | Interpretação da decisão |
|---|---|
| Kolmogorov-Smirnov (p-value) | Drift quando p-value < limiar |
| Chi-square (p-value) | Drift quando p-value < limiar |
| Z-test (p-value) | Drift quando p-value < limiar |
| Wasserstein distance (normed) | Drift quando distância > limiar |
| Jensen-Shannon distance | Drift quando distância > limiar |

Os testes baseados em p-value utilizam uma lógica
de decisão diferente daquela aplicada às métricas
de distância.

A implementação reconhece explicitamente essas
direções de comparação e rejeita métodos que não
estejam entre os suportados.

Também rejeita estatísticas inválidas, como
valores não finitos, e p-values fora de [0, 1].

### 7.2. Métodos observados nos lotes completos

Na comparação real entre:

- Referência: 30.751 registros.
- Produção simulada: 46.127 registros.

O Evidently selecionou:

- Wasserstein distance (normed) para as 11
  features numéricas.
- Jensen-Shannon distance para as 5
  features categóricas.

Nas execuções verificadas, o limiar aplicado
a essas distâncias foi 0,1.

Assim, uma feature apresenta drift quando
sua distância ultrapassa 0,1.

Os testes com amostras sintéticas menores
também verificaram métodos baseados em
p-value, incluindo limiar de 0,05.

O método e o limiar efetivamente utilizados
são preservados nos resultados por feature.
Não existe uma substituição indiscriminada
de todos os métodos por uma única estatística.

### 7.3. Critério agregado do projeto

O `DriftSummary` consolida:

- `features_analyzed`: quantidade monitorada.
- `features_drifted`: quantidade sinalizada.
- `drift_share`: proporção de features sinalizadas.
- `drift_detected`: verdadeiro quando pelo menos
  uma feature apresenta drift.

O indicador agregado adotado pelo projeto
não deve ser confundido com o critério global
de participação de features utilizado
internamente por presets do Evidently.

Neste projeto, uma única feature sinalizada
já torna `DriftSummary.drift_detected` verdadeiro.

Não foi aplicada correção adicional para
múltiplas comparações às distâncias observadas.

Os resultados representam evidências de
mudança de distribuição, não testes de
causalidade ou de deterioração preditiva.

## 8. Resultados experimentais

As execuções utilizaram:

- Referência: 30.751 registros.
- Produção: 46.127 registros.
- Seed de simulação: 642.
- Baseline persistido e threshold congelado.
- Quality gate Pandera antes do scoring e drift.

Os três cenários foram aprovados pelo
contrato de qualidade, permitindo o
processamento dos 46.127 registros.

### 8.1. Resumo dos cenários

| Cenário | Registros modificados | Features com drift | Participação |
|---|---:|---:|---:|
| `control` | 0 | 0/16 | 0% |
| `moderate` | 23.063 | 0/16 | 0% |
| `strong` | 46.127 | 2/16 | 12,5% |

No cenário forte, as variáveis sinalizadas foram:

- `AMT_CREDIT`.
- `AMT_INCOME_TOTAL`.

As outras 14 features não foram sinalizadas
pelos critérios estatísticos utilizados.

### 8.2. Estatísticas das variáveis alteradas

Distâncias normalizadas de Wasserstein
observadas nas execuções reais:

| Cenário | AMT_CREDIT | AMT_INCOME_TOTAL |
|---|---:|---:|
| `control` | 0,010424328 | 0,014411905 |
| `moderate` | 0,078945729 | 0,081555880 |
| `strong` | 0,376913087 | 0,335614716 |

Limiar de decisão: 0,1.

No cenário controle, as duas distâncias
permaneceram abaixo do limiar.

No cenário moderado, ambas aumentaram,
mas ainda permaneceram abaixo de 0,1.

No cenário forte, as duas distâncias
ultrapassaram o limiar e geraram alertas
de drift por feature.

As estatísticas foram obtidas de uma comparação
com a referência histórica, e não de uma
comparação entre os três cenários.

### 8.3. Interpretação do cenário moderado

O cenário moderado alterou controladamente
a renda e o crédito em aproximadamente metade
dos registros.

Apesar dessas alterações, nenhuma das
16 features ultrapassou seu limiar de drift.

Isso não significa que os dados não tenham
mudado. Significa que as diferenças medidas
não atingiram o critério de sinalização
adotado nas execuções.

O experimento evidencia a importância
de interpretar o valor da estatística
juntamente com o resultado booleano.

## 9. Impacto sobre as previsões do baseline

Após o quality gate, os lotes aprovados
foram processados pelo mesmo baseline
Logistic Regression persistido.

O threshold permaneceu fixo em
`0.1406724340221902`.

Não houve retreinamento, atualização
dos pesos ou recalibração do modelo
entre os cenários.

### 9.1. Resultados agregados

| Cenário | Probabilidade média prevista | Classificações positivas | Taxa de classificação positiva |
|---|---:|---:|---:|
| `control` | 0,080410829 | 6.623 | 14,3582% |
| `moderate` | 0,085251506 | 7.376 | 15,9906% |
| `strong` | 0,107568167 | 11.141 | 24,1529% |

As classificações positivas são previsões
do modelo acima de seu threshold.

Elas não representam inadimplências
efetivamente observadas.

### 9.2. Variações em relação ao controle

| Cenário | Variação nas classificações positivas | Variação na taxa positiva |
|---|---:|---:|
| `moderate` | +753 | +1,63 ponto percentual |
| `strong` | +4.518 | +9,79 pontos percentuais |

Os resultados demonstram sensibilidade
das previsões do baseline às mudanças
sintéticas introduzidas nos lotes.

A elevação das classificações positivas
é coerente com a alteração dos atributos
de entrada, mas não demonstra que houve
aumento real da inadimplência.

### 9.3. Limites da avaliação

As previsões foram produzidas sobre
lotes simulados, sem novos rótulos
observados após a transformação.

Consequentemente, não é possível calcular
a partir desses experimentos uma degradação
real de ROC-AUC, precisão, recall ou F1.

Também não é possível demonstrar
concept drift, pois não foi verificada
uma mudança na relação condicional
entre os atributos e o desfecho real.

O experimento avalia mudanças nas
distribuições de entrada e em saídas
agregadas do modelo congelado.

## 10. Interpretação conjunta dos resultados

Os resultados mostram que data drift
e variação nas previsões não são
indicadores equivalentes.

No cenário moderado, a taxa de
classificação positiva aumentou,
mesmo sem features sinalizadas
pelo detector de drift.

No cenário forte, duas features
ultrapassaram o limiar estatístico
e a distribuição das previsões
também apresentou alterações
agregadas mais intensas.

Essas evidências são complementares,
mas não estabelecem causalidade
estatística ou deterioração
de desempenho em produção.

As principais limitações desta etapa são:

- Dados de produção simulados.
- Referência histórica não temporal.
- Ausência de novos rótulos observados.
- Limiares de drift dependentes da
  metodologia aplicada pelo Evidently.
- Possibilidade de mudanças relevantes
  abaixo do limiar de sinalização.
- Ausência de avaliação temporal contínua.
- Ausência de retreinamento automático.

A aplicação de drift deve ser entendida
como instrumento de monitoramento e
investigação, não como um mecanismo
autossuficiente de decisão sobre
qualidade preditiva ou risco de crédito.

## 11. Interface operacional de monitoramento

O Bloco 3 disponibiliza a CLI:

`scripts/monitor_drift.py`

A ferramenta possui dois subcomandos:

- `simulate`: gera um lote de produção sintético
  a partir do conjunto de teste preparado.
- `monitor`: recebe um CSV bruto compatível com
  o contrato de inferência.

Ambos utilizam a referência histórica,
o baseline persistido e os mecanismos
de qualidade e detecção de drift.

### 11.1. Simulação de produção

Exemplo de execução no cenário forte:

```bash
python scripts/monitor_drift.py \
  --reference data/processed/reference.csv \
  --model artifacts/baseline_model.joblib \
  --batch-id drift-strong-642 \
  --json-output artifacts/drift-strong.json \
  --html-output artifacts/drift-strong.html \
  simulate \
  --production-prepared data/processed/test.csv \
  --scenario strong \
  --seed 642
```

O comando exige que o diretório dos relatórios
já exista e que os arquivos de saída ainda
não estejam presentes.

Para reproduzir os outros cenários, utilizar
`--scenario control` ou `--scenario moderate`,
com identificadores e destinos de relatório
distintos.

A seed padrão da simulação é 642.

### 11.2. Monitoramento de lote externo

Exemplo:

```bash
python scripts/monitor_drift.py \
  --reference data/processed/reference.csv \
  --model artifacts/baseline_model.joblib \
  --batch-id external-example \
  --json-output artifacts/external-example.json \
  --html-output artifacts/external-example.html \
  monitor \
  --production-raw caminho/para/lote-bruto.csv
```

O lote externo deve respeitar o contrato
de entrada bruta definido no Bloco 2.

A CLI não converte automaticamente qualquer
dataset arbitrário para esse contrato.

### 11.3. Códigos de saída

| Código | Significado |
|---|---|
| `0` | Monitoramento concluído com quality gate aprovado |
| `1` | Erro operacional |
| `2` | Lote rejeitado pelo quality gate |

O código `0` não significa ausência de drift.

Um lote aprovado com drift detectado continua
retornando `0`, pois a detecção é um resultado
do monitoramento, não uma falha de execução.

O código `2` representa rejeição de qualidade
antes da análise estatística e do scoring.

Erros de arquivos, incompatibilidades operacionais
e falhas de exportação são tratados como código `1`.

## 12. Relatórios e persistência

O monitoramento aprovado pode produzir:

- Relatório JSON agregado.
- Relatório HTML gerado pelo Evidently.

As exportações são realizadas pela camada
`drift/reporting.py`.

### 12.1. Relatório JSON

O JSON reúne informações operacionais,
resultados de qualidade, estatísticas
por feature e resumo agregado das previsões.

O resumo preditivo inclui:

- Quantidade de registros pontuados.
- Probabilidade média prevista.
- Quantidade de classificações positivas.
- Taxa de classificações positivas.
- Threshold utilizado pelo baseline.

As métricas são agregadas por lote.

O JSON de monitoramento não inclui vetores
individuais de probabilidades ou previsões.

### 12.2. Relatório HTML

O HTML utiliza o snapshot do Evidently
para apresentar visualizações das
distribuições e resultados estatísticos.

Na validação real do cenário forte,
o arquivo gerado apresentou aproximadamente
4,53 MB.

A inspeção textual realizada no HTML
não encontrou as strings `SK_ID_CURR`
e `TARGET`.

Essa verificação não constitui auditoria
completa de privacidade do conteúdo.

O HTML deve ser tratado como artefato
interno, pois pode conter detalhes das
distribuições dos dados analisados.

### 12.3. Proteção contra sobrescrita

Os relatórios são gravados com criação
exclusiva, impedindo sobrescrita
silenciosa de arquivos existentes.

A CLI também verifica antecipadamente:

- Existência dos arquivos de entrada.
- Existência dos diretórios de saída.
- Colisão entre destinos JSON e HTML.
- Colisão entre saídas e arquivos de entrada.
- Existência prévia dos relatórios.

### 12.4. Tratamento de falhas

A implementação contempla:

- Remoção de JSON parcial após erro
  de escrita tratado.
- Geração temporária do HTML antes
  da cópia para o destino definitivo.
- Remoção de HTML parcialmente copiado
  quando ocorre uma exceção tratada.
- Rollback do JSON caso a etapa
  posterior de exportação HTML falhe.

Os testes verificaram esses comportamentos
com falhas simuladas e controladas.

Essa estratégia não constitui transação
atômica ou durável entre dois arquivos.

Encerramentos abruptos do processo,
falhas de energia e condições adversariais
de concorrência não estão plenamente
cobertos pelas garantias atuais.

## 13. Dependências, warnings e privacidade

### 13.1. Dependências de monitoramento

Versões utilizadas e validadas:

| Biblioteca | Versão |
|---|---|
| Python | 3.12.2 |
| Evidently | 0.7.23 |
| Litestar | 2.22.0 |
| NumPy | 2.5.4 |
| pandas | 2.3.3 |
| Pandera | 0.35.0 |
| scikit-learn | 1.9.1 |
| pytest | 9.2.0 |

O `pyproject.toml` fixa explicitamente:

- `evidently==0.7.23`
- `litestar==2.22.0`

A fixação do Litestar foi adotada
após testes de compatibilidade
devido a APIs depreciadas utilizadas
por componentes legados do Evidently.

### 13.2. Tratamento de warnings

A configuração inicial apresentava
dez warnings durante a importação
do Evidently:

- Dois relativos ao acesso a
  `numpy.core` pelo código legado.
- Oito referentes a APIs depreciadas
  do Litestar.

A utilização do Litestar 2.22.0
eliminou os oito avisos relativos
às APIs depreciadas.

Os dois avisos restantes foram
isolados por um filtro específico
na configuração do pytest.

O filtro restringe a supressão à
mensagem, à categoria e ao módulo
de origem conhecidos.

Testes adicionais confirmaram que
outros `DeprecationWarning` continuam
visíveis no relatório do pytest.

A causa dos dois avisos do NumPy
permanece no Evidently 0.7.23.

A supressão direcionada não representa
correção do código interno da biblioteca.

### 13.3. Privacidade e proteção de dados

O projeto utiliza os princípios
de minimização de dados e separação
entre informações individuais e
métricas operacionais.

O monitoramento estatístico exclui
identificadores e rótulos da lista
de features analisadas.

Os relatórios JSON publicados pela
CLI contêm resultados agregados,
sem vetores de scores individuais.

Os datasets e artefatos locais
continuam protegidos pelas regras
de exclusão do Git.

Os relatórios HTML não devem ser
publicados indiscriminadamente.

O identificador operacional `batch_id`
não deve incorporar informações pessoais.

A arquitetura demonstrada não equivale,
por si só, à conformidade integral
com a LGPD ou com processos regulatórios
de concessão de crédito.

## 14. Evidências, rastreabilidade e limites

### 14.1. Testes automatizados

Após a integração funcional do Bloco 3
na branch `main`, foi executada a suíte
completa do repositório.

Resultado verificado:

- 211 testes aprovados.
- Nenhuma falha.
- Nenhum warning exibido no pytest.
- Ruff lint aprovado.
- Ruff format aprovado.
- `pip check` sem conflitos.

A suíte contempla os Blocos 0 a 3,
incluindo testes unitários e de integração.

### 14.2. Evidências operacionais

Foram verificadas execuções reais de:

- Simulação dos cenários controle,
  moderado e forte.
- Quality gate aprovado e scoring
  nos lotes simulados.
- Rejeição de lote com crédito negativo,
  sem scoring nem relatório de sucesso.
- Detecção de drift no cenário forte.
- Exportação de JSON e HTML.
- Proteção contra sobrescrita.
- Tratamento de falhas operacionais.
- Rollback de arquivos em falhas tratadas.

Na validação final do cenário forte,
a CLI executou com sucesso sobre
46.127 registros.

A execução produziu:

- 16 features analisadas.
- 2 features com drift.
- 11.141 classificações positivas.
- Relatórios JSON e HTML válidos.

Uma execução apresentou duração total
de 14,22 segundos no ambiente local.

Esse valor é uma observação isolada,
não um benchmark de desempenho.

### 14.3. Histórico de implementação

Principais commits do Bloco 3:

| Commit | Entrega |
|---|---|
| `664a00b` | Simulação determinística de produção |
| `72e0c7a` | Merge da simulação na main |
| `de657f1` | Detecção de drift, reporting e CLI |
| `54581c2` | Merge do monitoramento na main |

As branches funcionais foram desenvolvidas
localmente, validadas e integradas à
branch principal.

### 14.4. Limitações e continuidade

O Bloco 3 entrega monitoramento estatístico
por lotes e simulação controlada.

Não implementa:

- Ingestão contínua de eventos.
- Agendamento automático de execuções.
- Prometheus e Grafana.
- Alertas operacionais persistentes.
- Retreinamento automático.
- Avaliação de desempenho com novos rótulos.
- Detecção comprovada de concept drift.
- Análise causal das alterações.
- Auditoria completa de privacidade.

Essas limitações delimitam o escopo
do bloco e orientam o desenvolvimento
dos próximos componentes.

Posteriormente, o Bloco 4 incorporou o registro de eventos
operacionais e a infraestrutura Prometheus/Grafana. A lista acima
registra os limites do **Bloco 3 na data de sua entrega**, e não
as capacidades atuais do repositório. A integração está descrita
na seção 15 e em `docs/observability.md`.

O Bloco 5 deverá aprofundar
governança, privacidade e
análises de riscos associados
ao uso do modelo.

## 15. Integração posterior com a observabilidade — Bloco 4

Esta seção documenta a instrumentação **adicionada após a conclusão
do Bloco 3**. Ela não modifica os métodos estatísticos, a simulação,
o quality gate, os resultados de referência ou os códigos de saída
descritos nas seções anteriores.

### 15.1. Registro operacional do monitoramento

A interface `scripts/monitor_drift.py` passou a aceitar a opção
`--events-db` para habilitar a persistência de eventos no SQLite.
A opção não é obrigatória nas execuções históricas: sem ela,
os fluxos estatísticos e os relatórios do Bloco 3 preservam sua
finalidade original.

Na execução instrumentada, os eventos operacionais representam o
ciclo de vida do processamento e permitem distinguir:

- Conclusão do monitoramento sem drift detectado.
- Conclusão do monitoramento com drift detectado.
- Rejeição por qualidade, antes do scoring e do detector.
- Falha operacional durante a execução.

Uma ocorrência de drift não transforma, por si só, a execução em
falha: o cenário pode terminar com status operacional `completed`
e código de saída `0`. A rejeição de qualidade mantém o código `2`
e não gera scores nem relatórios de sucesso do monitoramento.

### 15.2. Fluxo de dados até o dashboard

```text
scripts/monitor_drift.py
        |
        | --events-db
        v
artifacts/observability/events.sqlite3
        |
        v
Metrics Exporter — GET /metrics
        |
        v
Prometheus — coleta periódica
        |
        v
Grafana — Operations Overview
```

O exporter consulta os eventos persistidos; **não executa**
novos lotes de monitoramento. O Prometheus coleta métricas a
cada 15 segundos na configuração local validada, mas não agenda
as simulações nem o processamento de lotes externos.

As famílias métricas relevantes para o monitoramento incluem
`credit_risk_executions_count`, `credit_risk_drift_detected_count`,
`credit_risk_quality_violations_count`, os agregados de duração,
`credit_risk_running_executions` e o timestamp de último sucesso.
As métricas são agregadas por pipeline e não apresentam
`SK_ID_CURR`, probabilidades individuais ou `batch_id` como labels.
O catálogo completo está em `docs/observability.md`.

### 15.3. Reprodução de uma execução instrumentada

Utilizar os mesmos arquivos locais e os mesmos parâmetros já
documentados na seção 11.1, acrescentando a opção global
`--events-db` **antes** do subcomando `simulate`:

```bash
python scripts/monitor_drift.py \
  --reference data/processed/reference.csv \
  --model artifacts/baseline_model.joblib \
  --batch-id drift-strong-observability-example \
  --events-db artifacts/observability/events.sqlite3 \
  --json-output artifacts/drift-strong-observability-example.json \
  --html-output artifacts/drift-strong-observability-example.html \
  simulate \
  --production-prepared data/processed/test.csv \
  --scenario strong \
  --seed 642
```

O comando pressupõe que os dados, o modelo e o diretório local
de artefatos já existam. Os caminhos de saída e o `batch_id`
devem ser inéditos para evitar colisões com execuções anteriores.
A execução instrumentada registra novos eventos e, portanto,
pode alterar os valores cumulativos exibidos no dashboard.

O procedimento completo para iniciar a infraestrutura, verificar
o exporter, consultar PromQL e conferir o Grafana está em
`docs/reproducibility.md`, seção 16.

### 15.4. Evidências e limites de interpretação

Na demonstração operacional do Bloco 4, o histórico SQLite
continha duas execuções de `monitoring`, uma delas com drift
detectado. A duração média histórica observada para esse
pipeline foi de aproximadamente 7,947 segundos. Esses valores
representam **um snapshot local**, e não uma medição de produção
ou um benchmark de desempenho.

As métricas de contagem são `gauge` calculados sobre o histórico
SQLite. O Prometheus registra valores nos instantes de coleta;
ele não reconstrói retroativamente o horário original de cada
evento. As contagens de violações não equivalem necessariamente
à quantidade de clientes ou lotes afetados.

Essa instrumentação não comprova degradação preditiva,
concept drift, causalidade ou aumento real de inadimplência.
Também não implementa execução agendada, notificações
automáticas de alerta, retreinamento ou controles completos
de conformidade regulatória. Essas distinções são detalhadas
em `docs/observability.md`.
