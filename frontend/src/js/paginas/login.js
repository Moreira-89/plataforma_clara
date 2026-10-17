import { chamar, textoDoErro } from '../nucleo/api.js'
import { aoMudarSessao, entrar, mensagemDeErro } from '../nucleo/firebase.js'
import { HOME, LOGIN, VISAO_GERAL, destinoPorPerfil } from '../nucleo/rotas.js'
import { $ } from '../nucleo/ui.js'

const EMAIL_VALIDO = /^\S+@\S+\.\S+$/
let modo = 'login'

// Entrada do painel escuro: sobe uma vez ao carregar (no cadastro e no login igual).
function animarEntrada() {
  const reduzir = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  for (const el of document.querySelectorAll('[data-reveal]')) {
    if (reduzir) {
      el.style.opacity = '1'
      el.style.transform = 'none'
      continue
    }
    const linha = el.dataset.reveal === 'line'
    const quadros = linha
      ? [{ transform: 'translateY(105%)' }, { transform: 'translateY(0)' }]
      : [{ opacity: 0, transform: 'translateY(20px)' }, { opacity: 1, transform: 'translateY(0)' }]
    const animacao = el.animate(quadros, { duration: linha ? 1100 : 800, delay: Number(el.dataset.delay) || 0, easing: 'cubic-bezier(.2,.7,.2,1)', fill: 'both' })
    animacao.onfinish = () => {
      el.style.opacity = '1'
      el.style.transform = 'none'
      animacao.cancel()
    }
  }
}

function mostrarErro(painel, texto) {
  $(`#erro-${painel}`).textContent = texto
}

function irPara(novo) {
  modo = novo
  $('#painel-login').hidden = novo !== 'login'
  $('#painel-cadastro').hidden = novo !== 'cadastro'
  for (const aba of document.querySelectorAll('.aba')) aba.setAttribute('aria-selected', String(aba.dataset.modo === novo))
  mostrarErro('login', '')
  mostrarErro('cadastro', '')
}

// Máscara de CPF (000.000.000-00) ou CNPJ (00.000.000/0000-00), conforme os dígitos.
function mascararDocumento(valor) {
  const d = valor.replace(/\D/g, '').slice(0, 14)
  if (d.length <= 11) return d.replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d{1,2})$/, '$1-$2')
  return d
    .replace(/^(\d{2})(\d)/, '$1.$2')
    .replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3')
    .replace(/\.(\d{3})(\d)/, '.$1/$2')
    .replace(/(\d{4})(\d)/, '$1-$2')
}

// Carregando: o botão fica desabilitado e o rótulo muda.
function carregando(painel, ativo, rotulo) {
  $(`#enviar-${painel}`).disabled = ativo
  $(`#rotulo-${painel}`).textContent = rotulo
}

// Com sessão ativa (inclusive logo após entrar), segue para a tela do perfil.
aoMudarSessao(async (usuario) => {
  if (!usuario) return
  const destino = await destinoPorPerfil()
  if (destino === LOGIN) mostrarErro(modo, 'Sua sessão expirou. Entre novamente.')
  else if (destino === HOME) mostrarErro(modo, 'Entrou, mas não foi possível carregar o seu perfil. Verifique a conexão com o servidor e tente de novo.')
  else window.location.href = destino
})

async function enviarLogin(evento) {
  evento.preventDefault()
  const dados = new FormData(evento.target)
  const email = String(dados.get('email') ?? '')
  const senha = String(dados.get('senha') ?? '')
  if (!EMAIL_VALIDO.test(email)) return mostrarErro('login', 'Informe um e-mail válido.')
  if (!senha) return mostrarErro('login', 'Informe a senha.')

  mostrarErro('login', '')
  carregando('login', true, 'Entrando...')
  try {
    await entrar(email, senha)
  } catch (erro) {
    mostrarErro('login', mensagemDeErro(erro))
  } finally {
    carregando('login', false, 'Entrar')
  }
}

async function enviarCadastro(evento) {
  evento.preventDefault()
  const dados = new FormData(evento.target)
  const nome = String(dados.get('nome') ?? '').trim()
  const email = String(dados.get('email') ?? '')
  const documento = String(dados.get('documento') ?? '')
  const senha = String(dados.get('senha') ?? '')
  const digitos = documento.replace(/\D/g, '').length
  if (!nome) return mostrarErro('cadastro', 'Informe o seu nome.')
  if (!EMAIL_VALIDO.test(email)) return mostrarErro('cadastro', 'Informe um e-mail válido.')
  if (digitos !== 11 && digitos !== 14) return mostrarErro('cadastro', 'O CPF tem 11 dígitos e o CNPJ, 14.')
  if (senha.length < 8) return mostrarErro('cadastro', 'A senha precisa ter pelo menos 8 caracteres.')

  mostrarErro('cadastro', '')
  carregando('cadastro', true, 'Criando conta...')
  try {
    const resposta = await chamar('POST', '/auth/register', { nome, email, senha, documento }, { autenticado: false })
    if (resposta.status !== 201) {
      mostrarErro('cadastro', textoDoErro(resposta))
      return
    }
    // O backend define o perfil antes de responder, então o token já nasce com ele.
    await entrar(email, senha)
    window.location.href = VISAO_GERAL
  } catch (erro) {
    mostrarErro('cadastro', erro.code ? mensagemDeErro(erro) : 'Não foi possível falar com o servidor.')
  } finally {
    carregando('cadastro', false, 'Criar conta')
  }
}

function ligarFormularios() {
  for (const aba of document.querySelectorAll('.aba')) aba.addEventListener('click', () => irPara(aba.dataset.modo))
  for (const link of document.querySelectorAll('[data-ir]')) {
    link.addEventListener('click', (evento) => {
      evento.preventDefault()
      irPara(link.dataset.ir)
    })
  }

  const senha = $('#senha-login')
  const mostrar = $('#mostrar-senha')
  mostrar.addEventListener('click', () => {
    const visivel = senha.type === 'password'
    senha.type = visivel ? 'text' : 'password'
    mostrar.textContent = visivel ? 'Ocultar' : 'Mostrar'
    mostrar.setAttribute('aria-label', visivel ? 'Ocultar senha' : 'Mostrar senha')
  })

  $('#documento').addEventListener('input', (evento) => (evento.target.value = mascararDocumento(evento.target.value)))
  $('#senha-nova').addEventListener('input', (evento) => {
    const tamanho = evento.target.value.length
    const preenchimento = $('#forca-preenchimento')
    preenchimento.style.transform = `scaleX(${Math.min(1, tamanho / 12)})`
    preenchimento.classList.toggle('forte', tamanho >= 8)
  })

  $('#form-login').addEventListener('submit', enviarLogin)
  $('#form-cadastro').addEventListener('submit', enviarCadastro)
}

ligarFormularios()
irPara(new URLSearchParams(window.location.search).get('modo') === 'cadastro' ? 'cadastro' : 'login')
animarEntrada()
