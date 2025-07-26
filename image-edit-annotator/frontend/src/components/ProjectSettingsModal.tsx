import { useState, useEffect } from 'react'
import { updateProject, type Project, type CaptionAPIConfig } from '../api'

interface ProjectSettingsModalProps {
  project: Project
  isOpen: boolean
  onClose: () => void
  onProjectUpdated: (updatedProject: Project) => void
}

export function ProjectSettingsModal({ project, isOpen, onClose, onProjectUpdated }: ProjectSettingsModalProps) {
  const [formData, setFormData] = useState({
    name: project.name,
    version: project.version,
    promptButtons: project.promptButtons || [],
    systemPrompt: project.systemPrompt || '',
    captionApiProvider: '',
    captionApiKey: '',
    captionApiModel: ''
  })
  const [newPromptButton, setNewPromptButton] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (project.captionApi) {
      try {
        const apiConfig: CaptionAPIConfig = JSON.parse(project.captionApi)
        setFormData(prev => ({
          ...prev,
          captionApiProvider: apiConfig.provider || '',
          captionApiKey: apiConfig.apiKey || '',
          captionApiModel: apiConfig.model || ''
        }))
      } catch (error) {
        console.error('Failed to parse caption API config:', error)
      }
    }
  }, [project.captionApi])

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const addPromptButton = () => {
    if (newPromptButton.trim() && !formData.promptButtons.includes(newPromptButton.trim())) {
      setFormData(prev => ({
        ...prev,
        promptButtons: [...prev.promptButtons, newPromptButton.trim()]
      }))
      setNewPromptButton('')
    }
  }

  const removePromptButton = (index: number) => {
    setFormData(prev => ({
      ...prev,
      promptButtons: prev.promptButtons.filter((_, i) => i !== index)
    }))
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      // Prepare caption API configuration
      let captionApi = null
      if (formData.captionApiProvider && formData.captionApiKey) {
        const apiConfig: CaptionAPIConfig = {
          provider: formData.captionApiProvider,
          apiKey: formData.captionApiKey,
          model: formData.captionApiModel || undefined
        }
        captionApi = JSON.stringify(apiConfig)
      }

      const updatedProject: Omit<Project, 'id'> = {
        name: formData.name,
        version: formData.version,
        promptButtons: formData.promptButtons,
        parentProjectId: project.parentProjectId,
        projectType: project.projectType,
        captionApi,
        systemPrompt: formData.systemPrompt || null
      }

      const response = await updateProject(project.id, updatedProject)
      onProjectUpdated(response.data)
      onClose()
    } catch (error) {
      console.error('Error updating project:', error)
      alert('Failed to update project')
    } finally {
      setSaving(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6">Project Settings</h2>
        
        <div className="space-y-6">
          {/* Basic Project Info */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">Basic Information</h3>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Project Name
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => handleInputChange('name', e.target.value)}
                className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                placeholder="Enter project name"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Version
              </label>
              <input
                type="text"
                value={formData.version}
                onChange={(e) => handleInputChange('version', e.target.value)}
                className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                placeholder="e.g., 1.0, v2.1"
              />
            </div>
          </div>

          {/* Prompt Buttons */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">Quick Prompt Buttons</h3>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Add New Prompt Button
              </label>
              <div className="flex space-x-2">
                <input
                  type="text"
                  value={newPromptButton}
                  onChange={(e) => setNewPromptButton(e.target.value)}
                  className="flex-1 p-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  placeholder="Enter prompt text"
                  onKeyPress={(e) => e.key === 'Enter' && addPromptButton()}
                />
                <button
                  onClick={addPromptButton}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
                >
                  Add
                </button>
              </div>
            </div>

            {formData.promptButtons.length > 0 && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Current Prompt Buttons
                </label>
                <div className="space-y-2">
                  {formData.promptButtons.map((button, index) => (
                    <div key={index} className="flex items-center justify-between p-2 border border-gray-200 dark:border-gray-600 rounded-lg">
                      <span className="text-gray-900 dark:text-white">{button}</span>
                      <button
                        onClick={() => removePromptButton(index)}
                        className="text-red-600 hover:text-red-800"
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Caption API Configuration (only for caption projects) */}
          {project.projectType === 'caption' && (
            <div className="space-y-4">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">Caption API Configuration</h3>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  System Prompt
                </label>
                <textarea
                  value={formData.systemPrompt}
                  onChange={(e) => handleInputChange('systemPrompt', e.target.value)}
                  className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white min-h-20 resize-y"
                  placeholder="Custom system prompt for AI captioning (e.g., 'Describe this image in detail for training a diffusion model')"
                  rows={3}
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  This prompt will be used when generating automatic captions. You can resize this text area as needed.
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  API Provider
                </label>
                <select
                  value={formData.captionApiProvider}
                  onChange={(e) => handleInputChange('captionApiProvider', e.target.value)}
                  className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  <option value="">Select API Provider</option>
                  <option value="gemini">Google Gemini</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  API Key
                </label>
                <input
                  type="password"
                  value={formData.captionApiKey}
                  onChange={(e) => handleInputChange('captionApiKey', e.target.value)}
                  className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  placeholder="Enter your API key"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Your API key is stored securely and only used for generating captions
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Model (Optional)
                </label>
                <input
                  type="text"
                  value={formData.captionApiModel}
                  onChange={(e) => handleInputChange('captionApiModel', e.target.value)}
                  className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  placeholder="e.g., gemini-1.5-flash (optional)"
                />
              </div>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex justify-end space-x-3 mt-8">
          <button
            onClick={onClose}
            disabled={saving}
            className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !formData.name.trim()}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  )
}