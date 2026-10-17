"""
Testes de `domain/investimentos.py`: carteira de demonstração do investidor.

Nenhum destes testes precisa de banco ou de rede.
"""

from datetime import date
from decimal import Decimal

from app.domain.blocos import BlocoDetalhado, BlocoListado, EmpresaDoBlocoDetalhada
from app.domain.investimentos import (
    PASSO_DO_VALOR,
    PROPORCAO_INVESTIDA,
    ranquear_empresas,
    resumir_por_etiqueta,
    valor_investido,
)

BLOCOS = [f"bloco-{i}" for i in range(400)]


def carteira(uid):
    return {b: valor_investido(uid, b) for b in BLOCOS if valor_investido(uid, b) is not None}


def test_o_mesmo_investidor_ve_sempre_os_mesmos_blocos_e_valores():
    assert carteira("uid-a") == carteira("uid-a")


def test_investidores_diferentes_recebem_carteiras_diferentes():
    assert carteira("uid-a") != carteira("uid-b")


def test_cerca_de_quarenta_por_cento_dos_blocos_entram():
    proporcao = len(carteira("uid-a")) / len(BLOCOS)

    assert abs(proporcao - PROPORCAO_INVESTIDA) < 0.1


def test_valor_e_multiplo_de_cinco_mil_entre_cinco_mil_e_quinhentos_mil():
    valores = list(carteira("uid-a").values())

    assert valores
    assert all(v % PASSO_DO_VALOR == 0 for v in valores)
    assert all(Decimal(5_000) <= v <= Decimal(500_000) for v in valores)


def test_os_valores_variam():
    assert len(set(carteira("uid-a").values())) > 5


def test_bloco_novo_nao_muda_o_que_o_investidor_ja_tinha():
    antes = {b: valor_investido("uid-a", b) for b in BLOCOS[:100]}

    depois = {b: valor_investido("uid-a", b) for b in BLOCOS[:100]}
    _ = [valor_investido("uid-a", b) for b in BLOCOS[100:]]

    assert antes == depois


def test_resumo_soma_por_etiqueta_da_maior_para_a_menor():
    resumo = resumir_por_etiqueta(
        [("Rubi", Decimal(10_000)), ("Safira", Decimal(50_000)), ("Rubi", Decimal(15_000))]
    )

    assert [r.etiqueta for r in resumo] == ["Safira", "Rubi"]
    assert resumo[1].total_investido == Decimal(25_000)
    assert resumo[1].quantidade_blocos == 2


def test_resumo_calcula_a_participacao_de_cada_etiqueta():
    resumo = resumir_por_etiqueta([("Rubi", Decimal(25_000)), ("Safira", Decimal(75_000))])

    assert [r.participacao for r in resumo] == [0.75, 0.25]


def test_resumo_desempata_pelo_nome_e_aceita_carteira_vazia():
    empatadas = resumir_por_etiqueta([("Safira", Decimal(5_000)), ("Rubi", Decimal(5_000))])

    assert [r.etiqueta for r in empatadas] == ["Rubi", "Safira"]
    assert resumir_por_etiqueta([]) == []


def bloco_com(etiqueta, *empresas):
    listado = BlocoListado(
        "b",
        "COD",
        etiqueta,
        Decimal(100),
        date(2026, 1, 1),
        date(2030, 1, 1),
        "R",
        None,
        len(empresas),
    )
    return BlocoDetalhado(
        listado,
        tuple(
            EmpresaDoBlocoDetalhada(i, "1", Decimal(0), Decimal(pct), nome, None)
            for i, nome, pct in empresas
        ),
    )


def test_ranking_distribui_o_valor_do_bloco_pela_fatia_de_cada_empresa():
    bloco = bloco_com("Safira", ("e1", "Beta", "25"), ("e2", "Alfa", "75"))

    ranking = ranquear_empresas([(Decimal(100_000), bloco)])

    assert [(r.id_empresa, r.capital_investido) for r in ranking] == [
        ("e2", Decimal("75000.00")),
        ("e1", Decimal("25000.00")),
    ]
    assert [r.participacao for r in ranking] == [0.75, 0.25]
    assert ranking[0].etiqueta == "Safira"


def test_ranking_soma_a_empresa_que_aparece_em_mais_de_um_bloco():
    um = bloco_com("Safira", ("e1", "Alfa", "50"), ("e2", "Beta", "50"))
    outro = bloco_com("Rubi", ("e2", "Beta", "100"))

    ranking = ranquear_empresas([(Decimal(10_000), um), (Decimal(20_000), outro)])

    assert [(r.id_empresa, r.capital_investido) for r in ranking] == [
        ("e2", Decimal("25000.00")),
        ("e1", Decimal("5000.00")),
    ]


def test_ranking_de_carteira_vazia_e_vazio():
    assert ranquear_empresas([]) == []
