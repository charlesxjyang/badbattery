"""Battery module thermal runaway simulation.

Coordinates thermal solver, TR models, and geometry to simulate
thermal runaway propagation through a battery module.
"""

from typing import Generator, List, Optional

from models.module_geometry import ModuleGeometry
from models.schemas import (
    AbuseType,
    CellState,
    SimulationConfig,
    SimulationFrame,
    SimulationResult,
    ThermalModel,
    TRPropagationEvent,
)
from models.thermal_runaway import ThermalRunawayModel
from solvers.thermal_lumped import LumpedThermalSolver


class Simulation:
    """Thermal runaway propagation simulation for battery modules.

    Coordinates geometry, thermal solver, and per-cell TR models to
    simulate heat propagation and cascading thermal runaway events.

    Args:
        config: SimulationConfig with module, cell, TR, cooling, abuse, solver params
    """

    def __init__(self, config: SimulationConfig) -> None:
        self.config = config

        # Initialize geometry
        self.geometry = ModuleGeometry(config.module)
        self.n_cells = self.geometry.n_cells

        # Initialize thermal solver
        if config.solver.thermal_model == ThermalModel.fem_3d:
            raise NotImplementedError("FEM 3D solver not yet implemented")

        self._init_thermal_solver()

        # Initialize TR model for each cell
        self.tr_models: List[ThermalRunawayModel] = [
            ThermalRunawayModel(
                onset_temp_c=config.thermal_runaway.onset_temp_c,
                peak_heat_w=config.thermal_runaway.peak_heat_w,
                total_energy_kj=config.thermal_runaway.total_energy_kj,
                duration_s=config.thermal_runaway.duration_s,
            )
            for _ in range(self.n_cells)
        ]

        # Simulation state
        self.current_time = 0.0
        self.tr_events: List[TRPropagationEvent] = []
        self.frames: List[SimulationFrame] = []
        self._completed = False
        self._abused = False

    def _init_thermal_solver(self) -> None:
        """Initialize the lumped thermal solver."""
        cell_config = self.config.cell
        cooling_config = self.config.cooling

        # Compute ambient HTC based on cooling type
        # For simplicity, use htc directly as W/K per cell
        ambient_htc = cooling_config.htc * 0.01  # Scale factor for per-cell

        self.thermal_solver = LumpedThermalSolver(
            n_cells=self.n_cells,
            cell_mass_kg=cell_config.mass_kg,
            cell_cp_j_kg_k=cell_config.specific_heat,
            cell_to_cell_r_k_w=cell_config.thermal_resistance,
            ambient_temp_c=cooling_config.coolant_temp_c,
            ambient_htc_w_k=ambient_htc,
        )

        # Set adjacency from geometry
        adjacency_pairs = self.geometry.get_adjacency_pairs()
        self.thermal_solver.set_adjacency(adjacency_pairs)

    def _apply_initial_abuse(self) -> None:
        """Apply initial abuse condition to target cell."""
        if self._abused:
            return

        abuse = self.config.abuse
        target = abuse.target_cell

        if target >= self.n_cells:
            raise ValueError(
                f"Target cell {target} exceeds module size {self.n_cells}"
            )

        if abuse.type == AbuseType.nail_penetration:
            # Nail penetration triggers immediate TR
            self.tr_models[target].check_trigger(
                temperature_c=self.config.thermal_runaway.onset_temp_c,
                current_time_s=self.current_time,
            )
            self.tr_events.append(
                TRPropagationEvent(
                    cell_id=target,
                    time_s=self.current_time,
                    trigger="nail_penetration",
                )
            )

        elif abuse.type == AbuseType.external_heat:
            # External heat applies constant heat source until TR triggers
            # Heat power based on short resistance (simplified model)
            heat_power = 1000.0  # W, could be computed from config
            self.thermal_solver.set_heat_source(target, heat_power)

        elif abuse.type == AbuseType.overcharge:
            # Overcharge generates heat, eventually triggering TR
            heat_power = 500.0  # W, simplified
            self.thermal_solver.set_heat_source(target, heat_power)

        self._abused = True

    def _update_heat_sources(self) -> None:
        """Update heat sources from TR models."""
        for cell_id, tr_model in enumerate(self.tr_models):
            if tr_model.triggered:
                heat = tr_model.get_heat_generation(self.current_time)
                self.thermal_solver.set_heat_source(cell_id, heat)

    def _check_tr_triggers(self) -> None:
        """Check if any cells should enter TR based on temperature."""
        temperatures = self.thermal_solver.get_temperatures()

        for cell_id, tr_model in enumerate(self.tr_models):
            if not tr_model.triggered:
                triggered = tr_model.check_trigger(
                    temperature_c=temperatures[cell_id],
                    current_time_s=self.current_time,
                )
                if triggered:
                    self.tr_events.append(
                        TRPropagationEvent(
                            cell_id=cell_id,
                            time_s=self.current_time,
                            trigger="thermal_propagation",
                        )
                    )

    def _create_frame(self) -> SimulationFrame:
        """Create a simulation frame with current state."""
        temperatures = self.thermal_solver.get_temperatures()

        cells = [
            CellState(
                id=cell_id,
                temperature_c=float(temperatures[cell_id]),
                in_thermal_runaway=self.tr_models[cell_id].triggered,
                tr_start_time=self.tr_models[cell_id].trigger_time,
            )
            for cell_id in range(self.n_cells)
        ]

        return SimulationFrame(time_s=self.current_time, cells=cells)

    def run(self) -> Generator[SimulationFrame, None, None]:
        """Run simulation, yielding frames at output intervals.

        Yields:
            SimulationFrame at each dt_output_s interval
        """
        solver_config = self.config.solver
        dt = solver_config.dt_s
        dt_output = solver_config.dt_output_s
        t_end = solver_config.time_end_s

        # Apply initial abuse
        self._apply_initial_abuse()

        # Yield initial frame
        frame = self._create_frame()
        self.frames.append(frame)
        yield frame

        next_output_time = dt_output

        while self.current_time < t_end:
            # Update heat sources from TR models
            self._update_heat_sources()

            # Advance thermal solution
            self.thermal_solver.solve_timestep(dt)
            self.current_time += dt

            # Check for new TR triggers
            self._check_tr_triggers()

            # Output frame at intervals
            if self.current_time >= next_output_time:
                frame = self._create_frame()
                self.frames.append(frame)
                yield frame
                next_output_time += dt_output

        # Final frame if not already at output time
        if self.current_time > self.frames[-1].time_s + dt:
            frame = self._create_frame()
            self.frames.append(frame)
            yield frame

        self._completed = True

    def run_complete(self) -> SimulationResult:
        """Run simulation to completion and return result.

        Returns:
            SimulationResult with all frames and events
        """
        # Consume the generator
        for _ in self.run():
            pass

        return self.get_result()

    def get_result(self) -> SimulationResult:
        """Get simulation result after run completes.

        Returns:
            SimulationResult with config, frames, TR events, completion status
        """
        return SimulationResult(
            config=self.config,
            frames=self.frames,
            tr_propagation_events=self.tr_events,
            completed=self._completed,
        )

    @property
    def completed(self) -> bool:
        """Whether simulation has completed."""
        return self._completed

    def get_tr_count(self) -> int:
        """Get count of cells that have entered TR."""
        return sum(1 for tr in self.tr_models if tr.triggered)

    def get_temperatures(self) -> List[float]:
        """Get current temperatures of all cells."""
        return self.thermal_solver.get_temperatures().tolist()
