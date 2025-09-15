export function ProgressBar({ current, total }: { current: number; total: number }) {
  const pct = total ? (current / total) * 100 : 0
  return (
    <div className="w-full bg-gray-200 h-2 rounded">
      <div className="bg-blue-500 h-2 rounded" style={{ width: pct + '%' }}></div>
    </div>
  )
}
