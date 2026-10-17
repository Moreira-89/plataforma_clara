import { $ } from '../nucleo/ui.js'

const EASE = 'cubic-bezier(.2,.7,.2,1)'

// Revelação no scroll: uma animação WAAPI pausada por elemento, tocada uma vez ao entrar na tela.
// Só transform e opacity (compostos na GPU); nada de layout a cada quadro.
function revelarNoScroll() {
  const elementos = [...document.querySelectorAll('[data-reveal]')]
  const reduzir = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  if (reduzir || !('IntersectionObserver' in window)) {
    for (const el of elementos) {
      el.style.opacity = '1'
      el.style.transform = 'none'
    }
    return
  }

  const animacoes = new Map()
  const observador = new IntersectionObserver(
    (entradas) => {
      for (const entrada of entradas) {
        if (!entrada.isIntersecting) continue
        for (const animacao of animacoes.get(entrada.target) ?? []) animacao.play()
        observador.unobserve(entrada.target)
      }
    },
    { rootMargin: '0px 0px -8% 0px', threshold: 0.01 },
  )

  const alturaDaJanela = window.innerHeight
  for (const el of elementos) {
    const linha = el.dataset.reveal === 'line'
    // Observa o contêiner: as linhas ficam recortadas pelo pai e o observador não as veria.
    const alvo = linha ? el.parentElement : el
    const quadros = linha
      ? [{ transform: 'translateY(105%)' }, { transform: 'translateY(0)' }]
      : [{ opacity: 0, transform: 'translateY(28px)' }, { opacity: 1, transform: 'translateY(0)' }]
    const animacao = el.animate(quadros, { duration: linha ? 1100 : 900, delay: Number(el.dataset.delay) || 0, easing: EASE, fill: 'both' })
    animacao.pause()
    animacao.onfinish = () => {
      el.style.opacity = '1'
      el.style.transform = 'none'
      animacao.cancel()
    }
    if (alvo.getBoundingClientRect().top < alturaDaJanela) {
      animacao.play()
      continue
    }
    animacoes.set(alvo, [...(animacoes.get(alvo) ?? []), animacao])
    observador.observe(alvo)
  }
}

// Texto que "acende" conforme a leitura: um único gradiente recortado no texto, atualizado em rAF.
function acenderTexto() {
  const trechos = [...document.querySelectorAll('[data-fill]')]
  if (!trechos.length || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
  let quadro = 0
  const atualizar = () => {
    if (quadro) return
    quadro = requestAnimationFrame(() => {
      quadro = 0
      const altura = window.innerHeight
      for (const trecho of trechos) {
        const caixa = trecho.getBoundingClientRect()
        const progresso = Math.min(1, Math.max(0, (altura * 0.85 - caixa.top) / (caixa.height + altura * 0.25)))
        trecho.style.backgroundPosition = `${(1 - progresso) * 100}% 0`
      }
    })
  }
  window.addEventListener('scroll', atualizar, { passive: true })
  atualizar()
}

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
      const entrar = document.createElement('a')
      entrar.className = 'topo-criar'
      entrar.href = destinoDoPerfil(resposta.corpo.perfil)
      entrar.textContent = resposta.corpo.perfil === 'gestora' ? 'Gestão de Blocos' : 'Visão geral'
      acoes.append(entrar)
    }
    const botao = document.createElement('button')
    botao.type = 'button'
    botao.className = 'topo-entrar'
    botao.textContent = 'Sair'
    botao.addEventListener('click', async () => {
      await sair()
      window.location.reload()
    })
    acoes.append(botao)
  })
}

revelarNoScroll()
acenderTexto()
mostrarSessao().catch(() => {})
