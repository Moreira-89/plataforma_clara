import logging
import os
import re
import json
from pathlib import Path
from typing import Any
from collections import defaultdict

import PyPDF2
import reflex as rx
from groq import APIStatusError
from google.cloud import bigquery
from google.oauth2 import service_account
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from markdown_pdf import MarkdownPdf, Section
from pydantic import SecretStr
from sqlalchemy import func

from plataforma_clara.model.schemas import tb_usuario

logger = logging.getLogger(__name__)

_PROJETO_ID = "plataforma-clara"
_TABELA_APORTES_BQ = f"{_PROJETO_ID}.dados_fidc.tb_aporte"
_ROOT_DIR = Path(__file__).resolve().parents[2]
_ENV_CREDENCIAL = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
_CANDIDATOS_CREDENCIAIS = (
    ([Path(_ENV_CREDENCIAL)] if _ENV_CREDENCIAL else [])
    + [
        _ROOT_DIR / "plataforma-clara-0eafb2cacca9.json",
        _ROOT_DIR / "credentials.json",
    ]
)
_PDF_REFERENCIA_PATH = _ROOT_DIR / "Relatório de Insights Financeiros FIDC - Google Gemini.pdf"
_MAX_REF_CHARS = 5000
_MAX_AMOSTRA_APORTES = 60
_MAX_GRUPOS_EMPRESA = 100

_SYSTEM_TEMPLATE = """
Atue como um Analista de Investimentos Sênior especializado em Risco de Crédito e Fundos de Investimento em Direitos Creditórios (FIDCs).

Sua comunicação deve ser institucional, objetiva, técnica e baseada em dados, adequada para investidores qualificados e institucionais. Evite linguagem promocional, opinativa ou especulativa.

🔹 Contexto Operacional

Você é o motor analítico da Plataforma Clara, um ecossistema que promove transparência, padronização e confiança no mercado de crédito estruturado.

A Plataforma Clara opera em parceria com a Núclea, onde:

O investidor aloca capital em um Bloco de Liquidez
A Núclea distribui os recursos entre empresas (sacados/cedentes) via FIDC
O investidor não possui poder de decisão sobre alocação individual
O relatório é exclusivamente informativo, não recomendativo
🔹 Princípios da Plataforma Clara
Transparência e confiança via rankeamento de risco
Governança e credibilidade para corretoras
Eficiência na precificação de crédito (taxas mais justas para melhores ratings)
🔹 Objetivo

Gerar o:

Relatório Mensal de Desempenho e Risco do Bloco de Liquidez (30 dias)

O relatório deve:

Refletir a situação atual do bloco
Analisar movimentações de rating
Evidenciar risco de crédito agregado
Não conter recomendações ou sugestões de ação
🔹 Regras de Análise (CRÍTICAS)
Utilize exclusivamente os dados fornecidos
Não invente informações
Não sugira decisões ao investidor
Não utilize linguagem subjetiva ou emocional
Caso não haja dados: declarar explicitamente ausência de movimentações
Sempre considerar:
estabilidade de fluxo de caixa
variação de rating
concentração de risco
impacto na liquidez do bloco
🔹 Classificação de Risco (Obrigatória)

Utilize estritamente os 22 níveis abaixo:

[1] AAA até [22] D (conforme tabela original — manter integralmente)

⚠️ Regra adicional:
Agrupe os ratings nas seguintes faixas analíticas:

╔═══════╦═══════╦═════════════════╦══════════════════════════════════════════════════════════════════╗
║ Nível ║ Nota  ║ Status de Risco ║ Descrição da Capacidade de Pagamento                             ║
╠═══════╬═══════╬═════════════════╬══════════════════════════════════════════════════════════════════╣
║   1   ║ AAA   ║ Excelente       ║ Capacidade máxima de pagamento; risco de crédito inexistente.    ║
║   2   ║ AA+   ║ Muito Superior  ║ Fluxo de caixa robusto; desvio mínimo em relação ao ideal.       ║
║   3   ║ AA    ║ Muito Superior  ║ Histórico consistente; altamente confiável perante credores.     ║
║   4   ║ AA-   ║ Muito Superior  ║ Alta estabilidade financeira; riscos externos marginais.         ║
║   5   ║ A+    ║ Superior        ║ Desempenho sólido; baixa sensibilidade a mudanças de mercado.    ║
║   6   ║ A     ║ Superior        ║ Capacidade financeira forte, mas suscetível a ciclos econômicos. ║
║   7   ║ A-    ║ Superior        ║ Solvente; vulnerável apenas a crises sistêmicas severas.         ║
║   8   ║ BBB+  ║ Adequado        ║ Cumpre obrigações com segurança; grau de investimento médio.     ║
║   9   ║ BBB   ║ Adequado        ║ Desempenho médio; exige monitoramento de garantias.              ║
║  10   ║ BBB-  ║ Adequado        ║ Limite mínimo para ser considerada uma empresa segura.           ║
║  11   ║ BB+   ║ Alerta          ║ Exposição moderada a falhas; início do grau especulativo.        ║
║  12   ║ BB    ║ Alerta          ║ Fluxo de caixa instável sob pressão macroeconômica.              ║
║  13   ║ BB-   ║ Alerta          ║ Desempenho financeiro irregular e pouco previsível.              ║
║  14   ║ B+    ║ Especulativo    ║ Depende totalmente de condições de mercado favoráveis.           ║
║  15   ║ B     ║ Especulativo    ║ Capacidade de pagamento limitada; alta alavancagem.              ║
║  16   ║ B-    ║ Especulativo    ║ Risco considerável de atraso em parcelas ou juros.               ║
║  17   ║ CCC+  ║ Crítico         ║ Histórico de atrasos; vulnerabilidade financeira alta.           ║
║  18   ║ CCC   ║ Crítico         ║ Necessita de renegociação ou aporte imediato de capital.         ║
║  19   ║ CCC-  ║ Crítico         ║ Inadimplência iminente; probabilidade alta de calote.            ║
║  20   ║ CC    ║ Severo          ║ Quase incapaz de honrar compromissos; em pré-moratória.          ║
║  21   ║ C     ║ Severo          ║ Recuperação judicial ou processo de interrupção em curso.        ║
║  22   ║ D     ║ Inativo         ║ Default (Inadimplência total); falência ou encerramento.         ║
╚═══════╩═══════╩═════════════════╩══════════════════════════════════════════════════════════════════╝

🔹 Estrutura Obrigatória do Relatório

O output deve seguir exatamente este formato em Markdown:

Resumo Executivo do Bloco
Consolidar a saúde do bloco em 1 parágrafo
Informar:
rating médio ponderado (se possível)
tendência (estável, melhora ou deterioração)
nível geral de risco (com base nas faixas)
Distribuição de Capital por Risco
Analisar a alocação por faixa de risco
Destacar:
concentração em faixas críticas ou especulativas
equilíbrio do portfólio
possíveis impactos na liquidez
Destaques do Mês (Upgrades e Downgrades)

Upgrades:

Listar empresas com melhoria de rating
Explicar impacto na percepção de risco
Relacionar com acesso a taxas mais eficientes (Pilar 3)
... (40 linhas)

Abaixo, fornecemos a transcrição de um relatório oficial e de alto padrão da Plataforma Clara. 
Você DEVE absorver a arquitetura do texto, a sofisticação do vocabulário, os subtítulos utilizados e a densidade analítica deste documento. Use-o como o SEU ESPELHO ESTRUTURAL (few-shot) para redigir o relatório atual.
=== INÍCIO DO DOCUMENTO DE REFERÊNCIA ===
{texto_do_pdf_referencia}
=== FIM DO DOCUMENTO DE REFERÊNCIA ===
</referencia_de_excelencia_institucional>

Siga as instruções acima, cruze as informações e inicie a geração do relatório
"""

_USER_TEMPLATE = """
    DADOS EXTRAÍDOS DO BIGQUERY (tb_aporte higienizada):
    {dados_bq}
    
    DADOS ESPECÍFICOS DO CLIENTE (Investimentos e Score ML):
    {dados_invest}
    
    Gere o relatório estruturado.
    """


def _normalizar_documento(documento: str) -> str:
    return re.sub(r"[^0-9]", "", str(documento or ""))


def _buscar_nome_investidor(documento_investidor: str) -> str:
    documento = _normalizar_documento(documento_investidor)
    if not documento:
        return "Investidor"

    with rx.session() as session:
        usuario = (
            session.query(tb_usuario)
            .filter(func.regexp_replace(tb_usuario.identificador_usuario, "[^0-9]", "", "g") == documento)
            .first()
        )
        if usuario and usuario.nome_usuario:
            return str(usuario.nome_usuario)

    return f"Investidor {documento}"


def _criar_cliente_bigquery() -> bigquery.Client:
    for caminho in _CANDIDATOS_CREDENCIAIS:
        if caminho.is_file():
            credentials = service_account.Credentials.from_service_account_file(str(caminho))
            return bigquery.Client(project=_PROJETO_ID, credentials=credentials)
    return bigquery.Client(project=_PROJETO_ID)


def _buscar_dados_bigquery_investidor(documento_investidor: str) -> list[dict[str, Any]]:
    documento = _normalizar_documento(documento_investidor)
    if not documento:
        return []

    query = f"""
        SELECT
            id_aporte_uuid,
            bloco_liquidez_setorial,
            empresa_sacada_nome,
            valor_aporte_compra,
            data_referencia_competencia,
            status_prazo_vencimento,
            score_risco_interno
        FROM `{_TABELA_APORTES_BQ}`
        WHERE REGEXP_REPLACE(documento_investidor_cpf_cnpj, r'[^0-9]', '') = @documento_investidor
        ORDER BY data_referencia_competencia DESC
        LIMIT 2000
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("documento_investidor", "STRING", documento)]
    )

    client = _criar_cliente_bigquery()
    dataframe = client.query(query, job_config=job_config).to_dataframe()
    if dataframe.empty:
        return []

    dados: list[dict[str, Any]] = []
    for row in dataframe.to_dict(orient="records"):
        dados.append(
            {
                "id_aporte_uuid": str(row.get("id_aporte_uuid") or ""),
                "bloco_liquidez_setorial": str(row.get("bloco_liquidez_setorial") or "N/A"),
                "empresa_sacada_nome": str(row.get("empresa_sacada_nome") or "N/A"),
                "valor_aporte_compra": float(row.get("valor_aporte_compra") or 0.0),
                "data_referencia_competencia": str(row.get("data_referencia_competencia") or ""),
                "status_prazo_vencimento": str(row.get("status_prazo_vencimento") or ""),
                "score_risco_interno": float(row.get("score_risco_interno") or 0.0),
            }
        )
    return dados


def _montar_dados_investimentos(nome_investidor: str, dados_bq: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dados: list[dict[str, Any]] = []
    for row in dados_bq:
        dados.append(
            {
                "nome_investidor": nome_investidor,
                "nome_empresa": row.get("empresa_sacada_nome", "N/A"),
                "score_ml": row.get("score_risco_interno", 0.0),
                "valor_investido": row.get("valor_aporte_compra", 0.0),
            }
        )
    return dados


def _to_json_compacto(dado: Any) -> str:
    return json.dumps(dado, ensure_ascii=False, separators=(",", ":"))


def _estimar_tokens_aprox(*textos: str) -> int:
    # Estimativa conservadora simples: ~1 token a cada 3.6 chars.
    total_chars = sum(len(t) for t in textos if t)
    return int(total_chars / 3.6)


def _compactar_dados_para_prompt(
    dados_bq: list[dict[str, Any]],
    *,
    limite_amostra: int,
    limite_empresas: int,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    """Compacta os dados para caber no limite de tokens sem perder visão de todos os blocos."""
    total_registros = len(dados_bq)

    blocos: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"qtd_aportes": 0, "valor_total_aportado": 0.0, "score_soma": 0.0}
    )
    empresas: dict[tuple[str, str], dict[str, Any]] = {}

    for row in dados_bq:
        bloco = str(row.get("bloco_liquidez_setorial") or "N/A")
        empresa = str(row.get("empresa_sacada_nome") or "N/A")
        valor = float(row.get("valor_aporte_compra") or 0.0)
        score = float(row.get("score_risco_interno") or 0.0)

        blocos[bloco]["qtd_aportes"] += 1
        blocos[bloco]["valor_total_aportado"] += valor
        blocos[bloco]["score_soma"] += score

        chave = (bloco, empresa)
        if chave not in empresas:
            empresas[chave] = {
                "bloco_liquidez_setorial": bloco,
                "empresa_sacada_nome": empresa,
                "qtd_aportes": 0,
                "valor_total_aportado": 0.0,
                "score_soma": 0.0,
            }
        empresas[chave]["qtd_aportes"] += 1
        empresas[chave]["valor_total_aportado"] += valor
        empresas[chave]["score_soma"] += score

    resumo_blocos = []
    for bloco, item in blocos.items():
        qtd = int(item["qtd_aportes"])
        resumo_blocos.append(
            {
                "bloco_liquidez_setorial": bloco,
                "qtd_aportes": qtd,
                "valor_total_aportado": round(float(item["valor_total_aportado"]), 2),
                "score_medio": round(float(item["score_soma"]) / qtd, 4) if qtd else 0.0,
            }
        )

    grupos_empresas = list(empresas.values())
    grupos_empresas.sort(
        key=lambda x: (
            x["bloco_liquidez_setorial"],
            -float(x["valor_total_aportado"]),
            x["empresa_sacada_nome"],
        )
    )
    grupos_empresas = grupos_empresas[:limite_empresas]

    dados_invest_prompt: list[dict[str, Any]] = []
    for g in grupos_empresas:
        qtd = int(g["qtd_aportes"])
        dados_invest_prompt.append(
            {
                "nome_investidor": "INVESTIDOR_LOGADO",
                "nome_empresa": g["empresa_sacada_nome"],
                "bloco_liquidez_setorial": g["bloco_liquidez_setorial"],
                "score_ml": round(float(g["score_soma"]) / qtd, 4) if qtd else 0.0,
                "valor_investido": round(float(g["valor_total_aportado"]), 2),
                "quantidade_aportes": qtd,
            }
        )

    amostra_aportes = dados_bq[:limite_amostra]
    dados_bq_prompt: dict[str, Any] = {
        "meta": {
            "qtd_registros_total": total_registros,
            "qtd_blocos_total": len(resumo_blocos),
            "qtd_grupos_empresa_enviados": len(dados_invest_prompt),
            "qtd_aportes_amostra_enviada": len(amostra_aportes),
            "observacao": (
                "Dados foram compactados para caber no limite de tokens do provedor, "
                "mantendo visão de todos os blocos e empresas agrupadas."
            ),
        },
        "resumo_blocos": resumo_blocos,
        "amostra_aportes": amostra_aportes,
    }

    meta = {
        "qtd_registros_total": total_registros,
        "qtd_blocos_total": len(resumo_blocos),
        "qtd_grupos_empresa_enviados": len(dados_invest_prompt),
        "qtd_aportes_amostra_enviada": len(amostra_aportes),
    }
    return dados_bq_prompt, dados_invest_prompt, meta


def _ler_pdf_referencia(max_chars: int = _MAX_REF_CHARS) -> str:
    texto_pdf_extraido = ""
    if not _PDF_REFERENCIA_PATH.exists():
        logger.info("PDF de referência não encontrado em %s. Seguindo sem few-shot.", _PDF_REFERENCIA_PATH)
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


def _gerar_markdown_chatgroq(
    *,
    nome_cliente: str,
    descricao_cliente: str,
    dados_bq: list[dict[str, Any]],
    dados_invest: list[dict[str, Any]],
) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY não encontrada no ambiente.")

    llm = ChatGroq(
        api_key=SecretStr(api_key),
        model="llama-3.3-70b-versatile",
        temperature=0.1,
        max_tokens=900,
    )

    prompt = ChatPromptTemplate.from_messages([("system", _SYSTEM_TEMPLATE), ("user", _USER_TEMPLATE)])

    tentativas = [
        {"limite_amostra": _MAX_AMOSTRA_APORTES, "limite_empresas": _MAX_GRUPOS_EMPRESA, "max_ref": 2500},
        {"limite_amostra": 30, "limite_empresas": 50, "max_ref": 800},
        {"limite_amostra": 15, "limite_empresas": 25, "max_ref": 0},
        {"limite_amostra": 8, "limite_empresas": 12, "max_ref": 0},
        {"limite_amostra": 4, "limite_empresas": 6, "max_ref": 0},
    ]

    ultimo_erro: Exception | None = None
    for idx, cfg in enumerate(tentativas, start=1):
        dados_bq_prompt, dados_invest_prompt, meta_prompt = _compactar_dados_para_prompt(
            dados_bq,
            limite_amostra=cfg["limite_amostra"],
            limite_empresas=cfg["limite_empresas"],
        )
        for item in dados_invest_prompt:
            item["nome_investidor"] = nome_cliente

        dados_bq_serializado = _to_json_compacto(dados_bq_prompt)
        dados_invest_serializado = _to_json_compacto(dados_invest_prompt)
        texto_referencia = _ler_pdf_referencia(cfg["max_ref"])
        estimativa_tokens = _estimar_tokens_aprox(
            _SYSTEM_TEMPLATE,
            _USER_TEMPLATE,
            dados_bq_serializado,
            dados_invest_serializado,
            texto_referencia,
            nome_cliente,
            descricao_cliente,
        )
        logger.info(
            "Tentativa %d: payload prompt (blocos=%d, grupos_empresas=%d, amostra=%d, ref_chars=%d, tok_aprox=%d).",
            idx,
            meta_prompt["qtd_blocos_total"],
            meta_prompt["qtd_grupos_empresa_enviados"],
            meta_prompt["qtd_aportes_amostra_enviada"],
            len(texto_referencia),
            estimativa_tokens,
        )

        prompt_formatado = prompt.format_messages(
            nome_cliente=nome_cliente,
            descricao_cliente=descricao_cliente,
            dados_bq=dados_bq_serializado,
            dados_invest=dados_invest_serializado,
            texto_do_pdf_referencia=texto_referencia,
        )

        try:
            resposta = llm.invoke(prompt_formatado)
            conteudo = getattr(resposta, "content", "") or ""
            if not str(conteudo).strip():
                raise RuntimeError("A IA retornou uma resposta vazia.")
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


def _gerar_pdf_e_ler_bytes(nome_investidor: str, markdown: str) -> tuple[bytes, str]:
    nome_limpo = re.sub(r"[^a-zA-Z0-9_-]+", "_", nome_investidor).strip("_") or "investidor"
    nome_arquivo = f"Relatorio_Consolidado_{nome_limpo}.pdf"
    caminho_arquivo = os.path.join(str(rx.get_upload_dir()), nome_arquivo)

    css_estilo = """
    @page {
        size: A4 landscape;
        margin: 1.5cm;
    }

    table {
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;      /* força colunas a respeitar a largura da página */
        font-size: 9pt;            /* reduz fonte para caber mais conteúdo */
        word-wrap: break-word;
        overflow-wrap: break-word;
    }

    th, td {
        border: 1px solid black;
        padding: 4px 6px;
        text-align: left;
        word-wrap: break-word;
        overflow-wrap: break-word;
        word-break: break-word;
    }

    th {
        background-color: #f2f2f2;
        font-size: 8pt;
    }

    /* Evita que uma linha da tabela seja cortada entre páginas */
    tr {
        page-break-inside: avoid;
    }

    /* Permite que a tabela quebre entre páginas, mas sem cortar linhas */
    table {
        page-break-inside: auto;
    }

    thead {
        display: table-header-group;  /* repete o cabeçalho em cada página */
    }
    """

    pdf = MarkdownPdf(toc_level=2)
    pdf.add_section(Section(markdown), user_css=css_estilo)
    pdf.save(caminho_arquivo)

    try:
        with open(caminho_arquivo, "rb") as arquivo_pdf:
            conteudo_bytes = arquivo_pdf.read()
    finally:
        if os.path.exists(caminho_arquivo):
            os.remove(caminho_arquivo)

    return conteudo_bytes, nome_arquivo


def gerar_relatorio_consolidado_investidor(documento_investidor: str) -> tuple[bytes, str]:
    documento = _normalizar_documento(documento_investidor)
    if not documento:
        raise ValueError("Não foi possível identificar o investidor logado.")

    nome_investidor = _buscar_nome_investidor(documento)
    dados_bq = _buscar_dados_bigquery_investidor(documento)
    if not dados_bq:
        raise ValueError("Nenhum investimento encontrado para esse investidor no BigQuery.")

    dados_invest = _montar_dados_investimentos(nome_investidor, dados_bq)
    descricao_cliente = (
        "Investidor da Plataforma Clara com análise consolidada de todos os blocos "
        "de liquidez em que possui alocação."
    )

    logger.info(
        "Gerando relatório IA com prompt institucional para %s (%d registros).",
        nome_investidor,
        len(dados_bq),
    )
    markdown = _gerar_markdown_chatgroq(
        nome_cliente=nome_investidor,
        descricao_cliente=descricao_cliente,
        dados_bq=dados_bq,
        dados_invest=dados_invest,
    )
    return _gerar_pdf_e_ler_bytes(nome_investidor, markdown)
