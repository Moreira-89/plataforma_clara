"""
Montagem dos campos de apresentação de um bloco: cor da etiqueta, score e nota de risco.

Compartilhado pelas rotas que devolvem blocos (`/blocos` e `/investimentos`).

COMO FUNCIONA:
    1. `risco` devolve `score` e `nota_risco` de um score numérico (ou ambos vazios).
    2. `listagem_do_bloco` junta os campos do bloco com a cor da pedra e o score ponderado pelo
       capital que cada empresa recebe.

Args:
    Nenhum.

Returns:
    dict: via `risco()` e `listagem_do_bloco()`.

Raises:
    Nenhum.
"""

from collections.abc import Mapping
from decimal import Decimal

from app.domain.blocos import BlocoListado, cor_da_etiqueta
from app.domain.risco import classificar_nota, score_ponderado


def risco(score: float | None) -> dict:
    """`score` e `nota_risco` de um score numérico; sem score, os dois ficam vazios."""
    return {"score": score, "nota_risco": None if score is None else classificar_nota(score)}


def listagem_do_bloco(
    bloco: BlocoListado, pares: list[tuple[str, Decimal]], scores: Mapping[str, float]
) -> dict:
    """Campos do bloco com a cor e o score ponderado pelo capital de cada empresa."""
    score = score_ponderado((scores.get(id_empresa), capital) for id_empresa, capital in pares)
    base = {k: v for k, v in vars(bloco).items() if k != "participacoes"}
    return {**base, "cor": cor_da_etiqueta(bloco.etiqueta), **risco(score)}
