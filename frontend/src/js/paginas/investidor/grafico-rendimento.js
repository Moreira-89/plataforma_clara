/*
 * Gráfico do rendimento mensal dos últimos 12 meses, em SVG puro (sem biblioteca).
 *
 * COMO FUNCIONA:
 *   1. Barras mostram o rendimento de cada mês em R$ (eixo da esquerda).
 *   2. Uma linha mostra o rendimento acumulado em % (eixo da direita).
 *   3. Passar o mouse sobre um mês destaca a barra e mostra um balão com os três valores.
 */
import { criar, moeda } from '../blocos/cartao.js'

const NS = 'http://www.w3.org/2000/svg'
const LARGURA = 760
const ALTURA = 280
const MARGEM = { esquerda: 76, direita: 52, topo: 16, base: 34 }
const DIVISOES = 4

const compacto = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', notation: 'compact', maximumFractionDigits: 1 })
const percentual = (valor, casas = 2) => `${Number(valor).toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas })}%`

function elemento(tag, atributos = {}, classe = '') {
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
const rotuloCurto = (data) => `${data.toLocaleDateString('pt-BR', { month: 'short' }).replace('.', '')}/${String(data.getFullYear()).slice(2)}`
const rotuloLongo = (data) => data.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })

// `meses`: [{mes, rendimento, taxa_percentual, acumulado_percentual}] do mais antigo ao mais novo.
export function montarGraficoRendimento(raiz, dica, meses) {
  const pontos = meses.map((m) => ({
    data: dataDoMes(m.mes),
    rendimento: Number(m.rendimento),
    taxa: Number(m.taxa_percentual),
    acumulado: Number(m.acumulado_percentual),
  }))
  const largura = LARGURA - MARGEM.esquerda - MARGEM.direita
  const altura = ALTURA - MARGEM.topo - MARGEM.base
  const maxValor = maximoRedondo(Math.max(...pontos.map((p) => p.rendimento)))
  const maxAcumulado = maximoRedondo(Math.max(...pontos.map((p) => p.acumulado)))
  const fatia = largura / pontos.length
  const x = (i) => MARGEM.esquerda + fatia * i + fatia / 2
  const yValor = (v) => MARGEM.topo + altura - (v / maxValor) * altura
  const yAcumulado = (v) => MARGEM.topo + altura - (v / maxAcumulado) * altura

  const svg = elemento('svg', { viewBox: `0 0 ${LARGURA} ${ALTURA}`, role: 'img', 'aria-label': 'Rendimento mensal e acumulado nos últimos 12 meses' }, 'grafico-svg')

  // Grade e eixos: R$ à esquerda, % à direita.
  const grade = elemento('g', {}, 'grafico-grade')
  const eixo = elemento('g', {}, 'grafico-eixo')
  for (let d = 0; d <= DIVISOES; d++) {
    const y = MARGEM.topo + altura - (altura / DIVISOES) * d
    grade.append(elemento('line', { x1: MARGEM.esquerda, x2: LARGURA - MARGEM.direita, y1: y, y2: y }))
    const esquerda = elemento('text', { x: MARGEM.esquerda - 8, y: y + 4, 'text-anchor': 'end' })
    esquerda.textContent = compacto.format((maxValor / DIVISOES) * d)
    const direita = elemento('text', { x: LARGURA - MARGEM.direita + 8, y: y + 4, 'text-anchor': 'start' })
    direita.textContent = percentual((maxAcumulado / DIVISOES) * d, 0)
    eixo.append(esquerda, direita)
  }
  pontos.forEach((p, i) => {
    const rotulo = elemento('text', { x: x(i), y: ALTURA - 12, 'text-anchor': 'middle' })
    rotulo.textContent = rotuloCurto(p.data)
    eixo.append(rotulo)
  })
  svg.append(grade, eixo)

  // Barras (rendimento) e linha (acumulado).
  const largBarra = fatia * 0.52
  const barras = pontos.map((p, i) => {
    const topo = yValor(p.rendimento)
    return elemento('rect', { x: x(i) - largBarra / 2, y: topo, width: largBarra, height: MARGEM.topo + altura - topo, rx: 4 }, 'grafico-barra')
  })
  svg.append(...barras)
  svg.append(elemento('path', { d: pontos.map((p, i) => `${i ? 'L' : 'M'}${x(i)},${yAcumulado(p.acumulado)}`).join(' ') }, 'grafico-linha'))
  pontos.forEach((p, i) => svg.append(elemento('circle', { cx: x(i), cy: yAcumulado(p.acumulado), r: 3.5 }, 'grafico-ponto')))

  // Uma faixa transparente por mês recebe o mouse.
  let ativa = null
  pontos.forEach((p, i) => {
    const alvo = elemento('rect', { x: MARGEM.esquerda + fatia * i, y: MARGEM.topo, width: fatia, height: altura }, 'grafico-alvo')
    alvo.addEventListener('pointermove', (evento) => {
      if (ativa !== i) {
        barras[ativa]?.classList.remove('ativa')
        barras[i].classList.add('ativa')
        ativa = i
        dica.replaceChildren(
          criar('strong', '', rotuloLongo(p.data)),
          criar('span', '', `Rendimento: ${moeda.format(p.rendimento)} (${percentual(p.taxa)})`),
          criar('span', '', `Acumulado: ${percentual(p.acumulado)}`),
        )
      }
      const caixa = raiz.getBoundingClientRect()
      dica.hidden = false
      dica.style.left = `${evento.clientX - caixa.left}px`
      dica.style.top = `${evento.clientY - caixa.top}px`
    })
    alvo.addEventListener('pointerleave', () => {
      barras[ativa]?.classList.remove('ativa')
      ativa = null
      dica.hidden = true
    })
    svg.append(alvo)
  })

  raiz.replaceChildren(svg)
}
