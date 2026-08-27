"""
Formatação de valores no padrão brasileiro.

Estas conversões estavam espalhadas por `dashboard_service`, `dashboard_state`,
`detalhes_bloco_state` e `explorar_blocos_state`, cada uma reimplementando a mesma
cadeia de `.replace()`. Reunidas aqui, elas continuam sendo o comportamento atual
da tela — inclusive onde esse comportamento é imperfeito (ver `formatar_milhoes`).

Na Fase 5, com o frontend desacoplado, boa parte disso deve virar responsabilidade
do cliente: a API entrega número, a UI decide como exibir. Até lá, o formato
precisa continuar idêntico ao que o investidor vê hoje.
"""

from typing import Any


def para_float(valor: Any) -> float:
    """
    Conversão tolerante de qualquer valor para float.

    Usada nos dados vindos de agregações SQL, onde `None` e `Decimal` convivem.

    Args:
        valor (Any): Valor a converter. `None`, "" e 0 viram 0.0.

    Returns:
        float: O valor convertido, ou 0.0 quando a conversão é impossível.
    """
    try:
        return float(valor or 0)
    except (TypeError, ValueError):
        return 0.0


def formatar_numero(valor: float) -> str:
    """
    Formata um número no padrão brasileiro, sem o símbolo da moeda.

    COMO FUNCIONA:
        Usa o separador de milhar do Python (vírgula) e depois troca os símbolos
        em três passos, com 'X' como marcador temporário para evitar que a troca
        de vírgula por ponto desfaça a troca anterior.

    Args:
        valor (float): Número a formatar.

    Returns:
        str: Número com ponto de milhar e vírgula decimal — ex: '1.234.567,89'.
    """
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_moeda(valor: float) -> str:
    """
    Formata um valor como moeda brasileira.

    Args:
        valor (float): Valor em reais.

    Returns:
        str: Valor prefixado — ex: 'R$ 1.234.567,89'.
    """
    return f"R$ {formatar_numero(valor)}"


def formatar_milhoes(valor: float) -> str:
    """
    Formata um valor em milhões de reais, com uma casa decimal.

    CARACTERIZAÇÃO DE LIMITAÇÃO CONHECIDA: a troca de símbolos aqui é parcial —
    só o ponto decimal vira vírgula, e o separador de milhar do Python (vírgula)
    permanece. Para valores abaixo de R$ 1 bilhão o resultado é correto
    ('R$ 12,3M'), mas R$ 1,5 bilhão sai como 'R$ 1,500,0M'. O comportamento é
    preservado porque é o que está nos cards de Explorar Blocos hoje; corrigir é
    mudança de UI, e vai junto da Fase 5.

    Args:
        valor (float): Valor em reais (não em milhões).

    Returns:
        str: Valor em milhões — ex: 'R$ 12,3M'.
    """
    return f"R$ {f'{valor / 1_000_000:,.1f}'.replace('.', ',')}M"


def para_milhoes(valor: float) -> float:
    """
    Converte um valor em reais para milhões, arredondado em duas casas.

    Usada nos gráficos, que plotam a escala em milhões para caber no eixo.

    Args:
        valor (float): Valor em reais.

    Returns:
        float: Valor dividido por 1.000.000 — ex: 12.35.
    """
    return round(valor / 1_000_000, 2)


def formatar_cnpj(cnpj: str) -> str:
    """
    Aplica a máscara XX.XXX.XXX/XXXX-XX ao CNPJ.

    COMO FUNCIONA:
        1. Preenche com zeros à esquerda até 14 dígitos — reconstrói CNPJs que
           perderam o zero inicial em alguma conversão numérica pelo caminho.
        2. Aplica a máscara apenas se o resultado tiver 14 dígitos exatos.
        3. Devolve o valor preenchido sem máscara quando não é um CNPJ válido,
           em vez de esconder o dado do usuário.

    Args:
        cnpj (str): CNPJ somente com dígitos, possivelmente sem zeros à esquerda.

    Returns:
        str: CNPJ mascarado — ex: '12.345.678/0001-99'.
    """
    limpo = str(cnpj).zfill(14)
    if len(limpo) == 14 and limpo.isdigit():
        return f"{limpo[:2]}.{limpo[2:5]}.{limpo[5:8]}/{limpo[8:12]}-{limpo[12:]}"
    return limpo


def formatar_percentual(fracao: float, casas: int = 1) -> str:
    """
    Formata uma fração (0–1) como percentual.

    Args:
        fracao (float): Valor entre 0 e 1.
        casas (int): Casas decimais exibidas. Padrão 1.

    Returns:
        str: Percentual — ex: '12.5%'. Mantém o ponto decimal, como na tela atual.
    """
    return f"{fracao * 100:.{casas}f}%"
