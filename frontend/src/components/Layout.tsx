import type { ReactNode } from 'react'
import { Bell, Check, CircleHelp, Home, LogOut, Menu, ReceiptText, WalletCards, X } from 'lucide-react'
import { Link, NavLink } from 'react-router-dom'
import type { AppNotification, User } from '../types'
import Brand from './Brand'
import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { dateTime, money } from '../lib/format'

export default function Layout({ children, user, onLogout }: { children: ReactNode; user: User; onLogout: () => void }) {
  const [open, setOpen] = useState(false)
  const [notifications, setNotifications] = useState<AppNotification[]>([])
  const [paymentAlert, setPaymentAlert] = useState<AppNotification | null>(null)
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [syncWarning, setSyncWarning] = useState('')
  const seenNotifications = useRef<Set<number>>(new Set())

  // UC004/UC006: a confirmação chega ao backend (webhook ou consulta de contingência)
  // e vira uma notificação persistida; avisos pendentes aparecem no próximo acesso.
  useEffect(() => {
    let active = true
    let requestInFlight = false
    const synchronize = async () => {
      if (requestInFlight || document.hidden) return
      requestInFlight = true
      try {
        try {
          const result = await api.syncPix()
          setSyncWarning(result.failures ? 'Não foi possível consultar todas as cobranças no BB.' : '')
        } catch {
          setSyncWarning('A sincronização com o Banco do Brasil está indisponível.')
        }
        const unread = await api.notifications(true)
        if (!active) return
        const fresh = unread.filter(item => !seenNotifications.current.has(item.id))
        unread.forEach(item => seenNotifications.current.add(item.id))
        setNotifications(unread)
        if (fresh.length) {
          setPaymentAlert(fresh[0])
          window.dispatchEvent(new Event('pix-receipts-updated'))
        }
      } catch { /* a próxima consulta tentará novamente */ }
      finally { requestInFlight = false }
    }
    void synchronize()
    const interval = window.setInterval(synchronize, 5000)
    const onVisible = () => { if (!document.hidden) void synchronize() }
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      active = false
      window.clearInterval(interval)
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [])

  useEffect(() => {
    if (!paymentAlert) return
    const timeout = window.setTimeout(() => setPaymentAlert(null), 5500)
    return () => window.clearTimeout(timeout)
  }, [paymentAlert])

  const markRead = (id: number) => {
    setNotifications(current => current.filter(item => item.id !== id))
    void api.readNotification(id).catch(() => undefined)
  }
  const markAllRead = () => {
    setNotifications([])
    void api.readAllNotifications().catch(() => undefined)
  }
  const closeAlert = () => {
    if (paymentAlert) markRead(paymentAlert.id)
    setPaymentAlert(null)
  }
  const links = <>
    <NavLink to="/" end onClick={() => setOpen(false)}><Home size={19} />Dashboard</NavLink>
    <NavLink to="/charges" onClick={() => setOpen(false)}><WalletCards size={19} />Cobranças</NavLink>
    <NavLink to="/receipts" onClick={() => setOpen(false)}><ReceiptText size={19} />Recebimentos</NavLink>
  </>
  return <div className="app-shell">
    <header><Brand /><nav className="desktop-nav">{links}</nav><div className="header-actions"><div className="notification-area"><button className="icon-button" aria-label="Notificações" onClick={() => setNotificationsOpen(value => !value)}><Bell size={20} />{notifications.length > 0 && <span className="notification-dot" />}</button>{notificationsOpen && <div className="notification-panel"><strong>Novos recebimentos</strong>{syncWarning && <small className="notification-warning">{syncWarning}</small>}{notifications.length ? <>{notifications.map(item => <Link key={item.id} to="/receipts" onClick={() => { markRead(item.id); setNotificationsOpen(false) }}><span>Pix recebido de {item.payer_name}<small>{dateTime(item.received_at)}</small></span><b>+ {money(item.amount)}</b></Link>)}<button className="text-button" onClick={markAllRead}>Marcar todas como lidas</button></> : !syncWarning && <small>Nenhuma nova confirmação.</small>}</div>}</div><button className="support"><CircleHelp size={19} /> Suporte</button><div className="user-chip"><span>{user.name.charAt(0)}</span><div><strong>{user.name.split(' ')[0]}</strong><small>{user.role}</small></div></div><button className="icon-button" onClick={onLogout} title="Sair"><LogOut size={19} /></button><button className="menu-button" onClick={() => setOpen(!open)}>{open ? <X /> : <Menu />}</button></div></header>
    {open && <nav className="mobile-nav">{links}</nav>}
    <main>{children}</main>
    {paymentAlert && <div className="payment-alert" role="status" aria-live="polite">
      <span className="payment-alert-check"><Check /></span>
      <div><small>Pagamento confirmado</small><strong>Pix recebido de {paymentAlert.payer_name}</strong><b>+ {money(paymentAlert.amount)}</b></div>
      <button onClick={closeAlert} aria-label="Fechar notificação"><X /></button>
    </div>}
  </div>
}
