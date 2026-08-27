"""
Estado de cadastro de novos usuários da Plataforma Clara.

Depois da extração do domínio, este state só cuida da tela. As regras — validação
de e-mail e documento, verificação de duplicidade, hash bcrypt e gravação — estão
em `services/autenticacao_service.py`, `domain/identidade.py` e
`domain/seguranca.py`, e traduzem falha em exceção de negócio. Aqui essas exceções
viram o texto que aparece para o usuário.
"""

import asyncio
import logging

import reflex as rx

from plataforma_clara.domain.erros import ErroDeNegocio
from plataforma_clara.domain.schemas import UsuarioCriacao
from plataforma_clara.services.autenticacao_service import registrar_usuario

# -----------------------------------------------------------------------------
# INICIALIZAÇÃO
# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# ESTADO DE CADASTRO
# -----------------------------------------------------------------------------


class CadastroUsuarioState(rx.State):
    """
    Estado responsável pelo formulário de cadastro de novos usuários.

    Mantém os dados digitados e a mensagem de retorno. Nenhuma regra de validação
    vive aqui: o formulário só coleta e exibe.
    """

    state_auto_setters = True

    tipo_usuario: str = ""
    nome_usuario: str = ""
    email_usuario: str = ""
    identificador_usuario: str = ""
    senha_hash_usuario: str = ""
    mensagem_para_usuario: str = ""

    # --- Setters de campos individuais do formulário ---

    def set_tipo_usuario(self, valor: str) -> None:
        self.tipo_usuario = valor

    def set_nome_usuario(self, valor: str) -> None:
        self.nome_usuario = valor

    def set_email_usuario(self, valor: str) -> None:
        self.email_usuario = valor

    def set_identificador_usuario(self, valor: str) -> None:
        self.identificador_usuario = valor

    def set_senha_hash_usuario(self, valor: str) -> None:
        self.senha_hash_usuario = valor

    # -----------------------------------------------------------------------------
    # MÉTODOS AUXILIARES INTERNOS
    # -----------------------------------------------------------------------------

    def _limpar_estado(self) -> None:
        """Reseta todos os campos do formulário para o valor padrão."""
        self.tipo_usuario = ""
        self.nome_usuario = ""
        self.email_usuario = ""
        self.identificador_usuario = ""
        self.senha_hash_usuario = ""
        self.mensagem_para_usuario = ""

    # -----------------------------------------------------------------------------
    # EVENTOS PÚBLICOS
    # -----------------------------------------------------------------------------

    @rx.event
    async def identificar_tipo_usuario(self, tipo_pagina: str):
        """
        Envia o formulário para cadastro e trata o resultado.

        COMO FUNCIONA:
            1. Montagem do Contrato — Os campos da tela viram um `UsuarioCriacao`.
               O perfil chega por parâmetro porque a página o passa a partir do
               seletor do formulário; o serviço recusa qualquer valor fora de
               'gestora' e 'investidor'.
            2. Cadastro em Thread — bcrypt é CPU-bound e o INSERT é I/O; ambos rodam
               fora do event loop.
            3. Erro de Negócio — Mensagem específica, vinda da própria exceção.
            4. Erro Inesperado — Mensagem genérica; o detalhe fica só no log.
            5. Redirecionamento — Cadastro concluído leva à tela de login.

        Args:
            tipo_pagina (str): Perfil escolhido no formulário — 'gestora' ou 'investidor'.
        """
        self.mensagem_para_usuario = ""

        # --- 1. MONTAGEM DO CONTRATO ---
        dados = UsuarioCriacao(
            tipo_usuario=tipo_pagina,
            nome_usuario=self.nome_usuario,
            email_usuario=self.email_usuario,
            identificador_usuario=self.identificador_usuario,
            senha=self.senha_hash_usuario,
        )

        try:
            # --- 2. CADASTRO EM THREAD ---
            await asyncio.to_thread(registrar_usuario, dados)

        # --- 3. ERRO DE NEGÓCIO ---
        except ErroDeNegocio as erro:
            self.mensagem_para_usuario = str(erro)
            return

        # --- 4. ERRO INESPERADO ---
        except Exception:
            logger.exception("Falha ao salvar usuário no banco de dados.")
            self.mensagem_para_usuario = "Não foi possível concluir o cadastro. Tente novamente."
            return

        # --- 5. REDIRECIONAMENTO ---
        self._limpar_estado()
        return rx.redirect("/login-usuario")
