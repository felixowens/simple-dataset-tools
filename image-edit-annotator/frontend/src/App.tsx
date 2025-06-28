import { useState, useEffect } from 'react'
import { Routes, Route } from 'react-router-dom'
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
    <div className="min-h-screen bg-gradient-to-br from-gray-800 to-gray-900 flex items-center justify-center p-4">
      <div className="bg-gray-700 p-8 rounded-xl shadow-2xl max-w-xl w-full text-white">
        <h1 className="text-3xl font-extrabold text-white mb-6 text-center">
          Image Edit Annotator
        </h1>
        <div className="p-4 bg-gray-800 rounded-lg border border-gray-600 mb-6">
          <p className="text-sm font-medium text-gray-300">API Status:</p>
          <p className="text-sm text-gray-400">{apiStatus}</p>
        </div>
        <Routes>
          <Route path="/projects/create" element={<ProjectForm />} />
          <Route path="/projects/:projectId" element={<ProjectPage />} />
        </Routes>
      </div>
    </div>
  )
}

export default App