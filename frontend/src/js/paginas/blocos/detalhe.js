// Ficha do bloco (pop-up "Ver mais detalhes"), compartilhada pelas telas de blocos.
import { chamar, textoDoErro } from '../../nucleo/api.js'
import { LOGIN, encerrarSeInvalida } from '../../nucleo/rotas.js'
import { $ } from '../../nucleo/ui.js'
import { TONS, cnpjFormatado, codigoCurto, criar, dataBr, moeda, percentual, rotuloScore, seloEtiqueta } from './cartao.js'
import { montarCubo } from './cubo.js'

// Texturas da amostra de cada empresa na tabela (mesma ordem das do cubo): [imagem, tamanho].
const TEXTURAS = [
  ['none', 'auto'],
  ['repeating-linear-gradient(45deg,rgba(255,255,255,.5) 0 4px,rgba(0,0,0,.3) 4px 8px)', 'auto'],
  ['radial-gradient(rgba(255,255,255,.5) 2px,transparent 2.5px)', '8px 8px'],
  ['linear-gradient(rgba(255,255,255,.5) 2px,transparent 2px),linear-gradient(90deg,rgba(0,0,0,.3) 2px,transparent 2px)', '8px 8px'],
  ['repeating-linear-gradient(0deg,rgba(0,0,0,.3) 0 3px,rgba(255,255,255,.5) 3px 6px)', 'auto'],
  ['repeating-linear-gradient(45deg,rgba(255,255,255,.5) 0 2px,transparent 2px 6px)', 'auto'],
  ['repeating-linear-gradient(90deg,rgba(255,255,255,.5) 0 3px,rgba(0,0,0,.3) 3px 6px)', 'auto'],
  ['conic-gradient(rgba(0,0,0,.3) 25%,rgba(255,255,255,.5) 0 50%,rgba(0,0,0,.3) 0 75%,rgba(255,255,255,.5) 0)', '8px 8px'],
]

let cuboDaFicha = null // para o giro do cubo da ficha anterior

function tile(rotulo, valor) {
  const caixa = criar('div')
  caixa.append(criar('span', '', rotulo), criar('strong', '', valor))
  return caixa
}

// Mesma cor e textura que a empresa tem no cubo, para ligar a linha da tabela à região do cubo.
function amostraDaEmpresa(cor, i) {
  const amostra = criar('i', 'amostra-empresa')
  const [textura, tamanho] = TEXTURAS[i % TEXTURAS.length]
  amostra.setAttribute('aria-hidden', 'true')
  amostra.style.backgroundColor = cor ?? 'var(--surface-strong)'
  amostra.style.backgroundImage = textura
  amostra.style.backgroundSize = tamanho
  amostra.style.filter = `brightness(${TONS[i % TONS.length]})`
  return amostra
}

// Com `valorInvestido`, a tabela mostra a fatia de cada empresa no bloco e o capital do investidor nela.
function tabelaEmpresas(bloco, valorInvestido) {
  const jaInvestiu = valorInvestido != null
  const colunas = [{ titulo: 'Empresa' }, { titulo: 'CNPJ' }, { titulo: 'Ramo' }]
  if (jaInvestiu) colunas.push({ titulo: '% do bloco', direita: true })
  colunas.push({ titulo: 'Capital estimado', direita: true })
  if (jaInvestiu) colunas.push({ titulo: 'Seu capital', direita: true })
  colunas.push({ titulo: 'Score de risco', direita: true })

  const rolagem = criar('div', 'tabela-rolagem')
  const tabela = criar('table', 'tabela')
  const cabecalho = criar('tr')
  for (const { titulo, direita } of colunas) cabecalho.append(criar('th', direita ? 'direita' : '', titulo))
  const topo = criar('thead')
  topo.append(cabecalho)

  const corpo = criar('tbody')
  bloco.empresas.forEach((e, i) => {
    const nome = criar('span', 'nome-empresa')
    nome.append(amostraDaEmpresa(bloco.cor, i), e.nome_fantasia ?? `Empresa ${e.id_empresa}`)
    const celulaNome = criar('td')
    celulaNome.append(nome)

    const linha = criar('tr')
    linha.append(celulaNome, criar('td', 'mono', cnpjFormatado(e.cnpj)), criar('td', '', e.ramo_atividade ?? '—'))
    const numerica = (texto) => linha.append(criar('td', 'mono direita', texto))
    if (jaInvestiu) numerica(percentual(e.percentual_liquidez))
    numerica(moeda.format(Number(e.capital_estimado)))
    if (jaInvestiu) numerica(moeda.format((Number(valorInvestido) * Number(e.percentual_liquidez)) / 100))
    numerica(rotuloScore(e.nota_risco, e.score))
    corpo.append(linha)
  })
  tabela.append(topo, corpo)
  rolagem.append(tabela)
  return rolagem
}

// Seção do bloco visual: lê as empresas e as porcentagens do bloco aberto.
function secaoBlocoVisual(bloco) {
  const secao = criar('section', 'ficha-visual')
  const caixa = criar('div', 'ficha-cubo')
  const raiz = criar('div')
  secao.append(criar('h3', '', 'Distribuição do capital entre as empresas'), caixa)
  caixa.append(raiz)
  const itens = bloco.empresas.map((e) => ({
    nome: e.nome_fantasia ?? cnpjFormatado(e.cnpj),
    cor: bloco.cor,
    etiqueta: bloco.etiqueta,
    participacao: Number(e.percentual_liquidez) / 100,
    detalhe: percentual(e.percentual_liquidez),
  }))
  return { secao, montar: () => (cuboDaFicha = montarCubo(raiz, itens, { lado: 170, altura: 280, ajuda: 'Arraste para girar · passe o mouse para ver a porcentagem de cada empresa' })) }
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
  const dialogo = $('#detalhe')
  const corpo = $('#detalhe-corpo')
  cuboDaFicha?.encerrar()
  dialogo.classList.toggle('ficha-larga', perfil === 'investidor')
  $('#detalhe-titulo').replaceChildren(seloEtiqueta(resumo.cor), criar('span', '', `${resumo.etiqueta} · ${codigoCurto(resumo.id_bloco)}`))
  corpo.replaceChildren(criar('p', 'mensagem', 'Carregando...'))
  document.body.style.overflow = 'hidden'
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
  const resumoDetalhe = criar('div', 'ficha-resumo')
  resumoDetalhe.append(
    tile('Etiqueta', bloco.etiqueta),
    tile('Data de vencimento', dataBr(bloco.data_vencimento)),
    tile('Score de risco do bloco', rotuloScore(bloco.nota_risco, bloco.score)),
  )
  if (jaInvestiu) {
    const participacao = (Number(valorInvestido) / Number(bloco.capital_total)) * 100
    resumoDetalhe.append(
      tile('Capital total do bloco', moeda.format(Number(bloco.capital_total))),
      tile('Você investiu', moeda.format(Number(valorInvestido))),
      tile('Sua participação no bloco', percentual(participacao)),
    )
  }
  const partes = [resumoDetalhe]

  // Responsável e observação são notas de gestão: só a gestora vê.
  if (perfil === 'gestora') {
    resumoDetalhe.append(tile('Responsável técnico', bloco.responsavel_tecnico), tile('Criado em', dataBr(bloco.data_criacao)))
    if (bloco.observacao) partes.push(criar('p', 'ficha-obs', `Observação: ${bloco.observacao}`))
  }

  const visual = secaoBlocoVisual(bloco)
  partes.push(visual.secao, tabelaEmpresas(bloco, valorInvestido))

  if (perfil === 'investidor' && !jaInvestiu) {
    const rodape = criar('div', 'ficha-rodape')
    mostrarAlocar(rodape, bloco)
    partes.push(rodape)
  }
  corpo.replaceChildren(...partes)
  visual.montar()
}

// Botão de fechar e clique no fundo escuro (fora do conteúdo) fecham o pop-up; ao fechar, a página volta a rolar.
export function ligarDialogoDeDetalhe() {
  const dialogo = $('#detalhe')
  $('#detalhe-fechar').addEventListener('click', () => dialogo.close())
  dialogo.addEventListener('click', (evento) => {
    if (evento.target === dialogo) dialogo.close()
  })
  dialogo.addEventListener('close', () => {
    cuboDaFicha?.encerrar()
    document.body.style.overflow = ''
  })
}
