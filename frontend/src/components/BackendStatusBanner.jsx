import { useEffect, useState } from 'react'
import { WifiOff } from 'lucide-react'

export default function BackendStatusBanner() {
  const [offline, setOffline] = useState(false)
  useEffect(() => { const listener = (event) => setOffline(!event.detail.reachable); window.addEventListener('smartseg:backend-status', listener); return () => window.removeEventListener('smartseg:backend-status', listener) }, [])
  if (!offline) return null
  return <div className="mb-5 flex items-center gap-2 border-l-4 border-clay bg-[#fff2ed] p-3 text-sm text-clay"><WifiOff size={17}/><span><b>Backend unreachable.</b> Dashboard data will refresh automatically when the local API returns.</span></div>
}
