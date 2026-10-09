"""
Testes de `domain/blocos.py`: etiquetas, código e validação do bloco de liquidez.

Nenhum destes testes precisa de banco ou de rede.
"""

from datetime import UTC, date, datetime
from decimal import Decimal as D

import pytest

from app.domain.blocos import ETIQUETAS, AlocacaoEmpresa, montar_bloco, slug_etiqueta
from app.domain.erros import BlocoInvalidoError

AGORA = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)
VENCIMENTO = date(2030, 1, 1)
DUAS = [AlocacaoEmpresa("e1", D("5")), AlocacaoEmpresa("e2", D("95"))]


def montar(**mudancas):
    dados = {
        "etiqueta": "Safira",
        "capital_total": D("1000000"),
        "data_vencimento": VENCIMENTO,
        "responsavel_tecnico": "Lucas",
        "observacao": None,
        "alocacoes": DUAS,
    }
    dados.update(mudancas)
    return montar_bloco(**dados, agora=AGORA, id_bloco="id-1")


def test_sao_quinze_etiquetas_com_cor_hexadecimal():
    assert len(ETIQUETAS) == 15
    assert all(cor.startswith("#") and len(cor) == 7 for cor in ETIQUETAS.values())


@pytest.mark.parametrize(
    ("nome", "esperado"),
    [("Safira", "SAFIRA"), ("Turmalina Paraíba", "TURMALINA_PARAIBA"), ("Benitoíta", "BENITOITA")],
)
def test_slug_da_etiqueta(nome, esperado):
    assert slug_etiqueta(nome) == esperado


def test_bloco_valido_calcula_capital_estimado_de_cada_empresa():
    bloco = montar()

    assert [e.capital_estimado for e in bloco.empresas] == [D("50000.00"), D("950000.00")]


def test_codigo_leva_a_etiqueta_e_o_instante_em_milissegundos():
    assert montar().codigo_identificacao == f"BLOCO_SAFIRA_{int(AGORA.timestamp() * 1000)}"


def test_data_de_criacao_e_a_do_dia_em_brasilia():
    tarde_da_noite_utc = datetime(2026, 10, 10, 1, 0, tzinfo=UTC)

    bloco = montar_bloco(
        "Safira", D("100"), VENCIMENTO, "Lucas", None, DUAS, agora=tarde_da_noite_utc, id_bloco="x"
    )

    assert bloco.data_criacao == date(2026, 10, 9)


def test_responsavel_e_observacao_sao_aparados():
    bloco = montar(responsavel_tecnico="  Lucas  ", observacao="  nota  ")

    assert (bloco.responsavel_tecnico, bloco.observacao) == ("Lucas", "nota")


def test_porcentagem_com_duas_casas_decimais_e_aceita():
    bloco = montar(alocacoes=[AlocacaoEmpresa("e1", D("12.50")), AlocacaoEmpresa("e2", D("87.50"))])

    assert bloco.empresas[0].capital_estimado == D("125000.00")


@pytest.mark.parametrize(
    "mudanca",
    [
        {"etiqueta": "Pedra Inexistente"},
        {"capital_total": D("0")},
        {"capital_total": D("-1")},
        {"capital_total": D("10.123")},
        {"data_vencimento": date(2026, 10, 9)},
        {"data_vencimento": date(2020, 1, 1)},
        {"responsavel_tecnico": "   "},
        {"observacao": "x" * 501},
        {"alocacoes": []},
        {"alocacoes": [AlocacaoEmpresa("e1", D("50")), AlocacaoEmpresa("e1", D("50"))]},
        {"alocacoes": [AlocacaoEmpresa("e1", D("0")), AlocacaoEmpresa("e2", D("100"))]},
        {"alocacoes": [AlocacaoEmpresa("e1", D("12.345")), AlocacaoEmpresa("e2", D("87.655"))]},
        {"alocacoes": [AlocacaoEmpresa("e1", D("100.01"))]},
    ],
)
def test_dados_invalidos_sao_recusados(mudanca):
    with pytest.raises(BlocoInvalidoError):
        montar(**mudanca)


@pytest.mark.parametrize("percentuais", [["50", "49.99"], ["50", "50.01"], ["99"]])
def test_soma_diferente_de_cem_e_recusada(percentuais):
    alocacoes = [AlocacaoEmpresa(f"e{i}", D(p)) for i, p in enumerate(percentuais)]

    with pytest.raises(BlocoInvalidoError, match="100%"):
        montar(alocacoes=alocacoes)


def test_observacao_com_quinhentos_caracteres_passa():
    assert len(montar(observacao="x" * 500).observacao) == 500
