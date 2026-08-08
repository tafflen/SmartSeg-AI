import { Award } from 'lucide-react'
export default function RewardBadge({ points }) { return <span className="inline-flex items-center gap-1 border border-terracotta bg-[#fff2df] px-2 py-1 text-xs font-semibold text-clay"><Award size={14}/>{points} pts</span> }
