import { useState, useEffect, useRef, useCallback } from 'react'
import { useSimulationStore } from '../store/simulationStore'

const PLAYBACK_SPEEDS = [0.5, 1, 2] as const

// Color scale matching ModuleViewer
function getColorAtPosition(t: number): string {
  if (t < 0.5) {
    const r = Math.round(t * 2 * 255)
    const g = Math.round(t * 2 * 255)
    const b = Math.round((1 - t * 2) * 255)
    return `rgb(${r},${g},${b})`
  } else {
    const r = 255
    const g = Math.round((1 - (t - 0.5) * 2) * 255)
    return `rgb(${r},${g},0)`
  }
}

export default function ResultsViewer() {
  const { frames, result, status, setCurrentFrame, config } = useSimulationStore()

  const [frameIndex, setFrameIndex] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [playbackSpeed, setPlaybackSpeed] = useState<(typeof PLAYBACK_SPEEDS)[number]>(1)
  const animationRef = useRef<number | null>(null)
  const lastTimeRef = useRef<number>(0)

  const hasFrames = frames.length > 0
  const currentFrame = hasFrames ? frames[frameIndex] : null
  const trEvents = result?.tr_propagation_events ?? []

  // Update store's currentFrame when frameIndex changes
  useEffect(() => {
    if (currentFrame) {
      setCurrentFrame(currentFrame)
    }
  }, [currentFrame, setCurrentFrame])

  // Reset to first frame when new simulation starts
  useEffect(() => {
    if (status === 'running') {
      setFrameIndex(0)
      setIsPlaying(false)
    }
  }, [status])

  // Auto-play animation when simulation completes
  useEffect(() => {
    if (status === 'completed' && frames.length > 1) {
      setFrameIndex(0)
      setIsPlaying(true)
    }
  }, [status, frames.length])

  // Animation loop
  const animate = useCallback(
    (timestamp: number) => {
      if (!isPlaying || !hasFrames) return

      const elapsed = timestamp - lastTimeRef.current
      const frameInterval = (config.solver.dt_output_s * 1000) / playbackSpeed

      if (elapsed >= frameInterval) {
        lastTimeRef.current = timestamp
        setFrameIndex((prev) => {
          const next = prev + 1
          if (next >= frames.length) {
            setIsPlaying(false)
            return prev
          }
          return next
        })
      }

      animationRef.current = requestAnimationFrame(animate)
    },
    [isPlaying, hasFrames, frames.length, config.solver.dt_output_s, playbackSpeed]
  )

  useEffect(() => {
    if (isPlaying) {
      lastTimeRef.current = performance.now()
      animationRef.current = requestAnimationFrame(animate)
    }
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [isPlaying, animate])

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const index = parseInt(e.target.value, 10)
    setFrameIndex(index)
    setIsPlaying(false)
  }

  const togglePlayPause = () => {
    if (!hasFrames) return
    if (frameIndex >= frames.length - 1) {
      setFrameIndex(0)
    }
    setIsPlaying(!isPlaying)
  }

  const cycleSpeed = () => {
    const currentIdx = PLAYBACK_SPEEDS.indexOf(playbackSpeed)
    const nextIdx = (currentIdx + 1) % PLAYBACK_SPEEDS.length
    setPlaybackSpeed(PLAYBACK_SPEEDS[nextIdx])
  }

  // Get events up to current time
  const visibleEvents = currentFrame
    ? trEvents.filter((e) => e.time_s <= currentFrame.time_s)
    : []

  if (!hasFrames && status !== 'running') {
    return (
      <div className="h-full flex items-center justify-center text-gray-500">
        <p>Run a simulation to see results</p>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col bg-gray-800 text-white p-4 space-y-4">
      {/* Playback Controls */}
      <div className="flex items-center gap-3">
        {/* Play/Pause Button */}
        <button
          onClick={togglePlayPause}
          disabled={!hasFrames}
          className="w-10 h-10 flex items-center justify-center bg-gray-700 hover:bg-gray-600
                     rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isPlaying ? (
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <rect x="6" y="4" width="4" height="16" />
              <rect x="14" y="4" width="4" height="16" />
            </svg>
          ) : (
            <svg className="w-5 h-5 ml-0.5" fill="currentColor" viewBox="0 0 24 24">
              <polygon points="5,3 19,12 5,21" />
            </svg>
          )}
        </button>

        {/* Time Slider */}
        <div className="flex-1 flex items-center gap-2">
          <span className="text-xs text-gray-400 w-16">
            {currentFrame ? `${currentFrame.time_s.toFixed(1)}s` : '0.0s'}
          </span>
          <input
            type="range"
            min={0}
            max={Math.max(0, frames.length - 1)}
            value={frameIndex}
            onChange={handleSliderChange}
            disabled={!hasFrames}
            className="flex-1 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer
                       disabled:opacity-50 disabled:cursor-not-allowed
                       [&::-webkit-slider-thumb]:appearance-none
                       [&::-webkit-slider-thumb]:w-4
                       [&::-webkit-slider-thumb]:h-4
                       [&::-webkit-slider-thumb]:bg-blue-500
                       [&::-webkit-slider-thumb]:rounded-full
                       [&::-webkit-slider-thumb]:cursor-pointer"
          />
          <span className="text-xs text-gray-400 w-16 text-right">
            {frames.length > 0 ? `${frames[frames.length - 1].time_s.toFixed(1)}s` : '0.0s'}
          </span>
        </div>

        {/* Speed Control */}
        <button
          onClick={cycleSpeed}
          className="px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded text-sm font-mono transition-colors"
        >
          {playbackSpeed}x
        </button>
      </div>

      {/* Temperature Legend */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-400">25°C</span>
        <div
          className="flex-1 h-3 rounded"
          style={{
            background: `linear-gradient(to right, ${getColorAtPosition(0)}, ${getColorAtPosition(0.5)}, ${getColorAtPosition(1)})`,
          }}
        />
        <span className="text-xs text-gray-400">400°C</span>
      </div>

      {/* Current Stats */}
      {currentFrame && (
        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="bg-gray-700 rounded p-2">
            <div className="text-xs text-gray-400">Max Temp</div>
            <div className="text-lg font-semibold">
              {Math.max(...currentFrame.cells.map((c) => c.temperature_c)).toFixed(0)}°C
            </div>
          </div>
          <div className="bg-gray-700 rounded p-2">
            <div className="text-xs text-gray-400">Cells in TR</div>
            <div className="text-lg font-semibold text-red-400">
              {currentFrame.cells.filter((c) => c.in_thermal_runaway).length}
            </div>
          </div>
          <div className="bg-gray-700 rounded p-2">
            <div className="text-xs text-gray-400">Frame</div>
            <div className="text-lg font-semibold">
              {frameIndex + 1}/{frames.length}
            </div>
          </div>
        </div>
      )}

      {/* TR Event Markers */}
      <div className="flex-1 overflow-y-auto">
        <h3 className="text-sm font-medium text-gray-400 mb-2">Thermal Runaway Events</h3>
        {visibleEvents.length === 0 ? (
          <p className="text-xs text-gray-500">No TR events yet</p>
        ) : (
          <div className="space-y-1">
            {visibleEvents.map((event, idx) => (
              <div
                key={idx}
                className="flex items-center gap-2 text-sm bg-red-900/30 border border-red-800 rounded px-2 py-1"
              >
                <span className="text-red-400">⚠</span>
                <span>
                  Cell {event.cell_id} entered TR at t={event.time_s.toFixed(1)}s
                </span>
                <span className="text-xs text-gray-400 ml-auto">({event.trigger})</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
