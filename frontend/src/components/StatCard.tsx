import type { ReactNode } from 'react'
export default function StatCard({ icon, label, value, note }: { icon: ReactNode; label: string; value: string; note: string }) {
  return <article className="stat-card"><div className="stat-icon">{icon}</div><div><span>{label}</span><strong>{value}</strong><small>{note}</small></div></article>
}

