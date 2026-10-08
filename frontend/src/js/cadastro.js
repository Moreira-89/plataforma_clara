import { chamar, textoDoErro } from './api.js'
import { aoMudarSessao, entrar, mensagemDeErro } from './firebase.js'
import { $, enviando, mostrarMensagem } from './ui.js'

const PAINEL = '/painel.html'

aoMudarSessao((usuario) => {
  if (usuario) window.location.href = PAINEL
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
      window.location.href = PAINEL
    } catch (erro) {
      mostrarMensagem(erro.code ? mensagemDeErro(erro) : 'Não foi possível falar com o servidor.', true)
    }
  })
})
