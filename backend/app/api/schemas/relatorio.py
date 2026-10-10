"""
Contratos de resposta dos relatórios em PDF.

COMO FUNCIONA:
    1. `POST /relatorios` devolve um `RelatorioStatus` com o id do pedido.
    2. `GET /relatorios/{id}` devolve o mesmo contrato com o estado atual.

Args:
    Nenhum.

Returns:
    Nenhum.

Raises:
    Nenhum.
"""

from pydantic import BaseModel, Field


class RelatorioStatus(BaseModel):
    """Estado de um relatório pedido pelo investidor."""

    id: str
    status: str = Field(description="Ex.: 'processando', 'pronto' ou 'falhou'")
