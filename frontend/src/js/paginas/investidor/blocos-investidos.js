import { chamar, textoDoErro } from '../../nucleo/api.js'
import { aoMudarSessao } from '../../nucleo/firebase.js'
import { montarMenu } from '../../nucleo/menu.js'
import { LOGIN, destinoDoPerfil, encerrarSeInvalida } from '../../nucleo/rotas.js'
import { $ } from '../../nucleo/ui.js'
import { criar, montarCartao, seloEtiqueta } from '../blocos/cartao.js'
import { abrirDetalhe, ligarDialogoDeDetalhe } from '../blocos/detalhe.js'

const menu = montarMenu('investidor')

// Agrupa por pedra. A API já devolve do bloco mais recente ao mais antigo, então a ordem dos
// grupos (pelo bloco mais novo de cada um) e a dos cartões dentro de cada grupo seguem essa regra.
function agruparPorEtiqueta(blocos) {
  const grupos = new Map()
  for (const bloco of blocos) {
    if (!grupos.has(bloco.etiqueta)) grupos.set(bloco.etiqueta, { cor: bloco.cor, blocos: [] })
    grupos.get(bloco.etiqueta).blocos.push(bloco)
  }
  return grupos
}

function desenhar(blocos) {
  const raiz = $('#grupos')
  raiz.replaceChildren()
  if (!blocos.length) {
    raiz.append(criar('p', 'vazio', 'Você ainda não investiu em nenhum bloco.'))
    return
  }

  for (const [etiqueta, grupo] of agruparPorEtiqueta(blocos)) {
    const secao = criar('section', 'grupo-etiqueta')
    secao.style.setProperty('--cor-etiqueta', grupo.cor ?? 'var(--surface-strong)')

    const topo = criar('div', 'grupo-topo')
    const quantidade = grupo.blocos.length
    topo.append(
      seloEtiqueta(grupo.cor),
      criar('h2', '', etiqueta),
      criar('span', 'grupo-quantidade', `${quantidade} ${quantidade === 1 ? 'bloco' : 'blocos'}`),
    )

    const grade = criar('div', 'grade-blocos')
    for (const bloco of grupo.blocos) {
      grade.append(
        montarCartao(bloco, {
          valorInvestido: bloco.valor_investido,
          aoDetalhes: () => abrirDetalhe(bloco, { perfil: 'investidor', valorInvestido: bloco.valor_investido }),
        }),
      )
    }
    secao.append(topo, grade)
    raiz.append(secao)
  }
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
  if (perfil.status === 200 && perfil.corpo.perfil !== 'investidor') {
    window.location.href = destinoDoPerfil(perfil.corpo.perfil)
    return
  }
  menu.definirUsuario(usuario.email)
  $('#conteudo').hidden = false
  ligarDialogoDeDetalhe()
  if (perfil.status !== 200) {
    avisar(`Não foi possível verificar o seu perfil: ${textoDoErro(perfil)}`)
    return
  }
  await carregar()
})
