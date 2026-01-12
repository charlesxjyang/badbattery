import { useEffect } from 'react'
import Scene from './components/Scene'
import ParameterPanel from './components/ParameterPanel'
import ResultsViewer from './components/ResultsViewer'
import { fetchHealth } from './api/client'

function App() {
  useEffect(() => {
    fetchHealth()
      .then((response) => console.log('Backend health:', response))
      .catch((error) => console.warn('Backend not available:', error.message))
  }, [])
  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <header className="border-b border-gray-700 p-4">
        <h1 className="text-2xl font-bold">EV Battery Safety Simulator</h1>
        <p className="text-gray-400">Thermal runaway propagation analysis</p>
      </header>

      <main className="p-4">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* 3D Viewer */}
          <div className="lg:col-span-2 bg-gray-800 rounded-lg overflow-hidden h-96">
            <Scene />
          </div>

          {/* Parameter Panel */}
          <div className="lg:row-span-2 bg-gray-800 rounded-lg overflow-hidden h-[calc(100vh-12rem)]">
            <ParameterPanel />
          </div>

          {/* Results Viewer */}
          <div className="lg:col-span-2 bg-gray-800 rounded-lg overflow-hidden h-72">
            <ResultsViewer />
          </div>
        </div>
      </main>
    </div>
  )
}

export default App
