import { aoMudarSessao, entrar, mensagemDeErro } from '../nucleo/firebase.js'
import { HOME, LOGIN, destinoPorPerfil } from '../nucleo/rotas.js'
import { $, enviando, mostrarMensagem } from '../nucleo/ui.js'

// Com sessão ativa (inclusive logo após entrar), segue para a tela do perfil.
aoMudarSessao(async (usuario) => {
  if (!usuario) return
  const destino = await destinoPorPerfil()
  if (destino === LOGIN) mostrarMensagem('Sua sessão expirou. Entre novamente.', true)
  else if (destino === HOME) mostrarMensagem('Entrou, mas não foi possível carregar o seu perfil. Verifique a conexão com o servidor e tente de novo.', true)
  else window.location.href = destino
})

$('#form-login').addEventListener('submit', async (evento) => {
  evento.preventDefault()
  const formulario = evento.target
  const dados = new FormData(formulario)

  await enviando(formulario, async () => {
    mostrarMensagem('Entrando...')
    try {
      await entrar(dados.get('email'), dados.get('senha'))
    } catch (erro) {
      mostrarMensagem(mensagemDeErro(erro), true)
    }
  })
})
