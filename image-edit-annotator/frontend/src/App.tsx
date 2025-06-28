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
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="mx-auto px-4 py-8 max-w-[100rem]">
        {/* Header */}
        <header className="text-center mb-6">
          <h1 className="text-4xl md:text-5xl font-semibold text-gray-900 dark:text-white mb-4 tracking-tight">
            Image Edit Annotator
          </h1>
          <p className="text-lg text-gray-600 dark:text-gray-300">
            Create high-quality image edit datasets with precision and ease
          </p>
        </header>

        {/* API Status Card */}
        <div className="mb-8 max-w-md mx-auto">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center space-x-3">
              <div className={`w-3 h-3 rounded-full ${apiStatus.includes('✅') ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
              <div>
                <p className="text-sm font-medium text-gray-900 dark:text-gray-100">API Status</p>
                <p className="text-sm text-gray-600 dark:text-gray-400">{apiStatus}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <main className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/projects/create" element={<ProjectForm />} />
            <Route path="/projects/:projectId" element={<ProjectPage />} />
            <Route path="/projects/:projectId/annotate" element={<AnnotationPage />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

import { useNavigate, useParams } from 'react-router-dom'
import { createProject, getProject, getImages, generateTasks, getTasks, updateTask, type Project, type Image, type TaskGenerationResponse, type Task } from './api'
import { FileUpload } from './components/FileUpload'
import { AnnotationWizard } from './components/AnnotationWizard'
import { TaskStatistics } from './components/TaskStatistics'

function Home() {
  return (
    <div className="p-12 text-center space-y-8">
      <div className="max-w-2xl mx-auto">
        <h2 className="text-3xl font-light text-gray-900 dark:text-white mb-4">
          Welcome to your workspace
        </h2>
        <p className="text-lg text-gray-600 dark:text-gray-300 leading-relaxed">
          Start by creating a new project to organize your image annotations,
          or continue working on an existing project.
        </p>
      </div>

      <div className="pt-8">
        <Link
          to="/projects/create"
          className="group inline-flex items-center px-8 py-4 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors duration-200"
        >
          <svg className="w-5 h-5 mr-3 group-hover:animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
          </svg>
          Create New Project
        </Link>
      </div>
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
    <div className="p-12 max-w-lg mx-auto">
      <div className="text-center mb-8">
        <h2 className="text-3xl font-light text-gray-900 dark:text-white mb-4">
          Create New Project
        </h2>
        <p className="text-gray-600 dark:text-gray-300">
          Set up your annotation workspace
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="space-y-2">
          <label htmlFor="projectName" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            Project Name
          </label>
          <input
            type="text"
            id="projectName"
            className="block w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors duration-200"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="My Dataset Project"
            required
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="projectVersion" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            Version
          </label>
          <input
            type="text"
            id="projectVersion"
            className="block w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors duration-200"
            value={version}
            onChange={(e) => setVersion(e.target.value)}
            placeholder="1.0.0"
            required
          />
        </div>

        <div className="pt-4">
          <button
            type="submit"
            className="w-full flex justify-center items-center py-4 px-6 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            Create Project
          </button>
        </div>
      </form>
    </div>
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
      return (
        <div className="p-12 text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-100 dark:bg-blue-900/30 rounded-full mb-4">
            <svg className="w-8 h-8 text-blue-600 dark:text-blue-400 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </div>
          <h3 className="text-xl font-light text-gray-900 dark:text-white mb-2">Loading project</h3>
          <p className="text-gray-600 dark:text-gray-400">Please wait while we fetch your project details...</p>
        </div>
      )
    case 'error':
      return (
        <div className="p-12 text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full mb-4">
            <svg className="w-8 h-8 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3 className="text-xl font-light text-gray-900 dark:text-white mb-2">Something went wrong</h3>
          <p className="text-gray-600 dark:text-gray-400 mb-6">{pageState.message}</p>
          <Link
            to="/"
            className="inline-flex items-center px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors duration-200"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to Home
          </Link>
        </div>
      )
    case 'success':
      const { project } = pageState
      return (
        <div className="p-8 space-y-8">
          {/* Project Header */}
          <div className="border-b border-gray-200 dark:border-gray-700 pb-6">
            <div className="flex items-start justify-between">
              <div>
                <h1 className="text-3xl font-light text-gray-900 dark:text-white mb-2">
                  {project.name}
                </h1>
                <div className="flex items-center space-x-4 text-sm text-gray-600 dark:text-gray-400">
                  <span className="flex items-center">
                    <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                    </svg>
                    Version {project.version}
                  </span>
                  <span className="flex items-center">
                    <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    {project.id.substring(0, 8)}...
                  </span>
                </div>
              </div>
              <Link
                to="/"
                className="flex items-center px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
              >
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
                Back to Home
              </Link>
            </div>
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

          {/* Export Section */}
          {tasks.length > 0 && tasks.filter(t => (t.imageBId?.Valid || t.prompt?.Valid) && !t.skipped).length > 0 && (
            <div>
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold text-white">Export Annotations</h3>
                <div className="text-sm text-gray-400">
                  {tasks.filter(t => (t.imageBId?.Valid || t.prompt?.Valid) && !t.skipped).length} completed annotations
                </div>
              </div>

              <div className="bg-gray-700 rounded-lg p-4 space-y-4">
                <p className="text-gray-300 text-sm">
                  Export your completed annotations in different formats for machine learning training.
                </p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* JSONL Export */}
                  <div className="bg-gray-600 rounded-lg p-4">
                    <h4 className="text-white font-medium mb-2">JSONL Format</h4>
                    <p className="text-gray-300 text-sm mb-3">
                      Standard format with source/target paths and prompts. One JSON object per line.
                    </p>
                    <a
                      href={`http://localhost:8080/projects/${projectId}/export/jsonl`}
                      download
                      className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm"
                    >
                      <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      Download JSONL
                    </a>
                  </div>

                  {/* AI-Toolkit Export */}
                  <div className="bg-gray-600 rounded-lg p-4">
                    <h4 className="text-white font-medium mb-2">AI-Toolkit Format</h4>
                    <p className="text-gray-300 text-sm mb-3">
                      ZIP archive with source/target folders and caption text files in both directories.
                    </p>
                    <a
                      href={`http://localhost:8080/projects/${projectId}/export/ai-toolkit`}
                      download
                      className="inline-flex items-center px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 text-sm"
                    >
                      <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z" />
                      </svg>
                      Download ZIP
                    </a>
                  </div>
                </div>

                <div className="bg-gray-800 rounded p-3">
                  <h5 className="text-white text-sm font-medium mb-2">Export Details:</h5>
                  <ul className="text-gray-400 text-xs space-y-1">
                    <li>• Only completed annotations are exported (not skipped tasks)</li>
                    <li>• JSONL: Each line contains {`{"a": "source_path", "b": "target_path", "prompt": "caption"}`}</li>
                    <li>• AI-Toolkit: Creates source/ and target/ folders with matching filenames + .txt captions in both folders</li>
                  </ul>
                </div>
              </div>
            </div>
          )}

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
                        className={`flex items-center justify-between p-3 border-b border-gray-600 last:border-b-0 ${isCompleted ? 'bg-green-900/20' :
                          isSkipped ? 'bg-yellow-900/20' :
                            'bg-gray-800/50'
                          }`}
                      >
                        <div className="flex items-center space-x-3">
                          <div className="text-sm font-mono text-gray-400">
                            #{index + 1}
                          </div>
                          <div className={`w-3 h-3 rounded-full ${isCompleted ? 'bg-green-500' :
                            isSkipped ? 'bg-yellow-500' :
                              'bg-gray-500'
                            }`} />
                          <div className="text-sm text-white">
                            Task {task.id.substring(0, 8)}...
                          </div>
                        </div>

                        <div className="flex items-center space-x-2">
                          <div className={`px-2 py-1 rounded text-xs font-medium ${isCompleted ? 'bg-green-600 text-white' :
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