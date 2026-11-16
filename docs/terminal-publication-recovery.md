# Terminal Event Persistence and Artifact Recovery

## 1. Objetivo

Este documento descreve a estrategia de publicacao de artefatos
e persistencia de eventos terminais das CLIs instrumentadas de
scoring e monitoramento de drift.

A estrategia foi introduzida para tratar o achado AUD-001,
relacionado a inconsistencias entre arquivos publicados e o
estado operacional persistido no SQLite.

## 2. Escopo

Componentes:

- `src/credit_risk_monitoring/observability/execution.py`
- `src/credit_risk_monitoring/observability/publication.py`
- `src/credit_risk_monitoring/observability/store.py`
- `scripts/score_batch.py`
- `scripts/monitor_drift.py`

A correcao nao altera os algoritmos de scoring, deteccao
de drift ou validacao de qualidade.

## 3. Ordem de execucao

A execucao instrumentada segue esta sequencia:

1. Persistir evento inicial com status `running`.
2. Executar o pipeline de scoring ou monitoramento.
3. Publicar os artefatos aplicaveis.
4. Registrar a identidade dos arquivos publicados.
5. Construir o evento terminal.
6. Persistir o evento terminal no SQLite.
7. Somente apos confirmacao do retorno de `finish()`,
   anunciar o resultado ao usuario.

A publicacao dos arquivos antecede a persistencia do evento
terminal. Portanto, nao existe transacao atomica envolvendo
simultaneamente SQLite e filesystem.

## 4. Falha na persistencia terminal

Quando `store.finish()` lanca uma excecao durante a persistencia
do evento de sucesso:

1. A excecao nao e interpretada automaticamente como falha
   do commit.
2. O executor consulta o evento persistido pelo `execution_id`.
3. Se o evento permanecer em `running`, tenta compensar os
   arquivos registrados.
4. Se a consulta falhar ou nao confirmar `running`, preserva
   os arquivos para reconciliacao.
5. A excecao e propagada ao chamador.

Uma excecao apos um commit efetivo pode resultar em evento
`completed` no SQLite, arquivos preservados e retorno de erro
operacional na CLI.

Esse comportamento conservador e intencional: o processo
nao declara sucesso quando a confirmacao da persistencia
terminal foi ambigua.

## 5. Identidade e compensacao de arquivos

O `PublicationTracker` registra metadados do arquivo
publicado, incluindo identificadores e atributos do filesystem.

Antes da remocao, verifica se os metadados continuam
compativeis com os registrados.

- Arquivos registrados e inalterados podem ser compensados.
- Arquivos substituidos ou modificados nao devem ser removidos
  pela compensacao quando a divergencia for detectada.
- Arquivos sem identidade confirmada sao preservados para
  reconciliacao manual.
- Falhas na compensacao sao propagadas; nao sao tratadas
  como recuperacao concluida.

A verificacao de identidade seguida de `unlink()` nao e
atomica. Existe uma janela de concorrencia entre ambas as
operacoes.

O mecanismo e uma compensacao de melhor esforco, nao uma
garantia de atomicidade nem um protocolo transacional
distribuido.

## 6. Falha durante publicacao

Nas CLIs instrumentadas:

- Arquivos ja registrados podem ser compensados pelo tracker.
- Arquivos criados sem registro confirmado sao preservados.
- A falha operacional pode ser persistida como evento `failed`,
  desde que a persistencia correspondente esteja disponivel.
- Nao ha anuncio de sucesso para a tentativa com falha.

O comportamento legado de limpeza das execucoes sem
instrumentacao permanece separado da compensacao rastreada.

## 7. Reconciliacao operacional

Quando houver falha operacional ou discrepancia entre SQLite
e arquivos de saida:

1. Identificar o `execution_id` e o `batch_id` da tentativa.
2. Consultar o evento correspondente no SQLite.
3. Verificar `execution_status`, `exit_code` e demais metadados.
4. Inspecionar a existencia e o conteudo dos arquivos esperados.
5. Confirmar que os arquivos pertencem a tentativa analisada.
6. Preservar evidencias antes de qualquer limpeza manual.
7. Remover ou arquivar arquivos remanescentes somente apos
   confirmar que nao pertencem a outra execucao.

Nao presumir que a ausencia de arquivos implica inexistencia
de evento terminal, nem que a existencia de arquivos implica
sucesso da tentativa.

Um evento `running` pode representar uma execucao interrompida
ou uma falha de persistencia terminal. O estado exige
investigacao antes de nova tentativa.

## 8. Reexecucao

As rotinas de exportacao utilizam criacao exclusiva de arquivos
de saida. Portanto, arquivos remanescentes podem impedir uma
nova tentativa usando os mesmos caminhos.

Recomendacoes:

- Preferir caminhos de saida distintos para novas tentativas.
- Investigar o estado anterior antes de qualquer remocao.
- Nao sobrescrever automaticamente arquivos existentes.
- Nao alterar manualmente eventos do SQLite sem um
  procedimento de reconciliacao formal.

## 9. Codigos de saida

O contrato operacional das CLIs preserva:

- `0`: execucao concluida com sucesso, inclusive quando ha
  drift detectado.
- `2`: lote rejeitado pelo gate de qualidade, quando aplicavel.
- `1`: falha operacional.

Uma rejeicao de qualidade nao deve ser confundida com
falha operacional. Um evento terminal pode estar
`completed` mesmo quando o exit code e `2`.

## 10. Limitacoes conhecidas

A solucao nao oferece:

- Commit atomico entre SQLite e filesystem.
- Protecao integral contra alteracoes concorrentes de arquivos.
- Recuperacao automatica de todas as tentativas interrompidas.
- Garantia de exclusao de todo arquivo parcial.
- Garantia de reexecucao automatica com os mesmos caminhos.

A reconciliacao manual continua necessaria em determinados
cenarios de falha.

## 11. Evidencias de teste

Os testes automatizados cobrem cenarios simulados de:

- Falha de `finish()` antes do commit terminal.
- Falha de consulta do SQLite apos erro terminal.
- Excecao posterior a um commit efetivo.
- Preservacao de arquivos substituidos.
- Falha durante compensacao.
- Falha de registro de identidade.
- Ausencia de anuncio prematuro de sucesso.
- Sanitizacao de falhas operacionais nas CLIs.

Arquivos de teste relevantes:

- `tests/unit/test_observability_execution.py`
- `tests/unit/test_observability_publication.py`
- `tests/unit/test_observed_scoring_cli.py`
- `tests/unit/test_observed_drift_cli.py`

Esses testes validam os cenarios simulados. Nao constituem
prova de atomicidade ou ausencia de condicoes de corrida.
