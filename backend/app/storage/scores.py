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
    dict[str, Any]: os dois meses mais recentes do histórico (score e pontos por critério), via
        `carregar_historico_recente()` (de `scores_empresas_historico.csv`, arquivo SQL 15).

Raises:
    Nenhum.
"""

import csv
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CAMINHO_SCORES = Path(__file__).resolve().parents[2] / "dados" / "scores_empresas.csv"
CAMINHO_HISTORICO = Path(__file__).resolve().parents[2] / "dados" / "scores_empresas_historico.csv"


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


_CRITERIOS = ("pt_qualidade_fundos", "pt_permanencia", "pt_risco_setor", "pt_aceitacao")


def _numero(texto: str | None) -> float | None:
    try:
        return float(texto) if texto not in (None, "") else None
    except ValueError:
        return None


@lru_cache
def carregar_historico_recente() -> dict[str, Any]:
    """
    Os dois meses mais recentes do histórico do score (base da tendência, dos upgrades e dos
    downgrades). Bloqueante na primeira chamada; depois fica em cache.

    O histórico sai do arquivo SQL 15, com uma linha por empresa e mês: `id_empresa`,
    `data_base` (AAAA-MM), `score`, os pontos dos 4 critérios (`pt_*`) e `trava_aplicada`.
    O mês mais recente dele é o mesmo do `scores_empresas.csv`.

    Returns:
        dict[str, Any]: {"mes_atual": "2026-08", "mes_anterior": "2026-07",
            "atual": {id: registro}, "anterior": {id: registro}}, em que registro =
            {"score", "pontos": {critério: pontos}, "trava"}. Sem o arquivo, ou com menos de dois
            meses, os meses vêm None e os dicionários vazios: o relatório declara a ausência de
            histórico.
    """
    vazio: dict[str, Any] = {"mes_atual": None, "mes_anterior": None, "atual": {}, "anterior": {}}
    if not CAMINHO_HISTORICO.is_file():
        logger.warning("Histórico de scores não encontrado: %s", CAMINHO_HISTORICO)
        return vazio

    por_mes: dict[str, dict[str, dict[str, Any]]] = {}
    with CAMINHO_HISTORICO.open(encoding="utf-8", newline="") as arquivo:
        for linha in csv.DictReader(arquivo):
            id_empresa = (linha.get("id_empresa") or "").strip()
            mes = (linha.get("data_base") or "").strip()
            score = _numero(linha.get("score"))
            if not id_empresa or not mes or score is None or not 0 <= score <= 100:
                continue
            por_mes.setdefault(mes, {})[id_empresa] = {
                "score": score,
                "pontos": {c: _numero(linha.get(c)) for c in _CRITERIOS},
                "trava": (linha.get("trava_aplicada") or "").strip() or None,
            }

    meses = sorted(por_mes)
    if len(meses) < 2:
        return vazio
    logger.info("Histórico de scores: %d meses; comparação %s → %s.", len(meses), *meses[-2:])
    return {
        "mes_atual": meses[-1],
        "mes_anterior": meses[-2],
        "atual": por_mes[meses[-1]],
        "anterior": por_mes[meses[-2]],
    }
