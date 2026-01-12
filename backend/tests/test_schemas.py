"""Tests for Pydantic schema validation."""

import pytest
from pydantic import ValidationError

from models.schemas import (
    AbuseConfig,
    AbuseType,
    CellConfig,
    CellState,
    CellType,
    CoolingConfig,
    CoolingType,
    ModuleConfig,
    SimulationConfig,
    SimulationFrame,
    SimulationResult,
    SolverConfig,
    ThermalModel,
    ThermalRunawayConfig,
    TRPropagationEvent,
)


class TestDefaultConfigs:
    """Test that configs with defaults can be created."""

    def test_cell_config_defaults(self):
        config = CellConfig(capacity_ah=5.0, mass_kg=0.07)
        assert config.chemistry == "NMC811"
        assert config.specific_heat == 1000.0
        assert config.thermal_resistance == 1.0

    def test_thermal_runaway_config_defaults(self):
        config = ThermalRunawayConfig()
        assert config.onset_temp_c == 150.0
        assert config.peak_heat_w == 5000.0
        assert config.total_energy_kj == 100.0
        assert config.duration_s == 30.0

    def test_cooling_config_defaults(self):
        config = CoolingConfig()
        assert config.type == CoolingType.none
        assert config.coolant_temp_c == 25.0
        assert config.htc == 50.0

    def test_abuse_config_defaults(self):
        config = AbuseConfig(type=AbuseType.nail_penetration, target_cell=0)
        assert config.short_resistance_mohm == 10.0

    def test_solver_config_defaults(self):
        config = SolverConfig()
        assert config.thermal_model == ThermalModel.lumped
        assert config.time_end_s == 60.0
        assert config.dt_s == 0.01
        assert config.dt_output_s == 0.5


class TestCustomConfigs:
    """Test configs with custom values."""

    def test_module_config_custom(self):
        config = ModuleConfig(
            rows=4,
            cols=3,
            cell_type=CellType.cylindrical_21700,
            spacing_mm=2.5,
        )
        assert config.rows == 4
        assert config.cols == 3
        assert config.cell_type == CellType.cylindrical_21700
        assert config.spacing_mm == 2.5

    def test_cell_config_custom(self):
        config = CellConfig(
            chemistry="LFP",
            capacity_ah=100.0,
            mass_kg=2.0,
            specific_heat=1200.0,
            thermal_resistance=0.5,
        )
        assert config.chemistry == "LFP"
        assert config.capacity_ah == 100.0
        assert config.mass_kg == 2.0
        assert config.specific_heat == 1200.0
        assert config.thermal_resistance == 0.5

    def test_cooling_config_custom(self):
        config = CoolingConfig(
            type=CoolingType.bottom_plate,
            coolant_temp_c=15.0,
            htc=500.0,
        )
        assert config.type == CoolingType.bottom_plate
        assert config.coolant_temp_c == 15.0
        assert config.htc == 500.0

    def test_full_simulation_config(self):
        config = SimulationConfig(
            module=ModuleConfig(
                rows=3,
                cols=4,
                cell_type=CellType.prismatic,
                spacing_mm=1.0,
            ),
            cell=CellConfig(
                chemistry="NMC622",
                capacity_ah=50.0,
                mass_kg=1.0,
            ),
            thermal_runaway=ThermalRunawayConfig(
                onset_temp_c=180.0,
                peak_heat_w=10000.0,
            ),
            cooling=CoolingConfig(type=CoolingType.side_channels),
            abuse=AbuseConfig(
                type=AbuseType.external_heat,
                target_cell=5,
            ),
            solver=SolverConfig(
                thermal_model=ThermalModel.fem_3d,
                time_end_s=120.0,
            ),
        )
        assert config.module.rows == 3
        assert config.cell.chemistry == "NMC622"
        assert config.thermal_runaway.onset_temp_c == 180.0
        assert config.cooling.type == CoolingType.side_channels
        assert config.abuse.target_cell == 5
        assert config.solver.thermal_model == ThermalModel.fem_3d


class TestValidationErrors:
    """Test that out-of-bounds values raise ValidationError."""

    def test_module_rows_too_low(self):
        with pytest.raises(ValidationError) as exc_info:
            ModuleConfig(rows=0, cols=1, cell_type=CellType.pouch, spacing_mm=1.0)
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_module_rows_too_high(self):
        with pytest.raises(ValidationError) as exc_info:
            ModuleConfig(rows=25, cols=1, cell_type=CellType.pouch, spacing_mm=1.0)
        assert "less than or equal to 20" in str(exc_info.value)

    def test_module_spacing_negative(self):
        with pytest.raises(ValidationError) as exc_info:
            ModuleConfig(rows=2, cols=2, cell_type=CellType.pouch, spacing_mm=-1.0)
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_cell_capacity_too_low(self):
        with pytest.raises(ValidationError) as exc_info:
            CellConfig(capacity_ah=0.05, mass_kg=0.1)
        assert "greater than or equal to 0.1" in str(exc_info.value)

    def test_cell_capacity_too_high(self):
        with pytest.raises(ValidationError) as exc_info:
            CellConfig(capacity_ah=600.0, mass_kg=0.1)
        assert "less than or equal to 500" in str(exc_info.value)

    def test_cell_mass_too_low(self):
        with pytest.raises(ValidationError) as exc_info:
            CellConfig(capacity_ah=5.0, mass_kg=0.001)
        assert "greater than or equal to 0.01" in str(exc_info.value)

    def test_thermal_runaway_onset_too_low(self):
        with pytest.raises(ValidationError) as exc_info:
            ThermalRunawayConfig(onset_temp_c=50.0)
        assert "greater than or equal to 80" in str(exc_info.value)

    def test_thermal_runaway_onset_too_high(self):
        with pytest.raises(ValidationError) as exc_info:
            ThermalRunawayConfig(onset_temp_c=350.0)
        assert "less than or equal to 300" in str(exc_info.value)

    def test_cooling_temp_too_low(self):
        with pytest.raises(ValidationError) as exc_info:
            CoolingConfig(coolant_temp_c=-50.0)
        assert "greater than or equal to -40" in str(exc_info.value)

    def test_cooling_temp_too_high(self):
        with pytest.raises(ValidationError) as exc_info:
            CoolingConfig(coolant_temp_c=100.0)
        assert "less than or equal to 60" in str(exc_info.value)

    def test_abuse_target_cell_negative(self):
        with pytest.raises(ValidationError) as exc_info:
            AbuseConfig(type=AbuseType.nail_penetration, target_cell=-1)
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_solver_time_end_too_low(self):
        with pytest.raises(ValidationError) as exc_info:
            SolverConfig(time_end_s=0.5)
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_solver_dt_too_small(self):
        with pytest.raises(ValidationError) as exc_info:
            SolverConfig(dt_s=0.0001)
        assert "greater than or equal to 0.001" in str(exc_info.value)


class TestResultSchemas:
    """Test result and state schemas."""

    def test_cell_state(self):
        state = CellState(id=0, temperature_c=25.0)
        assert state.id == 0
        assert state.temperature_c == 25.0
        assert state.in_thermal_runaway is False
        assert state.tr_start_time is None

    def test_cell_state_in_tr(self):
        state = CellState(
            id=3,
            temperature_c=200.0,
            in_thermal_runaway=True,
            tr_start_time=8.5,
        )
        assert state.in_thermal_runaway is True
        assert state.tr_start_time == 8.5

    def test_simulation_frame(self):
        frame = SimulationFrame(
            time_s=10.0,
            cells=[
                CellState(id=0, temperature_c=30.0),
                CellState(id=1, temperature_c=35.0),
            ],
        )
        assert frame.time_s == 10.0
        assert len(frame.cells) == 2
        assert frame.cells[1].temperature_c == 35.0

    def test_tr_propagation_event(self):
        event = TRPropagationEvent(
            cell_id=5,
            time_s=12.3,
            trigger="propagation from cell 4",
        )
        assert event.cell_id == 5
        assert event.time_s == 12.3
        assert event.trigger == "propagation from cell 4"

    def test_simulation_result(self):
        config = SimulationConfig(
            module=ModuleConfig(
                rows=2, cols=2, cell_type=CellType.cylindrical_18650, spacing_mm=1.0
            ),
            cell=CellConfig(capacity_ah=3.0, mass_kg=0.05),
            thermal_runaway=ThermalRunawayConfig(),
            cooling=CoolingConfig(),
            abuse=AbuseConfig(type=AbuseType.nail_penetration, target_cell=0),
            solver=SolverConfig(),
        )
        result = SimulationResult(
            config=config,
            frames=[
                SimulationFrame(
                    time_s=0.0,
                    cells=[CellState(id=i, temperature_c=25.0) for i in range(4)],
                ),
            ],
            tr_propagation_events=[
                TRPropagationEvent(cell_id=0, time_s=5.0, trigger="abuse"),
            ],
            completed=True,
        )
        assert result.completed is True
        assert len(result.frames) == 1
        assert len(result.tr_propagation_events) == 1
        assert result.config.module.rows == 2
