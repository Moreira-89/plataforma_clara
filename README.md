# Plataforma Clara

> Plataforma de transparência e análise de risco para FIDCs (Fundos de Investimento em Direitos Creditórios), conectando gestoras e investidores com score de risco, visualização de Blocos de Liquidez e relatórios gerados por IA.

Projeto acadêmico (FIAP).

---

## Estado atual

O projeto está **em migração**: nasceu como um monolito Reflex (full-stack Python) e está sendo reescrito como monorepo com backend FastAPI e frontend separado.

O Reflex foi removido. Restou o núcleo do backend, que não depende de framework de entrega nenhum:

- as regras de negócio e os modelos de dados,
- o acesso ao PostgreSQL e ao BigQuery,
- o processamento do CSV de ingestão,
- o serviço que gera o relatório em PDF via IA.

**Não há entry point.** Nada sobe ainda — a camada de entrega é a próxima coisa a ser escrita, e a estrutura de pastas do monorepo está sendo definida. O roadmap da migração vive no Notion.

---

## O que a plataforma faz

**Gestora** envia um CSV de aportes. Cada linha é validada, normalizada e gravada em dois lugares: PostgreSQL (operacional) e BigQuery (analítico).

**Investidor** enxerga a carteira agregada por Bloco de Liquidez — volume alocado, score médio de risco, empresas sacadas por trás de cada bloco — e pode gerar um relatório consolidado em PDF, escrito por um LLM a partir dos dados reais da própria carteira.

O `score_risco_interno` **chega pronto como coluna do CSV**. Não há modelo de ML no repositório; a plataforma classifica e apresenta o score, não o calcula.

---

## Como rodar

Requer **Python 3.12** (o `pandas~=2.3.3` não tem wheel para 3.14).

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # preencher as três variáveis abaixo
```

```bash
pytest              # suíte completa
ruff check .        # lint
```

A suíte não toca em Postgres, BigQuery nem Groq: as dependências externas são substituídas por fakes em `tests/conftest.py`.

Migrações:

```bash
alembic revision --autogenerate -m "descricao"
alembic upgrade head
```

A URL vem da `DATABASE_URL`, lida pelo `alembic/env.py` — o `alembic.ini` é versionado e não carrega credencial.

---

## Organização do código

A direção das dependências é regra dura: **`services/` → `infra/` → `domain/`**, nunca ao contrário.

| Pasta | Responsabilidade |
| --- | --- |
| `domain/` | Regras de negócio puras, modelos de tabela e contratos Pydantic. Não importa framework nenhum. |
| `infra/` | Engine, sessão e repositórios. **Todo o SQL vive aqui.** |
| `services/` | Orquestra domínio e infraestrutura: transação, cache, tratamento de falha, chamadas externas. |
| `alembic/` | Migrações do PostgreSQL. |
| `tests/` | Suíte de caracterização — documenta o comportamento atual, inclusive o discutível. |

Esta estrutura é herdada da fase anterior e **vai mudar** na reorganização do monorepo.

---

## Stack

| Camada | Tecnologia |
| --- | --- |
| Entrega | a definir |
| Hospedagem | Railway (aplicação, PostgreSQL e Redis) + Google Cloud (dados analíticos) |
| Banco operacional | PostgreSQL, SQLModel sobre SQLAlchemy |
| Banco analítico | Google BigQuery — `dados_fidc.tb_aporte` |
| Cache e fila | Redis |
| LLM | ChatGroq, `llama-3.3-70b-versatile` |
| PDF | `markdown-pdf` |
| Dados | pandas |
| Autenticação | bcrypt, 12 rounds |

---

## Variáveis de ambiente

Copie o `.env.example` e preencha:

```
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
GOOGLE_APPLICATION_CREDENTIALS={"type": "service_account", ...}   # ou caminho de um arquivo local
GROQ_API_KEY=gsk_...
```

Nunca versionar o `.env` nem o arquivo de credencial da service account.

---

## Pontos de atenção

- **Dupla escrita sem transação.** O aporte é gravado no PostgreSQL e depois no BigQuery, fora de qualquer transação. Uma falha no segundo passo diverge os dados em silêncio.
- **Schema em dois lugares.** Mudar `tb_aporte` exige alterar o modelo (`domain/models.py`), o schema do job (`services/ingestao_service.py`) e o contrato do CSV (`services/csv_processor.py`). Não há migração automática entre Postgres e BigQuery.
- **Números simulados.** `domain/projecoes.py` e `metricas.rentabilidade_estavel` produzem séries inventadas (fatores fixos e um hash do nome do bloco). A tela que os exibia sem rótulo, ao lado de dados reais, foi removida junto com o Reflex — não recriar o problema na próxima.
