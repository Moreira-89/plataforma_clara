import reflex as rx
from plataforma_clara.model.schemas import tb_usuario
import bcrypt


class AutenticacaoState(rx.State):
    email_usuario: str = ""
    senha_hash_usuario: str = ""
    mensagem_para_usuario: str = ""


    def fazer_login(self):
        # Normaliza valores vindos do formulário para evitar falhas por espaços acidentais.
        email_normalizado = (self.email_usuario or "").strip().lower()
        senha_digitada = self.senha_hash_usuario or ""

        if not email_normalizado or not senha_digitada:
            self.mensagem_para_usuario = "Preencha e-mail e senha para continuar."
            return

        with rx.session() as session:
            usuario = session.query(tb_usuario).filter_by(email_usuario=email_normalizado).first()

            senha_valida = False
            if usuario:
                try:
                    senha_valida = bcrypt.checkpw(
                        senha_digitada.encode("utf-8"),
                        usuario.senha_hash_usuario.encode("utf-8"),
                    )
                except (TypeError, ValueError):
                    # Hash inválido no banco: evita erro 500 e informa o usuário.
                    senha_valida = False

            if usuario and senha_valida:
                self.mensagem_para_usuario = "Login bem-sucedido!"

                if usuario.tipo_usuario == "investidor":
                    self.email_usuario = ""
                    self.senha_hash_usuario = ""
                    self.mensagem_para_usuario = ""
                    return rx.redirect("/dashboard-investidor")
                elif usuario.tipo_usuario == "gestora":
                    self.email_usuario = ""
                    self.senha_hash_usuario = ""
                    self.mensagem_para_usuario = ""
                    return rx.redirect("/dashboard-gestora")
                # Tipo inesperado não pode passar silenciosamente sem direcionamento.
                self.mensagem_para_usuario = "Tipo de usuário não reconhecido."
            else:
                self.mensagem_para_usuario = "Credenciais inválidas"
                self.email_usuario = ""
                self.senha_hash_usuario = ""
                return
