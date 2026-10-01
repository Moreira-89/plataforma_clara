import { chamar, textoDoErro } from './api.js'
import { aoMudarSessao, entrar, mensagemDeErro, obterToken, sair } from './firebase.js'

const $ = (seletor) => document.querySelector(seletor)

const ROTAS = [
  ['GET', '/auth/me'],
  ['GET', '/dashboard/gestora'],
  ['GET', '/dashboard/investidor'],
  ['GET', '/blocos'],
  ['POST', '/relatorios'],
]

function mostrarMensagem(texto, tipo = '') {
  const el = $('#mensagem')
  el.textContent = texto
  el.className = tipo
}

function mostrarResposta(resposta) {
  const el = $('#resposta')
  el.hidden = resposta == null
  el.textContent = resposta == null ? '' : `HTTP ${resposta.status}\n${JSON.stringify(resposta.corpo, null, 2)}`
}

function trocarAba(aba) {
  const entrando = aba === 'entrar'
  $('#form-entrar').hidden = !entrando
  $('#form-cadastrar').hidden = entrando
  $('#aba-entrar').classList.toggle('ativa', entrando)
  $('#aba-cadastrar').classList.toggle('ativa', !entrando)
  mostrarMensagem('')
  mostrarResposta(null)
}

async function tentar(acao) {
  mostrarMensagem('Aguarde...')
  mostrarResposta(null)
  try {
    await acao()
  } catch (erro) {
    mostrarMensagem(erro.code ? mensagemDeErro(erro) : erro.message, 'erro')
  }
}

async function aoEntrar(evento) {
  evento.preventDefault()
  const dados = new FormData(evento.target)
  await tentar(() => entrar(dados.get('email'), dados.get('senha')))
}

async function aoCadastrar(evento) {
  evento.preventDefault()
  const dados = new FormData(evento.target)
  await tentar(async () => {
    const resposta = await chamar(
      'POST',
      '/auth/register',
      {
        nome: dados.get('nome'),
        email: dados.get('email'),
        senha: dados.get('senha'),
        documento: dados.get('documento'),
      },
      { autenticado: false },
    )
    if (resposta.status !== 201) {
      mostrarMensagem(textoDoErro(resposta), 'erro')
      mostrarResposta(resposta)
      return
    }
    // O token já nasce com a claim, porque o backend a define antes de responder.
    await entrar(dados.get('email'), dados.get('senha'))
  })
}

async function chamarRota(metodo, caminho) {
  mostrarMensagem(`${metodo} ${caminho}...`)
  const resposta = await chamar(metodo, caminho)
  const liberado = resposta.status < 400 || resposta.status === 501
  mostrarMensagem(`${metodo} ${caminho} → ${resposta.status}`, liberado ? 'ok' : 'erro')
  mostrarResposta(resposta)
}

async function aoTrocarSessao(usuario) {
  $('#deslogado').hidden = Boolean(usuario)
  $('#logado').hidden = !usuario
  if (!usuario) return

  $('#usuario-email').textContent = usuario.email
  $('#usuario-perfil').textContent = '...'
  // forcar=true: garante o token com a claim mesmo logo depois do cadastro.
  await obterToken(true)
  const resposta = await chamar('GET', '/auth/me')
  if (resposta.status === 200) {
    $('#usuario-perfil').textContent = resposta.corpo.perfil
    mostrarMensagem('Logado.', 'ok')
  } else {
    $('#usuario-perfil').textContent = '—'
    mostrarMensagem(`/auth/me → ${resposta.status}: ${textoDoErro(resposta)}`, 'erro')
  }
  mostrarResposta(resposta)
}

for (const [metodo, caminho] of ROTAS) {
  const botao = document.createElement('button')
  botao.type = 'button'
  botao.textContent = `${metodo} ${caminho}`
  botao.addEventListener('click', () => chamarRota(metodo, caminho))
  $('#rotas').append(botao)
}

$('#aba-entrar').addEventListener('click', () => trocarAba('entrar'))
$('#aba-cadastrar').addEventListener('click', () => trocarAba('cadastrar'))
$('#form-entrar').addEventListener('submit', aoEntrar)
$('#form-cadastrar').addEventListener('submit', aoCadastrar)
$('#sair').addEventListener('click', async () => {
  await sair()
  mostrarMensagem('')
  mostrarResposta(null)
})

aoMudarSessao(aoTrocarSessao)
