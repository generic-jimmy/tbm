import { createContext, useContext, useState, createElement } from 'react'
import { api } from '../api/client'

const AuthCtx = createContext(null)

// NOTE: deliberately written with createElement() instead of JSX syntax.
// This file must stay .js (not .jsx) — some bundler/lint configs and any
// tooling that inspects extensions before content expects a plain .js file
// here. Using createElement keeps it valid, dependency-free JavaScript
// regardless of extension, so there is no repeat of the JSX-in-.js bug.
export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('tbm_token'))

  async function login(password) {
    const data = await api.login(password)
    localStorage.setItem('tbm_token', data.access_token)
    setToken(data.access_token)
  }

  function logout() {
    localStorage.removeItem('tbm_token')
    setToken(null)
  }

  return createElement(
    AuthCtx.Provider,
    { value: { token, isAuth: !!token, login, logout } },
    children
  )
}

export const useAuth = () => useContext(AuthCtx)
