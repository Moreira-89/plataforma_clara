/*
 * Visão geral da gestora: totais no topo e os gráficos do mercado, dos blocos, dos setores e dos alertas.
 *
 * COMO FUNCIONA:
 *   1. Confere a sessão e o perfil; quem não é gestora volta para a sua tela.
 *   2. Lê `GET /dashboard/gestora` de uma vez e entrega cada fatia ao seu gráfico (graficos.js).
 *   3. Dados do mercado são da CVM (Informe Mensal FIDC); score e nota dos blocos vêm das views do BigQuery.
 */
import { chamar, textoDoErro } from '../../nucleo/api.js'
import { aoMudarSessao } from '../../nucleo/firebase.js'
import { montarMenu } from '../../nucleo/menu.js'
import { LOGIN, destinoDoPerfil, encerrarSeInvalida } from '../../nucleo/rotas.js'
import { $ } from '../../nucleo/ui.js'
import { criar, moeda, moedaCompacta } from '../blocos/cartao.js'
import {
  COMPONENTES,
  graficoBlocos,
  graficoCapitalPorNota,
  graficoComposicao,
  graficoDistribuicao,
  graficoExposicao,
  graficoInadimplencia,
  graficoPatrimonio,
  graficoRating,
  graficoSetores,
  tabelaAlertas,
} from './graficos.js'

const menu = montarMenu('gestora')

const pct = (v, casas = 2) => `${Number(v).toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas })}%`
const mesAno = (iso) => new Date(`${iso}T00:00:00`).toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })

function avisar(texto) {
  const estado = $('#estado')
  estado.textContent = texto
  estado.classList.add('erro')
}

function desenharTotais({ resumo_blocos: blocos, mercado }) {
  $('#capital').textContent = moeda.format(blocos.capital_total)
  $('#qtd-blocos').textContent = blocos.quantidade
  $('#score-medio').textContent = blocos.score_medio == null ? '—' : blocos.score_medio.toLocaleString('pt-BR', { maximumFractionDigits: 1 })
  $('#inadimplencia').textContent = mercado ? pct(mercado.inadimplencia) : '—'
  $('#pl-mercado').textContent = mercado ? moedaCompacta.format(mercado.pl_total) : '—'
  $('#fonte').textContent = mercado ? `Mercado de FIDCs: CVM, Informe Mensal FIDC, competência de ${mesAno(mercado.referencia)}.` : ''
}

// Legenda dos 4 componentes do score, com a mesma cor dos segmentos.
function desenharLegendaDaComposicao() {
  $('#g-comp-legenda').replaceChildren(
    ...COMPONENTES.map((c) => {
      const item = criar('li')
      const marca = criar('i', 'legenda-barra')
      marca.style.background = c.cor
      item.append(marca, c.rotulo)
      return item
    }),
  )
}

function desenhar(dados) {
  desenharTotais(dados)
  if (dados.serie_mercado.length) {
    graficoInadimplencia($('#g-inad'), dados.serie_mercado)
    graficoPatrimonio($('#g-pl'), dados.serie_mercado)
  }
  graficoRating($('#g-rating'), dados.rating)
  graficoDistribuicao($('#g-dist'), dados.distribuicao_scores)
  graficoBlocos($('#g-blocos'), dados.blocos)
  desenharLegendaDaComposicao()
  graficoComposicao($('#g-comp'), dados.blocos)
  graficoCapitalPorNota($('#g-nota'), dados.capital_por_nota)
  graficoExposicao($('#g-expo'), dados.exposicao)
  graficoSetores($('#g-setores'), dados.setores)
  $('#g-alertas-sub').textContent = dados.alertas.length
    ? `${dados.alertas.length} empresas dos seus blocos têm alerta no score, da menor nota para a maior.`
    : 'Nenhuma empresa dos seus blocos tem alerta no score.'
  tabelaAlertas($('#g-alertas'), dados.alertas)
}

async function carregar() {
  $('#estado').textContent = 'Carregando a visão geral...'
  const resposta = await chamar('GET', '/dashboard/gestora')
  if (resposta.status !== 200) {
    avisar(`Não foi possível carregar a visão geral: ${textoDoErro(resposta)}`)
    return
  }
  $('#estado').textContent = ''
  $('#visao').hidden = false
  desenhar(resposta.corpo)
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
  if (perfil.status === 200 && perfil.corpo.perfil !== 'gestora') {
    window.location.href = destinoDoPerfil(perfil.corpo.perfil)
    return
  }
  menu.definirUsuario(usuario.email)
  $('#conteudo').hidden = false
  if (perfil.status !== 200) {
    avisar(`Não foi possível verificar o seu perfil: ${textoDoErro(perfil)}`)
    return
  }
  await carregar()
})
