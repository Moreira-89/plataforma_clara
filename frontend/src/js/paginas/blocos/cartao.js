// Peças compartilhadas pelas telas que mostram blocos: formatação e o cartão do bloco.

export const moeda = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
export const SEM_SCORE = '—'

// Nota e número juntos no pop-up (por exemplo, "A · 74"); os cartões mostram só a nota.
export const rotuloScore = (nota, score) => (score == null ? SEM_SCORE : `${nota} · ${Math.round(score)}`)
export const codigoCurto = (id) => id.slice(0, 8).toUpperCase()
export const dataBr = (iso) => iso.split('-').reverse().join('/')
export const cnpjFormatado = (c) => c.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5')

export function criar(tag, classe, texto) {
  const el = document.createElement(tag)
  if (classe) el.className = classe
  if (texto !== undefined) el.textContent = texto
  return el
}

export function seloEtiqueta(cor) {
  const selo = criar('i', 'selo-etiqueta')
  selo.style.background = cor ?? 'var(--surface-strong)'
  selo.setAttribute('aria-hidden', 'true')
  return selo
}

// Cartão do bloco. Opções: `valorInvestido` (mostra o quanto o investidor aplicou), `aoDetalhes`
// (clique em "Ver mais detalhes") e `detalhesDesativado` (botão presente, sem ação por enquanto).
export function montarCartao(bloco, { valorInvestido, aoDetalhes, detalhesDesativado = false } = {}) {
  const cartao = criar('article', 'cartao cartao-bloco')

  const topo = criar('div', 'cartao-topo')
  const etiqueta = criar('span', 'etiqueta-bloco')
  etiqueta.append(seloEtiqueta(bloco.cor), criar('span', '', bloco.etiqueta))
  topo.append(etiqueta, criar('span', 'codigo-bloco', `Cod: ${codigoCurto(bloco.id_bloco)}`))

  const score = criar('div', 'linha-score')
  score.append(criar('span', '', 'Score de risco'), criar('strong', 'nota-risco', bloco.nota_risco ?? SEM_SCORE))

  const empresas = `${bloco.quantidade_empresas} ${bloco.quantidade_empresas === 1 ? 'empresa' : 'empresas'}`
  const meta = criar('p', 'meta-bloco', `${empresas} · vence em ${dataBr(bloco.data_vencimento)}`)

  const botao = criar('button', 'btn btn-secundario', 'Ver mais detalhes')
  botao.type = 'button'
  botao.disabled = detalhesDesativado
  if (aoDetalhes) botao.addEventListener('click', aoDetalhes)

  cartao.append(topo, score, meta)
  if (valorInvestido != null) {
    const investido = criar('p', 'valor-investido', 'Investido: ')
    investido.append(criar('strong', 'numero', moeda.format(Number(valorInvestido))))
    cartao.append(investido)
  }
  cartao.append(botao)
  return cartao
}
