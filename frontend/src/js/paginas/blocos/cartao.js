// Peças compartilhadas pelas telas que mostram blocos: formatação e o cartão do bloco.

export const moeda = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
export const moedaCompacta = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', notation: 'compact', maximumFractionDigits: 1 })
export const SEM_SCORE = '—'
export const TONS = [1, 0.72, 1.28] // variação de brilho entre empresas da mesma cor
const SCORE_DE_RISCO = 40 // abaixo disso a nota aparece em vermelho

// Nota e número juntos na ficha (por exemplo, "A · 74"); os cartões mostram só a nota.
export const rotuloScore = (nota, score) => (score == null ? SEM_SCORE : `${nota} · ${Math.round(score)}`)
export const codigoCurto = (id) => id.slice(0, 8).toUpperCase()
export const dataBr = (iso) => iso.split('-').reverse().join('/')
export const cnpjFormatado = (c) => c.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5')
export const percentual = (valor, casas = 2) => `${Number(valor).toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: casas })}%`

// Busca pelo código (início do id ou código completo) ou pelo nome da etiqueta; sem termo, tudo combina.
export function combinaBusca(bloco, termo) {
  if (!termo) return true
  const alvo = termo.toLowerCase().replace(/\s+/g, '')
  const campos = [bloco.id_bloco, bloco.codigo_identificacao, bloco.etiqueta]
  return campos.some((c) => c.toLowerCase().replace(/\s+/g, '').includes(alvo))
}

export function criar(tag, classe, texto) {
  const el = document.createElement(tag)
  if (classe) el.className = classe
  if (texto !== undefined) el.textContent = texto
  return el
}

export function seloEtiqueta(cor) {
  const selo = criar('i', 'selo-etiqueta')
  selo.style.setProperty('--cor', cor ?? 'var(--surface-strong)')
  selo.setAttribute('aria-hidden', 'true')
  return selo
}

// Cartão do bloco. Opções: `valorInvestido` (linha "Investido"), `mostrarCapital` (linha "Capital", da gestora),
// `destacado` (bloco recém-criado), `indice` (escalona a entrada) e `aoDetalhes` (cartão ou botão).
export function montarCartao(bloco, { valorInvestido, mostrarCapital = false, destacado = false, indice = 0, aoDetalhes } = {}) {
  const cartao = criar('article', destacado ? 'cartao-bloco novo' : 'cartao-bloco')
  cartao.style.setProperty('--atraso', `${Math.min(indice, 8) * 50}ms`)

  const topo = criar('div', 'cartao-topo')
  const etiqueta = criar('span', 'etiqueta-bloco')
  etiqueta.append(seloEtiqueta(bloco.cor), criar('span', '', bloco.etiqueta))
  topo.append(etiqueta, criar('span', 'codigo-bloco', `Cod: ${codigoCurto(bloco.id_bloco)}`))
  cartao.style.setProperty('--cor', bloco.cor ?? 'var(--muted)')

  // Uma fatia por empresa, do tamanho da participação dela no bloco.
  const segmentos = criar('div', 'segmentos')
  segmentos.setAttribute('aria-hidden', 'true')
  bloco.fatias.forEach((fatia, k) => {
    const segmento = criar('i')
    segmento.style.setProperty('--fatia', Number(fatia))
    segmento.style.setProperty('--tom', TONS[k % TONS.length])
    segmentos.append(segmento)
  })

  const score = criar('div', 'linha-score')
  const nota = criar('strong', bloco.score != null && bloco.score < SCORE_DE_RISCO ? 'risco' : '', bloco.nota_risco ?? SEM_SCORE)
  score.append(criar('span', '', 'Score de risco'), nota)

  const empresas = `${bloco.quantidade_empresas} ${bloco.quantidade_empresas === 1 ? 'empresa' : 'empresas'}`
  cartao.append(topo, segmentos, score, criar('p', 'meta-bloco', `${empresas} · vence em ${dataBr(bloco.data_vencimento)}`))

  const linhaDeValor = (rotulo, valor) => {
    const linha = criar('p', 'valor-bloco', `${rotulo}: `)
    linha.append(criar('strong', '', moeda.format(Number(valor))))
    cartao.append(linha)
  }
  if (valorInvestido != null) linhaDeValor('Investido', valorInvestido)
  else if (mostrarCapital) linhaDeValor('Capital', bloco.capital_total)

  const botao = criar('button', 'botao-detalhes', 'Ver mais detalhes')
  botao.type = 'button'
  cartao.append(botao)

  // O cartão inteiro abre a ficha; o botão também, sem repetir o clique do cartão.
  if (aoDetalhes) {
    cartao.addEventListener('click', () => aoDetalhes())
    botao.addEventListener('click', (evento) => {
      evento.stopPropagation()
      aoDetalhes()
    })
  }
  return cartao
}
