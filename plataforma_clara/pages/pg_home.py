import reflex as rx

def home_page():
    return rx.center(
        rx.vstack(
            rx.heading("Bem-vindo à Plataforma Clara!", size="1"),
            rx.text("Acesse o menu para navegar pelas funcionalidades."),
            rx.button("Login", on_click=rx.redirect("/login-usuario")),
            rx.button("Cadastre-se", on_click=rx.redirect("/cadastro")),
            spacing="4",
        )
    )