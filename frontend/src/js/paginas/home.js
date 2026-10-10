import { $ } from '../nucleo/ui.js'

// A home funciona sem o Firebase; ele só troca os botões quando há sessão.
async function mostrarSessao() {
  const { aoMudarSessao, sair } = await import('../nucleo/firebase.js')
  const { chamar } = await import('../nucleo/api.js')
  const { NOVO_BLOCO, encerrarSeInvalida } = await import('../nucleo/rotas.js')

  aoMudarSessao(async (usuario) => {
    if (!usuario) return
    const resposta = await chamar('GET', '/auth/me')
    if (await encerrarSeInvalida(resposta)) return

    const acoes = $('#nav-acoes')
    acoes.replaceChildren()
    if (resposta.status === 200 && resposta.corpo.perfil === 'gestora') {
      const criar = document.createElement('a')
      criar.className = 'btn btn-primario'
      criar.href = NOVO_BLOCO
      criar.textContent = 'Criar bloco de liquidez'
      acoes.append(criar)
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
