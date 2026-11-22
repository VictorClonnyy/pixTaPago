import { useEffect, useState } from 'react'
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { api } from './api'
import type { User } from './types'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Charges from './pages/Charges'
import NewCharge from './pages/NewCharge'
import ChargeDetail from './pages/ChargeDetail'
import Receipts from './pages/Receipts'
import Bank from './pages/Bank'

export default function App() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()
  useEffect(() => { api.me().then(setUser).catch(() => setUser(null)).finally(() => setLoading(false)) }, [])
  if (window.location.pathname === '/cliente' || window.location.pathname === '/dono') {
    return <Routes><Route path="/cliente" element={<Bank actor="cliente" />} /><Route path="/dono" element={<Bank actor="dono" />} /></Routes>
  }
  if (loading) return <div className="boot">Carregando PixTáPago…</div>
  if (!user) return <Routes><Route path="*" element={<Login onLogin={(value) => { setUser(value); navigate('/') }} />} /></Routes>
  const logout = async () => { await api.logout(); setUser(null); navigate('/login') }
  return (
    <Layout user={user} onLogout={logout}>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/charges" element={<Charges />} />
        <Route path="/charges/new" element={<NewCharge />} />
        <Route path="/charges/:txid" element={<ChargeDetail />} />
        <Route path="/receipts" element={<Receipts />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}
