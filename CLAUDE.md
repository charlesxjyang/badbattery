# EV Battery Module Safety Simulator

## Project Overview

Multiphysics simulator for thermal runaway propagation in EV battery modules. Users configure module geometry, cell properties, and abuse scenarios, then run simulations to predict whether thermal runaway cascades through the module.

## Architecture

```
battery-safety-sim/
├── backend/                 # Python - simulation engine
│   ├── api/                 # FastAPI routes
│   ├── models/              # Physics models
│   │   ├── thermal.py       # Heat conduction (scikit-fem)
│   │   ├── electrochemical.py  # PyBaMM wrapper
│   │   ├── thermal_runaway.py  # Arrhenius kinetics
│   │   └── module.py        # Cell-to-cell coupling
│   ├── solvers/             # Numerical solvers
│   ├── presets/             # Cell/chemistry presets (YAML)
│   └── utils/               # Mesh generation, data export
├── frontend/                # React + Three.js - visualization
│   ├── components/
│   │   ├── ModuleConfigurator/  # 3D cell arrangement editor
│   │   ├── ParameterPanel/      # Input forms
│   │   ├── SimulationViewer/    # Results visualization
│   │   └── Charts/              # Time-series plots
│   ├── hooks/               # WebSocket, simulation state
│   └── utils/               # Geometry helpers, data transforms
├── shared/                  # Shared types/schemas
│   └── schemas/             # JSON schemas for API contracts
└── docs/                    # Technical documentation
```

## Tech Stack

### Backend (Python)
- **FastAPI** - API server with WebSocket support for live updates
- **PyBaMM** - Electrochemical cell models
- **scikit-fem** - 3D thermal finite element solver
- **gmsh** - Mesh generation (Python bindings)
- **NumPy/SciPy** - Numerical operations
- **Pydantic** - Data validation, matches frontend schemas

### Frontend (TypeScript/React)
- **React 18** with TypeScript
- **Three.js** via React Three Fiber (@react-three/fiber)
- **@react-three/drei** - Three.js helpers
- **Zustand** - State management
- **D3.js** or **Recharts** - Time-series charts
- **Tailwind CSS** - Styling
- **Vite** - Build tool

## Key Design Decisions

### Simulation runs on backend only
All physics computation happens in Python. Frontend is purely visualization and configuration. No Pyodide or in-browser simulation.

### WebSocket for live updates
Simulation progress and intermediate results stream to frontend via WebSocket. User sees temperature evolution in real-time, not just final results.

### Lumped thermal model first
Start with each cell as a single thermal node connected by thermal resistances. This runs in seconds and demonstrates core functionality. 3D FEM (scikit-fem) is optional "high fidelity" mode.

### Empirical gaps as explicit parameters
Internal short resistance, vent gas composition, and TR kinetics are user inputs with sensible defaults from literature presets. Don't hide uncertain physics in code.

### Clean solver abstraction
```python
class ThermalSolver(Protocol):
    def set_heat_sources(self, sources: dict[int, float]) -> None: ...
    def solve_timestep(self, dt: float) -> dict[int, float]: ...
```
Implementations can be swapped (lumped network, scikit-fem, eventually OpenFOAM) without changing simulation logic.

## Development Commands

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -e ".[dev]"

# Run API server
uvicorn api.main:app --reload --port 8000

# Run tests
pytest

# Type checking
mypy .
```

### Frontend
```bash
cd frontend
npm install

# Dev server
npm run dev  # runs on port 5173

# Type checking
npm run typecheck

# Linting
npm run lint
```

### Full stack local dev
Run backend on :8000 and frontend on :5173. Frontend proxies API requests to backend (configured in vite.config.ts).

## API Design

### REST Endpoints
- `GET /api/presets/cells` - List available cell presets
- `GET /api/presets/chemistries` - List chemistry presets
- `POST /api/simulations` - Create new simulation job
- `GET /api/simulations/{id}` - Get simulation status/results
- `DELETE /api/simulations/{id}` - Cancel running simulation

### WebSocket
- `ws://localhost:8000/ws/simulation/{id}` - Live simulation updates

### Simulation Config Schema
```typescript
interface SimulationConfig {
  module: {
    rows: number;
    cols: number;
    cellType: 'cylindrical_21700' | 'cylindrical_18650' | 'prismatic' | 'pouch';
    spacingMm: number;
  };
  cell: {
    chemistry: string;
    capacityAh: number;
    // ... or preset name
  };
  thermalRunaway: {
    modelType: 'single_step' | 'multi_step' | 'empirical_curve';
    // ... model-specific params
  };
  cooling: {
    type: 'none' | 'bottom_plate' | 'side_channels';
    coolantTempC: number;
    flowRateLpm: number;
  };
  abuse: {
    type: 'nail_penetration' | 'external_heat' | 'overcharge';
    targetCell: number;
    // ... abuse-specific params
  };
  solver: {
    thermalModel: 'lumped' | 'fem_3d';
    timeEndS: number;
    dtOutputS: number;
  };
}
```

## Frontend Component Guidelines

### 3D Visualization (Three.js)
- Use React Three Fiber, not raw Three.js
- Geometries: `BoxGeometry` for prismatic, `CylinderGeometry` for cylindrical cells
- Color mapping: temperature → color via custom shader or vertex colors
- Keep draw calls low: instanced meshes for identical cells
- OrbitControls for camera, but constrain to sensible bounds

### Module Configurator
- Click cell to select as abuse target
- Hover shows cell ID and current temperature (during results view)
- Drag to rotate, scroll to zoom
- Grid helper and axis indicators for orientation

### Parameter Forms
- Group logically: Module → Cell → Thermal Runaway → Cooling → Abuse → Solver
- Collapsible sections, most common params visible by default
- Preset dropdowns that populate multiple fields
- Validation feedback inline, not blocking
- "Advanced" expandable sections for expert params

### Results Visualization
- Time slider controls animation playback
- Play/pause/speed controls
- Temperature color scale with legend (25°C blue → 400°C red)
- Line chart: T(t) for each cell, with TR threshold line
- Event markers: "Cell 3 entered TR at t=8.2s"
- Export buttons: PNG snapshot, GIF animation, CSV data

## Code Style

### Python
- Type hints everywhere
- Pydantic models for all API data
- `ruff` for linting and formatting
- Docstrings for public functions (Google style)
- Tests in `tests/` mirroring source structure

### TypeScript
- Strict mode enabled
- Explicit return types on functions
- Props interfaces for all components
- Prefer `const` and immutable patterns
- CSS via Tailwind utility classes, no CSS files

## Performance Targets

- Module preview: 60fps with up to 100 cells
- Lumped simulation (12 cells, 60s): < 5 seconds
- FEM simulation (12 cells, 60s): < 2 minutes
- Results animation: 60fps playback
- WebSocket latency: < 100ms for progress updates

## Testing Strategy

### Backend
- Unit tests for physics models (known analytical solutions)
- Integration tests for API endpoints
- Validation against published TR propagation data

### Frontend
- Component tests with React Testing Library
- Visual regression tests for 3D views (optional, low priority)
- E2E tests with Playwright for critical flows (configure → run → view results)

## Future Extensions (Not MVP)

- Mechanical abuse simulation (CalculiX integration)
- Full CFD cooling (OpenFOAM via Docker)
- Vent gas dispersion and flammability
- Parameter sweeps and optimization
- Cloud deployment with job queue
- Multi-user support and saved configurations
- PDF report generation
