"""
Cria as tabelas dos Blocos de Liquidez no BigQuery.

COMO FUNCIONA:
    1. Usa a credencial e o dataset de `backend/.env`.
    2. Cria `tb_blocos_liquidez` e `tb_blocos_empresas` se não existirem.
    3. Pode rodar de novo sem efeito: nada é apagado nem alterado.

Uso:
    python -m app.jobs.criar_tabelas_blocos

Args:
    Nenhum.

Returns:
    int: Código de saída do processo (0 em sucesso).

Raises:
    google.api_core.exceptions.GoogleAPICallError: Sem permissão ou dataset inexistente.
"""

import logging
import sys

from app.config.logging import configurar_logging
from app.config.settings import settings
from app.storage.blocos import criar_tabelas

logger = logging.getLogger(__name__)


def main() -> int:
    """Cria as tabelas e registra o dataset usado."""
    configurar_logging()
    criar_tabelas()
    logger.info(
        "Tabelas de blocos prontas em %s.%s.", settings.project_id, settings.bigquery_dataset
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
