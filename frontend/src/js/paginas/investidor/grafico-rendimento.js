/*
 * Gráfico do rendimento mensal dos últimos 12 meses: barras (R$ por mês) e linha (% acumulado).
 *
 * COMO FUNCIONA:
 *   1. As barras mostram o rendimento de cada mês em R$ (eixo da esquerda); a linha, o acumulado em % (direita).
 *   2. O SVG desenha barras, linha e pontos; os rótulos dos eixos e dos meses são HTML por cima, em porcentagem.
 *   3. Passar o mouse sobre um mês destaca a barra e o ponto, apaga as outras barras e mostra um balão.
 *   4. A entrada anima as barras (crescem), a linha (se desenha) e some com `prefers-reduced-motion`.
 */
import { criar, moeda, moedaCompacta } from '../blocos/cartao.js'

const NS = 'http://www.w3.org/2000/svg'
const L = 760
const A = 280
const M = { e: 76, d: 52, t: 16, b: 34 }
const DIVISOES = 4

const pctFixo = (v, casas = 2) => `${Number(v).toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas })}%`

function svg(tag, atributos = {}, classe = '') {
  const el = document.createElementNS(NS, tag)
  for (const [nome, valor] of Object.entries(atributos)) el.setAttribute(nome, valor)
  if (classe) el.setAttribute('class', classe)
  return el
}

// Menor valor "redondo" (1, 2, 2,5, 5 ou 10 vezes uma potência de 10) que comporta o máximo.
function maximoRedondo(valor) {
  if (valor <= 0) return 1
  const potencia = 10 ** Math.floor(Math.log10(valor))
  return [1, 2, 2.5, 5, 10].map((f) => f * potencia).find((m) => m >= valor)
}

const dataDoMes = (iso) => {
  const [ano, mes] = iso.split('-').map(Number)
  return new Date(ano, mes - 1, 1)
}
const mesCurto = (d) => `${d.toLocaleDateString('pt-BR', { month: 'short' }).replace('.', '')}/${String(d.getFullYear()).slice(2)}`

// `meses`: [{mes, rendimento, taxa_percentual, acumulado_percentual}] do mais antigo ao mais novo.
export function montarGraficoRendimento(raiz, meses) {
  const pontos = meses.map((m) => ({
    data: dataDoMes(m.mes),
    rendimento: Number(m.rendimento),
    taxa: Number(m.taxa_percentual),
    acumulado: Number(m.acumulado_percentual),
  }))
  const largura = L - M.e - M.d
  const altura = A - M.t - M.b
  const maxValor = maximoRedondo(Math.max(...pontos.map((p) => p.rendimento)))
  const maxAcumulado = maximoRedondo(Math.max(...pontos.map((p) => p.acumulado)))
  const fatia = largura / pontos.length
  const x = (i) => M.e + fatia * i + fatia / 2
  const yValor = (v) => M.t + altura - (v / maxValor) * altura
  const yAcumulado = (v) => M.t + altura - (v / maxAcumulado) * altura
  const larguraBarra = fatia * 0.52

  const grafico = svg('svg', { viewBox: `0 0 ${L} ${A}`, role: 'img', 'aria-label': 'Rendimento mensal e acumulado nos últimos 12 meses' }, 'grafico-svg')
  const rotulos = criar('div', 'grafico-rotulos')
  rotulos.setAttribute('aria-hidden', 'true')
  const dica = criar('div', 'grafico-dica')
  dica.setAttribute('role', 'status')
  dica.hidden = true

  const rotulo = (classe, texto, estilo) => {
    const span = criar('span', classe, texto)
    Object.assign(span.style, estilo)
    rotulos.append(span)
  }
  for (let k = 0; k <= DIVISOES; k++) {
    const y = M.t + altura - (altura / DIVISOES) * k
    grafico.append(svg('line', { x1: M.e, x2: L - M.d, y1: y, y2: y }, 'grafico-grade'))
    const topo = `${(y / A) * 100}%`
    rotulo('esquerda', moedaCompacta.format((maxValor / DIVISOES) * k), { right: `calc(100% - ${(M.e / L) * 100}%)`, top: topo })
    rotulo('direita', pctFixo((maxAcumulado / DIVISOES) * k, 0), { left: `${((L - M.d) / L) * 100}%`, top: topo })
  }

  const barras = pontos.map((p, i) => {
    const topo = yValor(p.rendimento)
    const barra = svg('rect', { x: x(i) - larguraBarra / 2, y: topo, width: larguraBarra, height: M.t + altura - topo, rx: 4, opacity: 0.85 }, 'grafico-barra')
    barra.style.setProperty('--atraso', `${i * 45}ms`)
    return barra
  })
  grafico.append(...barras)
  const linha = svg('path', { d: pontos.map((p, i) => `${i ? 'L' : 'M'}${x(i)},${yAcumulado(p.acumulado)}`).join(' '), pathLength: 1 }, 'grafico-linha')
  grafico.append(linha)
  const marcas = pontos.map((p, i) => svg('circle', { cx: x(i), cy: yAcumulado(p.acumulado), r: 3.5 }, 'grafico-ponto'))
  grafico.append(...marcas)
  pontos.forEach((p, i) => rotulo('mes', mesCurto(p.data), { left: `${(x(i) / L) * 100}%` }))

  // Destaca o mês sob o mouse: barra cheia, outras apagadas, ponto maior e balão com os valores.
  function destacar(i) {
    barras.forEach((barra, k) => barra.setAttribute('opacity', i === null ? 0.85 : i === k ? 1 : 0.35))
    marcas.forEach((marca, k) => marca.setAttribute('r', i === k ? 5.5 : 3.5))
    if (i === null) {
      dica.hidden = true
      return
    }
    const p = pontos[i]
    const valor = (texto) => Object.assign(criar('b'), { textContent: texto })
    const linhaDeTexto = (rotuloTexto, texto) => {
      const span = criar('span', '', `${rotuloTexto}: `)
      span.append(valor(texto))
      return span
    }
    dica.replaceChildren(
      criar('strong', '', p.data.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })),
      linhaDeTexto('Rendimento', `${moeda.format(p.rendimento)} (${pctFixo(p.taxa)})`),
      linhaDeTexto('Acumulado', pctFixo(p.acumulado)),
    )
    dica.style.left = `${(x(i) / L) * 100}%`
    dica.style.top = `${(Math.min(yValor(p.rendimento), yAcumulado(p.acumulado)) / A) * 100}%`
    dica.hidden = false
  }
  pontos.forEach((p, i) => {
    const alvo = svg('rect', { x: M.e + fatia * i, y: M.t, width: fatia, height: 230 }, 'grafico-alvo')
    alvo.addEventListener('pointerenter', () => destacar(i))
    alvo.addEventListener('pointerleave', () => destacar(null))
    grafico.append(alvo)
  })

  raiz.replaceChildren(grafico, rotulos, dica)
}
