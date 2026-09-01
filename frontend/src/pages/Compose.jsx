import { useState, useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import { api } from '../api/client'
import { Btn, Card, Input, Select } from '../components/ui'
import { Send, AlertCircle, CheckCircle2, Paperclip, Plus, X, BookmarkPlus } from 'lucide-react'

const MEDIA_TYPES = [
  { value: 'photo',    label: 'Photo' },
  { value: 'video',    label: 'Video' },
  { value: 'audio',    label: 'Audio' },
  { value: 'document', label: 'Document' },
]

export default function Compose({ bots, toast }) {
  const loc      = useLocation()
  const prefill  = loc.state || {}
  const fileRef  = useRef(null)

  const [mode,       setMode]       = useState('text')   // 'text' | 'media'
  const [botHash,    setBotHash]    = useState(prefill.bot_hash || bots[0]?.token_hash || '')
  const [chatId,     setChatId]     = useState(String(prefill.chat_id || ''))
  const [text,       setText]       = useState('')
  const [parseMode,  setParseMode]  = useState('None')
  const [busy,       setBusy]       = useState(false)
  const [err,        setErr]        = useState('')
  const [success,    setSuccess]    = useState('')

  // Inline keyboard — URL buttons only (no callback_data handler server-side yet)
  const [buttons,    setButtons]    = useState([])   // [{ text, url }]
  const [kbOpen,     setKbOpen]     = useState(false)

  // Templates
  const [templates,     setTemplates]     = useState([])
  const [templateName,  setTemplateName]  = useState('')
  const [savingTemplate, setSavingTemplate] = useState(false)

  // Media
  const [file,       setFile]       = useState(null)
  const [mediaType,  setMediaType]  = useState('document')
  const [caption,    setCaption]    = useState('')

  useEffect(() => {
    if (prefill.bot_hash) setBotHash(prefill.bot_hash)
    if (prefill.chat_id)  setChatId(String(prefill.chat_id))
  }, [prefill.bot_hash, prefill.chat_id])

  useEffect(() => {
    api.templates().then(setTemplates).catch(() => {})
  }, [])

  function pickFile(f) {
    if (!f) return
    setFile(f)
    if (f.type.startsWith('image/')) setMediaType('photo')
    else if (f.type.startsWith('video/')) setMediaType('video')
    else if (f.type.startsWith('audio/')) setMediaType('audio')
    else setMediaType('document')
  }

  function applyTemplate(id) {
    const t = templates.find(t => String(t.id) === String(id))
    if (!t) return
    setText(t.text)
    if (t.reply_markup?.inline_keyboard) {
      setButtons(t.reply_markup.inline_keyboard.flat().map(b => ({ text: b.text, url: b.url || '' })))
      setKbOpen(true)
    }
    toast(`Loaded "${t.name}"`)
  }

  async function saveTemplate() {
    if (!templateName.trim() || !text.trim()) return
    setSavingTemplate(true)
    try {
      const reply_markup = buttons.length
        ? { inline_keyboard: buttons.filter(b => b.text && b.url).map(b => [b]) }
        : null
      const t = await api.createTemplate({ name: templateName.trim(), text, reply_markup })
      setTemplates(prev => [t, ...prev])
      setTemplateName('')
      toast('✔ Template saved')
    } catch (e) {
      toast(`✕ ${e.message}`)
    } finally { setSavingTemplate(false) }
  }

  async function deleteTemplate(id) {
    await api.deleteTemplate(id)
    setTemplates(prev => prev.filter(t => t.id !== id))
  }

  function buildReplyMarkup() {
    const valid = buttons.filter(b => b.text.trim() && b.url.trim())
    if (!valid.length) return null
    return { inline_keyboard: valid.map(b => [{ text: b.text.trim(), url: b.url.trim() }]) }
  }

  async function sendText(e) {
    e.preventDefault()
    if (!botHash || !chatId || !text.trim()) return
    setBusy(true); setErr(''); setSuccess('')
    try {
      const reply_markup = buildReplyMarkup()
      const r = await api.send({
        bot_hash:   botHash,
        chat_id:    chatId,
        text:       text.trim(),
        parse_mode: parseMode,
        ...(reply_markup ? { reply_markup } : {}),
      })
      setSuccess(`Message sent! ID: ${r.message_id}`)
      setText(''); setButtons([])
      toast('✔ Message sent')
    } catch (e) {
      setErr(e.message)
    } finally { setBusy(false) }
  }

  async function sendMedia(e) {
    e.preventDefault()
    if (!botHash || !chatId || !file) return
    setBusy(true); setErr(''); setSuccess('')
    try {
      const fd = new FormData()
      fd.append('bot_hash', botHash)
      fd.append('chat_id', chatId)
      fd.append('media_type', mediaType)
      fd.append('caption', caption)
      const reply_markup = buildReplyMarkup()
      if (reply_markup) fd.append('reply_markup', JSON.stringify(reply_markup))
      fd.append('file', file)
      const r = await api.sendMedia(fd)
      setSuccess(`Media sent! ID: ${r.message_id}`)
      setFile(null); setCaption(''); setButtons([])
      if (fileRef.current) fileRef.current.value = ''
      toast('✔ Media sent')
    } catch (e) {
      setErr(e.message)
    } finally { setBusy(false) }
  }

  const bot = bots.find(b => b.token_hash === botHash)
  const charCount = text.length
  const overLimit = charCount > 4096

  return (
    <div className="p-6 max-w-2xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-100">Compose Message</h1>
          <p className="text-sm text-gray-500 mt-0.5">Send a message from any of your bots</p>
        </div>
        <div className="flex bg-[#0d1425] border border-gray-800 rounded-lg p-1">
          {['text', 'media'].map(m => (
            <button key={m} onClick={() => setMode(m)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition ${
                mode === m ? 'bg-brand text-gray-950' : 'text-gray-400 hover:text-gray-200'}`}>
              {m === 'text' ? 'Text' : 'Photo / Document'}
            </button>
          ))}
        </div>
      </div>

      <Card className="p-6">
        <form onSubmit={mode === 'text' ? sendText : sendMedia} className="space-y-5">
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
                ⚠ This bot is not currently running — it can still send messages
              </p>
            )}
          </div>

          <Input
            label="Target Chat ID"
            value={chatId}
            onChange={e => setChatId(e.target.value)}
            placeholder="-100123456789 or 123456789"
            required
          />

          {mode === 'text' ? (
            <>
              {templates.length > 0 && (
                <div>
                  <label className="block text-xs text-gray-400 mb-1.5 font-medium uppercase tracking-wide">
                    Load Template
                  </label>
                  <div className="flex gap-2">
                    <select onChange={e => e.target.value && applyTemplate(e.target.value)}
                      defaultValue=""
                      className="flex-1 bg-[#0d1425] border border-gray-700 rounded-lg px-3 py-2 text-sm
                        text-gray-100 focus:outline-none focus:border-brand transition">
                      <option value="">— choose a saved reply —</option>
                      {templates.map(t => (
                        <option key={t.id} value={t.id}>{t.name}</option>
                      ))}
                    </select>
                  </div>
                </div>
              )}

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

              {/* Save as template */}
              <div className="flex gap-2">
                <Input placeholder="Template name…" value={templateName}
                  onChange={e => setTemplateName(e.target.value)} className="flex-1" />
                <Btn type="button" variant="outline" size="md" disabled={!templateName.trim() || !text.trim() || savingTemplate}
                  onClick={saveTemplate}>
                  <BookmarkPlus size={14} /> Save
                </Btn>
              </div>
              {templates.length > 0 && (
                <div className="flex flex-wrap gap-1.5 -mt-2">
                  {templates.map(t => (
                    <span key={t.id} className="inline-flex items-center gap-1 bg-[#0d1425] border border-gray-800
                      rounded-full pl-2.5 pr-1 py-0.5 text-xs text-gray-400">
                      {t.name}
                      <button type="button" onClick={() => deleteTemplate(t.id)}
                        className="hover:text-red-400 transition p-0.5">
                        <X size={10} />
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </>
          ) : (
            <>
              <div>
                <label className="block text-xs text-gray-400 mb-1.5 font-medium uppercase tracking-wide">
                  File
                </label>
                <div
                  onClick={() => fileRef.current?.click()}
                  className="border-2 border-dashed border-gray-700 hover:border-brand rounded-lg p-6
                    text-center cursor-pointer transition"
                >
                  <Paperclip size={20} className="mx-auto text-gray-500 mb-2" />
                  <p className="text-sm text-gray-400">
                    {file ? file.name : 'Click to choose a photo, video, audio, or document'}
                  </p>
                  {file && <p className="text-xs text-gray-600 mt-1">{(file.size / 1024).toFixed(0)} KB</p>}
                </div>
                <input ref={fileRef} type="file" className="hidden"
                  onChange={e => pickFile(e.target.files?.[0])} />
              </div>

              <Select label="Media Type" value={mediaType} onChange={e => setMediaType(e.target.value)}
                className="w-full">
                {MEDIA_TYPES.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
              </Select>

              <div>
                <label className="block text-xs text-gray-400 mb-1.5 font-medium uppercase tracking-wide">
                  Caption (optional)
                </label>
                <textarea
                  value={caption} onChange={e => setCaption(e.target.value)}
                  rows={3} placeholder="Add a caption…"
                  className="w-full bg-[#0d1425] border border-gray-700 rounded-lg px-3 py-2.5 text-sm
                    text-gray-100 placeholder-gray-600 focus:outline-none focus:border-brand
                    focus:ring-1 focus:ring-brand resize-none transition"
                />
              </div>
            </>
          )}

          {/* Inline keyboard builder — URL buttons */}
          <div>
            <button type="button" onClick={() => setKbOpen(o => !o)}
              className="text-xs text-brand hover:underline font-medium">
              {kbOpen ? '− Hide' : '+ Add'} link buttons (inline keyboard)
            </button>
            {kbOpen && (
              <div className="mt-2 space-y-2">
                {buttons.map((b, i) => (
                  <div key={i} className="flex gap-2">
                    <Input placeholder="Button text" value={b.text}
                      onChange={e => setButtons(bs => bs.map((x, j) => j === i ? { ...x, text: e.target.value } : x))}
                      className="flex-1" />
                    <Input placeholder="https://…" value={b.url}
                      onChange={e => setButtons(bs => bs.map((x, j) => j === i ? { ...x, url: e.target.value } : x))}
                      className="flex-[2]" />
                    <button type="button" onClick={() => setButtons(bs => bs.filter((_, j) => j !== i))}
                      className="text-gray-500 hover:text-red-400 transition px-2">
                      <X size={14} />
                    </button>
                  </div>
                ))}
                <Btn type="button" variant="ghost" size="sm"
                  onClick={() => setButtons(bs => [...bs, { text: '', url: '' }])}>
                  <Plus size={12} /> Add button
                </Btn>
                <p className="text-xs text-gray-600">
                  URL buttons only — they open a link when tapped, no server-side handling needed.
                </p>
              </div>
            )}
          </div>

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

          <div className="flex gap-3">
            <Btn variant="primary" type="submit"
              disabled={busy || !botHash || !chatId ||
                (mode === 'text' ? (!text.trim() || overLimit) : !file)}
              className="flex-1 justify-center py-2.5">
              {busy ? 'Sending…' : <><Send size={14} /> Send {mode === 'media' ? 'Media' : 'Message'}</>}
            </Btn>
            <Btn variant="ghost" type="button"
              onClick={() => { setText(''); setFile(null); setCaption(''); setButtons([]) }}>
              Clear
            </Btn>
          </div>
        </form>
      </Card>

      <div className="mt-4 bg-[#111b2e] border border-gray-800 rounded-xl p-4 space-y-1.5">
        <p className="text-xs font-medium text-brand mb-2">ℹ Chat ID Tips</p>
        <p className="text-xs text-gray-500">• User must send <code className="bg-[#0d1425] px-1 rounded">/start</code> to your bot before you can message them</p>
        <p className="text-xs text-gray-500">• Copy Chat ID from the Live Monitor (right-click any row → Copy Chat ID)</p>
        <p className="text-xs text-gray-500">• Groups and channels use negative IDs, e.g. <code className="bg-[#0d1425] px-1 rounded">-100123456789</code></p>
      </div>
    </div>
  )
}
