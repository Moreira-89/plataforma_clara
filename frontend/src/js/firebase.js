import { initializeApp } from 'firebase/app'
import {
  getAuth,
  signInWithEmailAndPassword,
  signOut,
  onAuthStateChanged,
} from 'firebase/auth'

const app = initializeApp({
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
})

export const auth = getAuth(app)

export const entrar = (email, senha) => signInWithEmailAndPassword(auth, email, senha)
export const sair = () => signOut(auth)
export const aoMudarSessao = (callback) => onAuthStateChanged(auth, callback)

// forcar=true busca um token novo, já com as claims atuais.
export const obterToken = (forcar = false) => auth.currentUser?.getIdToken(forcar)

const MENSAGENS = {
  'auth/invalid-credential': 'E-mail ou senha incorretos.',
  'auth/user-not-found': 'E-mail ou senha incorretos.',
  'auth/wrong-password': 'E-mail ou senha incorretos.',
  'auth/too-many-requests': 'Muitas tentativas. Aguarde e tente de novo.',
  'auth/network-request-failed': 'Sem conexão com o Firebase.',
  'auth/invalid-api-key': 'VITE_FIREBASE_API_KEY inválida. Confira o frontend/.env.',
}

export const mensagemDeErro = (erro) => MENSAGENS[erro.code] ?? `Erro do Firebase: ${erro.code ?? erro.message}`
