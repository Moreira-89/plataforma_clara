"""
Testes das rotas-esqueleto: existem no contrato e respondem 501 até terem fonte de dados.

Quando uma rota sair do esqueleto, o teste dela sai desta lista.
"""

import pytest
from fastapi.testclient import TestClient
from main import app

ROTAS = [
    ("POST", "/auth/login"),
    ("POST", "/auth/register"),
    ("GET", "/dashboard/gestora"),
    ("GET", "/dashboard/investidor"),
    ("GET", "/blocos"),
    ("GET", "/blocos/bloco-x"),
    ("POST", "/relatorios"),
    ("GET", "/relatorios/abc"),
]


@pytest.mark.parametrize(("metodo", "caminho"), ROTAS)
def test_rota_esqueleto_responde_501(metodo, caminho):
    with TestClient(app) as client:
        resposta = client.request(metodo, caminho)

    assert resposta.status_code == 501


def test_openapi_lista_todas_as_rotas():
    caminhos = app.openapi()["paths"]

    for _, caminho in ROTAS:
        assert caminho.replace("bloco-x", "{bloco_id}").replace("abc", "{relatorio_id}") in caminhos
