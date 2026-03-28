import reflex as rx 
from plataforma_clara.states.cadastro_usuario_state import CadastroUsuarioState

def formulario_cadastro(tipo_pagina: str) -> rx.Component:
    return rx.vstack(
        rx.heading(f"Cadastro de {tipo_pagina}", size="lg"),#type: ignore
        rx.input(
            placeholder="Insira seu nome",
            value=CadastroUsuarioState.nome_usuario,
            on_change=CadastroUsuarioState.set_nome_usuario#type: ignore
        ),
        rx.input(
            placeholder="Insira seu e-mail",
            value=CadastroUsuarioState.email_usuario,
            on_change=CadastroUsuarioState.set_email_usuario#type: ignore
        ),
        rx.input(
            placeholder="Insira seu CNPJ ou CPF",
            value=CadastroUsuarioState.identificador_usuario,
            on_change=CadastroUsuarioState.set_identificador_usuario#type: ignore
    ),
    rx.input(
            placeholder="Crie uma senha",
            value=CadastroUsuarioState.senha_hash_usuario,
            type="password",
            on_change=CadastroUsuarioState.set_senha_hash_usuario#type: ignore
    ),
    rx.button(
        "Cadastrar",
        on_click=CadastroUsuarioState.identificar_tipo_usuario(tipo_pagina=f"{tipo_pagina}")#type: ignore
    ),
    rx.text(CadastroUsuarioState.mensagem_para_usuario)
)

formulario_cadastro_gestora = formulario_cadastro(tipo_pagina="gestora")
formulario_cadastro_investidor = formulario_cadastro(tipo_pagina="investidor")