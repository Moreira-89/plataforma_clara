/*
 * Lista de blocos em cartões, usada pela Gestão de Blocos, por Blocos de Liquidez e por Blocos Investidos.
 *
 * COMO FUNCIONA:
 *   1. O modo vem de <body data-modo>: "gestora" e "liquidez" leem GET /blocos; "investidos", GET /investimentos.
 *   2. Busca (código ou etiqueta), filtro de etiqueta (só em Blocos Investidos) e ordenação refazem os cartões.
 *   3. Clicar no cartão abre a ficha (detalhe.js); na Gestão, "Criar novo bloco" abre o formulário.
 */
import { chamar, textoDoErro } from '../../nucleo/api.js'
import { aoMudarSessao } from '../../nucleo/firebase.js'
import { montarMenu } from '../../nucleo/menu.js'
import { LOGIN, destinoDoPerfil, encerrarSeInvalida } from '../../nucleo/rotas.js'
import { $, mostrarToast } from '../../nucleo/ui.js'
import { codigoCurto, combinaBusca, criar, moeda, moedaCompacta, montarCartao } from './cartao.js'
import { abrirDetalhe, ligarDialogoDeDetalhe } from './detalhe.js'

const PERFIL = document.body.dataset.perfil
const MODO = document.body.dataset.modo
const investidos = MODO === 'investidos'
const menu = montarMenu(PERFIL)
let blocos = []
let novoId = null

const valorDe = (bloco) => Number(bloco.valor_investido)
// "Mais recentes" ordena pela criação do bloco; os demais critérios são numéricos ou de data.
const ORDENS = {
  recentes: { rotulo: 'Mais recentes', comparar: (a, b) => b.data_criacao.localeCompare(a.data_criacao) },
  score: { rotulo: 'Maior score', comparar: (a, b) => (b.score ?? -1) - (a.score ?? -1) },
  'maior-valor': { rotulo: 'Maior investimento', comparar: (a, b) => valorDe(b) - valorDe(a) },
  'menor-valor': { rotulo: 'Menor investimento', comparar: (a, b) => valorDe(a) - valorDe(b) },
  vencimento: { rotulo: 'Vencimento mais próximo', comparar: (a, b) => a.data_vencimento.localeCompare(b.data_vencimento) },
}
const ORDENS_DO_MODO = investidos ? ['recentes', 'maior-valor', 'menor-valor', 'score', 'vencimento'] : ['recentes', 'score']

function preencherOrdens() {
  const seletor = $('#ordem')
  for (const chave of ORDENS_DO_MODO) {
    const opcao = criar('option', '', ORDENS[chave].rotulo)
    opcao.value = chave
    seletor.append(opcao)
  }
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
  filtro.replaceChildren(Object.assign(criar('option', '', 'Todas as etiquetas'), { value: '' }))
  for (const nome of [...nomes].sort((a, b) => a.localeCompare(b))) {
    const opcao = criar('option', '', nome)
    opcao.value = nome
    filtro.append(opcao)
  }
  filtro.value = etiquetaDaUrl ?? ''
}

function atualizarIndicadores() {
  if (MODO !== 'gestora') return
  $('#indicador-blocos').textContent = blocos.length
  $('#indicador-capital').textContent = moedaCompacta.format(blocos.reduce((soma, b) => soma + Number(b.capital_total), 0))
}

function desenhar() {
  const termo = $('#busca').value.trim()
  const etiqueta = investidos ? $('#filtro-etiqueta').value : ''
  const lista = $('#cartoes')
  lista.replaceChildren()

  const visiveis = blocos
    .filter((b) => (!etiqueta || b.etiqueta === etiqueta) && combinaBusca(b, termo))
    .sort(ORDENS[$('#ordem').value].comparar)

  if (MODO === 'investidos') {
    const total = visiveis.reduce((soma, b) => soma + valorDe(b), 0)
    $('#resumo').textContent = `${visiveis.length} ${visiveis.length === 1 ? 'bloco' : 'blocos'} · ${moeda.format(total)} investidos`
  } else if (MODO === 'liquidez') {
    $('#resumo').textContent = `${visiveis.length} ${visiveis.length === 1 ? 'bloco disponível' : 'blocos disponíveis'}`
  }

  if (!visiveis.length) {
    const vazio = investidos && !blocos.length ? 'Você ainda não investiu em nenhum bloco.' : 'Nenhum bloco encontrado.'
    lista.append(criar('p', 'vazio', vazio))
    return
  }
  visiveis.forEach((bloco, indice) => {
    const aoDetalhes = () => abrirDetalhe(bloco, { perfil: PERFIL, valorInvestido: investidos ? bloco.valor_investido : undefined })
    lista.append(
      montarCartao(bloco, {
        valorInvestido: investidos ? bloco.valor_investido : undefined,
        mostrarCapital: MODO === 'gestora',
        destacado: bloco.id_bloco === novoId,
        indice,
        aoDetalhes,
      }),
    )
  })
}

function avisar(texto) {
  const estado = $('#estado')
  estado.textContent = texto
  estado.classList.add('erro')
}

async function carregar() {
  $('#estado').classList.remove('erro')
  $('#estado').textContent = investidos ? 'Carregando seus investimentos...' : 'Carregando blocos...'
  const resposta = await chamar('GET', investidos ? '/investimentos' : '/blocos')
  if (resposta.status !== 200) {
    avisar(`Não foi possível carregar ${investidos ? 'os seus investimentos' : 'os blocos'}: ${textoDoErro(resposta)}`)
    return
  }
  $('#estado').textContent = ''
  blocos = resposta.corpo
  if (investidos) preencherEtiquetas(new URLSearchParams(window.location.search).get('etiqueta'))
  atualizarIndicadores()
  desenhar()
}

function limpar() {
  $('#busca').value = ''
  $('#ordem').value = 'recentes'
  if (investidos) {
    $('#filtro-etiqueta').value = ''
    sincronizarUrl('')
  }
  desenhar()
}

// Formulário de novo bloco em pop-up; ao criar, fecha, avisa e recarrega a lista com o bloco novo em destaque.
function ligarCriacao() {
  const dialogo = $('#dialogo-bloco')
  $('#criar-bloco').addEventListener('click', async () => {
    document.body.style.overflow = 'hidden'
    dialogo.showModal()
    const { prepararFormulario } = await import('../gestora/novo-bloco.js')
    await prepararFormulario({
      aoCriar: async (bloco) => {
        dialogo.close()
        novoId = bloco.id_bloco
        mostrarToast(`Bloco ${bloco.etiqueta} · ${codigoCurto(bloco.id_bloco)} criado.`)
        $('#busca').value = ''
        $('#ordem').value = 'recentes'
        await carregar()
      },
    })
  })
  $('#dialogo-bloco-fechar').addEventListener('click', () => dialogo.close())
  dialogo.addEventListener('click', (evento) => {
    if (evento.target === dialogo) dialogo.close()
  })
  dialogo.addEventListener('close', () => (document.body.style.overflow = ''))
}

function ligarControles() {
  preencherOrdens()
  $('#busca').addEventListener('input', desenhar)
  $('#ordem').addEventListener('change', desenhar)
  $('#limpar').addEventListener('click', limpar)
  if (investidos) {
    $('#filtro-etiqueta').addEventListener('change', () => {
      sincronizarUrl($('#filtro-etiqueta').value)
      desenhar()
    })
  }
  ligarDialogoDeDetalhe()
  if (MODO === 'gestora') ligarCriacao()
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
  if (perfil.status === 200 && perfil.corpo.perfil !== PERFIL) {
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
