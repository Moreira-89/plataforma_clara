"""
Regras de classificação de risco a partir do score interno.

A escada de faixas fica em um único módulo: uma mudança de política de risco é uma edição só.

ESCALA: 22 notas (AAA a D), a régua original do relatório da Plataforma Clara — 22 faixas iguais
de cerca de 4,55 pontos (100 ÷ 22). Ex.: AAA = 95,46 a 100; BB+ = 50,00 a 54,54; D = 0 a 4,53.
Os cortes PRECISAM ser iguais em três lugares: aqui, na tabela `dados_fidc.tb_escala_notas` do
BigQuery (arquivo SQL 12; o painel da gestora lê a nota dos blocos de lá) e no prompt do relatório
(`agents/prompt.py`).

O `score_risco_interno` chega pronto, calculado por fora (Score de Reputação Clara, dados públicos
da CVM) — a plataforma não treina nem executa nenhum modelo. Estas funções apenas TRADUZEM o número.
"""

from collections.abc import Iterable
from decimal import Decimal
from typing import Final, NamedTuple


class _Faixa(NamedTuple):
    """Uma nota da escala de risco."""

    piso: float
    nivel: int  # 1 = AAA (melhor), 22 = D (pior)
    nota: str
    status: str  # faixa analítica do relatório: Excelente, Muito Superior, ..., Inativo


# Faixas em ordem decrescente: a primeira cujo piso o score alcança vence.
# Escala: 0–100, onde MAIOR score significa MENOR risco.
_FAIXAS: Final[tuple[_Faixa, ...]] = (
    _Faixa(95.46, 1, "AAA", "Excelente"),
    _Faixa(90.91, 2, "AA+", "Muito Superior"),
    _Faixa(86.37, 3, "AA", "Muito Superior"),
    _Faixa(81.82, 4, "AA-", "Muito Superior"),
    _Faixa(77.28, 5, "A+", "Superior"),
    _Faixa(72.73, 6, "A", "Superior"),
    _Faixa(68.19, 7, "A-", "Superior"),
    _Faixa(63.64, 8, "BBB+", "Adequado"),
    _Faixa(59.10, 9, "BBB", "Adequado"),
    _Faixa(54.55, 10, "BBB-", "Adequado"),
    _Faixa(50.00, 11, "BB+", "Alerta"),
    _Faixa(45.46, 12, "BB", "Alerta"),
    _Faixa(40.91, 13, "BB-", "Alerta"),
    _Faixa(36.37, 14, "B+", "Especulativo"),
    _Faixa(31.82, 15, "B", "Especulativo"),
    _Faixa(27.28, 16, "B-", "Especulativo"),
    _Faixa(22.73, 17, "CCC+", "Crítico"),
    _Faixa(18.19, 18, "CCC", "Crítico"),
    _Faixa(13.64, 19, "CCC-", "Crítico"),
    _Faixa(9.09, 20, "CC", "Severo"),
    _Faixa(4.54, 21, "C", "Severo"),
)

# Aplicada quando o score não alcança nenhum piso acima.
_FAIXA_PADRAO: Final[_Faixa] = _Faixa(0.0, 22, "D", "Inativo")

# Faixas analíticas (Status de Risco do relatório), da melhor para a pior.
STATUS_EM_ORDEM: Final[tuple[str, ...]] = tuple(
    dict.fromkeys(f.status for f in (*_FAIXAS, _FAIXA_PADRAO))
)

# Posição de cada nota na escala, para ordenar listas de notas (1 = melhor).
_NIVEL_POR_NOTA: Final[dict[str, int]] = {f.nota: f.nivel for f in (*_FAIXAS, _FAIXA_PADRAO)}

# Pisos de adimplência usados na tabela de aportes da gestora.
_PISO_ADIMPLENTE: Final[float] = 60.0
_PISO_ATENCAO: Final[float] = 40.0

# Corte do KPI de inadimplência projetada — mais conservador que o piso de 'Atenção'.
_PISO_INADIMPLENCIA_PROJETADA: Final[float] = 50.0


def _faixa_de(score: float) -> _Faixa:
    """Devolve a faixa correspondente ao score, ou a faixa padrão se nenhuma servir."""
    for faixa in _FAIXAS:
        if score >= faixa.piso:
            return faixa
    return _FAIXA_PADRAO


def classificar_nota(score: float) -> str:
    """
    Traduz o score numérico na nota de crédito (AAA → D).

    Args:
        score (float): Score de risco interno, de 0 a 100.

    Returns:
        str: Nota da escala de 22 níveis — ex: 'BBB+'.
    """
    return _faixa_de(score).nota


def classificar_nota_com_nivel(score: float) -> str:
    """
    Traduz o score na nota acompanhada da faixa analítica — ex: 'BBB (Adequado)'.

    Formato usado no cabeçalho da página de detalhes do bloco.

    Args:
        score (float): Score de risco interno, de 0 a 100.

    Returns:
        str: Nota e faixa — ex: 'BB+ (Alerta)'.
    """
    faixa = _faixa_de(score)
    return f"{faixa.nota} ({faixa.status})"


def classificar_status(score: float) -> str:
    """
    Traduz o score na faixa analítica do relatório — ex: 'Adequado'.

    Args:
        score (float): Score de risco interno, de 0 a 100.

    Returns:
        str: Excelente, Muito Superior, Superior, Adequado, Alerta, Especulativo, Crítico,
            Severo ou Inativo.
    """
    return _faixa_de(score).status


def ordem_da_nota(nota: str) -> int:
    """
    Posição da nota na escala, para ordenar da melhor para a pior.

    Args:
        nota (str): Nota da escala de 22 níveis — ex: 'AA-'.

    Returns:
        int: 1 para AAA até 22 para D; 99 para uma nota desconhecida (vai para o fim).
    """
    return _NIVEL_POR_NOTA.get(nota, 99)


def classificar_adimplencia(score: float) -> str:
    """
    Traduz o score médio de uma empresa sacada em status de adimplência.

    Args:
        score (float): Score médio dos aportes da empresa.

    Returns:
        str: 'Adimplente' (>= 60), 'Atenção' (>= 40) ou 'Inadimplente'.
    """
    if score >= _PISO_ADIMPLENTE:
        return "Adimplente"
    if score >= _PISO_ATENCAO:
        return "Atenção"
    return "Inadimplente"


def esta_em_risco_de_inadimplencia(score: float) -> bool:
    """
    Indica se o score fica abaixo do corte do KPI de inadimplência projetada.

    Args:
        score (float): Score médio do bloco.

    Returns:
        bool: True quando o score é menor que 50.
    """
    return score < _PISO_INADIMPLENCIA_PROJETADA


def score_ponderado(pares: Iterable[tuple[float | None, Decimal | float]]) -> float | None:
    """
    Média dos scores ponderada pelo capital de cada empresa.

    Args:
        pares (Iterable[tuple[float | None, Decimal | float]]): (score, capital) de cada empresa.
            Empresas sem score ficam de fora da média.

    Returns:
        float | None: Score de 0 a 100 com uma casa decimal, ou None se nenhuma empresa tem score.
    """
    soma = 0.0
    peso_total = 0.0
    for score, capital in pares:
        if score is None:
            continue
        peso = float(capital)
        soma += score * peso
        peso_total += peso
    if peso_total <= 0:
        return None
    return round(soma / peso_total, 1)
