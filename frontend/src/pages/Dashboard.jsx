import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'
import { useWebSocket } from '../store/ws'
import { TypeIcon, Spinner } from '../components/ui'

function StatCard({ label, value, icon, color, sub }) {
  return (
    <div className="bg-[#111b2e] border border-gray-800 rounded-xl p-5 relative overflow-hidden">
      <div className="absolute top-0 inset-x-0 h-0.5 rounded-t-xl" style={{ background: color }} />
      <div className="flex items-start justify-between mb-1">
        <span className="text-xl">{icon}</span>
        <span className="font-mono text-2xl font-semibold tabular-nums" style={{ color }}>
          {(value ?? 0).toLocaleString()}
        </span>
      </div>
      <p className="text-xs text-gray-500">{label}</p>
      {sub && <p className="text-[10px] text-gray-700 mt-0.5">{sub}</p>}
    </div>
  )
}

export default function Dashboard() {
  const [stats,   setStats]   = useState(null)
  const [feed,    setFeed]    = useState([])
  const [loading, setLoading] = useState(true)

  async function loadStats() {
    try { setStats(await api.stats()) } catch {}
  }

  useEffect(() => {
    loadStats().finally(() => setLoading(false))
    const iv = setInterval(loadStats, 15000)
    return () => clearInterval(iv)
  }, [])

  const onWs = useCallback((msg) => {
    if (msg.type === 'new_message') {
      setFeed(f => [msg, ...f].slice(0, 120))
    }
    if (msg.type === 'stats_refresh') loadStats()
    if (msg.type === 'import_progress' && msg.status === 'done') loadStats()
  }, [])
  useWebSocket(onWs)

  if (loading) return (
    <div className="flex items-center justify-center h-full">
      <Spinner />
    </div>
  )

  const botApiCount   = stats?.total - (stats?.mtproto_imported || 0)
  const mtprotoCount  = stats?.mtproto_imported || 0

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-gray-100">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Real-time overview — Bot API + MTProto combined
        </p>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">
        <StatCard label="Total Messages"  icon="💬" color="#2AABEE"
          value={stats?.total}       sub="all sources" />
        <StatCard label="Text Messages"   icon="✍"  color="#00d98b"
          value={stats?.texts} />
        <StatCard label="Media Files"     icon="📂"  color="#ffc947"
          value={stats?.media} />
        <StatCard label="Active Chats"    icon="👥"  color="#a78bfa"
          value={stats?.chats} />
        <StatCard label="Active Bots"     icon="🤖"  color="#f97316"
          value={stats?.active_bots} />
        <StatCard label="MTProto Import"  icon="🔵"  color="#60a5fa"
          value={mtprotoCount}       sub="via Telethon" />
      </div>

      {/* Source breakdown */}
      {stats?.total > 0 && (
        <div className="bg-[#111b2e] border border-gray-800 rounded-xl p-4">
          <p className="text-xs font-semibold text-gray-400 mb-3">Message Sources</p>
          <div className="flex gap-4 items-center">
            <div className="flex-1 h-2 rounded-full bg-gray-800 overflow-hidden">
              <div
                className="h-full bg-brand rounded-full transition-all duration-500"
                style={{ width: `${stats?.total ? (botApiCount / stats.total) * 100 : 0}%` }}
              />
            </div>
            <div className="flex items-center gap-4 text-xs text-gray-500 flex-shrink-0">
              <span>
                <span className="inline-block w-2 h-2 rounded-sm bg-brand mr-1.5" />
                Bot API: <strong className="text-gray-300">{botApiCount.toLocaleString()}</strong>
              </span>
              <span>
                <span className="inline-block w-2 h-2 rounded-sm bg-blue-400 mr-1.5" />
                MTProto: <strong className="text-blue-300">{mtprotoCount.toLocaleString()}</strong>
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Live feed */}
      <div className="bg-[#111b2e] border border-gray-800 rounded-xl overflow-hidden">
        <div className="px-5 py-3.5 border-b border-gray-800 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-200">Live Feed</h2>
          <span className="flex items-center gap-1.5 text-xs text-emerald-400">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Live
          </span>
        </div>
        <div className="divide-y divide-gray-800/50 max-h-[400px] overflow-auto">
          {feed.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 gap-2 text-gray-600">
              <span className="text-3xl">📡</span>
              <span className="text-sm">Waiting for messages…</span>
            </div>
          ) : feed.map((m, i) => (
            <div key={i} className="flex items-start gap-3 px-5 py-3 hover:bg-[#141c2e] transition-colors">
              <TypeIcon kind={m.kind} />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                  <span className="text-xs font-medium text-gray-200">
                    {m.sender_name || 'system'}
                  </span>
                  <span className="text-xs text-gray-600">
                    {m.chat_title || (m.chat_id ? `chat:${m.chat_id}` : '')}
                  </span>
                  {m.bot_username && (
                    <span className="text-[10px] text-brand">@{m.bot_username}</span>
                  )}
                  <span className="text-xs text-gray-700 ml-auto whitespace-nowrap">
                    {m.ts ? new Date(m.ts).toLocaleTimeString() : ''}
                  </span>
                </div>
                <p className="text-xs text-gray-500 truncate">
                  {(m.content || '—').replace(/\n/g, ' ')}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
