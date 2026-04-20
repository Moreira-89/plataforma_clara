import asyncio
import logging

import reflex as rx

from plataforma_clara.services.relatorio_ia_service import (
    gerar_relatorio_consolidado_investidor,
)
from plataforma_clara.states.autenticacao_state import AutenticacaoState

logger = logging.getLogger(__name__)


class AssistenteIAState(rx.State):
    """Estado do fluxo Selecionar -> Gerar -> Download do relatório consolidado."""

    state_auto_setters = True

    relatorio_selecionado: str = ""
    is_loading: bool = False
    mensagem_para_usuario: str = ""

    def set_relatorio_selecionado(self, valor: str) -> None:
        self.relatorio_selecionado = valor

    @rx.var
    def opcoes_relatorio(self) -> list[str]:
        return ["Relatório Consolidado (todos os blocos)"]

    @rx.event
    async def gerar_e_baixar_relatorio(self):
        """Gera o PDF consolidado via ChatGroq e dispara rx.download."""
        self.mensagem_para_usuario = ""

        if not self.relatorio_selecionado:
            self.mensagem_para_usuario = "Selecione o tipo de relatório antes de gerar."
            return

        auth_state = await self.get_state(AutenticacaoState)
        documento = (auth_state.documento_usuario_logado or "").strip()
        if not documento:
            self.mensagem_para_usuario = "Sessão expirada. Faça login novamente."
            yield rx.redirect("/login-usuario")
            return

        self.is_loading = True
        yield

        try:
            pdf_bytes, nome_arquivo = await asyncio.to_thread(
                gerar_relatorio_consolidado_investidor, documento
            )
            self.mensagem_para_usuario = "Relatório gerado com sucesso."
            yield rx.download(data=pdf_bytes, filename=nome_arquivo)
        except ValueError as exc:
            self.mensagem_para_usuario = str(exc)
        except Exception:
            logger.exception("Erro ao gerar relatório consolidado de investimentos.")
            self.mensagem_para_usuario = (
                "Não foi possível gerar o relatório agora. Tente novamente em instantes."
            )
        finally:
            self.is_loading = False
            yield
