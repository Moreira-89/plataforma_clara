# Backlog

Ideias do roadmap inicial do projeto que nunca foram iniciadas. Registradas
para não se perder, mas cada uma precisa de um "ainda queremos isso?" antes
de qualquer trabalho — nenhuma foi formalmente cancelada, só ficaram paradas
enquanto o projeto encolheu de escopo (saída do Reflex, do Postgres, do CSV).
Nenhum item aqui é bloqueio de nada em [Em andamento](em-andamento.md).

## Event-Driven

Fazia sentido em cima da dupla escrita Postgres + BigQuery — que não existe
mais desde que o Postgres saiu do projeto.

- Subir um broker de eventos.
- Contratos de evento versionados: `AporteIngerido`, `LoteAportesProcessado`,
  `RelatorioSolicitado`, `RelatorioPronto`, `RelatorioFalhou`.
- Padrão *outbox*: relay que publica o outbox no broker.
- Consumidor BigQuery idempotente (dedupe por `id_aporte_uuid`).
- Consumidor de invalidação de cache.
- Retry com backoff + Dead Letter Queue.
- Cache distribuído em Redis.

## Graph-as-a-Service

Relatório modelado como grafo, em vez de função sequencial. `langgraph`
nunca entrou no `requirements.txt`.

- Relatório como grafo LangGraph: buscar dados → compactar → gerar markdown
  → renderizar PDF.
- Retry de limite de token como aresta condicional, no lugar do loop atual.
- Checkpointing por `thread_id`.
- Streaming de progresso (SSE ou WebSocket).
- Grafo atrás de endpoint HTTP.
- Disparo por evento `RelatorioSolicitado`.
- Persistir os relatórios gerados em storage, em vez de bytes efêmeros.

## Operação

- Logging estruturado com correlation ID atravessando os eventos.
- Health check de dependências: `/ready` (o `/health` já existe e não consulta serviço externo).
- Métricas (Prometheus) e tracing (OpenTelemetry).
- Deploy e gestão de secrets.
- Runbook de rollback.

## Decisões em aberto — só relevantes se o backlog acima for retomado

- **Broker de eventos.** Redis Streams vs. Kafka vs. Google Pub/Sub.
- **Hospedagem dos grafos de IA.** Mesmo processo FastAPI vs. servidor
  LangGraph separado.
- **Store de checkpoint dos grafos.** Redis é a única opção hoje — Postgres
  saiu do projeto.

## Dívidas conhecidas

**PDF de referência ausente.** `agents/relatorio.py` tenta ler um PDF de
referência (exemplo *few-shot* do prompt) que não está versionado no
repositório. O código trata a ausência — segue sem o exemplo — mas o prompt
fica sem aquele trecho.

**`formatar_milhoes` erra acima de R$ 1 bilhão.** Bug conhecido, travado por
teste de caracterização: o teste documenta o comportamento atual, não
corrige o bug.

**Enumeração de e-mail, a verificar.** A autenticação anterior (removida)
distinguia "e-mail não cadastrado" de "senha errada" pelo tempo de resposta.
Vale conferir como o Firebase Auth se comporta nesse ponto antes de expor o
cadastro publicamente.
