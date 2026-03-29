import reflex as rx

def home_page():
    return rx.center(
        rx.vstack(
            rx.heading("Bem-vindo à Plataforma Clara!", size="1"),
            rx.text("Acesse o menu para navegar pelas funcionalidades."),
            spacing="4",
        )
    )