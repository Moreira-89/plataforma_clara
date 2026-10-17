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

## Como a tela fala com o backend

| Passo | Chamada | Situação |
| --- | --- | --- |
| Pedir | `POST /relatorios` devolve `{id, status}` | existe no contrato; hoje responde 501 |
| Acompanhar | `GET /relatorios/{id}` devolve `{id, status}`, com `processando`, `pronto` ou `falhou` | existe no contrato; hoje responde 501 |
| Baixar | `GET /relatorios/{id}/pdf` devolve o arquivo | **ainda não existe** |

!!! warning "O backend ainda não gera relatórios"
    Hoje a tela abre e pede o relatório, mas o backend responde **501** e a tela mostra "A geração de
    relatórios ainda não está disponível". O motivo é que o agente (`agents/relatorio.py`) lê os aportes
    da tabela antiga `tb_aporte`, e a fonte dos dados de aportes ainda não foi decidida (ver o roadmap).
    Quando ela existir, falta ligar os dois endpoints ao agente e criar `GET /relatorios/{id}/pdf`; a tela
    já está pronta para esse contrato e não precisa mudar.
