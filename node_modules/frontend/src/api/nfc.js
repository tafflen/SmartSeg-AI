import api from './client'
export const scanNfc = (nfc_uid) => api.post('/nfc/scan', { nfc_uid }).then((r) => r.data)
export const getLastSeenUid = () => api.get('/nfc/last-seen').then((r) => r.data)
export const registerNfc = (nfc_uid, resident_id) => api.post('/nfc/register', { nfc_uid, resident_id }).then((r) => r.data)
