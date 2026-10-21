"""
Leitura dos scores de risco das empresas, de `backend/dados/scores_empresas.csv`.

Os scores são o Score de Reputação Clara, versão perfil público (v0.1.1), calculado no BigQuery
com dados públicos reais da CVM (Informe Mensal de FIDC, data-base ago/2026). Cada empresa do
cadastro (fictícia) recebe o perfil de um cedente real do mesmo setor; o nome e o CNPJ exibidos
continuam fictícios. A regra de cálculo está em `dados_fidc.tb_score_empresas` (arquivo SQL 12).
A plataforma só lê o arquivo; não treina nem executa modelo.

COMO FUNCIONA:
    1. Lê o CSV (`id_empresa`, `score`) uma vez por processo.
    2. Ignora linhas malformadas ou com score fora de 0 a 100.
    3. Sem o arquivo, devolve um dicionário vazio e registra um aviso: as telas mostram
       "—" no lugar do score, em vez de falhar.

Args:
    Nenhum.

Returns:
    dict[str, float]: id da empresa → score, via `carregar_scores()`.

Raises:
    Nenhum.
"""

import csv
import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

CAMINHO_SCORES = Path(__file__).resolve().parents[2] / "dados" / "scores_empresas.csv"


@lru_cache
def carregar_scores() -> dict[str, float]:
    """
    Carrega os scores por empresa. Bloqueante na primeira chamada; depois fica em cache.

    Returns:
        dict[str, float]: id da empresa → score de 0 a 100. Vazio se o arquivo não existe.
    """
    if not CAMINHO_SCORES.is_file():
        logger.warning("Arquivo de scores não encontrado: %s", CAMINHO_SCORES)
        return {}

    scores: dict[str, float] = {}
    with CAMINHO_SCORES.open(encoding="utf-8", newline="") as arquivo:
        for linha in csv.DictReader(arquivo):
            try:
                id_empresa = linha["id_empresa"].strip()
                score = float(linha["score"])
            except (KeyError, ValueError, AttributeError):
                continue
            if id_empresa and 0 <= score <= 100:
                scores[id_empresa] = score
    logger.info("Scores carregados: %d empresas.", len(scores))
    return scores
