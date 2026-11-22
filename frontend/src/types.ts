export type User = { id: number; name: string; email: string; role: string }
export type ChargeStatus = 'ACTIVE' | 'PAID' | 'EXPIRED' | 'CANCELED'
export type Charge = {
  id: number; txid: string; payer_name: string; amount: number; description: string
  status: ChargeStatus; pix_copy_paste: string; location?: string
  created_at: string; updated_at: string
}
export type Receipt = {
  id: number; e2eid: string; txid?: string; payer_name: string; amount: number
  origin: string; description: string; received_at: string
}
export type AppNotification = {
  id: number; receipt_e2eid: string; message: string; created_at: string; read_at: string | null
  payer_name: string; amount: number; txid?: string | null; received_at: string
}
export type PixSyncResult = { checked: number; newReceipts: number; failures: number }
export type DashboardData = {
  receivedToday: number; receivedMonth: number; pendingCharges: number
  paidCharges: number; recentCharges: Charge[]
}

export type BankActor = 'cliente' | 'dono'
export type BankTransaction = {
  id: number; e2eid: string; txid: string; amount: number; description: string
  paymentMethod: 'PIX_KEY' | 'PIX_QR'; createdAt: string; direction: 'IN' | 'OUT'
  counterparty: string; counterpartyKey: string
}
export type BankAccount = {
  actor: BankActor; name: string; document: string; pixKey: string
  balance: number; transactions: BankTransaction[]
}
export type PixRecipient = { name: string; document: string; pixKey: string; amount?: number | null }
