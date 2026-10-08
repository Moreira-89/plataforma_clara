"""
Testes de `/auth`: verificação de token, perfil e cadastro.

O Firebase é trocado por fakes em `conftest.py`; nada toca a rede.
"""

from conftest import cabecalho

CORPO = {
    "nome": "Ana",
    "email": "Ana@Exemplo.com",
    "senha": "senha-segura",
    "documento": "123.456.789-09",
}
CNPJ = "11.222.333/0001-81"


def test_me_sem_token_responde_401(client):
    resposta = client.get("/auth/me")

    assert resposta.status_code == 401
    assert resposta.headers["WWW-Authenticate"] == "Bearer"


def test_me_com_token_invalido_responde_401(client):
    assert client.get("/auth/me", headers=cabecalho("lixo")).status_code == 401


def test_me_com_token_sem_perfil_responde_403(client):
    assert client.get("/auth/me", headers=cabecalho("sem-perfil")).status_code == 403


def test_me_devolve_usuario_e_perfil(client):
    resposta = client.get("/auth/me", headers=cabecalho("investidor"))

    assert resposta.status_code == 200
    assert resposta.json() == {"uid": "u-inv", "perfil": "investidor", "email": "inv@exemplo.com"}


def test_cadastro_de_investidor_e_aberto(client, cadastro):
    resposta = client.post("/auth/register", json=CORPO)

    assert resposta.status_code == 201
    assert resposta.json() == {"uid": "uid-1", "perfil": "investidor"}
    dados, senha, perfil = cadastro.chamadas[0]
    assert (dados.email, dados.documento, senha, perfil.value) == (
        "ana@exemplo.com",
        "12345678909",
        "senha-segura",
        "investidor",
    )


def test_cadastro_nao_devolve_a_senha(client):
    assert "senha" not in client.post("/auth/register", json=CORPO).text


def test_cadastro_com_documento_repetido_responde_409(client):
    client.post("/auth/register", json=CORPO)

    resposta = client.post("/auth/register", json={**CORPO, "email": "outro@exemplo.com"})

    assert resposta.status_code == 409


def test_cadastro_com_email_repetido_responde_409(client):
    client.post("/auth/register", json=CORPO)

    resposta = client.post("/auth/register", json={**CORPO, "documento": CNPJ})

    assert resposta.status_code == 409


def test_cadastro_com_documento_invalido_responde_422(client):
    assert client.post("/auth/register", json={**CORPO, "documento": "123"}).status_code == 422


def test_cadastro_com_senha_curta_responde_422(client):
    assert client.post("/auth/register", json={**CORPO, "senha": "123"}).status_code == 422


def test_cadastro_de_gestora_sem_token_responde_401(client):
    assert client.post("/auth/register/gestora", json=CORPO).status_code == 401


def test_cadastro_de_gestora_por_investidor_responde_403(client):
    resposta = client.post("/auth/register/gestora", json=CORPO, headers=cabecalho("investidor"))

    assert resposta.status_code == 403


def test_cadastro_de_gestora_por_gestora_responde_201(client):
    corpo = {**CORPO, "documento": CNPJ}

    resposta = client.post("/auth/register/gestora", json=corpo, headers=cabecalho("gestora"))

    assert resposta.status_code == 201
    assert resposta.json()["perfil"] == "gestora"


def test_cadastro_de_gestora_com_cpf_responde_422(client):
    resposta = client.post("/auth/register/gestora", json=CORPO, headers=cabecalho("gestora"))

    assert resposta.status_code == 422
