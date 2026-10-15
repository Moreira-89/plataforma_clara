import { initializeApp } from 'firebase/app'
import {
  getAuth,
  signInWithEmailAndPassword,
  signOut,
  onAuthStateChanged,
} from 'firebase/auth'

let auth

// Inicia o Firebase na primeira vez que alguém o usa. Com a config ausente ou inválida, o erro
// aparece aqui, na hora do uso, e não derruba o script inteiro da página ao carregar.
function obterAuth() {
  auth ??= getAuth(
    initializeApp({
      apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
      authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
      projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
    }),
  )
  return auth
}

export const entrar = (email, senha) => signInWithEmailAndPassword(obterAuth(), email, senha)
export const sair = () => signOut(obterAuth())

// Sem Firebase utilizável, trata como "sem sessão" para as páginas seguirem para o login.
export function aoMudarSessao(callback) {
  try {
    return onAuthStateChanged(obterAuth(), callback)
  } catch (erro) {
    console.error('Firebase indisponível:', erro)
    callback(null)
    return () => {}
  }
}

// forcar=true busca um token novo, já com as claims atuais.
export const obterToken = (forcar = false) => auth?.currentUser?.getIdToken(forcar)

const MENSAGENS = {
  'auth/invalid-credential': 'E-mail ou senha incorretos.',
  'auth/user-not-found': 'E-mail ou senha incorretos.',
  'auth/wrong-password': 'E-mail ou senha incorretos.',
  'auth/too-many-requests': 'Muitas tentativas. Aguarde e tente de novo.',
  'auth/network-request-failed': 'Sem conexão com o Firebase.',
  'auth/invalid-api-key': 'A configuração do Firebase está ausente ou inválida (VITE_FIREBASE_*).',
}

export const mensagemDeErro = (erro) => MENSAGENS[erro.code] ?? `Erro do Firebase: ${erro.code ?? erro.message}`
