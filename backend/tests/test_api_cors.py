"""
Testes do CORS: só as origens configuradas recebem os cabeçalhos de liberação.

Nenhum destes testes precisa de banco ou de rede.
"""

from app.config.settings import Configuracao, settings


def preflight(client, origem):
    return client.options(
        "/auth/me",
        headers={
            "Origin": origem,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )


def test_origem_liberada_recebe_o_cabecalho(client):
    origem = settings.origens_cors[0]

    resposta = preflight(client, origem)

    assert resposta.status_code == 200
    assert resposta.headers["access-control-allow-origin"] == origem
    assert "authorization" in resposta.headers["access-control-allow-headers"].lower()


def test_origem_desconhecida_nao_e_liberada(client):
    resposta = preflight(client, "https://site-desconhecido.exemplo")

    assert "access-control-allow-origin" not in resposta.headers


def test_resposta_normal_leva_o_cabecalho_da_origem_liberada(client):
    origem = settings.origens_cors[0]

    resposta = client.get("/health", headers={"Origin": origem})

    assert resposta.headers["access-control-allow-origin"] == origem


def test_origens_sao_separadas_por_virgula_e_sem_espacos():
    config = Configuracao(cors_origens=" https://a.exemplo , https://b.exemplo ,")

    assert config.origens_cors == ["https://a.exemplo", "https://b.exemplo"]
