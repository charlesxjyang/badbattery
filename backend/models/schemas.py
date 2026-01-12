from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class CellType(str, Enum):
    cylindrical_21700 = "cylindrical_21700"
    cylindrical_18650 = "cylindrical_18650"
    prismatic = "prismatic"
    pouch = "pouch"


class CoolingType(str, Enum):
    none = "none"
    bottom_plate = "bottom_plate"
    side_channels = "side_channels"


class AbuseType(str, Enum):
    nail_penetration = "nail_penetration"
    external_heat = "external_heat"
    overcharge = "overcharge"


class ThermalModel(str, Enum):
    lumped = "lumped"
    fem_3d = "fem_3d"


class ModuleConfig(BaseModel):
    rows: int = Field(ge=1, le=20, description="Number of rows in the module")
    cols: int = Field(ge=1, le=20, description="Number of columns in the module")
    cell_type: CellType = Field(description="Type of cell in the module")
    spacing_mm: float = Field(
        ge=0.0, le=50.0, description="Spacing between cells in mm"
    )


class CellConfig(BaseModel):
    chemistry: str = Field(
        default="NMC811", description="Cell chemistry identifier"
    )
    capacity_ah: float = Field(
        ge=0.1, le=500.0, description="Cell capacity in Ah"
    )
    mass_kg: float = Field(
        ge=0.01, le=10.0, description="Cell mass in kg"
    )
    specific_heat: float = Field(
        ge=500.0, le=2000.0, default=1000.0, description="Specific heat in J/(kg·K)"
    )
    thermal_resistance: float = Field(
        ge=0.01, le=100.0, default=1.0, description="Thermal resistance in K/W"
    )


class ThermalRunawayConfig(BaseModel):
    onset_temp_c: float = Field(
        ge=80.0, le=300.0, default=150.0, description="TR onset temperature in °C"
    )
    peak_heat_w: float = Field(
        ge=100.0, le=100000.0, default=5000.0, description="Peak heat generation in W"
    )
    total_energy_kj: float = Field(
        ge=1.0, le=5000.0, default=100.0, description="Total energy released in kJ"
    )
    duration_s: float = Field(
        ge=0.1, le=600.0, default=30.0, description="TR duration in seconds"
    )


class CoolingConfig(BaseModel):
    type: CoolingType = Field(
        default=CoolingType.none, description="Type of cooling system"
    )
    coolant_temp_c: float = Field(
        ge=-40.0, le=60.0, default=25.0, description="Coolant temperature in °C"
    )
    htc: float = Field(
        ge=0.0, le=10000.0, default=50.0, description="Heat transfer coefficient in W/(m²·K)"
    )


class AbuseConfig(BaseModel):
    type: AbuseType = Field(description="Type of abuse scenario")
    target_cell: int = Field(ge=0, description="Index of the cell to abuse")
    short_resistance_mohm: float = Field(
        ge=0.1, le=1000.0, default=10.0, description="Internal short resistance in mΩ"
    )


class SolverConfig(BaseModel):
    thermal_model: ThermalModel = Field(
        default=ThermalModel.lumped, description="Thermal solver model type"
    )
    time_end_s: float = Field(
        ge=1.0, le=3600.0, default=60.0, description="Simulation end time in seconds"
    )
    dt_s: float = Field(
        ge=0.001, le=1.0, default=0.01, description="Solver timestep in seconds"
    )
    dt_output_s: float = Field(
        ge=0.01, le=10.0, default=0.5, description="Output timestep in seconds"
    )


class SimulationConfig(BaseModel):
    module: ModuleConfig
    cell: CellConfig
    thermal_runaway: ThermalRunawayConfig
    cooling: CoolingConfig
    abuse: AbuseConfig
    solver: SolverConfig


class CellState(BaseModel):
    id: int = Field(ge=0, description="Cell index")
    temperature_c: float = Field(description="Current temperature in °C")
    in_thermal_runaway: bool = Field(
        default=False, description="Whether cell is in thermal runaway"
    )
    tr_start_time: Optional[float] = Field(
        default=None, description="Time when TR started in seconds"
    )


class SimulationFrame(BaseModel):
    time_s: float = Field(ge=0.0, description="Simulation time in seconds")
    cells: list[CellState] = Field(description="State of all cells at this time")


class TRPropagationEvent(BaseModel):
    cell_id: int = Field(ge=0, description="Cell that entered TR")
    time_s: float = Field(ge=0.0, description="Time of TR onset")
    trigger: str = Field(description="What triggered TR (abuse, propagation, etc.)")


class SimulationResult(BaseModel):
    config: SimulationConfig = Field(description="Configuration used for simulation")
    frames: list[SimulationFrame] = Field(description="Time series of simulation states")
    tr_propagation_events: list[TRPropagationEvent] = Field(
        default_factory=list, description="List of TR events in chronological order"
    )
    completed: bool = Field(
        default=False, description="Whether simulation completed successfully"
    )
