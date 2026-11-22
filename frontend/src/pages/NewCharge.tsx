import { FormEvent, useState } from 'react'
import { ArrowRight, Info, QrCode } from 'lucide-react'
import { QRCodeSVG } from 'qrcode.react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { money } from '../lib/format'

export default function NewCharge() {
  const [amount, setAmount] = useState(''); const [description, setDescription] = useState(''); const [payerName, setPayerName] = useState(''); const [error, setError] = useState(''); const [busy, setBusy] = useState(false)
  const navigate = useNavigate(); const number = Number(amount.replace(',', '.')) || 0
  const preview = `000201-PIXTA-PAGO-PREVIEW-${number.toFixed(2)}`
  const submit = async (event: FormEvent) => { event.preventDefault(); setBusy(true); setError(''); try { const charge = await api.createCharge({ amount: number, description, payerName }); navigate(`/charges/${charge.txid}`) } catch (err) { setError((err as Error).message) } finally { setBusy(false) } }
  return <><div className="page-heading"><div><p className="eyebrow">Cobranças</p><h1>Gerar cobrança Pix</h1><p>Defina o valor e apresente o QR Code ao cliente.</p></div></div><div className="split-grid"><section className="panel form-panel"><h2>Dados da cobrança</h2><form onSubmit={submit}><label>Valor da cobrança<div className="money-input"><span>R$</span><input value={amount} onChange={e => setAmount(e.target.value)} inputMode="decimal" placeholder="0,00" required /></div></label><label>Nome do cliente <small>(opcional)</small><input value={payerName} onChange={e => setPayerName(e.target.value)} placeholder="Ex.: Maria Oliveira" /></label><label>Descrição <small>(opcional)</small><textarea value={description} onChange={e => setDescription(e.target.value.slice(0, 100))} placeholder="Ex.: Pagamento de serviço ou produto" /><span className="char-count">{description.length}/100</span></label>{error && <p className="form-error">{error}</p>}<button className="primary-button" disabled={busy || number <= 0}><QrCode /> {busy ? 'Gerando…' : 'Gerar cobrança'} <ArrowRight /></button></form></section><section className="panel qr-preview"><div><p className="eyebrow">Pré-visualização</p><h2>O cliente vai escanear aqui</h2></div><div className="qr-box"><QRCodeSVG value={preview} size={184} level="M" /><strong>{number > 0 ? money(number) : 'Informe o valor'}</strong><small>QR Code ilustrativo até a cobrança ser gerada</small></div><p className="info-row"><Info /> O QR Code e o Pix Copia e Cola representam a mesma cobrança.</p></section></div></>
}

