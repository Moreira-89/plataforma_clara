# CLAUDE.md — plataforma_clara

## Visão Geral

A Plataforma Clara reduz a assimetria de informação entre gestoras e investidores em FIDCs (Fundos de Investimento em Direitos Creditórios). Gestoras fazem upload de aportes via CSV; investidores acessam dashboard com score de risco preditivo (Score Nuclea), visualização de Blocos de Liquidez e relatórios em PDF gerados por IA. Projeto acadêmico (FIAP), com foco em robustez e baixo custo para MVP.

## Comandos

```bash
# Setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # preencher DATABASE_URL, GOOGLE_APPLICATION_CREDENTIALS, GROQ_API_KEY

# Dev
reflex run              # http://localhost:3000

# Banco de dados (Alembic direto — os modelos não usam mais rx.Model)
alembic revision --autogenerate -m "descricao"
alembic upgrade head

# Testes
pip install -r requirements-dev.txt
pytest                      # suíte completa
pytest -m "not integracao"  # o que a CI roda
ruff check .                # lint

# Docker (app + postgres + redis)
docker compose up --build
```

Use Python 3.12. O `requirements.txt` fixa `pandas~=2.3.3`, que não tem wheel para 3.14 — a instalação falha ao compilar dependências transitivas.

A suíte é de **caracterização**: documenta o comportamento atual (incluindo bugs conhecidos, marcados como tal nas docstrings), não o comportamento desejado. Um teste que quebra numa refatoração é uma pergunta ("essa mudança foi intencional?"), não necessariamente um erro. Não "consertar" um teste marcado como CARACTERIZAÇÃO DE BUG sem corrigir o código junto.

Os testes não tocam em Postgres, BigQuery nem Groq — as dependências externas são substituídas por fakes em `tests/conftest.py`. Os serviços recebem a sessão de banco por injeção (`sessao_factory=`), então testar não exige monkeypatch.

**O histórico do Alembic não reproduz o schema atual**: a migração que cria `tb_usuario` declara as colunas `nome`, `email` e `senha_hash`, e nenhuma migração posterior as renomeia para os nomes que o código usa (`nome_usuario`, `email_usuario`, `senha_hash_usuario`). O banco em uso foi ajustado por fora do histórico. Confira o diff de qualquer `--autogenerate` antes de aplicar.

## Arquitetura

Full-stack Python único: Reflex compila o frontend em React + WebSocket e expõe o backend via FastAPI. Estado reativo (`rx.State`) sincroniza servidor e browser automaticamente. Toda operação de I/O (Postgres, BigQuery, Groq) roda em `asyncio.to_thread` para não bloquear o event loop.

O código está organizado em camadas, e a direção das dependências é regra dura:

```
pages/ ──▶ states/ ──▶ services/ ──▶ infra/ ──▶ domain/
 (UI)     (Reflex)    (orquestração)  (banco)   (regras puras)
```

- **`domain/`** — regras de negócio, modelos de tabela e contratos Pydantic. **Não pode importar `reflex`, `fastapi` nem `services/`.** É o que atravessa a migração intacto.
- **`infra/`** — engine, sessão e repositórios. Todo o SQL vive aqui.
- **`services/`** — orquestra domínio + infra, decide escopo de transação, cache e tratamento de falha. Recebe a sessão por injeção (`sessao_factory=`).
- **`states/`** — só o que é de tela: ler campo, exibir mensagem, redirecionar. Nenhum cálculo novo.

```
Frontend (Reflex/React) ⇄ WebSocket ⇄ Backend (Reflex Server/FastAPI)
                                            │
                    ┌───────────────────────┼────────────────────────┐
                    ▼                                                 ▼
         PostgreSQL (Supabase)                              Google BigQuery
         tb_usuario, tb_aporte                              dados_fidc.tb_aporte
         (OLTP, autenticação)                                (OLAP, analytics)
                                                                       │
                                                                       ▼
                                                              ChatGroq (LLaMA 3 70B)
                                                              → geração de relatório PDF
```

Dupla persistência: cada aporte é gravado no PostgreSQL **e** no BigQuery em `WRITE_APPEND`. Qualquer mudança de schema em `tb_aporte` precisa ser replicada nos dois lados — no modelo (`domain/models.py`), no schema do job (`states/ingestao_dados_state.py::_SCHEMA_BIGQUERY`) e no contrato do CSV (`services/csv_processor.py::COLUNAS_OBRIGATORIAS`). O `tests/test_domain_models.py` trava a correspondência.

## Stack

| Camada | Tecnologia |
|---|---|
| Framework | Reflex (Python → React + FastAPI) |
| DB operacional | PostgreSQL via Supabase, ORM SQLAlchemy |
| DB analítico | Google BigQuery (`dados_fidc.tb_aporte`) |
| LLM | ChatGroq — `llama-3.3-70b-versatile`, temperatura 0.1, `max_tokens=900` |
| PDF | `markdown-pdf` (Markdown → PDF) |
| Dados | Pandas |
| Auth | bcrypt (12 rounds) |
| UI | Radix UI / `rx.color()`, ícones Lucide |
| ML | Nenhum modelo treinado no repositório — o `score_risco_interno` chega pronto como coluna do CSV de ingestão |
| Orquestração de IA | Langchain (prompt + invocação do Groq). `langgraph` está no `requirements.txt` mas ainda não é usado |

## Estrutura de Diretórios

```
plataforma_clara.py       # entry point: rotas e instanciação do app
rxconfig.py                # config Reflex (db_url, app_name)
domain/                    # camada pura — proibido importar reflex/fastapi
  models.py                #   tabelas SQLModel: tb_usuario, tb_aporte
  schemas.py               #   contratos Pydantic v2 (entrada/saída)
  metricas.py              #   KPIs, filtros e montagem das visões
  risco.py                 #   escada de classificação de risco (fonte única)
  formatacao.py            #   moeda, CNPJ e percentual no padrão BR
  identidade.py            #   normalização/validação de CPF, CNPJ e e-mail
  seguranca.py             #   hash bcrypt — único lugar que lida com senha
  projecoes.py             #   séries SIMULADAS dos gráficos (dado inventado)
  erros.py                 #   exceções de negócio
infra/
  db.py                    #   engine, sessão e dependência de sessão
  repositorios/            #   todo o SQL (aporte.py, usuario.py)
services/                  # orquestração: dashboard, bloco, ingestão, auth, IA, BigQuery
states/                    # um State por página/fluxo (herda rx.State)
components/sidebar.py      # sidebars reutilizáveis (gestora/investidor)
pages/                     # uma página por rota
```

## Convenções de Código

- **Docstrings obrigatórias** em todo módulo, padrão `@user_global`: resumo, seção "COMO FUNCIONA" com passos numerados, `Args`, `Returns`, `Raises`. Comentários inline explicam o *porquê*, não o *o quê*.
- **Logs**: sempre `logging.getLogger(__name__)`. Nunca `print()`.
- **Cores de UI**: sempre `rx.color("gray", 12)` ou tokens equivalentes. Nunca hex hardcoded.
- **Sidebars**: importar de `components/sidebar.py`. Nunca duplicar a implementação em uma página.
- **Badges reativos**: usar `rx.cond` para `color_scheme` dinâmico, não lógica condicional fora do fluxo reativo do Reflex.
- **I/O bloqueante** (queries, BigQuery, chamadas Groq): sempre dentro de `asyncio.to_thread`, nunca direto num handler `@rx.event` síncrono.
- **Sessão de banco**: nunca `rx.session()`. Serviços recebem `sessao_factory=` (padrão `infra.db.sessao`); repositórios recebem a `Session` pronta e não a fecham.
- **Regra de negócio**: mora em `domain/`. Um `rx.State` ou um endpoint só orquestra — se um cálculo aparece dentro de um `@rx.var`, ele está no lugar errado.

## Restrições Rígidas

- Nunca commitar `.env` ou credenciais de service account — ambos já cobertos por `.gitignore`, não recriar arquivos de credencial na raiz do projeto.
- Nunca alterar o schema de `tb_aporte` só no PostgreSQL ou só no BigQuery — as duas tabelas precisam ficar sincronizadas manualmente (não há migração automática entre elas).
- Nunca apresentar como real o que vem de `domain/projecoes.py` ou de `metricas.rentabilidade_estavel`: são números simulados, exibidos hoje ao lado de dados verdadeiros e sem rótulo que os distinga.
- Nunca usar hash de senha fora do padrão bcrypt de `domain/seguranca.py` — é o único módulo autorizado a gerar ou conferir hash, e o cost factor 12 não pode ser reduzido (hashes antigos seguiriam válidos, e só as senhas novas ficariam fracas).
- Nunca escrever SQL fora de `infra/repositorios/`, e nunca concatenar valor de usuário na query — documento sempre como bind parameter.
- Nunca importar `reflex` dentro de `domain/` ou `infra/`. É essa regra que faz a migração para FastAPI ser uma troca de camada de entrega, e não uma reescrita.
- Nunca chamar a API do Groq fora de `services/relatorio_ia_service.py` — é o único lugar com o retry progressivo (5 tentativas com cortes crescentes na amostra de aportes, nos grupos de empresa e no texto de referência) tratado para `APIStatusError` 413.
- Nunca assumir que existe modelo de ML no projeto: o score de risco é um dado de entrada, não um cálculo da plataforma.

## Variáveis de Ambiente

```
DATABASE_URL=postgresql://...                    # Supabase
GOOGLE_APPLICATION_CREDENTIALS={"type": "service_account", ...}  # ou caminho de arquivo local
GROQ_API_KEY=gsk_...
```