import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { api } from '../api/client'
import { Btn, Card, Input } from '../components/ui'
import { Send, AlertCircle, CheckCircle2 } from 'lucide-react'

export default function Compose({ bots, toast }) {
  const loc      = useLocation()
  const prefill  = loc.state || {}

  const [botHash,    setBotHash]    = useState(prefill.bot_hash || bots[0]?.token_hash || '')
  const [chatId,     setChatId]     = useState(String(prefill.chat_id || ''))
  const [text,       setText]       = useState('')
  const [parseMode,  setParseMode]  = useState('None')
  const [busy,       setBusy]       = useState(false)
  const [err,        setErr]        = useState('')
  const [success,    setSuccess]    = useState('')

  useEffect(() => {
    if (prefill.bot_hash) setBotHash(prefill.bot_hash)
    if (prefill.chat_id)  setChatId(String(prefill.chat_id))
  }, [prefill.bot_hash, prefill.chat_id])

  async function send(e) {
    e.preventDefault()
    if (!botHash || !chatId || !text.trim()) return
    setBusy(true); setErr(''); setSuccess('')
    try {
      const r = await api.send({
        bot_hash:   botHash,
        chat_id:    chatId,
        text:       text.trim(),
        parse_mode: parseMode,
      })
      setSuccess(`Message sent! ID: ${r.message_id}`)
      setText('')
      toast('✔ Message sent')
    } catch (e) {
      setErr(e.message)
    } finally { setBusy(false) }
  }

  const bot = bots.find(b => b.token_hash === botHash)
  const charCount = text.length
  const overLimit = charCount > 4096

  return (
    <div className="p-6 max-w-2xl">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-gray-100">Compose Message</h1>
        <p className="text-sm text-gray-500 mt-0.5">Send a message from any of your bots</p>
      </div>

      <Card className="p-6">
        <form onSubmit={send} className="space-y-5">
          {/* Bot selector */}
          <div>
            <label className="block text-xs text-gray-400 mb-1.5 font-medium uppercase tracking-wide">
              Send From
            </label>
            <select value={botHash} onChange={e => setBotHash(e.target.value)}
              className="w-full bg-[#0d1425] border border-gray-700 rounded-lg px-3 py-2.5 text-sm
                text-gray-100 focus:outline-none focus:border-brand transition">
              {bots.map(b => (
                <option key={b.token_hash} value={b.token_hash}>
                  @{b.username} — {b.name} {b.is_running ? '🟢' : '🔴'}
                </option>
              ))}
            </select>
            {bot && !bot.is_running && (
              <p className="text-xs text-amber-400 mt-1">
                ⚠ This bot is not currently polling — it can still send messages
              </p>
            )}
          </div>

          {/* Chat ID */}
          <Input
            label="Target Chat ID"
            value={chatId}
            onChange={e => setChatId(e.target.value)}
            placeholder="-100123456789 or 123456789"
            required
          />

          {/* Parse mode */}
          <div>
            <label className="block text-xs text-gray-400 mb-2 font-medium uppercase tracking-wide">
              Parse Mode
            </label>
            <div className="flex gap-4">
              {['None','Markdown','HTML'].map(m => (
                <label key={m} className="flex items-center gap-2 cursor-pointer">
                  <input type="radio" value={m} checked={parseMode === m}
                    onChange={() => setParseMode(m)}
                    className="accent-brand" />
                  <span className="text-sm text-gray-400">{m}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Message body */}
          <div>
            <label className="block text-xs text-gray-400 mb-1.5 font-medium uppercase tracking-wide">
              Message Body
            </label>
            <textarea
              value={text} onChange={e => setText(e.target.value)}
              rows={8} placeholder="Type your message here…"
              className="w-full bg-[#0d1425] border border-gray-700 rounded-lg px-3 py-2.5 text-sm
                text-gray-100 placeholder-gray-600 focus:outline-none focus:border-brand
                focus:ring-1 focus:ring-brand resize-none transition"
            />
            <p className={`text-xs mt-1 text-right ${overLimit ? 'text-red-400' : 'text-gray-600'}`}>
              {charCount} / 4096
            </p>
          </div>

          {/* Status messages */}
          {err && (
            <div className="flex items-start gap-2 bg-red-900/20 border border-red-800/40 rounded-lg p-3">
              <AlertCircle size={14} className="text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-red-300 whitespace-pre-line">{err}</p>
            </div>
          )}
          {success && (
            <div className="flex items-center gap-2 bg-emerald-900/20 border border-emerald-800/40 rounded-lg p-3">
              <CheckCircle2 size={14} className="text-emerald-400" />
              <p className="text-xs text-emerald-300">{success}</p>
            </div>
          )}

          {/* Send button */}
          <div className="flex gap-3">
            <Btn variant="primary" type="submit"
              disabled={busy || !botHash || !chatId || !text.trim() || overLimit}
              className="flex-1 justify-center py-2.5">
              {busy ? 'Sending…' : <><Send size={14} /> Send Message</>}
            </Btn>
            <Btn variant="ghost" type="button" onClick={() => setText('')}>Clear</Btn>
          </div>
        </form>
      </Card>

      {/* Hints */}
      <div className="mt-4 bg-[#111b2e] border border-gray-800 rounded-xl p-4 space-y-1.5">
        <p className="text-xs font-medium text-brand mb-2">ℹ Chat ID Tips</p>
        <p className="text-xs text-gray-500">• User must send <code className="bg-[#0d1425] px-1 rounded">/start</code> to your bot before you can message them</p>
        <p className="text-xs text-gray-500">• Copy Chat ID from the Live Monitor (right-click any row → Copy Chat ID)</p>
        <p className="text-xs text-gray-500">• Groups and channels use negative IDs, e.g. <code className="bg-[#0d1425] px-1 rounded">-100123456789</code></p>
      </div>
    </div>
  )
}
