import logging

import bcrypt
import reflex as rx
import asyncio
import re

from plataforma_clara.model.schemas import tb_usuario

logger = logging.getLogger(__name__)


class AutenticacaoState(rx.State):
    """Estado responsável pelo fluxo de login/autenticação."""

    state_auto_setters = True

    email_usuario: str = ""
    senha_hash_usuario: str = ""
    mensagem_para_usuario: str = ""
    documento_usuario_logado: str = ""

    def _limpar_formulario(self) -> None:
        """Reseta apenas os campos do formulário de login (preserva dados de sessão)."""
        self.email_usuario = ""
        self.senha_hash_usuario = ""
        self.mensagem_para_usuario = ""

    @rx.event
    async def fazer_login(self):
        """Valida credenciais do usuário assincronamente e redireciona."""
        email_normalizado = (self.email_usuario or "").strip().lower()
        senha_digitada = self.senha_hash_usuario or ""

        if not email_normalizado or not senha_digitada:
            self.mensagem_para_usuario = "Preencha e-mail e senha para continuar."
            return

        def _validar_credenciais():
            """Executado em thread isolada para operações bloqueantes de DB e Bcrypt."""
            with rx.session() as session:
                usuario = session.query(tb_usuario).filter_by(email_usuario=email_normalizado).first()
                
                if usuario:
                    try:
                        if bcrypt.checkpw(senha_digitada.encode("utf-8"), usuario.senha_hash_usuario.encode("utf-8")):
                            return {
                                "tipo_usuario": usuario.tipo_usuario,
                                "identificador_usuario": usuario.identificador_usuario
                            }
                    except (TypeError, ValueError):
                        logger.warning("Hash inválido para email: %s", email_normalizado)
                return None

        dados_usuario = await asyncio.to_thread(_validar_credenciais)

        if not dados_usuario:
            logger.info("Tentativa de login falhou para: %s", email_normalizado)
            self.mensagem_para_usuario = "Credenciais inválidas"
            self.email_usuario = ""
            self.senha_hash_usuario = ""
            return

        logger.info("Login bem-sucedido para: %s (tipo: %s)", email_normalizado, dados_usuario["tipo_usuario"])
        
        # Higienizar o documento de identidade (apenas números)
        doc_limpo = re.sub(r'[^0-9]', '', dados_usuario["identificador_usuario"])
        self.documento_usuario_logado = doc_limpo

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
        """Encerra a sessão do usuário e redireciona para a home."""
        self.documento_usuario_logado = ""
        self._limpar_formulario()
        return rx.redirect("/")
