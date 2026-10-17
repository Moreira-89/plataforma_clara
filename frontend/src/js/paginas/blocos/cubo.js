/*
 * Bloco visual (cubo 3D), feito só com CSS 3D (sem WebGL): como um cubo mágico, em que cada item
 * (aqui, uma empresa do bloco) ocupa uma região proporcional à sua porcentagem. É um componente único:
 * recebe os itens de um bloco e desenha só o que eles dizem.
 *
 * COMO FUNCIONA:
 *   1. O cubo tem 6 faces de 3x3 adesivos: 54 unidades, que representam 100% do dinheiro.
 *   2. Passando de 54 itens, os menores se juntam em "Outras empresas" (`limitarItens`).
 *   3. `distribuirAdesivos` reparte as 54 unidades entre os itens pela participação de cada um
 *      (maior resto), com no mínimo 1 adesivo por item.
 *   4. Os itens recebem os adesivos em sequência, face a face (o maior começa pela face da frente).
 *   5. Itens que repetem a mesma cor ganham, além do tom, uma textura própria (`estilosDosItens`),
 *      para as empresas de um bloco se distinguirem mesmo sendo da mesma cor.
 *   6. Ao aparecer, o cubo surge e os adesivos acendem em sequência (animação em CSS, com `--ordem`).
 *   7. Passar o mouse destaca todos os adesivos do item e chama `aoPassar`; arrastar gira o cubo;
 *      clicar sem arrastar chama `aoClicar` (opcional).
 */
import { criar } from './cartao.js'

const FACES = ['frente', 'direita', 'topo', 'tras', 'esquerda', 'base'] // ordem de preenchimento
const ADESIVOS_POR_FACE = 9
export const TOTAL_DE_ADESIVOS = FACES.length * ADESIVOS_POR_FACE
const TONS = [1, 0.72, 1.28] // variação de brilho entre itens da mesma cor
const PADROES = 8 // texturas diferentes (0 é a cor lisa); ver `data-padrao` em cubo.css
const GIRO_AUTOMATICO = 0.25 // graus por quadro
const SENSIBILIDADE = 0.5 // graus por pixel arrastado
const LIMIAR_DE_ARRASTO = 5 // pixels

// Reparte `total` unidades pelas participações (frações que somam 1); cada uma recebe ao menos 1.
export function distribuirAdesivos(participacoes, total = TOTAL_DE_ADESIVOS) {
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
export function estilosDosItens(itens) {
  const vistos = new Map()
  return itens.map((item) => {
    const n = vistos.get(item.cor) ?? 0
    vistos.set(item.cor, n + 1)
    return { tom: TONS[n % TONS.length], padrao: n % PADROES }
  })
}

// Um adesivo por item, no mínimo: passando de 54 itens, os menores viram "Outras empresas".
function limitarItens(itens) {
  if (itens.length <= TOTAL_DE_ADESIVOS) return itens
  const resto = itens.slice(TOTAL_DE_ADESIVOS - 1)
  return [
    ...itens.slice(0, TOTAL_DE_ADESIVOS - 1),
    { nome: `Outras empresas (${resto.length})`, cor: null, etiqueta: null, participacao: resto.reduce((soma, i) => soma + i.participacao, 0) },
  ]
}

// `entrada`: [{nome, cor, etiqueta, participacao}] do maior para o menor. Devolve a função que encerra o cubo.
export function montarCubo(raiz, entrada, { aoPassar, aoSair, aoClicar }) {
  const itens = limitarItens(entrada)
  const contagens = distribuirAdesivos(itens.map((i) => i.participacao))
  const dono = contagens.flatMap((quantidade, indice) => Array(quantidade).fill(indice))
  const estilos = estilosDosItens(itens)

  const cena = criar('div', 'cubo-cena')
  const cubo = criar('div', 'cubo')
  FACES.forEach((nome, f) => {
    const face = criar('div', `cubo-face cubo-${nome}`)
    for (let c = 0; c < ADESIVOS_POR_FACE; c++) {
      const indice = dono[f * ADESIVOS_POR_FACE + c]
      const adesivo = criar('div', 'cubo-adesivo')
      adesivo.dataset.indice = indice
      adesivo.style.setProperty('--cor', itens[indice].cor ?? 'var(--muted)')
      adesivo.style.setProperty('--tom', estilos[indice].tom)
      adesivo.dataset.padrao = estilos[indice].padrao
      adesivo.style.setProperty('--ordem', f * ADESIVOS_POR_FACE + c)
      face.append(adesivo)
    }
    cubo.append(face)
  })
  cena.append(cubo)
  raiz.replaceChildren(cena)

  let rx = -25
  let ry = -35
  let sobre = null
  let arrastando = false
  let arrastou = false
  let ultimo = null
  let quadro = 0

  const aplicar = () => (cubo.style.transform = `rotateX(${rx}deg) rotateY(${ry}deg)`)
  const girar = () => {
    if (sobre === null && !arrastando) {
      ry += GIRO_AUTOMATICO
      aplicar()
    }
    quadro = requestAnimationFrame(girar)
  }
  const indiceDe = (evento) => {
    const alvo = evento.target.closest?.('.cubo-adesivo')
    return alvo ? Number(alvo.dataset.indice) : null
  }
  // Destaca todos os adesivos do item sob o mouse.
  function destacar(indice) {
    if (indice === sobre) return
    for (const a of cubo.querySelectorAll('.cubo-adesivo.destaque')) a.classList.remove('destaque')
    sobre = indice
    if (indice === null) return aoSair()
    for (const a of cubo.querySelectorAll(`.cubo-adesivo[data-indice="${indice}"]`)) a.classList.add('destaque')
  }

  cena.addEventListener('pointerdown', (e) => {
    arrastando = true
    arrastou = false
    ultimo = [e.clientX, e.clientY]
  })
  cena.addEventListener('pointermove', (e) => {
    if (arrastando) {
      const [dx, dy] = [e.clientX - ultimo[0], e.clientY - ultimo[1]]
      if (!arrastou && Math.hypot(dx, dy) < LIMIAR_DE_ARRASTO) return
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
    const caixa = raiz.getBoundingClientRect()
    aoPassar(itens[indice], e.clientX - caixa.left, e.clientY - caixa.top)
  })
  const soltar = () => (arrastando = false)
  cena.addEventListener('pointerup', soltar)
  cena.addEventListener('pointercancel', soltar)
  cena.addEventListener('pointerleave', () => destacar(null))
  // Clique sem arrastar abre os blocos do item.
  cena.addEventListener('click', (e) => {
    const indice = indiceDe(e)
    if (indice !== null && !arrastou) aoClicar?.(itens[indice])
  })

  aplicar()
  quadro = requestAnimationFrame(girar)
  return () => cancelAnimationFrame(quadro)
}
