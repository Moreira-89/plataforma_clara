"""
Utilitário centralizado para gerenciar credenciais e conexões com o BigQuery.

Suporta dois modos de configuração da variável GOOGLE_APPLICATION_CREDENTIALS:
    1. String JSON completo (novo formato, ideal para ambientes de nuvem/CI)
    2. Caminho para arquivo .json (formato legado, para desenvolvimento local)
"""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

from google.cloud import bigquery
from google.oauth2 import service_account

# -----------------------------------------------------------------------------
# INICIALIZAÇÃO
# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# ID padrão do projeto GCP utilizado pela plataforma.
_PROJETO_ID = "plataforma-clara"


# -----------------------------------------------------------------------------
# FUNÇÕES INTERNAS (PRIVADAS)
# -----------------------------------------------------------------------------


def _parsear_credenciais_do_env() -> Optional[dict]:
    """
    Tenta obter credenciais do BigQuery da variável de ambiente.

    COMO FUNCIONA:
        1. Leitura da Variável — Obtém o valor de GOOGLE_APPLICATION_CREDENTIALS.
        2. Tentativa JSON — Se o valor começa com '{', tenta parsear como JSON string
           diretamente (ideal para produção/nuvem onde não há sistema de arquivos).
        3. Tentativa de Arquivo — Caso contrário, trata o valor como caminho para
           um arquivo .json no disco (fluxo de desenvolvimento local).
        4. Retorno — Devolve o dict de credenciais ou None se nenhum formato funcionou.

    Returns:
        Optional[dict]: Dicionário com credenciais ou None se não encontrado/inválido.
    """
    # --- 1. LEITURA DA VARIÁVEL ---
    env_cred = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()

    if not env_cred:
        logger.debug("GOOGLE_APPLICATION_CREDENTIALS não configurada.")
        return None

    # --- 2. TENTATIVA JSON ---
    # Se começa com '{', é uma string JSON inline (comum em variáveis de ambiente
    # em containers Docker ou pipelines de CI/CD).
    if env_cred.startswith("{"):
        try:
            credenciais_dict = json.loads(env_cred)
            logger.info("✓ Credenciais do BigQuery carregadas de string JSON no .env")
            return credenciais_dict
        except json.JSONDecodeError as e:
            logger.warning("Falha ao parsear GOOGLE_APPLICATION_CREDENTIALS como JSON: %s", e)

    # --- 3. TENTATIVA DE ARQUIVO ---
    # Trata a string como caminho para um arquivo JSON no disco.
    caminho = Path(env_cred)
    if caminho.is_file():
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                credenciais_dict = json.load(f)
            logger.info("✓ Credenciais do BigQuery carregadas de arquivo: %s", caminho)
            return credenciais_dict
        except (json.JSONDecodeError, IOError) as e:
            logger.warning("Falha ao carregar credenciais de arquivo %s: %s", caminho, e)

    # --- 4. RETORNO NULO ---
    return None


# -----------------------------------------------------------------------------
# FUNÇÕES PÚBLICAS
# -----------------------------------------------------------------------------


def criar_cliente_bigquery(project_id: Optional[str] = None) -> bigquery.Client:
    """
    Cria e retorna um cliente BigQuery autenticado.

    COMO FUNCIONA:
        1. Resolução do Projeto — Usa o project_id fornecido ou o padrão da plataforma.
        2. Carregamento de Credenciais — Chama _parsear_credenciais_do_env() para
           tentar obter credenciais explícitas (JSON string ou arquivo).
        3. Cliente com Credenciais Explícitas — Se encontradas, cria o cliente usando
           service_account.Credentials para autenticação determinística.
        4. Fallback ADC — Se não houver credenciais no .env, usa as Application Default
           Credentials do ambiente (útil no Cloud Run, GKE, etc).

    Args:
        project_id (Optional[str]): ID do projeto GCP. Padrão: "plataforma-clara".

    Returns:
        bigquery.Client: Cliente BigQuery autenticado e pronto para uso.

    Raises:
        google.auth.exceptions.DefaultCredentialsError: Se nenhuma credencial for
            encontrada e as ADC também estiverem ausentes.
    """
    # --- 1. RESOLUÇÃO DO PROJETO ---
    if project_id is None:
        project_id = _PROJETO_ID

    # --- 2. CARREGAMENTO DE CREDENCIAIS ---
    credenciais_dict = _parsear_credenciais_do_env()

    # --- 3. CLIENTE COM CREDENCIAIS EXPLÍCITAS ---
    if credenciais_dict:
        try:
            # from_service_account_info constrói o objeto de credenciais a partir
            # do dicionário JSON, sem precisar de arquivo em disco.
            credentials = service_account.Credentials.from_service_account_info(credenciais_dict)
            logger.debug("Cliente BigQuery criado com credenciais explícitas.")
            return bigquery.Client(project=project_id, credentials=credentials)
        except Exception as e:
            logger.warning(
                "Falha ao usar credenciais do .env: %s. Tentando credenciais padrão...", e
            )

    # --- 4. FALLBACK ADC ---
    # Application Default Credentials: o SDK do Google detecta automaticamente
    # credenciais do ambiente (variável GOOGLE_APPLICATION_CREDENTIALS padrão,
    # metadados do Cloud Run, gcloud CLI, etc).
    logger.info("Usando credenciais padrão do ambiente (Application Default Credentials).")
    return bigquery.Client(project=project_id)


def salvar_credenciais_em_arquivo_temporario() -> Optional[Path]:
    """
    Salva as credenciais em um arquivo temporário no disco.

    COMO FUNCIONA:
        1. Leitura — Obtém o dicionário de credenciais via _parsear_credenciais_do_env().
        2. Escrita — Cria um arquivo temporário com sufixo .json e serializa o dict.
        3. Retorno do Caminho — Devolve o Path para o arquivo, útil para ferramentas
           que exigem um arquivo físico (ex: bibliotecas legadas).

    Returns:
        Optional[Path]: Caminho do arquivo temporário ou None se não houver credenciais.

    Raises:
        OSError: Indiretamente, em caso de falha na criação do arquivo temporário.
    """
    # --- 1. LEITURA ---
    credenciais_dict = _parsear_credenciais_do_env()

    if not credenciais_dict:
        return None

    # --- 2. ESCRITA ---
    try:
        # delete=False é necessário para que o arquivo persista após o fechamento,
        # permitindo que outras ferramentas o leiam pelo caminho retornado.
        temp_file = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
            encoding="utf-8",
        )
        json.dump(credenciais_dict, temp_file)
        temp_file.close()

        # --- 3. RETORNO DO CAMINHO ---
        logger.debug("Credenciais salvas em arquivo temporário: %s", temp_file.name)
        return Path(temp_file.name)
    except Exception as e:
        logger.error("Falha ao salvar credenciais em arquivo temporário: %s", e)
        return None


def obter_info_credenciais() -> dict:
    """
    Retorna um dicionário de diagnóstico sobre as credenciais configuradas.

    Útil para logs de saúde da aplicação — nunca expõe dados sensíveis.

    COMO FUNCIONA:
        1. Inspecão do Env — Verifica o tipo da variável (JSON inline ou arquivo).
        2. Extração de Metadados — Lê project_id e client_email do dict de credenciais.
        3. Retorno — Devolve o dict de diagnóstico sem expor segredos.

    Returns:
        dict: Informações de diagnóstico com chaves: configurada, tipo, projeto,
              email_servico.
    """
    # --- 1. INSPEÇÃO DO ENV ---
    env_cred = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    credenciais_dict = _parsear_credenciais_do_env()

    info: dict = {
        "configurada": bool(env_cred),
        "tipo": None,
        "projeto": None,
        "email_servico": None,
    }

    if env_cred.startswith("{"):
        info["tipo"] = "string_json"
    elif Path(env_cred).is_file():
        info["tipo"] = "arquivo"

    # --- 2. EXTRAÇÃO DE METADADOS ---
    if credenciais_dict:
        info["projeto"] = credenciais_dict.get("project_id", "desconhecido")
        info["email_servico"] = credenciais_dict.get("client_email", "desconhecido")

    # --- 3. RETORNO ---
    return info
