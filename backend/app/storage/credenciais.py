"""
Credencial de service account do GCP, compartilhada por BigQuery e Firebase.

COMO FUNCIONA:
    1. Lê `settings.google_application_credentials`.
    2. Valor começando com '{' é tratado como JSON inline (produção, containers).
    3. Qualquer outro valor é tratado como caminho de um arquivo .json (local).
    4. Se nada funcionar, devolve None e quem chama cai nas credenciais padrão (ADC).

Args:
    Nenhum.

Returns:
    dict | None: A credencial, via `carregar_credenciais()`.

Raises:
    Nenhum: falhas de leitura viram warning e None.
"""

import json
import logging
from pathlib import Path

from app.config.settings import settings

logger = logging.getLogger(__name__)


def carregar_credenciais() -> dict | None:
    """
    Obtém a credencial de service account configurada no ambiente.

    Returns:
        dict | None: Dicionário da service account, ou None se ausente ou inválida.
    """
    bruto = settings.google_application_credentials.strip()
    if not bruto:
        logger.debug("GOOGLE_APPLICATION_CREDENTIALS não configurada.")
        return None

    if bruto.startswith("{"):
        try:
            return json.loads(bruto)
        except json.JSONDecodeError as e:
            logger.warning("Falha ao parsear GOOGLE_APPLICATION_CREDENTIALS como JSON: %s", e)

    caminho = Path(bruto)
    if caminho.is_file():
        try:
            return json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Falha ao carregar credenciais de %s: %s", caminho, e)

    return None
