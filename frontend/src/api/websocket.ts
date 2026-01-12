import type { SimulationConfig, SimulationFrame, SimulationResult } from '../store/simulationStore'

interface WebSocketMessage {
  type: 'frame' | 'result' | 'error'
  data?: SimulationFrame | SimulationResult
  message?: string
}

export function runSimulationWS(
  config: SimulationConfig,
  onFrame: (frame: SimulationFrame) => void,
  onComplete: (result: SimulationResult) => void,
  onError: (error: string) => void
): () => void {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  const ws = new WebSocket(`${protocol}//${host}/ws/simulation`)

  ws.onopen = () => {
    ws.send(JSON.stringify(config))
  }

  ws.onmessage = (event) => {
    try {
      const msg: WebSocketMessage = JSON.parse(event.data)

      switch (msg.type) {
        case 'frame':
          if (msg.data) {
            onFrame(msg.data as SimulationFrame)
          }
          break
        case 'result':
          if (msg.data) {
            onComplete(msg.data as SimulationResult)
          }
          ws.close()
          break
        case 'error':
          onError(msg.message ?? 'Unknown error')
          ws.close()
          break
      }
    } catch (err) {
      onError(`Failed to parse message: ${err}`)
    }
  }

  ws.onerror = () => {
    onError('WebSocket connection error')
  }

  ws.onclose = (event) => {
    if (event.code !== 1000 && event.code !== 1005) {
      onError(`Connection closed unexpectedly (code: ${event.code})`)
    }
  }

  // Return cleanup function to abort simulation
  return () => {
    if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
      ws.close()
    }
  }
}
