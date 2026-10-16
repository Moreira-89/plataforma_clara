"""
Investimentos de demonstração: quais blocos cada investidor "já tem" e com quanto.

Não existe mecanismo real de aporte (a fonte dos dados de aportes ainda não foi decidida). Para as
telas do investidor terem o que mostrar, cada conta recebe, de forma sorteada mas ESTÁVEL, alguns
blocos já investidos. Os valores são fictícios, como o resto dos dados de demonstração.

COMO FUNCIONA:
    1. Para cada par (investidor, bloco), um hash SHA-256 gera números pseudoaleatórios.
    2. Cerca de 40% dos blocos entram na carteira do investidor.
    3. O valor investido é um múltiplo de R$ 5 mil, de R$ 5 mil a R$ 500 mil.
    4. Como o resultado depende só do par, o mesmo investidor vê sempre os mesmos blocos e valores,
       outro investidor vê uma carteira diferente, e blocos novos não embaralham os antigos.

Args:
    Nenhum.

Returns:
    Decimal | None: via `valor_investido()`.

Raises:
    Nenhum.
"""

import hashlib
from decimal import Decimal
from typing import Final

# Fração dos blocos em que cada investidor "já investiu".
PROPORCAO_INVESTIDA: Final[float] = 0.4

PASSO_DO_VALOR: Final[int] = 5_000
_PASSOS_DO_VALOR: Final[int] = 100  # de R$ 5 mil a R$ 500 mil


def _fracao(sal: str, uid: str, id_bloco: str) -> float:
    """Número em [0, 1) determinado por (sal, investidor, bloco)."""
    resumo = hashlib.sha256(f"{sal}:{uid}:{id_bloco}".encode()).digest()
    return int.from_bytes(resumo[:8], "big") / 2**64


def valor_investido(uid: str, id_bloco: str) -> Decimal | None:
    """
    Quanto o investidor "já investiu" no bloco, ou None se não investiu.

    Args:
        uid (str): Uid do investidor no Firebase.
        id_bloco (str): Identificador do bloco.

    Returns:
        Decimal | None: Valor em R$, múltiplo de 5 mil entre 5 mil e 500 mil; None se o bloco
            não está na carteira dele.
    """
    if _fracao("escolha", uid, id_bloco) >= PROPORCAO_INVESTIDA:
        return None
    passos = 1 + int(_fracao("valor", uid, id_bloco) * _PASSOS_DO_VALOR)
    return Decimal(passos * PASSO_DO_VALOR)
