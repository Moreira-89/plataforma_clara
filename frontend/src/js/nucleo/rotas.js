import { chamar } from './api.js'
import { sair } from './firebase.js'

export const LOGIN = '/paginas/login.html'
export const HOME = '/'
export const GESTAO_BLOCOS = '/paginas/gestora/gestao-blocos.html'
export const BLOCOS_INVESTIDOR = '/paginas/investidor/blocos-de-liquidez.html'
export const BLOCOS_INVESTIDOS = '/paginas/investidor/blocos-investidos.html'

// Token recusado (ex.: conta apagada): desfaz a sessão local para não ficar preso nela.
export async function encerrarSeInvalida(resposta) {
  if (resposta.status !== 401) return false
  await sair()
  return true
}

// Tela de entrada de cada perfil.
export const destinoDoPerfil = (perfil) => (perfil === 'gestora' ? GESTAO_BLOCOS : BLOCOS_INVESTIDOR)

export async function destinoPorPerfil() {
  const resposta = await chamar('GET', '/auth/me')
  if (await encerrarSeInvalida(resposta)) return LOGIN
  return resposta.status === 200 ? destinoDoPerfil(resposta.corpo.perfil) : HOME
}
