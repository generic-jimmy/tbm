import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../store/auth'

export default function Login() {
  const [pw, setPw]     = useState('')
  const [err, setErr]   = useState('')
  const [busy, setBusy] = useState(false)
  const { login }       = useAuth()
  const navigate        = useNavigate()

  async function submit(e) {
    e.preventDefault()
    setBusy(true); setErr('')
    try {
      await login(pw)
      navigate('/')
    } catch (e) {
      setErr(e.message || 'Wrong password')
    } finally { setBusy(false) }
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="w-14 h-14 bg-brand rounded-2xl flex items-center justify-center text-2xl mx-auto mb-4">✈</div>
          <h1 className="text-xl font-semibold text-gray-100">BotManager Pro</h1>
          <p className="text-sm text-gray-500 mt-1">Sign in to continue</p>
        </div>
        <div className="bg-[#111b2e] border border-gray-800 rounded-2xl p-6">
          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1.5 font-medium uppercase tracking-wide">
                Admin Password
              </label>
              <input
                type="password" value={pw} onChange={e => setPw(e.target.value)}
                placeholder="Enter password"
                className="w-full bg-[#0d1425] border border-gray-700 rounded-lg px-3 py-2.5 text-sm
                  text-gray-100 placeholder-gray-600 focus:outline-none focus:border-brand
                  focus:ring-1 focus:ring-brand transition"
              />
            </div>
            {err && <p className="text-red-400 text-sm">{err}</p>}
            <button type="submit" disabled={busy || !pw}
              className="w-full bg-brand hover:bg-brand-dark disabled:opacity-50
                text-gray-950 font-semibold py-2.5 rounded-lg text-sm transition">
              {busy ? 'Signing in…' : 'Sign In'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
