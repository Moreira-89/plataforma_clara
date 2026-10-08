export const $ = (seletor) => document.querySelector(seletor)

export function mostrarMensagem(texto, erro = false) {
  const el = $('#mensagem')
  el.textContent = texto
  el.classList.toggle('erro', erro)
}

// Desabilita o botão de envio enquanto a chamada está em andamento.
export async function enviando(formulario, acao) {
  const botao = formulario.querySelector('button[type="submit"]')
  botao.disabled = true
  try {
    await acao()
  } finally {
    botao.disabled = false
  }
}
