import { useState, useEffect } from 'react'
import { ping } from './api'

function App() {
  const [apiStatus, setApiStatus] = useState<string>('checking...')

  useEffect(() => {
    const checkAPI = async () => {
      try {
        const response = await ping()
        setApiStatus(`✅ API Connected: ${response.data.message}`)
      } catch (error) {
        setApiStatus('❌ API Connection Failed')
        console.error('API connection error:', error)
      }
    }
    
    checkAPI()
  }, [])

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <div className="bg-white p-8 rounded-lg shadow-md max-w-md w-full">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">
          Image Edit Annotator
        </h1>
        <p className="text-gray-600 mb-4">
          P1: Project skeleton with CORS handshake
        </p>
        <div className="p-4 bg-gray-50 rounded border">
          <p className="text-sm font-medium text-gray-700">API Status:</p>
          <p className="text-sm text-gray-600">{apiStatus}</p>
        </div>
      </div>
    </div>
  )
}

export default App
