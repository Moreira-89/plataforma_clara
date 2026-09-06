"""
Serviço de autenticação e cadastro de usuários.

Reúne o que estava dentro de `AutenticacaoState` e `CadastroUsuarioState`. Os
states continuam existindo, mas agora só cuidam da tela: ler campo, exibir
mensagem, redirecionar. Toda a regra — normalizar, validar, conferir hash, gravar —
está aqui, e é o que a Fase 2 vai expor como `POST /auth/login` e `POST /auth/register`.

Este módulo e `domain/seguranca.py` são os únicos autorizados a lidar com senha.
"""

import logging
from collections.abc import Callable
from contextlib import AbstractContextManager

from sqlmodel import Session

from plataforma_clara.domain import identidade, seguranca
from plataforma_clara.domain.erros import (
    DadosIncompletosError,
    DocumentoInvalidoError,
    EmailJaCadastradoError,
)
from plataforma_clara.domain.models import Usuario
from plataforma_clara.domain.schemas import UsuarioAutenticado, UsuarioCriacao
from plataforma_clara.infra.db import sessao as sessao_padrao
from plataforma_clara.infra.repositorios.usuario import UsuarioRepositorio

logger = logging.getLogger(__name__)

FabricaDeSessao = Callable[[], AbstractContextManager[Session]]

# Perfis de acesso aceitos no cadastro.
TIPOS_DE_USUARIO = ("gestora", "investidor")


def autenticar(
    email: str,
    senha: str,
    *,
    sessao_factory: FabricaDeSessao = sessao_padrao,
) -> UsuarioAutenticado | None:
    """
    Valida as credenciais de um usuário.

    COMO FUNCIONA:
        1. Normalização — E-mail em minúsculas e sem espaços, como no cadastro.
        2. Busca — Um e-mail inexistente devolve None, sem revelar isso ao chamador
           de forma distinta de senha errada.
        3. Conferência do hash — bcrypt, em `domain/seguranca.py`.
        4. Montagem da identidade — Devolve o perfil e o documento já normalizado,
           que é a chave usada para filtrar os aportes do investidor.

    Esta função é CPU-bound (bcrypt é lento de propósito): chame-a dentro de
    `asyncio.to_thread` a partir de código assíncrono.

    Args:
        email (str): E-mail digitado na tela de login.
        senha (str): Senha em texto plano.
        sessao_factory (FabricaDeSessao): Fábrica de sessão de banco.

    Returns:
        UsuarioAutenticado | None: A identidade, ou None se as credenciais falharem.
    """
    # --- 1. NORMALIZAÇÃO ---
    email_normalizado = identidade.normalizar_email(email)
    if not email_normalizado or not senha:
        return None

    with sessao_factory() as sessao:
        # --- 2. BUSCA ---
        usuario = UsuarioRepositorio(sessao).buscar_por_email(email_normalizado)
        if usuario is None:
            logger.info("Tentativa de login para e-mail não cadastrado.")
            return None

        # --- 3. CONFERÊNCIA DO HASH ---
        if not seguranca.senha_confere(senha, usuario.senha_hash_usuario):
            logger.info("Tentativa de login falhou para: %s", email_normalizado)
            return None

        # --- 4. MONTAGEM DA IDENTIDADE ---
        logger.info("Login bem-sucedido: %s (tipo: %s)", email_normalizado, usuario.tipo_usuario)
        return UsuarioAutenticado(
            tipo_usuario=usuario.tipo_usuario,
            nome_usuario=usuario.nome_usuario,
            documento=identidade.normalizar_documento(usuario.identificador_usuario),
        )


def registrar_usuario(
    dados: UsuarioCriacao,
    *,
    sessao_factory: FabricaDeSessao = sessao_padrao,
) -> UsuarioAutenticado:
    """
    Valida e cadastra um novo usuário.

    COMO FUNCIONA:
        1. Validação do perfil — Só 'gestora' e 'investidor' são aceitos.
        2. Validação de presença e de formato de e-mail.
        3. Validação do documento — Estrutural (tamanho e dígitos); o CPF/CNPJ é
           gravado já normalizado, porque é a chave de ligação com os aportes.
        4. Verificação de duplicidade — Mensagem clara em vez de erro de constraint.
        5. Hash e gravação — A senha em texto plano não sai desta função.

    Args:
        dados (UsuarioCriacao): Dados do formulário de cadastro.
        sessao_factory (FabricaDeSessao): Fábrica de sessão de banco.

    Returns:
        UsuarioAutenticado: A identidade do usuário recém-criado.

    Raises:
        DadosIncompletosError: Campo obrigatório ausente, perfil ou e-mail inválido.
        DocumentoInvalidoError: CPF/CNPJ fora do padrão estrutural.
        EmailJaCadastradoError: Já existe usuário com esse e-mail.
    """
    # --- 1. VALIDAÇÃO DO PERFIL ---
    if dados.tipo_usuario not in TIPOS_DE_USUARIO:
        raise DadosIncompletosError("Tipo de usuário inválido")

    # --- 2. PRESENÇA E FORMATO ---
    email = identidade.normalizar_email(dados.email_usuario)
    nome = (dados.nome_usuario or "").strip()
    if not all((nome, email, dados.identificador_usuario, dados.senha)):
        raise DadosIncompletosError("Preencha todos os campos obrigatórios.")

    if not identidade.email_tem_formato_valido(email):
        raise DadosIncompletosError("Formato de e-mail inválido.")

    # --- 3. VALIDAÇÃO DO DOCUMENTO ---
    tipo_documento, documento_limpo = identidade.identificar_documento(dados.identificador_usuario)
    if tipo_documento == identidade.DOCUMENTO_INVALIDO:
        raise DocumentoInvalidoError("Documento inválido. Verifique os números digitados.")

    with sessao_factory() as sessao:
        repositorio = UsuarioRepositorio(sessao)

        # --- 4. DUPLICIDADE ---
        if repositorio.email_ja_cadastrado(email):
            logger.warning("Tentativa de cadastro duplicado: %s", email)
            raise EmailJaCadastradoError("Este e-mail já está cadastrado.")

        # --- 5. HASH E GRAVAÇÃO ---
        usuario = repositorio.criar(
            Usuario(
                tipo_usuario=dados.tipo_usuario,
                nome_usuario=nome,
                email_usuario=email,
                identificador_usuario=documento_limpo,
                senha_hash_usuario=seguranca.gerar_hash_senha(dados.senha),
            )
        )

    return UsuarioAutenticado(
        tipo_usuario=usuario.tipo_usuario,
        nome_usuario=usuario.nome_usuario,
        documento=documento_limpo,
    )
