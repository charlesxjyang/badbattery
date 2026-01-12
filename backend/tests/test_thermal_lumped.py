"""Tests for lumped parameter thermal solver."""

import numpy as np
import pytest

from solvers.thermal_lumped import LumpedThermalSolver


class TestNoHeatSource:
    """Test that temperatures remain at ambient with no heat input."""

    def test_temperatures_stay_at_ambient(self):
        solver = LumpedThermalSolver(
            n_cells=4,
            cell_mass_kg=0.07,
            cell_cp_j_kg_k=1000.0,
            cell_to_cell_r_k_w=1.0,
            ambient_temp_c=25.0,
            ambient_htc_w_k=0.5,
        )
        solver.set_adjacency_from_grid(2, 2)

        initial_temps = solver.get_temperatures()
        assert np.allclose(initial_temps, 25.0)

        # Run 100 timesteps
        for _ in range(100):
            solver.solve_timestep(0.1)

        final_temps = solver.get_temperatures()
        assert np.allclose(final_temps, 25.0, atol=1e-10)

    def test_uniform_elevated_temp_decays_to_ambient(self):
        """All cells at elevated temp should decay toward ambient."""
        solver = LumpedThermalSolver(
            n_cells=4,
            cell_mass_kg=0.07,
            cell_cp_j_kg_k=1000.0,
            cell_to_cell_r_k_w=1.0,
            ambient_temp_c=25.0,
            ambient_htc_w_k=5.0,  # Higher HTC for faster convergence
        )
        solver.set_adjacency_from_grid(2, 2)
        solver.set_temperatures([50.0, 50.0, 50.0, 50.0])

        # Run simulation (longer for convergence)
        for _ in range(5000):
            solver.solve_timestep(0.1)

        final_temps = solver.get_temperatures()
        # Should approach ambient
        assert np.allclose(final_temps, 25.0, atol=0.1)


class TestHeatSourceHeating:
    """Test that heat sources cause appropriate temperature changes."""

    def test_single_cell_heats_up(self):
        solver = LumpedThermalSolver(
            n_cells=4,
            cell_mass_kg=0.07,
            cell_cp_j_kg_k=1000.0,
            cell_to_cell_r_k_w=5.0,  # High resistance = less heat transfer
            ambient_temp_c=25.0,
            ambient_htc_w_k=0.1,  # Low ambient loss
        )
        solver.set_adjacency_from_grid(2, 2)

        # Apply heat to cell 0
        solver.set_heat_source(0, 100.0)  # 100W

        # Run for a short time
        for _ in range(100):
            solver.solve_timestep(0.01)

        temps = solver.get_temperatures()

        # Heated cell should be hottest
        assert temps[0] > temps[1]
        assert temps[0] > temps[2]
        assert temps[0] > temps[3]
        assert temps[0] > 25.0

    def test_neighbors_warm_slightly(self):
        """Adjacent cells should warm up due to conduction."""
        solver = LumpedThermalSolver(
            n_cells=9,
            cell_mass_kg=0.07,
            cell_cp_j_kg_k=1000.0,
            cell_to_cell_r_k_w=1.0,
            ambient_temp_c=25.0,
            ambient_htc_w_k=0.1,
        )
        # 3x3 grid:
        # 0 1 2
        # 3 4 5
        # 6 7 8
        solver.set_adjacency_from_grid(3, 3)

        # Heat center cell (4)
        solver.set_heat_source(4, 100.0)

        for _ in range(200):
            solver.solve_timestep(0.01)

        temps = solver.get_temperatures()

        # Center cell hottest
        assert temps[4] > temps[1]  # neighbors
        assert temps[4] > temps[3]
        assert temps[4] > temps[5]
        assert temps[4] > temps[7]

        # Direct neighbors warmer than corners
        direct_neighbors = [temps[1], temps[3], temps[5], temps[7]]
        corners = [temps[0], temps[2], temps[6], temps[8]]

        assert min(direct_neighbors) > max(corners)

        # All cells above ambient
        assert all(t > 25.0 for t in temps)

    def test_clear_heat_sources(self):
        solver = LumpedThermalSolver(
            n_cells=4,
            cell_mass_kg=0.07,
            cell_cp_j_kg_k=1000.0,
            cell_to_cell_r_k_w=1.0,
            ambient_temp_c=25.0,
            ambient_htc_w_k=0.5,
        )
        solver.set_heat_source(0, 100.0)
        solver.set_heat_source(1, 50.0)

        solver.clear_heat_sources()

        # Verify heat sources are cleared
        assert np.allclose(solver.heat_sources, 0.0)


class TestEnergyConservation:
    """Test energy conservation in the thermal solver."""

    def test_energy_input_equals_temperature_rise(self):
        """Energy added should equal thermal mass * temperature rise."""
        solver = LumpedThermalSolver(
            n_cells=1,
            cell_mass_kg=0.1,
            cell_cp_j_kg_k=1000.0,
            cell_to_cell_r_k_w=1.0,
            ambient_temp_c=25.0,
            ambient_htc_w_k=0.0,  # No ambient loss for clean test
        )

        initial_temp = solver.get_temperatures()[0]
        power_w = 50.0
        solver.set_heat_source(0, power_w)

        dt = 0.01
        n_steps = 100
        total_time = dt * n_steps

        for _ in range(n_steps):
            solver.solve_timestep(dt)

        final_temp = solver.get_temperatures()[0]

        # Energy added = Power * time
        energy_added = power_w * total_time

        # Expected temperature rise = Energy / (mass * cp)
        thermal_mass = 0.1 * 1000.0
        expected_delta_t = energy_added / thermal_mass

        actual_delta_t = final_temp - initial_temp

        assert np.isclose(actual_delta_t, expected_delta_t, rtol=1e-6)

    def test_isolated_system_energy_conservation(self):
        """Total energy in isolated system should be conserved."""
        solver = LumpedThermalSolver(
            n_cells=4,
            cell_mass_kg=0.1,
            cell_cp_j_kg_k=1000.0,
            cell_to_cell_r_k_w=0.1,  # Lower resistance = faster heat transfer
            ambient_temp_c=25.0,
            ambient_htc_w_k=0.0,  # Isolated from ambient
        )
        solver.set_adjacency_from_grid(2, 2)

        # Set non-uniform initial temperatures
        solver.set_temperatures([100.0, 25.0, 25.0, 25.0])

        thermal_mass = 0.1 * 1000.0  # per cell

        def total_energy():
            temps = solver.get_temperatures()
            # Energy relative to 0°C reference
            return sum(thermal_mass * t for t in temps)

        initial_energy = total_energy()

        # Run simulation - heat should redistribute but total energy conserve
        for _ in range(10000):
            solver.solve_timestep(0.01)

        final_energy = total_energy()

        # Energy should be conserved (no ambient loss)
        assert np.isclose(initial_energy, final_energy, rtol=1e-6)

        # Temperatures should equilibrate
        final_temps = solver.get_temperatures()
        expected_equilibrium = (100.0 + 25.0 + 25.0 + 25.0) / 4.0
        assert np.allclose(final_temps, expected_equilibrium, atol=0.1)

    def test_steady_state_with_ambient_loss(self):
        """With constant heat input and ambient loss, should reach steady state."""
        solver = LumpedThermalSolver(
            n_cells=1,
            cell_mass_kg=0.1,
            cell_cp_j_kg_k=1000.0,
            cell_to_cell_r_k_w=1.0,
            ambient_temp_c=25.0,
            ambient_htc_w_k=2.0,  # W/K
        )

        power_w = 10.0
        solver.set_heat_source(0, power_w)

        # Run to steady state (longer simulation)
        for _ in range(20000):
            solver.solve_timestep(0.01)

        final_temp = solver.get_temperatures()[0]

        # At steady state: Q_in = Q_out
        # power = htc * (T - T_ambient)
        # T = T_ambient + power / htc
        expected_temp = 25.0 + power_w / 2.0  # = 30.0

        assert np.isclose(final_temp, expected_temp, atol=0.1)


class TestAdjacency:
    """Test adjacency setup methods."""

    def test_manual_adjacency(self):
        solver = LumpedThermalSolver(
            n_cells=3,
            cell_mass_kg=0.1,
            cell_cp_j_kg_k=1000.0,
            cell_to_cell_r_k_w=1.0,
            ambient_temp_c=25.0,
            ambient_htc_w_k=0.5,
        )

        # Linear chain: 0 - 1 - 2
        solver.set_adjacency([(0, 1), (1, 2)])

        assert solver.adjacency[0, 1] == 1.0
        assert solver.adjacency[1, 0] == 1.0
        assert solver.adjacency[1, 2] == 1.0
        assert solver.adjacency[2, 1] == 1.0
        assert solver.adjacency[0, 2] == 0.0  # Not adjacent

    def test_grid_adjacency(self):
        solver = LumpedThermalSolver(
            n_cells=6,
            cell_mass_kg=0.1,
            cell_cp_j_kg_k=1000.0,
            cell_to_cell_r_k_w=1.0,
            ambient_temp_c=25.0,
            ambient_htc_w_k=0.5,
        )
        # 2x3 grid:
        # 0 1 2
        # 3 4 5
        solver.set_adjacency_from_grid(2, 3)

        # Check horizontal connections
        assert solver.adjacency[0, 1] == 1.0
        assert solver.adjacency[1, 2] == 1.0
        assert solver.adjacency[3, 4] == 1.0
        assert solver.adjacency[4, 5] == 1.0

        # Check vertical connections
        assert solver.adjacency[0, 3] == 1.0
        assert solver.adjacency[1, 4] == 1.0
        assert solver.adjacency[2, 5] == 1.0

        # Check non-connections
        assert solver.adjacency[0, 2] == 0.0  # Not adjacent
        assert solver.adjacency[0, 4] == 0.0  # Diagonal
        assert solver.adjacency[3, 5] == 0.0  # Not adjacent


class TestStability:
    """Test numerical stability helpers."""

    def test_max_stable_timestep(self):
        solver = LumpedThermalSolver(
            n_cells=4,
            cell_mass_kg=0.1,
            cell_cp_j_kg_k=1000.0,
            cell_to_cell_r_k_w=1.0,
            ambient_temp_c=25.0,
            ambient_htc_w_k=1.0,
        )
        solver.set_adjacency_from_grid(2, 2)

        max_dt = solver.get_max_stable_timestep()

        # Should be positive and reasonable
        assert max_dt > 0
        assert max_dt < 100  # Sanity check

        # Simulation should be stable with this timestep
        solver.set_temperatures([100.0, 25.0, 25.0, 25.0])
        for _ in range(100):
            temps = solver.solve_timestep(max_dt * 0.9)
            # No NaN or extreme values
            assert not np.any(np.isnan(temps))
            assert np.all(temps > -100)
            assert np.all(temps < 500)
