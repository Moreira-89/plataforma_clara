/*
 * Interface do chatbot da visão geral. Ainda não há LLM por trás: só a conversa na tela.
 *
 * COMO FUNCIONA:
 *   1. `montarChat` mostra uma saudação do assistente e liga o formulário de envio.
 *   2. Ao enviar, a mensagem do usuário entra na conversa e o campo é limpo.
 *   3. `responder` é o ponto de ligação futuro com o backend/LLM; hoje devolve um aviso fixo.
 *   4. A conversa vive só na página: recarregar começa de novo.
 */
import { criar } from '../blocos/cartao.js'
import { $ } from '../../nucleo/ui.js'

const SAUDACAO = 'Olá! Sou o assistente da Clara. Em breve vou responder suas dúvidas sobre os seus investimentos.'
const AVISO = 'Ainda não estou conectado a um modelo de linguagem, então não consigo responder por enquanto.'

// Ponto de ligação com a LLM: trocar por uma chamada à API quando ela existir.
async function responder(_mensagem) {
  return AVISO
}

export function montarChat() {
  const conversa = $('#chat-mensagens')
  const form = $('#chat-form')
  const campo = $('#chat-texto')

  function adicionar(autor, texto) {
    conversa.append(criar('p', `chat-balao ${autor}`, texto))
    conversa.scrollTop = conversa.scrollHeight
  }

  form.addEventListener('submit', async (evento) => {
    evento.preventDefault()
    const texto = campo.value.trim()
    if (!texto) return
    adicionar('usuario', texto)
    campo.value = ''
    adicionar('assistente', await responder(texto))
  })

  adicionar('assistente', SAUDACAO)
}
