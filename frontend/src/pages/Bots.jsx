import { useState, useCallback } from 'react'
import { api } from '../api/client'
import { useWebSocket } from '../store/ws'
import { Btn, Card, Input, StatusDot, Badge } from '../components/ui'
import { Plus, Trash2, Play, Square, RefreshCw, X,
         History, CheckCircle2, AlertCircle, Loader } from 'lucide-react'

// ─── Import History Modal ────────────────────────────────────────────────────
function ImportModal({ bot, onClose, toast }) {
  const [chatId,  setChatId]  = useState('')
  const [limit,   setLimit]   = useState('')
  const [incremental, setIncremental] = useState(false)
  const [downloadMedia, setDownloadMedia] = useState(false)
  const [busy,    setBusy]    = useState(false)
  const [jobId,   setJobId]   = useState(null)
  const [progress,setProgress]= useState(null)
  const [jobs,    setJobs]    = useState([])
  const [tab,     setTab]     = useState('new')

  // Load past jobs when switching to history tab
  async function loadJobs() {
    try { setJobs(await api.importJobs(bot.token_hash)) } catch {}
  }

  // WebSocket receives live progress for this bot
  const onWs = useCallback((msg) => {
    if (msg.type === 'import_progress' && msg.job_id === jobId) {
      setProgress(msg)
    }
  }, [jobId])
  useWebSocket(onWs, bot.token_hash)

  async function startImport(e) {
    e.preventDefault()
    setBusy(true)
    try {
      const payload = { bot_hash: bot.token_hash, incremental, download_media: downloadMedia }
      if (chatId.trim()) payload.chat_ids = [Number(chatId)]
      if (limit.trim())  payload.limit    = Number(limit)

      const r = await api.startImport(payload)
      setJobId(r.job_id)
      setProgress({ status: 'pending', imported: 0, skipped: 0, current_chat: null })
      toast('✔ Import started — tracking in real-time')
    } catch (e) {
      toast('Error: ' + e.message)
    } finally { setBusy(false) }
  }

  const statusIcon = {
    pending:  <Loader size={14} className="text-amber-400 animate-spin" />,
    running:  <Loader size={14} className="text-blue-400 animate-spin" />,
    done:     <CheckCircle2 size={14} className="text-emerald-400" />,
    error:    <AlertCircle  size={14} className="text-red-400" />,
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="bg-[#111b2e] border border-gray-700 rounded-2xl w-full max-w-lg">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
          <div>
            <h2 className="font-semibold text-gray-100">Import Full History</h2>
            <p className="text-xs text-gray-500 mt-0.5">@{bot.username} — via MTProto</p>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300 transition">
            <X size={18} />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-800">
          {[['new','New Import'],['history','Past Jobs']].map(([k,l]) => (
            <button key={k} onClick={() => { setTab(k); if (k==='history') loadJobs() }}
              className={`px-5 py-2.5 text-xs font-medium transition border-b-2
                ${tab===k ? 'border-brand text-brand' : 'border-transparent text-gray-500 hover:text-gray-300'}`}>
              {l}
            </button>
          ))}
        </div>

        <div className="p-6">
          {tab === 'new' && (
            <>
              {/* How it works */}
              <div className="bg-blue-900/20 border border-blue-800/40 rounded-xl p-4 mb-5 space-y-1.5">
                <p className="text-xs font-semibold text-blue-300 mb-2">⚡ How this works</p>
                <p className="text-xs text-blue-200/70">Uses MTProto (Telethon) with your bot token — no phone number needed.</p>
                <p className="text-xs text-blue-200/70">Fetches every message the bot can see going back to when it joined the chat.</p>
                <p className="text-xs text-blue-200/70">Requires <code className="bg-blue-950 px-1 rounded">TELEGRAM_API_ID</code> and <code className="bg-blue-950 px-1 rounded">TELEGRAM_API_HASH</code> in your env.</p>
              </div>

              <form onSubmit={startImport} className="space-y-4">
                <Input
                  label="Chat ID (optional — blank = all known chats)"
                  value={chatId} onChange={e => setChatId(e.target.value)}
                  placeholder="-100123456789"
                  type="number"
                />
                <Input
                  label="Message limit (optional — blank = unlimited)"
                  value={limit} onChange={e => setLimit(e.target.value)}
                  placeholder="e.g. 5000"
                  type="number"
                />

                <div className="flex flex-col gap-2 bg-[#0d1425] border border-gray-800 rounded-lg p-3">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" checked={incremental}
                      onChange={e => setIncremental(e.target.checked)}
                      className="accent-brand" />
                    <span className="text-xs text-gray-300">
                      Sync new messages only <span className="text-gray-600">(skip what's already imported — fast)</span>
                    </span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" checked={downloadMedia}
                      onChange={e => setDownloadMedia(e.target.checked)}
                      className="accent-brand" />
                    <span className="text-xs text-gray-300">
                      Download &amp; store media <span className="text-gray-600">(makes photos/files downloadable — slower, needs a storage group)</span>
                    </span>
                  </label>
                  <p className="text-[11px] text-gray-600 pt-1">
                    A stopped or crashed import always resumes automatically from where it left off — no need to check anything for that.
                  </p>
                </div>

                {/* Live progress */}
                {progress && (
                  <div className="bg-[#0d1425] border border-gray-700 rounded-xl p-4">
                    <div className="flex items-center gap-2 mb-3">
                      {statusIcon[progress.status] || null}
                      <span className="text-xs font-semibold text-gray-200 capitalize">
                        {progress.status}
                      </span>
                      {progress.job_id && (
                        <span className="text-[10px] font-mono text-gray-600 ml-auto">
                          {progress.job_id}
                        </span>
                      )}
                    </div>

                    {progress.current_chat && (
                      <p className="text-xs text-gray-400 mb-3 truncate">
                        📂 {progress.current_chat}
                      </p>
                    )}

                    {/* Progress bars */}
                    <div className="space-y-2">
                      <div className="flex justify-between text-xs text-gray-500 mb-1">
                        <span>Imported</span>
                        <span className="text-emerald-400 font-mono">
                          {(progress.imported || 0).toLocaleString()}
                        </span>
                      </div>
                      <div className="flex justify-between text-xs text-gray-500">
                        <span>Skipped (already in DB)</span>
                        <span className="text-gray-400 font-mono">
                          {(progress.skipped || 0).toLocaleString()}
                        </span>
                      </div>
                    </div>

                    {progress.error && (
                      <p className="text-xs text-red-400 mt-3 bg-red-900/20 rounded p-2">
                        {progress.error}
                      </p>
                    )}

                    {progress.status === 'done' && (
                      <p className="text-xs text-emerald-400 mt-3">
                        ✔ Import complete — check Live Monitor to see all messages
                      </p>
                    )}
                  </div>
                )}

                <div className="flex gap-3 pt-1">
                  <Btn variant="ghost" type="button" onClick={onClose} className="flex-1">
                    {progress?.status === 'done' ? 'Close' : 'Cancel'}
                  </Btn>
                  <Btn variant="primary" type="submit"
                    disabled={busy || (progress && ['pending','running'].includes(progress.status))}
                    className="flex-1 justify-center">
                    {busy ? 'Starting…' :
                      progress && ['pending','running'].includes(progress.status)
                        ? 'Running…'
                        : <><History size={13} /> Start Import</>
                    }
                  </Btn>
                </div>
              </form>
            </>
          )}

          {tab === 'history' && (
            <div className="space-y-2">
              {jobs.length === 0 ? (
                <p className="text-sm text-gray-500 text-center py-6">No import jobs yet</p>
              ) : jobs.map(j => (
                <div key={j.id}
                  className="bg-[#0d1425] border border-gray-800 rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-2">
                    {statusIcon[j.status] || null}
                    <span className="text-xs font-semibold text-gray-200 capitalize">{j.status}</span>
                    <span className="text-[10px] text-gray-600 font-mono ml-auto">{j.id}</span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-xs">
                    <div>
                      <p className="text-gray-600">Imported</p>
                      <p className="text-emerald-400 font-mono">{(j.imported||0).toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-gray-600">Skipped</p>
                      <p className="text-gray-400 font-mono">{(j.skipped||0).toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-gray-600">Started</p>
                      <p className="text-gray-400">{j.started_at ? new Date(j.started_at).toLocaleString() : '—'}</p>
                    </div>
                  </div>
                  {j.current_chat && (
                    <p className="text-xs text-gray-500 mt-2 truncate">📂 {j.current_chat}</p>
                  )}
                  {j.error && (
                    <p className="text-xs text-red-400 mt-2">{j.error}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Add Bot Modal ────────────────────────────────────────────────────────────
function AddBotModal({ onClose, onAdded, toast }) {
  const [token, setToken] = useState('')
  const [scid,  setScid]  = useState('')
  const [busy,  setBusy]  = useState(false)
  const [err,   setErr]   = useState('')

  async function submit(e) {
    e.preventDefault()
    setBusy(true); setErr('')
    try {
      const r = await api.addBot(token.trim(), scid ? Number(scid) : null)
      toast(`✔ Bot @${r.username} added and polling started`)
      onAdded(); onClose()
    } catch (e) { setErr(e.message) }
    finally { setBusy(false) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="bg-[#111b2e] border border-gray-700 rounded-2xl p-6 w-full max-w-md">
        <div className="flex items-center justify-between mb-6">
          <h2 className="font-semibold text-gray-100">Add New Bot</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300"><X size={18} /></button>
        </div>
        <form onSubmit={submit} className="space-y-4">
          <Input label="Bot Token (from @BotFather)" type="password"
            value={token} onChange={e => setToken(e.target.value)}
            placeholder="1234567890:AAAA..." required />
          <Input label="Storage Group Chat ID (optional)" value={scid}
            onChange={e => setScid(e.target.value)}
            placeholder="-100123456789" type="number" />
          <div className="bg-[#0d1425] rounded-xl p-3 space-y-1.5 text-xs text-gray-500">
            <p>📌 Get your token from <strong className="text-gray-400">@BotFather</strong></p>
            <p>📁 Storage group ID is a <strong className="text-gray-400">negative number</strong></p>
            <p>🤖 Bot must be <strong className="text-gray-400">admin</strong> in the storage group</p>
          </div>
          {err && <p className="text-red-400 text-sm">{err}</p>}
          <div className="flex gap-3 pt-1">
            <Btn variant="ghost" type="button" onClick={onClose} className="flex-1">Cancel</Btn>
            <Btn variant="primary" type="submit" disabled={busy || !token} className="flex-1 justify-center">
              {busy ? 'Validating…' : 'Add Bot'}
            </Btn>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─── Bot Card ─────────────────────────────────────────────────────────────────
function BotCard({ bot, onRefresh, toast }) {
  const [busy,        setBusy]        = useState(false)
  const [importModal, setImportModal] = useState(false)

  async function act(fn, label) {
    setBusy(true)
    try { await fn(); toast(`✔ ${label}`); onRefresh() }
    catch (e) { toast('Error: ' + e.message) }
    finally { setBusy(false) }
  }

  const statusColor = {
    polling:  'green', webhook: 'purple', draining: 'amber',
    starting: 'blue',  stopped:  'gray', error: 'red',
  }[bot.worker_status] || 'gray'

  return (
    <>
      <Card className="p-5 flex flex-col gap-4">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-brand/20 flex items-center justify-center text-xl flex-shrink-0">
              🤖
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-semibold text-gray-100">@{bot.username || 'unknown'}</span>
                <Badge color={statusColor}>
                  <StatusDot status={bot.worker_status} />
                  <span className="ml-1 capitalize">{bot.worker_status || 'stopped'}</span>
                </Badge>
              </div>
              <p className="text-xs text-gray-500">{bot.name} · ID {bot.bot_id}</p>
            </div>
          </div>
          <button onClick={() => act(() => api.removeBot(bot.token_hash), 'Bot removed')}
            className="text-gray-700 hover:text-red-400 transition p-1 flex-shrink-0">
            <Trash2 size={14} />
          </button>
        </div>

        {/* Meta grid */}
        <div className="grid grid-cols-2 gap-2 text-xs">
          {[
            ['Bot Hash',      bot.token_hash?.slice(0,12)+'…'],
            ['Storage Group', bot.storage_chat_id || '—'],
            ['Last Poll ID',  (bot.last_poll_id||0).toLocaleString()],
            ['Added',         bot.created_at ? new Date(bot.created_at).toLocaleDateString() : '—'],
          ].map(([label, value]) => (
            <div key={label} className="bg-[#0d1425] rounded-lg p-2.5">
              <p className="text-gray-600 mb-0.5">{label}</p>
              <p className="text-gray-400 font-mono truncate">{value}</p>
            </div>
          ))}
        </div>

        {/* Error */}
        {bot.worker_error && (
          <div className="bg-red-900/20 border border-red-800/40 rounded-lg p-3">
            <p className="text-xs text-red-400">{bot.worker_error}</p>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2">
          {bot.is_running ? (
            <Btn size="sm" variant="danger" className="flex-1 justify-center"
              onClick={() => act(() => api.stopBot(bot.token_hash), 'Polling stopped')}>
              <Square size={12} /> Stop
            </Btn>
          ) : (
            <Btn size="sm" variant="success" className="flex-1 justify-center"
              onClick={() => act(() => api.startBot(bot.token_hash), 'Polling started')}>
              <Play size={12} /> Start
            </Btn>
          )}
          <Btn size="sm" variant="ghost" disabled={busy}
            onClick={() => act(() => api.restartBot(bot.token_hash), 'Restarted')}>
            <RefreshCw size={12} />
          </Btn>
          <Btn size="sm" variant="ghost" onClick={() => setImportModal(true)}
            className="border-brand/30 text-brand hover:bg-brand/10">
            <History size={12} /> Import History
          </Btn>
        </div>
      </Card>

      {importModal && (
        <ImportModal bot={bot} toast={toast} onClose={() => setImportModal(false)} />
      )}
    </>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function Bots({ bots, onRefresh, toast }) {
  const [addModal, setAddModal] = useState(false)

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-gray-100">Bot Manager</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {bots.length} bot{bots.length !== 1 ? 's' : ''} registered
          </p>
        </div>
        <div className="flex gap-2">
          <Btn onClick={onRefresh}><RefreshCw size={14} /> Refresh</Btn>
          <Btn variant="primary" onClick={() => setAddModal(true)}>
            <Plus size={14} /> Add Bot
          </Btn>
        </div>
      </div>

      {/* MTProto info banner */}
      <div className="bg-[#111b2e] border border-brand/20 rounded-xl p-4 mb-6">
        <div className="flex items-start gap-3">
          <span className="text-2xl flex-shrink-0">⚡</span>
          <div>
            <p className="text-sm font-semibold text-brand mb-1">MTProto History Import Available</p>
            <p className="text-xs text-gray-400 leading-relaxed">
              Each bot card has an <strong className="text-gray-300">Import History</strong> button.
              This uses Telethon with your bot token to fetch the full message history of any chat
              the bot is a member of — going back to day one, not just 24 hours.
              Requires <code className="bg-gray-900 px-1 rounded text-brand">TELEGRAM_API_ID</code> and{' '}
              <code className="bg-gray-900 px-1 rounded text-brand">TELEGRAM_API_HASH</code> in your
              environment (free from{' '}
              <a href="https://my.telegram.org" target="_blank" rel="noreferrer"
                className="text-brand underline">my.telegram.org</a>).
            </p>
          </div>
        </div>
      </div>

      {bots.length === 0 ? (
        <Card className="p-12 text-center">
          <div className="text-5xl mb-4">🤖</div>
          <p className="text-gray-400 font-medium mb-1">No bots yet</p>
          <p className="text-sm text-gray-600 mb-5">
            Get a token from @BotFather and add it here
          </p>
          <Btn variant="primary" onClick={() => setAddModal(true)}>
            <Plus size={14} /> Add Your First Bot
          </Btn>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {bots.map(b => (
            <BotCard key={b.token_hash} bot={b} onRefresh={onRefresh} toast={toast} />
          ))}
        </div>
      )}

      {addModal && (
        <AddBotModal
          onClose={() => setAddModal(false)}
          onAdded={onRefresh}
          toast={toast}
        />
      )}
    </div>
  )
}
