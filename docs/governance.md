# Governança de Dados, Privacidade e LGPD — Credit Risk Monitoring

**Projeto:** Tech Challenge — Fase 4, FIAP Pós-Tech Machine Learning Engineering
**Documento:** `docs/governance.md`
**Bloco responsável:** 5 — Governança, Privacidade, Vieses e Causalidade
**Versão:** 1.0 — Governança e privacidade
**Data de referência:** 15/11/2026

---

## 1. Objetivo, escopo e classificação das evidências

Este documento descreve o tratamento de dados, os controles de privacidade e as responsabilidades de governança do projeto Credit Risk Monitoring.

O projeto utiliza o dataset Home Credit Default Risk, disponibilizado no Kaggle, para demonstrar um pipeline acadêmico de classificação de risco de crédito, validação de qualidade, detecção de data drift e observabilidade operacional.

A solução é executada localmente, com processamento por lotes e infraestrutura Docker Compose. Não realiza concessão ou recusa real de crédito, não recebe solicitações de clientes reais e não constitui sistema produtivo de uma instituição financeira.

O documento atende à dimensão de governança do Tech Challenge da FIAP, com foco em privacidade, base legal, mitigação de riscos e responsabilidade no tratamento das informações.

### 1.1. Classificação do conteúdo

Para evitar confusão entre evidência técnica, obrigação acadêmica e recomendação, adotam-se as seguintes categorias:

| Classificação | Significado |
|---|---|
| Requisito FIAP | Item solicitado pelo enunciado do Tech Challenge |
| Critério FIAP | Aspecto considerado na avaliação, incluindo Governança (15%) |
| Decisão de projeto | Escolha arquitetural adotada neste repositório |
| Implementado | Controle identificado no código ou na configuração examinados |
| Documentado | Procedimento ou resultado registrado, sem representar necessariamente execução atual |
| Proposto | Política ou controle recomendado, ainda não operacionalizado |
| Não implementado | Funcionalidade ausente da arquitetura examinada |
| Não verificado | Condição sem evidência suficiente para confirmação |

A aprovação de testes técnicos não equivale à comprovação de conformidade jurídica integral.

### 1.2. Limites da análise

A documentação foi elaborada a partir dos contratos e configurações do repositório, incluindo preparação, inferência, validação, drift, relatórios e observabilidade.

Não foram realizados testes de invasão, auditoria jurídica, análise forense de arquivos locais ou certificação de controles de segurança.

Os prazos de retenção apresentados são propostas internas do exercício acadêmico, não prazos impostos especificamente pela LGPD.

---

## 2. Arquitetura e ciclo de vida dos dados

### 2.1. Fluxo implementado

O processamento parte do dataset histórico e utiliza os seguintes componentes:

```text
Home Credit Default Risk
    |
    v
data/raw/application_train.csv
    |
    v
Preparação e particionamento
    |
    +--> train / validation / test
    |         |
    |         v
    |    Baseline LogisticRegression
    |         |
    |         v
    |    Modelo persistido
    |
    +--> reference
              |
              v
Lotes de produção simulada ou entrada externa
              |
              v
Quality gate Pandera
    |
    +---- REJEITADO
    |         |
    |         +--> Relatório de qualidade sem scores
    |
    +---- APROVADO
              |
              v
         Inferência
              |
              +--> Scores individuais (CSV opcional)
              |
              v
       Detecção de drift
       (pipeline monitoring)
              |
              +--> Relatório JSON agregado
              |
              +--> Relatório HTML Evidently

Execuções instrumentadas de scoring/monitoring
              |
              v
       Eventos operacionais SQLite
              |
              v
       Exporter GET /metrics
              |
              v
           Prometheus
              |
              +--> Regras de alerta
              |
              v
            Grafana
```

O diagrama representa os fluxos lógicos. A geração de scores individuais em CSV é opcional, e a persistência de eventos depende da execução instrumentada.

O monitoramento com Evidently é executado somente quando os contratos de qualidade permitem o processamento.

O Prometheus coleta métricas periodicamente, mas não agenda a execução dos pipelines de scoring ou drift.

### 2.2. Origem e particionamento

O arquivo `application_train.csv` possui 307.511 registros e 122 colunas.

A preparação histórica produz:

| Partição | Registros | Finalidade |
|---|---:|---|
| Train | 184.506 | Ajuste do baseline |
| Validation | 46.127 | Seleção do threshold |
| Test | 46.127 | Avaliação independente |
| Reference | 30.751 | Referência para monitoramento estatístico |

As partições são aleatórias e estratificadas, não temporais.

O conjunto de referência não possui TARGET no CSV utilizado para monitoramento. A seed padrão definida no código de preparação é 42, mas a seed efetivamente utilizada na geração histórica dos arquivos locais não foi comprovada pelo manifesto recuperado.

A seed 642 é utilizada nos cenários documentados de simulação de drift e não deve ser confundida com a seed histórica do particionamento.

---

## 3. Inventário e classificação das informações

### 3.1. Dados brutos

**Origem:** Home Credit Default Risk, Kaggle.
**Local:** `data/raw/application_train.csv`.
**Finalidade:** preparação do dataset e reprodução acadêmica.

O arquivo original reúne informações históricas relacionadas a solicitações de crédito, características financeiras, cadastrais e outros atributos.

A publicação do dataset em uma plataforma pública não comprova anonimização irreversível nem autorização irrestrita para qualquer utilização posterior.

**Situação atual:**
- Arquivo armazenado localmente.
- Diretório excluído do versionamento pelo `.gitignore`.
- Sem política de expurgo automatizado demonstrada.
- Permissões de acesso e criptografia do armazenamento local não verificadas.

**Recomendação:** restringir acesso, evitar cópias desnecessárias e eliminar o arquivo quando sua manutenção deixar de ser necessária para a finalidade acadêmica.

### 3.2. Dados processados

**Local:** `data/processed/`.

Os conjuntos processados contêm `SK_ID_CURR`, features selecionadas e, quando aplicável, TARGET.

A preparação reduz as variáveis utilizadas pelo modelo para 17 features, sendo 16 originais e um indicador derivado.

A redução do número de colunas diminui a superfície de exposição, mas não elimina automaticamente os riscos associados às informações preservadas.

O identificador `SK_ID_CURR` continua presente nas partições, embora não seja utilizado como preditor.

**Controle implementado:** separação das partições e exclusão do Git.

**Limitação:** os arquivos continuam contendo informações potencialmente pessoais ou associáveis a titulares.

### 3.3. Identificadores e atributos potencialmente pessoais

| Informação | Classificação de risco | Tratamento no projeto |
|---|---|---|
| `SK_ID_CURR` | Identificador pseudônimo ou associável | Mantido nos datasets; excluído das features do modelo |
| `TARGET` | Resultado histórico de crédito | Utilizado no treinamento e avaliação |
| `DAYS_BIRTH` | Informação relacionada à idade | Feature preditiva |
| `DAYS_EMPLOYED` | Informação sobre histórico de emprego | Feature com tratamento de sentinela |
| `AMT_INCOME_TOTAL` | Informação financeira | Feature preditiva e monitorada |
| `AMT_CREDIT` | Informação financeira | Feature preditiva e monitorada |
| `NAME_EDUCATION_TYPE` | Escolaridade | Feature preditiva e possível proxy |
| `NAME_INCOME_TYPE` | Ocupação/fonte de renda | Feature preditiva e possível proxy |
| `CNT_CHILDREN` e `CNT_FAM_MEMBERS` | Características familiares | Features preditivas |
| `EXT_SOURCE_2` e `EXT_SOURCE_3` | Indicadores externos de risco | Features preditivas com semântica externa limitada |

Outras informações do arquivo bruto não selecionadas para modelagem também exigem avaliação de privacidade enquanto o arquivo original estiver armazenado.

Não se afirma que todas essas variáveis constituam dados pessoais sensíveis na definição legal da LGPD. Entretanto, sua combinação pode permitir inferências pessoais, associações indiretas ou discriminação.

A ausência de nome ou CPF no conjunto modelado não é suficiente para comprovar anonimização.

### 3.4. Modelo e metadados

**Locais:**
- `artifacts/baseline_model.joblib`
- `artifacts/baseline_metrics.json`

O modelo persistido contém o pipeline ajustado e metadados de treinamento.

O baseline utiliza LogisticRegression com 17 features e threshold `0.1406724340221902`, selecionado pela maximização do F1 na validação.

Os artefatos estão excluídos do Git.

Embora não constituam uma exportação direta das linhas de treinamento, artefatos de modelos exigem proteção, pois podem revelar características do processo de treinamento ou estar sujeitos a riscos de extração de informações.

Arquivos joblib somente devem ser carregados de origem confiável, considerando os riscos associados à desserialização.

---

## 4. Inventário dos artefatos operacionais

| Categoria | Local ou tecnologia | Conteúdo | Controle atual |
|---|---|---|---|
| Dados brutos | `data/raw/` | Dataset histórico | Ignorado pelo Git |
| Partições | `data/processed/` | Features, identificadores e TARGET quando aplicável | Ignorado pelo Git |
| Lotes simulados | Diretórios locais de dados/artefatos | Dados derivados da referência histórica | Proteção depende do destino utilizado |
| Modelo | `artifacts/` | Pipeline e metadados | Ignorado pelo Git |
| Scores individuais | CSV opcional | Índice de linha, probabilidade e classificação | Geração opcional |
| Relatórios de qualidade | JSON | Status, estágios e violações agregadas | Sem valores individuais no contrato |
| Relatórios de drift | JSON | Resultados estatísticos por feature e resumo preditivo | Sem vetores individuais na serialização padrão |
| Snapshots Evidently | HTML | Visualizações e estatísticas de distribuição | Arquivo local, destino configurável |
| Eventos | `artifacts/observability/events.sqlite3` | Metadados operacionais | SQLite local |
| Métricas | Prometheus | Séries operacionais agregadas | Retenção de sete dias |
| Dashboards | Grafana | Consultas e visualizações operacionais | Interface local e autenticação administrativa |
| Credenciais | `.env` | Senha administrativa do Grafana | Excluído do Git |

**Importante:** os destinos de relatórios são configuráveis nas interfaces operacionais. A proteção por `.gitignore` depende do caminho e da extensão utilizada; a aplicação não demonstra uma política universal de classificação e bloqueio de caminhos inseguros.

Os volumes Docker persistentes também devem ser considerados no encerramento do ambiente acadêmico.

---

## 5. Privacidade por design e minimização

### 5.1. Controles existentes

Foram identificados os seguintes mecanismos:

1. Exclusão de dados brutos, processados e artefatos locais do Git.
2. Separação de `SK_ID_CURR` e TARGET das features preditivas.
3. Contratos Pandera que rejeitam lotes incompatíveis antes da inferência.
4. Resultados de qualidade com violações agregadas.
5. Serialização padrão de inferência sem probabilidades individuais.
6. Relatórios JSON de drift com resultados estatísticos agregados.
7. Restrição das features enviadas ao Evidently.
8. Eventos operacionais com contrato estruturado, sem campos destinados a dados cadastrais individuais.
9. Métricas Prometheus de baixa cardinalidade, sem identificadores de clientes como labels.
10. Montagem somente leitura do armazenamento SQLite no exporter.
11. Execução do exporter em ambiente de container com filesystem raiz somente leitura.
12. Publicação de Prometheus e Grafana em loopback no host.
13. Credencial administrativa do Grafana fornecida por arquivo local excluído do Git.

Esses controles reduzem riscos específicos, mas não equivalem a uma arquitetura integral de proteção de dados para produção.

### 5.2. Limitações

O objeto de inferência mantém probabilidades individuais em memória.

Sua serialização padrão não exporta esses vetores, mas o método permite inclusão explícita de scores, e a interface de scoring pode gerar CSV individual.

O CSV de scores pode ser associado ao lote original pela correspondência de linhas, mesmo sem exportar `SK_ID_CURR`.

O campo `batch_id` possui restrições sintáticas, mas não dispõe de mecanismo semântico que impeça a inclusão de informações pessoais em seu valor.

O snapshot HTML do Evidently utiliza exclusivamente as features selecionadas para monitoramento. Entretanto, pode incluir distribuições, estatísticas e categorias detalhadas, exigindo proteção contra divulgação indevida.

Não foram comprovados mecanismos de detecção automática de PII, anonimização formal, criptografia de arquivos, gestão centralizada de segredos ou controle de acesso individualizado aos datasets locais.

### 5.3. Controles adicionais propostos

Para uma evolução do projeto, recomendam-se:

- Política explícita para identificadores operacionais sem PII.
- Permissões de diretório restritas aos usuários autorizados.
- Criptografia de armazenamento quando aplicável.
- Revisão dos relatórios antes de compartilhamento.
- Controle de acesso por função.
- Redução da persistência de scores individuais.
- Processo de eliminação verificável.
- Registro de acessos e exportações, proporcional ao risco.
- Processo documentado de resposta a incidentes.

Nenhum desses itens deve ser apresentado como implementado sem evidência adicional.

---

## 6. LGPD e hipóteses de base legal

### 6.1. Enquadramento

A Lei nº 13.709/2018 estabelece princípios e hipóteses legais para o tratamento de dados pessoais.

O projeto utiliza informações históricas disponibilizadas em um dataset público, mas não realiza avaliação jurídica da cadeia original de coleta, das condições de anonimização ou das bases legais utilizadas pelos fornecedores dos dados.

A disponibilização pública não implica autorização irrestrita de tratamento.

Deve-se observar também as condições e termos de utilização do dataset disponibilizado pelo Kaggle.

### 6.2. Contexto acadêmico

A finalidade deste projeto é educacional: desenvolver e demonstrar mecanismos de monitoramento e governança de Machine Learning.

A finalidade acadêmica, isoladamente, não comprova uma hipótese legal aplicável a todas as operações.

A hipótese de realização de estudos por órgão de pesquisa, prevista na LGPD, possui condições e definições próprias e não deve ser automaticamente atribuída a qualquer projeto individual ou atividade acadêmica.

A avaliação jurídica dependeria da natureza da instituição responsável, da condição dos dados, dos agentes de tratamento, da finalidade efetiva e das demais circunstâncias.

Neste projeto, adotam-se medidas de minimização e restrição de divulgação como práticas preventivas, sem declaração de conformidade jurídica integral.

### 6.3. Cenário hipotético de uma fintech

Caso uma fintech brasileira utilizasse uma solução semelhante para analisar solicitações de crédito reais, seria necessário definir as hipóteses legais aplicáveis a cada finalidade de tratamento.

Entre as possibilidades a examinar estão:

| Hipótese | Aplicação potencial | Limitação |
|---|---|---|
| Proteção do crédito — art. 7º, X | Tratamento relacionado à avaliação e proteção do crédito | Não dispensa finalidade, necessidade, transparência e demais requisitos |
| Execução de contrato ou procedimentos preliminares — art. 7º, V | Solicitação de crédito e procedimentos relacionados ao contrato | Depende da relação concreta com o titular e da necessidade dos dados |
| Cumprimento de obrigação legal ou regulatória — art. 7º, II | Tratamentos exigidos por normas aplicáveis à instituição | Exige identificação da obrigação específica |
| Legítimo interesse — art. 7º, IX | Determinadas finalidades compatíveis, mediante avaliação apropriada | Exige necessidade, ponderação de direitos e salvaguardas; não se aplica a dados pessoais sensíveis |

A base legal deve ser avaliada por finalidade e operação. A proteção do crédito não autoriza automaticamente reutilizações incompatíveis, exposição pública de scores ou tratamento indiscriminado de atributos.

Na eventual presença de dados pessoais sensíveis, seria necessária análise específica das hipóteses previstas no artigo 11.

Não se deve presumir que consentimento seja obrigatório ou suficiente para todas as operações de crédito.

### 6.4. Princípios relevantes

A governança proposta considera:

- **Finalidade:** utilização para objetivos legítimos, específicos e informados.
- **Adequação:** compatibilidade entre tratamento e finalidade.
- **Necessidade:** limitação ao mínimo necessário.
- **Livre acesso e transparência:** informações apropriadas aos titulares.
- **Qualidade dos dados:** precisão e atualização conforme a finalidade.
- **Segurança e prevenção:** redução dos riscos de acesso indevido, perda e divulgação.
- **Não discriminação:** prevenção de tratamentos discriminatórios ilícitos ou abusivos.
- **Responsabilização e prestação de contas:** demonstração de medidas adotadas.

Os contratos Pandera contribuem para determinadas dimensões de qualidade, mas não comprovam isoladamente o cumprimento de todos esses princípios.

---

## 7. Direitos dos titulares e decisões automatizadas

### 7.1. Direitos aplicáveis em cenário real

Em um sistema de crédito efetivamente operacional, seria necessário estabelecer procedimentos para atender, conforme os requisitos legais aplicáveis:

- Confirmação da existência de tratamento.
- Acesso aos dados.
- Correção de informações incompletas ou inexatas.
- Solicitações cabíveis de anonimização, bloqueio ou eliminação.
- Informações sobre compartilhamento.
- Oposição ao tratamento nas hipóteses legais pertinentes.
- Portabilidade, quando aplicável.
- Revisão de decisões tomadas unicamente com base em tratamento automatizado, nos termos do artigo 20.

O exercício desses direitos não significa eliminação automática e irrestrita de todos os registros. Devem ser consideradas as hipóteses legais de conservação e as obrigações aplicáveis.

### 7.2. Decisões automatizadas

O artigo 20 da LGPD contempla o direito de solicitar revisão de decisões tomadas unicamente com base em tratamento automatizado de dados pessoais que afetem interesses do titular, incluindo decisões relacionadas a perfil de crédito.

O controlador também deve observar os requisitos relativos a informações claras e adequadas sobre critérios e procedimentos utilizados, consideradas as limitações legais pertinentes.

O Credit Risk Monitoring não implementa mecanismo de aprovação ou rejeição de crédito real.

O threshold do baseline é uma regra experimental de classificação selecionada por F1, não uma política econômica ou jurídica de concessão de crédito.

### 7.3. Fluxo hipotético de atendimento

Uma instituição financeira real deveria:

1. Disponibilizar canal apropriado ao titular.
2. Identificar e autenticar o solicitante de maneira proporcional.
3. Localizar os tratamentos e registros relevantes.
4. Avaliar a solicitação e suas condições legais.
5. Encaminhar pedidos de revisão de decisões quando aplicáveis.
6. Corrigir, restringir ou eliminar dados quando cabível.
7. Registrar a conclusão e comunicar o resultado.
8. Considerar cópias, relatórios derivados e backups conforme a política de retenção.

**Status:** fluxo recomendado e não implementado no projeto acadêmico.

---

## 8. Política proposta de retenção e descarte

### 8.1. Princípio geral

Os dados devem ser mantidos somente pelo período necessário às finalidades legítimas e às obrigações aplicáveis, com revisão dos motivos de conservação.

Para o projeto acadêmico, propõe-se uma política operacional simplificada, condicionada à preservação das evidências necessárias à avaliação e reprodução.

Os prazos abaixo não são imposições legais universais.

### 8.2. Matriz de retenção

| Categoria | Retenção proposta | Controle atual | Descarte previsto |
|---|---|---|---|
| Dataset bruto | Até 30 dias após encerramento e aceite da entrega | Local, sem expurgo automático | Exclusão controlada |
| Partições processadas | Até 30 dias após encerramento e aceite | Local, sem expurgo automático | Exclusão controlada |
| Lotes simulados | Até 30 dias após a execução, salvo necessidade de evidência | Local, sem expurgo automático | Exclusão após revisão |
| Scores individuais | Até 30 dias após a execução, preferencialmente menos | Exportação opcional, sem expurgo automático | Eliminação dos CSVs |
| Relatórios JSON/HTML | Até 90 dias após a execução, quando necessários para auditoria acadêmica | Sem expurgo automático | Revisão e eliminação |
| Eventos SQLite | Até 90 dias após a execução | Persistência local, sem TTL | Expurgo ou eliminação do banco ao encerrar |
| Séries Prometheus | 7 dias | Configurado no Docker Compose | Retenção gerenciada pelo Prometheus |
| Volume Grafana | Até o encerramento e aceite da entrega, salvo justificativa | Volume persistente | Remoção controlada do volume |
| Modelo e metadados | Até 90 dias após encerramento e aceite da entrega, salvo necessidade justificada | Arquivos locais | Exclusão controlada |
| Credenciais | Durante a necessidade operacional | `.env` local | Revogação e eliminação ao encerrar |

O marco de encerramento e aceite deverá ser registrado pelo responsável pelo projeto.

A execução da política exige revisão prévia de eventuais obrigações de conservação, necessidades de reprodução e cópias existentes.

### 8.3. Diferenças entre os armazenamentos

A retenção de sete dias do Prometheus diz respeito às séries temporais mantidas por esse serviço.

Ela não implica eliminação de:
- Eventos armazenados no SQLite.
- Relatórios JSON ou HTML.
- Datasets brutos ou processados.
- Scores individuais.
- Metadados persistidos no Grafana.
- Backups ou cópias eventualmente existentes.

Esses recursos possuem ciclos de vida independentes.

### 8.4. Procedimento de descarte proposto

Antes de eliminar informações:

1. Identificar a categoria e sua finalidade.
2. Verificar o prazo e a necessidade de conservação.
3. Identificar arquivos, volumes e cópias.
4. Confirmar que não há dependência operacional ou obrigação de preservação.
5. Executar descarte por mecanismo apropriado ao armazenamento.
6. Registrar o procedimento e suas exceções.
7. Verificar o resultado quando tecnicamente possível.

O descarte simples de arquivos não garante, em todos os meios de armazenamento, eliminação forense irrecuperável.

Não foi implementado script automático de expurgo, destruição criptográfica ou gerenciamento de backups neste bloco.

A remoção indiscriminada de volumes Docker pode destruir evidências necessárias à reprodução e não deve ser executada como rotina sem avaliação prévia.

---

## 9. Controle de acesso e segurança

### 9.1. Controles efetivamente identificados

O projeto utiliza um ambiente local Windows e containers Docker.

No Docker Compose:
- O exporter acessa o diretório de eventos por montagem somente leitura.
- O filesystem raiz do exporter é configurado como somente leitura.
- A porta HTTP do exporter não é publicada diretamente no host.
- Prometheus e Grafana possuem portas publicadas em `127.0.0.1`.
- O Grafana recebe senha administrativa por variável de ambiente.
- O cadastro público de usuários do Grafana está desabilitado.
- O Prometheus e o Grafana utilizam volumes persistentes.

O arquivo `.env` é excluído do Git.

As métricas operacionais não utilizam identificadores individuais de clientes como labels.

Essas decisões reduzem superfícies de exposição dentro do ambiente demonstrado.

### 9.2. Limitações de segurança

Não há evidência de implementação de:

- Autenticação completa para exposição externa do Prometheus.
- TLS na arquitetura local.
- Gestão centralizada de usuários e permissões.
- Gestão centralizada de segredos.
- Rotação automática de credenciais.
- Backup automatizado e testado.
- Expurgo automático de dados.
- Monitoramento de acessos aos arquivos do host.
- Controle corporativo de dispositivos.
- Processo operacional completo de resposta a incidentes.

O uso de loopback não substitui controles de produção para uma eventual exposição em rede.

### 9.3. Responsabilidades hipotéticas

| Papel | Responsabilidade proposta |
|---|---|
| Controlador | Definir finalidades, hipóteses legais e políticas |
| Responsável por dados | Gerenciar qualidade, classificação, retenção e acesso |
| Responsável pelo modelo | Avaliar desempenho, explicabilidade e riscos de viés |
| Segurança da informação | Definir controles técnicos e resposta a incidentes |
| Jurídico/privacidade | Avaliar bases legais, direitos e obrigações |
| Operações/MLOps | Monitorar execuções, drift e alertas |

No projeto acadêmico, essas funções são conceituais e não representam uma equipe formalmente constituída.

---

## 10. Riscos residuais e medidas recomendadas

| Risco | Situação atual | Medida recomendada | Prioridade proposta |
|---|---|---|---|
| Divulgação de datasets históricos | Proteção por `.gitignore` | Revisão de caminhos, acesso e cópias | Alta |
| Reidentificação por combinação de atributos | Não há anonimização comprovada | Minimização e avaliação do risco de reidentificação | Alta |
| Exposição de scores individuais | CSV opcional | Restringir persistência e compartilhamento | Alta |
| Identificador pessoal em `batch_id` | Validação apenas sintática | Política operacional e verificação de identificadores | Média |
| Compartilhamento de HTML Evidently | Exportação local possível | Revisão do conteúdo e acesso restrito | Média |
| Retenção indefinida do SQLite | Sem expurgo automático | Política e rotina de descarte | Alta |
| Persistência de volumes Docker | Volumes nomeados | Inventário e encerramento controlado | Média |
| Exposição externa da stack | Configuração voltada ao ambiente local | Autenticação, TLS e revisão de rede antes de produção | Alta |
| Uso indevido do modelo em decisão real | Sistema acadêmico | Validação jurídica, econômica, temporal e de fairness | Alta |
| Inferências discriminatórias | Atributos e proxies presentes | Avaliação de vieses por grupos e mitigação | Alta |

As prioridades são propostas de governança, não resultados de uma matriz quantitativa formal de risco.

As análises específicas de fairness e causalidade serão aprofundadas na etapa seguinte do Bloco 5.

---

## 11. Evidências e rastreabilidade

| Aspecto | Evidência técnica | Classificação |
|---|---|---|
| Seleção de features | `src/credit_risk_monitoring/data/preparation.py` | Implementado |
| Inferência bloqueante | `src/credit_risk_monitoring/modeling/inference.py` | Implementado |
| Resultados de qualidade | `src/credit_risk_monitoring/quality/results.py` | Implementado |
| Orquestração de drift | `src/credit_risk_monitoring/drift/monitoring.py` | Implementado |
| Estatísticas por feature | `src/credit_risk_monitoring/drift/detection.py` e `drift/results.py` | Implementado |
| Exportação de relatórios | `src/credit_risk_monitoring/drift/reporting.py` | Implementado |
| Eventos operacionais | `src/credit_risk_monitoring/observability/events.py` | Implementado |
| Persistência SQLite | `src/credit_risk_monitoring/observability/store.py` | Implementado |
| Isolamento e retenção Prometheus | `compose.yaml` | Configurado |
| Proteção contra versionamento | `.gitignore` | Implementado como configuração |
| Política geral de retenção | Este documento | Proposto |
| Atendimento a direitos dos titulares | Este documento | Proposto |
| Avaliação jurídica completa | Não realizada | Não implementado |
| Expurgo automático | Não identificado | Não implementado |

A verificação aqui apresentada corresponde à leitura estática dos arquivos disponibilizados durante o Bloco 5.

Não equivale à execução de uma auditoria de segurança.

---

## 12. Limitações, decisões e continuidade

### 12.1. Decisões adotadas

1. Manter a implementação funcional dos Blocos 0 a 4 inalterada.
2. Consolidar a governança em documentação específica.
3. Utilizar inventário baseado nos artefatos reais do projeto.
4. Distinguir controles implementados e propostos.
5. Não criar mecanismo automático de expurgo nesta etapa.
6. Não incorporar novas dependências de privacidade.
7. Não alterar features, modelo ou threshold.
8. Não alegar conformidade jurídica integral.

### 12.2. Limitações acadêmicas

O projeto não demonstra:
- Decisões reais de crédito.
- Validação temporal com novos dados produtivos.
- Base legal efetivamente definida para tratamento por uma fintech real.
- Anonimização formal do dataset.
- Atendimento operacional aos direitos de titulares.
- Certificação LGPD.
- Auditoria independente de segurança.
- Controles corporativos de acesso, retenção e descarte.

A existência de contratos de qualidade, métricas operacionais e documentação de governança não elimina os riscos inerentes à utilização de modelos de crédito.

### 12.3. Continuidade do Bloco 5

A avaliação de vieses e a discussão causal serão aprofundadas posteriormente, contemplando:

- Atributos de grupo realmente disponíveis.
- Proxies potenciais e riscos de discriminação.
- Representatividade e grupos com poucas observações.
- Disparidades preditivas, quando mensuradas.
- Mitigação e limites de interpretação.
- Causalidade conceitual das alterações simuladas.
- Distinção entre data drift, concept drift e desempenho observado.

Nenhuma conclusão quantitativa de fairness ou causalidade está sendo apresentada nesta versão.

---

## 13. Referências

### Legislação e orientação institucional

- Lei Geral de Proteção de Dados Pessoais — Lei nº 13.709/2018: https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm
- Autoridade Nacional de Proteção de Dados — Perguntas frequentes: https://www.gov.br/anpd/pt-br/acesso-a-informacao/perguntas-frequentes
- ANPD — Guia orientativo de legítimo interesse: https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/guia_orientativo_hipoteses_legais_tratamento_de_dados_pessoais_legitimo_interesse

### Dataset

- Home Credit Default Risk — Kaggle: https://www.kaggle.com/competitions/home-credit-default-risk/data

### Documentação interna

- [Arquitetura](architecture.md)
- [Reprodutibilidade](reproducibility.md)
- [Contratos de qualidade](quality-contracts.md)
- [Monitoramento de drift](drift-monitoring.md)
- [Observabilidade](observability.md)

---

**Estado documental:** política acadêmica proposta, baseada nos controles identificados na arquitetura local. Este documento não constitui parecer jurídico, comprovação de anonimização ou certificação de conformidade LGPD.
