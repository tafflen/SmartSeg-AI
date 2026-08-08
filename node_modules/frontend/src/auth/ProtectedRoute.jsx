import { Navigate } from 'react-router-dom'
import { getRole } from './auth'

export default function ProtectedRoute({ role, children }) {
  const currentRole = getRole()
  if (!localStorage.getItem('smartseg_token') || currentRole !== role) return <Navigate to="/login" replace />
  return children
}
