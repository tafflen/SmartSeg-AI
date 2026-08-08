import api from './client'
export const triggerFirebaseSync = () => api.post('/admin/sync/firebase').then((r) => r.data)
export const getAdminResidents = () => api.get('/admin/residents').then((r) => r.data)
