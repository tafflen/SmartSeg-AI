import api from './client'
export const getSummary = () => api.get('/rwa/dashboard-summary').then((r) => r.data)
export const getResidents = () => api.get('/rwa/residents?limit=200').then((r) => r.data)
export const getWasteEvents = (filters = {}) => api.get('/rwa/waste-events', { params: { limit: 200, ...filters } }).then((r) => r.data)
