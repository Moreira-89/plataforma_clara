# Roadmap

O que já existe, o que está em andamento e o que ainda precisa de decisão.
Esta é a página que muda toda semana — os outros três pilares (Visão Geral,
Produto, Arquitetura) descrevem o que é mais estável.

## Próximos passos, em ordem de prioridade

1. **Fonte dos dados de aportes.** A decisão mais urgente do projeto. O
   upload manual de CSV foi removido — não é assim que a plataforma vai
   operar com usuários reais. Falta decidir de onde os dados vêm
   (provavelmente consulta a um serviço externo que já os tenha) e como
   chegam ao BigQuery. Nada escreve em `tb_aporte` hoje, e o relatório por IA
   já depende disso e está quebrado por consequência.
2. **Agregação do dashboard (BigQuery).** Depende do item 1. A ideia é o
   dashboard ler o BigQuery via tabela(s) "gold", recriadas sob demanda —
   não em tempo real, não só por job agendado. Falta decidir a granularidade
   (uma tabela gold por consulta vs. uma única e granular) e se a recriação
   também dispara automático após cada carga de dado nova. Adiado de
   propósito: o time vai mexer bastante no dashboard, então desenhar a
   agregação antes disso estabilizar seria trabalho jogado fora.
3. **Firebase Auth.** Não há verificação de token nem rota protegida ainda.
4. **Endpoints.** Nenhum hoje — nem `/health`. `api/endpoints/authentication.py`
   e `register.py` existem como arquivo, vazios.
5. **Firestore.** Nada implementado. Reservado para o vínculo Firebase UID ↔
   CPF/CNPJ do investidor — pode nem precisar de banco separado, se virar
   *custom claim* no token.
6. **Redis.** Sobe no `docker-compose`, sem cliente na aplicação ainda.
7. **CORS.** Sem middleware. Necessário quando o frontend chamar a API de
   outro domínio.
8. **Frontend.** Só a casca hoje (Vite, Dockerfile, proxy de desenvolvimento).
   Nenhuma tela.

O que já está pronto para os itens 3–4 chamarem:

- `agents.relatorio.gerar_relatorio_consolidado_investidor` — PDF por IA
  (hoje sempre falha, ver item 1)
- `domain.metricas` — consolidação de KPIs e montagem das visões (sem quem
  as alimente, ver item 2)

## Decisões em aberto

- **Broker de eventos.** Redis Streams vs. Kafka vs. Google Pub/Sub. Só
  relevante se a visão "Event-Driven" abaixo for retomada.
- **Hospedagem dos grafos de IA.** Mesmo processo FastAPI vs. servidor
  LangGraph separado. Só relevante se "Graph-as-a-Service" abaixo for
  retomada.
- **Store de checkpoint dos grafos.** Redis é a única opção hoje — Postgres
  saiu do projeto. Só relevante se "Graph-as-a-Service" for retomada.

## Visão original — não retomada, confirmar se ainda vale

Ideias do roadmap inicial do projeto que nunca foram iniciadas. Registradas
para não se perder, mas cada uma precisa de um "ainda queremos isso?" antes
de qualquer trabalho — nenhuma foi formalmente cancelada, só ficaram paradas
enquanto o projeto encolheu de escopo (saída do Reflex, do Postgres, do CSV).

- **Event-Driven.** Broker de eventos, padrão *outbox*, contratos de evento
  versionados (`AporteIngerido`, `RelatorioSolicitado`, etc.), consumidores
  idempotentes. Fazia sentido em cima da dupla escrita Postgres + BigQuery —
  que não existe mais desde que o Postgres saiu do projeto.
- **Graph-as-a-Service.** Relatório modelado como grafo (LangGraph), com
  checkpointing, streaming de progresso e retry como aresta condicional.
  `langgraph` nunca entrou no `requirements.txt`.
- **Operação.** Logging estruturado com correlation ID, métricas
  (Prometheus), tracing (OpenTelemetry), runbook de rollback.

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
