import { useState, useMemo } from 'react'
import type { ThreeEvent } from '@react-three/fiber'
import type { CellType } from '../store/simulationStore'

interface CellProps {
  id: number
  position: [number, number, number]
  cellType: CellType
  temperature: number
  isHovered: boolean
  isSelected: boolean
  onClick: (id: number) => void
  onHover: (id: number | null) => void
}

// Map temperature to color (25°C blue -> 400°C red)
function temperatureToColor(temp: number): string {
  const minTemp = 25
  const maxTemp = 400
  const t = Math.max(0, Math.min(1, (temp - minTemp) / (maxTemp - minTemp)))

  // Blue (cold) -> Yellow (mid) -> Red (hot)
  if (t < 0.5) {
    // Blue to Yellow
    const r = Math.round(t * 2 * 255)
    const g = Math.round(t * 2 * 255)
    const b = Math.round((1 - t * 2) * 255)
    return `rgb(${r},${g},${b})`
  } else {
    // Yellow to Red
    const r = 255
    const g = Math.round((1 - (t - 0.5) * 2) * 255)
    const b = 0
    return `rgb(${r},${g},${b})`
  }
}

// Cell dimensions in meters (for 3D scale)
const CELL_DIMENSIONS: Record<CellType, { width: number; height: number; depth: number; radius?: number }> = {
  cylindrical_21700: { width: 0.021, height: 0.070, depth: 0.021, radius: 0.0105 },
  cylindrical_18650: { width: 0.018, height: 0.065, depth: 0.018, radius: 0.009 },
  prismatic: { width: 0.020, height: 0.100, depth: 0.080 },
  pouch: { width: 0.010, height: 0.100, depth: 0.080 },
}

// Scale factor for visibility
const SCALE = 100

function Cell({ id, position, cellType, temperature, isHovered, isSelected, onClick, onHover }: CellProps) {
  const dims = CELL_DIMENSIONS[cellType]
  const isCylindrical = cellType.startsWith('cylindrical')
  const color = temperatureToColor(temperature)

  const handleClick = (e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation()
    onClick(id)
  }

  const handlePointerOver = (e: ThreeEvent<PointerEvent>) => {
    e.stopPropagation()
    onHover(id)
  }

  const handlePointerOut = () => {
    onHover(null)
  }

  // Highlight effect
  const emissiveIntensity = isHovered ? 0.3 : isSelected ? 0.5 : 0

  if (isCylindrical) {
    return (
      <mesh
        position={position}
        rotation={[Math.PI / 2, 0, 0]}
        onClick={handleClick}
        onPointerOver={handlePointerOver}
        onPointerOut={handlePointerOut}
      >
        <cylinderGeometry args={[dims.radius! * SCALE, dims.radius! * SCALE, dims.height * SCALE, 16]} />
        <meshStandardMaterial
          color={color}
          emissive={isHovered || isSelected ? '#ffffff' : '#000000'}
          emissiveIntensity={emissiveIntensity}
        />
      </mesh>
    )
  }

  return (
    <mesh
      position={position}
      onClick={handleClick}
      onPointerOver={handlePointerOver}
      onPointerOut={handlePointerOut}
    >
      <boxGeometry args={[dims.depth * SCALE, dims.height * SCALE, dims.width * SCALE]} />
      <meshStandardMaterial
        color={color}
        emissive={isHovered || isSelected ? '#ffffff' : '#000000'}
        emissiveIntensity={emissiveIntensity}
      />
    </mesh>
  )
}

interface ModuleViewerProps {
  rows: number
  cols: number
  cellType: CellType
  spacingMm: number
  temperatures?: number[]
  selectedCell?: number | null
  onCellClick?: (id: number) => void
}

export default function ModuleViewer({
  rows,
  cols,
  cellType,
  spacingMm,
  temperatures,
  selectedCell = null,
  onCellClick,
}: ModuleViewerProps) {
  const [hoveredCell, setHoveredCell] = useState<number | null>(null)

  const cells = useMemo(() => {
    const dims = CELL_DIMENSIONS[cellType]
    const spacingM = spacingMm / 1000
    const cellWidth = dims.depth
    const cellDepth = dims.width

    // Calculate pitch (center-to-center distance)
    const pitchX = (cellWidth + spacingM) * SCALE
    const pitchZ = (cellDepth + spacingM) * SCALE

    // Calculate offset to center the module
    const offsetX = ((cols - 1) * pitchX) / 2
    const offsetZ = ((rows - 1) * pitchZ) / 2

    const result: Array<{ id: number; position: [number, number, number] }> = []

    for (let row = 0; row < rows; row++) {
      for (let col = 0; col < cols; col++) {
        const id = row * cols + col
        const x = col * pitchX - offsetX
        const z = row * pitchZ - offsetZ
        const y = (dims.height * SCALE) / 2 // Sit on ground plane

        result.push({ id, position: [x, y, z] })
      }
    }

    return result
  }, [rows, cols, cellType, spacingMm])

  const handleCellClick = (id: number) => {
    onCellClick?.(id)
  }

  return (
    <group>
      {cells.map(({ id, position }) => (
        <Cell
          key={id}
          id={id}
          position={position}
          cellType={cellType}
          temperature={temperatures?.[id] ?? 25}
          isHovered={hoveredCell === id}
          isSelected={selectedCell === id}
          onClick={handleCellClick}
          onHover={setHoveredCell}
        />
      ))}
    </group>
  )
}
