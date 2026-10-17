import { chamar, textoDoErro } from '../../nucleo/api.js'
import { aoMudarSessao } from '../../nucleo/firebase.js'
import { montarMenu } from '../../nucleo/menu.js'
import { BLOCOS_INVESTIDOS, LOGIN, destinoDoPerfil, encerrarSeInvalida } from '../../nucleo/rotas.js'
import { $ } from '../../nucleo/ui.js'
import { cnpjFormatado, criar, moeda } from '../blocos/cartao.js'
import { montarCubo } from '../blocos/cubo.js'
import { montarChat } from './chat.js'
import { montarGraficoRendimento } from './grafico-rendimento.js'

const menu = montarMenu('investidor')
const percentual = new Intl.NumberFormat('pt-BR', { style: 'percent', maximumFractionDigits: 1 })
const LIMITE_DO_RANKING = 10

const paraEtiqueta = (etiqueta) => `${BLOCOS_INVESTIDOS}?etiqueta=${encodeURIComponent(etiqueta)}`
const corDe = (etiqueta) => etiqueta.cor ?? 'var(--surface-strong)'

function desenharIndicadores(total, etiquetas) {
  $('#total').textContent = moeda.format(Number(total))
  $('#qtd-etiquetas').textContent = etiquetas.length
  $('#qtd-blocos').textContent = etiquetas.reduce((soma, e) => soma + e.quantidade_blocos, 0)
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
  for (const empresa of empresas.slice(0, LIMITE_DO_RANKING)) {
    const capital = Number(empresa.capital_investido)
    const nome = criar('span', 'empresa')
    const detalhe = criar('small')
    const selo = criar('i', 'selo')
    selo.style.setProperty('--cor', corDe(empresa))
    detalhe.append(selo, `${empresa.ramo_atividade ?? 'Ramo não informado'} · ${empresa.etiqueta}`)
    nome.append(criar('strong', '', empresa.nome_fantasia ?? cnpjFormatado(empresa.cnpj)), detalhe)

    const valores = criar('span', 'valores')
    valores.append(criar('strong', 'numero', moeda.format(capital)), criar('small', '', percentual.format(empresa.participacao)))
    const barra = criar('div', 'barra-fina')
    const preenchimento = criar('i')
    preenchimento.style.setProperty('--largura', `${(capital / maior) * 100}%`)
    barra.append(preenchimento)

    const linha = criar('li', 'linha-ranking')
    linha.append(nome, valores, barra)
    lista.append(linha)
  }
}

// Cada empresa da carteira é uma região do cubo (a fatia dela no dinheiro do investidor).
function desenharCubo(empresas) {
  const dica = $('#dica-cubo')
  const itens = empresas.map((e) => ({
    nome: e.nome_fantasia ?? cnpjFormatado(e.cnpj),
    cor: e.cor,
    etiqueta: e.etiqueta,
    capital: Number(e.capital_investido),
    participacao: e.participacao,
  }))
  try {
    montarCubo($('#cubo'), itens, {
      aoPassar: (item, x, y) => {
        const detalhe = item.capital == null ? percentual.format(item.participacao) : `${moeda.format(item.capital)} · ${percentual.format(item.participacao)}`
        dica.replaceChildren(criar('span', '', item.nome), criar('strong', 'numero', detalhe))
        dica.style.setProperty('--cor-dica', item.cor ?? 'var(--hairline)')
        dica.hidden = false
        dica.style.left = `${x}px`
        dica.style.top = `${y}px`
      },
      aoSair: () => (dica.hidden = true),
      aoClicar: (item) => item.etiqueta && (window.location.href = paraEtiqueta(item.etiqueta)),
    })
  } catch {
    $('#cubo').replaceChildren(criar('p', 'vazio', 'Não foi possível montar o cubo.'))
  }
}

function avisar(texto) {
  const estado = $('#estado')
  estado.textContent = texto
  estado.classList.add('erro')
}

async function carregarRendimento() {
  const resposta = await chamar('GET', '/investimentos/rendimento')
  if (resposta.status !== 200) {
    const estado = $('#grafico-estado')
    estado.textContent = `Não foi possível carregar o rendimento: ${textoDoErro(resposta)}`
    estado.classList.add('erro')
    return
  }
  const { rendimento_total: total, acumulado_percentual: acumulado, meses } = resposta.corpo
  if (!meses.length) return
  $('#rendimento-total').textContent = moeda.format(Number(total))
  $('#rendimento-acumulado').textContent = `${Number(acumulado).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}%`
  montarGraficoRendimento($('#grafico'), $('#dica-grafico'), meses)
}

async function carregarRanking() {
  $('#ranking-estado').textContent = 'Carregando ranking...'
  const resposta = await chamar('GET', '/investimentos/empresas')
  if (resposta.status !== 200) {
    const estado = $('#ranking-estado')
    estado.textContent = `Não foi possível carregar o ranking: ${textoDoErro(resposta)}`
    estado.classList.add('erro')
    return
  }
  desenharRanking(resposta.corpo)
  if (resposta.corpo.length) desenharCubo(resposta.corpo)
}

async function carregar() {
  $('#estado').textContent = 'Carregando sua visão geral...'
  const resposta = await chamar('GET', '/investimentos/resumo')
  if (resposta.status !== 200) {
    avisar(`Não foi possível carregar a sua visão geral: ${textoDoErro(resposta)}`)
    return
  }
  const { total_investido: total, etiquetas } = resposta.corpo
  if (!etiquetas.length) {
    $('#estado').textContent = 'Você ainda não investiu em nenhum bloco.'
    return
  }
  $('#estado').textContent = ''
  const dados = etiquetas.map((e) => ({ ...e, total: Number(e.total_investido) }))
  $('#visao').hidden = false
  desenharIndicadores(total, dados)
  await Promise.all([carregarRendimento(), carregarRanking()])
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
    avisar(`Não foi possível verificar o seu perfil: ${textoDoErro(perfil)}`)
    return
  }
  await carregar()
})
