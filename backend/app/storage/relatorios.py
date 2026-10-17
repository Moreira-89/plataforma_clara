"""
Repositório dos relatórios pedidos, guardados em memória do processo.

Os PDFs não são persistidos: somem quando o backend reinicia (persistir em storage está no roadmap).

COMO FUNCIONA:
    1. `criar` registra um pedido novo do investidor, em `processando`.
    2. `concluir` e `falhar` fecham o pedido; `obter` só devolve pedidos do próprio dono.
    3. `em_andamento` evita pedidos duplicados enquanto um do mesmo investidor ainda roda.
    4. Passando do limite de pedidos guardados, os mais antigos são descartados.

Args:
    Nenhum.

Returns:
    RepositorioDeRelatorios: via o objeto `repositorio` do módulo.

Raises:
    Nenhum.
"""

import uuid
from collections import OrderedDict
from typing import Final

from app.domain.relatorios import Relatorio, StatusRelatorio

LIMITE_DE_RELATORIOS: Final[int] = 50


class RepositorioDeRelatorios:
    """Pedidos de relatório em memória, do mais antigo para o mais novo."""

    def __init__(self, limite: int = LIMITE_DE_RELATORIOS) -> None:
        self._itens: OrderedDict[str, Relatorio] = OrderedDict()
        self._limite = limite

    def criar(self, uid: str) -> Relatorio:
        """Registra um pedido novo em `processando`."""
        relatorio = Relatorio(id=uuid.uuid4().hex, uid=uid)
        self._itens[relatorio.id] = relatorio
        while len(self._itens) > self._limite:
            self._itens.popitem(last=False)
        return relatorio

    def obter(self, id_relatorio: str, uid: str) -> Relatorio | None:
        """O pedido, se existir e for do investidor; senão None."""
        relatorio = self._itens.get(id_relatorio)
        return relatorio if relatorio and relatorio.uid == uid else None

    def em_andamento(self, uid: str) -> Relatorio | None:
        """O pedido ainda em `processando` do investidor, se houver."""
        return next(
            (
                r
                for r in self._itens.values()
                if r.uid == uid and r.status == StatusRelatorio.PROCESSANDO
            ),
            None,
        )

    def concluir(self, id_relatorio: str, pdf: bytes, arquivo: str) -> None:
        """Marca o pedido como pronto, com o PDF."""
        if relatorio := self._itens.get(id_relatorio):
            relatorio.status, relatorio.pdf, relatorio.arquivo = (
                StatusRelatorio.PRONTO,
                pdf,
                arquivo,
            )

    def falhar(self, id_relatorio: str, mensagem: str) -> None:
        """Marca o pedido como falho, com a mensagem para o investidor."""
        if relatorio := self._itens.get(id_relatorio):
            relatorio.status, relatorio.mensagem = StatusRelatorio.FALHOU, mensagem


repositorio = RepositorioDeRelatorios()
