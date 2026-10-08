import { aoMudarSessao, entrar, mensagemDeErro } from './firebase.js'
import { $, enviando, mostrarMensagem } from './ui.js'

const PAINEL = '/painel.html'

aoMudarSessao((usuario) => {
  if (usuario) window.location.href = PAINEL
})

$('#form-login').addEventListener('submit', async (evento) => {
  evento.preventDefault()
  const formulario = evento.target
  const dados = new FormData(formulario)

  await enviando(formulario, async () => {
    mostrarMensagem('Entrando...')
    try {
      await entrar(dados.get('email'), dados.get('senha'))
      window.location.href = PAINEL
    } catch (erro) {
      mostrarMensagem(mensagemDeErro(erro), true)
    }
  })
})
