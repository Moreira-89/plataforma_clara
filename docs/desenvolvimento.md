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

## Tipagem e pandas

O verificador de tipos (Pylance/Pyright) roda com a configuração em
`pyrightconfig.json`. Duas coisas ali não são óbvias:

**`extraPaths: ["backend"]`.** A raiz de imports do backend é `backend/`, não a
raiz do repositório — é de lá que `from app.config...` faz sentido. O pytest já
sabe disso pelo `pythonpath` do `backend/pytest.ini`; o editor precisa ser avisado
separadamente.

**Os `cast` em `csv_processor.py`.** Eles não mudam nada em tempo de execução. As
stubs do pandas declaram retornos amplos demais: indexar um DataFrame com uma
lista devolve, para o verificador, `DataFrame | Series | Unknown`. Esse tipo se
propaga por toda a função e derruba as chamadas seguintes (`.astype`, `.mask`,
`.dt`, `.dropna`) com erros que não existem de verdade. Um `cast` na origem
resolve a cadeia inteira — foi assim que cinco erros viraram zero.

O mesmo vale para o `DtypeArg` importado sob `TYPE_CHECKING`: é o tipo que o
`read_csv` declara para o parâmetro `dtype`, e vem de `pandas._typing`, que é
módulo privado. Sob `TYPE_CHECKING` ele serve ao verificador sem virar dependência
em tempo de execução.

!!! note "Se o Pylance disser que não resolve `fastapi`"
    O problema é quase sempre o interpretador selecionado no editor, não o código.
    Confira que é o `.venv` da raiz (Python 3.12) — em VS Code,
    **Python: Select Interpreter** e depois **Developer: Reload Window**. O
    `.vscode/settings.json` já aponta para o caminho certo, mas o editor guarda a
    escolha anterior.

### O `astype(object)` da etapa 8 do CSV

Parece redundante e não é. Quem "simplificar" aquela linha reintroduz um bug.

O contrato do `processar_arquivo_csv` é: **o DataFrame devolvido não contém nulos
do Pandas** — nada de `float("nan")`, `pd.NaT` ou `pd.NA`. Só `None`.

A etapa 4 converte as colunas de texto para o dtype `string`. Uma coluna
`StringDtype` **não consegue armazenar `None`**: ela converte silenciosamente para
`pd.NA`. Sem o `astype(object)` antes, o `where()` seguinte vira um no-op
justamente nas colunas de texto opcionais — hoje, `codigo_identificacao_isin`.

Na prática o `to_dict(orient="records")` da ingestão mascara o problema, porque
boxeia `pd.NA` para `None` na saída. Mas isso é garantia do consumidor, não deste
módulo: qualquer leitura por `.iloc`, `.itertuples` ou `.values` receberia `pd.NA`.
E `pd.NA` chegando ao Firestore ou ao BigQuery quebra na serialização.

Há um teste travando isso: `test_todo_valor_do_resultado_e_tipo_nativo_do_python`.
