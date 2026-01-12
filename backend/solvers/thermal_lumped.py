"""Lumped parameter thermal network solver for battery modules.

Each cell is modeled as a single thermal node with:
- Thermal mass (m * cp)
- Conductive coupling to adjacent cells via thermal resistance
- Convective loss to ambient environment
"""

from typing import List, Tuple, Union

import numpy as np
from numpy.typing import NDArray


class LumpedThermalSolver:
    """Explicit Euler solver for lumped thermal network.

    Args:
        n_cells: Number of cells in the module
        cell_mass_kg: Mass of each cell in kg
        cell_cp_j_kg_k: Specific heat capacity in J/(kg·K)
        cell_to_cell_r_k_w: Thermal resistance between adjacent cells in K/W
        ambient_temp_c: Ambient temperature in °C
        ambient_htc_w_k: Heat transfer coefficient to ambient in W/K
    """

    def __init__(
        self,
        n_cells: int,
        cell_mass_kg: float,
        cell_cp_j_kg_k: float,
        cell_to_cell_r_k_w: float,
        ambient_temp_c: float,
        ambient_htc_w_k: float,
    ) -> None:
        self.n_cells = n_cells
        self.cell_mass_kg = cell_mass_kg
        self.cell_cp_j_kg_k = cell_cp_j_kg_k
        self.cell_to_cell_r_k_w = cell_to_cell_r_k_w
        self.ambient_temp_c = ambient_temp_c
        self.ambient_htc_w_k = ambient_htc_w_k

        # Thermal mass for each cell (J/K)
        self.thermal_mass = cell_mass_kg * cell_cp_j_kg_k

        # Conductance between adjacent cells (W/K)
        self.cell_to_cell_conductance = (
            1.0 / cell_to_cell_r_k_w if cell_to_cell_r_k_w > 0 else 0.0
        )

        # Initialize temperatures to ambient
        self.temperatures: NDArray[np.float64] = np.full(
            n_cells, ambient_temp_c, dtype=np.float64
        )

        # Heat sources for each cell (W)
        self.heat_sources: NDArray[np.float64] = np.zeros(n_cells, dtype=np.float64)

        # Adjacency matrix: adjacency[i, j] = 1 if cells i and j are neighbors
        self.adjacency: NDArray[np.float64] = np.zeros(
            (n_cells, n_cells), dtype=np.float64
        )

    def set_adjacency(self, adjacency: List[Tuple[int, int]]) -> None:
        """Set cell-to-cell adjacency relationships.

        Args:
            adjacency: List of (cell_i, cell_j) tuples indicating neighboring cells.
                       Connections are symmetric (i->j implies j->i).
        """
        self.adjacency.fill(0)
        for i, j in adjacency:
            if 0 <= i < self.n_cells and 0 <= j < self.n_cells and i != j:
                self.adjacency[i, j] = 1.0
                self.adjacency[j, i] = 1.0

    def set_adjacency_from_grid(self, rows: int, cols: int) -> None:
        """Set adjacency for a rectangular grid of cells.

        Cells are numbered row-major: cell_id = row * cols + col

        Args:
            rows: Number of rows in the grid
            cols: Number of columns in the grid
        """
        adjacency_pairs: List[Tuple[int, int]] = []

        for row in range(rows):
            for col in range(cols):
                cell_id = row * cols + col

                # Right neighbor
                if col < cols - 1:
                    adjacency_pairs.append((cell_id, cell_id + 1))

                # Bottom neighbor
                if row < rows - 1:
                    adjacency_pairs.append((cell_id, cell_id + cols))

        self.set_adjacency(adjacency_pairs)

    def set_heat_source(self, cell_id: int, power_w: float) -> None:
        """Set heat generation for a specific cell.

        Args:
            cell_id: Index of the cell (0 to n_cells-1)
            power_w: Heat generation rate in Watts
        """
        if 0 <= cell_id < self.n_cells:
            self.heat_sources[cell_id] = power_w

    def clear_heat_sources(self) -> None:
        """Set all heat sources to zero."""
        self.heat_sources.fill(0.0)

    def set_temperatures(self, temperatures: Union[List[float], NDArray[np.float64]]) -> None:
        """Set temperatures for all cells.

        Args:
            temperatures: Array of temperatures in °C, length must equal n_cells
        """
        self.temperatures = np.array(temperatures, dtype=np.float64)

    def get_temperatures(self) -> NDArray[np.float64]:
        """Get current temperatures of all cells.

        Returns:
            Array of temperatures in °C for each cell
        """
        return self.temperatures.copy()

    def solve_timestep(self, dt_s: float) -> NDArray[np.float64]:
        """Advance the solution by one timestep using explicit Euler.

        Energy balance for each cell:
            m*cp * dT/dt = Q_source + Q_conduction - Q_ambient

        Where:
            Q_conduction = sum over neighbors of (T_neighbor - T_cell) / R
            Q_ambient = htc * (T_cell - T_ambient)

        Args:
            dt_s: Timestep size in seconds

        Returns:
            Updated temperatures array in °C
        """
        # Calculate heat flow rates for each cell
        dq_dt = np.zeros(self.n_cells, dtype=np.float64)

        for i in range(self.n_cells):
            # Heat from sources
            q_total = self.heat_sources[i]

            # Conduction from/to neighbors: Q = (T_j - T_i) / R = (T_j - T_i) * conductance
            for j in range(self.n_cells):
                if self.adjacency[i, j] > 0:
                    q_conduction = (
                        self.temperatures[j] - self.temperatures[i]
                    ) * self.cell_to_cell_conductance
                    q_total += q_conduction

            # Convective loss to ambient: Q = htc * (T_ambient - T_cell)
            q_ambient = self.ambient_htc_w_k * (
                self.ambient_temp_c - self.temperatures[i]
            )
            q_total += q_ambient

            # Rate of temperature change: dT/dt = Q / (m * cp)
            dq_dt[i] = q_total / self.thermal_mass

        # Explicit Euler update: T_new = T_old + dt * dT/dt
        self.temperatures = self.temperatures + dt_s * dq_dt

        return self.temperatures.copy()

    def get_max_stable_timestep(self) -> float:
        """Estimate maximum stable timestep for explicit Euler.

        For stability, dt < thermal_mass / (sum of conductances)

        Returns:
            Estimated maximum stable timestep in seconds
        """
        # Count max neighbors any cell has
        max_neighbors = int(np.max(np.sum(self.adjacency, axis=1)))

        # Total conductance = neighbor conductances + ambient htc
        total_conductance = (
            max_neighbors * self.cell_to_cell_conductance + self.ambient_htc_w_k
        )

        if total_conductance <= 0:
            return float("inf")

        # Safety factor of 0.5 for stability
        return 0.5 * self.thermal_mass / total_conductance
