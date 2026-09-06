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
# SEM ENTRY POINT NO MOMENTO: o app Reflex foi removido e o da API ainda não existe.

# Banco de dados (Alembic direto)
alembic revision --autogenerate -m "descricao"
alembic upgrade head

# Testes (pytest e ruff vêm no requirements.txt — não há arquivo de dev separado)
pytest                      # suíte completa
pytest -m "not integracao"  # o que a CI roda
ruff check .                # lint

# Docker (app + postgres + redis)
docker compose up --build
```

Use Python 3.12. O `requirements.txt` fixa `pandas~=2.3.3`, que não tem wheel para 3.14 — a instalação falha ao compilar dependências transitivas.

A suíte é de **caracterização**: documenta o comportamento atual (incluindo bugs conhecidos, marcados como tal nas docstrings), não o comportamento desejado. Um teste que quebra numa refatoração é uma pergunta ("essa mudança foi intencional?"), não necessariamente um erro. Não "consertar" um teste marcado como CARACTERIZAÇÃO DE BUG sem corrigir o código junto.

Os testes não tocam em Postgres, BigQuery nem Groq — as dependências externas são substituídas por fakes em `tests/conftest.py`. Os serviços recebem a sessão de banco por injeção (`sessao_factory=`), então testar não exige monkeypatch.

O histórico do Alembic foi regerado do zero na saída do Supabase: há uma única migração inicial, gerada a partir de `domain/models.py`, e `alembic upgrade head` num banco vazio produz o schema que o código espera. A URL vem da `DATABASE_URL` (lida em `alembic/env.py`), nunca do `alembic.ini`.

## Arquitetura

**O Reflex foi removido do repositório.** Saíram as camadas de UI (`pages/`, `states/`, `components/`), o entry point e o `rxconfig.py`. O que restou é backend puro, sem framework de entrega: nenhum módulo do projeto importa `reflex`, e a suíte roda com ele desinstalado. A estrutura de pastas definitiva do monorepo (backend + frontend) ainda vai ser definida — **enquanto isso, não invente diretório novo**.

Não há entry point. Nada sobe. A camada de entrega é a próxima coisa a ser escrita.

O código restante está em camadas, e a direção das dependências é regra dura:

```
(entrega, a definir) ──▶ services/ ──▶ infra/ ──▶ domain/
                       (orquestração)  (banco)   (regras puras)
```

- **`domain/`** — regras de negócio, modelos de tabela e contratos Pydantic. **Não pode importar `fastapi` nem `services/`.** É o que atravessa a migração intacto.
- **`infra/`** — engine, sessão e repositórios. Todo o SQL vive aqui.
- **`services/`** — orquestra domínio + infra, decide escopo de transação, cache e tratamento de falha. Recebe a sessão por injeção (`sessao_factory=`).

Toda operação de I/O (Postgres, BigQuery, Groq) é bloqueante e deve rodar em `asyncio.to_thread` quando chamada de código assíncrono.

```
                              (camada de entrega a definir)
                                            │
                    ┌───────────────────────┼────────────────────────┐
                    ▼                                                 ▼
         PostgreSQL (Railway)                               Google BigQuery
         tb_usuario, tb_aporte                              dados_fidc.tb_aporte
         (OLTP, autenticação)                                (OLAP, analytics)
                                                                       │
                                                                       ▼
                                                              ChatGroq (LLaMA 3 70B)
                                                              → geração de relatório PDF
```

Dupla persistência: cada aporte é gravado no PostgreSQL **e** no BigQuery em `WRITE_APPEND`. Qualquer mudança de schema em `tb_aporte` precisa ser replicada nos dois lados — no modelo (`domain/models.py`), no schema do job (`services/ingestao_service.py::_SCHEMA_BIGQUERY`) e no contrato do CSV (`services/csv_processor.py::COLUNAS_OBRIGATORIAS`). O `tests/test_domain_models.py` trava a correspondência.

## Stack

| Camada | Tecnologia |
|---|---|
| Entrega | **a definir** — o Reflex saiu, a API ainda não existe |
| Hospedagem | Railway (app, PostgreSQL e Redis) + Google Cloud (BigQuery) |
| DB operacional | PostgreSQL, SQLModel sobre SQLAlchemy |
| Cache e fila | Redis |
| DB analítico | Google BigQuery (`dados_fidc.tb_aporte`) |
| LLM | ChatGroq — `llama-3.3-70b-versatile`, temperatura 0.1, `max_tokens=900` |
| PDF | `markdown-pdf` (Markdown → PDF) |
| Dados | Pandas |
| Auth | bcrypt (12 rounds) |
| ML | Nenhum modelo treinado no repositório — o `score_risco_interno` chega pronto como coluna do CSV de ingestão |
| Orquestração de IA | Langchain (prompt + invocação do Groq) |

## Estrutura de Diretórios

Estrutura ATUAL, herdada da fase anterior. Vai mudar quando o monorepo for reorganizado.

```
domain/                    # camada pura — proibido importar framework de entrega
  models.py                #   tabelas SQLModel: tb_usuario, tb_aporte
  schemas.py               #   contratos Pydantic v2 (entrada/saída)
  metricas.py              #   KPIs, filtros e montagem das visões
  risco.py                 #   escada de classificação de risco (fonte única)
  formatacao.py            #   moeda, CNPJ e percentual no padrão BR
  identidade.py            #   normalização/validação de CPF, CNPJ e e-mail
  seguranca.py             #   hash bcrypt — único lugar que lida com senha
  erros.py                 #   exceções de negócio
infra/
  db.py                    #   engine, sessão e dependência de sessão
  repositorios/            #   todo o SQL (aporte.py, usuario.py)
services/                  # orquestração: dashboard, bloco, ingestão, auth, IA, BigQuery
alembic/                   # migrações (ver aviso acima sobre o histórico)
assets/                    # a logo lida pelo gerador de PDF do relatório
```

## Convenções de Código

- **Docstrings obrigatórias** em todo módulo, padrão `@user_global`: resumo, seção "COMO FUNCIONA" com passos numerados, `Args`, `Returns`, `Raises`. Comentários inline explicam o *porquê*, não o *o quê*.
- **Logs**: sempre `logging.getLogger(__name__)`. Nunca `print()`.
- **I/O bloqueante** (queries, BigQuery, chamadas Groq): sempre dentro de `asyncio.to_thread` quando chamado de código assíncrono.
- **Sessão de banco**: serviços recebem `sessao_factory=` (padrão `infra.db.sessao`); repositórios recebem a `Session` pronta e não a fecham.
- **Regra de negócio**: mora em `domain/`. A camada de entrega só orquestra — se um cálculo aparece dentro de um handler ou de um endpoint, ele está no lugar errado.

## Restrições Rígidas

- Nunca commitar `.env` ou credenciais de service account — ambos já cobertos por `.gitignore`, não recriar arquivos de credencial na raiz do projeto.
- Nunca alterar o schema de `tb_aporte` só no PostgreSQL ou só no BigQuery — as duas tabelas precisam ficar sincronizadas manualmente (não há migração automática entre elas).
- Nunca reintroduzir número inventado como se fosse dado. A evolução do AUM, o rendimento projetado e a rentabilidade dos blocos eram fatores fixos e um hash do nome do bloco, exibidos ao lado de números reais sem rótulo. Foram removidos. Se a tela nova precisar desses campos, ou vêm de dado real, ou vão rotulados como estimativa.
- Nunca usar hash de senha fora do padrão bcrypt de `domain/seguranca.py` — é o único módulo autorizado a gerar ou conferir hash, e o cost factor 12 não pode ser reduzido (hashes antigos seguiriam válidos, e só as senhas novas ficariam fracas).
- Nunca escrever SQL fora de `infra/repositorios/`, e nunca concatenar valor de usuário na query — documento sempre como bind parameter.
- Nunca reintroduzir `reflex` no projeto, e nunca importar o framework de entrega (hoje nenhum, amanhã `fastapi`) dentro de `domain/` ou `infra/`. É essa regra que faz trocar de camada de entrega ser uma troca, e não uma reescrita.
- Nunca chamar a API do Groq fora de `services/relatorio_ia_service.py` — é o único lugar com o retry progressivo (5 tentativas com cortes crescentes na amostra de aportes, nos grupos de empresa e no texto de referência) tratado para `APIStatusError` 413.
- Nunca assumir que existe modelo de ML no projeto: o score de risco é um dado de entrada, não um cálculo da plataforma.

## Variáveis de Ambiente

O `.env.example` é o modelo versionado; o `.env` real nunca entra no repositório.

```
DATABASE_URL=postgresql://...                    # Postgres do Railway
REDIS_URL=redis://...                            # Redis do Railway
GOOGLE_APPLICATION_CREDENTIALS={"type": "service_account", ...}  # ou caminho de arquivo local
GROQ_API_KEY=gsk_...
```