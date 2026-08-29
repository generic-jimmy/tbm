import { useState } from 'react'
import { api } from '../api/client'
import { Btn, Card, Input } from '../components/ui'
import { Download, FolderOpen, Search } from 'lucide-react'

const STATUS_CLS = {
  done:  'text-emerald-400', error: 'text-red-400',
  dl:    'text-amber-400',   info:  'text-gray-400',
}

export default function Files({ bots, toast }) {
  const [botHash,  setBotHash]  = useState(bots[0]?.token_hash || '')
  const [fileId,   setFileId]   = useState('')
  const [info,     setInfo]     = useState(null)
  const [history,  setHistory]  = useState([])
  const [loading,  setLoading]  = useState(false)

  async function fetchInfo() {
    if (!fileId.trim() || !botHash) return
    setLoading(true); setInfo(null)
    try {
      const r = await api.fileInfo(botHash, fileId.trim())
      setInfo(r)
      toast('File info loaded')
    } catch (e) { toast('Error: ' + e.message) }
    finally { setLoading(false) }
  }

  function startDownload() {
    if (!info) return
    const fname = info.file_path?.split('/').pop() || 'file'
    const url   = api.downloadUrl(botHash, fileId.trim())
    const entry = {
      id:      Date.now(),
      file_id: fileId.trim().slice(0, 24) + '…',
      fname,
      status:  'Downloading…',
      url,
    }
    setHistory(h => [entry, ...h])
    const a = document.createElement('a')
    a.href = url; a.download = fname; a.click()
    setTimeout(() => {
      setHistory(h => h.map(x => x.id === entry.id ? { ...x, status: '✔ Done' } : x))
    }, 2000)
    toast('Download started')
  }

  return (
    <div className="p-6 max-w-3xl">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-gray-100">File Manager</h1>
        <p className="text-sm text-gray-500 mt-0.5">Download files received by your bots</p>
      </div>

      {/* Bot selector */}
      <Card className="p-5 mb-6">
        <label className="block text-xs text-gray-400 mb-1.5 font-medium uppercase tracking-wide">Bot</label>
        <select value={botHash} onChange={e => setBotHash(e.target.value)}
          className="bg-[#0d1425] border border-gray-700 rounded-lg px-3 py-2 text-sm
            text-gray-100 focus:outline-none focus:border-brand">
          {bots.map(b => (
            <option key={b.token_hash} value={b.token_hash}>@{b.username} — {b.name}</option>
          ))}
        </select>
      </Card>

      {/* Manual download */}
      <Card className="p-5 mb-6">
        <h2 className="text-sm font-semibold text-gray-200 mb-4">Download by File ID</h2>
        <div className="flex gap-3">
          <input value={fileId} onChange={e => setFileId(e.target.value)}
            placeholder="Paste File ID here (from Live Monitor)"
            className="flex-1 bg-[#0d1425] border border-gray-700 rounded-lg px-3 py-2.5 text-sm
              text-gray-100 placeholder-gray-600 focus:outline-none focus:border-brand" />
          <Btn onClick={fetchInfo} disabled={loading || !fileId.trim()}>
            <Search size={14} /> {loading ? 'Loading…' : 'Info'}
          </Btn>
        </div>

        {/* File info */}
        {info && (
          <div className="mt-4 bg-[#0d1425] rounded-xl p-4 space-y-2">
            <div className="grid grid-cols-2 gap-3 text-xs">
              {[
                ['File ID',    info.file_id],
                ['File Path',  info.file_path],
                ['File Size',  info.file_size ? `${Number(info.file_size).toLocaleString()} bytes` : '—'],
              ].map(([l, v]) => (
                <div key={l}>
                  <p className="text-gray-600 mb-0.5">{l}</p>
                  <p className="text-gray-300 font-mono truncate">{v || '—'}</p>
                </div>
              ))}
            </div>
            <Btn variant="primary" onClick={startDownload} className="mt-3">
              <Download size={14} /> Download File
            </Btn>
          </div>
        )}
      </Card>

      {/* Download history */}
      {history.length > 0 && (
        <Card className="overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-800">
            <h2 className="text-sm font-semibold text-gray-200">Download History (this session)</h2>
          </div>
          <div className="divide-y divide-gray-800">
            {history.map(h => (
              <div key={h.id} className="flex items-center gap-3 px-5 py-3">
                <Download size={14} className="text-gray-600 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-gray-300 truncate">{h.fname}</p>
                  <p className="text-[10px] text-gray-600 font-mono truncate">{h.file_id}</p>
                </div>
                <span className={`text-xs ${STATUS_CLS[h.status?.includes('Done') ? 'done' : 'dl']}`}>
                  {h.status}
                </span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Tips */}
      <div className="mt-6 bg-[#111b2e] border border-gray-800 rounded-xl p-4 space-y-1">
        <p className="text-xs font-medium text-brand mb-2">📁 Storage Group</p>
        <p className="text-xs text-gray-500">When a bot receives a file and Auto-forward is enabled, the file is forwarded to your Storage Group and stored permanently on Telegram's servers.</p>
        <p className="text-xs text-gray-500 mt-1">The <strong className="text-gray-400">tg_storage_file_id</strong> column in the monitor contains the permanent file ID — use this for most reliable downloads.</p>
      </div>
    </div>
  )
}
