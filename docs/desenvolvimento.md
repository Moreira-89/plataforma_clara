# Desenvolvimento

## Tudo junto, com Docker

O caminho mais curto: sobe backend, frontend, Redis e esta documentação sem
instalar Python, Node ou Redis na máquina.

```bash
cp backend/.env.example backend/.env   # preencher antes
docker compose up --build
```

| Serviço | Endereço |
| --- | --- |
| Backend | <http://localhost:8000> — docs da API em `/docs` |
| Frontend | <http://localhost:5173> |
| RedisInsight | <http://localhost:8001> |
| Esta documentação | <http://localhost:8080> |

O backend sobe com `--reload` e bind mount: alterar um arquivo reinicia o processo
sozinho, sem rebuild.

!!! info "O compose não vai para produção"
    O Railway não lê `docker-compose.yml`. Ele builda o `Dockerfile` de cada
    serviço. Tudo que é só de desenvolvimento — o `--reload`, o bind mount, a
    interface do Redis — mora no compose, e não nos Dockerfiles, porque os
    Dockerfiles são os mesmos dos dois lados.

## Sem Docker

Requer **Python 3.12** e **Node 22**.

!!! warning "3.12, não 3.13+"
    O `requirements.txt` fixa `pandas~=2.3.3`, que não tem wheel para versões mais
    novas. A instalação falha ao compilar dependências transitivas.

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload      # http://localhost:8000/docs

# Frontend
cd frontend
npm install
npm run dev                    # http://localhost:5173
```

Em desenvolvimento o Vite faz proxy de `/api` para `http://localhost:8000`, então
o frontend funciona sem configurar CORS nem `VITE_API_URL`.

## Qualidade

```bash
cd backend
pytest                     # suíte completa
pytest -m "not integracao" # o que a CI roda
ruff check ..              # lint do repositório inteiro
```

A suíte **não toca** em BigQuery, Groq nem Firebase: as dependências externas são
substituídas por fakes em `backend/tests/conftest.py`. Roda em segundos e não
precisa de credencial nenhuma.

!!! note "A suíte é de caracterização"
    Ela documenta o comportamento **atual**, incluindo o discutível — que está
    marcado como tal nas docstrings. Um teste que quebra numa refatoração é uma
    pergunta ("essa mudança foi intencional?"), não necessariamente um erro.

## Configuração

Cada serviço tem o seu modelo: `backend/.env.example` e `frontend/.env.example`.
O `.env` real nunca é versionado.

O `settings.py` é o único ponto do backend que lê o ambiente. Todo o resto importa
`settings` de lá — assim uma variável renomeada quebra em um lugar só, e um campo
obrigatório ausente derruba a subida da aplicação em vez de falhar no meio de uma
requisição.

!!! danger "Credenciais"
    O arquivo JSON da service account do Google deve ficar **fora** do
    repositório. O `COPY . .` do Dockerfile leva para dentro da imagem tudo que
    estiver na pasta do serviço.
