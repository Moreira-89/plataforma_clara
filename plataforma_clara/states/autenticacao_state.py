import logging

import bcrypt
import reflex as rx

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
    def fazer_login(self):
        """Valida credenciais do usuário e redireciona para o dashboard correto."""
        # Normaliza valores vindos do formulário para evitar falhas por espaços acidentais.
        email_normalizado = (self.email_usuario or "").strip().lower()
        senha_digitada = self.senha_hash_usuario or ""

        if not email_normalizado or not senha_digitada:
            self.mensagem_para_usuario = "Preencha e-mail e senha para continuar."
            return

        with rx.session() as session:
            usuario = (
                session.query(tb_usuario)
                .filter_by(email_usuario=email_normalizado)
                .first()
            )

            senha_valida = False
            if usuario:
                try:
                    senha_valida = bcrypt.checkpw(
                        senha_digitada.encode("utf-8"),
                        usuario.senha_hash_usuario.encode("utf-8"),
                    )
                except (TypeError, ValueError):
                    # Hash inválido no banco: evita erro 500 e informa o usuário.
                    logger.warning(
                        "Hash de senha inválido no banco para email: %s",
                        email_normalizado,
                    )
                    senha_valida = False

            if not (usuario and senha_valida):
                logger.info("Tentativa de login falhou para: %s", email_normalizado)
                self.mensagem_para_usuario = "Credenciais inválidas"
                self.email_usuario = ""
                self.senha_hash_usuario = ""
                return

            # Login bem-sucedido — salva o documento ANTES de limpar o formulário
            logger.info("Login bem-sucedido para: %s (tipo: %s)", email_normalizado, usuario.tipo_usuario)
            self.documento_usuario_logado = usuario.identificador_usuario

            destino = {
                "investidor": "/dashboard-investidor",
                "gestora": "/dashboard-gestora",
            }.get(usuario.tipo_usuario)

            if destino:
                self._limpar_formulario()
                return rx.redirect(destino)

            # Tipo inesperado não pode passar silenciosamente sem direcionamento.
            self.mensagem_para_usuario = "Tipo de usuário não reconhecido."

    @rx.event
    def fazer_logout(self):
        """Encerra a sessão do usuário e redireciona para a home."""
        self.documento_usuario_logado = ""
        self._limpar_formulario()
        return rx.redirect("/")
