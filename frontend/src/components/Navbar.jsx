import { Leaf, LogOut } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { getRole, logout } from '../auth/auth'

const destinations = { resident: '/resident', rwa: '/rwa', gcc: '/gcc', admin: '/admin' }
export default function Navbar() {
  const navigate = useNavigate(); const role = getRole()
  return <header className="border-b border-line bg-paper"><div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4">
    <Link to={destinations[role] || '/login'} className="flex items-center gap-3 text-forest"><span className="grid h-9 w-9 place-items-center bg-terracotta text-paper"><Leaf size={20}/></span><span className="font-display text-xl">SmartSeg</span></Link>
    {role && <div className="flex items-center gap-4"><span className="hidden text-sm capitalize text-moss sm:block">{role} console</span><button onClick={() => { logout(); navigate('/login') }} className="flex items-center gap-2 border border-forest px-3 py-2 text-sm font-semibold text-forest hover:bg-forest hover:text-paper"><LogOut size={16}/> Log out</button></div>}
  </div></header>
}
