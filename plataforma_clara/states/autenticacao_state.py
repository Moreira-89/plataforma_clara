import reflex as rx

class AutenticacaoState(rx.State):
    email_usuario: str = ""
    senha_hash_usuario: str = ""
    mensagem_para_usuario: str = ""