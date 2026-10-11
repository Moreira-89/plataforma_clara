import { chamar, textoDoErro } from '../../nucleo/api.js'
import { aoMudarSessao } from '../../nucleo/firebase.js'
import { montarMenu } from '../../nucleo/menu.js'
import { LOGIN, destinoDoPerfil, encerrarSeInvalida } from '../../nucleo/rotas.js'
import { $ } from '../../nucleo/ui.js'

// A mesma tela serve a gestora e o investidor; o perfil vem do <body data-perfil>.
const PERFIL_DA_PAGINA = document.body.dataset.perfil
const moeda = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
const SEM_SCORE = '—'
const AVISO_SCORE = 'Score de risco indisponível: a fonte do score ainda não foi integrada.'

const menu = montarMenu(PERFIL_DA_PAGINA)
let blocos = []

const codigoCurto = (id) => id.slice(0, 8).toUpperCase()
const dataBr = (iso) => iso.split('-').reverse().join('/')
const cnpjFormatado = (c) => c.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5')

function criar(tag, classe, texto) {
  const el = document.createElement(tag)
  if (classe) el.className = classe
  if (texto !== undefined) el.textContent = texto
  return el
}

function seloEtiqueta(cor) {
  const selo = criar('i', 'selo-etiqueta')
  selo.style.background = cor ?? 'var(--surface-strong)'
  selo.setAttribute('aria-hidden', 'true')
  return selo
}

// Busca pelo código (início do id ou código completo) ou pelo nome da etiqueta.
function combina(bloco, termo) {
  if (!termo) return true
  const alvo = termo.toLowerCase().replace(/\s+/g, '')
  const campos = [bloco.id_bloco, bloco.codigo_identificacao, bloco.etiqueta]
  return campos.some((c) => c.toLowerCase().replace(/\s+/g, '').includes(alvo))
}

function desenharCartoes() {
  const termo = $('#busca').value.trim()
  const lista = $('#cartoes')
  lista.replaceChildren()
  // A ordem "mais recentes" é a da própria API; "maior score" só entra quando o score existir.
  const visiveis = blocos.filter((b) => combina(b, termo))

  if (!visiveis.length) {
    lista.append(criar('p', 'vazio', blocos.length ? 'Nenhum bloco encontrado para essa busca.' : 'Nenhum bloco criado ainda.'))
    return
  }

  for (const bloco of visiveis) {
    const cartao = criar('article', 'cartao cartao-bloco')

    const topo = criar('div', 'cartao-topo')
    const etiqueta = criar('span', 'etiqueta-bloco')
    etiqueta.append(seloEtiqueta(bloco.cor), criar('span', '', bloco.etiqueta))
    topo.append(etiqueta, criar('span', 'codigo-bloco', `Cod: ${codigoCurto(bloco.id_bloco)}`))

    const score = criar('div', 'linha-score')
    const valor = criar('strong', '', SEM_SCORE)
    valor.title = AVISO_SCORE
    score.append(criar('span', '', 'Score de risco'), valor)

    const empresas = `${bloco.quantidade_empresas} ${bloco.quantidade_empresas === 1 ? 'empresa' : 'empresas'}`
    const meta = criar('p', 'meta-bloco', `${empresas} · vence em ${dataBr(bloco.data_vencimento)}`)

    const botao = criar('button', 'btn btn-secundario', 'Ver mais detalhes')
    botao.type = 'button'
    botao.addEventListener('click', () => abrirDetalhe(bloco))

    cartao.append(topo, score, meta, botao)
    lista.append(cartao)
  }
}

function linha(rotulo, valor) {
  const caixa = criar('div')
  caixa.append(criar('span', '', rotulo), criar('strong', '', valor))
  return caixa
}

function tabelaEmpresas(empresas) {
  const rolagem = criar('div', 'tabela-detalhe')
  const tabela = criar('table', 'tabela')
  const cabecalho = criar('tr')
  for (const titulo of ['Empresa', 'CNPJ', 'Ramo', 'Capital estimado', 'Score de risco']) {
    cabecalho.append(criar('th', '', titulo))
  }
  const topo = criar('thead')
  topo.append(cabecalho)
  tabela.append(topo)
  const corpo = criar('tbody')
  for (const e of empresas) {
    const tr = criar('tr')
    tr.append(
      criar('td', '', e.nome_fantasia ?? `Empresa ${e.id_empresa}`),
      criar('td', '', cnpjFormatado(e.cnpj)),
      criar('td', '', e.ramo_atividade ?? '—'),
      criar('td', 'numero', moeda.format(Number(e.capital_estimado))),
    )
    const score = criar('td', 'numero', SEM_SCORE)
    score.title = AVISO_SCORE
    tr.append(score)
    corpo.append(tr)
  }
  tabela.append(corpo)
  rolagem.append(tabela)
  return rolagem
}

async function abrirDetalhe(resumo) {
  const dialogo = $('#detalhe')
  const titulo = $('#detalhe-titulo')
  const corpo = $('#detalhe-corpo')
  titulo.replaceChildren(seloEtiqueta(resumo.cor), criar('span', '', `${resumo.etiqueta} · ${codigoCurto(resumo.id_bloco)}`))
  corpo.replaceChildren(criar('p', 'mensagem', 'Carregando...'))
  dialogo.showModal()

  const resposta = await chamar('GET', `/blocos/${resumo.id_bloco}`)
  if (await encerrarSeInvalida(resposta)) {
    window.location.href = LOGIN
    return
  }
  if (resposta.status !== 200) {
    corpo.replaceChildren(criar('p', 'mensagem erro', `Não foi possível carregar o bloco: ${textoDoErro(resposta)}`))
    return
  }

  const bloco = resposta.corpo
  const resumoDetalhe = criar('div', 'resumo-detalhe')
  resumoDetalhe.append(
    linha('Etiqueta', bloco.etiqueta),
    linha('Data de vencimento', dataBr(bloco.data_vencimento)),
    linha('Score de risco do bloco', SEM_SCORE),
  )
  const partes = [resumoDetalhe]

  // Responsável e observação são notas de gestão: só a gestora vê.
  if (PERFIL_DA_PAGINA === 'gestora') {
    resumoDetalhe.append(linha('Responsável técnico', bloco.responsavel_tecnico), linha('Criado em', dataBr(bloco.data_criacao)))
    if (bloco.observacao) partes.push(criar('p', 'observacao-detalhe', `Observação: ${bloco.observacao}`))
  }

  partes.push(tabelaEmpresas(bloco.empresas), criar('p', 'nota-score', AVISO_SCORE))

  if (PERFIL_DA_PAGINA === 'investidor') {
    const rodape = criar('div', 'rodape-detalhe')
    const alocar = criar('button', 'btn btn-primario', 'Alocar dinheiro')
    alocar.type = 'button'
    alocar.disabled = true
    rodape.append(criar('small', '', 'Em breve'), alocar)
    partes.push(rodape)
  }
  corpo.replaceChildren(...partes)
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
  const dialogo = $('#detalhe')
  $('#detalhe-fechar').addEventListener('click', () => dialogo.close())
  // Clique no fundo escuro (fora do conteúdo) também fecha.
  dialogo.addEventListener('click', (evento) => {
    if (evento.target === dialogo) dialogo.close()
  })
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
