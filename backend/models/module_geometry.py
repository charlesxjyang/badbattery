"""Module geometry generation for battery cell arrangements.

Computes cell positions and adjacency relationships for rectangular
cell arrays based on module configuration.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple

from models.schemas import CellType, ModuleConfig


# Cell dimensions in mm: (width/diameter, depth, height)
# For cylindrical cells: (diameter, diameter, height)
# For prismatic/pouch: (width, depth, height)
CELL_DIMENSIONS: Dict[CellType, Tuple[float, float, float]] = {
    CellType.cylindrical_21700: (21.0, 21.0, 70.0),
    CellType.cylindrical_18650: (18.0, 18.0, 65.0),
    CellType.prismatic: (148.0, 27.0, 91.0),  # Typical prismatic cell
    CellType.pouch: (160.0, 8.0, 227.0),  # Typical pouch cell
}


@dataclass
class CellPosition:
    """Position and bounds of a single cell."""

    id: int
    center: Tuple[float, float, float]  # (x, y, z) in mm
    bounds: Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float]]
    # ((x_min, x_max), (y_min, y_max), (z_min, z_max))


class ModuleGeometry:
    """Generates cell positions and adjacency for a battery module.

    Cells are arranged in a rectangular grid with specified spacing.
    Cell IDs are assigned row-major: id = row * cols + col

    Args:
        config: ModuleConfig with rows, cols, cell_type, spacing_mm
    """

    def __init__(self, config: ModuleConfig) -> None:
        self.config = config
        self.rows = config.rows
        self.cols = config.cols
        self.cell_type = config.cell_type
        self.spacing_mm = config.spacing_mm

        # Get cell dimensions
        self.cell_width, self.cell_depth, self.cell_height = CELL_DIMENSIONS[
            self.cell_type
        ]

        # Compute cell positions
        self._positions: List[CellPosition] = []
        self._adjacency: Dict[int, List[int]] = {}
        self._compute_positions()
        self._compute_adjacency()

    @property
    def n_cells(self) -> int:
        """Total number of cells in the module."""
        return self.rows * self.cols

    def _cell_id(self, row: int, col: int) -> int:
        """Get cell ID from row and column indices."""
        return row * self.cols + col

    def _compute_positions(self) -> None:
        """Compute center positions and bounds for all cells."""
        self._positions = []

        # Pitch = cell dimension + spacing
        pitch_x = self.cell_width + self.spacing_mm
        pitch_y = self.cell_depth + self.spacing_mm

        for row in range(self.rows):
            for col in range(self.cols):
                cell_id = self._cell_id(row, col)

                # Center position
                cx = col * pitch_x + self.cell_width / 2
                cy = row * pitch_y + self.cell_depth / 2
                cz = self.cell_height / 2

                # Bounds
                x_min = col * pitch_x
                x_max = x_min + self.cell_width
                y_min = row * pitch_y
                y_max = y_min + self.cell_depth
                z_min = 0.0
                z_max = self.cell_height

                self._positions.append(
                    CellPosition(
                        id=cell_id,
                        center=(cx, cy, cz),
                        bounds=((x_min, x_max), (y_min, y_max), (z_min, z_max)),
                    )
                )

    def _compute_adjacency(self) -> None:
        """Compute adjacency relationships (4-connected grid)."""
        self._adjacency = {i: [] for i in range(self.n_cells)}

        for row in range(self.rows):
            for col in range(self.cols):
                cell_id = self._cell_id(row, col)
                neighbors: List[int] = []

                # Right neighbor
                if col < self.cols - 1:
                    neighbors.append(self._cell_id(row, col + 1))

                # Left neighbor
                if col > 0:
                    neighbors.append(self._cell_id(row, col - 1))

                # Bottom neighbor (next row)
                if row < self.rows - 1:
                    neighbors.append(self._cell_id(row + 1, col))

                # Top neighbor (previous row)
                if row > 0:
                    neighbors.append(self._cell_id(row - 1, col))

                self._adjacency[cell_id] = sorted(neighbors)

    def get_cell_positions(self) -> List[Dict]:
        """Get positions and bounds for all cells.

        Returns:
            List of dicts with keys: id, center (x, y, z), bounds
        """
        return [
            {
                "id": pos.id,
                "center": {"x": pos.center[0], "y": pos.center[1], "z": pos.center[2]},
                "bounds": {
                    "x": {"min": pos.bounds[0][0], "max": pos.bounds[0][1]},
                    "y": {"min": pos.bounds[1][0], "max": pos.bounds[1][1]},
                    "z": {"min": pos.bounds[2][0], "max": pos.bounds[2][1]},
                },
            }
            for pos in self._positions
        ]

    def get_adjacency(self) -> Dict[int, List[int]]:
        """Get adjacency relationships.

        Returns:
            Dict mapping cell ID to list of neighbor IDs
        """
        return self._adjacency.copy()

    def get_adjacency_pairs(self) -> List[Tuple[int, int]]:
        """Get adjacency as list of unique pairs.

        Returns:
            List of (cell_i, cell_j) tuples where i < j
        """
        pairs: List[Tuple[int, int]] = []
        for cell_id, neighbors in self._adjacency.items():
            for neighbor_id in neighbors:
                if cell_id < neighbor_id:
                    pairs.append((cell_id, neighbor_id))
        return pairs

    def get_module_bounds(self) -> Dict[str, Tuple[float, float]]:
        """Get overall module bounding box.

        Returns:
            Dict with x, y, z keys mapping to (min, max) tuples
        """
        pitch_x = self.cell_width + self.spacing_mm
        pitch_y = self.cell_depth + self.spacing_mm

        return {
            "x": (0.0, (self.cols - 1) * pitch_x + self.cell_width),
            "y": (0.0, (self.rows - 1) * pitch_y + self.cell_depth),
            "z": (0.0, self.cell_height),
        }

    def to_json(self) -> Dict:
        """Serialize geometry to JSON-compatible dict.

        Returns:
            Dict with module configuration, cell positions, adjacency,
            and overall bounds suitable for frontend consumption
        """
        return {
            "config": {
                "rows": self.rows,
                "cols": self.cols,
                "cell_type": self.cell_type.value,
                "spacing_mm": self.spacing_mm,
            },
            "cell_dimensions": {
                "width_mm": self.cell_width,
                "depth_mm": self.cell_depth,
                "height_mm": self.cell_height,
            },
            "n_cells": self.n_cells,
            "cells": self.get_cell_positions(),
            "adjacency": {str(k): v for k, v in self._adjacency.items()},
            "module_bounds": self.get_module_bounds(),
        }
