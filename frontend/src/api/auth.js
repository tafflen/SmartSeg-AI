import api from './client'
export const login = (payload) => api.post('/auth/login', payload).then((r) => r.data)
