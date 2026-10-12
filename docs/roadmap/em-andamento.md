# Em andamento

O que estamos implementando agora, em ordem de prioridade. Cada item lista o
que falta e, quando existe, o que já está pronto pra ser usado assim que o
item for resolvido.

## 1. Fonte dos dados de aportes

**A decisão mais urgente do projeto.** O upload manual de CSV foi removido —
não é assim que a plataforma vai operar com usuários reais. Falta decidir de
onde os dados vêm (provavelmente consulta a um serviço externo que já os
tenha) e como chegam ao BigQuery.

Junto com isso, decidir o **CNPJ alfanumérico** (emitido desde julho de 2026):
hoje o cadastro o recusa, porque o documento normalizado, que liga o usuário
aos aportes, só mantém dígitos. Depende de como a fonte representa o CNPJ.
Decisão a ser tomada com o grupo. Ver [Autenticação](../arquitetura/autenticacao.md).

## 2. Agregação do dashboard (BigQuery)

Depende do item 1. A ideia é o dashboard ler o BigQuery via tabela(s)
"gold", recriadas sob demanda — não em tempo real, não só por job agendado.
Falta decidir a granularidade (uma tabela gold por consulta vs. uma única e
granular com `GROUP BY` leve por cima em cada leitura) e se a recriação
também dispara automático após cada carga de dado nova, além do gatilho
manual. Adiado de propósito: o time vai mexer bastante no dashboard, então
desenhar a agregação antes disso estabilizar seria trabalho jogado fora.

`domain.metricas` já tem as regras de consolidação e montagem das visões —
falta só quem as alimente.

## 3. Endpoints do produto

Funcionam: `GET /health`, `/auth/*` e os blocos de liquidez (`GET /blocos/etiquetas`,
`POST /blocos`, `GET /blocos`, `GET /blocos/{id}` e `GET /empresas`; ver
[Blocos de Liquidez](../arquitetura/blocos.md)), já com o cadastro real de empresas
(`dados_fidc.tb_empresas_fidc`). As demais rotas já existem no contrato e respondem 501
até terem implementação. Planejadas:

- `GET /dashboard/gestora`, `GET /dashboard/investidor`
- `POST /relatorios` + `GET /relatorios/{id}`
- OpenAPI documentado

O que já está pronto para eles chamarem:

- `agents.relatorio.gerar_relatorio_consolidado_investidor` — PDF por IA
- `domain.metricas` — consolidação de KPIs e montagem das visões (sem quem
  as alimente, ver item 2)

## 4. Firestore

Já em uso só para identidade: `usuarios/{uid}` e o índice `documentos/{documento}`
que garante um CPF/CNPJ por conta (ver [Autenticação](../arquitetura/autenticacao.md)).
Dados de aporte continuam fora dele. Falta uma dependência que leia o documento
do usuário para filtrar os aportes dele, que entra com o primeiro endpoint real
do dashboard.

## 5. Redis

Sobe no `docker-compose`, sem cliente na aplicação ainda.

## 6. Frontend

Só a casca hoje (Vite, Dockerfile, proxy de desenvolvimento). Nenhuma tela.

## 7. Lock file de dependências

`requirements.txt` usa faixas de versão (`~=`), sem lock file fixando a
árvore inteira de dependências transitivas.
