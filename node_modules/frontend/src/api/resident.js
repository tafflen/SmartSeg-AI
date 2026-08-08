import api from './client'
export const getMyProfile = () => api.get('/resident/me').then((r) => r.data)
export const getWallet = () => api.get('/resident/wallet').then((r) => r.data)
export const getHistory = () => api.get('/resident/history?limit=100').then((r) => r.data)
