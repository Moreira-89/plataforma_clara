# Autenticação e perfis

Quem cuida de identidade e senha é o **Firebase Auth**. O backend nunca implementa
login próprio: ele cria contas, verifica o token em cada requisição e lê o perfil
que está dentro dele.

## Dois perfis

| Perfil | Quem é | Acesso |
| --- | --- | --- |
| `investidor` | Quem aporta no fundo | Dashboard do investidor, blocos, relatórios |
| `gestora` | Quem administra o fundo (hoje só a Núclea) | Dashboard da gestora, blocos, cadastro de outra gestora |

O perfil viaja numa *custom claim* do token, `perfil`, e nada mais. O CPF/CNPJ não
vai no token: fica no Firestore.

## Por que não existe `/auth/login`

O login acontece **no navegador**, pelo SDK web do Firebase
(`signInWithEmailAndPassword`), que devolve um ID token. A senha não passa pelo
backend nesse momento. O backend só recebe o token, no header
`Authorization: Bearer <token>`, e o verifica.

Para o frontend saber quem está logado e com qual perfil, existe `GET /auth/me`.

## Cadastro

`POST /auth/register` cria uma conta de **investidor**. É aberto, sem token. O
backend faz, nesta ordem:

1. Valida nome, e-mail e CPF/CNPJ (`domain/perfis.py`, que reusa `domain/identidade.py`).
   Falha: 422.
2. **Reserva o documento** em `documentos/{documento}` com `create()`, que falha se
   já existir. Falha: 409.
3. Cria o usuário no Firebase Auth. E-mail repetido: 409, e a reserva é desfeita.
4. Grava `usuarios/{uid}` com perfil, documento, tipo e nome, e aponta a reserva para o uid.
5. Define a claim `perfil` no usuário.
6. Se algo falhar depois do passo 3, o que foi criado é desfeito: não sobra conta pela metade.

Depois do `201`, o frontend faz o login e o token já nasce com a claim.

### Por que o documento fica no Firestore

O CPF/CNPJ normalizado é a chave que liga o usuário aos aportes. Se duas contas
pudessem declarar o mesmo documento, a segunda veria a carteira da primeira. Claims
não permitem perguntar "já existe alguém com este documento?"; o documento reservado
no Firestore permite, e `create()` torna a checagem atômica.

O acesso ao Firestore é só pelo Admin SDK do backend. As regras (`firestore.rules`)
negam qualquer leitura ou escrita vinda do navegador.

## Gestora

Hoje existe uma gestora, a Núclea. O backend já tem a lógica completa de cadastro
de gestora, e ela aparece no Swagger (`/docs`), mas **o frontend só oferece
cadastro de investidor**; o login do frontend atende os dois perfis.

- `POST /auth/register/gestora` exige token de uma gestora e aceita só **CNPJ**.
- A primeira gestora não tem token para chamar essa rota, então é criada pela linha
  de comando, com a credencial da service account:

```bash
cd backend
python -m app.jobs.criar_gestora --nome "Núclea" --email gestora@exemplo.com --cnpj 12.345.678/0001-90
```

## Verificação em cada rota protegida

1. Sem header `Authorization`: **401**.
2. Token inválido ou expirado: **401**, com `WWW-Authenticate: Bearer`.
3. Token válido sem a claim `perfil`: **403**.
4. Perfil sem permissão para a rota: **403**.
5. Falha ao buscar os certificados do Google: **503**.

| Rota | Quem acessa |
| --- | --- |
| `GET /health` | aberta |
| `POST /auth/register` | aberta |
| `POST /auth/register/gestora` | gestora |
| `GET /auth/me` | qualquer perfil |
| `GET /dashboard/gestora` | gestora |
| `GET /dashboard/investidor` | investidor |
| `GET /blocos`, `GET /blocos/{id}` | qualquer perfil |
| `POST /relatorios`, `GET /relatorios/{id}` | investidor |

!!! note "Revogação"
    O token vale até expirar, cerca de 1 hora. A verificação não consulta o Firebase
    a cada requisição (`check_revoked` desligado), para não pôr rede no caminho de
    toda chamada. Se isso virar problema, é uma troca em `storage/firebase.py`.

## Onde cada coisa mora

| Peça | Arquivo |
| --- | --- |
| Perfil, validação de cadastro | `domain/perfis.py` |
| Erros de negócio (viram HTTP em `api/erros.py`) | `domain/erros.py` |
| Verificação de token, Firestore | `storage/firebase.py` |
| Cadastro completo e compensação | `storage/usuarios.py` |
| Credencial da service account | `storage/credenciais.py` |
| `obter_usuario_atual`, `exigir_perfil` | `api/dependencias.py` |
| Rotas | `api/endpoints/auth.py` |

Nos testes, o verificador de token e o cadastro são trocados por fakes com
`app.dependency_overrides` (ver `tests/conftest.py`); nada toca o Firebase.
