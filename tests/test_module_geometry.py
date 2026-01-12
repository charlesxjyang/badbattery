"""Tests for module geometry generation."""

import sys
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import pytest

from models.module_geometry import ModuleGeometry
from models.schemas import CellType, ModuleConfig


class TestModuleGeometry:
    """Tests for ModuleGeometry class."""

    def test_2x3_module_has_6_cells(self) -> None:
        """A 2x3 module should have exactly 6 cells."""
        config = ModuleConfig(
            rows=2,
            cols=3,
            cell_type=CellType.cylindrical_21700,
            spacing_mm=2.0,
        )
        geometry = ModuleGeometry(config)

        assert geometry.n_cells == 6

    def test_neighbor_counts_2x3(self) -> None:
        """In a 2x3 module: corners have 2 neighbors, edges have 3, center has 4.

        Layout (cell IDs):
            0 - 1 - 2
            3 - 4 - 5

        Corners: 0, 2, 3, 5 (2 neighbors each)
        Edges: 1, 4 (3 neighbors each)
        No center cells in 2x3.
        """
        config = ModuleConfig(
            rows=2,
            cols=3,
            cell_type=CellType.cylindrical_21700,
            spacing_mm=2.0,
        )
        geometry = ModuleGeometry(config)
        adjacency = geometry.get_adjacency()

        # Corner cells have 2 neighbors
        corners = [0, 2, 3, 5]
        for cell_id in corners:
            assert len(adjacency[cell_id]) == 2, f"Corner cell {cell_id} should have 2 neighbors"

        # Edge cells (middle of each row) have 3 neighbors
        edges = [1, 4]
        for cell_id in edges:
            assert len(adjacency[cell_id]) == 3, f"Edge cell {cell_id} should have 3 neighbors"

    def test_neighbor_counts_3x3(self) -> None:
        """In a 3x3 module: corners have 2 neighbors, edges have 3, center has 4.

        Layout (cell IDs):
            0 - 1 - 2
            3 - 4 - 5
            6 - 7 - 8

        Corners: 0, 2, 6, 8 (2 neighbors each)
        Edges: 1, 3, 5, 7 (3 neighbors each)
        Center: 4 (4 neighbors)
        """
        config = ModuleConfig(
            rows=3,
            cols=3,
            cell_type=CellType.cylindrical_21700,
            spacing_mm=2.0,
        )
        geometry = ModuleGeometry(config)
        adjacency = geometry.get_adjacency()

        # Corner cells have 2 neighbors
        corners = [0, 2, 6, 8]
        for cell_id in corners:
            assert len(adjacency[cell_id]) == 2, f"Corner cell {cell_id} should have 2 neighbors"

        # Edge cells have 3 neighbors
        edges = [1, 3, 5, 7]
        for cell_id in edges:
            assert len(adjacency[cell_id]) == 3, f"Edge cell {cell_id} should have 3 neighbors"

        # Center cell has 4 neighbors
        assert len(adjacency[4]) == 4, "Center cell 4 should have 4 neighbors"

    def test_cell_positions_correctly_spaced(self) -> None:
        """Cell positions should be spaced by cell_width + spacing_mm."""
        spacing_mm = 3.0
        config = ModuleConfig(
            rows=2,
            cols=3,
            cell_type=CellType.cylindrical_21700,
            spacing_mm=spacing_mm,
        )
        geometry = ModuleGeometry(config)
        positions = geometry.get_cell_positions()

        # For 21700 cells: diameter = 21.0 mm
        cell_diameter = 21.0
        expected_pitch = cell_diameter + spacing_mm  # 24.0 mm

        # Check x-spacing between adjacent cells in same row
        # Cell 0 and Cell 1 are in row 0, columns 0 and 1
        cell_0 = positions[0]
        cell_1 = positions[1]
        x_distance = cell_1["center"]["x"] - cell_0["center"]["x"]
        assert x_distance == pytest.approx(expected_pitch), (
            f"X spacing between cells should be {expected_pitch} mm, got {x_distance}"
        )

        # Check y-spacing between adjacent cells in same column
        # Cell 0 and Cell 3 are in column 0, rows 0 and 1
        cell_3 = positions[3]
        y_distance = cell_3["center"]["y"] - cell_0["center"]["y"]
        assert y_distance == pytest.approx(expected_pitch), (
            f"Y spacing between cells should be {expected_pitch} mm, got {y_distance}"
        )

    def test_cell_positions_first_cell_at_origin(self) -> None:
        """First cell center should be at half cell width from origin."""
        config = ModuleConfig(
            rows=2,
            cols=2,
            cell_type=CellType.cylindrical_21700,
            spacing_mm=2.0,
        )
        geometry = ModuleGeometry(config)
        positions = geometry.get_cell_positions()

        cell_0 = positions[0]
        cell_diameter = 21.0
        cell_height = 70.0

        # First cell center should be at (diameter/2, diameter/2, height/2)
        assert cell_0["center"]["x"] == pytest.approx(cell_diameter / 2)
        assert cell_0["center"]["y"] == pytest.approx(cell_diameter / 2)
        assert cell_0["center"]["z"] == pytest.approx(cell_height / 2)
