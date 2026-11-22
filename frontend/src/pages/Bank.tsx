import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  ArrowDownLeft, ArrowLeft, ArrowUpRight, Check, ChevronRight,
  Camera, Eye, EyeOff, KeyRound, LogOut,
  QrCode, ReceiptText, ShieldCheck, WalletCards, X,
} from 'lucide-react'
import { api } from '../api'
import type { BankAccount, BankActor, BankTransaction, PixRecipient } from '../types'
import { dateTime, money } from '../lib/format'
import { uuid } from '../lib/uuid'
import PixCameraScanner from './bank/PixCameraScanner'

type Panel = 'key' | 'code' | 'receipt' | null

export default function Bank({ actor }: { actor: BankActor }) {
  const [account, setAccount] = useState<BankAccount | null>(null)
  const [balanceVisible, setBalanceVisible] = useState(true)
  const [panel, setPanel] = useState<Panel>(null)
  const [pixKey, setPixKey] = useState('')
  const [pixCode, setPixCode] = useState('')
  const [amount, setAmount] = useState('')
  const [description, setDescription] = useState('')
  const [recipient, setRecipient] = useState<PixRecipient | null>(null)
  const [receipt, setReceipt] = useState<BankTransaction | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const idempotencyKey = useRef(uuid())

  const load = useCallback(async () => setAccount(await api.bankAccount(actor)), [actor])
  useEffect(() => {
    let active = true
    api.bankAccount(actor).then(value => { if (active) setAccount(value) })
    const interval = window.setInterval(() => { if (!document.hidden) load().catch(() => undefined) }, 2000)
    return () => { active = false; window.clearInterval(interval) }
  }, [actor, load])

  const closePanel = () => {
    setPanel(null); setRecipient(null); setReceipt(null); setError('')
    setPixKey(''); setPixCode(''); setAmount(''); setDescription('')
    idempotencyKey.current = uuid()
  }

  const openPanel = (next: Panel) => { closePanel(); setPanel(next) }

  const previewKey = async () => {
    setBusy(true); setError('')
    try { setRecipient(await api.resolvePixKey(pixKey.trim())) }
    catch (err) { setError(messageOf(err)) }
    finally { setBusy(false) }
  }

  const previewCode = async () => {
    setBusy(true); setError('')
    try {
      const found = await api.previewPixCode(pixCode.trim())
      setRecipient(found)
      if (found.amount) setAmount(String(found.amount.toFixed(2)).replace('.', ','))
    } catch (err) { setError(messageOf(err)) }
    finally { setBusy(false) }
  }

  const confirmPayment = async () => {
    if (!recipient) return
    setBusy(true); setError('')
    try {
      const value = parseMoney(amount)
      const transaction = panel === 'key'
        ? await api.transferPix(actor, { pixKey: recipient.pixKey, amount: value, description, idempotencyKey: idempotencyKey.current })
        : await api.payPixCode(actor, { pix: pixCode, amount: value, description, idempotencyKey: idempotencyKey.current })
      setReceipt(transaction); setPanel('receipt'); await load()
    } catch (err) { setError(messageOf(err)) }
    finally { setBusy(false) }
  }

  const groupedTransactions = useMemo(() => account?.transactions ?? [], [account])
  if (!account) return <div className="bank-loading"><span className="bank-logo">A</span><p>Acessando sua conta…</p></div>

  return <div className="bank-app">
    <header className="bank-header">
      <div className="bank-wordmark"><span className="bank-logo">A</span><strong>aurora</strong></div>
      <div className="bank-profile"><div><strong>{account.name}</strong><small>Conta corrente</small></div><span>{account.name[0]}</span><button aria-label="Sair"><LogOut /></button></div>
    </header>

    <main className="bank-main">
      <section className="bank-welcome"><p>Olá, {account.name}</p><h1>Bom ter você por aqui.</h1></section>

      <section className="bank-balance-card">
        <div className="balance-label"><span>Saldo disponível</span><button onClick={() => setBalanceVisible(value => !value)} aria-label="Mostrar ou ocultar saldo">{balanceVisible ? <EyeOff /> : <Eye />}</button></div>
        <strong>{balanceVisible ? money(account.balance) : '••••••'}</strong>
        <small>Atualizado agora</small>
        <div className="balance-orb" />
      </section>

      <section className="bank-actions">
        <h2>O que você precisa?</h2>
        <div className="bank-action-grid">
          <button onClick={() => openPanel('key')}><span><KeyRound /></span><strong>Transferir Pix</strong><small>Use uma chave Pix</small><ChevronRight /></button>
          <button onClick={() => openPanel('code')}><span><QrCode /></span><strong>Pagar QR Code</strong><small>Leia ou cole o código</small><ChevronRight /></button>
        </div>
      </section>

      <section className="bank-statement">
        <div className="bank-section-title"><div><p>Conta corrente</p><h2>Últimas movimentações</h2></div><ReceiptText /></div>
        {groupedTransactions.length === 0 ? <div className="bank-empty"><WalletCards /><strong>Nenhuma movimentação ainda</strong><p>Seus pagamentos e recebimentos aparecerão aqui.</p></div> :
          <div className="bank-transaction-list">{groupedTransactions.map(item => <TransactionRow key={item.e2eid} item={item} />)}</div>}
      </section>
    </main>

    {panel && <div className="bank-overlay" role="presentation">
      <section className="bank-modal">
        <div className="bank-modal-top">
          <button onClick={recipient && panel !== 'receipt' ? () => setRecipient(null) : closePanel} aria-label="Voltar">{recipient && panel !== 'receipt' ? <ArrowLeft /> : <X />}</button>
          <div><small>Pix</small><strong>{panelTitle(panel, recipient)}</strong></div><span />
        </div>
        {panel === 'key' && !recipient && <PixKeyForm pixKey={pixKey} setPixKey={setPixKey} amount={amount} setAmount={setAmount} description={description} setDescription={setDescription} onContinue={previewKey} busy={busy} error={error} />}
        {panel === 'code' && !recipient && <PixCodeForm pixCode={pixCode} setPixCode={setPixCode} onContinue={previewCode} busy={busy} error={error} />}
        {(panel === 'key' || panel === 'code') && recipient && <Confirmation account={account} recipient={recipient} amount={amount} setAmount={setAmount} description={description} setDescription={setDescription} onConfirm={confirmPayment} busy={busy} error={error} amountLocked={Boolean(recipient.amount)} />}
        {panel === 'receipt' && receipt && <Receipt account={account} transaction={receipt} onClose={closePanel} />}
      </section>
    </div>}
  </div>
}

function PixKeyForm(props: { pixKey: string; setPixKey: (value: string) => void; amount: string; setAmount: (value: string) => void; description: string; setDescription: (value: string) => void; onContinue: () => void; busy: boolean; error: string }) {
  return <div className="bank-form">
    <div className="bank-form-intro"><span><KeyRound /></span><div><h3>Para quem você vai transferir?</h3><p>Digite a chave Pix do recebedor.</p></div></div>
    <label>Chave Pix<input autoFocus value={props.pixKey} onChange={event => props.setPixKey(event.target.value)} placeholder="CPF, celular, e-mail ou chave aleatória" /></label>
    <label>Valor<div className="bank-money"><span>R$</span><input inputMode="decimal" value={props.amount} onChange={event => props.setAmount(event.target.value)} placeholder="0,00" /></div></label>
    <label>Descrição <small>Opcional</small><input value={props.description} onChange={event => props.setDescription(event.target.value)} maxLength={140} placeholder="Escreva uma mensagem" /></label>
    {props.error && <p className="bank-error">{props.error}</p>}
    <button className="bank-main-button" disabled={props.busy || !props.pixKey.trim() || parseMoney(props.amount) <= 0} onClick={props.onContinue}>{props.busy ? 'Consultando…' : 'Continuar'}</button>
  </div>
}

function PixCodeForm(props: { pixCode: string; setPixCode: (value: string) => void; onContinue: () => void; busy: boolean; error: string }) {
  const [cameraOpen, setCameraOpen] = useState(false)
  const handleRead = (code: string) => { props.setPixCode(code); setCameraOpen(false) }

  if (cameraOpen) return <PixCameraScanner onCancel={() => setCameraOpen(false)} onRead={handleRead} />

  return <div className="bank-form">
    <div className="bank-form-intro"><span><QrCode /></span><div><h3>Leia ou cole o código Pix</h3><p>Confira os dados antes de confirmar.</p></div></div>
    <button type="button" className="bank-camera-button" onClick={() => setCameraOpen(true)}><Camera /> Escanear QR Code</button>
    <label>Pix Copia e Cola<textarea autoFocus value={props.pixCode} onChange={event => props.setPixCode(event.target.value)} placeholder="Cole o código completo aqui" /></label>
    {props.error && <p className="bank-error">{props.error}</p>}
    <button className="bank-main-button" disabled={props.busy || !props.pixCode.trim()} onClick={props.onContinue}>{props.busy ? 'Verificando…' : 'Continuar'}</button>
  </div>
}

function Confirmation(props: { account: BankAccount; recipient: PixRecipient; amount: string; setAmount: (value: string) => void; description: string; setDescription: (value: string) => void; onConfirm: () => void; busy: boolean; error: string; amountLocked: boolean }) {
  return <div className="bank-confirm">
    <div className="recipient-avatar">{props.recipient.name[0]}</div><p>Você está enviando para</p><h3>{props.recipient.name}</h3><small>{props.recipient.document}</small>
    <div className="bank-confirm-data"><div><span>Instituição</span><strong>Banco Aurora</strong></div><div><span>Chave Pix</span><strong>{props.recipient.pixKey}</strong></div><div><span>De</span><strong>{props.account.name} · Conta corrente</strong></div></div>
    <label>Valor<div className="bank-money"><span>R$</span><input inputMode="decimal" value={props.amount} disabled={props.amountLocked} onChange={event => props.setAmount(event.target.value)} /></div></label>
    <label>Descrição <small>Opcional</small><input value={props.description} onChange={event => props.setDescription(event.target.value)} maxLength={140} placeholder="Escreva uma mensagem" /></label>
    {props.error && <p className="bank-error">{props.error}</p>}
    <button className="bank-main-button" disabled={props.busy || parseMoney(props.amount) <= 0} onClick={props.onConfirm}>{props.busy ? 'Enviando…' : `Confirmar Pix de ${money(parseMoney(props.amount))}`}</button>
    <p className="bank-security"><ShieldCheck /> Transação protegida e processada em tempo real</p>
  </div>
}

function Receipt({ account, transaction, onClose }: { account: BankAccount; transaction: BankTransaction; onClose: () => void }) {
  return <div className="bank-receipt"><span className="receipt-check"><Check /></span><p>Pix enviado</p><h3>{money(transaction.amount)}</h3><small>para {transaction.counterparty}</small><div className="bank-confirm-data"><div><span>Data e hora</span><strong>{dateTime(transaction.createdAt)}</strong></div><div><span>Pagador</span><strong>{account.name}</strong></div><div><span>Recebedor</span><strong>{transaction.counterparty}</strong></div><div><span>Identificador</span><strong className="receipt-id">{transaction.e2eid}</strong></div></div><button className="bank-main-button" onClick={onClose}>Concluir</button></div>
}

function TransactionRow({ item }: { item: BankTransaction }) {
  const incoming = item.direction === 'IN'
  return <div className="bank-transaction"><span className={incoming ? 'incoming' : 'outgoing'}>{incoming ? <ArrowDownLeft /> : <ArrowUpRight />}</span><div><strong>{incoming ? `Pix recebido de ${item.counterparty}` : `Pix enviado para ${item.counterparty}`}</strong><small>{item.description || (item.paymentMethod === 'PIX_QR' ? 'Pagamento por QR Code' : 'Transferência Pix')} · {dateTime(item.createdAt)}</small></div><div><strong className={incoming ? 'credit' : ''}>{incoming ? '+' : '-'} {money(item.amount)}</strong><small>Concluído</small></div></div>
}

function panelTitle(panel: Panel, recipient: PixRecipient | null) {
  if (panel === 'receipt') return 'Comprovante'
  if (recipient) return 'Confirmar pagamento'
  return panel === 'code' ? 'Pagar com Pix' : 'Transferir com Pix'
}

function parseMoney(value: string) {
  const normalized = value.trim().replace(/\./g, '').replace(',', '.')
  const parsed = Number(normalized)
  return Number.isFinite(parsed) ? parsed : 0
}

function messageOf(error: unknown) { return error instanceof Error ? error.message : 'Não foi possível concluir. Tente novamente.' }
