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

# Banco de dados
reflex db init
reflex db migrate
reflex db upgrade
```

Não há suite de testes automatizados no repositório (sem pytest). Não assuma cobertura de testes ao propor mudanças — valide manualmente ou pergunte antes de refatorar código sem rede de segurança.

## Arquitetura

Full-stack Python único: Reflex compila o frontend em React + WebSocket e expõe o backend via FastAPI. Estado reativo (`rx.State`) sincroniza servidor e browser automaticamente. Toda operação de I/O (Postgres, BigQuery, Groq) roda em `asyncio.to_thread` para não bloquear o event loop.

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

Dupla persistência: cada aporte é gravado no PostgreSQL **e** no BigQuery em `WRITE_APPEND`. Qualquer mudança de schema em `tb_aporte` precisa ser replicada nos dois lados.

## Stack

| Camada | Tecnologia |
|---|---|
| Framework | Reflex (Python → React + FastAPI) |
| DB operacional | PostgreSQL via Supabase, ORM SQLAlchemy |
| DB analítico | Google BigQuery (`dados_fidc.tb_aporte`) |
| LLM | ChatGroq — `llama3-70b-8192`, temperatura 0 |
| PDF | WeasyPrint (Markdown/HTML → PDF) |
| Dados | Pandas |
| Auth | bcrypt (12 rounds) |
| UI | Radix UI / `rx.color()`, ícones Lucide |
| ML | Scikit-learn (Score Nuclea, modelo `.pkl`) |
| Orquestração de IA | Langchain (Insight Engine) |

## Estrutura de Diretórios

```
plataforma_clara.py     # entry point: rotas e instanciação do app
rxconfig.py              # config Reflex (db_url, app_name)
model/schemas.py         # modelos SQLAlchemy: tb_usuario, tb_aporte
states/                  # um State por página/fluxo (herda rx.State)
services/                # I/O externo: bigquery, dashboard, csv, relatório IA
components/sidebar.py    # sidebars reutilizáveis (gestora/investidor)
pages/                   # uma página por rota
```

## Convenções de Código

- **Docstrings obrigatórias** em todo módulo, padrão `@user_global`: resumo, seção "COMO FUNCIONA" com passos numerados, `Args`, `Returns`, `Raises`. Comentários inline explicam o *porquê*, não o *o quê*.
- **Logs**: sempre `logging.getLogger(__name__)`. Nunca `print()`.
- **Cores de UI**: sempre `rx.color("gray", 12)` ou tokens equivalentes. Nunca hex hardcoded.
- **Sidebars**: importar de `components/sidebar.py`. Nunca duplicar a implementação em uma página.
- **Badges reativos**: usar `rx.cond` para `color_scheme` dinâmico, não lógica condicional fora do fluxo reativo do Reflex.
- **I/O bloqueante** (queries, BigQuery, chamadas Groq): sempre dentro de `asyncio.to_thread`, nunca direto num handler `@rx.event` síncrono.

## Restrições Rígidas

- Nunca commitar `.env` ou credenciais de service account — ambos já cobertos por `.gitignore`, não recriar arquivos de credencial na raiz do projeto.
- Nunca alterar o schema de `tb_aporte` só no PostgreSQL ou só no BigQuery — as duas tabelas precisam ficar sincronizadas manualmente (não há migração automática entre elas).
- Nunca usar hash de senha fora do padrão bcrypt já implementado em `cadastro_usuario_state.py`.
- Nunca chamar a API do Groq fora de `services/relatorio_ia_service.py` — é o único lugar com o retry progressivo (redução de contexto em 20% por tentativa, até 3 tentativas) tratado para `RateLimitError`.

## Variáveis de Ambiente

```
DATABASE_URL=postgresql://...                    # Supabase
GOOGLE_APPLICATION_CREDENTIALS={"type": "service_account", ...}  # ou caminho de arquivo local
GROQ_API_KEY=gsk_...
```