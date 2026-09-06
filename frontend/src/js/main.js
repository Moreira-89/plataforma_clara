// Ponto de entrada do frontend.
//
// A URL do backend vem de VITE_API_URL, injetada no build. Em desenvolvimento o
// proxy do vite.config.js atende /api, então o padrão abaixo funciona nos dois
// casos sem mudar código.
const API = import.meta.env.VITE_API_URL ?? '/api'

document.querySelector('#app').textContent = `Plataforma Clara — API: ${API}`
