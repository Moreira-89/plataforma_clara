import { $ } from './ui.js'

// A home funciona sem o Firebase; ele só troca os botões quando há sessão.
import('./firebase.js')
  .then(({ aoMudarSessao }) =>
    aoMudarSessao((usuario) => {
      if (usuario) {
        $('#nav-acoes').innerHTML = '<a class="btn btn-primario" href="/painel.html">Ir para o painel</a>'
      }
    }),
  )
  .catch(() => {})
