// Pop-up "Ver mais detalhes" de um bloco, compartilhado pelas telas de blocos.
import { chamar, textoDoErro } from '../../nucleo/api.js'
import { LOGIN, encerrarSeInvalida } from '../../nucleo/rotas.js'
import { $ } from '../../nucleo/ui.js'
import { SEM_SCORE, cnpjFormatado, codigoCurto, criar, dataBr, moeda, rotuloScore, seloEtiqueta } from './cartao.js'
import { estilosDosItens, montarCubo } from './cubo.js'

const percentual = (valor) => `${Number(valor).toLocaleString('pt-BR', { maximumFractionDigits: 2 })}%`

let encerrarCubo = null // para o giro do cubo da ficha anterior

function linha(rotulo, valor) {
  const caixa = criar('div')
  caixa.append(criar('span', '', rotulo), criar('strong', '', valor))
  return caixa
}

// Mesma cor e textura que a empresa tem no cubo, para ligar a linha da tabela à região do cubo.
function amostraDaEmpresa(cor, estilo) {
  const amostra = criar('i', 'amostra-cubo')
  amostra.style.setProperty('--cor', cor ?? 'var(--surface-strong)')
  if (estilo) {
    amostra.style.setProperty('--tom', estilo.tom)
    amostra.dataset.padrao = estilo.padrao
  }
  return amostra
}

// Com `valorInvestido`, a tabela mostra a fatia de cada empresa no bloco e o capital do investidor nela.
function tabelaEmpresas(empresas, valorInvestido, cor, estilos) {
  const jaInvestiu = valorInvestido != null
  const titulos = ['Empresa', 'CNPJ', 'Ramo']
  if (jaInvestiu) titulos.push('% do bloco')
  titulos.push('Capital estimado')
  if (jaInvestiu) titulos.push('Seu capital')
  titulos.push('Score de risco')

  const rolagem = criar('div', 'tabela-detalhe')
  const tabela = criar('table', 'tabela')
  const cabecalho = criar('tr')
  for (const titulo of titulos) cabecalho.append(criar('th', '', titulo))
  const topo = criar('thead')
  topo.append(cabecalho)
  tabela.append(topo)

  const corpo = criar('tbody')
  empresas.forEach((e, i) => {
    const tr = criar('tr')
    const nome = criar('div', 'nome-empresa')
    nome.append(amostraDaEmpresa(cor, estilos[i]), e.nome_fantasia ?? `Empresa ${e.id_empresa}`)
    const celulaNome = criar('td')
    celulaNome.append(nome)
    tr.append(
      celulaNome,
      criar('td', '', cnpjFormatado(e.cnpj)),
      criar('td', '', e.ramo_atividade ?? '—'),
    )
    if (jaInvestiu) tr.append(criar('td', 'numero', percentual(e.percentual_liquidez)))
    tr.append(criar('td', 'numero', moeda.format(Number(e.capital_estimado))))
    if (jaInvestiu) {
      const capitalDele = (Number(valorInvestido) * Number(e.percentual_liquidez)) / 100
      tr.append(criar('td', 'numero', moeda.format(capitalDele)))
    }
    tr.append(criar('td', 'numero', rotuloScore(e.nota_risco, e.score)))
    corpo.append(tr)
  })
  tabela.append(corpo)
  rolagem.append(tabela)
  return rolagem
}

// Bloco visual da ficha: lê as empresas e as porcentagens do bloco aberto.
function secaoBlocoVisual() {
  const secao = criar('section', 'ficha-visual')
  const palco = criar('div', 'cubo-ficha')
  const raiz = criar('div', 'cubo-palco')
  const dica = criar('div', 'dica-cubo')
  dica.hidden = true
  palco.append(raiz, dica, criar('p', 'cubo-ajuda', 'Arraste para girar · passe o mouse para ver a porcentagem de cada empresa'))
  secao.append(criar('h3', '', 'Distribuição do capital entre as empresas'), palco)
  return { secao, raiz, dica }
}

const itensDoBloco = (bloco) =>
  bloco.empresas.map((e) => ({
    nome: e.nome_fantasia ?? cnpjFormatado(e.cnpj),
    cor: bloco.cor,
    etiqueta: bloco.etiqueta,
    participacao: Number(e.percentual_liquidez) / 100,
  }))

function desenharBlocoVisual(visual, itens) {
  encerrarCubo = montarCubo(visual.raiz, itens, {
    aoPassar: (item, x, y) => {
      visual.dica.replaceChildren(criar('span', '', item.nome), criar('strong', 'numero', percentual(item.participacao * 100)))
      visual.dica.style.setProperty('--cor-dica', item.cor ?? 'var(--hairline)')
      visual.dica.hidden = false
      visual.dica.style.left = `${x}px`
      visual.dica.style.top = `${y}px`
    },
    aoSair: () => (visual.dica.hidden = true),
  })
}

// "Alocar dinheiro" ainda não grava nada: só pede e mostra a confirmação do investimento.
function mostrarAlocar(rodape, bloco) {
  const alocar = criar('button', 'btn btn-primario', 'Alocar dinheiro')
  alocar.type = 'button'
  alocar.addEventListener('click', () => pedirConfirmacao(rodape, bloco))
  rodape.replaceChildren(alocar)
}

function pedirConfirmacao(rodape, bloco) {
  const pergunta = criar('p', 'confirmacao-texto', `Confirmar o investimento no bloco ${bloco.etiqueta} (${codigoCurto(bloco.id_bloco)})?`)
  const cancelar = criar('button', 'btn btn-secundario', 'Cancelar')
  cancelar.type = 'button'
  cancelar.addEventListener('click', () => mostrarAlocar(rodape, bloco))
  const confirmar = criar('button', 'btn btn-primario', 'Confirmar investimento')
  confirmar.type = 'button'
  confirmar.addEventListener('click', () => {
    const fechar = criar('button', 'btn btn-secundario', 'Fechar')
    fechar.type = 'button'
    fechar.addEventListener('click', () => $('#detalhe').close())
    rodape.replaceChildren(criar('p', 'confirmacao-texto sucesso-texto', 'Investimento confirmado.'), fechar)
  })
  rodape.replaceChildren(pergunta, cancelar, confirmar)
}

// Opções: `perfil` ('gestora' ou 'investidor') e `valorInvestido` (quando o investidor já investiu).
export async function abrirDetalhe(resumo, { perfil, valorInvestido } = {}) {
  const jaInvestiu = valorInvestido != null
  encerrarCubo?.()
  const dialogo = $('#detalhe')
  const corpo = $('#detalhe-corpo')
  dialogo.classList.toggle('detalhe-largo', jaInvestiu)
  $('#detalhe-titulo').replaceChildren(seloEtiqueta(resumo.cor), criar('span', '', `${resumo.etiqueta} · ${codigoCurto(resumo.id_bloco)}`))
  corpo.replaceChildren(criar('p', 'mensagem', 'Carregando...'))
  dialogo.showModal()

  const resposta = await chamar('GET', `/blocos/${resumo.id_bloco}`)
  if (await encerrarSeInvalida(resposta)) {
    window.location.href = LOGIN
    return
  }
  if (resposta.status !== 200) {
    corpo.replaceChildren(criar('p', 'mensagem erro', `Não foi possível carregar o bloco: ${textoDoErro(resposta)}`))
    return
  }

  const bloco = resposta.corpo
  const resumoDetalhe = criar('div', 'resumo-detalhe')
  resumoDetalhe.append(
    linha('Etiqueta', bloco.etiqueta),
    linha('Data de vencimento', dataBr(bloco.data_vencimento)),
    linha('Score de risco do bloco', rotuloScore(bloco.nota_risco, bloco.score)),
  )
  if (jaInvestiu) {
    const participacao = (Number(valorInvestido) / Number(bloco.capital_total)) * 100
    resumoDetalhe.append(
      linha('Capital total do bloco', moeda.format(Number(bloco.capital_total))),
      linha('Você investiu', moeda.format(Number(valorInvestido))),
      linha('Sua participação no bloco', percentual(participacao)),
    )
  }
  const partes = [resumoDetalhe]

  // Responsável e observação são notas de gestão: só a gestora vê.
  if (perfil === 'gestora') {
    resumoDetalhe.append(linha('Responsável técnico', bloco.responsavel_tecnico), linha('Criado em', dataBr(bloco.data_criacao)))
    if (bloco.observacao) partes.push(criar('p', 'observacao-detalhe', `Observação: ${bloco.observacao}`))
  }

  const visual = secaoBlocoVisual()
  const itens = itensDoBloco(bloco)
  partes.push(visual.secao, tabelaEmpresas(bloco.empresas, valorInvestido, bloco.cor, estilosDosItens(itens)))

  if (perfil === 'investidor' && !jaInvestiu) {
    const rodape = criar('div', 'rodape-detalhe')
    mostrarAlocar(rodape, bloco)
    partes.push(rodape)
  }
  corpo.replaceChildren(...partes)
  desenharBlocoVisual(visual, itens)
}

// Botão de fechar e clique no fundo escuro (fora do conteúdo) fecham o pop-up.
export function ligarDialogoDeDetalhe() {
  const dialogo = $('#detalhe')
  $('#detalhe-fechar').addEventListener('click', () => dialogo.close())
  dialogo.addEventListener('close', () => encerrarCubo?.())
  dialogo.addEventListener('click', (evento) => {
    if (evento.target === dialogo) dialogo.close()
  })
}
