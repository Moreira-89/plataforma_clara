"""
Números oficiais do relatório, calculados pelo código a partir da carteira do investidor.

A IA não faz conta: ela recebe estes números prontos e só os comenta. O PDF desenha os mesmos
números (cartões, tabelas e gráfico), então texto e desenho nunca discordam.

COMO FUNCIONA:
    1. `indicadores`: capital, empresas, score ponderado e nota da carteira, agora e no mês
       anterior, e a distribuição do capital por faixa de risco.
    2. `saude_dos_blocos`: uma linha por bloco, com score, nota e variação contra o mês anterior.
    3. `movimentacoes`: upgrades e downgrades (nota do mês contra a do mês anterior) com o motivo,
       que é o critério do score que mais mudou (dado real, do histórico do arquivo SQL 15).
    4. `principais_empresas`: as empresas com mais capital do investidor.

Todos recebem os registros de `relatorio.aportes_da_carteira` (um por bloco e empresa).

Args:
    Nenhum.

Returns:
    Nenhum.

Raises:
    Nenhum.
"""

import re
from collections import defaultdict
from typing import Any

from app.domain.risco import STATUS_EM_ORDEM, classificar_nota, classificar_status, ordem_da_nota

# Grau de investimento = Excelente a Adequado (AAA a BBB-); grau especulativo = Alerta a Inativo.
GRAU_INVESTIMENTO = STATUS_EM_ORDEM[:4]

_MESES = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")
_MAX_MOVIMENTACOES = 8  # por sentido (upgrades e downgrades), os de maior capital

# Critérios do score (arquivo SQL 12) e como cada um aparece no texto.
CRITERIOS = {
    "pt_qualidade_fundos": "qualidade dos fundos compradores",
    "pt_permanencia": "permanência nos fundos",
    "pt_risco_setor": "risco do setor",
    "pt_aceitacao": "aceitação em fundos",
}


def mes_curto(aaaa_mm: str | None) -> str | None:
    """'2026-07' -> 'jul/2026'."""
    if not aaaa_mm or not re.fullmatch(r"\d{4}-\d{2}", aaaa_mm):
        return aaaa_mm
    ano, mes = aaaa_mm.split("-")
    return f"{_MESES[int(mes) - 1]}/{ano}"


def moeda_compacta(valor: float) -> str:
    """R$ em formato curto: 'R$ 255 mil', 'R$ 5,4 mi'."""
    if valor >= 1_000_000:
        return f"R$ {valor / 1_000_000:.1f} mi".replace(".", ",")
    if valor >= 1_000:
        return f"R$ {valor / 1_000:.0f} mil"
    return f"R$ {valor:.0f}"


def _nome_do_bloco(row: dict[str, Any]) -> str:
    """Etiqueta e código curto do bloco, como no site ('Benitoíta · 19EA7F57'): há etiquetas
    repetidas (vários blocos Diamante), e só a etiqueta deixaria a tabela ambígua."""
    etiqueta = str(row.get("bloco_liquidez_setorial") or "N/A").split(" (")[0]
    id_bloco = str(row.get("id_aporte_uuid") or "").split(":")[0]
    return f"{etiqueta} · {id_bloco[:8].upper()}" if id_bloco else etiqueta


def _media_ponderada(pares: list[tuple[float | None, float]]) -> float | None:
    soma = sum(s * v for s, v in pares if s is not None)
    peso = sum(v for s, v in pares if s is not None)
    return round(soma / peso, 1) if peso > 0 else None


def _variacao_comparavel(trios: list[tuple[float | None, float | None, float]]) -> dict[str, Any]:
    """
    Variação do score no mês com as MESMAS empresas nos dois meses (score atual e anterior).

    Comparar a média de agora (todas as empresas) com a do mês anterior (só as que tinham score)
    misturaria mudança de nota com mudança de composição. Aqui as duas médias usam o mesmo grupo.

    Args:
        trios: (score atual, score anterior, valor) de cada empresa.

    Returns:
        dict[str, Any]: anterior, atual e variacao (médias ponderadas do grupo comparável) e o
            percentual do capital coberto por esse grupo.
    """
    ambos = [(a, b, v) for a, b, v in trios if a is not None and b is not None]
    total = sum(v for _, _, v in trios) or 1.0
    atual = _media_ponderada([(a, v) for a, _, v in ambos])
    anterior = _media_ponderada([(b, v) for _, b, v in ambos])
    return {
        "anterior": anterior,
        "atual": atual,
        "variacao": None if atual is None or anterior is None else round(atual - anterior, 1),
        "pct_capital_comparavel": round(100 * sum(v for _, _, v in ambos) / total, 1),
    }


def indicadores(aportes: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Números da carteira inteira (não a amostra que vai ao prompt).

    O score é a média ponderada pelo valor (a mesma conta do site); aporte sem score fica fora da
    média e entra na distribuição como "Sem score".
    """
    capital_total = 0.0
    por_faixa: dict[str, float] = defaultdict(float)
    atuais: list[tuple[float | None, float]] = []
    trios: list[tuple[float | None, float | None, float]] = []
    blocos, empresas = set(), set()
    for row in aportes:
        valor = float(row.get("valor_aporte_compra") or 0.0)
        score = row.get("score_risco_interno")
        capital_total += valor
        blocos.add(_nome_do_bloco(row) + str(row.get("bloco_liquidez_setorial")))
        empresas.add(str(row.get("id_empresa") or row.get("empresa_sacada_nome")))
        atuais.append((None if score is None else float(score), valor))
        trios.append(
            (
                None if score is None else float(score),
                (row.get("historico") or {}).get("score_anterior"),
                valor,
            )
        )
        por_faixa["Sem score" if score is None else classificar_status(float(score))] += valor

    score = _media_ponderada(atuais)
    comparavel = _variacao_comparavel(trios)
    distribuicao = [
        (
            faixa,
            round(100 * por_faixa[faixa] / capital_total, 1) if capital_total > 0 else 0.0,
            round(por_faixa[faixa], 2),
        )
        for faixa in [*STATUS_EM_ORDEM, "Sem score"]
        if por_faixa.get(faixa, 0) > 0
    ]
    investimento = round(sum(p for f, p, _ in distribuicao if f in GRAU_INVESTIMENTO), 1)
    especulativo = round(
        sum(p for f, p, _ in distribuicao if f not in GRAU_INVESTIMENTO and f != "Sem score"), 1
    )
    return {
        "capital_total": round(capital_total, 2),
        "qtd_blocos": len(blocos),
        "qtd_empresas": len(empresas),
        "score_ponderado": score,
        "nota": None if score is None else classificar_nota(score),
        "faixa": None if score is None else classificar_status(score),
        # Tendência no mês só com as empresas que têm score nos dois meses (ver _variacao_comparavel).
        "tendencia": comparavel,
        "distribuicao": distribuicao,
        "pct_grau_investimento": investimento,
        "pct_grau_especulativo": especulativo,
        # Textos prontos para os cartões do PDF.
        "capital": moeda_compacta(capital_total),
        "blocos": len(blocos),
        "empresas": len(empresas),
        "score": "—" if score is None else f"{score:.1f}".replace(".", ","),
    }


def _tendencia(atual: float | None, anterior: float | None) -> float | None:
    if atual is None or anterior is None:
        return None
    return round(atual - anterior, 1)


def saude_dos_blocos(aportes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Uma linha por bloco: capital do investidor, empresas, score, nota e variação no mês."""
    grupos: dict[str, dict[str, Any]] = {}
    total = sum(float(r.get("valor_aporte_compra") or 0.0) for r in aportes) or 1.0
    for row in aportes:
        chave = str(row.get("bloco_liquidez_setorial"))
        g = grupos.setdefault(
            chave,
            {"bloco": _nome_do_bloco(row), "capital": 0.0, "empresas": 0, "at": [], "trios": []},
        )
        valor = float(row.get("valor_aporte_compra") or 0.0)
        g["capital"] += valor
        g["empresas"] += 1
        score = row.get("score_risco_interno")
        g["at"].append((None if score is None else float(score), valor))
        g["trios"].append(
            (
                None if score is None else float(score),
                (row.get("historico") or {}).get("score_anterior"),
                valor,
            )
        )

    linhas = []
    for g in grupos.values():
        score = _media_ponderada(g["at"])
        tendencia = _variacao_comparavel(g["trios"])
        linhas.append(
            {
                "bloco": g["bloco"],
                "capital": round(g["capital"], 2),
                "pct_carteira": round(100 * g["capital"] / total, 1),
                "empresas": g["empresas"],
                "score": score,
                "nota": None if score is None else classificar_nota(score),
                "faixa": None if score is None else classificar_status(score),
                "variacao_score": tendencia["variacao"],
            }
        )
    return sorted(linhas, key=lambda linha: -linha["capital"])


def _motivo(hist: dict[str, Any]) -> str | None:
    """O critério do score que mais mudou entre os dois meses (ou a trava de risco)."""
    trava_atual, trava_anterior = hist.get("trava_atual"), hist.get("trava_anterior")
    if trava_atual and not trava_anterior:
        return "trava de risco: inadimplência dos fundos compradores muito acima do mercado"
    if trava_anterior and not trava_atual:
        return (
            "trava de risco retirada: inadimplência dos fundos compradores voltou a níveis normais"
        )
    atual, anterior = hist.get("pontos_atual") or {}, hist.get("pontos_anterior") or {}
    deltas = [
        (c, atual[c] - anterior[c])
        for c in CRITERIOS
        if atual.get(c) is not None and anterior.get(c) is not None
    ]
    if not deltas:
        return None
    criterio, delta = max(deltas, key=lambda d: abs(d[1]))
    if abs(delta) < 0.05:
        return None
    sinal = "+" if delta > 0 else "−"
    return f"{CRITERIOS[criterio]} ({sinal}{abs(delta):.1f} pts)".replace(".", ",")


def movimentacoes(aportes: list[dict[str, Any]], mes_atual: str | None) -> dict[str, Any]:
    """
    Upgrades e downgrades: a nota de cada empresa no mês atual contra a do mês anterior.

    Returns:
        dict[str, Any]: mes_anterior, mes_atual, totais e as listas (empresa, blocos, nota e score
            antes e agora, capital do investidor e motivo), as de maior capital primeiro.
    """
    empresas: dict[str, dict[str, Any]] = {}
    mes_anterior = None
    for row in aportes:
        hist = row.get("historico") or {}
        mes_anterior = mes_anterior or hist.get("mes_anterior")
        chave = str(row.get("id_empresa") or row.get("empresa_sacada_nome"))
        item = empresas.setdefault(
            chave,
            {
                "empresa": row.get("empresa_sacada_nome"),
                "blocos": set(),
                "capital": 0.0,
                "atual": row.get("score_risco_interno"),
                "hist": hist,
            },
        )
        item["blocos"].add(_nome_do_bloco(row))
        item["capital"] += float(row.get("valor_aporte_compra") or 0.0)

    upgrades, downgrades, estaveis, sem_comparacao = [], [], 0, 0
    for item in empresas.values():
        atual, anterior = item["atual"], item["hist"].get("score_anterior")
        if atual is None or anterior is None:
            sem_comparacao += 1
            continue
        nota_atual, nota_anterior = classificar_nota(float(atual)), classificar_nota(anterior)
        degraus = ordem_da_nota(nota_anterior) - ordem_da_nota(nota_atual)  # > 0 = melhorou
        if degraus == 0:
            estaveis += 1
            continue
        registro = {
            "empresa": item["empresa"],
            "blocos": ", ".join(sorted(item["blocos"])),
            "nota_anterior": nota_anterior,
            "nota_atual": nota_atual,
            "score_anterior": round(anterior, 1),
            "score_atual": round(float(atual), 1),
            # Variação do SCORE (o que a nota mede); diferente dos pontos do critério no motivo.
            "variacao_score": round(float(atual) - anterior, 1),
            "capital": round(item["capital"], 2),
            "motivo": _motivo(item["hist"]),
        }
        (upgrades if degraus > 0 else downgrades).append(registro)

    def _ordenar(lista: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(lista, key=lambda r: -r["capital"])[:_MAX_MOVIMENTACOES]

    return {
        "mes_anterior": mes_curto(mes_anterior),
        "mes_atual": mes_curto(mes_atual),
        "qtd_upgrades": len(upgrades),
        "qtd_downgrades": len(downgrades),
        "estaveis": estaveis,
        "sem_comparacao": sem_comparacao,
        "upgrades": _ordenar(upgrades),
        "downgrades": _ordenar(downgrades),
    }


def principais_empresas(aportes: list[dict[str, Any]], limite: int = 8) -> list[dict[str, Any]]:
    """As empresas com mais capital do investidor, com nota e variação no mês."""
    total = sum(float(r.get("valor_aporte_compra") or 0.0) for r in aportes) or 1.0
    empresas: dict[str, dict[str, Any]] = {}
    for row in aportes:
        chave = str(row.get("id_empresa") or row.get("empresa_sacada_nome"))
        item = empresas.setdefault(
            chave,
            {
                "empresa": row.get("empresa_sacada_nome"),
                "ramo": row.get("ramo_atividade"),
                "blocos": set(),
                "capital": 0.0,
                "score": row.get("score_risco_interno"),
                "anterior": (row.get("historico") or {}).get("score_anterior"),
            },
        )
        item["blocos"].add(_nome_do_bloco(row))
        item["capital"] += float(row.get("valor_aporte_compra") or 0.0)

    linhas = []
    for item in sorted(empresas.values(), key=lambda i: -i["capital"])[:limite]:
        score = None if item["score"] is None else float(item["score"])
        linhas.append(
            {
                "empresa": item["empresa"],
                "ramo": item["ramo"],
                "blocos": ", ".join(sorted(item["blocos"])),
                "capital": round(item["capital"], 2),
                "pct_carteira": round(100 * item["capital"] / total, 1),
                "score": None if score is None else round(score, 1),
                "nota": None if score is None else classificar_nota(score),
                "faixa": None if score is None else classificar_status(score),
                "variacao_score": _tendencia(score, item["anterior"]),
            }
        )
    return linhas
