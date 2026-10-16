import { obterToken } from './firebase.js'

// Em dev o proxy do Vite atende /api; em produção a URL vem do build.
const API = (import.meta.env.VITE_API_URL || '/api').replace(/\/+$/, '')

// Devolve { status, corpo } sem lançar em 4xx/5xx nem em falha de rede (status 0): a tela mostra o erro.
export async function chamar(metodo, caminho, corpo, { autenticado = true } = {}) {
  const cabecalhos = { 'Content-Type': 'application/json' }
  if (autenticado) {
    const token = await obterToken()
    if (token) cabecalhos.Authorization = `Bearer ${token}`
  }

  let resposta
  try {
    resposta = await fetch(`${API}${caminho}`, {
      method: metodo,
      headers: cabecalhos,
      body: corpo ? JSON.stringify(corpo) : undefined,
    })
  } catch {
    // Servidor fora do ar, URL errada ou CORS bloqueado: o navegador não distingue, e a tela precisa avisar.
    return { status: 0, corpo: { detail: 'Não foi possível falar com o servidor. Tente de novo em instantes.' } }
  }
  const texto = await resposta.text()
  try {
    return { status: resposta.status, corpo: texto ? JSON.parse(texto) : null }
  } catch {
    return { status: 502, corpo: { detail: 'Resposta inesperada do servidor. Confira VITE_API_URL e o backend.' } }
  }
}

// detail do FastAPI é texto, ou lista de erros de validação (422).
export function textoDoErro({ corpo }) {
  const detalhe = corpo?.detail
  if (Array.isArray(detalhe)) return detalhe.map((d) => `${d.loc.slice(1).join('.')}: ${d.msg}`).join('; ')
  return detalhe ?? 'Erro desconhecido.'
}
