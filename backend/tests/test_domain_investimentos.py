"""
Testes de `domain/investimentos.py`: carteira de demonstração do investidor.

Nenhum destes testes precisa de banco ou de rede.
"""

from decimal import Decimal

from app.domain.investimentos import PASSO_DO_VALOR, PROPORCAO_INVESTIDA, valor_investido

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
