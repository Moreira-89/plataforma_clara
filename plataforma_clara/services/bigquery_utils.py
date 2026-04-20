"""
Utilitário centralizado para gerenciar credenciais e conexões do BigQuery.

Suporta dois modos de configuração:
1. GOOGLE_APPLICATION_CREDENTIALS como string JSON (nova forma)
2. GOOGLE_APPLICATION_CREDENTIALS como caminho para arquivo (forma legada)
"""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

from google.cloud import bigquery
from google.oauth2 import service_account

logger = logging.getLogger(__name__)

_PROJETO_ID = "plataforma-clara"


def _parsear_credenciais_do_env() -> Optional[dict]:
    """
    Tenta obter credenciais do BigQuery da variável de ambiente.
    
    Suporta dois formatos:
    1. JSON string completo (novo formato)
    2. Caminho para arquivo JSON (formato legado)
    
    Returns:
        Dicionário com credenciais ou None se não encontrado
    """
    env_cred = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    
    if not env_cred:
        logger.debug("GOOGLE_APPLICATION_CREDENTIALS não configurada")
        return None
    
    # Tenta primeiro como JSON string
    if env_cred.startswith("{"):
        try:
            credenciais_dict = json.loads(env_cred)
            logger.info("✓ Credenciais do BigQuery carregadas de string JSON no .env")
            return credenciais_dict
        except json.JSONDecodeError as e:
            logger.warning("Falha ao parsear GOOGLE_APPLICATION_CREDENTIALS como JSON: %s", e)
    
    # Tenta como caminho para arquivo
    caminho = Path(env_cred)
    if caminho.is_file():
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                credenciais_dict = json.load(f)
            logger.info("✓ Credenciais do BigQuery carregadas de arquivo: %s", caminho)
            return credenciais_dict
        except (json.JSONDecodeError, IOError) as e:
            logger.warning("Falha ao carregar credenciais de arquivo %s: %s", caminho, e)
    
    return None


def criar_cliente_bigquery(project_id: Optional[str] = None) -> bigquery.Client:
    """
    Cria um cliente BigQuery com as credenciais disponíveis.
    
    Prioridade:
    1. Credenciais do GOOGLE_APPLICATION_CREDENTIALS (string JSON ou arquivo)
    2. Credenciais padrão do ambiente (Application Default Credentials)
    
    Args:
        project_id: ID do projeto GCP. Padrão: plataforma-clara
        
    Returns:
        Cliente BigQuery autenticado
        
    Raises:
        Pode lançar exceções da google.auth se autenticação falhar
    """
    if project_id is None:
        project_id = _PROJETO_ID
    
    # Tenta carregar credenciais da variável de ambiente
    credenciais_dict = _parsear_credenciais_do_env()
    
    if credenciais_dict:
        try:
            credentials = service_account.Credentials.from_service_account_info(credenciais_dict)
            logger.debug("Cliente BigQuery criado com credenciais explícitas")
            return bigquery.Client(project=project_id, credentials=credentials)
        except Exception as e:
            logger.warning("Falha ao usar credenciais do .env: %s. Tentando credenciais padrão...", e)
    
    # Fallback para credenciais padrão do ambiente
    logger.info("Usando credenciais padrão do ambiente (Application Default Credentials)")
    return bigquery.Client(project=project_id)


def salvar_credenciais_em_arquivo_temporario() -> Optional[Path]:
    """
    Se as credenciais estiverem em formato JSON string, salva em um arquivo temporário.
    
    Útil para ferramentas que exigem um arquivo de credenciais.
    
    Returns:
        Caminho para arquivo temporário ou None se não encontrado
    """
    credenciais_dict = _parsear_credenciais_do_env()
    
    if not credenciais_dict:
        return None
    
    try:
        # Cria arquivo temporário
        temp_file = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
            encoding="utf-8"
        )
        json.dump(credenciais_dict, temp_file)
        temp_file.close()
        
        logger.debug("Credenciais salvas em arquivo temporário: %s", temp_file.name)
        return Path(temp_file.name)
    except Exception as e:
        logger.error("Falha ao salvar credenciais em arquivo temporário: %s", e)
        return None


def obter_info_credenciais() -> dict:
    """
    Retorna informações sobre as credenciais configuradas (sem expor dados sensíveis).
    
    Returns:
        Dicionário com informações de diagnóstico
    """
    env_cred = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    credenciais_dict = _parsear_credenciais_do_env()
    
    info = {
        "configurada": bool(env_cred),
        "tipo": None,
        "projeto": None,
        "email_servico": None,
    }
    
    if env_cred.startswith("{"):
        info["tipo"] = "string_json"
    elif Path(env_cred).is_file():
        info["tipo"] = "arquivo"
    
    if credenciais_dict:
        info["projeto"] = credenciais_dict.get("project_id", "desconhecido")
        info["email_servico"] = credenciais_dict.get("client_email", "desconhecido")
    
    return info
