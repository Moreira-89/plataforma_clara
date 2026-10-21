import logoUrl from '../../img/logo-clara.png'
import { sair } from './firebase.js'
import { BLOCOS_INVESTIDOR, BLOCOS_INVESTIDOS, GESTAO_BLOCOS, HOME, RELATORIO, VISAO_GERAL, VISAO_GERAL_GESTORA, destinoDoPerfil } from './rotas.js'

// Telas de cada perfil. Tela nova entra aqui e aparece no menu de todas as páginas.
const ITENS = {
  gestora: [
    { rotulo: 'Visão geral', href: VISAO_GERAL_GESTORA },
    { rotulo: 'Gestão de Blocos', href: GESTAO_BLOCOS },
  ],
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

function logo(perfil, largura, altura) {
  const marca = criar('a', 'marca')
  marca.href = destinoDoPerfil(perfil)
  const imagem = criar('img')
  imagem.src = logoUrl
  imagem.alt = 'Plataforma Clara'
  imagem.width = largura
  imagem.height = altura
  marca.append(imagem)
  return marca
}

function itens(perfil, classe, rotuloAria) {
  const lista = criar('nav', classe)
  lista.setAttribute('aria-label', rotuloAria)
  for (const item of ITENS[perfil] ?? []) {
    const link = criar('a', '', item.rotulo)
    link.href = item.href
    if (window.location.pathname === item.href) {
      link.classList.add('ativo')
      link.setAttribute('aria-current', 'page')
    }
    lista.append(link)
  }
  return lista
}

function botaoSair(classe = 'menu-sair') {
  const botao = criar('button', classe, 'Sair')
  botao.type = 'button'
  botao.addEventListener('click', async () => {
    await sair()
    window.location.href = HOME
  })
  return botao
}

// Monta o menu lateral em <aside id="menu"> e, ao lado dele, a faixa superior usada em janelas
// estreitas; devolve quem mostra o usuário depois do login.
export function montarMenu(perfil) {
  const barra = document.querySelector('#menu')
  barra.className = 'menu-lateral'
  document.body.classList.add('com-menu')

  const rodape = criar('div', 'menu-rodape')
  const usuario = criar('span', 'usuario-menu')
  rodape.append(usuario, botaoSair())
  barra.replaceChildren(logo(perfil, 110, 36), itens(perfil, 'menu-itens', 'Menu'), rodape)

  const topo = criar('header', 'menu-topo')
  const faixa = criar('div', 'menu-topo-barra')
  faixa.append(logo(perfil, 98, 32), botaoSair())
  topo.append(faixa)
  if ((ITENS[perfil] ?? []).length > 1) topo.append(itens(perfil, 'menu-topo-itens', 'Menu'))
  barra.after(topo)

  return { definirUsuario: (email) => (usuario.textContent = email ?? '') }
}
