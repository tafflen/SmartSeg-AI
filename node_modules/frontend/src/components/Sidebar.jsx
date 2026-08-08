import { Activity, BarChart3, Home, ShieldCheck } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { getRole } from '../auth/auth'

const config = { resident: [['/resident', 'My dashboard', Home], ['/resident', 'Live activity', Activity]], rwa: [['/rwa', 'Society overview', Home], ['/rwa', 'Waste analytics', BarChart3]], gcc: [['/gcc', 'Ward overview', ShieldCheck], ['/gcc', 'Analytics', BarChart3]], admin: [['/admin', 'NFC registry', ShieldCheck]] }
export default function Sidebar() { const role = getRole(); return <aside className="hidden w-56 shrink-0 border-r border-line bg-paper p-4 md:block"><p className="mb-4 px-3 text-xs font-semibold uppercase tracking-[.14em] text-moss">Navigate</p>{(config[role] || []).map(([to,label,Icon], index) => <NavLink key={`${label}-${index}`} to={to} className="mb-1 flex items-center gap-3 border-l-2 border-transparent px-3 py-2 text-sm text-ink hover:border-terracotta hover:bg-cream"><Icon size={17}/>{label}</NavLink>)}</aside> }
