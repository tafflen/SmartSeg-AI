import api from './client'
export const getLiveEvents = () => api.get('/waste/live?limit=20').then((r) => r.data)
