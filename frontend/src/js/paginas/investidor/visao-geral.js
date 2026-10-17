import { chamar, textoDoErro } from '../../nucleo/api.js'
import { aoMudarSessao } from '../../nucleo/firebase.js'
import { montarMenu } from '../../nucleo/menu.js'
import { BLOCOS_INVESTIDOS, LOGIN, destinoDoPerfil, encerrarSeInvalida } from '../../nucleo/rotas.js'
import { $ } from '../../nucleo/ui.js'
import { cnpjFormatado, criar, moeda, percentual } from '../blocos/cartao.js'
import { montarCubo } from '../blocos/cubo.js'
import { montarChat } from './chat.js'
import { montarGraficoRendimento } from './grafico-rendimento.js'

const menu = montarMenu('investidor')
const LIMITE_DO_RANKING = 10
const SEM_COR = 'var(--surface-strong)'

const paraEtiqueta = (etiqueta) => `${BLOCOS_INVESTIDOS}?etiqueta=${encodeURIComponent(etiqueta)}`
const pctFixo = (v, casas = 2) => `${Number(v).toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas })}%`
const nomeDaEmpresa = (e) => e.nome_fantasia ?? cnpjFormatado(e.cnpj)

function avisar(seletor, texto) {
  const estado = $(seletor)
  estado.textContent = texto
  estado.classList.add('erro')
}

// Painel escuro: total, blocos, barra de alocação por etiqueta e legenda.
function desenharTotais(resumo) {
  const { total_investido: total, etiquetas } = resumo
  $('#total').textContent = moeda.format(Number(total))
  $('#qtd-blocos').textContent = etiquetas.reduce((soma, e) => soma + e.quantidade_blocos, 0)

  const barra = $('#aloc-barra')
  const legenda = $('#aloc-legenda')
  barra.replaceChildren()
  legenda.replaceChildren()
  etiquetas.forEach((etiqueta, i) => {
    const cor = etiqueta.cor ?? 'var(--muted)'
    const segmento = criar('i')
    segmento.style.setProperty('--fatia', Number(etiqueta.total_investido))
    segmento.style.setProperty('--cor', cor)
    segmento.style.setProperty('--atraso', `${150 + i * 80}ms`)
    barra.append(segmento)

    const item = criar('li')
    const ponto = criar('i')
    ponto.style.setProperty('--cor', cor)
    item.append(ponto, criar('span', '', etiqueta.etiqueta), criar('span', '', percentual(etiqueta.participacao * 100, 1)))
    legenda.append(item)
  })
}

// Ranking das empresas da carteira (as 10 que mais recebem); o nome cai para o CNPJ sem cadastro.
function desenharRanking(empresas) {
  const lista = $('#ranking')
  lista.replaceChildren()
  if (!empresas.length) {
    $('#ranking-estado').textContent = 'Ainda não há empresas na sua carteira.'
    return
  }
  $('#ranking-estado').textContent = ''
  const maior = Number(empresas[0].capital_investido)
  empresas.slice(0, LIMITE_DO_RANKING).forEach((empresa, i) => {
    const capital = Number(empresa.capital_investido)
    const botao = criar('button')
    botao.type = 'button'
    botao.setAttribute('aria-label', `${nomeDaEmpresa(empresa)}, ${moeda.format(capital)}. Abrir blocos ${empresa.etiqueta}`)
    botao.addEventListener('click', () => (window.location.href = paraEtiqueta(empresa.etiqueta)))

    const posicao = criar('span', i < 3 ? 'posicao destaque' : 'posicao', String(i + 1))
    const nome = criar('span', 'empresa')
    const detalhe = criar('small')
    const ponto = criar('i')
    ponto.style.setProperty('--cor', empresa.cor ?? SEM_COR)
    detalhe.append(ponto, criar('span', '', `${empresa.ramo_atividade ?? 'Ramo não informado'} · ${empresa.etiqueta}`))
    nome.append(criar('strong', '', nomeDaEmpresa(empresa)), detalhe)
    const valores = criar('span', 'valores')
    valores.append(criar('strong', '', moeda.format(capital)), criar('small', '', percentual(empresa.participacao * 100, 1)))
    const trilha = criar('span', 'trilha')
    const preenchimento = criar('i')
    preenchimento.style.setProperty('--largura', capital / maior)
    preenchimento.style.setProperty('--atraso', `${300 + i * 60}ms`)
    trilha.append(preenchimento)

    botao.append(posicao, nome, valores, trilha)
    const item = criar('li')
    item.append(botao)
    lista.append(item)
  })
}

// Cada empresa da carteira é uma região do cubo (a fatia dela no dinheiro do investidor).
function desenharCubo(empresas) {
  const itens = empresas.map((e) => ({
    nome: nomeDaEmpresa(e),
    cor: e.cor,
    etiqueta: e.etiqueta,
    participacao: e.participacao,
    detalhe: `${moeda.format(Number(e.capital_investido))} · ${percentual(e.participacao * 100, 1)}`,
  }))
  montarCubo($('#cubo'), itens, {
    lado: 230,
    altura: 360,
    ajuda: 'Arraste para girar · passe o mouse para ver o valor · clique para abrir os blocos',
    aoClicar: (item) => item.etiqueta && (window.location.href = paraEtiqueta(item.etiqueta)),
  })
}

async function carregarRendimento() {
  const resposta = await chamar('GET', '/investimentos/rendimento')
  if (resposta.status !== 200) {
    avisar('#grafico-estado', `Não foi possível carregar o rendimento: ${textoDoErro(resposta)}`)
    return
  }
  const { rendimento_total: total, acumulado_percentual: acumulado, meses } = resposta.corpo
  if (!meses.length) return
  $('#rendimento-total').textContent = moeda.format(Number(total))
  $('#rendimento-acumulado').textContent = pctFixo(acumulado)
  montarGraficoRendimento($('#grafico'), meses)
}

async function carregarEmpresas() {
  $('#ranking-estado').textContent = 'Carregando ranking...'
  const resposta = await chamar('GET', '/investimentos/empresas')
  if (resposta.status !== 200) {
    avisar('#ranking-estado', `Não foi possível carregar o ranking: ${textoDoErro(resposta)}`)
    return
  }
  desenharRanking(resposta.corpo)
  if (resposta.corpo.length) desenharCubo(resposta.corpo)
}

async function carregar() {
  $('#estado').textContent = 'Carregando sua visão geral...'
  const resposta = await chamar('GET', '/investimentos/resumo')
  if (resposta.status !== 200) {
    avisar('#estado', `Não foi possível carregar a sua visão geral: ${textoDoErro(resposta)}`)
    return
  }
  if (!resposta.corpo.etiquetas.length) {
    $('#estado').textContent = 'Você ainda não investiu em nenhum bloco.'
    return
  }
  $('#estado').textContent = ''
  $('#visao').hidden = false
  desenharTotais(resposta.corpo)
  await Promise.all([carregarRendimento(), carregarEmpresas()])
}

aoMudarSessao(async (usuario) => {
  if (!usuario) {
    window.location.href = LOGIN
    return
  }
  const perfil = await chamar('GET', '/auth/me')
  if (await encerrarSeInvalida(perfil)) {
    window.location.href = LOGIN
    return
  }
  if (perfil.status === 200 && perfil.corpo.perfil !== 'investidor') {
    window.location.href = destinoDoPerfil(perfil.corpo.perfil)
    return
  }
  menu.definirUsuario(usuario.email)
  $('#conteudo').hidden = false
  montarChat()
  if (perfil.status !== 200) {
    avisar('#estado', `Não foi possível verificar o seu perfil: ${textoDoErro(perfil)}`)
    return
  }
  await carregar()
})
