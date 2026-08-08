export function decodeToken(token) {
  try { return JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))) } catch { return null }
}
export const getRole = () => localStorage.getItem('smartseg_role') || decodeToken(localStorage.getItem('smartseg_token') || '')?.role
export const logout = () => { localStorage.removeItem('smartseg_token'); localStorage.removeItem('smartseg_role') }
