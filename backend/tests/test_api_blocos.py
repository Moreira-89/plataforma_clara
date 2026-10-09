"""
Testes de `/blocos/etiquetas`, `POST /blocos` e `/empresas`.

O BigQuery é trocado por fakes em `conftest.py`; nada toca a rede.
"""

from conftest import cabecalho

from app.domain.erros import (
    DadosIndisponiveisError,
    EmpresaJaEmBlocoError,
    EmpresaNaoEncontradaError,
)

CORPO = {
    "etiqueta": "Safira",
    "capital_total": "1000000.00",
    "data_vencimento": "2999-01-01",
    "responsavel_tecnico": "Lucas",
    "observacao": "primeiro bloco",
    "empresas": [
        {"id_empresa": "e1", "percentual_liquidez": "5"},
        {"id_empresa": "e2", "percentual_liquidez": "95"},
    ],
}


def test_etiquetas_exigem_login(client):
    assert client.get("/blocos/etiquetas").status_code == 401


def test_etiquetas_servem_a_qualquer_perfil(client):
    resposta = client.get("/blocos/etiquetas", headers=cabecalho("investidor"))

    assert resposta.status_code == 200
    etiquetas = resposta.json()
    assert len(etiquetas) == 15
    assert {"nome": "Safira", "cor": "#0F52BA"} in etiquetas


def test_busca_de_empresas_so_para_gestora(client):
    assert client.get("/empresas?busca=alfa").status_code == 401
    assert client.get("/empresas?busca=alfa", headers=cabecalho("investidor")).status_code == 403


def test_busca_de_empresas_devolve_as_encontradas(client, catalogo):
    resposta = client.get("/empresas?busca=alfa", headers=cabecalho("gestora"))

    assert resposta.status_code == 200
    assert resposta.json()[0] == {
        "id_empresa": "e1",
        "nome_fantasia": "Móveis Alfa",
        "razao_social": "Alfa Móveis Ltda",
        "cnpj": "11222333000181",
        "ramo_atividade": "Varejo",
    }
    assert catalogo.buscas == ["alfa"]


def test_busca_curta_demais_responde_422(client):
    assert client.get("/empresas?busca=a", headers=cabecalho("gestora")).status_code == 422


def test_busca_com_cadastro_fora_do_ar_responde_503(client, catalogo):
    catalogo.erro = DadosIndisponiveisError("fora do ar")

    assert client.get("/empresas?busca=alfa", headers=cabecalho("gestora")).status_code == 503


def test_criar_bloco_exige_login_e_perfil_de_gestora(client):
    assert client.post("/blocos", json=CORPO).status_code == 401
    assert client.post("/blocos", json=CORPO, headers=cabecalho("investidor")).status_code == 403


def test_gestora_cria_bloco(client, criador_de_bloco):
    resposta = client.post("/blocos", json=CORPO, headers=cabecalho("gestora"))

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["codigo_identificacao"].startswith("BLOCO_SAFIRA_")
    assert [e["capital_estimado"] for e in corpo["empresas"]] == ["50000.00", "950000.00"]
    bloco, uid = criador_de_bloco.criados[0]
    assert uid == "u-ges"
    assert bloco.observacao == "primeiro bloco"


def test_soma_diferente_de_cem_responde_422_e_nao_grava(client, criador_de_bloco):
    corpo = {**CORPO, "empresas": [{"id_empresa": "e1", "percentual_liquidez": "60"}]}

    resposta = client.post("/blocos", json=corpo, headers=cabecalho("gestora"))

    assert resposta.status_code == 422
    assert "100%" in resposta.json()["detail"]
    assert criador_de_bloco.criados == []


def test_etiqueta_invalida_responde_422(client):
    corpo = {**CORPO, "etiqueta": "Pedra Inexistente"}

    assert client.post("/blocos", json=corpo, headers=cabecalho("gestora")).status_code == 422


def test_vencimento_no_passado_responde_422(client):
    corpo = {**CORPO, "data_vencimento": "2020-01-01"}

    assert client.post("/blocos", json=corpo, headers=cabecalho("gestora")).status_code == 422


def test_porcentagem_com_tres_casas_responde_422(client):
    empresas = [
        {"id_empresa": "e1", "percentual_liquidez": "12.345"},
        {"id_empresa": "e2", "percentual_liquidez": "87.655"},
    ]

    resposta = client.post(
        "/blocos", json={**CORPO, "empresas": empresas}, headers=cabecalho("gestora")
    )

    assert resposta.status_code == 422


def test_empresa_que_ja_esta_em_bloco_responde_409(client, criador_de_bloco):
    criador_de_bloco.erro = EmpresaJaEmBlocoError("Empresa já pertence a outro bloco: e1.")

    resposta = client.post("/blocos", json=CORPO, headers=cabecalho("gestora"))

    assert resposta.status_code == 409


def test_empresa_fora_do_cadastro_responde_422(client, criador_de_bloco):
    criador_de_bloco.erro = EmpresaNaoEncontradaError("Empresa fora do cadastro: e1.")

    assert client.post("/blocos", json=CORPO, headers=cabecalho("gestora")).status_code == 422


def test_tabelas_fora_do_ar_respondem_503(client, criador_de_bloco):
    criador_de_bloco.erro = DadosIndisponiveisError("fora do ar")

    assert client.post("/blocos", json=CORPO, headers=cabecalho("gestora")).status_code == 503
