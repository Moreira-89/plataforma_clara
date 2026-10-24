"""
Layout do relatório em PDF com o design system da Plataforma Clara.

O relatório é um "papel timbrado" com três camadas:
    1. Moldura (este módulo): faixa escura com a logo no topo, ondas azuis no pé da página,
       rodapé com o aviso e a paginação. Igual em todas as páginas.
    2. Números (calculados pelo código em `agents/analise_carteira.py`): cartões no topo, tabela
       de saúde dos blocos, desenho da distribuição de capital, tabela de upgrades e downgrades
       (com o motivo) e tabela das principais empresas.
    3. Texto (escrito pela IA, em Markdown): o que os números significam para o investidor.

COMO FUNCIONA:
    1. `_montar_documento` monta o documento na ordem fixa das seções (resumo, saúde dos blocos,
       distribuição, destaques do mês, principais empresas, conclusão, como o score é calculado).
       Em cada seção, o código põe a tabela ou o gráfico e a IA entra com o texto (achado pelo
       título); se a IA não escreveu a seção, entra um texto padrão feito pelo código. No texto
       da IA, as faixas de risco ganham destaque só no peso da fonte (sem cor) e os valores
       (R$ e %) vão na fonte mono. O lugar dos desenhos é reservado com uma imagem transparente,
       que nunca é cortada entre páginas.
    2. O markdown_pdf monta o texto com o CSS da Clara (Inter e JetBrains Mono embutidas).
    3. `_desenhar_moldura` abre o PDF com o PyMuPDF e desenha a moldura e, nos lugares
       reservados, os cartões e a distribuição. Os desenhos ficam fora do markdown_pdf de
       propósito: o motor de layout dele repete fundos de blocos na página seguinte, e aqui o
       desenho é exato.

Cores e fontes vêm de `frontend/src/css/tokens.css` (design system da plataforma). As fontes
(OFL 1.1) e a logo ficam em `agents/assets/`; ver `assets/FONTES.md`.

Args:
    Nenhum.

Returns:
    Nenhum.

Raises:
    Nenhum.
"""

import html
import math
import re
from datetime import date
from pathlib import Path
from typing import Any

import pymupdf
from markdown_pdf import MarkdownPdf, Section

ASSETS = Path(__file__).resolve().parent / "assets"
_LOGO = ASSETS / "logo-clara.png"
_LOGO_PROPORCAO = 293 / 96  # largura ÷ altura do logo-clara.png

# Tokens do design system (frontend/src/css/tokens.css), em RGB de 0 a 1.
_COR = {
    nome: tuple(int(hexa[i : i + 2], 16) / 255 for i in (1, 3, 5))
    for nome, hexa in {
        "ink": "#0a0b0d",
        "body": "#5b616e",
        "muted": "#7c828a",
        "hairline": "#dee1e6",
        "canvas": "#ffffff",
        "surface_soft": "#f7f7f7",
        "surface_strong": "#eef0f3",
        "surface_dark": "#0a0b0d",
        "on_dark_soft": "#a8acb3",
        "primary": "#0052ff",
        "primary_active": "#003ecc",
        "primary_claro": "#b3c9ff",
    }.items()
}

# Faixas analíticas da régua de 22 notas (domain/risco.py), da melhor para a pior.
# Grau de investimento = Excelente a Adequado (AAA a BBB-); grau especulativo = Alerta a Inativo
# (BB+ a D), como na descrição do BB+ no prompt ("início do grau especulativo").
_GRAU_INVESTIMENTO = ("Excelente", "Muito Superior", "Superior", "Adequado")
_NOTAS_DA_FAIXA = {
    "Excelente": "AAA",
    "Muito Superior": "AA+ a AA-",
    "Superior": "A+ a A-",
    "Adequado": "BBB+ a BBB-",
    "Alerta": "BB+ a BB-",
    "Especulativo": "B+ a B-",
    "Crítico": "CCC+ a CCC-",
    "Severo": "CC e C",
    "Inativo": "D",
    "Sem score": "sem dado",
}
# Só duas famílias de cor no gráfico: azuis para o grau de investimento (mais escuro = melhor) e
# terrosos para o grau especulativo (mais escuro = pior). O texto não leva cor.
_TOM_DA_FAIXA = {
    "Excelente": "#002a8f",
    "Muito Superior": "#003ecc",
    "Superior": "#0052ff",
    "Adequado": "#7aa5ff",
    "Alerta": "#f0c9a8",
    "Especulativo": "#e0956a",
    "Crítico": "#c25a35",
    "Severo": "#93391f",
    "Inativo": "#5e2414",
    "Sem score": "#c9cdd3",
}
# Começo do grau de investimento na régua de score (piso do BBB-, domain/risco.py).
_PISO_GRAU_INVESTIMENTO = 54.55

# Página A4 em pé, em pontos.
_FAIXA_TOPO = 56
_ONDA = 96
_MARGEM_X = 54
_RECUO_TEXTO = 10  # o markdown_pdf recua o texto ~10 pt além da borda; o desenho acompanha
_BORDAS = (_MARGEM_X, _FAIXA_TOPO + 34, -_MARGEM_X, -(_ONDA + 14))
_KPI_ALTURA = 64
_LINHA_LEGENDA = 17
_LARGURA_UTIL = 595 - 2 * (_MARGEM_X + _RECUO_TEXTO)
_ESPACO = "espaco.png"  # PNG transparente de 1 px: reserva o lugar de um desenho

_CSS = """
@font-face { font-family: Inter; src: url(Inter-Regular.ttf); }
@font-face { font-family: Inter; src: url(Inter-SemiBold.ttf); font-weight: bold; }
@font-face { font-family: InterMedium; src: url(Inter-Medium.ttf); }
@font-face { font-family: Mono; src: url(JetBrainsMono-Medium.ttf); }

body { font-family: Inter; font-size: 10pt; line-height: 1.55; color: #3b404a; }

h1 { font-family: Inter; font-weight: normal; font-size: 24pt; line-height: 1.15;
     color: #0a0b0d; margin: 0 0 4pt 0; }
.meta { font-size: 8.5pt; color: #7c828a; margin: 0 0 18pt 0; }
.meta b { color: #0a0b0d; font-weight: normal; font-family: InterMedium; }

h2 { font-family: InterMedium; font-weight: normal; font-size: 13pt; color: #0a0b0d;
     margin: 20pt 0 8pt 0; padding: 0 0 5pt 0; border-bottom: 1px solid #dee1e6; }
h3 { font-family: InterMedium; font-weight: normal; font-size: 10.5pt; color: #0052ff;
     margin: 12pt 0 4pt 0; }
p { margin: 0 0 8pt 0; }
strong, b { font-weight: bold; color: #0a0b0d; }
ul, ol { margin: 0 0 8pt 0; padding-left: 14pt; }
li { margin: 0 0 4pt 0; }

table { width: 100%; border-collapse: collapse; margin: 6pt 0 12pt 0; font-size: 9pt; }
th { font-family: InterMedium; font-weight: normal; font-size: 7.5pt; color: #7c828a;
     text-align: left; padding: 6pt 8pt; border-top: 0.5px solid #7c828a;
     border-bottom: 1px solid #dee1e6; }
td { padding: 7pt 8pt; border-bottom: 1px solid #eef0f3; color: #0a0b0d; }
tr { page-break-inside: avoid; }

.num { font-family: Mono; font-size: 8.8pt; color: #0a0b0d; }
table.dados { font-size: 8.3pt; margin: 2pt 0 10pt 0; }
table.dados th { font-size: 6.5pt; padding: 5pt 5pt; }
table.dados td { padding: 5pt 5pt; }
table.dados .num { font-size: 8pt; }
.apagado { color: #a8acb3; }
.codigo { font-family: Mono; font-size: 6.5pt; color: #7c828a; }
.nota-tabela { font-size: 8.5pt; color: #5b616e; margin: 0 0 6pt 0; }
.faixa { font-family: InterMedium; color: #0a0b0d; }
/* Sem background-color de propósito: o motor do markdown_pdf repete o fundo de blocos na
   página seguinte (aparece como uma faixa cinza solta). Só a borda azul marca a caixa. */
.aviso { border-left: 3px solid #0052ff; padding: 4pt 10pt; font-size: 8.5pt; color: #5b616e;
         margin-top: 10pt; }
"""


_LEITURA_DA_FAIXA = {
    # Resumo da descrição de cada faixa na tabela de 22 notas (agents/prompt.py): o que a faixa
    # significa na escala, não uma afirmação sobre uma empresa específica.
    "Excelente": "capacidade máxima de pagamento",
    "Muito Superior": "fluxo de caixa robusto",
    "Superior": "desempenho sólido",
    "Adequado": "cumpre obrigações; pede monitoramento",
    "Alerta": "início do grau especulativo",
    "Especulativo": "depende de condições favoráveis",
    "Crítico": "vulnerabilidade financeira alta",
    "Severo": "capacidade muito comprometida",
    "Inativo": "pior perfil da escala",
    "Sem score": "sem dado público no mês",
}

# Seções do relatório, na ordem em que aparecem. O texto de cada uma vem da IA (procurado pelo
# título); tabelas, gráfico e números vêm do código.
_SECOES = (
    ("resumo", "Resumo Executivo da Carteira", r"resumo|sum[aá]rio"),
    ("blocos", "Análise dos Blocos", r"an[aá]lise|sa[uú]de|blocos"),
    ("distribuicao", "Distribuição de Capital por Risco", r"distribui"),
    ("destaques", "Destaques do Mês", r"destaque|upgrade|downgrade|movimenta"),
    ("empresas", "Principais Empresas da Carteira", r"principa|empresas|matriz"),
    ("conclusao", "Conclusão", r"conclus"),
)
# Seções que o código escreve sozinho: se a IA as escrever, o texto dela é ignorado.
_SECOES_DO_CODIGO = r"transpar|aviso|metodolog|fonte|como o score"

_TITULO_NO_DESENHO = 34  # o título da seção é desenhado junto, para nunca ficar sozinho no pé


def _altura_distribuicao(indicadores: dict[str, Any]) -> float:
    """Altura do desenho da distribuição: título, barra, legenda (uma linha por faixa) e régua."""
    return _TITULO_NO_DESENHO + 78 + _LINHA_LEGENDA * len(indicadores["distribuicao"]) + 74


def _espaco(largura: float, altura: float) -> str:
    """Reserva um retângulo no texto; o desenho é feito depois, por cima, com o PyMuPDF."""
    return f'<img src="{_ESPACO}" width="{largura:.0f}" height="{altura:.0f}" />'


def _pct(valor: float) -> str:
    return f"{valor:.1f}".replace(".", ",") + "%"


def _num(valor: float | None, casas: int = 1) -> str:
    return "—" if valor is None else f"{valor:.{casas}f}".replace(".", ",")


def _moeda(valor: float) -> str:
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _valor(valor: float) -> str:
    """Valor em reais sem o 'R$' (o cabeçalho da coluna já diz a moeda)."""
    return _moeda(valor).removeprefix("R$ ")


def _rotulo_blocos(blocos: str) -> str:
    """'Benitoíta · DF243041' -> etiqueta em cima e código menor embaixo (cabe em coluna estreita)."""
    partes = []
    for bloco in blocos.split(", "):
        etiqueta, _, codigo = bloco.partition(" · ")
        partes.append(
            html.escape(etiqueta)
            + (f'<br/><span class="codigo">{html.escape(codigo)}</span>' if codigo else "")
        )
    return "<br/>".join(partes)


def _variacao(valor: float | None) -> str:
    """Variação do score no mês, com seta: '↑ +1,2', '↓ −0,8', '=' ou '—' (sem histórico)."""
    if valor is None:
        return '<span class="apagado">—</span>'
    if abs(valor) < 0.05:
        return '<span class="apagado">=</span>'
    seta, sinal = ("↑", "+") if valor > 0 else ("↓", "−")
    return f"{seta} {sinal}{_num(abs(valor))}"


def _tabela(cabecalho: list[tuple[str, bool]], linhas: list[list[str]]) -> str:
    """Tabela HTML simples (sem fundo de célula: o motor do PDF repete fundos na página seguinte)."""
    ths = "".join(
        f'<th style="text-align:{"right" if direita else "left"}">{t}</th>'
        for t, direita in cabecalho
    )
    trs = "".join(
        "<tr>"
        + "".join(
            f'<td style="text-align:{"right" if d else "left"}">{c}</td>'
            for c, (_, d) in zip(linha, cabecalho, strict=True)
        )
        + "</tr>"
        for linha in linhas
    )
    return f'<table class="dados"><thead><tr>{ths}</tr></thead><tbody>{trs}</tbody></table>'


def _tabela_blocos(blocos: list[dict[str, Any]]) -> str:
    linhas = [
        [
            f"<b>{html.escape(b['bloco'])}</b>",
            str(b["empresas"]),
            f'<span class="num">{_valor(b["capital"])}</span>',
            f'<span class="num">{_pct(b["pct_carteira"])}</span>',
            f'<span class="num">{_num(b["score"])}</span>',
            f"<b>{b['nota'] or '—'}</b> {b['faixa'] or ''}",
            _variacao(b["variacao_score"]),
        ]
        for b in blocos
    ]
    cab = [
        ("BLOCO", False),
        ("EMPRESAS", True),
        ("SEU CAPITAL (R$)", True),
        ("% CARTEIRA", True),
        ("SCORE", True),
        ("NOTA", False),
        ("NO MÊS", True),
    ]
    return _tabela(cab, linhas)


def _tabela_empresas(empresas: list[dict[str, Any]]) -> str:
    linhas = [
        [
            f"<b>{html.escape(e['empresa'] or '—')}</b>",
            html.escape(e["ramo"] or "—"),
            _rotulo_blocos(e["blocos"]),
            f'<span class="num">{_valor(e["capital"])}</span>',
            f'<span class="num">{_num(e["score"])}</span>',
            f"<b>{e['nota'] or '—'}</b>",
            _variacao(e["variacao_score"]),
        ]
        for e in empresas
    ]
    cab = [
        ("EMPRESA", False),
        ("RAMO", False),
        ("BLOCO", False),
        ("SEU CAPITAL (R$)", True),
        ("SCORE", True),
        ("NOTA", False),
        ("NO MÊS", True),
    ]
    return _tabela(cab, linhas)


def _bloco_destaques(mov: dict[str, Any]) -> str:
    """Resumo da comparação de notas e a tabela de upgrades e downgrades (código)."""
    if not mov.get("mes_anterior"):
        return ""
    resumo = (
        f'<p class="nota-tabela">Comparação de notas <b>{mov["mes_anterior"]} → '
        f"{mov['mes_atual']}</b>: {mov['qtd_upgrades']} upgrade(s), {mov['qtd_downgrades']} "
        f"downgrade(s), {mov['estaveis']} empresa(s) com a nota estável"
        + (f" e {mov['sem_comparacao']} sem dado nos dois meses" if mov["sem_comparacao"] else "")
        + ". A tabela mostra até 8 em cada sentido: as de maior capital na sua carteira.</p>"
    )
    linhas = [
        [
            f"<b>{html.escape(m['empresa'] or '—')}</b>",
            _rotulo_blocos(m["blocos"]),
            f"{'↑' if tipo == 'upgrades' else '↓'} {m['nota_anterior']} → <b>{m['nota_atual']}</b>",
            html.escape(m["motivo"] or "pequenas mudanças em vários critérios"),
        ]
        for tipo in ("upgrades", "downgrades")
        for m in mov[tipo]
    ]
    if not linhas:
        return resumo
    cab = [
        ("EMPRESA", False),
        ("BLOCO", False),
        ("NOTA (↑ UPGRADE · ↓ DOWNGRADE)", False),
        ("CRITÉRIO DO SCORE QUE MAIS MUDOU", False),
    ]
    return resumo + "\n\n" + _tabela(cab, linhas)


def _textos_padrao(conteudo: dict[str, Any]) -> dict[str, str]:
    """Texto feito pelo código para cada seção, usado quando a IA não escreve a seção."""
    ind = conteudo["indicadores"]
    mov = conteudo["movimentacoes"]
    dist = ind["distribuicao"]
    resumo = (
        f"Sua carteira soma {_moeda(ind['capital_total'])} em {ind['qtd_blocos']} bloco(s) e "
        f"{ind['qtd_empresas']} empresa(s). O score médio, ponderado pelo capital, é "
        f"{_num(ind['score_ponderado'])}, de 0 a 100 (quanto maior, menor o risco)."
    )
    tend = ind.get("tendencia") or {}
    if tend.get("variacao") is not None:
        mov = conteudo["movimentacoes"]
        resumo += (
            f" Considerando as empresas com score nos dois meses ({_pct(tend['pct_capital_comparavel'])}"
            f" do capital), o score passou de {_num(tend['anterior'])} em {mov['mes_anterior']} para "
            f"{_num(tend['atual'])} em {mov['mes_atual']}."
        )
    maior = max(dist, key=lambda d: d[1]) if dist else None
    distribuicao = (
        f"{_pct(ind['pct_grau_investimento'])} do seu capital está em faixas de grau de "
        f"investimento (Excelente a Adequado) e {_pct(ind['pct_grau_especulativo'])} em faixas de "
        "grau especulativo (Alerta a Inativo)."
        + (f" A maior parcela está na faixa {maior[0]} ({_pct(maior[1])})." if maior else "")
    )
    destaques = (
        "Ainda não há histórico de notas para comparar com o mês anterior; as movimentações "
        "aparecem assim que houver dois meses de dados."
        if not mov.get("mes_anterior")
        else (
            "Nenhuma empresa da sua carteira mudou de nota no período."
            if not (mov["qtd_upgrades"] or mov["qtd_downgrades"])
            else ""
        )
    )
    return {
        "resumo": resumo,
        "blocos": "",
        "distribuicao": distribuicao,
        "destaques": destaques,
        "empresas": "",
        "conclusao": "",
    }


def _secoes_da_ia(markdown: str) -> dict[str, str]:
    """Separa o texto da IA por seção (pelo título); devolve {chave: corpo da seção}."""
    texto = re.sub(r"^#\s", "## ", markdown.strip(), flags=re.MULTILINE)
    partes = re.split(r"^##\s+(.+)$", texto, flags=re.MULTILINE)
    corpos: dict[str, list[str]] = {}
    if partes[0].strip():
        corpos.setdefault("resumo", []).append(partes[0].strip())
    for titulo, corpo in zip(partes[1::2], partes[2::2], strict=False):
        nome = titulo.strip().lower()
        if re.search(_SECOES_DO_CODIGO, nome):
            continue
        chave = next((k for k, _, padrao in _SECOES if re.search(padrao, nome)), "conclusao")
        if corpo.strip():
            corpos.setdefault(chave, []).append(corpo.strip())
    return {k: "\n\n".join(v) for k, v in corpos.items()}


def _tratar_texto_ia(texto: str) -> str:
    """Valores (R$ e %) na fonte mono e faixas de risco com destaque discreto (sem cor)."""
    texto = re.sub(
        r"R\$\s?[\d.]+(?:,\d+)?(?:\s?(?:mil|mi|bi)\b)?",
        lambda m: f'<span class="num">{m.group(0)}</span>',
        texto,
    )
    texto = re.sub(
        r"(?<![\w>])\d+(?:,\d+)?\s?%", lambda m: f'<span class="num">{m.group(0)}</span>', texto
    )
    linhas = []
    for linha in texto.split("\n"):
        if not linha.startswith("#"):
            for faixa in sorted(_LEITURA_DA_FAIXA, key=len, reverse=True):
                if faixa == "Sem score":
                    continue
                linha = re.sub(
                    rf"(?<![\w>]){faixa}(?![\w<])", f'<span class="faixa">{faixa}</span>', linha
                )
        linhas.append(linha)
    return "\n".join(linhas)


def _montar_documento(markdown: str, nome_investidor: str, conteudo: dict[str, Any] | None) -> str:
    """
    O documento inteiro, na ordem fixa das seções: o código põe tabelas, gráfico e números; a IA
    entra com o texto de cada seção (ou o código usa um texto padrão, se ela não escreveu).
    """
    data_base = (conteudo or {}).get("data_base") or "—"
    cabecalho = (
        "# Relatório de Desempenho e Risco\n\n"
        f'<p class="meta">Investidor <b>{html.escape(nome_investidor)}</b> &nbsp;·&nbsp; '
        f"Gerado em <b>{date.today().strftime('%d/%m/%Y')}</b> &nbsp;·&nbsp; "
        f"Score com dados públicos da CVM, data-base <b>{html.escape(data_base)}</b></p>\n\n"
    )
    if not conteudo:
        # Sem os números do código, o texto da IA entra como veio.
        return cabecalho + _tratar_texto_ia(re.sub(r"^#\s", "## ", markdown, flags=re.M))

    ind = conteudo["indicadores"]
    ia = _secoes_da_ia(markdown)
    padrao = _textos_padrao(conteudo)
    codigo = {
        "blocos": _tabela_blocos(conteudo["blocos"]),
        "distribuicao": _espaco(_LARGURA_UTIL, _altura_distribuicao(ind))
        if ind["distribuicao"]
        else "",
        "destaques": _bloco_destaques(conteudo["movimentacoes"]),
        "empresas": _tabela_empresas(conteudo["principais_empresas"]),
    }

    partes = [cabecalho, _espaco(_LARGURA_UTIL, _KPI_ALTURA)]
    for chave, titulo, _ in _SECOES:
        texto = _tratar_texto_ia(ia[chave]) if ia.get(chave) else padrao[chave]
        corpo = "\n\n".join(x for x in (codigo.get(chave, ""), texto) if x)
        if not corpo:
            continue
        if chave == "distribuicao" and codigo["distribuicao"]:
            # O título vai desenhado dentro do gráfico (_desenhar_distribuicao): os dois mudam de
            # página juntos.
            partes.append(corpo)
        else:
            partes.append(f"## {titulo}\n\n{corpo}")
    partes.append(
        '<p class="aviso">Este relatório é exclusivamente informativo e não constitui recomendação '
        "de investimento. Fonte do score: CVM, Informe Mensal de FIDC (dados públicos), "
        f"data-base {html.escape(data_base)}. Em conformidade com a LGPD, o relatório não traz "
        "dados de pessoas físicas.</p>"
    )
    return "\n\n".join(partes) + "\n"


def _escrever(pagina, ponto, texto: str, fonte, tamanho: float, cor) -> None:
    """Escreve uma linha de texto com uma das fontes embutidas."""
    tw = pymupdf.TextWriter(pagina.rect)
    tw.append(ponto, texto, font=fonte, fontsize=tamanho)
    tw.write_text(pagina, color=cor)


def _cor_hex(hexa: str) -> tuple[float, float, float]:
    return tuple(int(hexa[i : i + 2], 16) / 255 for i in (1, 3, 5))


def _desenhar_cartoes(pagina, r: pymupdf.Rect, ind: dict[str, Any], fontes: dict) -> None:
    """Quatro cartões com os números oficiais da carteira (calculados pelo código)."""
    vao = 8
    largura = (r.width - 3 * vao) / 4
    blocos = ind["blocos"]
    cartoes = [
        ("CAPITAL INVESTIDO", ind["capital"], f"{blocos} bloco" + ("s" if blocos != 1 else "")),
        ("EMPRESAS", str(ind["empresas"]), "na carteira"),
        ("SCORE PONDERADO", ind["score"], "pelo capital, 0 a 100"),
        # A carteira não tem nota própria: as notas são das empresas e dos blocos.
        ("GRAU DE INVESTIMENTO", _pct(ind["pct_grau_investimento"]), "do capital, AAA a BBB-"),
    ]
    for k, (rotulo, valor, detalhe) in enumerate(cartoes):
        cx = r.x0 + k * (largura + vao)
        pagina.draw_rect(
            pymupdf.Rect(cx, r.y0, cx + largura, r.y1),
            color=None,
            fill=_COR["surface_soft"],
            radius=0.08,
        )
        _escrever(pagina, (cx + 10, r.y0 + 16), rotulo, fontes["texto"], 6.5, _COR["muted"])
        _escrever(pagina, (cx + 10, r.y0 + 39), valor, fontes["mono"], 15, _COR["ink"])
        _escrever(pagina, (cx + 10, r.y0 + 54), detalhe, fontes["texto"], 7.5, _COR["body"])


def _texto_direita(pagina, x1: float, y: float, texto: str, fonte, tam: float, cor) -> None:
    _escrever(pagina, (x1 - fonte.text_length(texto, fontsize=tam), y), texto, fonte, tam, cor)


def _desenhar_distribuicao(pagina, r: pymupdf.Rect, ind: dict[str, Any], fontes: dict) -> None:
    """
    Desenho da distribuição de capital por faixa de risco, em três partes:
        1. Uma barra única com todo o capital, dividida por faixa, e as chaves de "grau de
           investimento" e "grau especulativo" por cima (o resumo em uma olhada).
        2. A legenda: faixa, notas que ela reúne, valor em R$ e % do capital.
        3. A régua de score de 0 a 100, com o ponto onde a carteira está e onde começa o grau
           de investimento.
    """
    dist = ind["distribuicao"]
    x0, x1 = r.x0, r.x1
    largura = x1 - x0
    muted, ink, body = _COR["muted"], _COR["ink"], _COR["body"]

    # Título da seção, no mesmo estilo dos títulos ## do texto.
    _escrever(
        pagina, (x0, r.y0 + 14), "Distribuição de Capital por Risco", fontes["medio"], 13, ink
    )
    pagina.draw_line((x0, r.y0 + 21), (x1, r.y0 + 21), color=_COR["hairline"], width=0.75)
    r = pymupdf.Rect(x0, r.y0 + _TITULO_NO_DESENHO, x1, r.y1)

    # --- 1. Barra única + chaves --------------------------------------------------------------
    y_barra, alt_barra = r.y0 + 26, 20
    pedacos = []
    x = x0
    for faixa, pct, _ in dist:
        w = largura * pct / 100
        pedacos.append((faixa, x, x + w, pct))
        x += w
    for faixa, a, b, pct in pedacos:
        pagina.draw_rect(
            pymupdf.Rect(a, y_barra, max(a + 0.8, b - 1.2), y_barra + alt_barra),
            color=None,
            fill=_cor_hex(_TOM_DA_FAIXA[faixa]),
        )
        rotulo = _pct(pct)
        if b - a > fontes["mono"].text_length(rotulo, fontsize=7.5) + 10:
            claro = faixa in ("Adequado", "Alerta", "Especulativo", "Sem score")
            _escrever(
                pagina,
                (a + 6, y_barra + 13.5),
                rotulo,
                fontes["mono"],
                7.5,
                ink if claro else _COR["canvas"],
            )

    grupos = [
        ("GRAU DE INVESTIMENTO", [p for p in pedacos if p[0] in _GRAU_INVESTIMENTO]),
        (
            "GRAU ESPECULATIVO",
            [p for p in pedacos if p[0] not in _GRAU_INVESTIMENTO and p[0] != "Sem score"],
        ),
    ]
    for nome, partes in grupos:
        if not partes:
            continue
        a, b = partes[0][1], partes[-1][2] - 1.2
        total = sum(p[3] for p in partes)
        yc = y_barra - 8
        pagina.draw_line((a, yc), (b, yc), color=_COR["hairline"], width=0.8)
        pagina.draw_line((a, yc), (a, yc + 4), color=_COR["hairline"], width=0.8)
        pagina.draw_line((b, yc), (b, yc + 4), color=_COR["hairline"], width=0.8)
        texto = f"{nome}  {_pct(total)}"
        tw = fontes["texto"].text_length(texto, fontsize=6.5)
        xt = min(max(a, (a + b - tw) / 2), x1 - tw)
        pagina.draw_rect(
            pymupdf.Rect(xt - 4, yc - 6, xt + tw + 4, yc + 3), color=None, fill=_COR["canvas"]
        )
        _escrever(pagina, (xt, yc + 2.2), texto, fontes["texto"], 6.5, muted)

    # --- 2. Legenda ----------------------------------------------------------------------------
    y = y_barra + alt_barra + 24
    x_notas, x_leitura, x_capital = x0 + 104, x0 + 168, x1 - 62
    _escrever(pagina, (x0 + 16, y - 9), "FAIXA", fontes["texto"], 6, muted)
    _escrever(pagina, (x_notas, y - 9), "NOTAS", fontes["texto"], 6, muted)
    _escrever(pagina, (x_leitura, y - 9), "O QUE A FAIXA SIGNIFICA", fontes["texto"], 6, muted)
    _texto_direita(pagina, x_capital, y - 9, "CAPITAL", fontes["texto"], 6, muted)
    _texto_direita(pagina, x1, y - 9, "% DO TOTAL", fontes["texto"], 6, muted)
    for faixa, pct, valor in dist:
        y += _LINHA_LEGENDA
        pagina.draw_rect(
            pymupdf.Rect(x0, y - 8, x0 + 8, y), color=None, fill=_cor_hex(_TOM_DA_FAIXA[faixa])
        )
        _escrever(pagina, (x0 + 16, y), faixa, fontes["medio"], 8.5, ink)
        _escrever(pagina, (x_notas, y), _NOTAS_DA_FAIXA[faixa], fontes["texto"], 7.5, body)
        _escrever(pagina, (x_leitura, y), _LEITURA_DA_FAIXA[faixa], fontes["texto"], 7.5, body)
        _texto_direita(pagina, x_capital, y, _moeda(valor), fontes["mono"], 7.5, body)
        _texto_direita(pagina, x1, y, _pct(pct), fontes["mono"], 8, ink)
        pagina.draw_line((x0, y + 5), (x1, y + 5), color=_COR["surface_strong"], width=0.6)

    # --- 3. Régua de score ----------------------------------------------------------------------
    score = ind.get("score_ponderado")
    yr = y + 40
    _escrever(
        pagina, (x0, yr - 18), "ONDE A CARTEIRA ESTÁ NA RÉGUA DE SCORE", fontes["texto"], 6, muted
    )
    pos = lambda v: x0 + largura * v / 100  # noqa: E731
    pagina.draw_rect(pymupdf.Rect(x0, yr, x1, yr + 4), color=None, fill=_COR["surface_strong"])
    pagina.draw_rect(
        pymupdf.Rect(pos(_PISO_GRAU_INVESTIMENTO), yr, x1, yr + 4),
        color=None,
        fill=_cor_hex("#c7d8ff"),
    )
    for v in (0, 50, 100):
        rot = str(v)
        lx = pos(v) - fontes["mono"].text_length(rot, fontsize=6.5) / 2
        lx = min(max(lx, x0), x1 - fontes["mono"].text_length(rot, fontsize=6.5))
        _escrever(pagina, (lx, yr + 14), rot, fontes["mono"], 6.5, muted)
    xg = pos(_PISO_GRAU_INVESTIMENTO)
    pagina.draw_line((xg, yr - 3), (xg, yr + 7), color=_COR["primary"], width=0.8)
    _escrever(
        pagina,
        (xg + 4, yr + 14),
        "início do grau de investimento (BBB-)",
        fontes["texto"],
        6.5,
        body,
    )
    if score is not None:
        xs = pos(score)
        pagina.draw_circle((xs, yr + 2), 4.5, color=_COR["canvas"], fill=_COR["ink"], width=1.5)
        rot = f"Score da carteira · {_pct(score)[:-1]}"
        tw = fontes["medio"].text_length(rot, fontsize=7.5)
        lx = min(max(xs - tw / 2, x0), x1 - tw)
        _escrever(pagina, (lx, yr - 8), rot, fontes["medio"], 7.5, ink)


def _onda(pagina, topo: float, amplitude: float, ciclos: float, fase: float, cor) -> None:
    """
    Uma onda suave de ponta a ponta (senoide), preenchida até o pé da página.

    Desenhada por baixo do que já existe (overlay=False): por isso as ondas são desenhadas da
    frente para trás, e a última desenhada fica no fundo.
    """
    w, h = pagina.rect.width, pagina.rect.height
    pontos = [
        pymupdf.Point(x, topo + amplitude * math.sin(2 * math.pi * ciclos * x / w + fase))
        for x in (w * k / 120 for k in range(121))
    ]
    forma = pagina.new_shape()
    forma.draw_polyline([pymupdf.Point(0, h), *pontos, pymupdf.Point(w, h)])
    forma.finish(color=None, fill=cor, closePath=True)
    forma.commit(overlay=False)


def _desenhar_moldura(caminho: Path, conteudo: dict[str, Any] | None) -> None:
    """Faixa com a logo, ondas, rodapé e paginação em todas as páginas; números na 1ª."""
    doc = pymupdf.open(caminho)
    total = doc.page_count
    fontes = {
        "texto": pymupdf.Font(fontfile=str(ASSETS / "Inter-Regular.ttf")),
        "medio": pymupdf.Font(fontfile=str(ASSETS / "Inter-Medium.ttf")),
        "mono": pymupdf.Font(fontfile=str(ASSETS / "JetBrainsMono-Medium.ttf")),
    }

    espacos = 0
    for i, pagina in enumerate(doc, start=1):
        w, h = pagina.rect.width, pagina.rect.height
        # Isola o conteúdo do markdown_pdf num bloco próprio (q ... Q): sem isso, o primeiro texto
        # escrito por cima herdaria a transformação deixada por ele e sairia espelhado.
        pagina.wrap_contents()

        if conteudo:
            indicadores = conteudo["indicadores"]
            # Os espaços reservados (_espaco) viram desenhos: o 1º do documento são os cartões,
            # o 2º é a distribuição de capital.
            for info in pagina.get_image_info():
                if info["width"] != 1 or info["height"] != 1:
                    continue
                r = pymupdf.Rect(info["bbox"])
                if espacos == 0:
                    _desenhar_cartoes(pagina, r, indicadores, fontes)
                elif espacos == 1:
                    _desenhar_distribuicao(pagina, r, indicadores, fontes)
                espacos += 1

        # Topo: faixa escura com a logo e uma linha azul fina embaixo.
        pagina.draw_rect(
            pymupdf.Rect(0, 0, w, _FAIXA_TOPO), color=None, fill=_COR["surface_dark"], overlay=False
        )
        pagina.draw_rect(
            pymupdf.Rect(0, _FAIXA_TOPO, w, _FAIXA_TOPO + 2), color=None, fill=_COR["primary"]
        )
        altura_logo = 24
        y_logo = (_FAIXA_TOPO - altura_logo) / 2
        pagina.insert_image(
            pymupdf.Rect(
                _MARGEM_X, y_logo, _MARGEM_X + altura_logo * _LOGO_PROPORCAO, y_logo + altura_logo
            ),
            filename=str(_LOGO),
        )
        rotulo = "RELATÓRIO MENSAL · BLOCOS DE LIQUIDEZ"
        largura_rotulo = fontes["texto"].text_length(rotulo, fontsize=7)
        _escrever(
            pagina,
            (w - _MARGEM_X - largura_rotulo, _FAIXA_TOPO / 2 + 2.5),
            rotulo,
            fontes["texto"],
            7,
            _COR["on_dark_soft"],
        )

        # Pé: três ondas azuis, da mais escura (frente) para a mais clara (fundo).
        _onda(pagina, h - _ONDA + 62, 9, 1.3, 2.4, _COR["primary_active"])
        _onda(pagina, h - _ONDA + 38, 12, 1.1, 0.9, _COR["primary"])
        _onda(pagina, h - _ONDA + 18, 14, 0.9, 0.0, _COR["primary_claro"])

        # Rodapé em branco sobre a onda escura: aviso e paginação.
        aviso = (
            "Plataforma Clara · Documento informativo, não constitui recomendação de investimento."
        )
        _escrever(pagina, (_MARGEM_X, h - 18), aviso, fontes["texto"], 7, _COR["canvas"])
        paginacao = f"{i:02d} / {total:02d}"
        largura_pag = fontes["mono"].text_length(paginacao, fontsize=7.5)
        _escrever(
            pagina,
            (w - _MARGEM_X - largura_pag, h - 18),
            paginacao,
            fontes["mono"],
            7.5,
            _COR["canvas"],
        )

    # Embute só os caracteres usados das fontes: o PDF cai de ~1 MB para algumas centenas de KB.
    doc.subset_fonts()
    doc.save(caminho.with_suffix(".final.pdf"), garbage=3, deflate=True)
    doc.close()
    caminho.with_suffix(".final.pdf").replace(caminho)


def gerar_pdf(
    markdown: str,
    nome_investidor: str,
    destino: Path,
    conteudo: dict[str, Any] | None = None,
) -> Path:
    """
    Monta o PDF do relatório no layout da Clara.

    Args:
        markdown (str): Texto do relatório escrito pela IA, com um título ## por seção.
        nome_investidor (str): Nome exibido no cabeçalho.
        destino (Path): Caminho do PDF a gravar.
        conteudo (dict | None): Números oficiais calculados pelo código
            (`relatorio.conteudo_oficial`): data_base, indicadores, blocos, movimentacoes e
            principais_empresas. Sem eles, o PDF sai só com o texto da IA, sem cartões,
            tabelas e gráfico.

    Returns:
        Path: O próprio `destino`.
    """
    texto = _montar_documento(markdown, nome_investidor, conteudo)
    pdf = MarkdownPdf(toc_level=2)
    pdf.add_section(
        Section(texto, root=str(ASSETS), paper_size="A4", borders=_BORDAS), user_css=_CSS
    )
    pdf.meta["title"] = "Relatório de Desempenho e Risco — Plataforma Clara"
    pdf.meta["author"] = "Plataforma Clara"
    pdf.save(str(destino))
    _desenhar_moldura(destino, conteudo)
    return destino
