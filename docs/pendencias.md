# O que falta

Lista honesta do que **não existe** no repositório hoje. Está aqui para ninguém —
pessoa ou assistente — assumir que existe.

## 1. Firestore

**O buraco mais importante.** A ingestão processa o CSV e carrega no BigQuery, mas
**não grava em nenhum banco de leitura rápida**. `ingerir_csv` devolve os
registros prontos nos dois formatos; falta quem os persista.

Sem isso, o dashboard não tem de onde ler sem varrer o analítico — que é lento e
cobrado por byte lido.

## 2. Firebase Auth

Não há verificação de token nem rota protegida. Falta o Firebase Admin no
lifespan, a dependência que valida o token e a leitura das claims.

## 3. Endpoints

Só existe `/health`. Nenhuma rota de aporte, dashboard, bloco ou relatório.

O que já está pronto para ser chamado por eles:

- `ingestion.ingerir_csv` — validação e preparo dos registros
- `ingestion.enviar_ao_bigquery` — carga analítica
- `agents.relatorio.gerar_relatorio_consolidado_investidor` — PDF por IA
- `domain.metricas` — consolidação de KPIs e montagem das visões

## 4. Redis

Sobe no compose, com interface em <http://localhost:8001>, mas **não há cliente na
aplicação**. Nada é cacheado.

## 5. Agregações do dashboard

`domain/metricas.py` tem as regras de consolidação, mas nada as alimenta: as
consultas eram SQL e saíram com o Postgres.

!!! note "Um detalhe que vai reaparecer"
    As funções de métricas foram escritas assumindo linhas vindas de um `GROUP BY`.
    Quando o Firestore entrar, a forma dos dados de entrada muda — elas podem
    precisar de ajuste, ou de descarte, se a agregação passar a ser feita no
    BigQuery.

## 6. Frontend

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
