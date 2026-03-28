import reflex as rx
from plataforma_clara.model.schemas import tb_usuario
import bcrypt


class AutenticacaoState(rx.State):
    email_usuario: str = ""
    senha_hash_usuario: str = ""
    mensagem_para_usuario: str = ""


    def fazer_login(self):
        
        with rx.session() as session:
            usuario = session.query(tb_usuario).filter_by(email_usuario=self.email_usuario).first()

            if usuario and bcrypt.checkpw(self.senha_hash_usuario.encode('utf-8'), usuario.senha_hash_usuario.encode('utf-8')):
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
            else:
                self.mensagem_para_usuario = "Credenciais inválidas"
                self.email_usuario = ""
                self.senha_hash_usuario = ""
                return