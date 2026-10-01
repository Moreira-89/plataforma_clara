"""
Utilitário centralizado para gerenciar credenciais e conexões com o BigQuery.

Suporta dois modos de configuração da variável GOOGLE_APPLICATION_CREDENTIALS:
    1. String JSON completo (novo formato, ideal para ambientes de nuvem/CI)
    2. Caminho para arquivo .json (formato legado, para desenvolvimento local)
"""

import logging

from google.cloud import bigquery
from google.oauth2 import service_account

from app.config.settings import settings
from app.storage.credenciais import carregar_credenciais

# -----------------------------------------------------------------------------
# INICIALIZAÇÃO
# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# ID padrão do projeto GCP utilizado pela plataforma.
_PROJETO_ID = settings.project_id


# -----------------------------------------------------------------------------
# FUNÇÕES PÚBLICAS
# -----------------------------------------------------------------------------


def criar_cliente_bigquery(project_id: str | None = None) -> bigquery.Client:
    """
    Cria e retorna um cliente BigQuery autenticado.

    COMO FUNCIONA:
        1. Resolução do Projeto — Usa o project_id fornecido ou o padrão da plataforma.
        2. Carregamento de Credenciais — Chama carregar_credenciais() para
           tentar obter credenciais explícitas (JSON string ou arquivo).
        3. Cliente com Credenciais Explícitas — Se encontradas, cria o cliente usando
           service_account.Credentials para autenticação determinística.
        4. Fallback ADC — Se não houver credenciais no .env, usa as Application Default
           Credentials do ambiente (útil no Cloud Run, GKE, etc).

    Args:
        project_id (Optional[str]): ID do projeto GCP. Padrão: settings.project_id.

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
    credenciais_dict = carregar_credenciais()

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




