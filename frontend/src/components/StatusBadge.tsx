import { Check, Clock3, X } from 'lucide-react'
import type { ChargeStatus } from '../types'
const labels = { ACTIVE: 'Pendente', PAID: 'Pago', EXPIRED: 'Expirado', CANCELED: 'Cancelado' }
export default function StatusBadge({ status }: { status: ChargeStatus }) {
  return <span className={`status status-${status.toLowerCase()}`}>{status === 'PAID' ? <Check /> : status === 'ACTIVE' ? <Clock3 /> : <X />}{labels[status]}</span>
}

