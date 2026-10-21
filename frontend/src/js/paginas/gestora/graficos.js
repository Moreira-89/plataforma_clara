/*
 * Gráficos da visão geral da gestora, desenhados em SVG e HTML (sem biblioteca).
 *
 * COMO FUNCIONA:
 *   1. `graficoLinha` desenha uma série mensal (inadimplência, PL) com eixo rotulado e balão ao passar o mouse.
 *   2. `graficoRating`, `graficoBlocos` e `graficoCapitalPorNota` listam barras horizontais de uma só série.
 *   3. `graficoComposicao` empilha os 4 componentes do score de cada bloco; `graficoDistribuicao` faz o histograma dos scores.
 *   4. `graficoSetores` e `graficoExposicao` põem duas barras por setor, na mesma escala.
 *   5. `tabelaAlertas` lista as empresas dos blocos com alerta no score.
 */
import { criar, moeda, moedaCompacta } from '../blocos/cartao.js'

const NS = 'http://www.w3.org/2000/svg'
const L = 760
const A = 260
const M = { e: 56, d: 16, t: 16, b: 34 }
const NOTAS_RUINS = ['C', 'D', 'E', 'F', 'G', 'H']
const PASSOS = [1, 2, 2.5, 5, 10]

// Componentes do score, na ordem em que são empilhados.
export const COMPONENTES = [
  { chave: 'qualidade_fundos', rotulo: 'Qualidade dos fundos', cor: 'var(--primary)' },
  { chave: 'permanencia', rotulo: 'Permanência', cor: 'var(--ink)' },
  { chave: 'risco_setor', rotulo: 'Risco do setor', cor: 'var(--muted)' },
  { chave: 'aceitacao', rotulo: 'Aceitação', cor: 'var(--hairline-strong)' },
]

const num = (v, casas = 1) => Number(v).toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas })
const pct = (v, casas = 1) => `${num(v, casas)}%`
const dataDoMes = (iso) => new Date(`${iso}T00:00:00`)
const mesCurto = (iso) => {
  const d = dataDoMes(iso)
  return `${d.toLocaleDateString('pt-BR', { month: 'short' }).replace('.', '')}/${String(d.getFullYear()).slice(2)}`
}

function svg(tag, atributos = {}, classe = '') {
  const el = document.createElementNS(NS, tag)
  for (const [nome, valor] of Object.entries(atributos)) el.setAttribute(nome, valor)
  if (classe) el.setAttribute('class', classe)
  return el
}

// Menor passo "redondo" (1, 2, 2,5, 5 ou 10 vezes uma potência de 10) que cabe `bruto`.
function passoRedondo(bruto) {
  const potencia = 10 ** Math.floor(Math.log10(bruto))
  return PASSOS.map((f) => f * potencia).find((p) => p >= bruto)
}

// Eixo que não parte de zero: o piso fica um pouco abaixo do menor valor, para a variação aparecer.
function escalaDoEixo(menor, maior, divisoes = 4) {
  const passo = passoRedondo(((maior - menor) * 1.2) / divisoes || Math.abs(maior) * 0.1 || 1)
  let piso = Math.floor(menor / passo) * passo
  if (menor - piso < passo * 0.25) piso -= passo
  const total = Math.ceil((maior - piso) / passo + 0.25)
  return { piso, passo, total, teto: piso + passo * total }
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

// Série mensal em linha. `pontos`: [{ mes, valor, extra? }]; `extra` é uma frase a mais no balão.
export function graficoLinha(raiz, pontos, { formatar, formatarEixo = formatar, descricao, variacao }) {
  const valores = pontos.map((p) => p.valor)
  const { piso, passo, total, teto } = escalaDoEixo(Math.min(...valores), Math.max(...valores))
  const largura = L - M.e - M.d
  const altura = A - M.t - M.b
  const deslocamento = largura / Math.max(pontos.length - 1, 1)
  const x = (i) => M.e + deslocamento * i
  const y = (v) => M.t + altura - ((v - piso) / (teto - piso)) * altura

  const grafico = svg('svg', { viewBox: `0 0 ${L} ${A}`, role: 'img', 'aria-label': descricao }, 'grafico-svg')
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

  for (let k = 0; k <= total; k++) {
    const yk = M.t + altura - (altura / total) * k
    grafico.append(svg('line', { x1: M.e, x2: L - M.d, y1: yk, y2: yk }, 'grafico-grade'))
    rotulo('esquerda', formatarEixo(piso + passo * k), { right: `calc(100% - ${(M.e / L) * 100}%)`, top: `${(yk / A) * 100}%` })
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
    const linhas = [criar('strong', '', dataDoMes(ponto.mes).toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })), criar('b', '', formatar(ponto.valor))]
    if (i > 0 && variacao) linhas.push(criar('span', '', variacao(ponto.valor, pontos[i - 1].valor)))
    if (ponto.extra) linhas.push(criar('span', '', ponto.extra))
    dica.replaceChildren(...linhas)
    dica.style.left = `${(x(i) / L) * 100}%`
    dica.style.top = `${(y(ponto.valor) / A) * 100}%`
    dica.hidden = false
  }
  pontos.forEach((_, i) => {
    const alvo = svg('rect', { x: x(i) - deslocamento / 2, y: M.t, width: deslocamento, height: altura }, 'grafico-alvo')
    alvo.addEventListener('pointerenter', () => destacar(i))
    alvo.addEventListener('pointerleave', () => destacar(null))
    grafico.append(alvo)
  })

  raiz.replaceChildren(grafico, rotulos, dica)
}

// Inadimplência mensal do mercado, com a variação em pontos percentuais no balão.
export function graficoInadimplencia(raiz, serie) {
  graficoLinha(
    raiz,
    serie.map((p) => ({ mes: p.mes, valor: Number(p.inadimplencia) })),
    {
      formatar: (v) => pct(v, 2),
      formatarEixo: (v) => pct(v, 1),
      descricao: 'Inadimplência mensal do mercado de FIDCs',
      variacao: (atual, anterior) => `${atual >= anterior ? '+' : '−'}${num(Math.abs(atual - anterior), 2)} p.p. no mês`,
    },
  )
}

// Patrimônio líquido do mercado; o balão traz também a quantidade de fundos ativos.
export function graficoPatrimonio(raiz, serie) {
  graficoLinha(
    raiz,
    serie.map((p) => ({ mes: p.mes, valor: Number(p.pl_total), extra: `${Number(p.fundos_ativos).toLocaleString('pt-BR')} fundos ativos` })),
    {
      formatar: (v) => moedaCompacta.format(v),
      descricao: 'Patrimônio líquido do mercado de FIDCs',
      variacao: (atual, anterior) => `${atual >= anterior ? '+' : '−'}${num(Math.abs((atual / anterior - 1) * 100), 1)}% no mês`,
    },
  )
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
        valor: pct(f.participacao),
        indice: i,
      }),
    ),
  )
}

// Ranking dos blocos pelo score (0 a 100), na cor da etiqueta.
export function graficoBlocos(lista, blocos) {
  lista.replaceChildren(
    ...blocos
      .filter((b) => b.score != null)
      .map((b, i) =>
        linhaDeBarra({
          rotulo: b.etiqueta,
          detalhe: `${moeda.format(b.capital_total)} · ${b.qtd_empresas} empresas`,
          largura: b.score / 100,
          cor: b.cor ?? 'var(--primary)',
          valor: `${b.nota} · ${num(b.score)}`,
          indice: i,
          classe: 'barra-bloco',
        }),
      ),
  )
}

// Os 4 componentes empilhados: a soma dos segmentos é o score do bloco (escala de 0 a 100).
export function graficoComposicao(lista, blocos) {
  lista.replaceChildren(
    ...blocos
      .filter((b) => b.componentes)
      .map((b, i) => {
        const item = criar('li', 'barra barra-bloco')
        const nome = criar('span', 'barra-nome')
        nome.append(criar('strong', '', b.etiqueta), criar('small', '', `${moeda.format(b.capital_total)} · ${b.qtd_empresas} empresas`))
        const trilha = criar('span', 'trilha trilha-empilhada')
        trilha.title = COMPONENTES.map((c) => `${c.rotulo}: ${num(b.componentes[c.chave])}`).join('\n')
        COMPONENTES.forEach((c, k) => {
          const segmento = criar('i')
          segmento.style.setProperty('--fatia', b.componentes[c.chave])
          segmento.style.setProperty('--atraso', `${150 + i * 40 + k * 30}ms`)
          segmento.style.background = c.cor
          trilha.append(segmento)
        })
        item.append(nome, trilha, criar('span', 'barra-valor', num(b.score ?? 0)))
        return item
      }),
  )
}

// Capital dos blocos em cada nota, da melhor para a pior.
export function graficoCapitalPorNota(lista, notas) {
  const maior = Math.max(...notas.map((n) => n.capital))
  const total = notas.reduce((soma, n) => soma + n.capital, 0)
  lista.replaceChildren(
    ...notas.map((n, i) =>
      linhaDeBarra({
        rotulo: n.nota,
        detalhe: `${n.quantidade} ${n.quantidade === 1 ? 'bloco' : 'blocos'} · ${pct((n.capital / total) * 100, 0)} do capital`,
        largura: n.capital / maior,
        valor: moedaCompacta.format(n.capital),
        indice: i,
      }),
    ),
  )
}

// Histograma dos scores das empresas em faixas de 10 pontos; o topo da coluna é o perfil compartilhado.
export function graficoDistribuicao(raiz, faixas) {
  const maior = Math.max(...faixas.map((f) => f.empresas))
  raiz.replaceChildren(
    ...faixas.map((f, i) => {
      const coluna = criar('div', 'coluna')
      coluna.title = `${f.inicio} a ${f.inicio + 9}: ${f.empresas} empresas (${f.perfil_compartilhado} com perfil compartilhado)`
      const pilha = criar('span', 'coluna-pilha')
      pilha.style.setProperty('--altura', f.empresas / maior)
      pilha.style.setProperty('--atraso', `${150 + i * 60}ms`)
      const compartilhado = criar('i', 'coluna-compartilhada')
      compartilhado.style.flex = f.perfil_compartilhado
      const proprio = criar('i', 'coluna-propria')
      proprio.style.flex = f.empresas - f.perfil_compartilhado
      pilha.append(compartilhado, proprio)
      coluna.append(criar('b', '', String(f.empresas)), pilha, criar('small', '', `${f.inicio}–${f.inicio + 9}`))
      return coluna
    }),
  )
}

// Duas barras por item na mesma escala (%); `a` em azul e `b` na cor informada.
function barrasDuplas(lista, itens, corB) {
  const maior = Math.max(...itens.flatMap((s) => [s.a ?? 0, s.b ?? 0]), 1)
  lista.replaceChildren(
    ...itens.map((s, i) => {
      const item = criar('li', 'barra barra-dupla')
      const nome = criar('span', 'barra-nome')
      nome.append(criar('strong', '', s.nome))
      if (s.detalhe) nome.append(criar('small', '', s.detalhe))
      const pares = criar('span', 'barra-par')
      const linha = (valor, cor) => {
        const trilha = criar('span', 'trilha')
        const preenchimento = criar('i')
        preenchimento.style.setProperty('--largura', (valor ?? 0) / maior)
        preenchimento.style.setProperty('--atraso', `${150 + i * 50}ms`)
        preenchimento.style.background = cor
        trilha.append(preenchimento)
        return [trilha, criar('span', 'trilha-valor', valor == null ? '—' : pct(valor))]
      }
      pares.append(...linha(s.a, 'var(--primary)'), ...linha(s.b, corB))
      item.append(nome, pares)
      return item
    }),
  )
}

// Peso do setor na carteira (azul) e inadimplência dos fundos concentrados nele (vermelho).
export function graficoSetores(lista, setores) {
  barrasDuplas(
    lista,
    setores.map((s) => ({ nome: s.setor, a: s.participacao_mercado, b: s.inadimplencia })),
    'var(--semantic-down)',
  )
}

// Capital dos seus blocos por setor (azul) contra o peso do setor na economia real do mercado (preto).
export function graficoExposicao(lista, exposicao) {
  barrasDuplas(
    lista,
    exposicao.map((e) => ({
      nome: e.setor,
      detalhe: e.inadimplencia == null ? null : `inadimplência do setor: ${pct(e.inadimplencia)}`,
      a: e.participacao_blocos,
      b: e.participacao_mercado,
    })),
    'var(--ink)',
  )
}

// Empresas dos blocos com alerta no score, da menor nota para a maior.
export function tabelaAlertas(corpo, alertas) {
  corpo.replaceChildren(
    ...alertas.map((a) => {
      const linha = criar('tr')
      linha.append(criar('td', '', a.nome), criar('td', '', a.etiqueta), criar('td', 'direita mono', num(a.score)), criar('td', 'celula-alerta', a.alerta))
      return linha
    }),
  )
}
