import { baixarArquivo, chamar, textoDoErro } from '../../nucleo/api.js'
import { aoMudarSessao } from '../../nucleo/firebase.js'
import { montarMenu } from '../../nucleo/menu.js'
import { LOGIN, destinoDoPerfil, encerrarSeInvalida } from '../../nucleo/rotas.js'
import { $ } from '../../nucleo/ui.js'

const menu = montarMenu('investidor')
const INTERVALO_MS = 3000
const MAX_CONSULTAS = 100 // ~5 minutos
const ARQUIVO = 'relatorio-clara.pdf'
let idDoRelatorio = null
let temporizador = null
let pdf = null // { blob, url } do relatório pronto
let faltaArquivo = false // pronto no servidor, mas o PDF ainda não foi carregado

// Etapas mostradas na tela; cada estado marca até onde o pedido chegou.
const ETAPAS = ['solicitado', 'gerando', 'pronto']

function mostrar(etapaAtual, texto, { erro = false, repetir = false } = {}) {
  $('#andamento').hidden = false
  const posicao = ETAPAS.indexOf(etapaAtual)
  const pronto = etapaAtual === 'pronto' && !erro
  document.querySelectorAll('.relatorio-etapas li').forEach((item, i) => {
    const sucesso = pronto && item.dataset.etapa === 'pronto'
    const feita = !sucesso && (i < posicao || pronto)
    const atual = !sucesso && !feita && i === posicao
    item.className = sucesso ? 'sucesso' : feita ? 'feita' : atual ? (erro ? 'erro' : 'atual') : ''
    if (sucesso || atual) item.setAttribute('aria-current', 'step')
    else item.removeAttribute('aria-current')
  })
  $('#relatorio-scan').hidden = pronto || erro
  const mensagem = $('#andamento-texto')
  mensagem.textContent = texto
  mensagem.classList.toggle('erro', erro)
  $('#tentar-de-novo').hidden = !repetir
  $('#gerar').disabled = !(erro || pronto)
}

// Prévia no iframe e botão de download: só ficam ativos com o PDF em mãos.
function mostrarPrevia(arquivo) {
  const frame = $('#previa-frame')
  const aviso = $('#previa-vazia')
  if (pdf) URL.revokeObjectURL(pdf.url)
  pdf = arquivo ? { blob: arquivo, url: URL.createObjectURL(arquivo) } : null
  frame.hidden = !pdf
  aviso.hidden = Boolean(pdf)
  aviso.classList.remove('erro')
  frame.src = pdf ? `${pdf.url}#view=FitH&navpanes=0` : 'about:blank'
  $('#baixar').disabled = !pdf
}

function avisarPrevia(texto) {
  mostrarPrevia(null)
  const aviso = $('#previa-vazia')
  aviso.textContent = texto
  aviso.classList.add('erro')
}

function falhar(texto, etapa = 'gerando') {
  mostrar(etapa, texto, { erro: true, repetir: true })
}

function mostrarErro(resposta, etapa) {
  // 501: o backend ainda não gera relatórios (falta a fonte dos aportes).
  if (resposta.status === 501) falhar(`A geração de relatórios ainda não está disponível. ${textoDoErro(resposta)}`, etapa)
  else falhar(`Não foi possível gerar o relatório: ${textoDoErro(resposta)}`, etapa)
}

async function carregarPdf() {
  faltaArquivo = false
  mostrar('pronto', 'Seu relatório está pronto. Carregando a prévia...')
  const resposta = await baixarArquivo(`/relatorios/${idDoRelatorio}/pdf`)
  if (!resposta.blob) {
    faltaArquivo = true
    avisarPrevia(`Não foi possível carregar a prévia: ${textoDoErro(resposta)}`)
    mostrar('pronto', 'Seu relatório está pronto, mas o arquivo não pôde ser carregado.', { erro: true, repetir: true })
    return
  }
  mostrarPrevia(resposta.blob)
  mostrar('pronto', 'Seu relatório está pronto. Veja a prévia ao lado ou baixe o PDF.')
}

// Devolve true quando o acompanhamento terminou (pronto ou falhou).
function aplicarEstado(corpo) {
  if (corpo.status === 'pronto') carregarPdf()
  else if (corpo.status === 'falhou') falhar(corpo.mensagem ?? 'A geração do relatório falhou. Tente de novo.')
  else {
    mostrar('gerando', 'Estamos gerando o seu relatório. Isso pode levar alguns instantes.')
    return false
  }
  return true
}

async function acompanhar(tentativa = 1) {
  const resposta = await chamar('GET', `/relatorios/${idDoRelatorio}`)
  if (resposta.status !== 200) return mostrarErro(resposta, 'gerando')
  if (aplicarEstado(resposta.corpo)) return
  if (tentativa >= MAX_CONSULTAS) return falhar('O relatório está demorando mais que o normal. Tente de novo mais tarde.')
  temporizador = setTimeout(() => acompanhar(tentativa + 1), INTERVALO_MS)
}

async function gerar() {
  clearTimeout(temporizador)
  faltaArquivo = false
  $('#gerar').disabled = true
  mostrarPrevia(null)
  mostrar('solicitado', 'Enviando o pedido...')
  const resposta = await chamar('POST', '/relatorios')
  if (resposta.status !== 200) return mostrarErro(resposta, 'solicitado')
  idDoRelatorio = resposta.corpo.id
  if (!aplicarEstado(resposta.corpo)) temporizador = setTimeout(() => acompanhar(), INTERVALO_MS)
}

// Baixa o mesmo arquivo da prévia, sem nova chamada ao servidor.
function baixar() {
  if (!pdf) return
  const link = document.createElement('a')
  link.href = pdf.url
  link.download = ARQUIVO
  link.click()
  const botao = $('#baixar')
  botao.textContent = 'PDF baixado'
  setTimeout(() => (botao.textContent = 'Baixar PDF'), 2200)
}

function ligarControles() {
  $('#gerar').addEventListener('click', gerar)
  $('#tentar-de-novo').addEventListener('click', () => (faltaArquivo ? carregarPdf() : gerar()))
  $('#baixar').addEventListener('click', baixar)
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
  ligarControles()
})
