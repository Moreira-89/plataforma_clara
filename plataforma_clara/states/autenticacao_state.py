"""
Estado de autenticação da Plataforma Clara.

Depois da extração do domínio, este state só faz o que é de tela: guardar o que
foi digitado, exibir mensagem e redirecionar. A validação de credenciais vive em
`services/autenticacao_service.py` e o hash em `domain/seguranca.py`.

O documento do usuário logado continua sendo guardado aqui, em memória do servidor,
sem token — é a D1 do roadmap, e é a Fase 2 que a resolve com JWT.
"""

import asyncio
import logging

import reflex as rx

from plataforma_clara.services.autenticacao_service import autenticar

# -----------------------------------------------------------------------------
# INICIALIZAÇÃO
# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# Para onde cada perfil vai depois do login.
_DESTINO_POR_PERFIL = {
    "investidor": "/dashboard-investidor",
    "gestora": "/dashboard-gestora",
}


# -----------------------------------------------------------------------------
# ESTADO DE AUTENTICAÇÃO
# -----------------------------------------------------------------------------


class AutenticacaoState(rx.State):
    """
    Estado responsável pelo fluxo de login e logout.

    Mantém as credenciais digitadas durante o preenchimento do formulário e o
    documento normalizado após o login bem-sucedido.
    """

    state_auto_setters = True

    email_usuario: str = ""
    senha_hash_usuario: str = ""
    mensagem_para_usuario: str = ""
    # Armazena apenas dígitos do CPF/CNPJ após login; usado em filtros SQL e BigQuery.
    documento_usuario_logado: str = ""

    # --- Setters manuais (necessários para campos sensíveis não expostos via auto_setter) ---

    def set_email_usuario(self, valor: str) -> None:
        self.email_usuario = valor

    def set_senha_hash_usuario(self, valor: str) -> None:
        self.senha_hash_usuario = valor

    # -----------------------------------------------------------------------------
    # MÉTODOS AUXILIARES INTERNOS
    # -----------------------------------------------------------------------------

    def _limpar_formulario(self) -> None:
        """Reseta apenas os campos do formulário (preserva documento_usuario_logado)."""
        self.email_usuario = ""
        self.senha_hash_usuario = ""
        self.mensagem_para_usuario = ""

    # -----------------------------------------------------------------------------
    # EVENTOS PÚBLICOS
    # -----------------------------------------------------------------------------

    @rx.event
    async def fazer_login(self):
        """
        Valida as credenciais do usuário e redireciona conforme o perfil.

        COMO FUNCIONA:
            1. Validação de Presença — Campos vazios recebem uma mensagem própria,
               diferente de "credenciais inválidas".
            2. Autenticação em Thread — `autenticar` faz I/O de banco e roda bcrypt,
               que é CPU-bound; `asyncio.to_thread` evita travar o event loop.
            3. Tratamento de Falha — Mensagem genérica, sem revelar se o problema
               foi o e-mail ou a senha, e limpeza dos campos.
            4. Redirecionamento por Perfil — Guarda o documento normalizado e leva
               ao dashboard correspondente.
        """
        # --- 1. VALIDAÇÃO DE PRESENÇA ---
        if not (self.email_usuario or "").strip() or not self.senha_hash_usuario:
            self.mensagem_para_usuario = "Preencha e-mail e senha para continuar."
            return

        # --- 2. AUTENTICAÇÃO EM THREAD ---
        usuario = await asyncio.to_thread(
            autenticar, self.email_usuario, self.senha_hash_usuario
        )

        # --- 3. TRATAMENTO DE FALHA ---
        if usuario is None:
            self.mensagem_para_usuario = "Credenciais inválidas"
            self.email_usuario = ""
            self.senha_hash_usuario = ""
            return

        # --- 4. REDIRECIONAMENTO POR PERFIL ---
        self.documento_usuario_logado = usuario.documento

        destino = _DESTINO_POR_PERFIL.get(usuario.tipo_usuario)
        if destino:
            self._limpar_formulario()
            return rx.redirect(destino)

        self.mensagem_para_usuario = "Tipo de usuário não reconhecido."

    @rx.event
    def fazer_logout(self):
        """
        Encerra a sessão do usuário e redireciona para a página inicial.

        COMO FUNCIONA:
            1. Limpeza do Documento — Remove o identificador da sessão ativa.
            2. Limpeza do Formulário — Reseta campos de e-mail, senha e mensagem.
            3. Redirecionamento — Envia o usuário para a landing page ('/').
        """
        # --- 1. LIMPEZA DO DOCUMENTO ---
        self.documento_usuario_logado = ""
        # --- 2. LIMPEZA DO FORMULÁRIO ---
        self._limpar_formulario()
        # --- 3. REDIRECIONAMENTO ---
        return rx.redirect("/")
