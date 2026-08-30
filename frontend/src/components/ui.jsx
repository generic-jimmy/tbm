// Shared UI primitives
export const C = {
  bg:      'bg-gray-950',
  panel:   'bg-surface-1',
  card:    'bg-surface-2',
  card2:   'bg-surface-3',
  border:  'border-gray-800',
  text:    'text-gray-100',
  muted:   'text-gray-400',
  dim:     'text-gray-600',
  accent:  'text-brand',
  green:   'text-emerald-400',
  red:     'text-red-400',
  amber:   'text-amber-400',
  purple:  'text-purple-400',
}

export function Card({ children, className = '', ...p }) {
  return (
    <div className={`bg-[#111b2e] border border-gray-800 rounded-xl ${className}`} {...p}>
      {children}
    </div>
  )
}

export function Btn({ children, variant = 'ghost', size = 'md', className = '', ...p }) {
  const base = 'inline-flex items-center gap-2 rounded-lg font-medium transition-all cursor-pointer disabled:opacity-50'
  const sizes = { sm: 'px-3 py-1.5 text-xs', md: 'px-4 py-2 text-sm', lg: 'px-5 py-2.5 text-sm' }
  const variants = {
    primary: 'bg-brand hover:bg-brand-dark text-gray-950',
    success: 'bg-emerald-500 hover:bg-emerald-600 text-gray-950',
    danger:  'bg-red-500 hover:bg-red-600 text-white',
    ghost:   'bg-[#141c2e] hover:bg-[#172035] text-gray-300 border border-gray-800',
    outline: 'border border-gray-700 hover:bg-[#141c2e] text-gray-300',
  }
  return (
    <button className={`${base} ${sizes[size]} ${variants[variant]} ${className}`} {...p}>
      {children}
    </button>
  )
}

export function Input({ label, className = '', ...p }) {
  return (
    <div>
      {label && <label className="block text-xs text-gray-400 mb-1.5 font-medium uppercase tracking-wide">{label}</label>}
      <input
        className={`w-full bg-[#111b2e] border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100
          placeholder-gray-600 focus:outline-none focus:border-brand focus:ring-1 focus:ring-brand transition ${className}`}
        {...p}
      />
    </div>
  )
}

export function Select({ label, children, className = '', ...p }) {
  return (
    <div>
      {label && <label className="block text-xs text-gray-400 mb-1.5 font-medium uppercase tracking-wide">{label}</label>}
      <select
        className={`bg-[#111b2e] border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100
          focus:outline-none focus:border-brand transition ${className}`}
        {...p}
      >
        {children}
      </select>
    </div>
  )
}

export function Badge({ children, color = 'blue' }) {
  const colors = {
    blue:   'bg-blue-900/40 text-blue-300 border-blue-800',
    green:  'bg-emerald-900/40 text-emerald-300 border-emerald-800',
    red:    'bg-red-900/40 text-red-300 border-red-800',
    amber:  'bg-amber-900/40 text-amber-300 border-amber-800',
    purple: 'bg-purple-900/40 text-purple-300 border-purple-800',
    gray:   'bg-gray-800 text-gray-400 border-gray-700',
  }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs border font-medium ${colors[color]}`}>
      {children}
    </span>
  )
}

export function StatusDot({ status }) {
  const map = {
    polling:  'bg-emerald-400 shadow-emerald-400/50',
    draining: 'bg-amber-400 shadow-amber-400/50',
    starting: 'bg-blue-400 shadow-blue-400/50',
    stopped:  'bg-gray-600',
    error:    'bg-red-400 shadow-red-400/50',
  }
  const cls = map[status] || 'bg-gray-600'
  return (
    <span className={`inline-block w-2 h-2 rounded-full ${cls} ${status !== 'stopped' ? 'shadow-[0_0_6px_1px]' : ''}`} />
  )
}

export const MSG_META = {
  text:     { color: '#2AABEE', icon: '💬', label: 'Text' },
  photo:    { color: '#a78bfa', icon: '📷', label: 'Photo' },
  document: { color: '#ffc947', icon: '📎', label: 'Doc' },
  video:    { color: '#f97316', icon: '🎬', label: 'Video' },
  audio:    { color: '#00d98b', icon: '🎵', label: 'Audio' },
  voice:    { color: '#06b6d4', icon: '🎙', label: 'Voice' },
  sticker:  { color: '#f43f5e', icon: '🎭', label: 'Sticker' },
  location: { color: '#84cc16', icon: '📍', label: 'Location' },
  contact:  { color: '#e879f9', icon: '👤', label: 'Contact' },
  edited:   { color: '#fbbf24', icon: '✏',  label: 'Edited' },
  system:   { color: '#6b7280', icon: '⚙',  label: 'System' },
}

export function TypeIcon({ kind }) {
  const m = MSG_META[kind] || MSG_META.system
  return <span style={{ color: m.color }}>{m.icon}</span>
}

export function Spinner() {
  return <div className="w-5 h-5 border-2 border-gray-700 border-t-brand rounded-full animate-spin" />
}

export function copy(text, label, toast) {
  navigator.clipboard.writeText(String(text)).then(() => toast(`✔ ${label} copied`))
}
