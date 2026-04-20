import reflex as rx 
from plataforma_clara.states.cadastro_usuario_state import CadastroUsuarioState

def formulario_cadastro() -> rx.Component:
    """Página de Cadastro da Plataforma Clara."""
    
    return rx.hstack(
        rx.vstack(
            rx.vstack(
                rx.heading("Clara", size="9", weight="bold", color="white", mb="2"),
                rx.text(
                    "Junte-se ao ecossistema de FIDCs", 
                    size="5", 
                    color="#94A3B8",
                    weight="medium"
                ),
                rx.text(
                    "Crie sua conta para acessar relatórios detalhados, alocações de capital e o Ranking de Reputação Nuclea.", 
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
                rx.heading("Criar Conta", size="7", weight="bold", color="#0F172A"),
                rx.text("Preencha os dados abaixo para se registrar.", size="3", color="#64748B", mb="6"),

                rx.vstack(
                    rx.vstack(
                        rx.text("Perfil de Acesso", size="2", weight="bold", color="#334155"),
                        rx.select(
                            ["investidor", "gestora"],
                            placeholder="Selecione seu perfil",
                            width="100%",
                            size="3",
                            on_change=CadastroUsuarioState.set_tipo_usuario,
                        ),
                        width="100%",
                        align_items="flex-start",
                        spacing="1",
                    ),

                    rx.vstack(
                        rx.text("Nome Completo / Razão Social", size="2", weight="bold", color="#334155"),
                        rx.input(
                            placeholder="Digite seu nome ou nome da empresa",
                            width="100%",
                            size="3",
                            variant="surface",
                            color_scheme="gray",
                            on_change=CadastroUsuarioState.set_nome_usuario,
                        ),
                        width="100%",
                        align_items="flex-start",
                        spacing="1",
                    ),

                    rx.flex(
                        rx.vstack(
                            rx.text("CPF / CNPJ", size="2", weight="bold", color="#334155"),
                            rx.input(
                                placeholder="Apenas números",
                                width="100%",
                                size="3",
                                variant="surface",
                                color_scheme="gray",
                                on_change=CadastroUsuarioState.set_identificador_usuario,
                            ),
                            width="100%",
                            align_items="flex-start",
                            spacing="1",
                        ),
                        rx.vstack(
                            rx.text("E-mail Pessoal / Corporativo", size="2", weight="bold", color="#334155"),
                            rx.input(
                                placeholder="seu@email.com",
                                type="email",
                                width="100%",
                                size="3",
                                variant="surface",
                                color_scheme="gray",
                                on_change=CadastroUsuarioState.set_email_usuario,
                            ),
                            width="100%",
                            align_items="flex-start",
                            spacing="1",
                        ),
                        direction=rx.breakpoints(initial="column", md="row"), 
                        spacing="4",
                        width="100%",
                    ),

                    rx.vstack(
                        rx.text("Senha", size="2", weight="bold", color="#334155"),
                        rx.input(
                            placeholder="••••••••",
                            type="password",
                            width="100%",
                            size="3",
                            variant="surface",
                            color_scheme="gray",
                            on_change=CadastroUsuarioState.set_senha_hash_usuario,
                        ),
                        width="100%",
                        align_items="flex-start",
                        spacing="1",
                    ),
                    
                    width="100%",
                    spacing="4",
                    mt="2"
                ),

                rx.cond(
                    CadastroUsuarioState.mensagem_para_usuario != "",
                    rx.callout(
                        CadastroUsuarioState.mensagem_para_usuario,
                        icon="info",
                        color_scheme="blue",
                        width="100%",
                        mt="4"
                    ),
                ),

                rx.button(
                    "Criar Conta",
                    width="100%",
                    size="3",
                    bg="#2563EB",
                    color="white",
                    weight="bold",
                    mt="6",
                    _hover={"bg": "#1D4ED8"},
                    on_click=lambda: CadastroUsuarioState.identificar_tipo_usuario(CadastroUsuarioState.tipo_usuario), 
                ),

                rx.text(
                    "Já possui uma conta? ",
                    rx.link("Faça login aqui", href="/login-usuario", color="#2563EB", weight="bold"),
                    size="2",
                    mt="6",
                    color="#475569",
                    text_align="center",
                    width="100%"
                ),

                width=["100%", "90%", "85%", "75%"],
                max_width="550px",
                align_items="flex-start",
                padding="2rem",
                bg="white",
                border_radius="12px",
                box_shadow="0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)",
            ),
            width=["100%", "100%", "50%"],
            height="100vh",
            bg="#F8FAFC",
            padding_y="2rem", 
        ),
        
        width="100vw",
        height="100vh",
        margin="0",
        spacing="0",
    )
