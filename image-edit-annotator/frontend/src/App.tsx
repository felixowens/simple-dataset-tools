import { useState, useEffect } from 'react'
import { Routes, Route, Link } from 'react-router-dom'
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
          <Route path="/" element={<Home />} />
          <Route path="/projects/create" element={<ProjectForm />} />
          <Route path="/projects/:projectId" element={<ProjectPage />} />
        </Routes>
      </div>
    </div>
  )
}

import { useNavigate, useParams } from 'react-router-dom'
import { createProject, getProject, type Project } from './api'

function Home() {
  return (
    <div className="space-y-4 text-center">
      <h2 className="text-2xl font-bold text-white">Welcome</h2>
      <p className="text-gray-300">Start by creating a new project or opening an existing one.</p>
      <Link
        to="/projects/create"
        className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
      >
        Create New Project
      </Link>
    </div>
  )
}

function ProjectForm() {
  const [name, setName] = useState('')
  const [version, setVersion] = useState('')
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const response = await createProject({ name, version })
      navigate(`/projects/${response.data.id}`)
    } catch (error) {
      console.error('Error creating project:', error)
      alert('Failed to create project.')
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6 p-6 bg-gray-800 rounded-xl shadow-2xl">
      <h2 className="text-2xl font-bold text-white text-center mb-6">Create New Project</h2>
      <div>
        <label htmlFor="projectName" className="block text-sm font-medium text-gray-300 mb-2">
          Project Name
        </label>
        <input
          type="text"
          id="projectName"
          className="block w-full rounded-md bg-gray-700 border border-gray-600 text-white placeholder-gray-500 focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-3"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="My Awesome Project"
          required
        />
      </div>
      <div>
        <label htmlFor="projectVersion" className="block text-sm font-medium text-gray-300 mb-2">
          Version
        </label>
        <input
          type="text"
          id="projectVersion"
          className="block w-full rounded-md bg-gray-700 border border-gray-600 text-white placeholder-gray-500 focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-3"
          value={version}
          onChange={(e) => setVersion(e.target.value)}
          placeholder="1.0.0"
          required
        />
      </div>
      <button
        type="submit"
        className="w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-base font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition duration-150 ease-in-out"
      >
        Create Project
      </button>
    </form>
  )
}

type ProjectPageState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'success'; project: Project }

function ProjectPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const [pageState, setPageState] = useState<ProjectPageState>({ status: 'loading' })

  useEffect(() => {
    const fetchProject = async () => {
      if (!projectId) {
        setPageState({ status: 'error', message: 'Project ID is missing.' })
        return
      }
      try {
        const response = await getProject(projectId)
        setPageState({ status: 'success', project: response.data })
      } catch (err) {
        console.error('Error fetching project:', err)
        setPageState({ status: 'error', message: 'Failed to load project.' })
      }
    }

    fetchProject()
  }, [projectId])

  switch (pageState.status) {
    case 'loading':
      return <p className="text-white">Loading project...</p>
    case 'error':
      return <p className="text-red-400">{pageState.message}</p>
    case 'success':
      const { project } = pageState
      return (
        <div className="space-y-4">
          <h2 className="text-2xl font-bold text-white">Project: {project.name}</h2>
          <p className="text-gray-300">Version: {project.version}</p>
          <p className="text-gray-300">ID: {project.id}</p>
          {/* More project details and annotation UI will go here */}
        </div>
      )
    default:
      return null
  }
}

export default App