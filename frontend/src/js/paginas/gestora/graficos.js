/*
 * Gráficos da visão geral da gestora, desenhados em SVG e HTML (sem biblioteca).
 *
 * COMO FUNCIONA:
 *   1. `graficoInadimplencia` desenha a linha mensal da inadimplência do mercado, com balão ao passar o mouse.
 *   2. `graficoRating` lista a participação de cada nota SCR na carteira; as piores notas ficam em vermelho.
 *   3. `graficoBlocos` ranqueia os blocos pelo score, com a cor da etiqueta.
 *   4. `graficoSetores` põe, lado a lado, o peso do setor na carteira e a inadimplência dos fundos concentrados nele.
 */
import { criar, moeda, moedaCompacta } from '../blocos/cartao.js'

const NS = 'http://www.w3.org/2000/svg'
const L = 760
const A = 260
const M = { e: 48, d: 16, t: 16, b: 34 }
const DIVISOES = 4
const NOTAS_RUINS = ['C', 'D', 'E', 'F', 'G', 'H']

const pct = (v, casas = 1) => `${Number(v).toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas })}%`
const mesCurto = (iso) => {
  const [ano, mes] = iso.split('-').map(Number)
  const nome = new Date(ano, mes - 1, 1).toLocaleDateString('pt-BR', { month: 'short' }).replace('.', '')
  return `${nome}/${String(ano).slice(2)}`
}

function svg(tag, atributos = {}, classe = '') {
  const el = document.createElementNS(NS, tag)
  for (const [nome, valor] of Object.entries(atributos)) el.setAttribute(nome, valor)
  if (classe) el.setAttribute('class', classe)
  return el
}

// Uma linha de barra: rótulo, trilha com preenchimento e valor; `largura` vai de 0 a 1.
function linhaDeBarra({ rotulo, detalhe, largura, cor, valor, indice, classe = '' }) {
  const item = criar('li', `barra ${classe}`.trim())
  const nome = criar('span', 'barra-nome')
  nome.append(criar('strong', '', rotulo))
  if (detalhe) nome.append(criar('small', '', detalhe))
  const trilha = criar('span', 'trilha')
  const preenchimento = criar('i')
  preenchimento.style.setProperty('--largura', Math.max(0, Math.min(1, largura)))
  preenchimento.style.setProperty('--atraso', `${150 + indice * 50}ms`)
  if (cor) preenchimento.style.background = cor
  trilha.append(preenchimento)
  item.append(nome, trilha, criar('span', 'barra-valor', valor))
  return item
}

// Linha da inadimplência mensal; o eixo não parte de zero e vem rotulado, para a variação aparecer.
export function graficoInadimplencia(raiz, serie) {
  const pontos = serie.map((p) => ({ mes: p.mes, valor: Number(p.inadimplencia) }))
  const piso = Math.floor(Math.min(...pontos.map((p) => p.valor)) - 0.5)
  const teto = Math.ceil(Math.max(...pontos.map((p) => p.valor)) + 0.5)
  const largura = L - M.e - M.d
  const altura = A - M.t - M.b
  const passo = largura / Math.max(pontos.length - 1, 1)
  const x = (i) => M.e + passo * i
  const y = (v) => M.t + altura - ((v - piso) / (teto - piso)) * altura

  const grafico = svg('svg', { viewBox: `0 0 ${L} ${A}`, role: 'img', 'aria-label': 'Inadimplência mensal do mercado de FIDCs' }, 'grafico-svg')
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
    const yk = M.t + altura - (altura / DIVISOES) * k
    grafico.append(svg('line', { x1: M.e, x2: L - M.d, y1: yk, y2: yk }, 'grafico-grade'))
    rotulo('esquerda', pct(piso + ((teto - piso) / DIVISOES) * k, 1), { right: `calc(100% - ${(M.e / L) * 100}%)`, top: `${(yk / A) * 100}%` })
  }

  const caminho = pontos.map((p, i) => `${i ? 'L' : 'M'}${x(i)},${y(p.valor)}`).join(' ')
  grafico.append(svg('path', { d: `${caminho} L${x(pontos.length - 1)},${M.t + altura} L${x(0)},${M.t + altura} Z` }, 'grafico-preenchimento'))
  grafico.append(svg('path', { d: caminho, pathLength: 1 }, 'grafico-linha'))
  const marcas = pontos.map((p, i) => svg('circle', { cx: x(i), cy: y(p.valor), r: 3.5 }, 'grafico-ponto'))
  grafico.append(...marcas)
  pontos.forEach((p, i) => rotulo('mes', mesCurto(p.mes), { left: `${(x(i) / L) * 100}%` }))

  function destacar(i) {
    marcas.forEach((marca, k) => marca.setAttribute('r', i === k ? 5.5 : 3.5))
    if (i === null) {
      dica.hidden = true
      return
    }
    const ponto = pontos[i]
    const anterior = i > 0 ? pontos[i - 1].valor : null
    const linhas = [criar('strong', '', new Date(`${ponto.mes}T00:00:00`).toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })), criar('b', '', pct(ponto.valor, 2))]
    if (anterior !== null) {
      const dif = ponto.valor - anterior
      linhas.push(criar('span', '', `${dif >= 0 ? '+' : '−'}${Math.abs(dif).toLocaleString('pt-BR', { maximumFractionDigits: 2 })} p.p. no mês`))
    }
    dica.replaceChildren(...linhas)
    dica.style.left = `${(x(i) / L) * 100}%`
    dica.style.top = `${(y(ponto.valor) / A) * 100}%`
    dica.hidden = false
  }
  pontos.forEach((_, i) => {
    const alvo = svg('rect', { x: x(i) - passo / 2, y: M.t, width: passo, height: altura }, 'grafico-alvo')
    alvo.addEventListener('pointerenter', () => destacar(i))
    alvo.addEventListener('pointerleave', () => destacar(null))
    grafico.append(alvo)
  })

  raiz.replaceChildren(grafico, rotulos, dica)
}

// Participação de cada nota SCR na carteira; C a H são as notas de maior risco.
export function graficoRating(lista, faixas) {
  const maior = Math.max(...faixas.map((f) => f.participacao))
  lista.replaceChildren(
    ...faixas.map((f, i) =>
      linhaDeBarra({
        rotulo: f.nota,
        detalhe: moedaCompacta.format(f.valor),
        largura: f.participacao / maior,
        cor: NOTAS_RUINS.includes(f.nota) ? 'var(--semantic-down)' : f.nota === 'B' ? 'var(--muted)' : null,
        valor: pct(f.participacao, 1),
        indice: i,
      }),
    ),
  )
}

// Ranking dos blocos pelo score (0 a 100), na cor da etiqueta.
export function graficoBlocos(lista, blocos) {
  const comScore = blocos.filter((b) => b.score != null)
  lista.replaceChildren(
    ...comScore.map((b, i) =>
      linhaDeBarra({
        rotulo: b.etiqueta,
        detalhe: `${moeda.format(b.capital_total)} · ${b.qtd_empresas} empresas`,
        largura: b.score / 100,
        cor: b.cor ?? 'var(--primary)',
        valor: `${b.nota} · ${Math.round(b.score)}`,
        indice: i,
        classe: 'barra-bloco',
      }),
    ),
  )
}

// Peso do setor na carteira (azul) e inadimplência dos fundos concentrados nele (vermelho).
export function graficoSetores(lista, setores) {
  // Mesma escala (%) nas duas barras, para o comprimento valer como comparação.
  const maior = Math.max(...setores.flatMap((s) => [s.participacao_mercado, s.inadimplencia ?? 0]))
  lista.replaceChildren(
    ...setores.map((s, i) => {
      const item = criar('li', 'barra barra-dupla')
      const nome = criar('span', 'barra-nome')
      nome.append(criar('strong', '', s.setor))
      const pares = criar('span', 'barra-par')
      const linha = (largura, cor, valor) => {
        const trilha = criar('span', 'trilha')
        const preenchimento = criar('i')
        preenchimento.style.setProperty('--largura', largura)
        preenchimento.style.setProperty('--atraso', `${150 + i * 50}ms`)
        preenchimento.style.background = cor
        trilha.append(preenchimento)
        const rotulo = criar('span', 'trilha-valor', valor)
        return [trilha, rotulo]
      }
      pares.append(
        ...linha(s.participacao_mercado / maior, 'var(--primary)', pct(s.participacao_mercado, 1)),
        ...linha(s.inadimplencia == null ? 0 : s.inadimplencia / maior, 'var(--semantic-down)', s.inadimplencia == null ? '—' : pct(s.inadimplencia, 1)),
      )
      item.append(nome, pares)
      return item
    }),
  )
}
