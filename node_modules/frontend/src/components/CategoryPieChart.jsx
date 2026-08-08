import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { categoryColor } from './WasteFeedTable'
const hex = { PLASTIC: '#3A7CA5', ORGANIC: '#4F8A5B', METAL: '#7A7F85', OTHER: '#D49A29' }
export function categoryData(source) { return Object.entries(source || {}).map(([name, value]) => ({ name, value })) }
export default function CategoryPieChart({ data }) { const chartData = Array.isArray(data) ? data : categoryData(data); return <ResponsiveContainer width="100%" height={240}><PieChart><Pie data={chartData} dataKey="value" nameKey="name" innerRadius={52} outerRadius={82} paddingAngle={3}>{chartData.map((item) => <Cell key={item.name} fill={hex[item.name] || '#D49A29'}/>)}</Pie><Tooltip/><Legend iconType="square"/></PieChart></ResponsiveContainer> }
