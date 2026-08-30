import { useState, useEffect, useCallback, useRef } from 'react'
import { api } from '../api/client'
import { useWebSocket } from '../store/ws'
import { MSG_META, TypeIcon, Btn, Spinner, copy } from '../components/ui'
import { Search, Download, Copy, Reply, RefreshCw } from 'lucide-react'

const KIND_TABS  = ['all','text','photo','document','video','audio','voice','sticker','location','contact']
const SRC_TABS   = ['all','bot_api','telethon']
const SRC_LABELS = { all: 'All Sources', bot_api: '⚡ Bot API', telethon: '🔵 MTProto' }

// ─── Detail panel ─────────────────────────────────────────────────────────────
function DetailPanel({ row, bots, toast, navigate }) {
  if (!row) return (
    <div className="flex items-center justify-center h-full text-sm text-gray-600 p-6 text-center">
      Click any row to see full details
    </div>
  )

  const bot = bots.find(b => b.token_hash === row.bot_hash)
  const fields = [
    ['Time',        row.ts ? new Date(row.ts).toLocaleString() : '—'],
    ['Type',        row.kind],
    ['Source',      row.source === 'telethon' ? '🔵 MTProto' : '⚡ Bot API'],
    ['Sender',      row.sender_name],
    ['User ID',     row.sender_id],
    ['Chat',        row.chat_title],
    ['Chat ID',     row.chat_id],
    ['Bot',         bot ? `@${bot.username}` : row.bot_hash?.slice(0,8)+'…'],
    ['File ID',     row.tg_storage_file_id || row.file_id],
    ['File Name',   row.file_name],
    ['File Size',   row.file_size ? `${Number(row.file_size).toLocaleString()} bytes` : null],
    ['MIME',        row.mime_type],
    ['Forwarded',   row.is_forwarded ? `Yes — ${row.fwd_from || '?'}` : 'No'],
    ['Reply To',    row.reply_to_id],
    ['Storage ID',  row.tg_storage_msg_id],
  ]

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-800 flex-shrink-0">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Detail</p>
      </div>

      <div className="flex-1 overflow-auto px-4 py-3 space-y-2">
        {fields.map(([label, value]) => value != null && String(value).length > 0 && (
          <div key={label} className="flex gap-2">
            <span className="text-[10px] text-gray-600 w-20 flex-shrink-0 pt-0.5 leading-4">{label}</span>
            <span
              className="text-xs text-gray-300 break-all cursor-pointer hover:text-brand transition leading-4"
              title="Click to copy"
              onClick={() => copy(value, label, toast)}
            >{String(value)}</span>
          </div>
        ))}

        {(row.content || row.caption) && (
          <div className="pt-3 border-t border-gray-800">
            <p className="text-[10px] text-gray-600 mb-1.5">Content</p>
            <p className="text-xs text-gray-300 whitespace-pre-wrap bg-[#0d1425] rounded-lg p-2.5 leading-relaxed">
              {row.content || ''}
            </p>
            {row.caption && (
              <p className="text-xs text-gray-400 mt-2 bg-[#0d1425] rounded-lg p-2.5">
                📝 {row.caption}
              </p>
            )}
          </div>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex-shrink-0 border-t border-gray-800 px-4 py-3 space-y-1">
        {(row.tg_storage_file_id || row.file_id) && (
          <button onClick={() => copy(row.tg_storage_file_id || row.file_id, 'File ID', toast)}
            className="flex items-center gap-2 w-full px-3 py-1.5 text-xs text-gray-400
              hover:bg-[#172035] hover:text-brand rounded-lg transition">
            <Copy size={11} /> Copy File ID
          </button>
        )}
        <button onClick={() => copy(row.sender_id, 'User ID', toast)}
          className="flex items-center gap-2 w-full px-3 py-1.5 text-xs text-gray-400
            hover:bg-[#172035] hover:text-brand rounded-lg transition">
          <Copy size={11} /> Copy User ID
        </button>
        <button onClick={() => copy(row.chat_id, 'Chat ID', toast)}
          className="flex items-center gap-2 w-full px-3 py-1.5 text-xs text-gray-400
            hover:bg-[#172035] hover:text-brand rounded-lg transition">
          <Copy size={11} /> Copy Chat ID
        </button>
        {row.chat_id && (
          <button onClick={() => navigate('/compose', { state: { chat_id: row.chat_id, bot_hash: row.bot_hash } })}
            className="flex items-center gap-2 w-full px-3 py-1.5 text-xs text-gray-400
              hover:bg-[#172035] hover:text-emerald-400 rounded-lg transition">
            <Reply size={11} /> Reply to Chat
          </button>
        )}
        {row.bot_hash && (row.tg_storage_file_id || row.file_id) && (
          <a href={api.downloadUrl(row.bot_hash, row.tg_storage_file_id || row.file_id)}
            download
            className="flex items-center gap-2 w-full px-3 py-1.5 text-xs text-gray-400
              hover:bg-[#172035] hover:text-amber-400 rounded-lg transition">
            <Download size={11} /> Download File
          </a>
        )}
      </div>
    </div>
  )
}

// ─── Context menu ─────────────────────────────────────────────────────────────
function CtxMenu({ menu, row, toast, navigate, onClose }) {
  useEffect(() => {
    if (!menu) return
    const fn = () => onClose()
    window.addEventListener('click', fn)
    return () => window.removeEventListener('click', fn)
  }, [menu, onClose])

  if (!menu || !row) return null

  const fid = row.tg_storage_file_id || row.file_id
  return (
    <div style={{ top: menu.y, left: Math.min(menu.x, window.innerWidth - 180) }}
      className="fixed z-50 bg-[#111b2e] border border-gray-700 rounded-xl shadow-2xl py-1 min-w-44"
      onClick={e => e.stopPropagation()}>
      {fid && <Item icon={<Copy size={11}/>} label="Copy File ID" onClick={() => { copy(fid, 'File ID', toast); onClose() }} />}
      <Item icon={<Copy size={11}/>} label="Copy User ID" onClick={() => { copy(row.sender_id, 'User ID', toast); onClose() }} />
      <Item icon={<Copy size={11}/>} label="Copy Chat ID" onClick={() => { copy(row.chat_id, 'Chat ID', toast); onClose() }} />
      <div className="my-1 border-t border-gray-800" />
      {row.chat_id && (
        <Item icon={<Reply size={11}/>} label="Reply to Chat"
          onClick={() => { navigate('/compose', { state: { chat_id: row.chat_id, bot_hash: row.bot_hash } }); onClose() }} />
      )}
      {fid && row.bot_hash && (
        <a href={api.downloadUrl(row.bot_hash, fid)} download onClick={onClose}
          className="flex items-center gap-2.5 px-3 py-2 text-xs text-gray-400
            hover:bg-[#172035] hover:text-amber-400 transition">
          <Download size={11} /> Download File
        </a>
      )}
    </div>
  )
}

function Item({ icon, label, onClick }) {
  return (
    <button onClick={onClick} className="flex items-center gap-2.5 w-full px-3 py-2 text-xs
      text-gray-400 hover:bg-[#172035] hover:text-brand transition">
      {icon} {label}
    </button>
  )
}

// ─── Main Monitor page ────────────────────────────────────────────────────────
export default function Monitor({ bots, toast, navigate }) {
  const [rows,     setRows]     = useState([])
  const [sel,      setSel]      = useState(null)
  const [loading,  setLoading]  = useState(true)
  const [kindTab,  setKindTab]  = useState('all')
  const [srcTab,   setSrcTab]   = useState('all')
  const [search,   setSearch]   = useState('')
  const [botFlt,   setBotFlt]   = useState('all')
  const [chatFlt,  setChatFlt]  = useState('')
  const [chats,    setChats]    = useState([])
  const [menu,     setMenu]     = useState(null)
  const [sortCol,  setSortCol]  = useState('ts')
  const [sortAsc,  setSortAsc]  = useState(false)
  const searchTimer = useRef(null)

  const activeBotHash = botFlt !== 'all' ? botFlt : bots[0]?.token_hash

  async function load(extra = {}) {
    if (!activeBotHash) { setRows([]); setLoading(false); return }
    setLoading(true)
    try {
      const data = await api.messages({
        bot_hash: activeBotHash,
        kind:     kindTab !== 'all' ? kindTab : undefined,
        source:   srcTab  !== 'all' ? srcTab  : undefined,
        chat_id:  chatFlt || undefined,
        search:   search  || undefined,
        limit:    300,
        ...extra,
      })
      setRows(data)
    } catch (e) { toast('Load error: ' + e.message) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [kindTab, srcTab, botFlt, chatFlt, activeBotHash])
  useEffect(() => {
    clearTimeout(searchTimer.current)
    searchTimer.current = setTimeout(() => load(), 350)
    return () => clearTimeout(searchTimer.current)
  }, [search])

  useEffect(() => {
    if (!activeBotHash) return
    api.chats(activeBotHash).then(setChats).catch(() => {})
  }, [activeBotHash])

  const onWs = useCallback((msg) => {
    if (msg.type === 'stats_refresh') return
    if (msg.type !== 'new_message') return
    if (botFlt !== 'all' && msg.bot_hash !== botFlt) return
    if (kindTab !== 'all' && msg.kind !== kindTab) return
    if (srcTab  !== 'all' && (msg.source || 'bot_api') !== srcTab) return
    setRows(prev => [msg, ...prev].slice(0, 400))
  }, [botFlt, kindTab, srcTab])
  useWebSocket(onWs)

  function sortBy(col) {
    setSortAsc(a => sortCol === col ? !a : false)
    setSortCol(col)
  }

  const displayed = [...rows].sort((a, b) => {
    let av = a[sortCol], bv = b[sortCol]
    if (typeof av === 'string') { av = av.toLowerCase(); bv = (bv||'').toLowerCase() }
    return sortAsc ? (av > bv ? 1 : -1) : (av < bv ? 1 : -1)
  })

  function Th({ col, label, cls = '' }) {
    return (
      <th onClick={() => sortBy(col)}
        className={`px-3 py-2.5 text-left text-xs font-medium text-gray-500
          cursor-pointer hover:text-gray-300 select-none whitespace-nowrap ${cls}`}>
        {label}{sortCol === col ? (sortAsc ? ' ↑' : ' ↓') : ''}
      </th>
    )
  }

  return (
    <div className="flex flex-col h-full bg-gray-950">
      {/* ── Header ── */}
      <div className="px-5 py-3 border-b border-gray-800 flex items-center gap-3 flex-wrap bg-[#0d1425]">
        <h1 className="text-base font-semibold text-gray-100">Live Monitor</h1>

        {/* Bot filter */}
        <select value={botFlt} onChange={e => setBotFlt(e.target.value)}
          className="bg-[#111b2e] border border-gray-700 rounded-lg px-3 py-1.5 text-xs text-gray-300">
          <option value="all">All Bots</option>
          {bots.map(b => <option key={b.token_hash} value={b.token_hash}>@{b.username}</option>)}
        </select>

        {/* Chat filter */}
        <select value={chatFlt} onChange={e => setChatFlt(e.target.value)}
          className="bg-[#111b2e] border border-gray-700 rounded-lg px-3 py-1.5 text-xs text-gray-300">
          <option value="">All Chats</option>
          {chats.map(c => (
            <option key={c.chat_id} value={c.chat_id}>
              {c.title || `Chat ${c.chat_id}`}
            </option>
          ))}
        </select>

        {/* Search */}
        <div className="relative">
          <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-600" />
          <input value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search content, sender, file…"
            className="bg-[#111b2e] border border-gray-700 rounded-lg pl-7 pr-3 py-1.5
              text-xs text-gray-300 placeholder-gray-600 focus:outline-none focus:border-brand w-48" />
        </div>

        <div className="ml-auto flex items-center gap-2">
          <Btn size="sm" onClick={() => load()}><RefreshCw size={12} /> Reload</Btn>
          <div className="relative group">
            <Btn size="sm">Export ▾</Btn>
            <div className="absolute right-0 top-full mt-1 z-20 hidden group-hover:flex flex-col
              bg-[#111b2e] border border-gray-700 rounded-xl shadow-2xl py-1 min-w-32">
              {['csv','json','xlsx'].map(t => (
                <a key={t}
                  href={api.exportUrl(t, activeBotHash,
                    kindTab !== 'all' ? kindTab : null,
                    chatFlt || null,
                    srcTab  !== 'all' ? srcTab  : null)}
                  download
                  className="px-4 py-2 text-xs text-gray-400 hover:text-brand hover:bg-[#172035] transition">
                  {t.toUpperCase()}
                </a>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── Source tabs (MTProto vs Bot API) ── */}
      <div className="flex border-b border-gray-800 bg-[#0a0f1a] px-1">
        {SRC_TABS.map(s => (
          <button key={s} onClick={() => setSrcTab(s)}
            className={`px-4 py-2 text-xs whitespace-nowrap transition border-b-2 font-medium
              ${srcTab === s
                ? s === 'telethon' ? 'border-blue-400 text-blue-400'
                  : s === 'bot_api' ? 'border-brand text-brand'
                  : 'border-gray-400 text-gray-300'
                : 'border-transparent text-gray-600 hover:text-gray-400'}`}>
            {SRC_LABELS[s]}
          </button>
        ))}
        {srcTab === 'telethon' && (
          <span className="ml-3 self-center text-[10px] text-blue-400/70 font-medium">
            Full history — fetched via MTProto
          </span>
        )}
      </div>

      {/* ── Kind tabs ── */}
      <div className="flex border-b border-gray-800 bg-[#0d1425] overflow-x-auto">
        {KIND_TABS.map(t => {
          const m = MSG_META[t]
          return (
            <button key={t} onClick={() => setKindTab(t)}
              className={`px-3 py-2 text-xs whitespace-nowrap transition border-b-2
                ${kindTab === t ? 'border-brand text-brand' : 'border-transparent text-gray-600 hover:text-gray-400'}`}>
              {m ? `${m.icon} ${m.label}` : 'All'}
            </button>
          )
        })}
      </div>

      {/* ── Content: table + detail ── */}
      <div className="flex flex-1 min-h-0">
        {/* Table */}
        <div className="flex-1 overflow-auto">
          {loading ? (
            <div className="flex items-center justify-center h-32"><Spinner /></div>
          ) : displayed.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-40 gap-2 text-sm text-gray-600">
              <span className="text-2xl">📭</span>
              {srcTab === 'telethon'
                ? 'No MTProto messages yet — use Import History in Bot Manager'
                : 'No messages found'}
            </div>
          ) : (
            <table className="w-full text-xs">
              <thead className="sticky top-0 z-10 bg-[#0d1425]">
                <tr>
                  <Th col="ts"          label="Time"    cls="w-24" />
                  <Th col="kind"        label="Type"    cls="w-24" />
                  <Th col="source"      label="Source"  cls="w-20" />
                  <Th col="sender_name" label="Sender"  cls="w-28" />
                  <Th col="sender_id"   label="User ID" cls="w-24" />
                  <Th col="chat_title"  label="Chat"    cls="w-28" />
                  <Th col="file_id"     label="File ID" cls="w-32" />
                  <Th col="content"     label="Preview" cls="" />
                </tr>
              </thead>
              <tbody>
                {displayed.map((row, i) => {
                  const m   = MSG_META[row.kind] || MSG_META.system
                  const isSel = sel?.msg_id === row.msg_id && sel?.bot_hash === row.bot_hash
                      && sel?.chat_id === row.chat_id
                  const fid = row.tg_storage_file_id || row.file_id || ''
                  const isMtproto = row.source === 'telethon'

                  return (
                    <tr key={i}
                      onClick={() => setSel(isSel ? null : row)}
                      onContextMenu={e => { e.preventDefault(); setSel(row); setMenu({ x: e.clientX, y: e.clientY }) }}
                      className={`border-b border-gray-800/40 cursor-pointer transition-colors
                        ${isSel ? 'bg-[#1c2a45]' : 'hover:bg-[#141c2e]'}`}>
                      <td className="px-3 py-2 text-gray-600 whitespace-nowrap font-mono">
                        {row.ts ? new Date(row.ts).toLocaleTimeString() : '—'}
                      </td>
                      <td className="px-3 py-2 whitespace-nowrap" style={{ color: m.color }}>
                        {m.icon} {m.label}
                      </td>
                      <td className="px-3 py-2 whitespace-nowrap">
                        <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${
                          isMtproto
                            ? 'bg-blue-900/40 text-blue-300'
                            : 'bg-gray-800 text-gray-500'
                        }`}>
                          {isMtproto ? 'MTProto' : 'Bot API'}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-gray-300 truncate max-w-28">{row.sender_name || '—'}</td>
                      <td className="px-3 py-2 text-gray-500 font-mono">{row.sender_id || '—'}</td>
                      <td className="px-3 py-2 text-gray-400 truncate max-w-28">
                        {row.chat_title || row.chat_id || '—'}
                      </td>
                      <td className="px-3 py-2 text-gray-600 font-mono truncate max-w-32">
                        {fid ? fid.slice(0, 20) + (fid.length > 20 ? '…' : '') : '—'}
                      </td>
                      <td className="px-3 py-2 text-gray-400 truncate max-w-xs">
                        {(row.content || '').replace(/\n/g, ' ').slice(0, 80)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Detail panel */}
        <div className="w-60 flex-shrink-0 border-l border-gray-800 bg-[#0d1425] overflow-hidden">
          <DetailPanel row={sel} bots={bots} toast={toast} navigate={navigate} />
        </div>
      </div>

      <CtxMenu menu={menu} row={sel} toast={toast} navigate={navigate}
        onClose={() => setMenu(null)} />
    </div>
  )
}
