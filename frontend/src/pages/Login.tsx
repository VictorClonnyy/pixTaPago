import { FormEvent, useState } from 'react'
import { ArrowRight, Eye, EyeOff, LockKeyhole, Mail } from 'lucide-react'
import { api } from '../api'
import type { User } from '../types'
import Brand from '../components/Brand'

export default function Login({ onLogin }: { onLogin: (user: User) => void }) {
  const [email, setEmail] = useState('demo@pixtapago.com.br')
  const [password, setPassword] = useState('pix123')
  const [show, setShow] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setError('')
    try { onLogin(await api.login(email, password)) } catch (err) { setError((err as Error).message) } finally { setBusy(false) }
  }
  return <div className="login-page"><div className="orb orb-one" /><div className="orb orb-two" /><section className="login-card"><Brand /><div><p className="eyebrow">Acesso seguro</p><h1>Boas-vindas</h1><p className="subtitle">Confirme seus recebimentos Pix sem abrir o app do banco.</p></div><form onSubmit={submit}><label>E-mail ou usuário<div className="input-wrap"><Mail /><input value={email} onChange={e => setEmail(e.target.value)} type="email" required /></div></label><label>Senha<div className="input-wrap"><LockKeyhole /><input value={password} onChange={e => setPassword(e.target.value)} type={show ? 'text' : 'password'} required /><button type="button" onClick={() => setShow(!show)}>{show ? <EyeOff /> : <Eye />}</button></div></label>{error && <p className="form-error">{error}</p>}<div className="login-row"><label className="check"><input type="checkbox" defaultChecked /> Lembrar-me</label><button type="button" className="text-button">Esqueci minha senha</button></div><button className="primary-button" disabled={busy}>{busy ? 'Entrando…' : <>Entrar <ArrowRight /></>}</button></form><div className="demo-note"><LockKeyhole /><span><strong>Ambiente de demonstração</strong>Use demo@pixtapago.com.br e senha pix123</span></div></section></div>
}

