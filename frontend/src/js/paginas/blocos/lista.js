import { chamar, textoDoErro } from '../../nucleo/api.js'
import { aoMudarSessao } from '../../nucleo/firebase.js'
import { montarMenu } from '../../nucleo/menu.js'
import { LOGIN, destinoDoPerfil, encerrarSeInvalida } from '../../nucleo/rotas.js'
import { $ } from '../../nucleo/ui.js'
import { combinaBusca, criar, montarCartao } from './cartao.js'
import { abrirDetalhe, ligarDialogoDeDetalhe } from './detalhe.js'

// A mesma tela serve a gestora e o investidor; o perfil vem do <body data-perfil>.
const PERFIL_DA_PAGINA = document.body.dataset.perfil
const menu = montarMenu(PERFIL_DA_PAGINA)
let blocos = []

function desenharCartoes() {
  const termo = $('#busca').value.trim()
  const lista = $('#cartoes')
  lista.replaceChildren()
  // "Mais recentes" é a ordem da própria API; "Maior score" ordena do maior para o menor, sem score por último.
  let visiveis = blocos.filter((b) => combinaBusca(b, termo))
  if ($('#ordem').value === 'score') visiveis = [...visiveis].sort((a, b) => (b.score ?? -1) - (a.score ?? -1))

  if (!visiveis.length) {
    lista.append(criar('p', 'vazio', blocos.length ? 'Nenhum bloco encontrado para essa busca.' : 'Nenhum bloco criado ainda.'))
    return
  }

  for (const bloco of visiveis) lista.append(montarCartao(bloco, { aoDetalhes: () => abrirDetalhe(bloco, { perfil: PERFIL_DA_PAGINA }) }))
}

async function carregar(aviso = '') {
  $('#estado').textContent = 'Carregando blocos...'
  const resposta = await chamar('GET', '/blocos')
  if (resposta.status !== 200) {
    const estado = $('#estado')
    estado.textContent = `Não foi possível carregar os blocos: ${textoDoErro(resposta)}`
    estado.classList.add('erro')
    return
  }
  $('#estado').textContent = aviso
  blocos = resposta.corpo
  desenharCartoes()
}

function ligarControles() {
  $('#busca').addEventListener('input', desenharCartoes)
  $('#ordem').addEventListener('change', desenharCartoes)
  $('#ver-tudo').addEventListener('click', () => {
    $('#busca').value = ''
    $('#ordem').value = 'recentes'
    desenharCartoes()
  })
  ligarDialogoDeDetalhe()
  if (PERFIL_DA_PAGINA === 'gestora') ligarCriacao()
}

// Formulário de novo bloco em pop-up; ao criar, fecha e recarrega a lista com o aviso.
function ligarCriacao() {
  const dialogo = $('#dialogo-bloco')
  $('#criar-bloco').addEventListener('click', async () => {
    dialogo.showModal()
    const { prepararFormulario } = await import('../gestora/novo-bloco.js')
    await prepararFormulario({
      aoCriar: async (bloco) => {
        dialogo.close()
        await carregar(`Bloco criado: ${bloco.codigo_identificacao}`)
      },
    })
  })
  $('#dialogo-bloco-fechar').addEventListener('click', () => dialogo.close())
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
  if (perfil.status === 200 && perfil.corpo.perfil !== PERFIL_DA_PAGINA) {
    window.location.href = destinoDoPerfil(perfil.corpo.perfil)
    return
  }
  menu.definirUsuario(usuario.email)
  $('#conteudo').hidden = false
  ligarControles()
  if (perfil.status !== 200) {
    const estado = $('#estado')
    estado.textContent = `Não foi possível verificar o seu perfil: ${textoDoErro(perfil)}`
    estado.classList.add('erro')
    return
  }
  await carregar()
})
