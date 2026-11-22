const request = async <T>(path: string, options: RequestInit = {}): Promise<T> => {
  const response = await fetch(path, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({ message: 'Não foi possível concluir a operação.' }))
    throw new Error(body.message)
  }
  if (response.status === 204) return undefined as T
  return response.json()
}

export const api = {
  me: () => request<import('./types').User>('/api/auth/me'),
  login: (email: string, password: string) => request<import('./types').User>('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  logout: () => request<void>('/api/auth/logout', { method: 'POST' }),
  dashboard: () => request<import('./types').DashboardData>('/api/dashboard'),
  charges: () => request<import('./types').Charge[]>('/api/charges'),
  charge: (txid: string) => request<import('./types').Charge>(`/api/charges/${txid}`),
  createCharge: (data: { amount: number; description: string; payerName: string }) => request<import('./types').Charge>('/api/charges', { method: 'POST', body: JSON.stringify(data) }),
  receipts: (query = '', period: { start?: string; end?: string } = {}) => {
    const params = new URLSearchParams({ q: query })
    if (period.start) params.set('inicio', period.start)
    if (period.end) params.set('fim', period.end)
    return request<import('./types').Receipt[]>(`/api/receipts?${params}`)
  },
  notifications: (onlyUnread = true) => request<import('./types').AppNotification[]>(`/api/notifications${onlyUnread ? '?unread=1' : ''}`),
  readNotification: (id: number) => request<void>(`/api/notifications/${id}/read`, { method: 'POST' }),
  readAllNotifications: () => request<{ updated: number }>('/api/notifications/read-all', { method: 'POST' }),
  syncPix: () => request<import('./types').PixSyncResult>('/api/pix/sync', { method: 'POST' }),
  bankAccount: (actor: import('./types').BankActor) => request<import('./types').BankAccount>(`/api/bank/accounts/${actor}`),
  resolvePixKey: (key: string) => request<import('./types').PixRecipient>(`/api/bank/pix/resolve?key=${encodeURIComponent(key)}`),
  previewPixCode: (pix: string) => request<import('./types').PixRecipient>('/api/bank/pix/preview', { method: 'POST', body: JSON.stringify({ pix }) }),
  transferPix: (actor: import('./types').BankActor, data: { pixKey: string; amount: number; description: string; idempotencyKey: string }) => request<import('./types').BankTransaction>(`/api/bank/accounts/${actor}/pix/transfer`, { method: 'POST', body: JSON.stringify(data) }),
  payPixCode: (actor: import('./types').BankActor, data: { pix: string; amount: number; description: string; idempotencyKey: string }) => request<import('./types').BankTransaction>(`/api/bank/accounts/${actor}/pix/pay`, { method: 'POST', body: JSON.stringify(data) }),
}
