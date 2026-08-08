import axios from 'axios'

const api = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || 'http://localhost:8000' })
api.interceptors.request.use((request) => {
  const token = localStorage.getItem('smartseg_token')
  if (token) request.headers.Authorization = `Bearer ${token}`
  return request
})
api.interceptors.response.use((response) => response, (error) => {
  if (!error.response) window.dispatchEvent(new CustomEvent('smartseg:backend-status', { detail: { reachable: false } }))
  if (error.response?.status === 401) {
    localStorage.removeItem('smartseg_token'); localStorage.removeItem('smartseg_role')
    if (window.location.pathname !== '/login') window.location.assign('/login')
  }
  return Promise.reject(error)
})
api.interceptors.response.use((response) => { window.dispatchEvent(new CustomEvent('smartseg:backend-status', { detail: { reachable: true } })); return response })
export default api
