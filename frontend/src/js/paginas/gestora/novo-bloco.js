/*
 * Formulário de criação de bloco, aberto num pop-up da Gestão de Blocos.
 *
 * COMO FUNCIONA:
 *   1. A gestora busca empresas (nome fantasia ou CNPJ), marca várias e as adiciona à tabela.
 *   2. Em cada empresa, digita a porcentagem do capital; "Realocado", "Disponível" e a barra mostram quanto falta,
 *      e "Dividir igualmente" reparte 100% de uma vez.
 *   3. O bloco só pode ser criado com as porcentagens somando exatamente 100%.
 *   4. A prévia do bloco visual (cubo) se atualiza conforme as porcentagens mudam.
 */
import { chamar, textoDoErro } from '../../nucleo/api.js'
import { $ } from '../../nucleo/ui.js'
import { cnpjFormatado, criar, moeda, percentual } from '../blocos/cartao.js'
import { montarCubo } from '../blocos/cubo.js'

const ATRASO_BUSCA = 300
const MAX_RESULTADOS = 8
const ETIQUETA_INICIAL = 'Diamante'

let etiquetas = []
let linhas = [] // empresas já na tabela: { id, empresa, pct } (pct é o texto digitado, ex.: "12,5")
const marcadas = new Map() // marcadas na busca, ainda não adicionadas; sobrevivem a novas buscas
let encontradas = []
let capitalCentavos = 0
let temporizador
let previa = null
let aoCriarBloco = () => {}
let iniciado = false

// "1.234,5" -> 1234.5
const numero = (texto) => {
  const n = Number.parseFloat(String(texto).replace(/\./g, '').replace(',', '.'))
  return Number.isFinite(n) ? n : 0
}
const capitalTotal = () => capitalCentavos / 100
const capitalParaApi = () => `${Math.floor(capitalCentavos / 100)}.${String(capitalCentavos % 100).padStart(2, '0')}`
const somaPercentuais = () => Math.round(linhas.reduce((soma, l) => soma + numero(l.pct), 0) * 100) / 100
const etiquetaEscolhida = () => etiquetas.find((e) => e.nome === $('#etiqueta').value)

// Máscara de moeda: os dígitos viram centavos (digitar 123456 mostra R$ 1.234,56).
function aoDigitarCapital(evento) {
  const digitos = evento.target.value.replace(/\D/g, '').replace(/^0+/, '')
  capitalCentavos = digitos ? Number(digitos) : 0
  evento.target.value = capitalCentavos ? moeda.format(capitalCentavos / 100) : ''
  mudou()
}

function formularioValido() {
  const vencimento = $('#data-vencimento')
  return (
    somaPercentuais() === 100 &&
    capitalCentavos > 0 &&
    vencimento.value &&
    vencimento.value >= vencimento.min &&
    $('#responsavel').value.trim() &&
    linhas.every((l) => numero(l.pct) > 0)
  )
}

function atualizarCubo() {
  const comPercentual = linhas.filter((l) => numero(l.pct) > 0)
  $('#previa-cubo').hidden = !comPercentual.length
  if (!comPercentual.length) return
  const etiqueta = etiquetaEscolhida()
  const total = comPercentual.reduce((soma, l) => soma + numero(l.pct), 0) || 1
  const itens = comPercentual.map((l) => ({
    nome: l.empresa.nome_fantasia,
    cor: etiqueta?.cor ?? null,
    participacao: numero(l.pct) / total,
    detalhe: percentual(numero(l.pct)),
  }))
  if (previa) previa.atualizar(itens)
  else previa = montarCubo($('#previa-cubo-raiz'), itens, { lado: 130, altura: 220, ajuda: 'Atualiza conforme você distribui o capital' })
}

// Atualiza tudo o que depende das porcentagens, do capital e da etiqueta, sem refazer a tabela.
function mudou() {
  const soma = somaPercentuais()
  const excedido = soma > 100
  const completo = soma === 100
  const realocado = $('#realocado')
  realocado.textContent = percentual(soma)
  realocado.classList.toggle('excedido', excedido)
  realocado.classList.toggle('completo', completo)
  $('#disponivel').textContent = percentual(Math.max(0, 100 - soma))
  const barra = $('#barra-alocacao')
  barra.style.transform = `scaleX(${Math.min(1, soma / 100)})`
  barra.classList.toggle('excedido', excedido)
  barra.classList.toggle('completo', completo)
  $('#dividir').hidden = linhas.length < 2

  for (const l of linhas) {
    const celula = document.querySelector(`[data-capital="${CSS.escape(l.id)}"]`)
    if (celula) celula.textContent = moeda.format((capitalTotal() * numero(l.pct)) / 100)
  }
  if (excedido && !$('#mensagem').dataset.erroFixo) $('#mensagem').textContent = 'As porcentagens passam de 100%.'
  else if (!excedido && !$('#mensagem').dataset.erroFixo) $('#mensagem').textContent = ''
  $('#salvar').disabled = !formularioValido()

  const etiqueta = etiquetaEscolhida()
  $('#selo-cor').style.background = etiqueta?.cor ?? ''
  atualizarCubo()
}

function mostrarErro(texto) {
  const mensagem = $('#mensagem')
  mensagem.textContent = texto
  if (texto) mensagem.dataset.erroFixo = '1'
  else delete mensagem.dataset.erroFixo
}

// Qualquer alteração limpa o erro anterior.
function aoAlterar() {
  mostrarErro('')
  mudou()
}

function desenharTabela() {
  const corpo = $('#corpo-tabela')
  corpo.replaceChildren()
  $('#tabela-vazia').hidden = linhas.length > 0

  for (const linha of linhas) {
    const { id, empresa } = linha
    const tr = criar('tr')
    const celula = (texto, classe) => criar('td', classe ?? '', texto)
    tr.append(celula(empresa.nome_fantasia), celula(cnpjFormatado(empresa.cnpj), 'mono'), celula(empresa.ramo_atividade))

    const capital = celula('', 'mono direita')
    capital.dataset.capital = id
    tr.append(capital)

    const entrada = criar('input')
    entrada.setAttribute('inputmode', 'decimal')
    entrada.setAttribute('aria-label', `Porcentagem para ${empresa.nome_fantasia}`)
    entrada.value = linha.pct
    entrada.addEventListener('input', () => {
      // Só dígitos e uma vírgula, com até 2 casas.
      linha.pct = entrada.value.replace(/[^\d,]/g, '').replace(/(,.*?),/g, '$1').replace(/(,\d{2})\d+$/, '$1')
      entrada.value = linha.pct
      aoAlterar()
    })
    const campo = criar('span', 'campo-pct')
    campo.append(entrada, criar('span', '', '%'))
    const tdPct = criar('td', 'celula-pct')
    tdPct.append(campo)
    tr.append(tdPct)

    const remover = criar('button', 'remover', '×')
    remover.type = 'button'
    remover.setAttribute('aria-label', `Remover ${empresa.nome_fantasia}`)
    remover.addEventListener('click', () => {
      linhas = linhas.filter((l) => l.id !== id)
      desenharTabela()
      aoAlterar()
    })
    const tdRemover = criar('td', 'celula-remover')
    tdRemover.append(remover)
    tr.append(tdRemover)

    corpo.append(tr)
  }
  mudou()
}

function atualizarBotaoAdicionar() {
  $('#adicionar').disabled = marcadas.size === 0
}

// Chips com as empresas marcadas, em qualquer busca; o × desmarca.
function desenharSelecionadas() {
  const lista = $('#selecionadas')
  lista.replaceChildren()
  lista.hidden = marcadas.size === 0
  for (const [id, empresa] of marcadas) {
    const item = criar('li', '', empresa.nome_fantasia)
    const remover = criar('button', '', '×')
    remover.type = 'button'
    remover.setAttribute('aria-label', `Desmarcar ${empresa.nome_fantasia}`)
    remover.addEventListener('click', () => {
      marcadas.delete(id)
      desenharSelecionadas()
      desenharResultados()
    })
    item.append(remover)
    lista.append(item)
  }
  atualizarBotaoAdicionar()
}

function desenharResultados() {
  const lista = $('#resultados')
  lista.replaceChildren()
  const livres = encontradas.filter((e) => !linhas.some((l) => l.id === e.id_empresa)).slice(0, MAX_RESULTADOS)
  lista.hidden = livres.length === 0
  for (const empresa of livres) {
    const rotulo = criar('label')
    const caixa = criar('input')
    caixa.type = 'checkbox'
    caixa.checked = marcadas.has(empresa.id_empresa)
    caixa.addEventListener('change', () => {
      if (caixa.checked) marcadas.set(empresa.id_empresa, empresa)
      else marcadas.delete(empresa.id_empresa)
      desenharSelecionadas()
    })
    const nome = criar('span', '', empresa.nome_fantasia)
    nome.append(criar('small', '', `${empresa.ramo_atividade} · ${empresa.nota_risco ? `Nota ${empresa.nota_risco}` : 'Sem score'}`))
    rotulo.append(caixa, nome, criar('small', '', cnpjFormatado(empresa.cnpj)))
    const item = criar('li')
    item.append(rotulo)
    lista.append(item)
  }
}

async function buscar() {
  const texto = $('#busca-empresa').value.trim()
  const estado = $('#busca-estado')
  estado.classList.remove('erro')
  encontradas = []
  desenharResultados()
  if (texto.length < 2) {
    estado.textContent = ''
    return
  }
  estado.textContent = 'Buscando...'
  const resposta = await chamar('GET', `/empresas?busca=${encodeURIComponent(texto)}`)
  if (resposta.status === 200) {
    encontradas = resposta.corpo
    const livres = encontradas.filter((e) => !linhas.some((l) => l.id === e.id_empresa))
    estado.textContent = livres.length ? '' : 'Nenhuma empresa encontrada.'
    desenharResultados()
  } else {
    estado.textContent = resposta.status === 503 ? 'O cadastro de empresas está indisponível.' : textoDoErro(resposta)
    estado.classList.add('erro')
  }
}

function adicionarMarcadas() {
  for (const [id, empresa] of marcadas) linhas.push({ id, empresa, pct: '' })
  marcadas.clear()
  $('#busca-empresa').value = ''
  encontradas = []
  $('#busca-estado').textContent = ''
  desenharSelecionadas()
  desenharResultados()
  desenharTabela()
  aoAlterar()
}

// Reparte 100% igualmente; a primeira empresa leva o resto dos centésimos.
function dividirIgualmente() {
  const n = linhas.length
  const base = Math.floor(10000 / n) / 100
  const resto = Math.round((100 - base * n) * 100) / 100
  linhas.forEach((l, k) => (l.pct = String(k === 0 ? Math.round((base + resto) * 100) / 100 : base).replace('.', ',')))
  desenharTabela()
  aoAlterar()
}

function limparFormulario() {
  $('#form-bloco').reset()
  $('#etiqueta').value = etiquetas.some((e) => e.nome === ETIQUETA_INICIAL) ? ETIQUETA_INICIAL : etiquetas[0]?.nome
  capitalCentavos = 0
  marcadas.clear()
  encontradas = []
  linhas = []
  desenharSelecionadas()
  desenharResultados()
  desenharTabela()
  $('#contador-observacao').textContent = '0 / 500'
  mostrarErro('')
  mudou()
}

async function criarBloco(evento) {
  evento.preventDefault()
  if (!formularioValido()) {
    mostrarErro('Revise os dados: as porcentagens precisam fechar 100%.')
    return
  }
  const dados = new FormData($('#form-bloco'))
  $('#salvar').disabled = true
  const resposta = await chamar('POST', '/blocos', {
    etiqueta: dados.get('etiqueta'),
    capital_total: capitalParaApi(),
    data_vencimento: dados.get('data_vencimento'),
    responsavel_tecnico: dados.get('responsavel_tecnico'),
    observacao: dados.get('observacao'),
    empresas: linhas.map((l) => ({ id_empresa: l.id, percentual_liquidez: numero(l.pct).toFixed(2) })),
  })

  if (resposta.status === 201) {
    limparFormulario()
    aoCriarBloco(resposta.corpo)
  } else {
    mostrarErro(textoDoErro(resposta))
    $('#salvar').disabled = !formularioValido()
  }
}

async function iniciar() {
  const resposta = await chamar('GET', '/blocos/etiquetas')
  if (resposta.status !== 200) {
    mostrarErro('Não foi possível carregar as etiquetas.')
    return false
  }
  etiquetas = resposta.corpo
  const seletor = $('#etiqueta')
  for (const { nome } of etiquetas) seletor.append(new Option(nome, nome))
  seletor.value = etiquetas.some((e) => e.nome === ETIQUETA_INICIAL) ? ETIQUETA_INICIAL : etiquetas[0]?.nome

  // O vencimento tem de ser depois de hoje.
  $('#data-vencimento').min = new Date(Date.now() + 24 * 3600 * 1000).toISOString().slice(0, 10)

  $('#etiqueta').addEventListener('change', aoAlterar)
  $('#data-vencimento').addEventListener('input', aoAlterar)
  $('#responsavel').addEventListener('input', aoAlterar)
  $('#capital-total').addEventListener('input', aoDigitarCapital)
  $('#observacao').addEventListener('input', (e) => {
    $('#contador-observacao').textContent = `${e.target.value.length} / 500`
  })
  $('#busca-empresa').addEventListener('input', () => {
    clearTimeout(temporizador)
    temporizador = setTimeout(buscar, ATRASO_BUSCA)
  })
  $('#adicionar').addEventListener('click', adicionarMarcadas)
  $('#dividir').addEventListener('click', dividirIgualmente)
  $('#form-bloco').addEventListener('submit', criarBloco)
  desenharTabela()
  return true
}


// Chamado a cada abertura do pop-up; a primeira vez carrega as etiquetas e liga os eventos.
export async function prepararFormulario({ aoCriar }) {
  aoCriarBloco = aoCriar
  if (!iniciado) iniciado = await iniciar()
  return iniciado
}
