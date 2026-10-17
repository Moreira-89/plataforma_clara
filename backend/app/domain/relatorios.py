"""
Relatório em PDF do investidor: o estado de um pedido.

COMO FUNCIONA:
    1. `StatusRelatorio` diz em que pé está o pedido: processando, pronto ou falhou.
    2. `Relatorio` guarda o dono (uid), o estado e, quando pronto, o PDF e o nome do arquivo.

Args:
    Nenhum.

Returns:
    Nenhum.

Raises:
    Nenhum.
"""

from dataclasses import dataclass
from enum import StrEnum


class StatusRelatorio(StrEnum):
    """Estados de um pedido de relatório."""

    PROCESSANDO = "processando"
    PRONTO = "pronto"
    FALHOU = "falhou"


@dataclass
class Relatorio:
    """Um pedido de relatório; o PDF só existe depois de pronto."""

    id: str
    uid: str
    status: StatusRelatorio = StatusRelatorio.PROCESSANDO
    pdf: bytes | None = None
    arquivo: str | None = None
    mensagem: str | None = None
