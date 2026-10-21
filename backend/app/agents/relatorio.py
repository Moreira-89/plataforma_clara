"""
Serviço de geração de relatório consolidado de investimentos via IA (ChatGroq).

Fluxo principal:
    1. `aportes_da_carteira` transforma a carteira do investidor (blocos investidos, valor e empresas,
       a mesma fonte do cubo e do ranking da visão geral) nos registros que o prompt espera.
    2. Compacta os dados para caber no limite de tokens do provedor Groq.
    3. Envia o prompt institucional ao LLM via Groq (modelo em `settings.llm_model_name`).
    4. Converte o Markdown gerado em PDF e retorna os bytes para download.
"""

import json
import logging
import re
import shutil
import tempfile
from collections.abc import Iterable, Mapping
from decimal import Decimal
from pathlib import Path
from typing import Any

import PyPDF2
from groq import APIStatusError
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from app.agents import analise_carteira, layout_pdf
from app.agents.prompt import DESCRICAO_CLIENTE, SYSTEM_TEMPLATE, USER_TEMPLATE
from app.config.settings import settings
from app.domain import identidade
from app.domain.blocos import BlocoDetalhado
from app.domain.risco import classificar_nota

# -----------------------------------------------------------------------------
# INICIALIZAÇÃO
# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)

_ASSETS_DIR = Path(__file__).resolve().parent / "assets"
_PDF_REFERENCIA_PATH = _ASSETS_DIR / "Relatório de Insights Financeiros FIDC - Google Gemini.pdf"
_MAX_REF_CHARS = 5000
# Mês dos dados públicos da CVM usados no score (backend/dados/scores_empresas.csv).
# Atualizar junto com o CSV.
_DATA_BASE_SCORE = "ago/2026"

# Alias mantido: a normalização é a mesma do resto da plataforma, agora em
# domain/identidade.py. O nome curto continua porque é usado em vários pontos daqui.
_normalizar_documento = identidade.normalizar_documento


def _nome_para_exibicao(documento: str, nome_investidor: str | None) -> str:
    """
    Decide o nome que aparece no relatório.

    Antes isto era uma consulta ao PostgreSQL. Não é mais: quem chama já sabe quem
    é o usuário — o nome vem do token do Firebase — e o gerador de relatório não
    precisa de acesso a banco de usuário nenhum para escrever um PDF.

    Args:
        documento (str): CPF/CNPJ já normalizado, usado só no fallback.
        nome_investidor (str | None): Nome vindo do chamador.

    Returns:
        str: O nome recebido, ou um rótulo legível quando não vier nenhum.
    """
    if nome_investidor and nome_investidor.strip():
        return nome_investidor.strip()
    return f"Investidor {documento}" if documento else "Investidor"


def aportes_da_carteira(
    carteira: Iterable[tuple[Decimal, BlocoDetalhado]],
    scores: Mapping[str, float],
    historico: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Transforma a carteira do investidor nos registros que o prompt espera (um por bloco e empresa).

    O capital do investidor numa empresa é o valor investido no bloco vezes a fatia da empresa nele.

    Args:
        carteira (Iterable[tuple[Decimal, BlocoDetalhado]]): Pares (valor investido, bloco detalhado).
        scores (Mapping[str, float]): Score de risco (0 a 100) de cada empresa.
        historico (Mapping[str, Any] | None): Os dois meses mais recentes do histórico do score
            (`storage.scores.carregar_historico_recente`), para a tendência e os upgrades e
            downgrades.

    Returns:
        list[dict[str, Any]]: Registros com bloco, empresa, ramo, valor, datas, score e nota, e em
            "historico" o score e os pontos do mês anterior (quando houver).
    """
    historico = historico or {}
    atual_h, anterior_h = historico.get("atual") or {}, historico.get("anterior") or {}
    aportes: list[dict[str, Any]] = []
    for valor, detalhado in carteira:
        bloco = detalhado.bloco
        for empresa in detalhado.empresas:
            score = scores.get(empresa.id_empresa)
            ant = anterior_h.get(empresa.id_empresa) or {}
            agora = atual_h.get(empresa.id_empresa) or {}
            capital = (valor * empresa.percentual_liquidez / 100).quantize(Decimal("0.01"))
            aportes.append(
                {
                    "id_aporte_uuid": f"{bloco.id_bloco}:{empresa.id_empresa}",
                    "bloco_liquidez_setorial": f"{bloco.etiqueta} ({bloco.codigo_identificacao})",
                    "empresa_sacada_nome": empresa.nome_fantasia or empresa.cnpj,
                    "valor_aporte_compra": float(capital),
                    "data_referencia_competencia": bloco.data_criacao.isoformat(),
                    "status_prazo_vencimento": f"vence em {bloco.data_vencimento.isoformat()}",
                    "score_risco_interno": score,
                    "nota_risco": None if score is None else classificar_nota(score),
                    "id_empresa": empresa.id_empresa,
                    "ramo_atividade": empresa.ramo_atividade,
                    # Uso interno (tendência e motivos); não vai para a amostra do prompt.
                    "historico": {
                        "mes_atual": historico.get("mes_atual"),
                        "mes_anterior": historico.get("mes_anterior"),
                        "score_anterior": ant.get("score"),
                        "pontos_atual": agora.get("pontos"),
                        "pontos_anterior": ant.get("pontos"),
                        "trava_atual": agora.get("trava"),
                        "trava_anterior": ant.get("trava"),
                    },
                }
            )
    return aportes


def _to_json_compacto(dado: Any) -> str:
    return json.dumps(dado, ensure_ascii=False, separators=(",", ":"))


def _estimar_tokens_aprox(*textos: str) -> int:
    # Estimativa conservadora simples: ~1 token a cada 3.6 chars.
    total_chars = sum(len(t) for t in textos if t)
    return int(total_chars / 3.6)


def conteudo_oficial(aportes: list[dict[str, Any]]) -> dict[str, Any]:
    """Todos os números do relatório, calculados pelo código (os mesmos no texto e no PDF)."""
    mes_atual = next(
        (
            r["historico"].get("mes_atual")
            for r in aportes
            if (r.get("historico") or {}).get("mes_atual")
        ),
        None,
    )
    return {
        "data_base": analise_carteira.mes_curto(mes_atual) or _DATA_BASE_SCORE,
        "indicadores": analise_carteira.indicadores(aportes),
        "blocos": analise_carteira.saude_dos_blocos(aportes),
        "movimentacoes": analise_carteira.movimentacoes(aportes, mes_atual),
        "principais_empresas": analise_carteira.principais_empresas(aportes),
    }


def _conteudo_para_prompt(
    conteudo: dict[str, Any], *, limite_movimentacoes: int, limite_empresas: int
) -> dict[str, Any]:
    """O conteúdo oficial sem os textos de exibição do PDF e sem campos repetidos (economiza tokens).

    Os limites cortam só o que vai ao modelo; o PDF continua com as tabelas completas.
    """
    ind = conteudo["indicadores"]
    mov = conteudo["movimentacoes"]

    def _mov_curta(m: dict[str, Any]) -> dict[str, Any]:
        # score_anterior sai: score_atual + variacao_score já dizem o mesmo.
        return {k: v for k, v in m.items() if k != "score_anterior"}

    empresas = conteudo["principais_empresas"]
    return {
        "data_base": conteudo["data_base"],
        "indicadores": {
            "capital_total": ind["capital_total"],
            "qtd_blocos": ind["qtd_blocos"],
            "qtd_empresas": ind["qtd_empresas"],
            "score_ponderado": ind["score_ponderado"],
            "nota": ind["nota"],
            "faixa": ind["faixa"],
            # Variação no mês só com as empresas que têm score nos dois meses: "anterior" e "atual"
            # são as médias desse mesmo grupo (cobre pct_capital_comparavel do capital).
            "tendencia_no_mes": ind["tendencia"],
            "distribuicao_capital_por_faixa_pct": {f: p for f, p, _ in ind["distribuicao"]},
            "pct_grau_investimento": ind["pct_grau_investimento"],
            "pct_grau_especulativo": ind["pct_grau_especulativo"],
        },
        "blocos": conteudo["blocos"],
        "movimentacoes": {
            **{k: v for k, v in mov.items() if k not in ("upgrades", "downgrades")},
            # Os maiores pelo capital (a lista já vem ordenada assim).
            "upgrades": [_mov_curta(m) for m in mov.get("upgrades", [])[:limite_movimentacoes]],
            "downgrades": [_mov_curta(m) for m in mov.get("downgrades", [])[:limite_movimentacoes]],
        },
        "principais_empresas": empresas[:limite_empresas],
        # Calculada sobre as 8 maiores, mesmo quando a lista enviada é menor.
        "concentracao": {
            "pct_3_maiores": round(sum(e["pct_carteira"] for e in empresas[:3]), 1),
            "pct_8_maiores": round(sum(e["pct_carteira"] for e in empresas[:8]), 1),
        },
    }


def _compactar_dados_para_prompt(
    dados_bq: list[dict[str, Any]],
    *,
    limite_movimentacoes: int,
    limite_empresas: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Monta o que vai ao modelo: só os números oficiais, que já cobrem todos os blocos.

    A amostra de aportes e as listas por empresa saíram: repetiam o que "conteudo_oficial" já
    traz e estouravam o limite de tokens por minuto do Groq (8.000 no plano gratuito).
    """
    dados_bq_prompt: dict[str, Any] = {
        # Números oficiais calculados pelo código (agents/analise_carteira.py): o PDF já os mostra
        # em cartões, tabelas e no gráfico; o texto deve usar exatamente estes valores.
        "conteudo_oficial": _conteudo_para_prompt(
            conteudo_oficial(dados_bq),
            limite_movimentacoes=limite_movimentacoes,
            limite_empresas=limite_empresas,
        ),
    }
    meta = {
        "qtd_registros_total": len(dados_bq),
        "limite_movimentacoes": limite_movimentacoes,
        "limite_empresas": limite_empresas,
    }
    return dados_bq_prompt, meta


def _ler_pdf_referencia(max_chars: int = _MAX_REF_CHARS) -> str:
    texto_pdf_extraido = ""
    if not _PDF_REFERENCIA_PATH.exists():
        logger.info(
            "PDF de referência não encontrado em %s. Seguindo sem few-shot.", _PDF_REFERENCIA_PATH
        )
        return ""
    try:
        with open(_PDF_REFERENCIA_PATH, "rb") as arquivo_pdf:
            leitor_pdf = PyPDF2.PdfReader(arquivo_pdf)
            for pagina in leitor_pdf.pages:
                texto_pdf_extraido += (pagina.extract_text() or "") + "\n"
                if len(texto_pdf_extraido) >= max_chars:
                    texto_pdf_extraido = texto_pdf_extraido[:max_chars]
                    break
    except Exception as exc:
        logger.warning("Não foi possível ler o PDF de referência: %s", exc)
        return ""
    return texto_pdf_extraido


_PREFIXO_PROVEDOR = "groq:"
_MAX_TOKENS_RESPOSTA = 8192
_ESFORCO_RACIOCINIO = "medium"


def _nome_modelo_groq(nome_configurado: str) -> str:
    """Converte "groq:openai/gpt-oss-120b" em "openai/gpt-oss-120b"."""
    nome = nome_configurado.strip().strip('"')
    if nome.startswith(_PREFIXO_PROVEDOR):
        nome = nome[len(_PREFIXO_PROVEDOR) :]
    if not nome:
        raise RuntimeError("LLM_MODEL_NAME está vazio.")
    return nome


def _criar_llm() -> ChatGroq:
    """Monta o cliente do LLM a partir de `settings`."""
    if not settings.groq_api_key.get_secret_value():
        raise RuntimeError("GROQ_API_KEY não encontrada no ambiente.")

    return ChatGroq(
        api_key=settings.groq_api_key,
        model=_nome_modelo_groq(settings.llm_model_name),
        temperature=settings.llm_temperature,
        max_tokens=_MAX_TOKENS_RESPOSTA,
        reasoning_effort=_ESFORCO_RACIOCINIO,
    )


def _gerar_markdown_chatgroq(
    *,
    nome_cliente: str,
    descricao_cliente: str,
    dados_bq: list[dict[str, Any]],
) -> str:
    llm = _criar_llm()

    prompt = ChatPromptTemplate.from_messages(
        [("system", SYSTEM_TEMPLATE), ("user", USER_TEMPLATE)]
    )

    # Cada tentativa corta mais um pouco do que vai ao modelo (o PDF não muda).
    tentativas = [
        {"limite_movimentacoes": 8, "limite_empresas": 8, "max_ref": 1500},
        {"limite_movimentacoes": 8, "limite_empresas": 8, "max_ref": 0},
        {"limite_movimentacoes": 5, "limite_empresas": 5, "max_ref": 0},
        {"limite_movimentacoes": 3, "limite_empresas": 3, "max_ref": 0},
    ]

    ultimo_erro: Exception | None = None
    for idx, cfg in enumerate(tentativas, start=1):
        dados_bq_prompt, meta_prompt = _compactar_dados_para_prompt(
            dados_bq,
            limite_movimentacoes=cfg["limite_movimentacoes"],
            limite_empresas=cfg["limite_empresas"],
        )
        dados_bq_serializado = _to_json_compacto(dados_bq_prompt)
        texto_referencia = _ler_pdf_referencia(cfg["max_ref"])
        estimativa_tokens = _estimar_tokens_aprox(
            SYSTEM_TEMPLATE,
            USER_TEMPLATE,
            dados_bq_serializado,
            texto_referencia,
            nome_cliente,
            descricao_cliente,
        )
        logger.info(
            "Tentativa %d: payload prompt (movimentacoes<=%d, empresas<=%d, ref_chars=%d, tok_aprox=%d).",
            idx,
            meta_prompt["limite_movimentacoes"],
            meta_prompt["limite_empresas"],
            len(texto_referencia),
            estimativa_tokens,
        )

        prompt_formatado = prompt.format_messages(
            nome_cliente=nome_cliente,
            descricao_cliente=descricao_cliente,
            dados_bq=dados_bq_serializado,
            texto_do_pdf_referencia=texto_referencia,
        )

        try:
            resposta = llm.invoke(prompt_formatado)
            conteudo = getattr(resposta, "content", "") or ""
            if not str(conteudo).strip():
                motivo = getattr(resposta, "response_metadata", {}).get("finish_reason")
                raise RuntimeError(f"A IA retornou uma resposta vazia (finish_reason={motivo}).")
            return str(conteudo)
        except APIStatusError as exc:
            ultimo_erro = exc
            if exc.status_code == 413 and idx < len(tentativas):
                logger.warning(
                    "Prompt excedeu limite de tokens (tentativa %d/%d). Reduzindo payload e tentando novamente.",
                    idx,
                    len(tentativas),
                )
                continue
            raise

    if ultimo_erro is not None:
        raise ultimo_erro
    raise RuntimeError("Falha inesperada ao gerar relatório com ChatGroq.")


def _gerar_pdf_e_ler_bytes(
    nome_investidor: str, markdown: str, conteudo: dict[str, Any] | None
) -> tuple[bytes, str]:
    nome_limpo = re.sub(r"[^a-zA-Z0-9_-]+", "_", nome_investidor).strip("_") or "investidor"
    nome_arquivo = f"Relatorio_Consolidado_{nome_limpo}.pdf"
    # O PDF é escrito em disco só porque markdown_pdf não expõe saída em memória;
    # ele é lido e apagado logo abaixo.
    diretorio_temporario = tempfile.mkdtemp(prefix="relatorio_clara_")
    caminho_arquivo = Path(diretorio_temporario) / nome_arquivo

    try:
        # Layout da Clara (agents/layout_pdf.py): moldura com logo e ondas; cartões, tabelas e
        # gráfico com os números do código; e o texto da IA em cada seção.
        layout_pdf.gerar_pdf(markdown, nome_investidor, caminho_arquivo, conteudo)
        conteudo_bytes = caminho_arquivo.read_bytes()
    finally:
        # rmtree em vez de rmdir: se sobrar qualquer arquivo extra no diretório, o rmdir
        # levantaria OSError DENTRO do finally e mascararia a exceção original da geração do
        # PDF. Limpeza não pode virar a causa raiz.
        shutil.rmtree(diretorio_temporario, ignore_errors=True)

    return conteudo_bytes, nome_arquivo


# -----------------------------------------------------------------------------
# PONTO DE ENTRADA PÚBLICO
# -----------------------------------------------------------------------------


def gerar_relatorio_consolidado_investidor(
    nome_investidor: str | None, aportes: list[dict[str, Any]]
) -> tuple[bytes, str]:
    """
    Orquestra todo o fluxo de geração do relatório consolidado em PDF.

    COMO FUNCIONA:
        1. Nome de Exibição — Vem do chamador (token do Firebase); sem ele, um rótulo.
        2. Montagem do Payload — Estrutura os dados de investimentos para o prompt, a partir dos
           registros de `aportes_da_carteira` (a carteira do investidor).
        3. Geração do Markdown — Chama o ChatGroq com prompt institucional e retry
           progressivo para lidar com limites de token (status 413).
        4. Conversão para PDF — Monta o PDF no layout da Clara (agents/layout_pdf.py): moldura
           com a logo; cartões, tabelas e gráfico com os números calculados pelo código
           (`conteudo_oficial`); e o texto da IA em cada seção. O arquivo temporário é removido
           após leitura.

    Args:
        nome_investidor (str | None): Nome para exibir no relatório, vindo de quem
                                      autenticou o usuário.
        aportes (list[dict[str, Any]]): Registros da carteira, de `aportes_da_carteira`.

    Returns:
        tuple[bytes, str]: Tupla com (bytes do PDF, nome do arquivo para download).

    Raises:
        ValueError: Se não houver investimentos na carteira.
        RuntimeError: Se o ChatGroq retornar resposta vazia após todas as tentativas.
        APIStatusError: Se o Groq retornar erro diferente de 413 (ex: autenticação).
    """
    if not aportes:
        raise ValueError("Nenhum investimento encontrado para esse investidor.")

    nome_investidor = _nome_para_exibicao("", nome_investidor)

    logger.info(
        "Gerando relatório IA com prompt institucional para %s (%d registros).",
        nome_investidor,
        len(aportes),
    )
    markdown = _gerar_markdown_chatgroq(
        nome_cliente=nome_investidor,
        descricao_cliente=DESCRICAO_CLIENTE,
        dados_bq=aportes,
    )
    return _gerar_pdf_e_ler_bytes(nome_investidor, markdown, conteudo_oficial(aportes))
