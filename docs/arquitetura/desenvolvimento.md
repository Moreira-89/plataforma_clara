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
# Backend (o .venv fica na raiz do repositório, onde o editor o procura)
python -m venv .venv && source .venv/bin/activate
cd backend
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload      # http://localhost:8000/docs

# Frontend
cd frontend
npm install
npm run dev                    # http://localhost:5173
```

Em desenvolvimento o Vite faz proxy de `/api` para `http://localhost:8000`, então
o frontend funciona sem `VITE_API_URL`.

## Firebase (autenticação)

Passos manuais, uma vez por projeto GCP. Detalhes em [Autenticação](autenticacao.md).

1. No console do Firebase, ativar o provedor **E-mail/senha** em Authentication.
2. Criar o banco **Firestore** em modo Native.
3. Publicar as regras do Firestore. No console do Firebase: **Firestore Database** →
   aba **Regras** → apagar o conteúdo do editor → colar o conteúdo do
   `firestore.rules` da raiz do repositório → **Publicar**.
4. Dar à service account os papéis **Firebase Authentication Admin** e **Cloud Datastore User**.
5. Criar a primeira gestora: `cd backend && python -m app.jobs.criar_gestora --nome ... --email ... --cnpj ...`.

!!! info "Para que servem as regras"
    As regras só valem para acesso vindo do navegador ou do SDK web. O backend usa
    o Admin SDK, que as ignora, então o cadastro funciona com qualquer regra. A
    regra `allow read, write: if false` existe para que ninguém leia ou grave
    CPF/CNPJ direto do navegador.

    Banco criado em **modo de produção** já nega tudo por padrão; em **modo de
    teste** as regras padrão liberam tudo por 30 dias, então publicar é
    necessário. Na dúvida, publique: o resultado é o mesmo. Depois de publicar, a
    aba Regras mostra a data e o texto publicados.

Sem variável nova: o Firebase usa o `PROJECT_ID` e o `GOOGLE_APPLICATION_CREDENTIALS`
que o BigQuery já usa.

### Testar o login no frontend

O frontend tem a home, o cadastro de investidor, o login e a tela de criação de bloco
de liquidez (só gestora). Depois de entrar, a gestora vai direto para essa tela; o
investidor, que ainda não tem tela própria, volta para a home. O login e o cadastro
precisam da config web do Firebase:

1. No console do Firebase: **Configurações do projeto** → **Geral** → **Seus apps** →
   registrar um app da **Web** (`</>`). O console mostra `apiKey` e `authDomain`.
2. Preencher em `frontend/.env`: `VITE_FIREBASE_API_KEY`, `VITE_FIREBASE_AUTH_DOMAIN` e
   `VITE_FIREBASE_PROJECT_ID`. Esses valores não são segredo: vão no bundle.
3. Subir `uvicorn main:app --reload` em `backend/` e `npm run dev` em `frontend/`.
4. Abrir <http://localhost:5173/paginas/login.html>.

Em desenvolvimento o proxy do Vite evita o CORS. Já no Docker, o frontend chama a API
diretamente em outra origem, e é o CORS da API que libera: ele aceita as origens de
`CORS_ORIGENS` em `backend/.env` (separadas por vírgula; padrão `http://localhost:5173`).

`VITE_API_URL` pode ficar **vazio** em desenvolvimento: o frontend usa `/api`, que o
proxy do Vite encaminha ao backend. Em produção ela recebe a URL pública do backend.

!!! warning "Abra em um navegador comum"
    O navegador embutido do VS Code bloqueia a chamada de login ao Google e a tela
    mostra "Sem conexão com o Firebase". Abra <http://localhost:5173> no Chrome,
    Firefox ou Brave. Extensões de bloqueio de anúncio também podem causar o mesmo
    erro; teste em janela anônima.

### Estrutura do frontend

```
index.html                home
paginas/                  uma pasta por área, um HTML por tela
  login.html  cadastro.html
  gestora/gestao-blocos.html     (inclui o pop-up de criação de bloco)
  investidor/blocos-de-liquidez.html
src/css/                  tokens, base e componentes (principal.css junta os três)
  paginas/                um CSS por tela ou grupo de telas
src/js/nucleo/            api, firebase, rotas, ui e menu, usados por todas as telas
src/js/paginas/           um script por tela, espelhando paginas/ (blocos/lista.js serve
                          às duas telas de blocos, gestora e investidor; gestora/novo-bloco.js é o
                          formulário do pop-up)
```

Tela nova: um HTML em `paginas/`, o script em `src/js/paginas/`, o CSS em
`src/css/paginas/` e uma linha em `vite.config.js` para entrar no build.

## Tabelas de blocos no BigQuery

Uma vez por dataset, para criar `tb_blocos_liquidez` e `tb_blocos_empresas`:

```bash
cd backend
python -m app.jobs.criar_tabelas_blocos
```

Usa a credencial e o `BIGQUERY_DATASET` do `backend/.env` (recomendado: `tabelas_silvers`) e
pode rodar de novo sem apagar nada. O cadastro de empresas fica em outro dataset
(`BIGQUERY_DATASET_EMPRESAS`, padrão `dados_fidc`). Detalhes em [Blocos de Liquidez](blocos.md).

## Deploy no Railway

Dois serviços, cada um com o `Dockerfile` da sua pasta (`backend/` e `frontend/`) como raiz.

**Backend** (variáveis do serviço):

| Variável | Valor |
| --- | --- |
| `GOOGLE_APPLICATION_CREDENTIALS` | O JSON da service account em **uma linha só**, sem aspas. |
| `PROJECT_ID` | `plataforma-clara` |
| `BIGQUERY_DATASET` | `tabelas_silvers` (tabelas de blocos) |
| `BIGQUERY_DATASET_EMPRESAS` | `dados_fidc` (cadastro de empresas) |
| `CORS_ORIGENS` | A URL pública do frontend, com `https://` e sem barra no final. |
| `GROQ_API_KEY` | Só para o relatório em PDF (`POST /relatorios`); sem ela a geração falha e o pedido vira `falhou`. |

**Frontend**: as variáveis abaixo entram **no build**, não em tempo de execução. O Vite as embute
no bundle, e o `frontend/Dockerfile` as recebe como build args (`ARG`). Mudou o valor, é preciso
refazer o build do serviço.

| Variável | Valor |
| --- | --- |
| `VITE_API_URL` | A URL pública do backend. |
| `VITE_FIREBASE_API_KEY` | A `apiKey` do app Web no console do Firebase. |
| `VITE_FIREBASE_AUTH_DOMAIN` | O `authDomain` do app Web. |
| `VITE_FIREBASE_PROJECT_ID` | `plataforma-clara` |

**Firebase:** em Authentication → Configurações → Domínios autorizados, acrescente o domínio
público do frontend; sem isso o login falha na versão publicada.

**Se o login mostrar "A configuração do Firebase está ausente ou inválida":** alguma das três
variáveis `VITE_FIREBASE_*` não chegou ao build do frontend (faltou defini-la, ou o build é anterior
a ela). Defina a variável no serviço e refaça o build.

**Conferir depois de publicar:** `GET <backend>/health` responde `{"status":"ok"}`; a home do
frontend abre; o login funciona; a Gestão de Blocos lista os blocos. Um erro de CORS no
console do navegador quer dizer que `CORS_ORIGENS` não bate exatamente com a URL do frontend.

## Qualidade

```bash
cd backend
ruff check ..              # lint do repositório inteiro (é o que a CI roda)
```

O projeto **não tem testes automatizados**, por decisão do dono: é um projeto acadêmico e testes
unitários não importam agora. A pasta `backend/tests/` e o pytest foram removidos. A conferência é
manual, pela documentação interativa (`/docs`) e pelo frontend.

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

## Tipagem

O verificador de tipos (Pylance/Pyright) roda com a configuração em
`pyrightconfig.json`.

**`extraPaths: ["backend"]`.** A raiz de imports do backend é `backend/`, não a
raiz do repositório — é de lá que `from app.config...` faz sentido. O editor precisa ser avisado disso.

!!! note "Se o Pylance disser que não resolve `fastapi`"
    O problema é quase sempre o interpretador selecionado no editor, não o código.
    Confira que é o `.venv` da raiz (Python 3.12) — em VS Code,
    **Python: Select Interpreter** e depois **Developer: Reload Window**. O
    `.vscode/settings.json` já aponta para o caminho certo, mas o editor guarda a
    escolha anterior.
