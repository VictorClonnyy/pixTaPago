import { useEffect, useState } from 'react'
import { ArrowRight, CircleDollarSign, CircleCheck, Clock3, ListFilter, Plus, TrendingUp } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import type { DashboardData } from '../types'
import StatCard from '../components/StatCard'
import StatusBadge from '../components/StatusBadge'
import { dateTime, money, shortTxid } from '../lib/format'

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null)
  // Carrega os indicadores e as cobranças recentes da tela T02.
  useEffect(() => {
    let active = true
    const loadSummary = async () => {
      const summary = await api.dashboard()
      if (active) setData(summary)
    }
    void loadSummary()
    return () => { active = false }
  }, [])
  if (!data) return <div className="loading-card">Carregando resumo…</div>
  return <><div className="page-heading"><div><p className="eyebrow">Visão geral</p><h1>Dashboard</h1><p>Acompanhe cobranças e recebimentos em um só lugar.</p></div><Link className="primary-button compact" to="/charges/new"><Plus /> Nova cobrança</Link></div><section className="stats-grid"><StatCard icon={<CircleDollarSign />} label="Recebido hoje" value={money(data.receivedToday)} note="Créditos confirmados" /><StatCard icon={<Clock3 />} label="Cobranças pendentes" value={String(data.pendingCharges)} note="Aguardando pagamento" /><StatCard icon={<CircleCheck />} label="Cobranças pagas" value={String(data.paidCharges)} note="Total confirmado" /><StatCard icon={<TrendingUp />} label="Recebido no mês" value={money(data.receivedMonth)} note="Acumulado do período" /></section><section className="quick-grid"><Link to="/charges/new" className="quick-card"><span><Plus /></span><div><strong>Gerar cobrança</strong><small>Crie um QR Code Pix</small></div><ArrowRight /></Link><Link to="/charges" className="quick-card"><span><ListFilter /></span><div><strong>Consultar status</strong><small>Localize pelo TXID</small></div><ArrowRight /></Link></section><section className="panel"><div className="panel-title"><div><p className="eyebrow">Movimentação</p><h2>Cobranças recentes</h2></div><Link to="/charges">Ver todas <ArrowRight /></Link></div><div className="table-scroll"><table><thead><tr><th>TXID</th><th>Cliente</th><th>Valor</th><th>Status</th><th>Atualização</th><th /></tr></thead><tbody>{data.recentCharges.map(charge => <tr key={charge.txid}><td className="mono">{shortTxid(charge.txid)}</td><td>{charge.payer_name}</td><td className="amount">{money(charge.amount)}</td><td><StatusBadge status={charge.status} /></td><td>{dateTime(charge.updated_at)}</td><td><Link className="row-link" to={`/charges/${charge.txid}`}>Abrir</Link></td></tr>)}</tbody></table></div></section></>
}

