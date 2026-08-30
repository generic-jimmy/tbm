import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

/**
 * Top-level ErrorBoundary — catches any render error in the tree and shows a
 * recovery screen instead of a permanent white screen with no way out.
 * This is a class component because error boundaries must be class-based in React.
 */
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, info) {
    console.error('[TBM] Render error:', error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
          <div className="max-w-md w-full bg-[#111b2e] border border-red-800/40 rounded-2xl p-6 text-center">
            <div className="text-5xl mb-4">⚠️</div>
            <h2 className="text-lg font-semibold text-gray-100 mb-2">Something went wrong</h2>
            <p className="text-sm text-gray-500 mb-5 font-mono break-all leading-relaxed">
              {this.state.error?.message || 'Unexpected render error'}
            </p>
            <button
              onClick={() => { this.setState({ hasError: false }); window.location.reload() }}
              className="px-5 py-2 bg-[#2AABEE] hover:bg-[#1e9ed6] text-gray-950 font-semibold rounded-lg text-sm transition"
            >
              Reload App
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>
)
