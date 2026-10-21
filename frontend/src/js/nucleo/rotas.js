import { chamar } from './api.js'
import { sair } from './firebase.js'

export const LOGIN = '/paginas/login.html'
export const HOME = '/'
export const VISAO_GERAL_GESTORA = '/paginas/gestora/visao-geral.html'
export const GESTAO_BLOCOS = '/paginas/gestora/gestao-blocos.html'
export const VISAO_GERAL = '/paginas/investidor/visao-geral.html'
export const BLOCOS_INVESTIDOR = '/paginas/investidor/blocos-de-liquidez.html'
export const BLOCOS_INVESTIDOS = '/paginas/investidor/blocos-investidos.html'
export const RELATORIO = '/paginas/investidor/relatorio.html'

// Token recusado (ex.: conta apagada): desfaz a sessão local para não ficar preso nela.
export async function encerrarSeInvalida(resposta) {
  if (resposta.status !== 401) return false
  await sair()
  return true
}

// Tela de entrada de cada perfil.
export const destinoDoPerfil = (perfil) => (perfil === 'gestora' ? VISAO_GERAL_GESTORA : VISAO_GERAL)

export async function destinoPorPerfil() {
  const resposta = await chamar('GET', '/auth/me')
  if (await encerrarSeInvalida(resposta)) return LOGIN
  return resposta.status === 200 ? destinoDoPerfil(resposta.corpo.perfil) : HOME
}
