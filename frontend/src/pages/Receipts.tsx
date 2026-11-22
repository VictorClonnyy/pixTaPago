import { useEffect, useMemo, useState } from 'react'
import { CircleCheck, Clock3, Search, Wallet } from 'lucide-react'
import { api } from '../api'
import type { Receipt } from '../types'
import StatCard from '../components/StatCard'
import { dateTime, money, shortTxid } from '../lib/format'

export default function Receipts() {
  const [receipts, setReceipts] = useState<Receipt[]>([]); const [query, setQuery] = useState(''); const [selected, setSelected] = useState<Receipt | null>(null)
  const [start, setStart] = useState(''); const [end, setEnd] = useState(''); const [error, setError] = useState('')
  useEffect(() => {
    let active = true
    const load = () => api.receipts('', { start, end }).then(rows => {
      if (!active) return
      setError('')
      setReceipts(rows)
      setSelected(current => current ? rows.find(row => row.e2eid === current.e2eid) || rows[0] || null : rows[0] || null)
    }).catch(err => { if (active) setError((err as Error).message) })
    void load()
    const onUpdate = () => { void load() }
    window.addEventListener('pix-receipts-updated', onUpdate)
    return () => { active = false; window.removeEventListener('pix-receipts-updated', onUpdate) }
  }, [start, end])
  const shown = useMemo(() => receipts.filter(r => `${r.payer_name} ${r.txid} ${r.e2eid}`.toLowerCase().includes(query.toLowerCase())), [receipts, query])
  const total = receipts.reduce((sum, row) => sum + row.amount, 0)
  return <><div className="page-heading"><div><p className="eyebrow">Confirmações</p><h1>Recebimentos</h1><p>Acompanhe pagamentos confirmados, com ou sem cobrança associada.</p></div></div><section className="stats-grid three"><StatCard icon={<Wallet />} label="Total no período" value={money(total)} note="Recebimentos confirmados" /><StatCard icon={<CircleCheck />} label="Pagamentos" value={String(receipts.length)} note="Sem duplicidade por E2E ID" /><StatCard icon={<Clock3 />} label="Último recebimento" value={receipts[0] ? money(receipts[0].amount) : money(0)} note={receipts[0] ? dateTime(receipts[0].received_at) : 'Nenhum registro'} /></section><div className="receipts-grid"><section className="panel"><div className="toolbar period-toolbar"><div className="input-wrap search"><Search /><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Buscar cliente, TXID ou E2E ID" /></div><label className="period-field">De<input type="date" value={start} max={end || undefined} onChange={e => setStart(e.target.value)} /></label><label className="period-field">Até<input type="date" value={end} min={start || undefined} onChange={e => setEnd(e.target.value)} /></label>{(start || end) && <button className="text-button" onClick={() => { setStart(''); setEnd('') }}>Limpar período</button>}</div>{error && <p className="form-error">{error}</p>}<div className="table-scroll"><table><thead><tr><th>Data</th><th>Cliente</th><th>TXID</th><th>Origem</th><th>Valor</th></tr></thead><tbody>{shown.map(row => <tr key={row.e2eid} className={selected?.e2eid === row.e2eid ? 'selected-row' : ''} onClick={() => setSelected(row)}><td>{dateTime(row.received_at)}</td><td>{row.payer_name}</td><td className="mono">{row.txid ? shortTxid(row.txid) : 'Sem vínculo'}</td><td>{row.origin}</td><td className="amount">{money(row.amount)}</td></tr>)}</tbody></table></div></section><aside className="panel receipt-detail"><p className="eyebrow">Registro selecionado</p><h2>Detalhes do recebimento</h2>{selected ? <dl><div><dt>Cliente</dt><dd>{selected.payer_name}</dd></div><div><dt>Valor</dt><dd className="money-highlight">{money(selected.amount)}</dd></div><div><dt>Data e hora</dt><dd>{dateTime(selected.received_at)}</dd></div><div><dt>Origem</dt><dd>{selected.origin}</dd></div><div><dt>TXID</dt><dd className="mono break">{selected.txid || 'Pagamento direto na chave'}</dd></div><div><dt>E2E ID</dt><dd className="mono break">{selected.e2eid}</dd></div></dl> : <p className="empty">Selecione um recebimento.</p>}</aside></div></>
}
