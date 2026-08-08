import { useEffect, useMemo, useState } from 'react'
import { CircleDollarSign, Recycle, Scale, Wifi } from 'lucide-react'
import { getHistory, getMyProfile, getWallet } from '../../api/resident'
import { getLiveEvents } from '../../api/waste'
import CategoryPieChart from '../../components/CategoryPieChart'
import StatCard from '../../components/StatCard'
import WasteFeedTable from '../../components/WasteFeedTable'

export default function ResidentDashboard() {
  const [profile, setProfile] = useState(null); const [wallet, setWallet] = useState(null); const [history, setHistory] = useState([]); const [live, setLive] = useState([]); const [error, setError] = useState('')
  useEffect(() => { Promise.all([getMyProfile(), getWallet(), getHistory(), getLiveEvents()]).then(([p,w,h,l]) => {setProfile(p);setWallet(w);setHistory(h);setLive(l)}).catch(() => setError('Unable to load your SmartSeg data.')) }, [])
  useEffect(() => { const base = (import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/^http/, 'ws'); let socket; try { socket = new WebSocket(`${base}/ws/live-feed`); socket.onmessage = (message) => { const event = JSON.parse(message.data); setLive((current) => [event, ...current.filter((item) => item.id !== event.id)].slice(0, 20)) } } catch { /* WebSocket setup can fail in restricted networks. */ }
    // Fallback polling keeps the live panel useful if a proxy blocks WebSockets.
    const poller = setInterval(() => getLiveEvents().then(setLive).catch(() => {}), 5000); return () => { socket?.close(); clearInterval(poller) }
  }, [])
  const breakdown = useMemo(() => history.reduce((totals, item) => ({ ...totals, [item.category]: (totals[item.category] || 0) + 1 }), {}), [history])
  return <div className="space-y-7"><div><p className="text-sm text-moss">Resident portal</p><h1 className="text-4xl text-forest">Hello, {profile?.name?.split(' ')[0] || 'neighbour'}.</h1></div>{error && <p className="border-l-4 border-clay bg-[#fff2ed] p-3 text-clay">{error}</p>}<div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"><StatCard icon={CircleDollarSign} label="Reward balance" value={`${wallet?.points ?? 0} pts`} trend={`₹${wallet?.redeemable_value ?? 0} estimated value`} tone="terracotta"/><StatCard icon={Recycle} label="Items segregated" value={history.length}/><StatCard icon={Scale} label="Latest reward" value={`${history[0]?.reward_points ?? 0} pts`} tone="moss"/></div><div className="grid gap-6 lg:grid-cols-[1.15fr_.85fr]"><section className="panel p-6"><h2 className="section-title">Recent contributions</h2><div className="mt-4"><WasteFeedTable events={history.slice(0, 8)}/></div></section><section className="panel p-6"><h2 className="section-title">Your sorting mix</h2><CategoryPieChart data={breakdown}/></section></div><section className="panel p-6"><div className="flex items-center gap-2"><Wifi size={18} className="text-terracotta"/><h2 className="section-title">Live feed</h2></div><p className="mt-1 text-sm text-moss">Freshly classified items from the SmartSeg station.</p><div className="mt-4"><WasteFeedTable events={live}/></div></section></div>
}
