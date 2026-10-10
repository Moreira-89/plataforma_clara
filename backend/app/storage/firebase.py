"""
Cliente do Firebase Admin: verificação de token e acesso ao Firestore.

COMO FUNCIONA:
    1. `inicializar_firebase` cria o app uma vez, no lifespan, com a mesma credencial
       do BigQuery (ou as credenciais padrão do ambiente).
    2. `verificar_token` valida um ID token e devolve as claims.
    3. `cliente_firestore` devolve o cliente do banco operacional.
    Todas as chamadas são bloqueantes: quem chama de código assíncrono usa
    `asyncio.to_thread`.

Args:
    Nenhum.

Returns:
    Nenhum.

Raises:
    TokenInvalidoError: Token ausente, malformado, expirado ou revogado.
    AutenticacaoIndisponivelError: Falha ao buscar os certificados do Google.
"""

import logging
from typing import Any

import firebase_admin
from firebase_admin import auth, credentials, firestore
from google.cloud.firestore import Client

from app.config.settings import settings
from app.domain.erros import AutenticacaoIndisponivelError, TokenInvalidoError
from app.storage.credenciais import carregar_credenciais

logger = logging.getLogger(__name__)


def inicializar_firebase() -> None:
    """Cria o app do Firebase Admin, se ainda não existir. Não faz chamada de rede."""
    try:
        firebase_admin.get_app()
        return
    except ValueError:
        pass

    credencial = credentials.ApplicationDefault()
    dados = carregar_credenciais()
    if dados:
        try:
            credencial = credentials.Certificate(dados)
        except ValueError as e:
            logger.warning("Credencial do .env inválida para o Firebase: %s. Usando a padrão.", e)

    firebase_admin.initialize_app(credencial, {"projectId": settings.project_id})
    logger.info("Firebase Admin inicializado.")


def verificar_token(token: str) -> dict[str, Any]:
    """
    Verifica um ID token do Firebase.

    Não consulta revogação: o token vale até expirar (1h), sem rede a cada requisição.

    Args:
        token (str): ID token vindo do header Authorization.

    Returns:
        dict[str, Any]: Claims do token (`uid`, `email`, `perfil`, ...).

    Raises:
        TokenInvalidoError: Token inválido ou expirado.
        AutenticacaoIndisponivelError: Falha ao buscar os certificados do Google.
    """
    try:
        return auth.verify_id_token(token)
    except (ValueError, auth.InvalidIdTokenError, auth.ExpiredIdTokenError) as e:
        raise TokenInvalidoError("Token inválido ou expirado.") from e
    except auth.CertificateFetchError as e:
        raise AutenticacaoIndisponivelError("Não foi possível verificar o token.") from e


def cliente_firestore() -> Client:
    """Devolve o cliente do Firestore ligado ao app do Firebase."""
    return firestore.client()
