"""Tests for the Simulation class."""

import sys
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import pytest

from models.schemas import (
    AbuseConfig,
    AbuseType,
    CellConfig,
    CellType,
    CoolingConfig,
    ModuleConfig,
    SimulationConfig,
    SolverConfig,
    ThermalRunawayConfig,
)
from models.simulation import Simulation


@pytest.fixture
def default_config() -> SimulationConfig:
    """Create a default simulation config for testing."""
    return SimulationConfig(
        module=ModuleConfig(
            rows=2,
            cols=3,
            cell_type=CellType.cylindrical_21700,
            spacing_mm=2.0,
        ),
        cell=CellConfig(
            chemistry="NMC811",
            capacity_ah=5.0,
            mass_kg=0.07,
            specific_heat=1000.0,
            thermal_resistance=2.0,
        ),
        thermal_runaway=ThermalRunawayConfig(
            onset_temp_c=150.0,
            peak_heat_w=5000.0,
            total_energy_kj=100.0,
            duration_s=30.0,
        ),
        cooling=CoolingConfig(
            coolant_temp_c=25.0,
            htc=50.0,
        ),
        abuse=AbuseConfig(
            type=AbuseType.nail_penetration,
            target_cell=0,
        ),
        solver=SolverConfig(
            time_end_s=10.0,
            dt_s=0.01,
            dt_output_s=0.5,
        ),
    )


class TestSimulation:
    """Tests for Simulation class."""

    def test_simulation_runs_for_10_seconds(self, default_config: SimulationConfig) -> None:
        """Simulation should run for the configured 10 seconds."""
        sim = Simulation(default_config)
        result = sim.run_complete()

        assert result.completed is True
        # Last frame should be at or near 10 seconds
        assert result.frames[-1].time_s >= 9.5
        assert result.frames[-1].time_s <= 10.5

    def test_target_cell_enters_tr(self, default_config: SimulationConfig) -> None:
        """Target cell (cell 0) should enter thermal runaway."""
        sim = Simulation(default_config)
        result = sim.run_complete()

        # Find the target cell state in the final frame
        final_frame = result.frames[-1]
        target_cell_state = next(c for c in final_frame.cells if c.id == 0)

        assert target_cell_state.in_thermal_runaway is True
        assert target_cell_state.tr_start_time is not None

    def test_frames_have_increasing_time(self, default_config: SimulationConfig) -> None:
        """Simulation frames should have strictly increasing timestamps."""
        sim = Simulation(default_config)
        result = sim.run_complete()

        assert len(result.frames) > 1, "Should have multiple frames"

        times = [frame.time_s for frame in result.frames]
        for i in range(1, len(times)):
            assert times[i] > times[i - 1], (
                f"Frame times should increase: frame {i-1} at {times[i-1]}s, "
                f"frame {i} at {times[i]}s"
            )

    def test_at_least_one_propagation_event(self, default_config: SimulationConfig) -> None:
        """At least one TR propagation event should be recorded."""
        sim = Simulation(default_config)
        result = sim.run_complete()

        assert len(result.tr_propagation_events) >= 1, (
            "Should have at least one TR propagation event"
        )

        # The first event should be the abused cell
        first_event = result.tr_propagation_events[0]
        assert first_event.cell_id == 0
        assert first_event.trigger == "nail_penetration"

    def test_generator_yields_frames(self, default_config: SimulationConfig) -> None:
        """The run() generator should yield frames at output intervals."""
        sim = Simulation(default_config)

        frames = list(sim.run())

        # With dt_output_s=0.5 and time_end_s=10.0, expect ~21 frames
        # (initial frame at t=0, then frames at 0.5, 1.0, ..., 10.0)
        assert len(frames) >= 20
        assert frames[0].time_s == 0.0

    def test_cell_temperatures_increase_during_tr(self, default_config: SimulationConfig) -> None:
        """Cell temperatures should increase when TR is active."""
        sim = Simulation(default_config)
        result = sim.run_complete()

        initial_temp = result.frames[0].cells[0].temperature_c
        final_temp = result.frames[-1].cells[0].temperature_c

        # Target cell should heat up significantly
        assert final_temp > initial_temp + 50, (
            f"Target cell should heat up: initial={initial_temp}°C, final={final_temp}°C"
        )
