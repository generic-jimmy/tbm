import { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../store/auth'
import { LayoutDashboard, Radio, Send, FolderOpen, Bot, LogOut, Menu, X } from 'lucide-react'

const NAV = [
  { to: '/',        icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/monitor', icon: Radio,            label: 'Live Monitor' },
  { to: '/compose', icon: Send,             label: 'Compose' },
  { to: '/files',   icon: FolderOpen,       label: 'File Manager' },
  { to: '/bots',    icon: Bot,              label: 'Bot Manager' },
]

export default function Layout({ children, toast }) {
  const { logout } = useAuth()
  const navigate   = useNavigate()
  const [open, setOpen] = useState(false)

  function doLogout() { logout(); navigate('/login') }

  return (
    <div className="flex h-screen bg-gray-950 overflow-hidden">
      {/* Sidebar */}
      <aside className={`
        fixed inset-y-0 left-0 z-40 flex flex-col bg-[#0d1425] border-r border-gray-800
        transition-transform duration-200
        ${open ? 'translate-x-0' : '-translate-x-full'}
        md:relative md:translate-x-0 w-52 flex-shrink-0
      `}>
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 py-5 border-b border-gray-800">
          <div className="w-8 h-8 bg-brand rounded-full flex items-center justify-center text-gray-950 font-bold text-sm">✈</div>
          <span className="font-semibold text-gray-100 text-sm">BotManager Pro</span>
          <button className="ml-auto md:hidden text-gray-500" onClick={() => setOpen(false)}><X size={16} /></button>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-2 py-4 space-y-0.5 overflow-y-auto">
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink key={to} to={to} end={to === '/'} onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all
                ${isActive
                  ? 'bg-[#1c2a45] text-brand font-medium'
                  : 'text-gray-400 hover:bg-[#172035] hover:text-gray-200'}`
              }>
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-2 py-3 border-t border-gray-800">
          <button onClick={doLogout}
            className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm text-gray-500
              hover:bg-red-900/20 hover:text-red-400 transition-all">
            <LogOut size={16} />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Mobile overlay */}
      {open && <div className="fixed inset-0 z-30 bg-black/50 md:hidden" onClick={() => setOpen(false)} />}

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar (mobile) */}
        <div className="md:hidden flex items-center gap-3 px-4 py-3 border-b border-gray-800 bg-[#0d1425]">
          <button onClick={() => setOpen(true)} className="text-gray-400"><Menu size={20} /></button>
          <span className="font-semibold text-gray-100 text-sm">BotManager Pro</span>
        </div>

        <main className="flex-1 overflow-auto">{children}</main>
      </div>

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50
          bg-[#1c2a45] border border-brand/30 text-brand text-sm px-4 py-2 rounded-lg shadow-xl">
          {toast}
        </div>
      )}
    </div>
  )
}
