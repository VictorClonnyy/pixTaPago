import { useEffect, useState } from 'react'
import { Check, Clipboard } from 'lucide-react'
import { QRCodeSVG } from 'qrcode.react'
import { useParams } from 'react-router-dom'
import { api } from '../api'
import type { Charge } from '../types'
import StatusBadge from '../components/StatusBadge'
import { dateTime, money } from '../lib/format'

export default function ChargeDetail() {
  const { txid = '' } = useParams()
  const [charge, setCharge] = useState<Charge | null>(null)
  const [copied, setCopied] = useState(false)

  // Carrega a cobrança ao abrir a tela T04.
  useEffect(() => {
    let active = true
    const loadCharge = async () => {
      const value = await api.charge(txid)
      if (active) setCharge(value)
    }
    void loadCharge()
    return () => { active = false }
  }, [txid])

  // UC003: enquanto a cobrança estiver pendente, consulta a situação a cada 3 segundos.
  const waitingForPayment = charge?.status === 'ACTIVE'
  useEffect(() => {
    if (!waitingForPayment) return
    let requestInFlight = false
    const refreshStatus = async () => {
      if (requestInFlight || document.hidden) return
      requestInFlight = true
      try { setCharge(await api.charge(txid)) }
      catch { /* a próxima consulta tentará novamente */ }
      finally { requestInFlight = false }
    }
    const interval = window.setInterval(refreshStatus, 3000)
    return () => window.clearInterval(interval)
  }, [txid, waitingForPayment])

  if (!charge) return <div className="loading-card">Consultando cobrança…</div>

  const copy = async () => {
    await navigator.clipboard.writeText(charge.pix_copy_paste)
    setCopied(true)
    setTimeout(() => setCopied(false), 1800)
  }

  return <>
    <div className="page-heading">
      <div><p className="eyebrow">Consulta por TXID</p><h1>Detalhes da cobrança</h1><p className="mono full-txid">{charge.txid}</p></div>
    </div>
    <div className="split-grid">
      <section className="panel detail-panel">
        <div className="detail-head">
          <div>
            <span>Status da cobrança</span>
            <StatusBadge status={charge.status} />
            {charge.status === 'ACTIVE' && <small className="auto-update">Atualização automática ativa</small>}
          </div>
          <strong>{money(charge.amount)}</strong>
        </div>
        <dl>
          <div><dt>Cliente</dt><dd>{charge.payer_name}</dd></div>
          <div><dt>Descrição</dt><dd>{charge.description || 'Não informada'}</dd></div>
          <div><dt>Criada em</dt><dd>{dateTime(charge.created_at)}</dd></div>
          <div><dt>Última consulta</dt><dd>{dateTime(charge.updated_at)}</dd></div>
        </dl>
      </section>
      <section className="panel qr-preview">
        <h2>Pagamento da cobrança</h2>
        <div className="qr-box"><QRCodeSVG value={charge.pix_copy_paste} size={196} level="M" /><small>Payload retornado pela API Pix do BB</small></div>
        <div className="copy-box"><code>{charge.pix_copy_paste}</code><button onClick={copy}>{copied ? <Check /> : <Clipboard />}{copied ? 'Copiado' : 'Copiar código'}</button></div>
      </section>
    </div>
    <section className="panel timeline-panel">
      <h2>Histórico de status</h2>
      <div className="timeline">
        <div className="done"><span><Check /></span><strong>Cobrança criada no BB</strong><small>{dateTime(charge.created_at)}</small></div>
        <div className={charge.status === 'PAID' ? 'done' : 'current'}><span>{charge.status === 'PAID' ? <Check /> : ''}</span><strong>{charge.status === 'PAID' ? 'Pagamento confirmado' : 'Aguardando confirmação do BB'}</strong><small>{dateTime(charge.updated_at)}</small></div>
      </div>
    </section>
  </>
}
