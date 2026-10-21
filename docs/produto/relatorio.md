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
inventar faixas.

**Histórico do score (upgrades e downgrades).** O endpoint `POST /relatorios` também lê
`backend/dados/scores_empresas_historico.csv` (`storage/scores.py`, `carregar_historico_recente`),
com o score e os pontos de cada critério por empresa e mês. O arquivo vem do SQL 15
(`dados_fidc.tb_score_empresas_historico`), que recalcula o score para cada mês do Informe Mensal com a
mesma regra do score atual. Só os dois meses mais recentes entram no relatório: cada registro recebe o
score e os pontos do mês anterior. Sem o arquivo, o relatório diz que ainda não há histórico.

**Números calculados pelo código.** `agents/analise_carteira.py` calcula todos os números do relatório:
- indicadores e tendência no mês (só com as empresas que têm score nos dois meses, para não misturar
  mudança de nota com mudança de composição);
- saúde por bloco;
- distribuição do capital por faixa;
- upgrades e downgrades, com o critério que mais mudou (ou a trava);
- as 8 maiores posições.

`relatorio.conteudo_oficial` junta esses números. O PDF os mostra em cartões, tabelas e gráfico, e o
modelo recebe **só eles**, com a ordem de citá-los como estão. A IA escreve o texto; o código faz as contas.

!!! info "Dados de demonstração"
    A carteira é a de demonstração (sorteada de forma estável por conta), com empresas fictícias.
    Os scores vêm de dados públicos reais da CVM (Score de Reputação Clara). O relatório herda isso.
    A carteira não tem data de investimento: as movimentações comparam a nota de cada empresa entre os
    dois meses mais recentes do Informe Mensal, não desde a entrada do investidor.

## O PDF

`agents/layout_pdf.py` monta o documento em pé (A4), com o design system da Clara:
- cabeçalho escuro com a logo;
- ondas em três tons de azul no rodapé;
- fontes Inter e JetBrains Mono (em `agents/assets/`, licença OFL, ver `FONTES.md`).

A ordem das seções é fixa:
1. Cartões: capital, empresas, score ponderado e nota.
2. Resumo Executivo da Carteira.
3. Saúde dos Blocos (tabela).
4. Distribuição de Capital por Risco (barra grau de investimento × especulativo, legenda e régua do
   score).
5. Destaques do Mês (tabela de upgrades e downgrades, até 8 em cada sentido).
6. Principais Empresas da Carteira (tabela).
7. Conclusão.
8. Como o Score é Calculado, o aviso, a fonte e a nota de LGPD (texto fixo).

Tabelas e gráficos saem do código. O texto de cada seção vem da IA; se ela pular uma seção, entra um
texto padrão do código. Os blocos aparecem como "Etiqueta · CÓDIGO", como no site, porque há
etiquetas repetidas.

## Como a tela fala com o backend

| Passo | Chamada | O que faz |
| --- | --- | --- |
| Pedir | `POST /relatorios` devolve `{id, status}` | Carrega a carteira, registra o pedido e gera o PDF em segundo plano. Sem investimentos, responde 409; se já há um pedido em andamento do mesmo investidor, devolve esse. |
| Acompanhar | `GET /relatorios/{id}` devolve `{id, status, mensagem}`, com `processando`, `pronto` ou `falhou` | Só o dono vê o pedido (outro investidor recebe 404). |
| Baixar | `GET /relatorios/{id}/pdf` devolve o arquivo | 409 enquanto não está pronto ou se falhou. |

A geração (`agents.relatorio.gerar_relatorio_consolidado_investidor`) roda fora do loop do servidor
(`asyncio.to_thread`), chama o Groq com o prompt institucional e converte o Markdown em PDF. Se o Groq
recusar o prompt por tamanho (erro 413), o agente tenta de novo com menos itens para a IA, até 4 vezes.
Os cortes são:
1. sem o texto de referência;
2. com 5 movimentações e 5 empresas;
3. com 3 de cada.

O PDF não muda com esses cortes. O plano gratuito do Groq aceita 8.000 tokens por minuto; o pedido de uma
carteira de 9 blocos e 97 empresas fica perto de 6 mil. Gerar dois relatórios no mesmo minuto pode dar
erro de limite (429): basta esperar 1 minuto. Uma geração leva de alguns segundos a cerca de meio minuto.

## Onde ajustar os prompts

Todo o texto enviado ao modelo está em `backend/app/agents/prompt.py`: o system prompt
(`SYSTEM_TEMPLATE`), a mensagem do usuário com os dados da carteira e a tabela de notas
(`USER_TEMPLATE`) e a descrição do cliente (`DESCRICAO_CLIENTE`). Para mudar o tom, a estrutura do
relatório ou as regras de análise, é só editar esse arquivo; `agents/relatorio.py` só monta e envia as
mensagens. O prompt define o tom (institucional, falando com o investidor), as 6 seções de texto e as
regras: citar os números como vêm, não inventar fatos, motivos ou efeitos sobre liquidez, e não
recomendar. Os templates usam variáveis do Langchain entre chaves (`{dados_bq}`,
`{texto_do_pdf_referencia}`), que não devem ser renomeadas; uma chave literal precisa ser dobrada.

## Limites conhecidos

- **PDFs só em memória.** Ficam no processo do backend (até 50 pedidos) e somem quando ele reinicia ou
  se houver mais de uma instância. Persistir em storage está no [backlog](../roadmap/backlog.md).
- **Documento de referência ausente.** O agente aceita um PDF de exemplo (few-shot) em
  `backend/app/agents/assets/`, mas ele não está no repositório; sem ele o relatório sai sem o exemplo.
- **Qualidade do texto.** Os números das tabelas, dos cartões e do gráfico vêm do código e estão
  certos. O texto é de um modelo de linguagem: nos testes, ele às vezes ainda ignora uma regra de tom.
  Exemplos: falar de liquidez ou terminar com um quase-conselho ("demanda atenção"). Mais proibições no
  prompt gastam tokens e não garantem o resultado.
- **Próximo passo (futuro).** Quebrar o prompt em um pedido por seção, cada um só com os seus dados, e
  fazer o código conferir notas e faixas citadas antes de montar o PDF.
