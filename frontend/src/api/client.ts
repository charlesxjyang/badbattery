import type { SimulationConfig, SimulationResult, ModuleConfig } from '../store/simulationStore'

const API_BASE = '/api'

interface HealthResponse {
  status: string
}

interface ModulePreview {
  cells: Array<{
    id: number
    position: { x: number; y: number; z: number }
    dimensions: { width: number; height: number; depth: number }
  }>
  adjacency: Array<[number, number]>
  bounds: {
    min: { x: number; y: number; z: number }
    max: { x: number; y: number; z: number }
  }
}

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE}/health`)
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`)
  }
  return response.json()
}

export async function fetchCellPresets(): Promise<string[]> {
  const response = await fetch(`${API_BASE}/presets/cells`)
  if (!response.ok) {
    throw new Error(`Failed to fetch cell presets: ${response.status}`)
  }
  return response.json()
}

export async function fetchCellPreset(name: string): Promise<Record<string, unknown>> {
  const response = await fetch(`${API_BASE}/presets/cells/${encodeURIComponent(name)}`)
  if (!response.ok) {
    throw new Error(`Failed to fetch preset ${name}: ${response.status}`)
  }
  return response.json()
}

export async function fetchModulePreview(config: ModuleConfig): Promise<ModulePreview> {
  const params = new URLSearchParams({
    rows: config.rows.toString(),
    cols: config.cols.toString(),
    cell_type: config.cell_type,
    spacing_mm: config.spacing_mm.toString(),
  })

  const response = await fetch(`${API_BASE}/module/preview?${params}`)
  if (!response.ok) {
    throw new Error(`Failed to fetch module preview: ${response.status}`)
  }
  return response.json()
}

export async function runSimulation(config: SimulationConfig): Promise<SimulationResult> {
  const response = await fetch(`${API_BASE}/simulations`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(config),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || `Simulation failed: ${response.status}`)
  }

  return response.json()
}
