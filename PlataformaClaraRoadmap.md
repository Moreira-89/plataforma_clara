# Roadmap — Plataforma Clara

> Migração de **Reflex (monolito full-stack)** para **FastAPI + arquitetura Event-Driven + Graph-as-a-Service**.
>
> Este documento é a fonte única de verdade sobre o que já existe, o que falta e em qual branch cada frente é atacada.
> Atualizar ao concluir cada item — marcar `[x]` e anotar a data.

**Última atualização:** 2026-08-25

---

## 1. Onde estamos hoje (baseline)

Estado do `main` no momento em que a migração começou. Tudo abaixo **já está implementado e funcionando** em Reflex.

### 1.1 Domínio e dados

- [x] Modelagem de `tb_usuario` e `tb_aporte` (SQLModel sobre SQLAlchemy) — `model/schemas.py`
- [x] 6 migrations Alembic versionadas — `alembic/versions/`
- [x] Dupla persistência: PostgreSQL (Supabase, OLTP) + BigQuery (`dados_fidc.tb_aporte`, OLAP)
- [x] Utilitário centralizado de credenciais GCP com dois modos (JSON inline ou caminho de arquivo) — `services/bigquery_utils.py`

### 1.2 Fluxo de ingestão (gestora)

- [x] Upload de CSV com validação de 19 colunas obrigatórias — `services/csv_processor.py`
- [x] Descarte de linhas sem CNPJ / valor / documento do investidor (colunas críticas)
- [x] Coerção de tipos: 6 colunas numéricas, 2 colunas de data
- [x] Geração de UUID novo por linha (nunca reutiliza o `id_aporte_uuid` do CSV — evita colisão em re-upload)
- [x] `bulk_insert_mappings` no Postgres
- [x] Envio ao BigQuery em `WRITE_APPEND` com schema explícito, como background task

### 1.3 Dashboards

- [x] Agregações SQL por `bloco_liquidez_setorial` (SUM valor, AVG score, COUNT aportes)
- [x] Visão da gestora (consolidada) e visão do investidor (filtrada por documento)
- [x] Página de detalhes de bloco com rota dinâmica `[bloco_id]`
- [x] Explorar blocos com filtros de busca, setor e score
- [x] Cache em memória com TTL de 5 min nas 3 consultas pesadas

### 1.4 Relatório por IA

- [x] Busca de dados no Postgres + BigQuery (query parametrizada, sem concatenação de SQL)
- [x] Prompt institucional de Analista Sênior de Risco de Crédito
- [x] Compactação progressiva do payload em 5 níveis para caber no limite de tokens
- [x] Retry automático em `APIStatusError` 413 reduzindo a amostra
- [x] Renderização Markdown → PDF e download dos bytes

### 1.5 Autenticação e UI

- [x] Cadastro com hash bcrypt (12 rounds) e normalização de CPF/CNPJ
- [x] Login com validação de credenciais e redirecionamento por perfil
- [x] 8 páginas Reflex, sidebars reutilizáveis, identidade visual com logo

---

## 2. Dívidas técnicas conhecidas (auditoria de 2026-08-25)

Levantadas na análise inicial. Algumas somem de graça com a nova arquitetura; outras precisam de ação explícita.

| # | Dívida | Gravidade | Resolvida por |
|---|---|---|---|
| D1 | Autenticação vive só em memória (`rx.State`), sem token. Não é portável para FastAPI. | 🔴 Alta | `feat/auth-jwt` |
| D2 | Rotas `/dashboard-gestora` e `/dashboard-investidor` sem guard — renderizam para qualquer visitante. | 🔴 Alta | `feat/auth-jwt` |
| D3 | Dupla escrita PG + BigQuery sem garantia transacional: falha no BQ diverge os dados em silêncio. | 🔴 Alta | `feat/outbox-pattern` |
| D4 | Caches globais de módulo não sobrevivem a múltiplos workers Uvicorn. | 🟡 Média | `feat/redis-cache` |
| D5 | Zero testes automatizados — nenhuma rede de segurança para refatorar. | 🔴 Alta | `chore/test-harness` |
| D6 | Sem Dockerfile, sem CI, sem pipeline de deploy. | 🟡 Média | `chore/docker-ci` |
| D7 | `services/` acoplado ao `rx.session()` do Reflex. | 🟡 Média | `refactor/domain-extraction` |
| D8 | `langgraph` declarado no `requirements.txt` mas nunca importado. | 🟢 Baixa | `feat/graph-service` |
| D9 | PDF de referência do prompt (`Relatório de Insights Financeiros FIDC - Google Gemini.pdf`) não existe no repo. | 🟢 Baixa | `feat/graph-service` |
| D10 | `CLAUDE.md` diverge do código: cita WeasyPrint (é `markdown-pdf`), scikit-learn e modelo `.pkl` (não existem — `score_risco_interno` vem pronto do CSV). | 🟢 Baixa | `docs/align-claude-md` |
| D11 | `requirements.txt` sem lock file e sem separação dev/prod. | 🟢 Baixa | `chore/docker-ci` |

---

## 3. Decisões de arquitetura pendentes

**Bloqueiam o desenho detalhado.** Registrar a decisão aqui assim que fechada (formato ADR curto: decisão + porquê).

- [ ] **AD-1 — Escopo do frontend.** Reescrever em React/Next.js ou o escopo atual é só a API (frontend depois)?
- [ ] **AD-2 — Broker de eventos.** Redis Streams (barato, simples, cabe no MVP) vs. Kafka (vitrine para a banca, mais operação) vs. Google Pub/Sub (já estamos em GCP).
- [ ] **AD-3 — Hospedagem do Graph-as-a-Service.** Grafos no mesmo processo FastAPI vs. LangGraph Server como serviço separado.
- [ ] **AD-4 — Store de checkpoint dos grafos.** Postgres (reaproveita Supabase) vs. Redis.
- [ ] **AD-5 — Estratégia de corte.** Big bang vs. strangler fig (Reflex e FastAPI coexistindo enquanto as rotas migram uma a uma).

---

## 4. Backlog de migração

### Fase 0 — Fundação `chore/test-harness`, `chore/docker-ci`, `docs/align-claude-md`

Sem isso, refatorar é apostar. Vem antes de tocar em qualquer código de domínio.

- [ ] pytest + pytest-asyncio configurados
- [ ] Testes de caracterização dos 3 fluxos (ingestão, dashboard, relatório) — capturam o comportamento **atual**, mesmo o esquisito
- [ ] Fixtures de banco (Postgres em container) e mocks de BigQuery/Groq
- [ ] Dockerfile + docker-compose (app, postgres, redis)
- [ ] GitHub Actions: lint (ruff) + testes em PR
- [ ] Corrigir divergências do `CLAUDE.md` (D10)
- [ ] Separar `requirements-dev.txt` / lock file (D11)

### Fase 1 — Extração do domínio `refactor/domain-extraction`

Objetivo: `services/` puro, sem nenhum import de `reflex`.

- [ ] Camada de repositório para `tb_usuario` e `tb_aporte` (SQLAlchemy puro)
- [ ] Trocar `rx.session()` por `Session` injetada via dependência
- [ ] Extrair `model/schemas.py` para SQLModel/SQLAlchemy sem `rx.Model`
- [ ] Schemas Pydantic v2 de entrada/saída, separados dos modelos de tabela
- [ ] Mover regra de negócio que hoje vive em `states/` (cálculo de KPIs, filtros) para o domínio

### Fase 2 — API FastAPI `feat/fastapi-skeleton`, `feat/auth-jwt`

- [ ] Esqueleto FastAPI: `main.py`, routers, settings via `pydantic-settings`, lifespan
- [ ] Autenticação JWT (access + refresh), `OAuth2PasswordBearer` (D1)
- [ ] Middleware/dependência de autorização por perfil — gestora vs. investidor (D2)
- [ ] `POST /auth/login`, `POST /auth/register`, `POST /auth/refresh`
- [ ] `POST /aportes/upload` (CSV)
- [ ] `GET /dashboard/gestora`, `GET /dashboard/investidor`
- [ ] `GET /blocos`, `GET /blocos/{bloco_id}`
- [ ] `POST /relatorios` (dispara) + `GET /relatorios/{id}` (consulta/baixa)
- [ ] OpenAPI documentado, CORS configurado

### Fase 3 — Event-Driven `feat/event-bus`, `feat/outbox-pattern`, `feat/consumers`

- [ ] Escolher e subir o broker (depende de **AD-2**)
- [ ] Contratos de evento versionados (Pydantic): `AporteIngerido`, `LoteAportesProcessado`, `RelatorioSolicitado`, `RelatorioPronto`, `RelatorioFalhou`
- [ ] Tabela `outbox` + gravação na mesma transação da escrita no Postgres (D3)
- [ ] Relay que publica o outbox no broker (polling ou CDC)
- [ ] Consumidor BigQuery idempotente (dedupe por `id_aporte_uuid`)
- [ ] Consumidor de invalidação de cache
- [ ] Retry com backoff exponencial + Dead Letter Queue
- [ ] Cache distribuído em Redis substituindo os caches de módulo (D4)

### Fase 4 — Graph-as-a-Service `feat/graph-service`

- [ ] Modelar o relatório como grafo LangGraph: `buscar_dados → compactar → gerar_markdown → renderizar_pdf` (D8)
- [ ] Retry de token limit como **aresta condicional**, substituindo o `for` com `continue`
- [ ] Checkpointing por `thread_id` (depende de **AD-4**) — execução retomável
- [ ] Streaming de progresso (SSE ou WebSocket) para o cliente
- [ ] Expor o grafo atrás de endpoint HTTP (depende de **AD-3**)
- [ ] Disparo do grafo por evento `RelatorioSolicitado`, emissão de `RelatorioPronto`
- [ ] Resolver o PDF de referência ausente (D9): versionar o arquivo ou remover a dependência
- [ ] Persistir relatórios gerados (storage) em vez de devolver bytes efêmeros

### Fase 5 — Frontend `feat/frontend` *(depende de AD-1)*

- [ ] Scaffold do projeto e cliente HTTP com refresh de token
- [ ] Telas: login, cadastro, dashboard gestora, dashboard investidor, explorar blocos, detalhes de bloco, ingestão, relatórios
- [ ] Consumo do streaming de progresso do relatório
- [ ] Preservar a identidade visual atual (logos em `assets/`)

### Fase 6 — Operação `chore/observability`, `chore/deploy`

- [ ] Logging estruturado (JSON) com correlation ID atravessando os eventos
- [ ] Health checks: `/health` e `/ready`
- [ ] Métricas (Prometheus) e tracing distribuído (OpenTelemetry)
- [ ] Deploy (Cloud Run / Railway / Fly.io) e gestão de secrets
- [ ] Runbook de rollback

---

## 5. Mapa de branches

Base sempre `main`. Uma branch por frente, PR pequeno, merge com squash.

| Branch | Fase | Escopo | Depende de |
|---|---|---|---|
| `chore/test-harness` | 0 | pytest, fixtures, testes de caracterização | — |
| `chore/docker-ci` | 0 | Dockerfile, compose, GitHub Actions | — |
| `docs/align-claude-md` | 0 | corrigir divergências do CLAUDE.md | — |
| `refactor/domain-extraction` | 1 | services/ sem Reflex, repositórios, Pydantic | `chore/test-harness` |
| `feat/fastapi-skeleton` | 2 | app, routers, settings, lifespan | `refactor/domain-extraction` |
| `feat/auth-jwt` | 2 | JWT, guards por perfil | `feat/fastapi-skeleton` |
| `feat/event-bus` | 3 | broker, contratos de evento, publisher | AD-2 |
| `feat/outbox-pattern` | 3 | tabela outbox, relay, transação | `feat/event-bus` |
| `feat/consumers` | 3 | consumidor BQ idempotente, DLQ | `feat/outbox-pattern` |
| `feat/redis-cache` | 3 | cache distribuído | `feat/fastapi-skeleton` |
| `feat/graph-service` | 4 | LangGraph, checkpointing, streaming | AD-3, AD-4 |
| `feat/frontend` | 5 | UI desacoplada | AD-1, `feat/auth-jwt` |
| `chore/observability` | 6 | logs, métricas, tracing | — |
| `chore/deploy` | 6 | deploy e secrets | `chore/docker-ci` |

**Convenção de commit:** `<tipo>: <descrição no imperativo>` — `feat`, `fix`, `refactor`, `chore`, `docs`, `style`, `test`.

---

## 6. Ordem sugerida de execução

```
Fase 0 ──────────────────────────► rede de segurança antes de qualquer refactor
   │
   ▼
Fase 1 ──────────────────────────► domínio limpo, sem Reflex
   │
   ▼
Fase 2 ──────────────────────────► API funcional com auth de verdade
   │
   ├──► Fase 3 (event-driven) ──┐
   │                             ├──► Fase 5 (frontend)
   └──► Fase 4 (graph service) ─┘
                                        │
                                        ▼
                                     Fase 6 (operação)
```

Fases 3 e 4 podem correr em paralelo depois que a Fase 2 estabilizar — dependem da API, não uma da outra.
