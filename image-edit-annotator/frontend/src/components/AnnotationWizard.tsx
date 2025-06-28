import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getTasks, getImages, updateTask, type Task, type Image } from '../api'
import { TaskStatistics } from './TaskStatistics'

interface AnnotationWizardProps {
  projectId: string
}

export function AnnotationWizard({ projectId }: AnnotationWizardProps) {
  const navigate = useNavigate()
  const [tasks, setTasks] = useState<Task[]>([])
  const [images, setImages] = useState<Image[]>([])
  const [currentTaskIndex, setCurrentTaskIndex] = useState(0)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [prompt, setPrompt] = useState('')
  const [selectedImageBId, setSelectedImageBId] = useState<string>('')

  const currentTask = tasks[currentTaskIndex]
  const totalTasks = tasks.length

  useEffect(() => {
    loadData()
  }, [projectId])

  useEffect(() => {
    if (currentTask) {
      setPrompt(currentTask.prompt?.String || '')
      setSelectedImageBId(currentTask.imageBId?.String || '')
    }
  }, [currentTask])

  const loadData = async () => {
    setLoading(true)
    try {
      const [tasksResponse, imagesResponse] = await Promise.all([
        getTasks(projectId),
        getImages(projectId)
      ])
      setTasks(tasksResponse.data)
      setImages(imagesResponse.data)

      // Find first incomplete task (resume functionality)
      const firstIncomplete = tasksResponse.data.findIndex(t =>
        !(t.imageBId?.Valid || t.prompt?.Valid) && !t.skipped
      )
      if (firstIncomplete >= 0) {
        setCurrentTaskIndex(firstIncomplete)
      } else {
        // If no incomplete tasks, start from beginning for review
        setCurrentTaskIndex(0)
      }
    } catch (error) {
      console.error('Error loading data:', error)
    } finally {
      setLoading(false)
    }
  }

  const getImageById = (id: string): Image | undefined => {
    return images.find(img => img.id === id)
  }

  const getImageUrl = (imagePath: string) => {
    return `http://localhost:8080/projects/${projectId}/${imagePath}`
  }

  const handleSave = async () => {
    if (!currentTask || (!selectedImageBId && !prompt.trim())) return

    setSaving(true)
    try {
      await updateTask(currentTask.id, {
        imageBId: selectedImageBId ? { String: selectedImageBId, Valid: true } : null,
        prompt: prompt.trim() ? { String: prompt.trim(), Valid: true } : null,
        skipped: false
      })

      // Update local task state
      const updatedTasks = [...tasks]
      updatedTasks[currentTaskIndex] = {
        ...currentTask,
        imageBId: { String: selectedImageBId, Valid: !!selectedImageBId },
        prompt: { String: prompt.trim(), Valid: !!prompt.trim() }
      }
      setTasks(updatedTasks)

      // Move to next task
      goToNextTask()
    } catch (error) {
      console.error('Error saving task:', error)
      alert('Failed to save annotation')
    } finally {
      setSaving(false)
    }
  }

  const handleSkip = async () => {
    if (!currentTask) return

    setSaving(true)
    try {
      await updateTask(currentTask.id, {
        skipped: true
      })

      // Update local task state
      const updatedTasks = [...tasks]
      updatedTasks[currentTaskIndex] = {
        ...currentTask,
        skipped: true
      }
      setTasks(updatedTasks)

      goToNextTask()
    } catch (error) {
      console.error('Error skipping task:', error)
      alert('Failed to skip task')
    } finally {
      setSaving(false)
    }
  }

  const goToNextTask = () => {
    const nextIncompleteIndex = tasks.findIndex((t, idx) =>
      idx > currentTaskIndex && !(t.imageBId?.Valid || t.prompt?.Valid) && !t.skipped
    )

    if (nextIncompleteIndex >= 0) {
      setCurrentTaskIndex(nextIncompleteIndex)
    } else {
      // All tasks completed
      navigate(`/projects/${projectId}`)
    }
  }

  const goToPreviousTask = () => {
    if (currentTaskIndex > 0) {
      setCurrentTaskIndex(currentTaskIndex - 1)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <div className="text-white">Loading annotation tasks...</div>
      </div>
    )
  }

  if (tasks.length === 0) {
    return (
      <div className="text-center py-8">
        <h3 className="text-xl font-semibold text-white mb-4">No Tasks Available</h3>
        <p className="text-gray-300 mb-4">Generate tasks first to start annotating.</p>
        <button
          onClick={() => navigate(`/projects/${projectId}`)}
          className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
        >
          Back to Project
        </button>
      </div>
    )
  }

  if (!currentTask) {
    return (
      <div className="text-center py-8">
        <h3 className="text-xl font-semibold text-white mb-4">All Tasks Completed!</h3>
        <p className="text-gray-300 mb-4">You have finished annotating all available tasks.</p>
        <button
          onClick={() => navigate(`/projects/${projectId}`)}
          className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
        >
          Back to Project
        </button>
      </div>
    )
  }

  const imageA = getImageById(currentTask.imageAId)
  const candidateImages = currentTask.candidateBIds
    ?.map(id => getImageById(id))
    .filter(Boolean) as Image[] || []

  return (
    <div className="flex gap-6">
      {/* Sidebar - Task Navigation */}
      <div className="w-80 space-y-4">
        {/* Task Statistics */}
        <TaskStatistics tasks={tasks} />
        
        {/* Current Task Info */}
        <div className="bg-gray-700 rounded-lg p-4">
          <div className="flex justify-between items-center mb-2">
            <h3 className="text-lg font-bold text-white">Current Task</h3>
            <div className="text-gray-300">
              {currentTaskIndex + 1} of {totalTasks}
            </div>
          </div>
          {currentTask && (
            <div className="space-y-2 text-sm">
              <div className="text-gray-300">
                Task ID: <span className="font-mono text-gray-400">{currentTask.id.substring(0, 12)}...</span>
              </div>
              <div className="text-gray-300">
                Candidates: <span className="text-gray-400">{candidateImages.length}</span>
              </div>
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div className="bg-gray-700 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-white mb-3">Quick Actions</h3>
          <div className="space-y-2">
            <button
              onClick={() => {
                const nextIncomplete = tasks.findIndex((t, idx) => 
                  idx > currentTaskIndex && !(t.imageBId?.Valid || t.prompt?.Valid) && !t.skipped
                )
                if (nextIncomplete >= 0) {
                  setCurrentTaskIndex(nextIncomplete)
                } else {
                  // Wrap around to first incomplete
                  const firstIncomplete = tasks.findIndex(t =>
                    !(t.imageBId?.Valid || t.prompt?.Valid) && !t.skipped
                  )
                  if (firstIncomplete >= 0) {
                    setCurrentTaskIndex(firstIncomplete)
                  }
                }
              }}
              className="w-full px-3 py-2 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-700"
            >
              Jump to Next Incomplete
            </button>
            
            <button
              onClick={() => {
                const firstIncomplete = tasks.findIndex(t =>
                  !(t.imageBId?.Valid || t.prompt?.Valid) && !t.skipped
                )
                if (firstIncomplete >= 0) {
                  setCurrentTaskIndex(firstIncomplete)
                } else {
                  setCurrentTaskIndex(0)
                }
              }}
              className="w-full px-3 py-2 text-sm bg-gray-600 text-white rounded hover:bg-gray-500"
            >
              Jump to First Incomplete
            </button>
          </div>
        </div>

        {/* Task List */}
        <div className="bg-gray-700 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-white mb-3">All Tasks</h3>
          <div className="space-y-1 max-h-64 overflow-y-auto">
            {tasks.map((task, index) => {
              const isCompleted = (task.imageBId?.Valid || task.prompt?.Valid) && !task.skipped
              const isSkipped = task.skipped
              const isCurrent = index === currentTaskIndex
              
              return (
                <div
                  key={task.id}
                  className={`flex items-center justify-between p-2 rounded cursor-pointer transition-all ${
                    isCurrent ? 'bg-indigo-600' :
                    isCompleted ? 'bg-green-800/50 hover:bg-green-700/50' :
                    isSkipped ? 'bg-yellow-800/50 hover:bg-yellow-700/50' :
                    'bg-gray-600/50 hover:bg-gray-600'
                  }`}
                  onClick={() => setCurrentTaskIndex(index)}
                >
                  <div className="flex items-center space-x-2">
                    <div className="text-sm font-mono text-gray-300">
                      #{index + 1}
                    </div>
                    <div className={`w-2 h-2 rounded-full ${
                      isCompleted ? 'bg-green-400' :
                      isSkipped ? 'bg-yellow-400' :
                      'bg-gray-400'
                    }`} />
                  </div>
                  
                  <div className={`text-xs px-2 py-1 rounded ${
                    isCompleted ? 'bg-green-600 text-white' :
                    isSkipped ? 'bg-yellow-600 text-black' :
                    'bg-gray-500 text-gray-300'
                  }`}>
                    {isCompleted ? 'Done' : isSkipped ? 'Skip' : 'Todo'}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 space-y-6">
        {/* Header */}
        <div className="bg-gray-700 rounded-lg p-4">
          <h2 className="text-xl font-bold text-white">Annotation Wizard</h2>
        </div>

      {/* Navigation */}
      <div className="flex justify-between">
        <button
          onClick={goToPreviousTask}
          disabled={currentTaskIndex === 0}
          className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Previous
        </button>
        <button
          onClick={() => navigate(`/projects/${projectId}`)}
          className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-500"
        >
          Back to Project
        </button>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Source Image (A) - Full Column */}
        <div className="bg-gray-700 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-white mb-4">Source Image (A)</h3>
          {imageA ? (
            <div className="space-y-2">
              <img
                src={getImageUrl(imageA.path)}
                alt="Source image"
                className="w-full h-80 object-contain bg-gray-800 rounded"
              />
              <p className="text-xs text-gray-400 text-center">{imageA.path.split('/').pop()}</p>
            </div>
          ) : (
            <div className="w-full h-80 bg-gray-600 rounded flex items-center justify-center">
              <span className="text-gray-400">Image not found</span>
            </div>
          )}
        </div>

        {/* Selected Target Image (B) - Large Preview */}
        <div className="bg-gray-700 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-white mb-4">Selected Target Image (B)</h3>
          {selectedImageBId ? (
            <div className="space-y-2">
              <img
                src={getImageUrl(getImageById(selectedImageBId)?.path || '')}
                alt="Selected target image"
                className="w-full h-80 object-contain bg-gray-800 rounded"
              />
              <p className="text-xs text-gray-400 text-center">
                {getImageById(selectedImageBId)?.path.split('/').pop()}
              </p>
              <button
                onClick={() => setSelectedImageBId('')}
                className="w-full px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700"
              >
                Clear Selection
              </button>
            </div>
          ) : (
            <div className="w-full h-80 bg-gray-600 rounded flex items-center justify-center">
              <span className="text-gray-400">No image selected</span>
            </div>
          )}
        </div>

        {/* Candidate Images Selection */}
        <div className="bg-gray-700 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-white mb-4">
            {candidateImages.length > 0 ? 'Candidate Images' : 'All Project Images'}
          </h3>
          
          {candidateImages.length > 0 ? (
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {candidateImages.map((image) => (
                <div
                  key={image.id}
                  className={`cursor-pointer border-2 rounded-lg p-2 transition-all ${selectedImageBId === image.id
                      ? 'border-indigo-500 bg-indigo-900/30'
                      : 'border-gray-500 hover:border-gray-400'
                    }`}
                  onClick={() => setSelectedImageBId(image.id)}
                >
                  <div className="flex items-center space-x-3">
                    <img
                      src={getImageUrl(image.path)}
                      alt="Candidate image"
                      className="w-20 h-20 object-contain bg-gray-800 rounded"
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-white truncate">{image.path.split('/').pop()}</p>
                      <p className="text-xs text-gray-400 font-mono">{image.pHash.substring(0, 12)}...</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {images.filter(img => img.id !== currentTask.imageAId).map((image) => (
                <div
                  key={image.id}
                  className={`cursor-pointer border-2 rounded-lg p-2 transition-all ${selectedImageBId === image.id
                      ? 'border-indigo-500 bg-indigo-900/30'
                      : 'border-gray-500 hover:border-gray-400'
                    }`}
                  onClick={() => setSelectedImageBId(image.id)}
                >
                  <div className="flex items-center space-x-3">
                    <img
                      src={getImageUrl(image.path)}
                      alt="Project image"
                      className="w-20 h-20 object-contain bg-gray-800 rounded"
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-white truncate">{image.path.split('/').pop()}</p>
                      <p className="text-xs text-gray-400 font-mono">{image.pHash.substring(0, 12)}...</p>
                    </div>
                  </div>
                </div>
              ))}
              {images.filter(img => img.id !== currentTask.imageAId).length === 0 && (
                <div className="text-center py-8 text-gray-400">
                  <p>No other images available</p>
                  <p className="text-sm">Upload more images to select from</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Prompt Input */}
      <div className="bg-gray-700 rounded-lg p-4">
        <h3 className="text-lg font-semibold text-white mb-4">Edit Description</h3>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe what changes were made from image A to image B..."
          className="w-full h-24 p-3 bg-gray-800 border border-gray-600 rounded text-white placeholder-gray-400 resize-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          autoFocus
        />
      </div>

      {/* Action Buttons */}
      <div className="flex justify-end space-x-3">
        <button
          onClick={handleSkip}
          disabled={saving}
          className="px-6 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700 disabled:opacity-50"
        >
          Skip Task
        </button>
        <button
          onClick={handleSave}
          disabled={saving || (!selectedImageBId && !prompt.trim())}
          className="px-6 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save & Next'}
        </button>
      </div>
      </div>
    </div>
  )
}