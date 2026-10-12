import { $ } from '../nucleo/ui.js'

// A home funciona sem o Firebase; ele só troca os botões quando há sessão.
async function mostrarSessao() {
  const { aoMudarSessao, sair } = await import('../nucleo/firebase.js')
  const { chamar } = await import('../nucleo/api.js')
  const { destinoDoPerfil, encerrarSeInvalida } = await import('../nucleo/rotas.js')

  aoMudarSessao(async (usuario) => {
    if (!usuario) return
    const resposta = await chamar('GET', '/auth/me')
    if (await encerrarSeInvalida(resposta)) return

    const acoes = $('#nav-acoes')
    acoes.replaceChildren()
    if (resposta.status === 200) {
      const gestora = resposta.corpo.perfil === 'gestora'
      const entrar = document.createElement('a')
      entrar.className = 'btn btn-primario'
      entrar.href = destinoDoPerfil(resposta.corpo.perfil)
      entrar.textContent = gestora ? 'Gestão de Blocos' : 'Blocos de Liquidez'
      acoes.append(entrar)
    }
    const botao = document.createElement('button')
    botao.type = 'button'
    botao.className = 'btn btn-contorno-escuro'
    botao.textContent = 'Sair'
    botao.addEventListener('click', async () => {
      await sair()
      window.location.reload()
    })
    acoes.append(botao)
  })
}

mostrarSessao().catch(() => {})
