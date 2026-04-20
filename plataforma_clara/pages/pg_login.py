import reflex as rx
from plataforma_clara.states.autenticacao_state import AutenticacaoState


def formulario_login() -> rx.Component:
    """Página de Login da Plataforma Clara."""
    
    return rx.hstack(
        rx.vstack(
            rx.vstack(
                rx.heading("Clara", size="9", weight="bold", color="white", mb="2"),
                rx.text(
                    "Transparência e Inteligência em FIDCs", 
                    size="5", 
                    color="#94A3B8",
                    weight="medium"
                ),
                rx.text(
                    "Conectando Gestoras e Investidores com segurança, rastreabilidade e análise de risco preditiva.", 
                    size="3", 
                    color="#64748B",
                    mt="4",
                    max_width="400px",
                ),
                align_items="flex-start",
                justify_content="center",
                height="100%",
                padding_left="15%",
            ),
            display=["none", "none", "flex"], 
            width=["0%", "0%", "50%"],
            height="100vh",
            bg="#0F172A",
            background_image="radial-gradient(circle at 20% 50%, #1E293B 0%, #0F172A 50%)",
        ),

        rx.center(
            rx.vstack(
                rx.heading("Bem-vindo de volta", size="7", weight="bold", color="#0F172A"),
                rx.text("Insira suas credenciais para acessar sua conta.", size="3", color="#64748B", mb="6"),

                rx.text("E-mail", size="2", weight="bold", width="100%", text_align="left", color="#334155"),
                rx.input(
                    placeholder="seu@email.com",
                    type="email",
                    width="100%",
                    size="3",
                    border_color="#CBD5E1",
                    on_change=AutenticacaoState.set_email_usuario, 
                ),

                rx.text("Senha", size="2", weight="bold", width="100%", text_align="left", mt="4", color="#334155"),
                rx.input(
                    placeholder="••••••••",
                    type="password",
                    width="100%",
                    size="3",
                    border_color="#CBD5E1",
                    _placeholder={"color": "#64748B"},
                    on_change=AutenticacaoState.set_senha_hash_usuario,
                ),

                rx.cond(
                    AutenticacaoState.mensagem_para_usuario != "",
                    rx.callout(
                        AutenticacaoState.mensagem_para_usuario,
                        icon="info",
                        color_scheme="red",
                        width="100%",
                        mt="4",
                    ),
                ),

                rx.hstack(
                    rx.link("Esqueceu a senha?", href="#", size="2", color="#2563EB", weight="medium"),
                    justify_content="flex_end",
                    width="100%",
                    mt="4",
                    mb="6",
                ),

                rx.button(
                    "Entrar na Plataforma",
                    width="100%",
                    size="3",
                    bg="#2563EB",
                    color="white",
                    weight="bold",
                    _hover={"bg": "#1D4ED8"},
                    on_click=AutenticacaoState.fazer_login, 
                ),

                rx.text(
                    "Não possui uma conta? ",
                    rx.link("Solicite acesso aqui", href="/cadastro", color="#2563EB", weight="bold"),
                    size="2",
                    mt="8",
                    color="#475569",
                    text_align="center",
                    width="100%"
                ),

                width=["100%", "80%", "70%", "60%"],
                max_width="450px",
                align_items="flex-start",
                padding="2rem",
                bg="white",
                border_radius="12px",
                box_shadow="0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)",
            ),
            width=["100%", "100%", "50%"],
            height="100vh",
            bg="#F8FAFC",
        ),
        
        width="100vw",
        height="100vh",
        margin="0",
        spacing="0",
    )
