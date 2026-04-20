import os
import PyPDF2
from dotenv import load_dotenv
from pydantic import BaseModel, Field, SecretStr
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from markdown_pdf import MarkdownPdf, Section

# Importações para o BigQuery
from google.cloud import bigquery
from google.oauth2 import service_account

# 1. Configuração do Ambiente
base_dir = os.path.dirname(__file__)
load_dotenv(os.path.join(base_dir, ".env"))

# Caminhos centralizados (evita hardcode repetido e facilita troca de ambiente)
CREDENTIALS_PATH = os.path.join(base_dir, "credentials.json")
PDF_REFERENCIA_PATH = os.path.join(
    os.path.dirname(base_dir),
    "Relatório de Insights Financeiros FIDC - Google Gemini.pdf"
)

# 2. Definição dos Modelos e Estado
class ClienteNuclea(BaseModel):
    nome: str = Field(description="Nome do cliente/investidor") 
    descricao_cliente: str = Field(description="Breve descrição do perfil do cliente")

class RelatorioNucleaState(TypedDict):
    cliente: ClienteNuclea
    dados_bigquery: list  # Dados da tb_aporte (Contexto do Fundo)
    dados_empresas: list  # Dados de Investimentos + Score ML (Contexto do Cliente)
    relatorio_gerado: str


# 3. Nós do LangGraph
def extrair_dados_aporte_bigquery(state: RelatorioNucleaState):
    """Nó que conecta ao BigQuery aplicando as regras de LGPD no SQL (Sem filtro de CNPJ)"""
    if not os.path.exists(CREDENTIALS_PATH):
        print("❌ Arquivo credentials.json não encontrado.")
        return {"dados_bigquery": []}

    try:
        credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH)
        client = bigquery.Client(credentials=credentials, project="plataforma-clara")
        
        # Query sem o WHERE de CNPJ
        query = """
            SELECT 
                id_aporte_uuid,
                bloco_liquidez_setorial,
                valor_aporte_compra,
                data_referencia_competencia,
                status_prazo_vencimento,
                score_risco_interno,
                
                -- BLINDAGEM LGPD: Protegendo o Documento do Sacado
                IF(
                    LENGTH(REGEXP_REPLACE(cnpj_sacado_limpo, r'[^0-9]', '')) <= 11, 
                    '***.***.***-**', 
                    cnpj_sacado_limpo
                ) AS documento_sacado_seguro,
                
                -- BLINDAGEM LGPD: Ocultando Nome de Pessoa Física
                IF(
                    LENGTH(REGEXP_REPLACE(cnpj_sacado_limpo, r'[^0-9]', '')) <= 11, 
                    'Pessoa Física Anonimizada', 
                    empresa_sacada_nome
                ) AS nome_sacado_seguro

            FROM `plataforma-clara.dados_fidc.tb_aporte`
            ORDER BY data_referencia_competencia DESC
            LIMIT 100
        """
        
        query_job = client.query(query)
        resultados_df = query_job.to_dataframe()
        
        if resultados_df.empty:
            print("⚠️ Aviso: Nenhum histórico de aporte encontrado na tb_aporte.")
            return {"dados_bigquery": []}
        
        print(f"✅ Conexão 1/2: {len(resultados_df)} aportes extraídos do BigQuery.")
        return {"dados_bigquery": resultados_df.to_dict(orient="records")}

    except Exception as e:
        print(f"❌ Erro Conexão 1: {e}")
        return {"dados_bigquery": []}


def extrair_investimentos_score(state: RelatorioNucleaState):
    """Segunda Conexão: Traz os investimentos específicos do cliente logado e o Score de ML"""
    # Query para trazer o Nome do Investidor e o Score ML Float
    query = """
        SELECT 
            nome_investidor,
            nome_empresa,
            score_ml,
            valor_investido
        FROM `plataforma-clara.dados_fidc.tb_investimentos_score`
        WHERE nome_investidor = @nome_cliente
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("nome_cliente", "STRING", state["cliente"].nome)]
    )

    try:
        credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH)
        client = bigquery.Client(credentials=credentials, project="plataforma-clara")
        query_job = client.query(query, job_config=job_config)
        res = query_job.to_dataframe().to_dict(orient="records")
        print(f"✅ Conexão 2/2: Investimentos extraídos e validados para o investidor: {state['cliente'].nome}.")
        return {"dados_empresas": res}
    except Exception as e:
        print(f"❌ Erro Conexão 2: {e}")
        return {"dados_empresas": []}


def gerar_relatorio_ia(state: RelatorioNucleaState):
    """Nó que junta tudo e aciona o modelo via Groq"""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY não encontrada.")
        
    # Utilizando um modelo otimizado e válido no Groq para geração de relatórios
    llm = ChatGroq(api_key=SecretStr(api_key), model="llama-3.3-70b-versatile", temperature=0.1)
    
    # =========================================================================
    # INÍCIO DA INSERÇÃO: LENDO O PDF DE EXEMPLO PARA O FEW-SHOT
    # =========================================================================
    caminho_pdf = PDF_REFERENCIA_PATH
    
    texto_pdf_extraido = ""
    try:
        with open(caminho_pdf, "rb") as arquivo_pdf:
            leitor_pdf = PyPDF2.PdfReader(arquivo_pdf)
            for pagina in leitor_pdf.pages:
                texto_pdf_extraido += pagina.extract_text() + "\n"
    except Exception as e:
        print(f"⚠️ Aviso: Não foi possível ler o PDF de exemplo. Erro: {e}")
        texto_pdf_extraido = "Erro ao carregar o exemplo de referência."
    # =========================================================================

    # Detalhes 
    system_template = """
Você é a Insight AI, a inteligência artificial de análise e transparência de FIDCs da Plataforma Clara. 

Sua missão é atuar com a precisão de um Analista de Investimentos Sênior, a visão estratégica de um Diretor de RI (Relações com Investidores) e a capacidade analítica de um Especialista em Data Science. Você redigirá relatórios analíticos personalizados para investidores de grande porte, focados em trazer previsibilidade, segurança, credibilidade e confiança sobre o desempenho dos blocos de liquidez nos quais investem.

<tom_e_estilo>
- Institucional de Alto Padrão: Utilize terminologia avançada do mercado de capitais (ex: duration, yield, default rate, mitigação de risco, arquitetura de capital).
- Transparente e Tecnológico: Reflita a precisão analítica e a segurança estrutural da Plataforma Clara na gestão de ativos na casa dos milhões.
- Estruturação: Organize os dados de forma modular, sofisticada e direta, evitando redundâncias.
</tom_e_estilo>

<contexto_plataforma>
Na Clara, a arquitetura de capital é dividida em blocos de liquidez. Independentemente do setor das empresas que recebem o aporte, cada bloco é batizado exclusivamente com o nome de uma gema ou pedra preciosa (ex: Esmeralda, Safira, Rubi, Ametista, Diamante).
- Objetivo: Transformar ativos complexos e pulverizados (crédito corporativo) em um produto financeiro líquido, elegante e de fácil compreensão, onde a pedra preciosa representa a solidez da operação.
- Mitigação de Risco Sistêmico: O investidor foca na performance do bloco. Se uma empresa de um setor específico enfrenta dificuldades, a saúde do bloco é preservada pelo desempenho pulverizado das demais. Mantenha este conceito claro nas análises de risco.
</contexto_plataforma>

<diretrizes_criticas>
1. COMPLIANCE LGPD (CRÍTICO E INEGOCIÁVEL): O relatório lidará com dados financeiros reais. É ESTRITAMENTE PROIBIDO mencionar CPFs, nomes de pessoas físicas, e-mails pessoais ou telefones diretos. Caso a base de dados (BigQuery) forneça esses dados, você DEVE mascará-los ou omiti-los. Dados de Pessoa Jurídica (CNPJ, Razão Social) são públicos e têm uso permitido.
2. ZERO ALUCINAÇÃO (FIDEDIGNIDADE): Baseie sua análise ÚNICA E EXCLUSIVAMENTE nos dados de entrada fornecidos nas variáveis (BigQuery, status financeiro). Não invente valores, prazos, taxas ou nomes de empresas. Se uma informação não for fornecida, não a presuma.
</diretrizes_criticas>

<regras_de_negocio_score_ml>
Você receberá o campo 'score_ml' de cada empresa, que é um valor Float (0.0 a 100.0). Você deve classificar RIGOROSAMENTE a empresa no nível correspondente abaixo para compor a Matriz de Risco:

- 95.46 a 100.0 -> Nível 1 (AAA) | Excelente | Capacidade máxima de pagamento; risco de crédito inexistente.
- 90.91 a 95.45 -> Nível 2 (AA+) | Muito Superior | Fluxo de caixa robusto; desvio mínimo em relação ao ideal.
- 86.37 a 90.90 -> Nível 3 (AA) | Muito Superior | Histórico consistente; altamente confiável perante credores.
- 81.82 a 86.36 -> Nível 4 (AA-) | Muito Superior | Alta estabilidade financeira; riscos externos marginais.
- 77.28 a 81.81 -> Nível 5 (A+) | Superior | Desempenho sólido; baixa sensibilidade a mudanças de mercado.
- 72.73 a 77.27 -> Nível 6 (A) | Superior | Capacidade financeira forte, mas suscetível a ciclos econômicos.
- 68.19 a 72.72 -> Nível 7 (A-) | Superior | Solvente; vulnerável apenas a crises sistêmicas severas.
- 63.64 a 68.18 -> Nível 8 (BBB+) | Adequado | Cumpre obrigações com segurança; grau de investimento médio.
- 59.10 a 63.63 -> Nível 9 (BBB) | Adequado | Desempenho médio; exige monitoramento de garantias.
- 54.55 a 59.09 -> Nível 10 (BBB-) | Adequado | Limite mínimo para ser considerada uma empresa segura.
- 50.00 a 54.54 -> Nível 11 (BB+) | Alerta | Exposição moderada a falhas; início do grau especulativo.
- 45.46 a 49.99 -> Nível 12 (BB) | Alerta | Fluxo de caixa instável sob pressão macroeconômica.
- 40.91 a 45.45 -> Nível 13 (BB-) | Alerta | Desempenho financeiro irregular e pouco previsível.
- 36.37 a 40.90 -> Nível 14 (B+) | Especulativo | Depende totalmente de condições de mercado favoráveis.
- 31.82 a 36.36 -> Nível 15 (B) | Especulativo | Capacidade de pagamento limitada; alta alavancagem.
- 27.28 a 31.81 -> Nível 16 (B-) | Especulativo | Risco considerável de atraso em parcelas ou juros.
- 22.73 a 27.27 -> Nível 17 (CCC+) | Crítico | Histórico de atrasos; vulnerabilidade financeira alta.
- 18.19 a 22.72 -> Nível 18 (CCC) | Crítico | Necessita de renegociação ou aporte imediato de capital.
- 13.64 a 18.18 -> Nível 19 (CCC-) | Crítico | Inadimplência iminente; probabilidade alta de calote.
- 9.09 a 13.63  -> Nível 20 (CC) | Severo | Quase incapaz de honrar compromissos; em pré-moratória.
- 4.54 a 9.08   -> Nível 21 (C) | Severo | Recuperação judicial ou processo de interrupção em curso.
- 0.00 a 4.53   -> Nível 22 (D) | Inativo | Default (Inadimplência total); falência ou encerramento.
</regras_de_negocio_score_ml>

<formato_de_saida_obrigatorio>
O seu relatório final DEVE ser gerado em Markdown, seguindo estritamente a estrutura abaixo:

# Análise de Liquidez: [Nome do Bloco]

## Alinhamento Estratégico
[Conecte o perfil do cliente informado em {descricao_cliente} com o volume total e a tese de investimento aplicada ao bloco.]

## Análise do Aporte (Data Warehouse)
[Resumo financeiro baseado nos dados de entrada (tb_aporte), focando em volumes alocados, status de liquidação e histórico de performance.]

## Saúde do Bloco de Liquidez
[Avaliação do status geral do bloco (Ex: Esmeralda, Safira) com base na pulverização do risco e adimplência geral dos ativos subjacentes.]
Na Clara, nossa arquitetura de capital é dividida em blocos. Independente do setor de atuação das empresas que recebem o aporte, cada bloco de liquidez é batizado invariavelmente com o nome de uma gema ou pedra preciosa. Mantenha este padrão em todas as referências. Isso permite que a plataforma crie estruturas financeiras padronizadas que podem ser replicadas rapidamente. O investidor ou o sistema foca na performance do bloco e não apenas na volatilidade de um setor específico. 
Mitigação de Risco: Se uma empresa de um setor específico enfrenta dificuldades, a saúde do bloco é preservada pelo desempenho das demais.

IMPORTANTE - Deve-se seguir os exemplo dos padrões abaixo:
    - Esmeralda 
    - Safira
    - Rubi
    - Ametista
    - Diamante

A intenção é transformar ativos complexos e pulverizados (o crédito das empresas) em um produto financeiro líquido, elegante e de fácil compreensão, onde a "pedra preciosa" representa a solidez e a transparência da operação estruturada pela Clara.

## Matriz de Risco e Conclusão
[Analise as empresas do bloco de forma específica, destacando os perfis de risco baseados no Score ML. Para a exibição dos dados, utilize o formato de tabela Markdown exato abaixo, preenchendo as colunas conforme a regra de conversão de Score ML.]

| Nome da Empresa | Bloco de Liquidez | Valor Devido Atual (R$) | Dias de Atraso | Score ML | Nível (Nota) | Classificação | Descrição da Capacidade de Pagamento |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| [Razão Social] | [Nome da Pedra] | [Valor] | [Dias] | [Score numérico] | [Nível + Nota] | [Classificação] | [Descrição da tabela de regras] |

[Conclusão estratégica em 1 a 2 parágrafos reforçando a segurança da gestão da Clara.]
</formato_de_saida_obrigatorio>

<dados_de_entrada>
- Nome do Cliente: {nome_cliente}
- Contexto do Cliente: {descricao_cliente}
- Dados Financeiros do Bloco e Empresas (JSON/Texto BQ): {dados_bq}
</dados_de_entrada>

<referencia_de_excelencia_institucional>
Abaixo, fornecemos a transcrição de um relatório oficial e de alto padrão da Plataforma Clara. 
Você DEVE absorver a arquitetura do texto, a sofisticação do vocabulário, os subtítulos utilizados e a densidade analítica deste documento. Use-o como o SEU ESPELHO ESTRUTURAL (few-shot) para redigir o relatório atual.
=== INÍCIO DO DOCUMENTO DE REFERÊNCIA ===
{texto_do_pdf_referencia}
=== FIM DO DOCUMENTO DE REFERÊNCIA ===
</referencia_de_excelencia_institucional>

Siga as instruções acima, cruze as informações e inicie a geração do relatório.
"""
    
    user_template = """
    DADOS EXTRAÍDOS DO BIGQUERY (tb_aporte higienizada):
    {dados_bq}
    
    DADOS ESPECÍFICOS DO CLIENTE (Investimentos e Score ML):
    {dados_invest}
    
    Gere o relatório estruturado.
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_template),
        ("user", user_template)
    ])
    
    # =========================================================================
    # FIM DA INSERÇÃO: PASSANDO O TEXTO DO PDF PARA A VARIÁVEL DO PROMPT
    # =========================================================================
    prompt_formatado = prompt.format_messages(
        nome_cliente=state["cliente"].nome,
        descricao_cliente=state["cliente"].descricao_cliente,
        dados_bq=state["dados_bigquery"],
        dados_invest=state["dados_empresas"],
        texto_do_pdf_referencia=texto_pdf_extraido # <-- INJETANDO O PDF AQUI
    )
    
    resposta = llm.invoke(prompt_formatado)
    return {"relatorio_gerado": resposta.content}

# 5. Montagem e compilação do Grafo (dentro do guard para evitar execução ao importar)
def criar_app():
    """Monta e compila o grafo LangGraph. Chame esta função para obter a app."""
    workflow = StateGraph(RelatorioNucleaState)

    workflow.add_node("extrair_aporte", extrair_dados_aporte_bigquery)
    workflow.add_node("extrair_investimentos", extrair_investimentos_score)
    workflow.add_node("insight_ai", gerar_relatorio_ia)

    workflow.add_edge(START, "extrair_aporte")
    workflow.add_edge("extrair_aporte", "extrair_investimentos")
    workflow.add_edge("extrair_investimentos", "insight_ai")
    workflow.add_edge("insight_ai", END)

    return workflow.compile()

# --- EXECUÇÃO PRINCIPAL ---
if __name__ == "__main__":
    # 1. Definindo o investidor logado
    # Na produção, este objeto virá do login/sessão do usuário na plataforma Clara
    investidor_logado = ClienteNuclea(
        nome="Arthur Giovanni", 
        descricao_cliente="Investidor de perfil moderado com foco em ativos setoriais de logística."
    )
    
    # 2. Injetando apenas o cliente no estado inicial.
    # Os dados reais serão extraídos do BigQuery e da base de empresas 
    # pelos nós do LangGraph ('extrair_aporte' e 'extrair_investimentos').
    estado_inicial = {
        "cliente": investidor_logado
    }

    # 3. Compilando e executando o grafo
    app_clara = criar_app()

    print(f"Iniciando a esteira Insight AI para {investidor_logado.nome}...\n")
    resultado = app_clara.invoke(estado_inicial)
    
    print("\n" + "="*50)
    print("RELATÓRIO GERADO COM SUCESSO:")
    print("="*50 + "\n")

    # 1. O CSS continua o mesmo
    css_estilo = """
    table {
        width: 100%;
        border-collapse: collapse;
    }
    th, td {
        border: 1px solid black;
        padding: 8px;
        text-align: left;
    }
    th {
        background-color: #f2f2f2;
    }
    """

    # 2. Criar o PDF (Passamos o CSS aqui no construtor principal)
    pdf = MarkdownPdf(toc_level=2) 

    # 3. Adicionar a seção (Apenas o conteúdo, sem o argumento rebelde)
    pdf.add_section(Section(resultado["relatorio_gerado"]), user_css=css_estilo)

    # 4. Salvar PDF exclusivo com nome do cliente
    nome_pdf = f"documento_corrigido_{investidor_logado.nome}.pdf"
    pdf.save(nome_pdf)
    print(f"✅ PDF salvo com sucesso: {nome_pdf}")
