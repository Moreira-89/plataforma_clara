import { chamar, textoDoErro } from '../../nucleo/api.js'
import { aoMudarSessao } from '../../nucleo/firebase.js'
import { montarMenu } from '../../nucleo/menu.js'
import { LOGIN, destinoDoPerfil, encerrarSeInvalida } from '../../nucleo/rotas.js'
import { $ } from '../../nucleo/ui.js'
import { combinaBusca, criar, moeda, montarCartao } from '../blocos/cartao.js'
import { abrirDetalhe, ligarDialogoDeDetalhe } from '../blocos/detalhe.js'

const menu = montarMenu('investidor')
let blocos = []

// "Mais recentes" é a ordem da própria API (criação do bloco); os demais critérios ordenam aqui.
const ORDENS = {
  recentes: null,
  'maior-valor': (a, b) => Number(b.valor_investido) - Number(a.valor_investido),
  'menor-valor': (a, b) => Number(a.valor_investido) - Number(b.valor_investido),
  score: (a, b) => (b.score ?? -1) - (a.score ?? -1),
  vencimento: (a, b) => a.data_vencimento.localeCompare(b.data_vencimento),
}

// Mantém o ?etiqueta= da URL igual ao filtro (a visão geral abre a tela já filtrada).
function sincronizarUrl(etiqueta) {
  const url = new URL(window.location.href)
  if (etiqueta) url.searchParams.set('etiqueta', etiqueta)
  else url.searchParams.delete('etiqueta')
  window.history.replaceState(null, '', url)
}

function preencherEtiquetas(etiquetaDaUrl) {
  const filtro = $('#filtro-etiqueta')
  const nomes = new Set(blocos.map((b) => b.etiqueta))
  if (etiquetaDaUrl) nomes.add(etiquetaDaUrl)
  for (const nome of [...nomes].sort((a, b) => a.localeCompare(b))) {
    const opcao = criar('option', '', nome)
    opcao.value = nome
    filtro.append(opcao)
  }
  filtro.value = etiquetaDaUrl ?? ''
}

function desenhar() {
  const termo = $('#busca').value.trim()
  const etiqueta = $('#filtro-etiqueta').value
  const lista = $('#cartoes')
  lista.replaceChildren()

  let visiveis = blocos.filter((b) => (!etiqueta || b.etiqueta === etiqueta) && combinaBusca(b, termo))
  const ordem = ORDENS[$('#ordem').value]
  if (ordem) visiveis = [...visiveis].sort(ordem)

  const total = visiveis.reduce((soma, b) => soma + Number(b.valor_investido), 0)
  $('#resumo').textContent = blocos.length ? `${visiveis.length} de ${blocos.length} blocos · ${moeda.format(total)} investidos` : ''

  if (!visiveis.length) {
    lista.append(criar('p', 'vazio', blocos.length ? 'Nenhum bloco encontrado para esses filtros.' : 'Você ainda não investiu em nenhum bloco.'))
    return
  }
  for (const bloco of visiveis) {
    lista.append(
      montarCartao(bloco, {
        valorInvestido: bloco.valor_investido,
        aoDetalhes: () => abrirDetalhe(bloco, { perfil: 'investidor', valorInvestido: bloco.valor_investido }),
      }),
    )
  }
}

function ligarControles() {
  $('#busca').addEventListener('input', desenhar)
  $('#ordem').addEventListener('change', desenhar)
  $('#filtro-etiqueta').addEventListener('change', () => {
    sincronizarUrl($('#filtro-etiqueta').value)
    desenhar()
  })
  $('#ver-tudo').addEventListener('click', () => {
    $('#busca').value = ''
    $('#ordem').value = 'recentes'
    $('#filtro-etiqueta').value = ''
    sincronizarUrl('')
    desenhar()
  })
  ligarDialogoDeDetalhe()
}

function avisar(texto) {
  const estado = $('#estado')
  estado.textContent = texto
  estado.classList.add('erro')
}

async function carregar() {
  $('#estado').textContent = 'Carregando seus investimentos...'
  const resposta = await chamar('GET', '/investimentos')
  if (resposta.status !== 200) {
    avisar(`Não foi possível carregar os seus investimentos: ${textoDoErro(resposta)}`)
    return
  }
  $('#estado').textContent = ''
  blocos = resposta.corpo
  preencherEtiquetas(new URLSearchParams(window.location.search).get('etiqueta'))
  desenhar()
}

aoMudarSessao(async (usuario) => {
  if (!usuario) {
    window.location.href = LOGIN
    return
  }
  const perfil = await chamar('GET', '/auth/me')
  if (await encerrarSeInvalida(perfil)) {
    window.location.href = LOGIN
    return
  }
  if (perfil.status === 200 && perfil.corpo.perfil !== 'investidor') {
    window.location.href = destinoDoPerfil(perfil.corpo.perfil)
    return
  }
  menu.definirUsuario(usuario.email)
  $('#conteudo').hidden = false
  ligarControles()
  if (perfil.status !== 200) {
    avisar(`Não foi possível verificar o seu perfil: ${textoDoErro(perfil)}`)
    return
  }
  await carregar()
})
