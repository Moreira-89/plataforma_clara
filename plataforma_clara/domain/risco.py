"""
Regras de classificação de risco a partir do score interno.

Antes da extração do domínio, esta escada de faixas existia em QUATRO lugares
diferentes e com formatos de saída distintos: no `CASE WHEN` da query da gestora,
no `DetalhesBlocoState`, no `ExplorarBlocosState` e no `DashboardState`. Ficando
em um único módulo, uma mudança de política de risco passa a ser uma edição só.

ATENÇÃO — os dois vocabulários de nível DIVERGEM e a divergência é preservada de
propósito, porque é o que está na tela hoje: um score de 45 aparece como
"B (Médio Risco)" na página de detalhes do bloco e como "Alto (B)" no KPI do
dashboard. Unificar isso é decisão de produto, não de refatoração — por isso as
duas colunas de rótulo ficam explícitas na tabela `_FAIXAS`.

O `score_risco_interno` chega pronto como coluna do CSV de ingestão — a plataforma
não treina nem executa nenhum modelo. Estas funções apenas TRADUZEM o número.
"""

from typing import Final, NamedTuple


class _Faixa(NamedTuple):
    """Uma faixa da escala de risco, com os rótulos de cada formato de exibição."""

    piso: float
    nota: str
    nivel_detalhe: str  # usado em "A+ (Baixo Risco)" — página de detalhes do bloco
    nivel_kpi: str  # usado em "Baixo (A+)" — KPI de risco médio do dashboard


# Faixas em ordem decrescente: a primeira cujo piso o score alcança vence.
# Escala: 0–100, onde MAIOR score significa MENOR risco.
_FAIXAS: Final[tuple[_Faixa, ...]] = (
    _Faixa(80.0, "A+", "Baixo", "Baixo"),
    _Faixa(70.0, "A", "Baixo", "Baixo"),
    _Faixa(60.0, "A-", "Baixo", "Moderado"),
    _Faixa(50.0, "B+", "Médio", "Médio"),
    _Faixa(40.0, "B", "Médio", "Alto"),
)

# Aplicada quando o score não alcança nenhum piso acima.
_FAIXA_PADRAO: Final[_Faixa] = _Faixa(0.0, "C-", "Alto", "Crítico")

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
    Traduz o score numérico na nota de crédito curta (A+ → C-).

    Args:
        score (float): Score de risco interno, de 0 a 100.

    Returns:
        str: Nota na escala 'A+', 'A', 'A-', 'B+', 'B' ou 'C-'.
    """
    return _faixa_de(score).nota


def classificar_nota_com_nivel(score: float) -> str:
    """
    Traduz o score na nota acompanhada do nível — ex: 'A+ (Baixo Risco)'.

    Formato usado no cabeçalho da página de detalhes do bloco.

    Args:
        score (float): Score de risco interno, de 0 a 100.

    Returns:
        str: Nota e nível — ex: 'B+ (Médio Risco)'.
    """
    faixa = _faixa_de(score)
    return f"{faixa.nota} ({faixa.nivel_detalhe} Risco)"


def classificar_nivel_com_nota(score: float) -> str:
    """
    Traduz o score no nível acompanhado da nota — ex: 'Baixo (A+)'.

    Formato usado no KPI de risco médio do dashboard. Um score zerado (ou ausente)
    devolve 'N/A' em vez de 'Crítico (C-)': sem dados, a plataforma não afirma que
    o risco é crítico.

    Args:
        score (float): Score de risco interno, de 0 a 100.

    Returns:
        str: Nível e nota — ex: 'Moderado (A-)' — ou 'N/A' quando o score é zero.
    """
    if not score:
        return "N/A"
    faixa = _faixa_de(score)
    return f"{faixa.nivel_kpi} ({faixa.nota})"


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
