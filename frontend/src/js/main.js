// Em dev o proxy do Vite atende /api; em produção a URL vem do build.
const API = import.meta.env.VITE_API_URL ?? '/api'

document.querySelector('#app').textContent = `Plataforma Clara — API: ${API}`
