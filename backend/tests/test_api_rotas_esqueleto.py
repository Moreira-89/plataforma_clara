"""
Testes das rotas-esqueleto: exigem o perfil certo e respondem 501 até terem fonte de dados.

Quando uma rota sair do esqueleto, o teste dela sai desta lista.
"""

import pytest
from conftest import cabecalho

# (método, caminho, perfil que passa, perfil que deve ser recusado ou None se qualquer um passa)
ROTAS = [
    ("GET", "/dashboard/gestora", "gestora", "investidor"),
    ("GET", "/dashboard/investidor", "investidor", "gestora"),
    ("GET", "/blocos", "investidor", None),
    ("GET", "/blocos/bloco-x", "gestora", None),
    ("POST", "/relatorios", "investidor", "gestora"),
    ("GET", "/relatorios/abc", "investidor", "gestora"),
]


@pytest.mark.parametrize(("metodo", "caminho", "_certo", "_errado"), ROTAS)
def test_sem_token_responde_401(client, metodo, caminho, _certo, _errado):
    assert client.request(metodo, caminho).status_code == 401


@pytest.mark.parametrize(
    ("metodo", "caminho", "_certo", "errado"), [r for r in ROTAS if r[3] is not None]
)
def test_perfil_errado_responde_403(client, metodo, caminho, _certo, errado):
    resposta = client.request(metodo, caminho, headers=cabecalho(errado))

    assert resposta.status_code == 403


@pytest.mark.parametrize(("metodo", "caminho", "certo", "_errado"), ROTAS)
def test_perfil_certo_chega_ao_esqueleto_501(client, metodo, caminho, certo, _errado):
    resposta = client.request(metodo, caminho, headers=cabecalho(certo))

    assert resposta.status_code == 501


def test_openapi_lista_todas_as_rotas(client):
    caminhos = client.get("/openapi.json").json()["paths"]

    esperados = {
        "/health",
        "/auth/me",
        "/auth/register",
        "/auth/register/gestora",
        "/dashboard/gestora",
        "/dashboard/investidor",
        "/blocos",
        "/blocos/{bloco_id}",
        "/relatorios",
        "/relatorios/{relatorio_id}",
    }
    assert esperados <= set(caminhos)
    assert "/auth/login" not in caminhos
