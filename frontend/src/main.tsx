import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { ErrorBoundary } from './components/ErrorBoundary'
import './styles/globals.css'  // Make sure global styles are imported

// Enable better error logging
const enableDebugMode = () => {
  window.onerror = (message, source, lineno, colno, error) => {
    console.error('Global error:', { message, source, lineno, colno, error })
    return false
  }

  window.onunhandledrejection = (event) => {
    console.error('Unhandled promise rejection:', event.reason)
  }
}

enableDebugMode()
console.log('Main.tsx is executing')

const rootElement = document.getElementById('root')
console.log('Root element:', rootElement)

if (!rootElement) {
  throw new Error('Failed to find the root element')
}

const root = ReactDOM.createRoot(rootElement)
console.log('Created React root')

try {
  root.render(
    <React.StrictMode>
      <ErrorBoundary fallback={<div>Something went wrong. Check console for details.</div>}>
        <App />
      </ErrorBoundary>
    </React.StrictMode>
  )
  console.log('Rendered app successfully')
} catch (error) {
  console.error('Error rendering app:', error)
  // Render a basic error message if the app fails to mount
  rootElement.innerHTML = `
    <div style="padding: 20px; text-align: center;">
      <h1>Error Loading Application</h1>
      <p>Please check the console for details.</p>
    </div>
  `
} 