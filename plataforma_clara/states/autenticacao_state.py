"""
Estado de autenticação da Plataforma Clara.

Gerencia o fluxo completo de login e logout: validação de credenciais com bcrypt,
normalização do documento do usuário logado e redirecionamento por perfil.
"""

import asyncio
import logging
import re

import bcrypt
import reflex as rx

from plataforma_clara.model.schemas import tb_usuario

# -----------------------------------------------------------------------------
# INICIALIZAÇÃO
# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# ESTADO DE AUTENTICAÇÃO
# -----------------------------------------------------------------------------


class AutenticacaoState(rx.State):
    """
    Estado responsável pelo fluxo de login e logout.

    Mantém as credenciais digitadas pelo usuário durante o preenchimento
    do formulário e o documento normalizado após login bem-sucedido.
    """

    state_auto_setters = True

    email_usuario: str = ""
    senha_hash_usuario: str = ""
    mensagem_para_usuario: str = ""
    # Armazena apenas dígitos do CPF/CNPJ após login; usado em filtros SQL e BigQuery.
    documento_usuario_logado: str = ""

    # --- Setters manuais (necessários para campos sensíveis não expostos via auto_setter) ---

    def set_email_usuario(self, valor: str) -> None:
        self.email_usuario = valor

    def set_senha_hash_usuario(self, valor: str) -> None:
        self.senha_hash_usuario = valor

    # -----------------------------------------------------------------------------
    # MÉTODOS AUXILIARES INTERNOS
    # -----------------------------------------------------------------------------

    def _limpar_formulario(self) -> None:
        """Reseta apenas os campos do formulário de login (preserva documento_usuario_logado)."""
        self.email_usuario = ""
        self.senha_hash_usuario = ""
        self.mensagem_para_usuario = ""

    # -----------------------------------------------------------------------------
    # EVENTOS PÚBLICOS
    # -----------------------------------------------------------------------------

    @rx.event
    async def fazer_login(self):
        """
        Valida as credenciais do usuário e redireciona conforme o perfil.

        COMO FUNCIONA:
            1. Normalização do E-mail — Strip e lowercase para comparação uniforme.
            2. Validação de Presença — Garante que ambos os campos estejam preenchidos.
            3. Consulta ao Banco (em Thread) — Busca o usuário pelo e-mail e verifica
               o hash bcrypt da senha. Executado em asyncio.to_thread para não bloquear
               o event loop do Reflex (bcrypt é CPU-bound e relativamente lento).
            4. Tratamento de Falha — Mensagem de erro genérica e limpeza dos campos.
            5. Redirecionamento por Perfil — Redireciona para o dashboard correspondente
               ao tipo_usuario ('gestora' ou 'investidor').
        """
        # --- 1. NORMALIZAÇÃO DO E-MAIL ---
        email_normalizado = (self.email_usuario or "").strip().lower()
        senha_digitada = self.senha_hash_usuario or ""

        # --- 2. VALIDAÇÃO DE PRESENÇA ---
        if not email_normalizado or not senha_digitada:
            self.mensagem_para_usuario = "Preencha e-mail e senha para continuar."
            return

        # --- 3. CONSULTA AO BANCO (EM THREAD) ---
        def _validar_credenciais():
            """Executado em thread isolada — bcrypt.checkpw é bloqueante e CPU-bound."""
            with rx.session() as session:
                usuario = session.query(tb_usuario).filter_by(email_usuario=email_normalizado).first()

                if usuario:
                    try:
                        senha_correta = bcrypt.checkpw(
                            senha_digitada.encode("utf-8"),
                            usuario.senha_hash_usuario.encode("utf-8"),
                        )
                        if senha_correta:
                            return {
                                "tipo_usuario": usuario.tipo_usuario,
                                "identificador_usuario": usuario.identificador_usuario,
                            }
                    except (TypeError, ValueError):
                        logger.warning("Hash inválido para e-mail: %s", email_normalizado)
                return None

        dados_usuario = await asyncio.to_thread(_validar_credenciais)

        # --- 4. TRATAMENTO DE FALHA ---
        if not dados_usuario:
            logger.info("Tentativa de login falhou para: %s", email_normalizado)
            self.mensagem_para_usuario = "Credenciais inválidas"
            self.email_usuario = ""
            self.senha_hash_usuario = ""
            return

        logger.info(
            "Login bem-sucedido: %s (tipo: %s)", email_normalizado, dados_usuario["tipo_usuario"]
        )

        # O documento é normalizado (somente dígitos) para uso em filtros SQL e BigQuery.
        doc_limpo = re.sub(r"[^0-9]", "", dados_usuario["identificador_usuario"])
        self.documento_usuario_logado = doc_limpo

        # --- 5. REDIRECIONAMENTO POR PERFIL ---
        destino = {
            "investidor": "/dashboard-investidor",
            "gestora": "/dashboard-gestora",
        }.get(dados_usuario["tipo_usuario"])

        if destino:
            self._limpar_formulario()
            return rx.redirect(destino)

        self.mensagem_para_usuario = "Tipo de usuário não reconhecido."

    @rx.event
    def fazer_logout(self):
        """
        Encerra a sessão do usuário e redireciona para a página inicial.

        COMO FUNCIONA:
            1. Limpeza do Documento — Remove o identificador da sessão ativa.
            2. Limpeza do Formulário — Reseta campos de e-mail, senha e mensagem.
            3. Redirecionamento — Envia o usuário para a landing page ('/').
        """
        # --- 1. LIMPEZA DO DOCUMENTO ---
        self.documento_usuario_logado = ""
        # --- 2. LIMPEZA DO FORMULÁRIO ---
        self._limpar_formulario()
        # --- 3. REDIRECIONAMENTO ---
        return rx.redirect("/")
