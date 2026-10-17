/*
 * Bloco visual (cubo 3D em CSS, sem WebGL): como um cubo mágico, em que cada item (uma empresa)
 * ocupa uma região proporcional à sua participação. Componente único: recebe os itens e desenha.
 *
 * COMO FUNCIONA:
 *   1. O cubo tem 6 faces de 3x3 adesivos: 54 unidades, que representam 100%.
 *   2. Passando de 54 itens, os menores se juntam em "Outras empresas" (`limitar`).
 *   3. `distribuir` reparte as 54 unidades pela participação (maior resto), com no mínimo 1 por item.
 *   4. Os itens recebem os adesivos em sequência, face a face (o maior começa pela face da frente).
 *   5. Itens que repetem a mesma cor ganham tom e textura próprios (`estilos`).
 *   6. O giro é por tempo (não por quadro), pausa fora da tela e com a aba oculta; com
 *      `prefers-reduced-motion` o cubo não gira sozinho nem anima a entrada.
 *   7. O balão e o texto de ajuda fazem parte do componente; passar o mouse destaca a região do item.
 *
 * Args (`montarCubo`):
 *   raiz (HTMLElement): Contêiner onde o cubo é montado.
 *   itens (list): [{nome, cor, participacao, detalhe?, etiqueta?}], do maior para o menor.
 *   opcoes ({lado, altura, ajuda, aoClicar}): Tamanho em px, texto de ajuda e clique sem arrastar (opcional).
 *
 * Returns:
 *   {atualizar(itens), encerrar()}: troca os itens (sem repetir a animação de entrada) e para o giro.
 */
import { TONS, criar } from './cartao.js'

const FACES = ['frente', 'direita', 'topo', 'tras', 'esquerda', 'base'] // ordem de preenchimento
const POR_FACE = 9
export const TOTAL_DE_ADESIVOS = FACES.length * POR_FACE
const PADROES = 8 // texturas diferentes (0 é a cor lisa); ver `data-p` em cubo.css
const GRAUS_POR_SEG = 15
const SENSIBILIDADE = 0.5 // graus por pixel arrastado
const LIMIAR = 5 // pixels
const TRANSFORMACOES = {
  frente: 'translateZ(calc(var(--lado) / 2))',
  tras: 'rotateY(180deg) translateZ(calc(var(--lado) / 2))',
  direita: 'rotateY(90deg) translateZ(calc(var(--lado) / 2))',
  esquerda: 'rotateY(-90deg) translateZ(calc(var(--lado) / 2))',
  topo: 'rotateX(90deg) translateZ(calc(var(--lado) / 2))',
  base: 'rotateX(-90deg) translateZ(calc(var(--lado) / 2))',
}

const reduzMovimento = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches

// Reparte `total` unidades pelas participações (frações que somam 1); cada uma recebe ao menos 1.
function distribuir(participacoes, total = TOTAL_DE_ADESIVOS) {
  const cotas = participacoes.map((p) => p * total)
  const contagens = cotas.map((c) => Math.max(1, Math.floor(c)))
  const resto = (i) => cotas[i] - contagens[i]
  const indices = cotas.map((_, i) => i)
  let soma = contagens.reduce((a, b) => a + b, 0)
  while (soma < total) {
    contagens[indices.reduce((a, b) => (resto(b) > resto(a) ? b : a))]++
    soma++
  }
  while (soma > total) {
    const candidatos = indices.filter((i) => contagens[i] > 1)
    contagens[candidatos.reduce((a, b) => (resto(b) < resto(a) ? b : a))]--
    soma--
  }
  return contagens
}

// Tom e textura de cada item: o primeiro de cada cor fica liso; os seguintes alternam tom e textura.
function estilos(itens) {
  const vistos = new Map()
  return itens.map((item) => {
    const n = vistos.get(item.cor) ?? 0
    vistos.set(item.cor, n + 1)
    return { tom: TONS[n % TONS.length], padrao: n % PADROES }
  })
}

// Um adesivo por item, no mínimo: passando de 54 itens, os menores viram "Outras empresas".
function limitar(itens) {
  if (itens.length <= TOTAL_DE_ADESIVOS) return itens
  const resto = itens.slice(TOTAL_DE_ADESIVOS - 1)
  return [
    ...itens.slice(0, TOTAL_DE_ADESIVOS - 1),
    { nome: `Outras empresas (${resto.length})`, cor: null, participacao: resto.reduce((soma, i) => soma + i.participacao, 0) },
  ]
}

const percentual = (p) => `${(p * 100).toLocaleString('pt-BR', { maximumFractionDigits: 2 })}%`

export function montarCubo(raiz, itensIniciais, { lado = 170, altura = 280, ajuda = '', aoClicar } = {}) {
  raiz.classList.add('cubo-bloco-visual')
  raiz.style.setProperty('--lado', `${lado}px`)
  raiz.style.setProperty('--altura', `${altura}px`)
  const palco = criar('div', 'cubo-palco')
  const dica = criar('div', 'cubo-dica')
  dica.hidden = true
  raiz.replaceChildren(palco, dica, criar('p', 'cubo-ajuda', ajuda))

  let itens = []
  let cubo = null
  let rx = -25
  let ry = -35
  let sobre = null
  let arrastando = false
  let arrastou = false
  let visivel = true
  let montado = false
  let quadro = 0
  let ultimoTempo = 0

  const aplicar = () => cubo && (cubo.style.transform = `rotateX(${rx}deg) rotateY(${ry}deg)`)

  function ciclo() {
    const ativo = visivel && !document.hidden && !reduzMovimento() && cubo
    if (!ativo) {
      cancelAnimationFrame(quadro)
      quadro = 0
      return
    }
    if (quadro) return
    ultimoTempo = performance.now()
    const passo = (agora) => {
      const dt = Math.min(64, agora - ultimoTempo)
      ultimoTempo = agora
      if (sobre === null && !arrastando) {
        ry += (GRAUS_POR_SEG * dt) / 1000
        aplicar()
      }
      quadro = requestAnimationFrame(passo)
    }
    quadro = requestAnimationFrame(passo)
  }

  // Destaca todos os adesivos do item sob o mouse.
  function destacar(indice) {
    if (indice === sobre) return
    for (const a of cubo.querySelectorAll('.cubo-adesivo.ligado')) a.classList.remove('ligado')
    sobre = indice
    if (indice === null) {
      dica.hidden = true
      return
    }
    for (const a of cubo.querySelectorAll(`.cubo-adesivo[data-i="${indice}"]`)) a.classList.add('ligado')
  }

  function ligar(cena) {
    let ultimo = null
    const indiceDe = (e) => {
      const adesivo = e.target.closest?.('.cubo-adesivo')
      return adesivo ? Number(adesivo.dataset.i) : null
    }
    cena.addEventListener('pointerdown', (e) => {
      arrastando = true
      arrastou = false
      ultimo = [e.clientX, e.clientY]
    })
    cena.addEventListener('pointermove', (e) => {
      if (arrastando) {
        const dx = e.clientX - ultimo[0]
        const dy = e.clientY - ultimo[1]
        if (!arrastou && Math.hypot(dx, dy) < LIMIAR) return
        if (!arrastou) cena.setPointerCapture(e.pointerId)
        arrastou = true
        ry += dx * SENSIBILIDADE
        rx -= dy * SENSIBILIDADE
        ultimo = [e.clientX, e.clientY]
        aplicar()
        destacar(null)
        return
      }
      const indice = indiceDe(e)
      destacar(indice)
      if (indice === null) return
      const item = itens[indice]
      const caixa = raiz.getBoundingClientRect()
      dica.replaceChildren(criar('span', '', item.nome), criar('strong', '', item.detalhe ?? percentual(item.participacao)))
      dica.style.setProperty('--cor-dica', item.cor ?? 'var(--hairline)')
      dica.style.left = `${e.clientX - caixa.left}px`
      dica.style.top = `${e.clientY - caixa.top}px`
      dica.hidden = false
    })
    const soltar = () => (arrastando = false)
    cena.addEventListener('pointerup', soltar)
    cena.addEventListener('pointercancel', soltar)
    cena.addEventListener('pointerleave', () => destacar(null))
    // Clique sem arrastar.
    cena.addEventListener('click', (e) => {
      const indice = indiceDe(e)
      if (indice !== null && !arrastou) aoClicar?.(itens[indice])
    })
  }

  function montar(novos) {
    itens = limitar(novos)
    sobre = null
    dica.hidden = true
    if (!itens.length) {
      palco.replaceChildren()
      cubo = null
      return
    }
    const contagens = distribuir(itens.map((i) => i.participacao))
    const dono = contagens.flatMap((quantidade, indice) => Array(quantidade).fill(indice))
    const estiloDe = estilos(itens)

    const cena = criar('div', reduzMovimento() || montado ? 'cubo-cena' : 'cubo-cena entra')
    montado = true
    cubo = criar('div', 'cubo')
    FACES.forEach((nome, f) => {
      const face = criar('div', 'cubo-face')
      face.style.transform = TRANSFORMACOES[nome]
      for (let c = 0; c < POR_FACE; c++) {
        const i = dono[f * POR_FACE + c]
        const adesivo = criar('div', 'cubo-adesivo')
        adesivo.dataset.i = i
        adesivo.dataset.p = estiloDe[i].padrao
        adesivo.style.setProperty('--cor', itens[i].cor ?? 'var(--muted)')
        adesivo.style.setProperty('--tom', estiloDe[i].tom)
        adesivo.style.setProperty('--ordem', f * POR_FACE + c)
        face.append(adesivo)
      }
      cubo.append(face)
    })
    cena.append(cubo)
    palco.replaceChildren(cena)
    aplicar()
    ligar(cena)
    cancelAnimationFrame(quadro)
    quadro = 0
    ciclo()
  }

  // Só gira com o cubo visível e a aba aberta.
  const observador = new IntersectionObserver(([entrada]) => {
    visivel = entrada.isIntersecting
    ciclo()
  })
  observador.observe(raiz)
  document.addEventListener('visibilitychange', ciclo)

  let chave = null
  function atualizar(novos) {
    const proxima = JSON.stringify(novos)
    if (proxima === chave) return
    chave = proxima
    montar(novos)
  }
  atualizar(itensIniciais)

  return {
    atualizar,
    encerrar() {
      cancelAnimationFrame(quadro)
      quadro = 0
      observador.disconnect()
      document.removeEventListener('visibilitychange', ciclo)
    },
  }
}
