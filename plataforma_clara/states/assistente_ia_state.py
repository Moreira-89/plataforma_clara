"""
Estado do fluxo de geração de relatório consolidado via IA (Assistente).

Gerencia o ciclo Selecionar → Gerar → Download:
    - Bloqueia o botão durante o processamento (is_loading).
    - Executa o serviço de IA em thread separada para não travar a UI.
    - Dispara rx.download com os bytes do PDF gerado.
"""

import asyncio
import logging

import reflex as rx

from plataforma_clara.services.relatorio_ia_service import (
    gerar_relatorio_consolidado_investidor,
)
from plataforma_clara.states.autenticacao_state import AutenticacaoState

# -----------------------------------------------------------------------------
# INICIALIZAÇÃO
# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# ESTADO DO ASSISTENTE IA
# -----------------------------------------------------------------------------


class AssistenteIAState(rx.State):
    """
    Estado do fluxo Selecionar → Gerar → Download do relatório consolidado.

    `is_loading` é lido diretamente na UI para desabilitar o botão e exibir
    o spinner durante o processamento, evitando cliques duplicados.
    """

    state_auto_setters = True

    relatorio_selecionado: str = ""
    is_loading: bool = False
    mensagem_para_usuario: str = ""

    def set_relatorio_selecionado(self, valor: str) -> None:
        self.relatorio_selecionado = valor

    # -----------------------------------------------------------------------------
    # COMPUTED VAR
    # -----------------------------------------------------------------------------

    @rx.var
    def opcoes_relatorio(self) -> list[str]:
        """Opções disponíveis para seleção de tipo de relatório."""
        return ["Relatório Consolidado (todos os blocos)"]

    # -----------------------------------------------------------------------------
    # EVENTOS PÚBLICOS
    # -----------------------------------------------------------------------------

    @rx.event
    async def gerar_e_baixar_relatorio(self):
        """
        Gera o PDF consolidado via ChatGroq e dispara o download no browser.

        COMO FUNCIONA:
            1. Validação da Seleção — Garante que o tipo de relatório foi selecionado.
            2. Recuperação do Documento — Obtém o documento do investidor logado via
               get_state(AutenticacaoState). Redireciona para login se a sessão expirou.
            3. Ativação do Loading — Define is_loading=True e emite yield para que a
               UI atualize imediatamente (o Reflex não atualiza até o próximo yield).
            4. Geração em Thread — Toda a lógica pesada (BigQuery + Groq + PDF) roda em
               asyncio.to_thread para não bloquear o event loop.
            5. Download — rx.download injeta o arquivo PDF no browser do usuário
               como download automático (via data URI).
            6. Finally — is_loading é desativado mesmo em caso de erro, sempre.

        Raises:
            ValueError: Propagado como mensagem amigável ao usuário (ex: sem aportes).
            Exception: Capturada e exibida como mensagem genérica de erro.
        """
        self.mensagem_para_usuario = ""

        # --- 1. VALIDAÇÃO DA SELEÇÃO ---
        if not self.relatorio_selecionado:
            self.mensagem_para_usuario = "Selecione o tipo de relatório antes de gerar."
            return

        # --- 2. RECUPERAÇÃO DO DOCUMENTO ---
        auth_state = await self.get_state(AutenticacaoState)
        documento = (auth_state.documento_usuario_logado or "").strip()
        if not documento:
            self.mensagem_para_usuario = "Sessão expirada. Faça login novamente."
            yield rx.redirect("/login-usuario")
            return

        # --- 3. ATIVAÇÃO DO LOADING ---
        self.is_loading = True
        yield  # Força o Reflex a enviar o estado atualizado para o frontend antes de continuar

        try:
            # --- 4. GERAÇÃO EM THREAD ---
            # gerar_relatorio_consolidado_investidor é síncrono e CPU-bound
            # (bcrypt + pandas + Groq API + PDF). asyncio.to_thread isola a execução.
            pdf_bytes, nome_arquivo = await asyncio.to_thread(
                gerar_relatorio_consolidado_investidor, documento
            )
            self.mensagem_para_usuario = "Relatório gerado com sucesso."

            # --- 5. DOWNLOAD ---
            yield rx.download(data=pdf_bytes, filename=nome_arquivo)

        except ValueError as exc:
            # Erros de negócio (ex: "Nenhum investimento encontrado") — mensagem direta.
            self.mensagem_para_usuario = str(exc)
        except Exception:
            logger.exception("Erro ao gerar relatório consolidado de investimentos.")
            self.mensagem_para_usuario = (
                "Não foi possível gerar o relatório agora. Tente novamente em instantes."
            )
        finally:
            # --- 6. FINALLY ---
            self.is_loading = False
            yield
