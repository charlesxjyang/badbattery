import { useState, useEffect, type ReactNode } from 'react'
import { useSimulationStore } from '../store/simulationStore'
import { fetchCellPresets, fetchCellPreset } from '../api/client'

interface SectionProps {
  title: string
  defaultOpen?: boolean
  children: ReactNode
}

function Section({ title, defaultOpen = false, children }: SectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen)

  return (
    <div className="border-b border-gray-700">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-3 hover:bg-gray-750 transition-colors"
      >
        <span className="font-medium text-sm">{title}</span>
        <svg
          className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {isOpen && <div className="px-3 pb-3 space-y-3">{children}</div>}
    </div>
  )
}

interface InputFieldProps {
  label: string
  value: number | string
  onChange: (value: number | string) => void
  type?: 'number' | 'text'
  min?: number
  max?: number
  step?: number
  unit?: string
}

function InputField({
  label,
  value,
  onChange,
  type = 'number',
  min,
  max,
  step,
  unit,
}: InputFieldProps) {
  return (
    <div>
      <label className="block text-xs text-gray-400 mb-1">
        {label}
        {unit && <span className="text-gray-500 ml-1">({unit})</span>}
      </label>
      <input
        type={type}
        value={value}
        onChange={(e) =>
          onChange(type === 'number' ? parseFloat(e.target.value) || 0 : e.target.value)
        }
        min={min}
        max={max}
        step={step}
        className="w-full bg-gray-700 border border-gray-600 rounded px-2 py-1.5 text-sm
                   focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
      />
    </div>
  )
}

interface SelectFieldProps {
  label: string
  value: string
  onChange: (value: string) => void
  options: { value: string; label: string }[]
}

function SelectField({ label, value, onChange, options }: SelectFieldProps) {
  return (
    <div>
      <label className="block text-xs text-gray-400 mb-1">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full bg-gray-700 border border-gray-600 rounded px-2 py-1.5 text-sm
                   focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  )
}

export default function ParameterPanel() {
  const {
    config,
    status,
    isRunning,
    currentFrame,
    error,
    updateModule,
    updateCell,
    updateThermalRunaway,
    updateCooling,
    updateAbuse,
    updateSolver,
    startSimulation,
    stopSimulation,
  } = useSimulationStore()

  const [cellPresets, setCellPresets] = useState<string[]>([])
  const [selectedPreset, setSelectedPreset] = useState<string>('')
  const [loadingPreset, setLoadingPreset] = useState(false)

  // Fetch available presets on mount
  useEffect(() => {
    fetchCellPresets()
      .then(setCellPresets)
      .catch((err) => console.warn('Failed to load cell presets:', err.message))
  }, [])

  // Load preset when selected
  const handlePresetChange = async (presetName: string) => {
    setSelectedPreset(presetName)
    if (!presetName) return

    setLoadingPreset(true)
    try {
      const preset = await fetchCellPreset(presetName)
      updateCell({
        chemistry: (preset.chemistry as string) ?? config.cell.chemistry,
        capacity_ah: (preset.capacity_ah as number) ?? config.cell.capacity_ah,
        mass_kg: (preset.mass_kg as number) ?? config.cell.mass_kg,
        specific_heat: (preset.specific_heat as number) ?? config.cell.specific_heat,
        thermal_resistance: (preset.thermal_resistance as number) ?? config.cell.thermal_resistance,
      })
    } catch (err) {
      console.error('Failed to load preset:', err)
    } finally {
      setLoadingPreset(false)
    }
  }

  const handleRunSimulation = () => {
    if (isRunning) {
      stopSimulation()
    } else {
      startSimulation()
    }
  }

  // Calculate progress
  const progress = currentFrame
    ? (currentFrame.time_s / config.solver.time_end_s) * 100
    : 0

  return (
    <div className="h-full flex flex-col bg-gray-800 text-white overflow-hidden">
      <div className="flex-1 overflow-y-auto">
        {/* Module Section */}
        <Section title="Module" defaultOpen>
          <div className="grid grid-cols-2 gap-2">
            <InputField
              label="Rows"
              value={config.module.rows}
              onChange={(v) => updateModule({ rows: v as number })}
              min={1}
              max={20}
              step={1}
            />
            <InputField
              label="Columns"
              value={config.module.cols}
              onChange={(v) => updateModule({ cols: v as number })}
              min={1}
              max={20}
              step={1}
            />
          </div>
          <SelectField
            label="Cell Type"
            value={config.module.cell_type}
            onChange={(v) => updateModule({ cell_type: v as typeof config.module.cell_type })}
            options={[
              { value: 'cylindrical_21700', label: '21700 Cylindrical' },
              { value: 'cylindrical_18650', label: '18650 Cylindrical' },
              { value: 'prismatic', label: 'Prismatic' },
              { value: 'pouch', label: 'Pouch' },
            ]}
          />
          <InputField
            label="Spacing"
            value={config.module.spacing_mm}
            onChange={(v) => updateModule({ spacing_mm: v as number })}
            min={0}
            max={50}
            step={0.5}
            unit="mm"
          />
        </Section>

        {/* Cell Section */}
        <Section title="Cell">
          {cellPresets.length > 0 && (
            <div>
              <label className="block text-xs text-gray-400 mb-1">Load Preset</label>
              <select
                value={selectedPreset}
                onChange={(e) => handlePresetChange(e.target.value)}
                disabled={loadingPreset}
                className="w-full bg-gray-700 border border-gray-600 rounded px-2 py-1.5 text-sm
                           focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500
                           disabled:opacity-50"
              >
                <option value="">-- Select Preset --</option>
                {cellPresets.map((preset) => (
                  <option key={preset} value={preset}>
                    {preset}
                  </option>
                ))}
              </select>
            </div>
          )}
          <InputField
            label="Chemistry"
            value={config.cell.chemistry}
            onChange={(v) => updateCell({ chemistry: v as string })}
            type="text"
          />
          <div className="grid grid-cols-2 gap-2">
            <InputField
              label="Capacity"
              value={config.cell.capacity_ah}
              onChange={(v) => updateCell({ capacity_ah: v as number })}
              min={0.1}
              max={500}
              step={0.1}
              unit="Ah"
            />
            <InputField
              label="Mass"
              value={config.cell.mass_kg}
              onChange={(v) => updateCell({ mass_kg: v as number })}
              min={0.01}
              max={10}
              step={0.01}
              unit="kg"
            />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <InputField
              label="Specific Heat"
              value={config.cell.specific_heat}
              onChange={(v) => updateCell({ specific_heat: v as number })}
              min={500}
              max={2000}
              step={10}
              unit="J/kg·K"
            />
            <InputField
              label="Thermal R"
              value={config.cell.thermal_resistance}
              onChange={(v) => updateCell({ thermal_resistance: v as number })}
              min={0.01}
              max={100}
              step={0.1}
              unit="K/W"
            />
          </div>
        </Section>

        {/* Thermal Runaway Section */}
        <Section title="Thermal Runaway">
          <div className="grid grid-cols-2 gap-2">
            <InputField
              label="Onset Temp"
              value={config.thermal_runaway.onset_temp_c}
              onChange={(v) => updateThermalRunaway({ onset_temp_c: v as number })}
              min={80}
              max={300}
              step={5}
              unit="°C"
            />
            <InputField
              label="Peak Heat"
              value={config.thermal_runaway.peak_heat_w}
              onChange={(v) => updateThermalRunaway({ peak_heat_w: v as number })}
              min={100}
              max={100000}
              step={100}
              unit="W"
            />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <InputField
              label="Total Energy"
              value={config.thermal_runaway.total_energy_kj}
              onChange={(v) => updateThermalRunaway({ total_energy_kj: v as number })}
              min={1}
              max={5000}
              step={10}
              unit="kJ"
            />
            <InputField
              label="Duration"
              value={config.thermal_runaway.duration_s}
              onChange={(v) => updateThermalRunaway({ duration_s: v as number })}
              min={0.1}
              max={600}
              step={1}
              unit="s"
            />
          </div>
        </Section>

        {/* Cooling Section */}
        <Section title="Cooling">
          <SelectField
            label="Cooling Type"
            value={config.cooling.type}
            onChange={(v) => updateCooling({ type: v as typeof config.cooling.type })}
            options={[
              { value: 'none', label: 'None' },
              { value: 'bottom_plate', label: 'Bottom Plate' },
              { value: 'side_channels', label: 'Side Channels' },
            ]}
          />
          <div className="grid grid-cols-2 gap-2">
            <InputField
              label="Coolant Temp"
              value={config.cooling.coolant_temp_c}
              onChange={(v) => updateCooling({ coolant_temp_c: v as number })}
              min={-40}
              max={60}
              step={1}
              unit="°C"
            />
            <InputField
              label="HTC"
              value={config.cooling.htc}
              onChange={(v) => updateCooling({ htc: v as number })}
              min={0}
              max={10000}
              step={10}
              unit="W/m²·K"
            />
          </div>
        </Section>

        {/* Abuse Section */}
        <Section title="Abuse" defaultOpen>
          <SelectField
            label="Abuse Type"
            value={config.abuse.type}
            onChange={(v) => updateAbuse({ type: v as typeof config.abuse.type })}
            options={[
              { value: 'nail_penetration', label: 'Nail Penetration' },
              { value: 'external_heat', label: 'External Heat' },
              { value: 'overcharge', label: 'Overcharge' },
            ]}
          />
          <div className="grid grid-cols-2 gap-2">
            <InputField
              label="Target Cell"
              value={config.abuse.target_cell}
              onChange={(v) => updateAbuse({ target_cell: v as number })}
              min={0}
              max={config.module.rows * config.module.cols - 1}
              step={1}
            />
            <InputField
              label="Short R"
              value={config.abuse.short_resistance_mohm}
              onChange={(v) => updateAbuse({ short_resistance_mohm: v as number })}
              min={0.1}
              max={1000}
              step={1}
              unit="mΩ"
            />
          </div>
        </Section>

        {/* Solver Section */}
        <Section title="Solver">
          <SelectField
            label="Thermal Model"
            value={config.solver.thermal_model}
            onChange={(v) => updateSolver({ thermal_model: v as typeof config.solver.thermal_model })}
            options={[
              { value: 'lumped', label: 'Lumped (Fast)' },
              { value: 'fem_3d', label: '3D FEM (Detailed)' },
            ]}
          />
          <div className="grid grid-cols-2 gap-2">
            <InputField
              label="End Time"
              value={config.solver.time_end_s}
              onChange={(v) => updateSolver({ time_end_s: v as number })}
              min={1}
              max={3600}
              step={1}
              unit="s"
            />
            <InputField
              label="Output Δt"
              value={config.solver.dt_output_s}
              onChange={(v) => updateSolver({ dt_output_s: v as number })}
              min={0.01}
              max={10}
              step={0.1}
              unit="s"
            />
          </div>
        </Section>
      </div>

      {/* Progress & Run Button */}
      <div className="p-3 border-t border-gray-700 space-y-2">
        {/* Progress indicator */}
        {(isRunning || status === 'completed') && currentFrame && (
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-gray-400">
              <span>t = {currentFrame.time_s.toFixed(1)}s</span>
              <span>{progress.toFixed(0)}%</span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all duration-300 ${
                  status === 'completed' ? 'bg-green-500' : 'bg-blue-500'
                }`}
                style={{ width: `${Math.min(100, progress)}%` }}
              />
            </div>
          </div>
        )}

        {/* Error message */}
        {error && (
          <div className="text-xs text-red-400 bg-red-900/30 rounded p-2">
            {error}
          </div>
        )}

        {/* Status indicator */}
        {status === 'completed' && (
          <div className="text-xs text-green-400 text-center">
            Simulation completed
          </div>
        )}

        <button
          onClick={handleRunSimulation}
          className={`w-full py-2.5 px-4 rounded font-medium transition-colors ${
            isRunning
              ? 'bg-red-600 hover:bg-red-700 text-white'
              : 'bg-blue-600 hover:bg-blue-700 text-white'
          }`}
        >
          {isRunning ? 'Stop Simulation' : 'Run Simulation'}
        </button>
      </div>
    </div>
  )
}
