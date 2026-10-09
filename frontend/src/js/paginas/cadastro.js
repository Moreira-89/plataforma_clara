import { chamar, textoDoErro } from '../nucleo/api.js'
import { aoMudarSessao, entrar, mensagemDeErro } from '../nucleo/firebase.js'
import { HOME, LOGIN, destinoPorPerfil } from '../nucleo/rotas.js'
import { $, enviando, mostrarMensagem } from '../nucleo/ui.js'

aoMudarSessao(async (usuario) => {
  if (!usuario) return
  const destino = await destinoPorPerfil()
  if (destino === LOGIN) window.location.href = LOGIN
  else window.location.href = destino
})

$('#form-cadastro').addEventListener('submit', async (evento) => {
  evento.preventDefault()
  const formulario = evento.target
  const dados = new FormData(formulario)

  await enviando(formulario, async () => {
    mostrarMensagem('Criando sua conta...')
    try {
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
        mostrarMensagem(textoDoErro(resposta), true)
        return
      }
      // O backend define o perfil antes de responder, então o token já nasce com ele.
      await entrar(dados.get('email'), dados.get('senha'))
      window.location.href = HOME
    } catch (erro) {
      mostrarMensagem(erro.code ? mensagemDeErro(erro) : 'Não foi possível falar com o servidor.', true)
    }
  })
})
