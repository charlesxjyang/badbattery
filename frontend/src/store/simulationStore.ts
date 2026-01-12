import { create } from 'zustand'
import { runSimulationWS } from '../api/websocket'

export type CellType = 'cylindrical_21700' | 'cylindrical_18650' | 'prismatic' | 'pouch'
export type CoolingType = 'none' | 'bottom_plate' | 'side_channels'
export type AbuseType = 'nail_penetration' | 'external_heat' | 'overcharge'
export type ThermalModel = 'lumped' | 'fem_3d'

export interface ModuleConfig {
  rows: number
  cols: number
  cell_type: CellType
  spacing_mm: number
}

export interface CellConfig {
  chemistry: string
  capacity_ah: number
  mass_kg: number
  specific_heat: number
  thermal_resistance: number
}

export interface ThermalRunawayConfig {
  onset_temp_c: number
  peak_heat_w: number
  total_energy_kj: number
  duration_s: number
}

export interface CoolingConfig {
  type: CoolingType
  coolant_temp_c: number
  htc: number
}

export interface AbuseConfig {
  type: AbuseType
  target_cell: number
  short_resistance_mohm: number
}

export interface SolverConfig {
  thermal_model: ThermalModel
  time_end_s: number
  dt_s: number
  dt_output_s: number
}

export interface SimulationConfig {
  module: ModuleConfig
  cell: CellConfig
  thermal_runaway: ThermalRunawayConfig
  cooling: CoolingConfig
  abuse: AbuseConfig
  solver: SolverConfig
}

export interface CellState {
  id: number
  temperature_c: number
  in_thermal_runaway: boolean
  tr_start_time: number | null
}

export interface SimulationFrame {
  time_s: number
  cells: CellState[]
}

export interface TRPropagationEvent {
  cell_id: number
  time_s: number
  trigger: string
}

export interface SimulationResult {
  config: SimulationConfig
  frames: SimulationFrame[]
  tr_propagation_events: TRPropagationEvent[]
  completed: boolean
}

type SimulationStatus = 'idle' | 'running' | 'completed' | 'error'

interface SimulationStore {
  // Configuration
  config: SimulationConfig

  // Simulation state
  status: SimulationStatus
  isRunning: boolean
  currentFrame: SimulationFrame | null
  frames: SimulationFrame[]
  result: SimulationResult | null
  error: string | null
  cancelSimulation: (() => void) | null

  // Actions
  updateModule: (updates: Partial<ModuleConfig>) => void
  updateCell: (updates: Partial<CellConfig>) => void
  updateThermalRunaway: (updates: Partial<ThermalRunawayConfig>) => void
  updateCooling: (updates: Partial<CoolingConfig>) => void
  updateAbuse: (updates: Partial<AbuseConfig>) => void
  updateSolver: (updates: Partial<SolverConfig>) => void

  startSimulation: () => void
  stopSimulation: () => void
  setStatus: (status: SimulationStatus) => void
  setCurrentFrame: (frame: SimulationFrame | null) => void
  setResult: (result: SimulationResult | null) => void
  setError: (error: string | null) => void
  reset: () => void
}

const defaultConfig: SimulationConfig = {
  module: {
    rows: 3,
    cols: 4,
    cell_type: 'cylindrical_21700',
    spacing_mm: 2.0,
  },
  cell: {
    chemistry: 'NMC811',
    capacity_ah: 5.0,
    mass_kg: 0.07,
    specific_heat: 1000.0,
    thermal_resistance: 1.0,
  },
  thermal_runaway: {
    onset_temp_c: 150.0,
    peak_heat_w: 5000.0,
    total_energy_kj: 100.0,
    duration_s: 30.0,
  },
  cooling: {
    type: 'none',
    coolant_temp_c: 25.0,
    htc: 50.0,
  },
  abuse: {
    type: 'nail_penetration',
    target_cell: 0,
    short_resistance_mohm: 10.0,
  },
  solver: {
    thermal_model: 'lumped',
    time_end_s: 60.0,
    dt_s: 0.01,
    dt_output_s: 0.5,
  },
}

export const useSimulationStore = create<SimulationStore>((set, get) => ({
  config: defaultConfig,
  status: 'idle',
  isRunning: false,
  currentFrame: null,
  frames: [],
  result: null,
  error: null,
  cancelSimulation: null,

  updateModule: (updates) =>
    set((state) => ({
      config: { ...state.config, module: { ...state.config.module, ...updates } },
    })),

  updateCell: (updates) =>
    set((state) => ({
      config: { ...state.config, cell: { ...state.config.cell, ...updates } },
    })),

  updateThermalRunaway: (updates) =>
    set((state) => ({
      config: {
        ...state.config,
        thermal_runaway: { ...state.config.thermal_runaway, ...updates },
      },
    })),

  updateCooling: (updates) =>
    set((state) => ({
      config: { ...state.config, cooling: { ...state.config.cooling, ...updates } },
    })),

  updateAbuse: (updates) =>
    set((state) => ({
      config: { ...state.config, abuse: { ...state.config.abuse, ...updates } },
    })),

  updateSolver: (updates) =>
    set((state) => ({
      config: { ...state.config, solver: { ...state.config.solver, ...updates } },
    })),

  startSimulation: () => {
    const { config, isRunning } = get()
    if (isRunning) return

    // Reset state for new simulation
    set({
      status: 'running',
      isRunning: true,
      currentFrame: null,
      frames: [],
      result: null,
      error: null,
    })

    const cancel = runSimulationWS(
      config,
      // onFrame
      (frame) => {
        set((state) => ({
          currentFrame: frame,
          frames: [...state.frames, frame],
        }))
      },
      // onComplete
      (result) => {
        set({
          status: 'completed',
          isRunning: false,
          result,
          cancelSimulation: null,
        })
      },
      // onError
      (errorMsg) => {
        set({
          status: 'error',
          isRunning: false,
          error: errorMsg,
          cancelSimulation: null,
        })
      }
    )

    set({ cancelSimulation: cancel })
  },

  stopSimulation: () => {
    const { cancelSimulation } = get()
    if (cancelSimulation) {
      cancelSimulation()
      set({
        status: 'idle',
        isRunning: false,
        cancelSimulation: null,
      })
    }
  },

  setStatus: (status) => set({ status, isRunning: status === 'running' }),
  setCurrentFrame: (currentFrame) => set({ currentFrame }),
  setResult: (result) => set({ result }),
  setError: (error) => set({ error }),
  reset: () =>
    set({
      status: 'idle',
      isRunning: false,
      currentFrame: null,
      frames: [],
      result: null,
      error: null,
      cancelSimulation: null,
    }),
}))
