# O que falta

Lista honesta do que **não existe** no repositório hoje. Está aqui para ninguém —
pessoa ou assistente — assumir que existe.

## 1. Fonte dos dados de aportes

**O buraco mais importante — e o mais urgente de decidir.** O upload manual de
CSV pela gestora foi removido de propósito: não é assim que a plataforma vai
operar quando tiver usuários de verdade. Em vez disso, a ideia é consultar
direto algum serviço que já tenha esses dados — mas isso não está desenhado.

Consequência concreta: `tb_aporte` no BigQuery não recebe escrita de lugar
nenhum hoje, e `agents/relatorio.py` (que consulta essa tabela) sempre falha
com "nenhum investimento encontrado".

## 2. Agregação do dashboard (BigQuery) — AD-6

Decisão registrada no roadmap do Notion: uma tabela gold por consulta vs. uma
gold única e granular, e se a recriação roda automática após cada carga de
dado ou só sob demanda. Adiada de propósito — o time vai mexer bastante no
dashboard, então desenhar a agregação antes disso estabilizar seria trabalho
jogado fora. `domain/metricas.py` já tem as regras de consolidação; falta
decidir o que as alimenta. Depende do item 1.

## 3. Firebase Auth

Não há verificação de token nem rota protegida. Falta o Firebase Admin no
lifespan, a dependência que valida o token e a leitura das claims.

## 4. Endpoints

Nenhum — nem `/health`. `api/endpoints/authentication.py` e `register.py`
existem como arquivo, vazios.

O que já está pronto para ser chamado por eles:

- `agents.relatorio.gerar_relatorio_consolidado_investidor` — PDF por IA
  (hoje sempre falha, ver item 1)
- `domain.metricas` — consolidação de KPIs e montagem das visões (sem quem as
  alimente, ver item 2)

## 5. Firestore

Nada implementado. Reservado para o vínculo Firebase UID ↔ CPF/CNPJ do
investidor — e pode nem precisar de banco separado, se esse vínculo virar
custom claim no próprio token do Firebase.

## 6. Redis

Sobe no compose, com interface em <http://localhost:8001>, mas **não há cliente na
aplicação**. Nada é cacheado.

## 7. CORS

Sem middleware. Precisa entrar quando o frontend chamar a API de outro domínio.

## 8. Frontend

Existe a casca: Vite, Dockerfile, nginx e o proxy de desenvolvimento. Nenhuma tela.

## Dívidas que atravessaram a reconstrução

**Enumeração de e-mail.** A autenticação anterior distinguia "e-mail não
cadastrado" de "senha errada" pelo tempo de resposta, e o cadastro dizia
explicitamente quando o e-mail já existia. O código saiu com o Firebase, mas vale
conferir como o Firebase se comporta nesse ponto antes de expor o cadastro.

**PDF de referência ausente.** O gerador de relatório tenta ler um PDF de
referência que não está versionado. O código trata a ausência, mas o prompt fica
sem aquele trecho.

**`formatar_milhoes` erra acima de R$ 1 bilhão.** Devolve `R$ 1,500,0M`. Está
travado por teste, documentado como bug conhecido.
