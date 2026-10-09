import { chamar, textoDoErro } from '../../nucleo/api.js'
import { aoMudarSessao, sair } from '../../nucleo/firebase.js'
import { HOME, LOGIN, encerrarSeInvalida } from '../../nucleo/rotas.js'
import { $, mostrarMensagem } from '../../nucleo/ui.js'

const ATRASO_BUSCA = 300
const LIMITE_DIGITOS = 13 // até R$ 9.999.999.999.999
const TOTAL = 10000 // 100,00% em centésimos, para somar sem erro de ponto flutuante
const moeda = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })

const empresas = new Map() // id_empresa -> { dados, centesimos }
let etiquetas = []
let encontradas = []
let temporizador

const formatarCnpj = (c) =>
  c.length === 14 ? c.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5') : c

const paraCentesimos = (texto) => Math.round(Number(texto) * 100) || 0
const formatarPercentual = (centesimos) =>
  `${(centesimos / 100).toLocaleString('pt-BR', { maximumFractionDigits: 2 })}%`

let capitalCentavos = 0

const capitalTotal = () => capitalCentavos / 100

// Formata o que foi digitado em BRL: separador de milhar sempre, vírgula e até 2 casas.
function formatarCapital(texto) {
  const [inteiro = '', ...resto] = texto.replace(/[^\d,]/g, '').split(',')
  const reais = inteiro.replace(/^0+(?=\d)/, '').slice(0, LIMITE_DIGITOS)
  const temVirgula = texto.includes(',')
  if (!reais && !temVirgula) return { texto: '', centavos: 0 }
  const decimais = resto.join('').slice(0, 2)
  const parteInteira = Number(reais || 0).toLocaleString('pt-BR')
  return {
    texto: `R$ ${parteInteira}${temVirgula ? `,${decimais}` : ''}`,
    centavos: Number(reais || 0) * 100 + Number(decimais.padEnd(2, '0')),
  }
}

// Reaplica a máscara a cada tecla, mantendo o cursor junto dos mesmos dígitos.
function aoDigitarCapital(evento) {
  const campo = evento.target
  const digitosAntesDoCursor = campo.value.slice(0, campo.selectionStart).replace(/[^\d,]/g, '').length
  const { texto, centavos } = formatarCapital(campo.value)
  capitalCentavos = centavos
  campo.value = texto

  let vistos = 0
  let posicao = texto.length
  if (digitosAntesDoCursor === 0) posicao = texto.length ? 3 : 0
  else {
    for (let i = 0; i < texto.length; i++) {
      if (/[\d,]/.test(texto[i]) && ++vistos === digitosAntesDoCursor) {
        posicao = i + 1
        break
      }
    }
  }
  campo.setSelectionRange(posicao, posicao)
  atualizarResumo()
}

// Ao sair do campo, completa as duas casas: R$ 1.000.000,00.
function aoSairDoCapital(evento) {
  evento.target.value = capitalCentavos ? moeda.format(capitalCentavos / 100) : ''
}

const capitalParaApi = () => `${Math.floor(capitalCentavos / 100)}.${String(capitalCentavos % 100).padStart(2, '0')}`

function somaCentesimos() {
  let soma = 0
  for (const { centesimos } of empresas.values()) soma += centesimos
  return soma
}

function atualizarResumo() {
  const soma = somaCentesimos()
  const realocado = $('#realocado')
  const disponivel = $('#disponivel')
  realocado.textContent = formatarPercentual(soma)
  disponivel.textContent = formatarPercentual(TOTAL - soma)
  realocado.classList.toggle('excedido', soma > TOTAL)
  disponivel.classList.toggle('excedido', soma > TOTAL)
  disponivel.classList.toggle('completo', soma === TOTAL)

  for (const [id, { centesimos }] of empresas) {
    const celula = document.querySelector(`[data-capital="${CSS.escape(id)}"]`)
    if (celula) celula.textContent = centesimos ? moeda.format((capitalTotal() * centesimos) / TOTAL) : '—'
  }
  validar()
}

function validar() {
  const formulario = $('#form-bloco')
  const dados = new FormData(formulario)
  const completo =
    dados.get('etiqueta') &&
    capitalTotal() > 0 &&
    dados.get('data_vencimento') &&
    String(dados.get('responsavel_tecnico')).trim() &&
    empresas.size > 0 &&
    somaCentesimos() === TOTAL &&
    [...empresas.values()].every((e) => e.centesimos > 0)
  $('#salvar').disabled = !completo
}

function desenharTabela() {
  const corpo = $('#corpo-tabela')
  corpo.replaceChildren()
  $('#tabela-vazia').hidden = empresas.size > 0

  for (const [id, { dados, centesimos }] of empresas) {
    const linha = document.createElement('tr')
    const celula = (texto) => {
      const td = document.createElement('td')
      td.textContent = texto
      return td
    }
    linha.append(celula(dados.nome_fantasia), celula(formatarCnpj(dados.cnpj)), celula(dados.ramo_atividade))

    const capital = celula('—')
    capital.dataset.capital = id
    capital.classList.add('numero')
    linha.append(capital)

    const entrada = document.createElement('input')
    entrada.type = 'number'
    entrada.min = '0.01'
    entrada.max = '100'
    entrada.step = '0.01'
    entrada.value = centesimos ? String(centesimos / 100) : ''
    entrada.setAttribute('aria-label', `Porcentagem de ${dados.nome_fantasia}`)
    entrada.addEventListener('input', () => {
      empresas.get(id).centesimos = paraCentesimos(entrada.value)
      atualizarResumo()
    })
    const tdPercentual = document.createElement('td')
    tdPercentual.append(entrada)
    linha.append(tdPercentual)

    const remover = document.createElement('button')
    remover.type = 'button'
    remover.className = 'remover'
    remover.textContent = '×'
    remover.setAttribute('aria-label', `Remover ${dados.nome_fantasia}`)
    remover.addEventListener('click', () => {
      empresas.delete(id)
      desenharTabela()
      atualizarResumo()
    })
    const tdRemover = document.createElement('td')
    tdRemover.append(remover)
    linha.append(tdRemover)

    corpo.append(linha)
  }
  atualizarResumo()
}

function desenharResultados() {
  const lista = $('#resultados')
  lista.replaceChildren()
  const livres = encontradas.filter((e) => !empresas.has(e.id_empresa))
  lista.hidden = livres.length === 0
  for (const empresa of livres) {
    const item = document.createElement('li')
    const rotulo = document.createElement('label')
    const caixa = document.createElement('input')
    caixa.type = 'checkbox'
    caixa.value = empresa.id_empresa
    caixa.addEventListener('change', () => {
      $('#adicionar').disabled = lista.querySelectorAll('input:checked').length === 0
    })
    const nome = document.createElement('span')
    nome.textContent = empresa.nome_fantasia
    const cnpj = document.createElement('small')
    cnpj.textContent = formatarCnpj(empresa.cnpj)
    rotulo.append(caixa, nome, cnpj)
    item.append(rotulo)
    lista.append(item)
  }
  $('#adicionar').disabled = true
}

async function buscar() {
  const texto = $('#busca').value.trim()
  const estado = $('#busca-estado')
  encontradas = []
  desenharResultados()
  if (texto.length < 2) {
    estado.textContent = ''
    return
  }
  estado.textContent = 'Buscando...'
  estado.classList.remove('erro')
  const resposta = await chamar('GET', `/empresas?busca=${encodeURIComponent(texto)}`)
  if (resposta.status === 200) {
    encontradas = resposta.corpo
    estado.textContent = encontradas.length ? '' : 'Nenhuma empresa livre encontrada.'
    desenharResultados()
  } else {
    estado.textContent = resposta.status === 503 ? 'O cadastro de empresas está indisponível.' : textoDoErro(resposta)
    estado.classList.add('erro')
  }
}

function adicionarSelecionadas() {
  const marcadas = new Set([...document.querySelectorAll('#resultados input:checked')].map((c) => c.value))
  for (const empresa of encontradas) {
    if (marcadas.has(empresa.id_empresa)) empresas.set(empresa.id_empresa, { dados: empresa, centesimos: 0 })
  }
  $('#busca').value = ''
  encontradas = []
  desenharResultados()
  $('#busca-estado').textContent = ''
  desenharTabela()
}

function atualizarEtiqueta() {
  const escolhida = etiquetas.find((e) => e.nome === $('#etiqueta').value)
  $('#selo-cor').style.background = escolhida ? escolhida.cor : ''
  const slug = (escolhida?.nome ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').toUpperCase().replace(/[^A-Z0-9]+/g, '_')
  $('#codigo-previa').textContent = escolhida ? `Código: BLOCO_${slug}_… (número gerado ao salvar)` : 'Código: gerado ao salvar'
  validar()
}

function limparFormulario() {
  $('#form-bloco').reset()
  capitalCentavos = 0
  empresas.clear()
  desenharTabela()
  atualizarEtiqueta()
  $('#contador-observacao').textContent = '0 / 500'
}

async function criarBloco(evento) {
  evento.preventDefault()
  const dados = new FormData($('#form-bloco'))
  const botao = $('#salvar')
  botao.disabled = true
  mostrarMensagem('Criando o bloco...')
  $('#sucesso').hidden = true

  const resposta = await chamar('POST', '/blocos', {
    etiqueta: dados.get('etiqueta'),
    capital_total: capitalParaApi(),
    data_vencimento: dados.get('data_vencimento'),
    responsavel_tecnico: dados.get('responsavel_tecnico'),
    observacao: dados.get('observacao'),
    empresas: [...empresas].map(([id, { centesimos }]) => ({
      id_empresa: id,
      percentual_liquidez: (centesimos / 100).toFixed(2),
    })),
  })

  if (resposta.status === 201) {
    mostrarMensagem('')
    const bloco = resposta.corpo
    const aviso = $('#sucesso')
    aviso.textContent = `Bloco criado: ${bloco.codigo_identificacao}`
    aviso.hidden = false
    limparFormulario()
  } else {
    mostrarMensagem(textoDoErro(resposta), true)
    validar()
  }
}

async function iniciar() {
  const resposta = await chamar('GET', '/blocos/etiquetas')
  if (resposta.status !== 200) {
    mostrarMensagem('Não foi possível carregar as etiquetas.', true)
    return
  }
  etiquetas = resposta.corpo
  const seletor = $('#etiqueta')
  seletor.append(new Option('Selecione a etiqueta', ''))
  for (const { nome } of etiquetas) seletor.append(new Option(nome, nome))

  const amanha = new Date(Date.now() + 24 * 3600 * 1000)
  $('#data-vencimento').min = amanha.toISOString().slice(0, 10)

  $('#etiqueta').addEventListener('change', atualizarEtiqueta)
  $('#form-bloco').addEventListener('input', validar)
  $('#capital-total').addEventListener('input', aoDigitarCapital)
  $('#capital-total').addEventListener('blur', aoSairDoCapital)
  $('#observacao').addEventListener('input', (e) => {
    $('#contador-observacao').textContent = `${e.target.value.length} / 500`
  })
  $('#busca').addEventListener('input', () => {
    clearTimeout(temporizador)
    temporizador = setTimeout(buscar, ATRASO_BUSCA)
  })
  $('#adicionar').addEventListener('click', adicionarSelecionadas)
  $('#form-bloco').addEventListener('submit', criarBloco)
  desenharTabela()
}

$('#sair').addEventListener('click', async () => {
  await sair()
  window.location.href = '/'
})

aoMudarSessao(async (usuario) => {
  if (!usuario) {
    window.location.href = LOGIN
    return
  }
  const perfil = await chamar('GET', '/auth/me')
  if (await encerrarSeInvalida(perfil)) return
  if (perfil.status === 200 && perfil.corpo.perfil !== 'gestora') {
    window.location.href = HOME
    return
  }
  $('#conteudo').hidden = false
  if (perfil.status !== 200) {
    $('#form-bloco').hidden = true
    $('#erro-pagina').textContent = `Não foi possível verificar o seu perfil: ${textoDoErro(perfil)}`
    $('#erro-pagina').hidden = false
    return
  }
  await iniciar()
})
