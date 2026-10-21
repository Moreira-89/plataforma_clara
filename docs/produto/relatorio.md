# Relatório

O investidor pede, pela tela **Relatório** (item do menu lateral), um relatório consolidado em PDF sobre os
seus investimentos, gerado por inteligência artificial. O relatório é informativo: não traz recomendações
de investimento.

## A tela

1. **Pedido.** Um cartão explica o que é o relatório (situação atual da carteira, movimentações de
   rating e risco de crédito agregado) e tem o botão **Gerar relatório**.
2. **Andamento.** Depois do clique aparece uma faixa de três etapas, **Solicitado**, **Gerando** e
   **Pronto**, com uma mensagem embaixo. A tela consulta o estado a cada 3 segundos, por até cerca de
   5 minutos.
3. **Prévia e download.** Quando o relatório fica pronto, a tela baixa o PDF uma vez e o mostra no painel
   **Prévia do relatório**, à direita, dentro da própria página (o visualizador de PDF do navegador, num
   `iframe`). O botão **Baixar PDF**, no topo desse painel, fica desabilitado até o arquivo estar
   carregado e então baixa o mesmo arquivo, sem nova chamada ao servidor.
4. **Falha.** Se o pedido falha, a tela mostra o motivo em vermelho e o botão **Tentar de novo**.

## De onde vêm os dados

O relatório usa **os mesmos dados que alimentam o cubo e o ranking da Visão geral**: a carteira do
investidor (os blocos em que ele "já investiu", com o valor aplicado em cada um e as empresas de cada
bloco). `api/carteira.py` carrega essa carteira e é usado pelo ranking (`GET /investimentos/empresas`) e
pelo relatório. Não existe mais a tabela `tb_aporte`.

Para o prompt, `agents/relatorio.py` (`aportes_da_carteira`) transforma a carteira em um registro por
**bloco e empresa**, com o capital do investidor na empresa (valor investido no bloco vezes a fatia da
empresa), a data de criação do bloco, o vencimento, o score (0 a 100) e a nota (AAA a D). O prompt traz
a tabela exata das 22 notas com as faixas de score, as mesmas de `domain/risco.py`, para o modelo não
inventar faixas, e uma seção fixa que explica como o score é formado (sem inventar motivos por empresa).

!!! info "Dados de demonstração"
    A carteira é a de demonstração (sorteada de forma estável por conta), com empresas fictícias.
    Os scores vêm de dados públicos reais da CVM (Score de Reputação Clara). O relatório herda isso. Os dados também **não têm data de investimento nem histórico de
    ratings**: o prompt manda o modelo declarar a ausência de movimentações em vez de inventá-las.

## Como a tela fala com o backend

| Passo | Chamada | O que faz |
| --- | --- | --- |
| Pedir | `POST /relatorios` devolve `{id, status}` | Carrega a carteira, registra o pedido e gera o PDF em segundo plano. Sem investimentos, responde 409; se já há um pedido em andamento do mesmo investidor, devolve esse. |
| Acompanhar | `GET /relatorios/{id}` devolve `{id, status, mensagem}`, com `processando`, `pronto` ou `falhou` | Só o dono vê o pedido (outro investidor recebe 404). |
| Baixar | `GET /relatorios/{id}/pdf` devolve o arquivo | 409 enquanto não está pronto ou se falhou. |

A geração (`agents.relatorio.gerar_relatorio_consolidado_investidor`) roda fora do loop do servidor
(`asyncio.to_thread`), chama o Groq com o prompt institucional e converte o Markdown em PDF. Se o Groq
recusar o prompt por tamanho (erro 413), o agente reduz a amostra e tenta de novo, até 5 vezes. Uma
geração leva de alguns segundos a cerca de meio minuto.

## Onde ajustar os prompts

Todo o texto enviado ao modelo está em `backend/app/agents/prompt.py`: o system prompt
(`SYSTEM_TEMPLATE`), a mensagem do usuário com os dados da carteira e a tabela de notas
(`USER_TEMPLATE`) e a descrição do cliente (`DESCRICAO_CLIENTE`). Para mudar o tom, a estrutura do
relatório ou as regras de análise, é só editar esse arquivo; `agents/relatorio.py` só monta e envia as
mensagens. Os templates usam variáveis do Langchain entre chaves (`{dados_bq}`, `{dados_invest}`,
`{texto_do_pdf_referencia}`), que não devem ser renomeadas; uma chave literal precisa ser dobrada.

## Limites conhecidos

- **PDFs só em memória.** Ficam no processo do backend (até 50 pedidos) e somem quando ele reinicia ou
  se houver mais de uma instância. Persistir em storage está no [backlog](../roadmap/backlog.md).
- **Documento de referência ausente.** O agente aceita um PDF de exemplo (few-shot) em
  `backend/app/agents/assets/`, mas ele não está no repositório; sem ele o relatório sai sem o exemplo.
- **Qualidade do texto.** É a de um modelo de linguagem: números e totais do PDF devem ser conferidos
  contra a tela, e o prompt pede valores por extenso e as notas da plataforma, mas isso não é garantia.
