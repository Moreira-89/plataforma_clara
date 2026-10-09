import { chamar } from './api.js'
import { sair } from './firebase.js'

export const LOGIN = '/paginas/login.html'
export const HOME = '/'
export const NOVO_BLOCO = '/paginas/gestora/novo-bloco.html'

// Token recusado (ex.: conta apagada): desfaz a sessão local para não ficar preso nela.
export async function encerrarSeInvalida(resposta) {
  if (resposta.status !== 401) return false
  await sair()
  return true
}

// A gestora entra direto na criação de blocos; o investidor, sem tela própria ainda, na home.
export async function destinoPorPerfil() {
  const resposta = await chamar('GET', '/auth/me')
  if (await encerrarSeInvalida(resposta)) return LOGIN
  return resposta.status === 200 && resposta.corpo.perfil === 'gestora' ? NOVO_BLOCO : HOME
}
