"""FastAPI application for Battery Safety Simulator."""

from pathlib import Path
from typing import Any, Dict, List

import yaml
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from models.module_geometry import ModuleGeometry
from models.schemas import CellType, ModuleConfig, SimulationConfig, SimulationResult
from models.simulation import Simulation

app = FastAPI(title="Battery Safety Simulator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Path to presets directory
PRESETS_DIR = Path(__file__).parent.parent / "presets"
CELLS_PRESETS_DIR = PRESETS_DIR / "cells"


@app.get("/api/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/api/presets/cells")
async def list_cell_presets() -> List[str]:
    """List available cell preset names.

    Returns:
        List of preset names (without .yaml extension)
    """
    if not CELLS_PRESETS_DIR.exists():
        return []

    presets = []
    for file in CELLS_PRESETS_DIR.glob("*.yaml"):
        presets.append(file.stem)

    return sorted(presets)


@app.get("/api/presets/cells/{name}")
async def get_cell_preset(name: str) -> Dict[str, Any]:
    """Get cell configuration for a specific preset.

    Args:
        name: Preset name (without .yaml extension)

    Returns:
        Cell configuration dictionary from YAML file
    """
    preset_path = CELLS_PRESETS_DIR / f"{name}.yaml"

    if not preset_path.exists():
        raise HTTPException(status_code=404, detail=f"Preset '{name}' not found")

    with open(preset_path) as f:
        preset_data = yaml.safe_load(f)

    return preset_data


@app.post("/api/simulations")
async def run_simulation(config: SimulationConfig) -> SimulationResult:
    """Run a thermal runaway simulation.

    Args:
        config: Complete simulation configuration

    Returns:
        SimulationResult with frames and propagation events
    """
    try:
        sim = Simulation(config)
        result = sim.run_complete()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))


@app.get("/api/module/preview")
async def get_module_preview(
    rows: int = Query(ge=1, le=20, description="Number of rows"),
    cols: int = Query(ge=1, le=20, description="Number of columns"),
    cell_type: CellType = Query(description="Cell type"),
    spacing_mm: float = Query(ge=0.0, le=50.0, description="Cell spacing in mm"),
) -> Dict[str, Any]:
    """Get module geometry for 3D preview.

    Args:
        rows: Number of rows in the module
        cols: Number of columns in the module
        cell_type: Type of cell (cylindrical_21700, cylindrical_18650, prismatic, pouch)
        spacing_mm: Spacing between cells in mm

    Returns:
        Geometry JSON with cell positions, adjacency, and bounds
    """
    config = ModuleConfig(
        rows=rows,
        cols=cols,
        cell_type=cell_type,
        spacing_mm=spacing_mm,
    )

    geometry = ModuleGeometry(config)
    return geometry.to_json()


@app.websocket("/ws/simulation")
async def websocket_simulation(websocket: WebSocket) -> None:
    """WebSocket endpoint for streaming simulation results.

    Protocol:
        1. Client connects
        2. Client sends SimulationConfig as JSON
        3. Server streams SimulationFrame messages as simulation progresses
        4. Server sends final SimulationResult with completed=true

    Message format (server -> client):
        - Progress frames: {"type": "frame", "data": SimulationFrame}
        - Final result: {"type": "result", "data": SimulationResult}
        - Errors: {"type": "error", "message": str}
    """
    await websocket.accept()

    try:
        # Wait for SimulationConfig from client
        config_data = await websocket.receive_json()

        # Validate config
        try:
            config = SimulationConfig(**config_data)
        except ValidationError as e:
            await websocket.send_json({
                "type": "error",
                "message": f"Invalid configuration: {e}"
            })
            await websocket.close(code=1008)
            return

        # Create simulation
        try:
            sim = Simulation(config)
        except ValueError as e:
            await websocket.send_json({
                "type": "error",
                "message": f"Simulation setup error: {e}"
            })
            await websocket.close(code=1008)
            return
        except NotImplementedError as e:
            await websocket.send_json({
                "type": "error",
                "message": f"Not implemented: {e}"
            })
            await websocket.close(code=1008)
            return

        # Run simulation, streaming frames
        for frame in sim.run():
            await websocket.send_json({
                "type": "frame",
                "data": frame.model_dump()
            })

        # Send final result
        result = sim.get_result()
        await websocket.send_json({
            "type": "result",
            "data": result.model_dump()
        })

    except WebSocketDisconnect:
        # Client disconnected - graceful handling
        pass
    except Exception as e:
        # Unexpected error - try to notify client before closing
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"Simulation error: {e}"
            })
        except Exception:
            pass  # Client may already be disconnected
        await websocket.close(code=1011)
