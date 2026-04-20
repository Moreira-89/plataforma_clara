import reflex as rx
from plataforma_clara.states.autenticacao_state import AutenticacaoState


def formulario_login() -> rx.Component:
    """Página de Login da Plataforma Clara."""
    
    return rx.hstack(
        # ==========================================
        # LADO ESQUERDO: Branding e Proposta de Valor
        # ==========================================
        rx.vstack(
            rx.vstack(
                rx.heading("Clara", size="9", weight="bold", color="white", mb="2"),
                rx.text(
                    "Transparência e Inteligência em FIDCs", 
                    size="5", 
                    color="#94A3B8", # Slate 400
                    weight="medium"
                ),
                rx.text(
                    "Conectando Gestoras e Investidores com segurança, rastreabilidade e análise de risco preditiva.", 
                    size="3", 
                    color="#64748B", # Slate 500
                    mt="4",
                    max_width="400px",
                ),
                align_items="flex-start",
                justify_content="center",
                height="100%",
                padding_left="15%",
            ),
            # Classes de responsividade: Oculto em mobile, visível em telas médias/grandes
            display=["none", "none", "flex"], 
            width=["0%", "0%", "50%"],
            height="100vh",
            bg="#0F172A", # Fundo escuro (Slate 900) corporativo
            background_image="radial-gradient(circle at 20% 50%, #1E293B 0%, #0F172A 50%)", # Efeito de luz sutil
        ),

        # ==========================================
        # LADO DIREITO: Formulário de Login
        # ==========================================
        rx.center(
            rx.vstack(
                # Cabeçalho do Form
                rx.heading("Bem-vindo de volta", size="7", weight="bold", color="#0F172A"),
                rx.text("Insira suas credenciais para acessar sua conta.", size="3", color="#64748B", mb="6"),

                # Campo de E-mail
                rx.text("E-mail", size="2", weight="bold", width="100%", text_align="left", color="#334155"),
                rx.input(
                    placeholder="seu@email.com",
                    type="email",
                    width="100%",
                    size="3",
                    border_color="#CBD5E1",
                    # O Reflex gera automaticamente 'set_nome_da_variavel' para variáveis no State
                    on_change=AutenticacaoState.set_email_usuario, 
                ),

                # Campo de Senha
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

                # Controles Extras (Lembrar / Esqueci a senha)
                rx.hstack(
                    rx.link("Esqueceu a senha?", href="#", size="2", color="#2563EB", weight="medium"),
                    justify_content="flex_end",
                    width="100%",
                    mt="4",
                    mb="6",
                ),

                # Botão de Login
                rx.button(
                    "Entrar na Plataforma",
                    width="100%",
                    size="3",
                    bg="#2563EB", # Blue 600
                    color="white",
                    weight="bold",
                    _hover={"bg": "#1D4ED8"}, # Blue 700 no hover
                    on_click=AutenticacaoState.fazer_login, 
                ),

                # Link de Cadastro
                rx.text(
                    "Não possui uma conta? ",
                    rx.link("Solicite acesso aqui", href="/cadastro", color="#2563EB", weight="bold"),
                    size="2",
                    mt="8",
                    color="#475569",
                    text_align="center",
                    width="100%"
                ),

                # Estilização do Container do Form
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
            bg="#F8FAFC", # Slate 50 (cinza clarinho para o fundo do form)
        ),
        
        # Configurações do container principal (hstack)
        width="100vw",
        height="100vh",
        margin="0",
        spacing="0",
    )
