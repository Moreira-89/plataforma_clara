"""
Estado de cadastro de novos usuários da Plataforma Clara.

Gerencia o fluxo de criação de conta: validação de campos, identificação
de documento (CPF/CNPJ), geração de hash bcrypt e persistência no banco.
"""

import asyncio
import logging
import re

import bcrypt
import reflex as rx

from plataforma_clara.model.schemas import tb_usuario

# -----------------------------------------------------------------------------
# INICIALIZAÇÃO
# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# Regex para validação básica de formato de e-mail.
_EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

# Regras de validação estrutural para CPF (11 dígitos) e CNPJ (14 dígitos).
_REGRAS_DOCUMENTOS: dict[str, dict] = {
    "CPF": {"tamanho": 11, "permite_letras": False},
    "CNPJ": {"tamanho": 14, "permite_letras": False},
}


# -----------------------------------------------------------------------------
# ESTADO DE CADASTRO
# -----------------------------------------------------------------------------


class CadastroUsuarioState(rx.State):
    """
    Estado responsável por gerenciar o fluxo de cadastro de novos usuários.

    Mantém os dados do formulário, valida-os progressivamente e persiste
    o novo registro no banco após confirmação de unicidade do e-mail.
    """

    state_auto_setters = True

    tipo_usuario: str = ""
    nome_usuario: str = ""
    email_usuario: str = ""
    identificador_usuario: str = ""
    senha_hash_usuario: str = ""
    mensagem_para_usuario: str = ""

    # --- Setters de campos individuais do formulário ---

    def set_tipo_usuario(self, valor: str) -> None:
        self.tipo_usuario = valor

    def set_nome_usuario(self, valor: str) -> None:
        self.nome_usuario = valor

    def set_email_usuario(self, valor: str) -> None:
        self.email_usuario = valor

    def set_identificador_usuario(self, valor: str) -> None:
        self.identificador_usuario = valor

    def set_senha_hash_usuario(self, valor: str) -> None:
        self.senha_hash_usuario = valor

    # -----------------------------------------------------------------------------
    # MÉTODOS AUXILIARES INTERNOS
    # -----------------------------------------------------------------------------

    def _limpar_estado(self) -> None:
        """Reseta todos os campos do formulário para o valor padrão."""
        self.tipo_usuario = ""
        self.nome_usuario = ""
        self.email_usuario = ""
        self.identificador_usuario = ""
        self.senha_hash_usuario = ""
        self.mensagem_para_usuario = ""

    # -----------------------------------------------------------------------------
    # EVENTOS PÚBLICOS
    # -----------------------------------------------------------------------------

    @rx.event
    async def identificar_tipo_usuario(self, tipo_pagina: str):
        """
        Valida os dados do formulário e salva o novo usuário no banco.

        COMO FUNCIONA:
            1. Normalização de Campos — Strip e lowercase nos campos de texto.
            2. Validação de Tipo — Verifica se o perfil recebido é 'gestora' ou 'investidor'.
            3. Validação de Presença — Todos os campos obrigatórios devem estar preenchidos.
            4. Validação de E-mail — Checa o formato com regex básica.
            5. Validação do Documento — Chama _identificar_e_limpar_documento para determinar
               se é CPF (11 dígitos) ou CNPJ (14 dígitos) e rejeitar documentos inválidos.
            6. Persistência em Thread — O hash bcrypt e o INSERT no banco são executados em
               asyncio.to_thread para não bloquear o event loop (bcrypt é CPU-bound).
            7. Redirecionamento — Após cadastro bem-sucedido, vai para a página de login.

        Args:
            tipo_pagina (str): Perfil vindo da URL ou seleção — 'gestora' ou 'investidor'.
        """
        # --- 1. NORMALIZAÇÃO DE CAMPOS ---
        self.mensagem_para_usuario = ""
        self.email_usuario = (self.email_usuario or "").strip().lower()
        self.nome_usuario = (self.nome_usuario or "").strip()

        # --- 2. VALIDAÇÃO DE TIPO ---
        if tipo_pagina not in ("gestora", "investidor"):
            self.mensagem_para_usuario = "Tipo de usuário inválido"
            return
        self.tipo_usuario = tipo_pagina

        # --- 3. VALIDAÇÃO DE PRESENÇA ---
        campos_obrigatorios = [
            self.nome_usuario,
            self.email_usuario,
            self.identificador_usuario,
            self.senha_hash_usuario,
        ]
        if not all(campos_obrigatorios):
            self.mensagem_para_usuario = "Preencha todos os campos obrigatórios."
            return

        # --- 4. VALIDAÇÃO DE E-MAIL ---
        if not _EMAIL_REGEX.match(self.email_usuario):
            self.mensagem_para_usuario = "Formato de e-mail inválido."
            return

        # --- 5. VALIDAÇÃO DO DOCUMENTO ---
        tipo_doc, doc_limpo = self._identificar_e_limpar_documento(self.identificador_usuario)
        if tipo_doc == "INVALIDO":
            self.mensagem_para_usuario = "Documento inválido. Verifique os números digitados."
            return
        self.identificador_usuario = doc_limpo
        self.mensagem_para_usuario = f"{tipo_doc} validado com sucesso!"

        # --- 6. PERSISTÊNCIA EM THREAD ---
        await asyncio.to_thread(self._salvar_informacao_banco)

        if self.mensagem_para_usuario != "Usuário cadastrado com sucesso!":
            return

        # --- 7. REDIRECIONAMENTO ---
        self._limpar_estado()
        return rx.redirect("/login-usuario")

    @staticmethod
    def _identificar_e_limpar_documento(doc_bruto: str) -> tuple[str, str]:
        """
        Remove formatação e valida se a string corresponde a um CPF ou CNPJ.

        COMO FUNCIONA:
            Itera sobre _REGRAS_DOCUMENTOS comparando o tamanho da string limpa
            e a presença exclusiva de dígitos. A validação é apenas estrutural —
            não verifica dígitos verificadores (suficiente para o MVP).

        Args:
            doc_bruto (str): String digitada pelo usuário (com ou sem formatação).

        Returns:
            tuple[str, str]: ('CPF'|'CNPJ'|'INVALIDO', string limpa somente dígitos).
        """
        # Remove tudo que não seja letra ou número antes de classificar.
        doc_limpo = re.sub(r"[^a-zA-Z0-9]", "", str(doc_bruto)).upper()
        tamanho_atual = len(doc_limpo)

        for tipo, regras in _REGRAS_DOCUMENTOS.items():
            if tamanho_atual != regras["tamanho"]:
                continue
            if not regras["permite_letras"] and not doc_limpo.isdigit():
                continue
            return tipo, doc_limpo

        return "INVALIDO", doc_limpo

    @staticmethod
    def _gerar_hash_senha(senha_texto_plano: str) -> str:
        """
        Criptografa a senha usando bcrypt com salt aleatório.

        bcrypt é propositalmente lento (trabalho computacional configurável),
        o que torna ataques de força bruta inviáveis. O gensalt() usa o
        cost factor padrão de 12 rounds.

        Args:
            senha_texto_plano (str): Senha digitada pelo usuário.

        Returns:
            str: Hash decodificado em string para armazenamento no banco.
        """
        senha_bytes = senha_texto_plano.encode("utf-8")
        hash_gerado = bcrypt.hashpw(senha_bytes, bcrypt.gensalt())
        return hash_gerado.decode("utf-8")

    def _salvar_informacao_banco(self) -> None:
        """
        Gera o hash da senha e persiste o novo usuário no banco.

        Verifica antes se o e-mail já existe para evitar duplicatas (a coluna
        tb_usuario.email_usuario tem constraint UNIQUE no banco, mas a verificação
        prévia dá uma mensagem de erro mais amigável do que uma exceção de DB).
        """
        senha_hash = self._gerar_hash_senha(self.senha_hash_usuario)

        try:
            with rx.session() as session:
                usuario_existente = (
                    session.query(tb_usuario)
                    .filter_by(email_usuario=self.email_usuario)
                    .first()
                )
                if usuario_existente:
                    self.mensagem_para_usuario = "Este e-mail já está cadastrado."
                    logger.warning("Tentativa de cadastro duplicado: %s", self.email_usuario)
                    return

                novo_usuario = tb_usuario(
                    tipo_usuario=self.tipo_usuario,
                    nome_usuario=self.nome_usuario,
                    email_usuario=self.email_usuario,
                    identificador_usuario=self.identificador_usuario,
                    senha_hash_usuario=senha_hash,
                )
                session.add(novo_usuario)
                session.commit()

        except Exception:
            logger.exception("Falha ao salvar usuário no banco de dados.")
            self.mensagem_para_usuario = "Não foi possível concluir o cadastro. Tente novamente."
            return

        logger.info("Novo usuário cadastrado: %s (%s)", self.email_usuario, self.tipo_usuario)
        self.mensagem_para_usuario = "Usuário cadastrado com sucesso!"
