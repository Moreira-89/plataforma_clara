import { obterToken } from './firebase.js'

// Em dev o proxy do Vite atende /api; em produção a URL vem do build.
const API = import.meta.env.VITE_API_URL ?? '/api'

// Devolve { status, corpo } sem lançar em 4xx/5xx: a tela mostra o status.
export async function chamar(metodo, caminho, corpo, { autenticado = true } = {}) {
  const cabecalhos = { 'Content-Type': 'application/json' }
  if (autenticado) {
    const token = await obterToken()
    if (token) cabecalhos.Authorization = `Bearer ${token}`
  }

  const resposta = await fetch(`${API}${caminho}`, {
    method: metodo,
    headers: cabecalhos,
    body: corpo ? JSON.stringify(corpo) : undefined,
  })
  const texto = await resposta.text()
  let json = null
  try {
    json = texto ? JSON.parse(texto) : null
  } catch {
    json = texto
  }
  return { status: resposta.status, corpo: json }
}

// detail do FastAPI é texto, ou lista de erros de validação (422).
export function textoDoErro({ corpo }) {
  const detalhe = corpo?.detail
  if (Array.isArray(detalhe)) return detalhe.map((d) => `${d.loc.slice(1).join('.')}: ${d.msg}`).join('; ')
  return detalhe ?? 'Erro desconhecido.'
}
