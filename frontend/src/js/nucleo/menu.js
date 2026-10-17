import logoUrl from '../../img/logo-clara.png'
import { sair } from './firebase.js'
import { BLOCOS_INVESTIDOR, BLOCOS_INVESTIDOS, GESTAO_BLOCOS, HOME, RELATORIO, VISAO_GERAL, destinoDoPerfil } from './rotas.js'

// Telas de cada perfil. Tela nova entra aqui e aparece no menu de todas as páginas.
const ITENS = {
  gestora: [{ rotulo: 'Gestão de Blocos', href: GESTAO_BLOCOS }],
  investidor: [
    { rotulo: 'Visão geral', href: VISAO_GERAL },
    { rotulo: 'Blocos de Liquidez', href: BLOCOS_INVESTIDOR },
    { rotulo: 'Blocos Investidos', href: BLOCOS_INVESTIDOS },
    { rotulo: 'Relatório', href: RELATORIO },
  ],
}

function criar(tag, classe, texto) {
  const el = document.createElement(tag)
  if (classe) el.className = classe
  if (texto !== undefined) el.textContent = texto
  return el
}

// Monta o menu lateral em <aside id="menu">; devolve quem mostra o usuário depois do login.
export function montarMenu(perfil) {
  const barra = document.querySelector('#menu')
  barra.className = 'menu-lateral'
  document.body.classList.add('com-menu')

  const marca = criar('a', 'marca')
  marca.href = destinoDoPerfil(perfil)
  const logo = criar('img')
  logo.src = logoUrl
  logo.alt = 'Plataforma Clara'
  marca.append(logo)

  const itens = criar('nav', 'menu-itens')
  itens.setAttribute('aria-label', 'Menu')
  for (const item of ITENS[perfil] ?? []) {
    const link = criar('a', '', item.rotulo)
    link.href = item.href
    if (window.location.pathname === item.href) {
      link.classList.add('ativo')
      link.setAttribute('aria-current', 'page')
    }
    itens.append(link)
  }

  const rodape = criar('div', 'menu-rodape')
  const usuario = criar('span', 'usuario-menu')
  const botaoSair = criar('button', 'btn btn-secundario', 'Sair')
  botaoSair.type = 'button'
  botaoSair.addEventListener('click', async () => {
    await sair()
    window.location.href = HOME
  })
  rodape.append(usuario, botaoSair)

  barra.replaceChildren(marca, itens, rodape)
  return { definirUsuario: (email) => (usuario.textContent = email ?? '') }
}
