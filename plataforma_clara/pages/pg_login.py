import reflex as rx
from plataforma_clara.states.autenticacao_state import AutenticacaoState

def formulario_login(): 
    return rx.vstack(
        rx.heading("Login", size="1"),#type: ignore
        rx.input(
            placeholder="Insira seu e-mail",
            value=AutenticacaoState.email_usuario,
            on_change=AutenticacaoState.set_email_usuario#type: ignore
        ),
        rx.input(
            placeholder="Insira sua senha",
            value=AutenticacaoState.senha_hash_usuario,
            type="password",
            on_change=AutenticacaoState.set_senha_hash_usuario#type: ignore
        ),
        rx.button(
            "Entrar",
            on_click=AutenticacaoState.fazer_login#type: ignore
        ),
        rx.text(AutenticacaoState.mensagem_para_usuario)
    )