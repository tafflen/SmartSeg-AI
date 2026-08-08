import RewardBadge from './RewardBadge'

const colors = { PLASTIC: 'bg-plastic', ORGANIC: 'bg-organic', METAL: 'bg-metal', OTHER: 'bg-other' }
export const categoryColor = (category) => colors[category] || colors.OTHER
export default function WasteFeedTable({ events = [], showResident = false, emptyLabel = 'No waste events yet.' }) {
  return <div className="overflow-x-auto"><table className="w-full min-w-[520px] text-sm"><thead><tr className="border-b border-line"><th className="table-head py-3">Category</th>{showResident && <th className="table-head py-3">Resident</th>}<th className="table-head py-3">When</th><th className="table-head py-3">Weight</th><th className="table-head py-3">Reward</th></tr></thead><tbody>{events.map((event) => <tr key={event.id} className="border-b border-line/70 last:border-0"><td className="py-3 font-semibold"><span className={`category-dot ${categoryColor(event.category)}`}/>{event.category}</td>{showResident && <td className="py-3">#{event.resident_id}</td>}<td className="py-3 text-moss">{new Date(event.timestamp).toLocaleString()}</td><td className="py-3">{event.weight_grams ?? '—'} g</td><td className="py-3"><RewardBadge points={event.reward_points}/></td></tr>)}{!events.length && <tr><td colSpan={showResident ? 5 : 4} className="py-8 text-center text-moss">{emptyLabel}</td></tr>}</tbody></table></div>
}
