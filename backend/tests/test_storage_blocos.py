"""
Testes de `storage/empresas.py` e `storage/blocos.py` com um cliente BigQuery falso.

Conferem a ordem das consultas, os parâmetros e a tradução dos erros; o SQL em si foi
exercitado à mão no BigQuery real.
"""

from datetime import UTC, date, datetime
from decimal import Decimal as D
from types import SimpleNamespace

import pytest
from google.api_core.exceptions import NotFound

from app.domain.blocos import AlocacaoEmpresa, montar_bloco
from app.domain.erros import (
    BlocoNaoEncontradoError,
    DadosIndisponiveisError,
    EmpresaJaEmBlocoError,
    EmpresaNaoEncontradaError,
)
from app.storage import blocos, empresas


class JobFalso:
    def __init__(self, resposta):
        self.resposta = resposta

    def result(self):
        if isinstance(self.resposta, Exception):
            raise self.resposta
        return self.resposta


class ClienteFalso:
    """Devolve, em ordem, uma resposta por consulta e guarda o que foi consultado."""

    def __init__(self, *respostas):
        self.respostas = list(respostas)
        self.consultas = []

    def query(self, sql, job_config=None):
        self.consultas.append((sql, job_config))
        return JobFalso(self.respostas.pop(0))


@pytest.fixture
def bloco():
    return montar_bloco(
        "Safira",
        D("1000"),
        date(2999, 1, 1),
        "Lucas",
        "obs",
        [AlocacaoEmpresa("e1", D("40")), AlocacaoEmpresa("e2", D("60"))],
        agora=datetime(2026, 10, 9, tzinfo=UTC),
        id_bloco="id-1",
    )


def usar(monkeypatch, modulo, cliente):
    monkeypatch.setattr(modulo, "cliente_compartilhado", lambda: cliente)


def linha(**campos):
    return SimpleNamespace(**campos)


def test_busca_manda_o_texto_como_parametro_e_nao_no_sql(monkeypatch):
    cliente = ClienteFalso(
        [
            linha(
                id_empresa="e1",
                nome_fantasia="Alfa",
                razao_social="Alfa Ltda",
                cnpj="1",
                ramo_atividade="Varejo",
            )
        ]
    )
    usar(monkeypatch, empresas, cliente)

    achadas = empresas.buscar_empresas("Alfa'; DROP TABLE x; --")

    sql, config = cliente.consultas[0]
    assert "DROP TABLE" not in sql
    parametros = {p.name: p.value for p in config.query_parameters}
    assert parametros["texto"] == "Alfa'; DROP TABLE x; --"
    assert parametros["digitos"] == ""
    assert achadas[0].nome_fantasia == "Alfa"


def test_busca_por_cnpj_com_mascara_manda_so_os_digitos(monkeypatch):
    cliente = ClienteFalso([])
    usar(monkeypatch, empresas, cliente)

    empresas.buscar_empresas("11.222.333/0001-81")

    parametros = {p.name: p.value for p in cliente.consultas[0][1].query_parameters}
    assert parametros["digitos"] == "11222333000181"


def test_busca_sem_a_tabela_vira_dados_indisponiveis(monkeypatch):
    usar(monkeypatch, empresas, ClienteFalso(NotFound("sem tb_empresas")))

    with pytest.raises(DadosIndisponiveisError):
        empresas.buscar_empresas("alfa")


def test_criar_bloco_confere_empresas_e_grava_numa_transacao(monkeypatch, bloco):
    cliente = ClienteFalso(
        [
            linha(id_empresa="e1", cnpj="11222333000181"),
            linha(id_empresa="e2", cnpj="11444777000161"),
        ],
        [],
        [],
    )
    usar(monkeypatch, blocos, cliente)

    blocos.criar_bloco(bloco, "u-ges")

    assert len(cliente.consultas) == 3
    script = cliente.consultas[2][0]
    assert "BEGIN TRANSACTION" in script and "COMMIT TRANSACTION" in script
    assert script.index("tb_blocos_liquidez") < script.index("tb_blocos_empresas")


def test_empresa_fora_do_cadastro_nao_grava(monkeypatch, bloco):
    cliente = ClienteFalso([linha(id_empresa="e1", cnpj="11222333000181")])
    usar(monkeypatch, blocos, cliente)

    with pytest.raises(EmpresaNaoEncontradaError, match="e2"):
        blocos.criar_bloco(bloco, "u-ges")

    assert len(cliente.consultas) == 1


def test_empresa_que_ja_esta_em_bloco_nao_grava(monkeypatch, bloco):
    cliente = ClienteFalso(
        [
            linha(id_empresa="e1", cnpj="11222333000181"),
            linha(id_empresa="e2", cnpj="11444777000161"),
        ],
        [linha(id_empresa="e2")],
    )
    usar(monkeypatch, blocos, cliente)

    with pytest.raises(EmpresaJaEmBlocoError, match="e2"):
        blocos.criar_bloco(bloco, "u-ges")

    assert len(cliente.consultas) == 2


def test_tabela_ausente_vira_dados_indisponiveis(monkeypatch, bloco):
    usar(monkeypatch, blocos, ClienteFalso(NotFound("sem tabela")))

    with pytest.raises(DadosIndisponiveisError):
        blocos.criar_bloco(bloco, "u-ges")


def linha_bloco(**campos):
    base = {
        "id_bloco": "b1",
        "codigo_identificacao": "BLOCO_SAFIRA_1",
        "etiqueta": "Safira",
        "capital_total": D("1000"),
        "data_criacao": date(2026, 10, 9),
        "data_vencimento": date(2030, 1, 1),
        "responsavel_tecnico": "Lucas",
        "observacao": None,
        "quantidade_empresas": 2,
    }
    return linha(**{**base, **campos})


def linha_empresa(**campos):
    base = {
        "id_empresa": "e1",
        "cnpj": "11222333000181",
        "capital_estimado": D("400"),
        "percentual_liquidez": D("40"),
        "nome_fantasia": "Alfa",
        "ramo_atividade": "Varejo",
    }
    return linha(**{**base, **campos})


def test_listar_blocos_devolve_um_item_por_bloco(monkeypatch):
    cliente = ClienteFalso([linha_bloco(), linha_bloco(id_bloco="b2", etiqueta="Rubi")])
    usar(monkeypatch, blocos, cliente)

    lista = blocos.listar_blocos()

    assert [b.id_bloco for b in lista] == ["b1", "b2"]
    assert lista[0].quantidade_empresas == 2
    assert "ORDER BY b.criado_em DESC" in cliente.consultas[0][0]


def test_listar_blocos_sem_tabela_vira_dados_indisponiveis(monkeypatch):
    usar(monkeypatch, blocos, ClienteFalso(NotFound("sem tabela")))

    with pytest.raises(DadosIndisponiveisError):
        blocos.listar_blocos()


def test_buscar_bloco_manda_o_id_como_parametro(monkeypatch):
    cliente = ClienteFalso([linha_bloco()], [linha_empresa()])
    usar(monkeypatch, blocos, cliente)

    detalhado = blocos.buscar_bloco("b1' OR '1'='1")

    for sql, config in cliente.consultas:
        assert "OR '1'='1" not in sql
        assert {p.name: p.value for p in config.query_parameters} == {"id_bloco": "b1' OR '1'='1"}
    assert detalhado.empresas[0].nome_fantasia == "Alfa"


def test_buscar_bloco_inexistente(monkeypatch):
    usar(monkeypatch, blocos, ClienteFalso([]))

    with pytest.raises(BlocoNaoEncontradoError):
        blocos.buscar_bloco("nao-existe")


def test_buscar_bloco_sem_o_cadastro_de_empresas_devolve_sem_nome(monkeypatch):
    cliente = ClienteFalso(
        [linha_bloco()],
        NotFound("sem tb_empresas"),
        [linha_empresa(nome_fantasia=None, ramo_atividade=None)],
    )
    usar(monkeypatch, blocos, cliente)

    detalhado = blocos.buscar_bloco("b1")

    assert detalhado.empresas[0].nome_fantasia is None
    assert "tb_empresas" in cliente.consultas[1][0]
    assert "tb_empresas" not in cliente.consultas[2][0]


def test_buscar_bloco_com_tabela_de_blocos_ausente_vira_dados_indisponiveis(monkeypatch):
    usar(monkeypatch, blocos, ClienteFalso(NotFound("sem tabela")))

    with pytest.raises(DadosIndisponiveisError):
        blocos.buscar_bloco("b1")
