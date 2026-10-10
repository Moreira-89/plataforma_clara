"""
Teste do healthcheck.

Modelo para os testes de rota: `TestClient` como context manager, porque sem o
`with` o lifespan não roda. Não precisa de banco nem de rede.
"""

from fastapi.testclient import TestClient
from main import app


def test_health_devolve_ok_e_versao():
    with TestClient(app) as client:
        resposta = client.get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "versao": app.version}
