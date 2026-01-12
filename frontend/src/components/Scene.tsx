import { Canvas } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import { useSimulationStore } from '../store/simulationStore'
import ModuleViewer from './ModuleViewer'

function SceneContent() {
  const { config, currentFrame, updateAbuse } = useSimulationStore()
  const { module: moduleConfig, abuse } = config

  // Get temperatures from current frame, or use ambient temp
  const temperatures = currentFrame?.cells.map((c) => c.temperature_c)

  const handleCellClick = (cellId: number) => {
    updateAbuse({ target_cell: cellId })
  }

  return (
    <>
      {/* Lighting */}
      <ambientLight intensity={0.4} />
      <directionalLight position={[10, 10, 5]} intensity={1} />

      {/* Helpers */}
      <gridHelper args={[20, 20, '#444444', '#222222']} />
      <axesHelper args={[5]} />

      {/* Battery Module */}
      <ModuleViewer
        rows={moduleConfig.rows}
        cols={moduleConfig.cols}
        cellType={moduleConfig.cell_type}
        spacingMm={moduleConfig.spacing_mm}
        temperatures={temperatures}
        selectedCell={abuse.target_cell}
        onCellClick={handleCellClick}
      />

      {/* Camera controls */}
      <OrbitControls
        enableDamping
        dampingFactor={0.05}
        minDistance={2}
        maxDistance={50}
        maxPolarAngle={Math.PI / 2}
      />
    </>
  )
}

export default function Scene() {
  return (
    <Canvas
      camera={{ position: [15, 15, 15], fov: 50 }}
      style={{ background: '#1a1a2e' }}
    >
      <SceneContent />
    </Canvas>
  )
}
