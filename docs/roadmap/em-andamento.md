# Em andamento

O que estamos implementando agora, em ordem de prioridade. Cada item lista o
que falta e, quando existe, o que já está pronto pra ser usado assim que o
item for resolvido.

## 1. Fonte dos dados de aportes

**A decisão mais urgente do projeto.** O upload manual de CSV foi removido —
não é assim que a plataforma vai operar com usuários reais. Falta decidir de
onde os dados vêm (provavelmente consulta a um serviço externo que já os
tenha) e como chegam ao BigQuery.

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

## 3. Firebase Auth

Não há verificação de token nem rota protegida ainda. Autorização por
perfil — gestora vs. investidor — depende disso.

Rotas planejadas: `POST /auth/login`, `POST /auth/register`.
As duas já existem em `api/endpoints/auth.py`, respondendo 501.

## 4. Endpoints do produto

`GET /health` funciona. As demais rotas já existem no contrato e respondem
501 até terem implementação. Planejadas:

- `GET /dashboard/gestora`, `GET /dashboard/investidor`
- `GET /blocos`, `GET /blocos/{bloco_id}`
- `POST /relatorios` + `GET /relatorios/{id}`
- OpenAPI documentado, CORS configurado

O que já está pronto para eles chamarem:

- `agents.relatorio.gerar_relatorio_consolidado_investidor` — PDF por IA
- `domain.metricas` — consolidação de KPIs e montagem das visões (sem quem
  as alimente, ver item 2)

## 5. Firestore

Nada implementado. Reservado para o vínculo Firebase UID ↔ CPF/CNPJ do
investidor — pode nem precisar de banco separado, se virar *custom claim*
no token.

## 6. Redis

Sobe no `docker-compose`, sem cliente na aplicação ainda.

## 7. CORS

Sem middleware. Necessário assim que o frontend chamar a API de outro
domínio.

## 8. Frontend

Só a casca hoje (Vite, Dockerfile, proxy de desenvolvimento). Nenhuma tela.

## 9. Lock file de dependências

`requirements.txt` usa faixas de versão (`~=`), sem lock file fixando a
árvore inteira de dependências transitivas.
