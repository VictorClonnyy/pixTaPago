import { useEffect, useMemo, useState } from 'react'
import { Plus, Search } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import type { Charge } from '../types'
import StatusBadge from '../components/StatusBadge'
import { dateTime, money, shortTxid } from '../lib/format'

export default function Charges() {
  const [charges, setCharges] = useState<Charge[]>([]); const [query, setQuery] = useState('')
  useEffect(() => { api.charges().then(setCharges) }, [])
  const shown = useMemo(() => charges.filter(c => `${c.txid} ${c.payer_name} ${c.description}`.toLowerCase().includes(query.toLowerCase())), [charges, query])
  return <><div className="page-heading"><div><p className="eyebrow">Cobranças</p><h1>Gerencie seus Pix</h1><p>Consulte o status ou crie uma nova cobrança.</p></div><Link className="primary-button compact" to="/charges/new"><Plus /> Nova cobrança</Link></div><section className="panel"><div className="toolbar"><div className="input-wrap search"><Search /><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Buscar por cliente, descrição ou TXID" /></div></div><div className="table-scroll"><table><thead><tr><th>TXID</th><th>Cliente</th><th>Descrição</th><th>Valor</th><th>Status</th><th>Criada em</th><th /></tr></thead><tbody>{shown.map(charge => <tr key={charge.txid}><td className="mono">{shortTxid(charge.txid)}</td><td>{charge.payer_name}</td><td>{charge.description || '—'}</td><td className="amount">{money(charge.amount)}</td><td><StatusBadge status={charge.status} /></td><td>{dateTime(charge.created_at)}</td><td><Link className="row-link" to={`/charges/${charge.txid}`}>Detalhes</Link></td></tr>)}</tbody></table></div>{shown.length === 0 && <p className="empty">Nenhuma cobrança encontrada.</p>}</section></>
}

