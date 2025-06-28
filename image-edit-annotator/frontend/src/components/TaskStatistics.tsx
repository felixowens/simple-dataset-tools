import { type Task } from '../api'

interface TaskStatisticsProps {
  tasks: Task[]
}

export function TaskStatistics({ tasks }: TaskStatisticsProps) {
  const totalTasks = tasks.length
  const completedTasks = tasks.filter(t => (t.imageBId?.Valid || t.prompt?.Valid) && !t.skipped).length
  const skippedTasks = tasks.filter(t => t.skipped).length
  const pendingTasks = totalTasks - completedTasks - skippedTasks

  const getPercentage = (count: number) => totalTasks > 0 ? Math.round((count / totalTasks) * 100) : 0

  return (
    <div className="bg-gray-700 rounded-lg p-4">
      <h3 className="text-lg font-semibold text-white mb-4">Task Progress</h3>
      
      {/* Progress Bar */}
      <div className="w-full bg-gray-600 rounded-full h-3 mb-4 overflow-hidden">
        <div className="h-full flex">
          <div 
            className="bg-green-500 transition-all duration-500"
            style={{ width: `${getPercentage(completedTasks)}%` }}
          />
          <div 
            className="bg-yellow-500 transition-all duration-500"
            style={{ width: `${getPercentage(skippedTasks)}%` }}
          />
          <div 
            className="bg-gray-500 transition-all duration-500"
            style={{ width: `${getPercentage(pendingTasks)}%` }}
          />
        </div>
      </div>

      {/* Statistics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="text-center">
          <div className="text-2xl font-bold text-white">{totalTasks}</div>
          <div className="text-xs text-gray-300">Total</div>
        </div>
        
        <div className="text-center">
          <div className="text-2xl font-bold text-green-400">{completedTasks}</div>
          <div className="text-xs text-gray-300">Completed</div>
          <div className="text-xs text-gray-400">({getPercentage(completedTasks)}%)</div>
        </div>
        
        <div className="text-center">
          <div className="text-2xl font-bold text-yellow-400">{skippedTasks}</div>
          <div className="text-xs text-gray-300">Skipped</div>
          <div className="text-xs text-gray-400">({getPercentage(skippedTasks)}%)</div>
        </div>
        
        <div className="text-center">
          <div className="text-2xl font-bold text-gray-400">{pendingTasks}</div>
          <div className="text-xs text-gray-300">Pending</div>
          <div className="text-xs text-gray-400">({getPercentage(pendingTasks)}%)</div>
        </div>
      </div>

      {/* Status Legend */}
      <div className="flex justify-center items-center space-x-6 mt-4 text-xs">
        <div className="flex items-center space-x-1">
          <div className="w-3 h-3 bg-green-500 rounded-full"></div>
          <span className="text-gray-300">Completed</span>
        </div>
        <div className="flex items-center space-x-1">
          <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
          <span className="text-gray-300">Skipped</span>
        </div>
        <div className="flex items-center space-x-1">
          <div className="w-3 h-3 bg-gray-500 rounded-full"></div>
          <span className="text-gray-300">Pending</span>
        </div>
      </div>
    </div>
  )
}