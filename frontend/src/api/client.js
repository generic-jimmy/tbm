const BASE = ''

export function getToken() { return localStorage.getItem('tbm_token') }

async function request(path, opts = {}) {
  const token = getToken()
  const isForm = opts.body instanceof FormData
  const res = await fetch(BASE + path, {
    ...opts,
    headers: {
      ...(isForm ? {} : { 'Content-Type': 'application/json' }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(opts.headers || {}),
    },
  })
  if (res.status === 401) {
    localStorage.removeItem('tbm_token')
    window.location.href = '/login'
    return
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  const ct = res.headers.get('content-type') || ''
  if (ct.includes('application/json')) return res.json()
  return res
}

export const api = {
  // ── auth ──────────────────────────────────────────────────────────────────
  login: (password) =>
    request('/api/auth/login', { method: 'POST', body: JSON.stringify({ password }) }),

  // ── bots ──────────────────────────────────────────────────────────────────
  bots:       ()                   => request('/api/bots'),
  addBot:     (token, storage_chat_id) =>
    request('/api/bots', { method: 'POST', body: JSON.stringify({ token, storage_chat_id }) }),
  removeBot:  (hash)               => request(`/api/bots/${hash}`,          { method: 'DELETE' }),
  startBot:   (hash)               => request(`/api/bots/${hash}/start`,    { method: 'POST' }),
  stopBot:    (hash)               => request(`/api/bots/${hash}/stop`,     { method: 'POST' }),
  restartBot: (hash)               => request(`/api/bots/${hash}/restart`,  { method: 'POST' }),
  botStatus:  (hash)               => request(`/api/bots/${hash}/status`),
  updateStorage: (hash, id) =>
    request(`/api/bots/${hash}/storage`, { method: 'PUT', body: JSON.stringify({ storage_chat_id: id }) }),

  // ── MTProto history import ─────────────────────────────────────────────────
  startImport: (payload) =>
    request('/api/history/import', { method: 'POST', body: JSON.stringify(payload) }),
  importJob:  (jobId) => request(`/api/history/job/${jobId}`),
  importJobs: (hash)  => request(`/api/history/jobs?bot_hash=${hash}`),

  // ── messages ──────────────────────────────────────────────────────────────
  messages: (params) => {
    const q = new URLSearchParams(
      Object.fromEntries(
        Object.entries(params).filter(([, v]) => v != null && v !== '' && v !== 'all')
      )
    )
    return request(`/api/messages?${q}`)
  },

  // ── stats ──────────────────────────────────────────────────────────────────
  stats:    ()     => request('/api/stats'),
  botStats: (hash) => request(`/api/stats/bot?bot_hash=${hash}`),

  // ── chats ──────────────────────────────────────────────────────────────────
  chats: (hash) => request(`/api/chats?bot_hash=${hash}`),

  // ── send ───────────────────────────────────────────────────────────────────
  // reply_markup, if passed, is { inline_keyboard: [[{text,url}], ...] } —
  // URL buttons only (no callback_data handler wired up server-side yet).
  send: (payload) =>
    request('/api/send', { method: 'POST', body: JSON.stringify(payload) }),

  sendMedia: (formData) =>
    request('/api/send/media', { method: 'POST', body: formData }),

  // ── templates ─────────────────────────────────────────────────────────────
  templates:       ()               => request('/api/templates'),
  createTemplate:  (payload)        =>
    request('/api/templates', { method: 'POST', body: JSON.stringify(payload) }),
  deleteTemplate:  (id)             =>
    request(`/api/templates/${id}`, { method: 'DELETE' }),

  // ── files ──────────────────────────────────────────────────────────────────
  fileInfo: (hash, fid) => request(`/api/files/${fid}/info?bot_hash=${hash}`),

  // Downloads use ?token= because the browser cannot inject Authorization
  // headers on direct link clicks / <a download> / window.open().
  // The backend's require_auth_or_query dependency reads this param.
  downloadUrl: (hash, fid) =>
    `${BASE}/api/files/${fid}/download?bot_hash=${hash}&token=${getToken()}`,

  // ── export ─────────────────────────────────────────────────────────────────
  exportUrl: (type, hash, kind, chatId, source) => {
    const q = new URLSearchParams({ bot_hash: hash })
    if (kind   && kind   !== 'all') q.set('kind',    kind)
    if (chatId)                      q.set('chat_id', chatId)
    if (source && source !== 'all') q.set('source',  source)
    // Same as downloadUrl — pass token as query param for browser link downloads.
    q.set('token', getToken())
    return `${BASE}/api/export/${type}?${q}`
  },
}

export function wsUrl(botHash = null) {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const token = getToken()
  const base  = `${proto}://${window.location.host}/ws?token=${token}`
  return botHash ? `${base}&bot_hash=${botHash}` : base
}
