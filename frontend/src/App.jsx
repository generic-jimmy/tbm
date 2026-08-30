import { useState, useEffect, useCallback } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom'
import { AuthProvider, useAuth } from './store/auth'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Monitor from './pages/Monitor'
import Compose from './pages/Compose'
import Files from './pages/Files'
import Bots from './pages/Bots'
import { api } from './api/client'
import { Spinner } from './components/ui'

function Protected() {
  const { isAuth }        = useAuth()
  const navigate          = useNavigate()
  const location          = useLocation()
  const [bots,  setBots]  = useState([])
  const [toast, setToast] = useState('')
  const [ready, setReady] = useState(false)

  function showToast(msg) {
    setToast(msg)
    setTimeout(() => setToast(''), 2500)
  }

  async function loadBots() {
    try { setBots(await api.bots()) } catch {}
  }

  useEffect(() => {
    if (!isAuth) return
    loadBots().finally(() => setReady(true))
    const iv = setInterval(loadBots, 10000)
    return () => clearInterval(iv)
  }, [isAuth])

  if (!isAuth) return <Navigate to="/login" state={{ from: location }} replace />
  if (!ready)  return (
    <div className="h-screen flex items-center justify-center bg-gray-950">
      <Spinner />
    </div>
  )

  const shared = { bots, onRefresh: loadBots, toast: showToast, navigate }

  return (
    <Layout toast={toast}>
      <Routes>
        <Route path="/"        element={<Dashboard {...shared} />} />
        <Route path="/monitor" element={<Monitor   {...shared} />} />
        <Route path="/compose" element={<Compose   {...shared} />} />
        <Route path="/files"   element={<Files     {...shared} />} />
        <Route path="/bots"    element={<Bots      {...shared} />} />
        <Route path="*"        element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/*"     element={<Protected />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
