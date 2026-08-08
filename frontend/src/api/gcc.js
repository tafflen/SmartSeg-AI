import api from './client'
export const getAnalytics = () => api.get('/gcc/analytics').then((r) => r.data)
export const getCompliance = () => api.get('/gcc/compliance-report').then((r) => r.data)
