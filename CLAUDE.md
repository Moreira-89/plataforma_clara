# CLAUDE.md — plataforma_clara

## Visão Geral

A Plataforma Clara reduz a assimetria de informação entre gestoras e investidores em FIDCs (Fundos de Investimento em Direitos Creditórios). Gestoras enviam aportes via CSV; investidores acessam dashboard com score de risco, visualização de Blocos de Liquidez e relatórios em PDF gerados por IA. Projeto acadêmico (FIAP).

**Monorepo em reconstrução.** O projeto nasceu como monolito Reflex; o Reflex e o Postgres foram removidos, e a aplicação está sendo remontada como backend FastAPI + frontend Vite, sobre GCP.

## Comandos

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Python 3.12
pip install -r requirements.txt
cp .env.example .env          # preencher antes de subir
uvicorn main:app --reload     # http://localhost:8000/docs

pytest                        # suíte
pytest -m "not integracao"    # o que a CI roda
ruff check ..                 # lint (config no pyproject.toml da raiz)

# Frontend
cd frontend
npm install
npm run dev                   # http://localhost:5173

# Tudo junto: backend (8000), frontend (5173), RedisInsight (8001), docs (8080)
docker compose up --build
docker compose up docs      # só a documentação
```

Use Python 3.12. O `requirements.txt` fixa `pandas~=2.3.3`, que não tem wheel para 3.14 — a instalação falha ao compilar dependências transitivas.

A suíte é de **caracterização**: documenta o comportamento atual (incluindo bugs conhecidos, marcados nas docstrings), não o desejado. Um teste que quebra numa refatoração é uma pergunta ("essa mudança foi intencional?"), não necessariamente um erro.

Os testes não tocam em BigQuery, Groq nem Firebase — as dependências externas são substituídas por fakes em `backend/tests/conftest.py`.

## Arquitetura

Dois serviços independentes no mesmo repositório, cada um com o seu `Dockerfile`, para virarem dois serviços separados no Railway. O frontend fala com o backend por HTTP, usando a URL pública do serviço. Em desenvolvimento, o proxy do Vite atende `/api` — não há CORS configurado ainda.

```
┌──────────────┐        HTTP        ┌──────────────┐
│  frontend/   │ ─────────────────▶ │  backend/    │
│  Vite+nginx  │                    │  FastAPI     │
└──────────────┘                    └──────┬───────┘
                                           │
        ┌──────────────┬─────────────┬─────┴────────┐
        ▼              ▼             ▼              ▼
   Firebase Auth   Firestore     BigQuery        Redis
   (identidade)   (operacional)  (analítico)     (cache)
                                      │
                                      ▼
                                 ChatGroq → relatório PDF
```

Dentro do backend a direção das dependências é regra dura:

```
api/ ──▶ agents/ · ingestion/ · storage/ ──▶ domain/
(entrega)      (orquestração/IO)          (regras puras)
```

- **`domain/`** — regras de negócio puras. **Não pode importar `fastapi`, nem `agents/`, `api/`, `ingestion/` ou `storage/`.** É o que atravessa qualquer troca de stack intacto.
- **`api/`** — endpoints, schemas de entrada/saída e dependências do FastAPI. Só orquestra.
- **`agents/`** — tudo de IA: prompt, chamada ao LLM, montagem do relatório.
- **`ingestion/`** — entrada de dados: validação do CSV e preparo dos registros.
- **`storage/`** — clientes de persistência e credenciais (BigQuery hoje; Firestore e Redis a entrar).
- **`config/`** — `settings.py` é o **único** lugar que lê variável de ambiente.
- **`jobs/`** — tarefas de fundo e agendadas.

## Stack

| Camada | Tecnologia |
|---|---|
| Hospedagem | Railway (dois serviços: backend e frontend) |
| API | FastAPI + uvicorn |
| Frontend | Vite, servido por nginx |
| Autenticação | Firebase Auth *(a implementar)* |
| Dados operacionais | Firestore *(a implementar)* |
| Dados analíticos | Google BigQuery (dataset em `BIGQUERY_DATASET`) |
| Cache | Redis *(a implementar)* |
| LLM | ChatGroq via Langchain |
| PDF | `markdown-pdf` |
| Dados | pandas |
| ML | Nenhum modelo no repositório — `score_risco_interno` chega pronto no CSV |

## Estrutura de Diretórios

```
backend/
  main.py                  # cria o app e monta o lifespan. Só montagem.
  Dockerfile
  pytest.ini
  requirements.txt
  .env.example
  app/
    agents/                #   IA: relatorio.py e os assets do PDF
    api/lifespan.py        #   ciclo de vida da aplicação
    api/schemas/           #   contratos Pydantic de entrada e saída
    config/                #   settings.py (env) e logging.py
    domain/                #   risco, metricas, formatacao, identidade, erros
    ingestion/             #   csv_processor.py e aportes.py
    jobs/                  #   tarefas de fundo (vazio)
    storage/               #   bigquery.py (Firestore e Redis a entrar)
  tests/
frontend/
  Dockerfile               # build Node → nginx
  vite.config.js           # proxy /api para o backend em desenvolvimento
  src/                     # css, js, img
  .env.example
docs/                      # documentação MkDocs
mkdocs.yml
docker-compose.yml         # backend + frontend + redis-stack + docs
pyproject.toml             # config do ruff, repositório inteiro
pyrightconfig.json         # extraPaths para o editor resolver `from app...`
.vscode/settings.json      # interpretador e pytest
```

## Pontos de Atenção

Instruções do dono do projeto. Valem sobre qualquer padrão default.

- **Comentário no código é curto** — no máximo uma linha, dizendo o que aquele trecho faz. Explicação longa (o porquê de uma decisão, histórico, armadilha conhecida) vai para markdown em `docs/`. Não encher arquivo de comentário.
- **Mudanças grandes estão autorizadas.** O projeto é acadêmico, ainda sem usuários. Apagar pasta, remover biblioteca, refazer camada inteira: pode. Não travar pedindo confirmação a cada passo, não repetir aviso de risco já respondido, e não tratar como perda o trabalho que vai ser refeito.
- **Conferir o disco, não só o Git.** `git ls-files` não mostra diretório vazio, porque o Git não versiona diretório. Depois de remover coisa, verificar com `find`/`ls` — é o que o editor mostra.
- **O `.env` fica em `backend/`**, não na raiz. Junto com o `.env.example` de cada serviço.
- **`docs/` é MkDocs**, servido em <http://localhost:8080>. A organização atual é provisória e vai mudar.

## Convenções de Código

- **Docstrings obrigatórias** em todo módulo: resumo, seção "COMO FUNCIONA" com passos numerados, `Args`, `Returns`, `Raises`. A restrição de tamanho acima vale para comentários, não para docstrings.
- **Logs**: sempre `logging.getLogger(__name__)`. Nunca `print()`.
- **I/O bloqueante** (BigQuery, Groq, Firestore): sempre dentro de `asyncio.to_thread` quando chamado de código assíncrono.
- **Regra de negócio**: mora em `domain/`. Endpoint só orquestra — se um cálculo aparece dentro de um handler, está no lugar errado.
- **Configuração**: só `config/settings.py` lê o ambiente. Nenhum `os.getenv` espalhado.

## Restrições Rígidas

- Nunca commitar `.env` ou credenciais de service account. Não manter arquivo de credencial na raiz do repositório — o `COPY . .` do Docker o levaria para dentro da imagem.
- Nunca alterar o schema dos aportes só de um lado — o schema do job (`ingestion/aportes.py::_SCHEMA_BIGQUERY`) e o contrato do CSV (`ingestion/csv_processor.py::COLUNAS_OBRIGATORIAS`) precisam ficar sincronizados na mão.
- Nunca reintroduzir número inventado como se fosse dado. A evolução do AUM, o rendimento projetado e a rentabilidade por bloco eram fatores fixos e um hash do nome do bloco, exibidos ao lado de números reais sem rótulo. Foram removidos. Se a tela nova precisar desses campos, ou vêm de dado real, ou vão rotulados como estimativa.
- Nunca implementar autenticação própria: quem cuida de identidade e senha é o Firebase. O backend verifica o token e lê as claims.
- Nunca chamar a API do Groq fora de `agents/relatorio.py` — é o único lugar com o retry progressivo (5 tentativas com cortes crescentes na amostra de aportes, nos grupos de empresa e no texto de referência) tratado para `APIStatusError` 413.
- Nunca importar camada de entrega dentro de `domain/`. É essa regra que faz trocar de stack ser uma troca, e não uma reescrita.
- Nunca assumir que existe modelo de ML no projeto: o score de risco é um dado de entrada, não um cálculo da plataforma.

## Variáveis de Ambiente

Cada serviço tem o seu modelo: `backend/.env.example` e `frontend/.env.example`. O `.env` real nunca entra no repositório.

```
GOOGLE_APPLICATION_CREDENTIALS={"type": "service_account", ...}  # ou caminho de arquivo
PROJECT_ID=plataforma-clara
BIGQUERY_DATASET=dados_cvm
REDIS_URL=redis://localhost:6379/0
GROQ_API_KEY=gsk_...
LLM_MODEL_NAME="groq:openai/gpt-oss-120b"
LLM_TEMPERATURE=0.1
```

Não criar variável de ambiente nova sem que algo a consuma.

## O Que Ainda Não Existe

Não invente que existe. Nesta ordem:

1. **Firestore** — a persistência operacional. `ingestion/aportes.py` processa o CSV e carrega no BigQuery, mas **não grava em lugar nenhum de leitura rápida**.
2. **Firebase Auth** — não há verificação de token nem rota protegida.
3. **Endpoints** — só existe `/health`. Nenhuma rota de aporte, dashboard, bloco ou relatório.
4. **Redis** — declarado no compose, sem cliente na aplicação.
5. **CORS** — sem middleware. Precisa entrar quando o frontend chamar a API de outro domínio.
6. **Agregações do dashboard** — as consultas eram SQL e saíram com o Postgres. `domain/metricas.py` tem as regras de consolidação, mas nada as alimenta.
