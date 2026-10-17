export const $ = (seletor) => document.querySelector(seletor)

// Aviso curto no rodapé da tela; some sozinho (a animação dura 3 s).
export function mostrarToast(texto) {
  document.querySelector('.toast')?.remove()
  const aviso = document.createElement('p')
  aviso.className = 'toast'
  aviso.setAttribute('role', 'status')
  const ponto = document.createElement('span')
  ponto.textContent = '●'
  aviso.append(ponto, ` ${texto}`)
  document.body.append(aviso)
  aviso.addEventListener('animationend', () => aviso.remove())
}
