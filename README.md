# Plataforma Clara

> Plataforma de transparência e análise de risco para FIDCs (Fundos de Investimento em Direitos Creditórios), conectando gestoras e investidores com score de risco, visualização de Blocos de Liquidez e relatórios gerados por IA.

Projeto acadêmico (FIAP).

---

## Estado atual

**Monorepo em reconstrução.** O projeto nasceu como monolito Reflex sobre PostgreSQL. O Reflex e o Postgres saíram; o que está de pé é o esqueleto de dois serviços independentes — `backend/` (FastAPI) e `frontend/` (Vite) — sobre o ecossistema Google Cloud.

Já existe: o processamento e a validação do CSV de aportes, a carga no BigQuery, o gerador de relatório por IA e as regras de negócio (classificação de risco, KPIs, formatação, validação de CPF/CNPJ).

Ainda não existe: Firestore, Firebase Auth, Redis e os endpoints. A API sobe e responde `/health`, nada além disso.

---

## O que a plataforma faz

**Gestora** envia um CSV de aportes. Cada linha é validada, normalizada e gravada em dois lugares: PostgreSQL (operacional) e BigQuery (analítico).

**Investidor** enxerga a carteira agregada por Bloco de Liquidez — volume alocado, score médio de risco, empresas sacadas por trás de cada bloco — e pode gerar um relatório consolidado em PDF, escrito por um LLM a partir dos dados reais da própria carteira.

O `score_risco_interno` **chega pronto como coluna do CSV**. Não há modelo de ML no repositório; a plataforma classifica e apresenta o score, não o calcula.

---

## Como rodar

Requer **Python 3.12** (o `pandas~=2.3.3` não tem wheel para 3.14) e **Node 22**.

```bash
# Backend
cd backend
cp .env.example .env          # preencher antes de subir
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload     # http://localhost:8000/docs
pytest                        # suíte
ruff check ..                 # lint

# Frontend
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

Ou tudo junto — backend, frontend, Redis e a documentação:

```bash
docker compose up --build
```

| Serviço | Endereço |
| --- | --- |
| Backend | <http://localhost:8000> (docs da API em `/docs`) |
| Frontend | <http://localhost:5173> |
| RedisInsight | <http://localhost:8001> |
| Documentação | <http://localhost:8080> |

A suíte não toca em BigQuery, Groq nem Firebase: as dependências externas são substituídas por fakes em `backend/tests/conftest.py`.

---

## Organização do código

Dois serviços, cada um com o seu `Dockerfile`, para virarem dois serviços separados no Railway.

```
backend/
  main.py              # cria o app, lifespan e CORS
  app/
    agents/            # IA: prompt, LLM, montagem do relatório
    api/schemas/       # contratos Pydantic de entrada e saída
    config/            # settings (env) e logging
    domain/            # regras puras: risco, métricas, formatação, identidade
    ingestion/         # validação do CSV e preparo dos registros
    jobs/              # tarefas de fundo
    storage/           # clientes de persistência e credenciais
  tests/
frontend/
  src/                 # css, js, img
  vite.config.js       # proxy /api para o backend em desenvolvimento
```

Dentro do backend a direção das dependências é regra dura: **`api/` → `agents/`, `ingestion/`, `storage/` → `domain/`**, nunca ao contrário. `domain/` não importa framework nenhum.

---

## Stack

| Camada | Tecnologia |
| --- | --- |
| Hospedagem | Railway — um serviço para o backend, outro para o frontend |
| API | FastAPI + uvicorn |
| Frontend | Vite, servido por nginx |
| Autenticação | Firebase Auth *(a implementar)* |
| Dados operacionais | Firestore *(a implementar)* |
| Dados analíticos | Google BigQuery — dataset em `BIGQUERY_DATASET` |
| Cache | Redis *(a implementar)* |
| LLM | ChatGroq via Langchain |
| PDF | `markdown-pdf` |
| Dados | pandas |

---

## Variáveis de ambiente

Copie o `.env.example` de cada serviço (`backend/` e `frontend/`). O `.env` real nunca é versionado — e o arquivo de credencial da service account deve ficar **fora** do repositório, senão o `COPY . .` do Docker o leva para dentro da imagem.

```
GOOGLE_APPLICATION_CREDENTIALS={"type": "service_account", ...}   # ou caminho de um arquivo
PROJECT_ID=plataforma-clara
BIGQUERY_DATASET=dados_cvm
REDIS_URL=redis://localhost:6379/0
GROQ_API_KEY=gsk_...
LLM_MODEL_NAME="groq:openai/gpt-oss-120b"
LLM_TEMPERATURE=0.1
```

---

## Pontos de atenção

- **Falta a persistência operacional.** A ingestão processa o CSV e carrega no BigQuery, mas não grava em nenhum banco de leitura rápida. O Firestore ainda não foi implementado.
- **Schema em dois lugares.** Mudar as colunas do aporte exige alterar o schema do job (`backend/app/ingestion/aportes.py`) e o contrato do CSV (`backend/app/ingestion/csv_processor.py`) juntos.
- **Números simulados, removidos.** A evolução do AUM, o rendimento projetado e a rentabilidade por bloco eram inventados (fatores fixos e um hash do nome do bloco) e apareciam ao lado de dados reais sem rótulo. Saíram junto com a UI. Se voltarem, que venham de dado real ou rotulados como estimativa.
