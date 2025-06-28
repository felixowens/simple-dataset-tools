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
    <body className="min-h-screen bg-gradient-to-br from-gray-800 to-gray-900 flex items-center justify-center p-4">
      <div className="bg-gray-700 p-8 rounded-xl shadow-2xl max-w-7xl w-full text-white">
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
          <Route path="/projects/:projectId/annotate" element={<AnnotationPage />} />
        </Routes>
      </div>
    </body>
  )
}

import { useNavigate, useParams } from 'react-router-dom'
import { createProject, getProject, getImages, generateTasks, getTasks, updateTask, type Project, type Image, type TaskGenerationResponse, type Task } from './api'
import { FileUpload } from './components/FileUpload'
import { AnnotationWizard } from './components/AnnotationWizard'
import { TaskStatistics } from './components/TaskStatistics'

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
  const [images, setImages] = useState<Image[]>([])
  const [imagesLoading, setImagesLoading] = useState(false)
  const [tasks, setTasks] = useState<Task[]>([])
  const [tasksLoading, setTasksLoading] = useState(false)
  const [taskGeneration, setTaskGeneration] = useState<{ loading: boolean; result?: TaskGenerationResponse }>({ loading: false })

  const fetchImages = async () => {
    if (!projectId) return
    setImagesLoading(true)
    try {
      const response = await getImages(projectId)
      setImages(response.data)
    } catch (err) {
      console.error('Error fetching images:', err)
    } finally {
      setImagesLoading(false)
    }
  }

  const fetchTasks = async () => {
    if (!projectId) return
    setTasksLoading(true)
    try {
      const response = await getTasks(projectId)
      setTasks(response.data)
    } catch (err) {
      console.error('Error fetching tasks:', err)
    } finally {
      setTasksLoading(false)
    }
  }

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

  useEffect(() => {
    if (pageState.status === 'success') {
      fetchImages()
      fetchTasks()
    }
  }, [pageState.status, projectId])

  const handleUploadComplete = () => {
    fetchImages()
  }

  const handleGenerateTasks = async () => {
    if (!projectId) return
    setTaskGeneration({ loading: true })
    try {
      const response = await generateTasks(projectId)
      setTaskGeneration({ loading: false, result: response.data })
      // Refresh tasks after generation
      fetchTasks()
    } catch (err) {
      console.error('Error generating tasks:', err)
      setTaskGeneration({ loading: false })
    }
  }

  const handleRequeueSkipped = async () => {
    if (!projectId) return
    setTasksLoading(true)
    try {
      // Get all skipped tasks and update them to not be skipped
      const skippedTasks = tasks.filter(t => t.skipped)
      await Promise.all(
        skippedTasks.map(task => 
          updateTask(task.id, { skipped: false })
        )
      )
      // Refresh tasks after re-queuing
      fetchTasks()
      alert(`Re-queued ${skippedTasks.length} skipped tasks`)
    } catch (err) {
      console.error('Error re-queuing skipped tasks:', err)
      alert('Failed to re-queue skipped tasks')
    } finally {
      setTasksLoading(false)
    }
  }

  switch (pageState.status) {
    case 'loading':
      return <p className="text-white">Loading project...</p>
    case 'error':
      return <p className="text-red-400">{pageState.message}</p>
    case 'success':
      const { project } = pageState
      return (
        <div className="space-y-6">
          <div>
            <h2 className="text-2xl font-bold text-white">Project: {project.name}</h2>
            <p className="text-gray-300">Version: {project.version}</p>
            <p className="text-gray-400 text-sm">ID: {project.id}</p>
          </div>

          <div>
            <h3 className="text-lg font-semibold text-white mb-4">Upload Images</h3>
            <FileUpload
              projectId={project.id}
              onUploadComplete={handleUploadComplete}
            />
          </div>

          <div>
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-white">Images ({images.length})</h3>
              <button
                onClick={fetchImages}
                disabled={imagesLoading}
                className="px-3 py-1 text-sm bg-gray-600 text-white rounded hover:bg-gray-500 disabled:opacity-50"
              >
                {imagesLoading ? 'Loading...' : 'Refresh'}
              </button>
            </div>

            {images.length === 0 ? (
              <div className="text-center py-8 text-gray-400">
                <p>No images uploaded yet.</p>
                <p className="text-sm">Upload some images to get started.</p>
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                {images.map((image) => (
                  <div key={image.id} className="bg-gray-700 rounded-lg p-3">
                    <div className="aspect-square bg-gray-600 rounded mb-2 flex items-center justify-center">
                      <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                    </div>
                    <p className="text-xs text-gray-300 truncate" title={image.path}>
                      {image.path.split('/').pop()}
                    </p>
                    <p className="text-xs text-gray-500 font-mono">
                      {image.pHash.substring(0, 8)}...
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Task Statistics */}
          {tasks.length > 0 && (
            <TaskStatistics tasks={tasks} />
          )}

          <div>
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-white">Task Generation</h3>
              {tasks.length > 0 && (
                <div className="flex space-x-2">
                  <Link
                    to={`/projects/${projectId}/annotate`}
                    className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                  >
                    {(() => {
                      const pendingTasks = tasks.filter(t => !(t.imageBId?.Valid || t.prompt?.Valid) && !t.skipped).length
                      const completedTasks = tasks.filter(t => (t.imageBId?.Valid || t.prompt?.Valid) && !t.skipped).length
                      if (pendingTasks === 0 && completedTasks > 0) {
                        return 'Review Annotations'
                      } else if (completedTasks > 0) {
                        return 'Resume Annotating'
                      } else {
                        return 'Start Annotating'
                      }
                    })()}
                  </Link>
                  
                  {/* Re-queue Skipped Button */}
                  {tasks.filter(t => t.skipped).length > 0 && (
                    <button
                      onClick={handleRequeueSkipped}
                      disabled={tasksLoading}
                      className="px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700 disabled:opacity-50"
                    >
                      Re-queue Skipped ({tasks.filter(t => t.skipped).length})
                    </button>
                  )}
                </div>
              )}
            </div>

            <div className="bg-gray-700 rounded-lg p-4 space-y-4">
              <p className="text-gray-300 text-sm">
                Generate annotation tasks by finding similar images for each uploaded image.
              </p>

              <button
                onClick={handleGenerateTasks}
                disabled={taskGeneration.loading || images.length === 0}
                className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {taskGeneration.loading ? 'Generating Tasks...' : 'Generate Tasks'}
              </button>

              {taskGeneration.result && (
                <div className="mt-4 p-3 bg-green-900/30 border border-green-600/30 rounded">
                  <h4 className="text-green-400 font-medium mb-2">Tasks Generated Successfully!</h4>
                  <div className="text-green-300 text-sm space-y-1">
                    <p>Tasks Created: {taskGeneration.result.tasksCreated}</p>
                    <p>Average Candidates per Task: {taskGeneration.result.averageCandidates.toFixed(1)}</p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Task List */}
          {tasks.length > 0 && (
            <div>
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold text-white">Tasks ({tasks.length})</h3>
                <button
                  onClick={fetchTasks}
                  disabled={tasksLoading}
                  className="px-3 py-1 text-sm bg-gray-600 text-white rounded hover:bg-gray-500 disabled:opacity-50"
                >
                  {tasksLoading ? 'Loading...' : 'Refresh'}
                </button>
              </div>

              <div className="bg-gray-700 rounded-lg overflow-hidden">
                <div className="max-h-64 overflow-y-auto">
                  {tasks.map((task, index) => {
                    const isCompleted = (task.imageBId?.Valid || task.prompt?.Valid) && !task.skipped
                    const isSkipped = task.skipped
                    
                    return (
                      <div
                        key={task.id}
                        className={`flex items-center justify-between p-3 border-b border-gray-600 last:border-b-0 ${
                          isCompleted ? 'bg-green-900/20' : 
                          isSkipped ? 'bg-yellow-900/20' : 
                          'bg-gray-800/50'
                        }`}
                      >
                        <div className="flex items-center space-x-3">
                          <div className="text-sm font-mono text-gray-400">
                            #{index + 1}
                          </div>
                          <div className={`w-3 h-3 rounded-full ${
                            isCompleted ? 'bg-green-500' :
                            isSkipped ? 'bg-yellow-500' :
                            'bg-gray-500'
                          }`} />
                          <div className="text-sm text-white">
                            Task {task.id.substring(0, 8)}...
                          </div>
                        </div>
                        
                        <div className="flex items-center space-x-2">
                          <div className={`px-2 py-1 rounded text-xs font-medium ${
                            isCompleted ? 'bg-green-600 text-white' :
                            isSkipped ? 'bg-yellow-600 text-white' :
                            'bg-gray-600 text-gray-300'
                          }`}>
                            {isCompleted ? 'Completed' : isSkipped ? 'Skipped' : 'Pending'}
                          </div>
                          
                          {task.candidateBIds && task.candidateBIds.length > 0 && (
                            <div className="text-xs text-gray-400">
                              {task.candidateBIds.length} candidates
                            </div>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      )
    default:
      return null
  }
}

function AnnotationPage() {
  const { projectId } = useParams<{ projectId: string }>()
  
  if (!projectId) {
    return (
      <div className="text-center py-8">
        <p className="text-red-400">Project ID is missing</p>
      </div>
    )
  }

  return <AnnotationWizard projectId={projectId} />
}

export default App