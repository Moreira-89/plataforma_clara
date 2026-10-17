/*
 * Interface do chatbot da visão geral. Ainda não há LLM por trás: só a conversa na tela.
 *
 * COMO FUNCIONA:
 *   1. `montarChat` mostra uma saudação do assistente e liga o formulário de envio.
 *   2. Ao enviar, a mensagem entra na conversa, aparece o indicador "digitando" e o campo é limpo.
 *   3. `responder` é o ponto de ligação futuro com o backend/LLM; hoje espera um instante e devolve um aviso fixo.
 *   4. A conversa vive só na página: recarregar começa de novo.
 */
import { criar } from '../blocos/cartao.js'
import { $ } from '../../nucleo/ui.js'

const SAUDACAO = 'Olá! Sou o assistente da Clara. Em breve vou responder suas dúvidas sobre os seus investimentos.'
const AVISO = 'Ainda não estou conectado a um modelo de linguagem, então não consigo responder por enquanto.'
const ESPERA_MS = 900

// Ponto de ligação com a LLM: trocar por uma chamada à API quando ela existir.
async function responder(_mensagem) {
  await new Promise((resolver) => setTimeout(resolver, ESPERA_MS))
  return AVISO
}

export function montarChat() {
  const conversa = $('#chat-log')
  const form = $('#chat-form')
  const campo = $('#chat-texto')
  let digitando = null

  const rolarParaOFim = () => (conversa.scrollTop = conversa.scrollHeight)
  function adicionar(texto, meu) {
    conversa.append(criar('p', meu ? 'chat-balao meu' : 'chat-balao', texto))
    rolarParaOFim()
  }
  function mostrarDigitando(ativo) {
    digitando?.remove()
    digitando = null
    if (!ativo) return
    digitando = criar('p', 'chat-digitando')
    digitando.setAttribute('aria-label', 'Assistente digitando')
    digitando.append(criar('i'), criar('i'), criar('i'))
    conversa.append(digitando)
    rolarParaOFim()
  }

  form.addEventListener('submit', async (evento) => {
    evento.preventDefault()
    const texto = campo.value.trim()
    if (!texto) return
    adicionar(texto, true)
    campo.value = ''
    mostrarDigitando(true)
    const resposta = await responder(texto)
    mostrarDigitando(false)
    adicionar(resposta, false)
  })

  adicionar(SAUDACAO, false)
}
