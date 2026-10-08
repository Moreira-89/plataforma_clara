import { chamar, textoDoErro } from './api.js'
import { aoMudarSessao, obterToken, sair } from './firebase.js'
import { $, mostrarMensagem } from './ui.js'

aoMudarSessao(async (usuario) => {
  if (!usuario) {
    window.location.href = '/login.html'
    return
  }

  $('#usuario-email').textContent = usuario.email
  // forcar=true: garante o token com a claim de perfil mesmo logo após o cadastro.
  await obterToken(true)
  const resposta = await chamar('GET', '/auth/me')
  if (resposta.status === 200) {
    $('#usuario-perfil').textContent = resposta.corpo.perfil
  } else {
    $('#usuario-perfil').textContent = '—'
    mostrarMensagem(`Não foi possível ler o perfil: ${textoDoErro(resposta)}`, true)
  }
})

$('#sair').addEventListener('click', async () => {
  await sair()
  window.location.href = '/'
})
