# Produto

Como a plataforma funciona do ponto de vista de quem usa — sem entrar em qual
tecnologia resolve cada parte. Para isso, ver [Arquitetura](../arquitetura/index.md).

Dois perfis usam a plataforma: **investidor** e **gestora**. Cada um vê uma
versão diferente dos mesmos dados.

## Fluxo do investidor

1. **Login.** O investidor entra com e-mail e senha.
2. **Dashboard.** A primeira tela mostra três números consolidados — quanto
   está alocado no total, o score médio de risco da carteira e quantos
   aportes ele tem — e a mesma informação quebrada por **Bloco de Liquidez**:
   volume, score médio e quantidade de aportes daquele bloco.
3. **Transparência.** Uma tabela mostra, empresa por empresa, em qual bloco o
   dinheiro do investidor está aplicado, o score daquela empresa e o valor.
   É a tela que dá nome ao produto: não existe "confia em mim", existe a
   lista.
4. **Detalhe de um bloco.** Ao entrar num bloco específico, o investidor vê o
   volume total daquele bloco, o score médio, o prazo médio dos recebíveis, e
   a lista de empresas financiadas dentro dele — cada uma com seu peso no
   volume do bloco, o valor e a nota de risco.
5. **Relatório.** O investidor pode pedir um relatório consolidado em PDF,
   escrito em linguagem natural por um assistente de IA, a partir dos dados
   reais da própria carteira dele — não um texto genérico.

## Fluxo da gestora

1. **Login.**
2. **Dashboard consolidado.** A gestora vê a mesma visão por Bloco de
   Liquidez, mas sem filtro de investidor — é o fundo inteiro.
3. **Tabela de empresas.** Uma visão de todas as empresas sacadas (que devem
   os recebíveis) no fundo, com valor total alocado, nota de risco e status
   de adimplência de cada uma.

!!! warning "Como os dados entram no sistema: ainda não definido"
    O fluxo original — a gestora subindo uma planilha manualmente — foi
    removido de propósito: não é assim que a plataforma vai operar com
    usuários reais. A ideia é que os dados venham de uma consulta direta a
    algum sistema que já os tenha, mas **isso ainda não foi desenhado**. É a
    decisão mais urgente do projeto. Ver [Roadmap](../roadmap/index.md).

## O que o score de risco é — e o que não é

O score de risco de cada empresa é a **previsão de um modelo de machine
learning**. A plataforma classifica esse número numa escala de nota (de A+ a C-)
e num status de adimplência, mas hoje **não contém o modelo**: o score entra como
dado pronto. Onde o modelo roda e quem o fornece ainda está a definir.

## Regra de produto: nunca simular sem avisar

Em algum momento a plataforma já mostrou números que pareciam dados reais mas
eram simulados — evolução de patrimônio, rendimento projetado — sem nenhum
rótulo avisando isso. Numa plataforma que se vende pela transparência, número
inventado sem rótulo é o pior defeito possível.

**Regra que fica:** qualquer número exibido ou vem de dado real, ou é
explicitamente rotulado como estimativa. Sem exceção, e sem "por enquanto".
