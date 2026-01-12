"""Tests for module geometry generation."""

import pytest

from models.schemas import CellType, ModuleConfig
from models.module_geometry import CELL_DIMENSIONS, ModuleGeometry


class TestCellCount:
    """Test correct number of cells generated."""

    def test_2x3_module_has_6_cells(self):
        config = ModuleConfig(
            rows=2, cols=3, cell_type=CellType.cylindrical_21700, spacing_mm=2.0
        )
        geom = ModuleGeometry(config)

        assert geom.n_cells == 6
        assert len(geom.get_cell_positions()) == 6
        assert len(geom.get_adjacency()) == 6

    def test_various_module_sizes(self):
        for rows, cols in [(1, 1), (1, 5), (4, 1), (3, 4), (5, 5)]:
            config = ModuleConfig(
                rows=rows,
                cols=cols,
                cell_type=CellType.prismatic,
                spacing_mm=1.0,
            )
            geom = ModuleGeometry(config)

            expected = rows * cols
            assert geom.n_cells == expected
            assert len(geom.get_cell_positions()) == expected


class TestAdjacency:
    """Test adjacency relationships."""

    def test_corner_cells_have_2_neighbors(self):
        """Corner cells in a grid have exactly 2 neighbors."""
        config = ModuleConfig(
            rows=3, cols=4, cell_type=CellType.cylindrical_21700, spacing_mm=2.0
        )
        geom = ModuleGeometry(config)
        adjacency = geom.get_adjacency()

        # 3x4 grid:
        # 0  1  2  3
        # 4  5  6  7
        # 8  9  10 11

        # Corners: 0, 3, 8, 11
        assert len(adjacency[0]) == 2  # neighbors: 1, 4
        assert len(adjacency[3]) == 2  # neighbors: 2, 7
        assert len(adjacency[8]) == 2  # neighbors: 4, 9
        assert len(adjacency[11]) == 2  # neighbors: 7, 10

    def test_edge_cells_have_3_neighbors(self):
        """Edge (non-corner) cells have exactly 3 neighbors."""
        config = ModuleConfig(
            rows=3, cols=4, cell_type=CellType.cylindrical_21700, spacing_mm=2.0
        )
        geom = ModuleGeometry(config)
        adjacency = geom.get_adjacency()

        # Edge cells: 1, 2 (top), 4, 7 (sides), 9, 10 (bottom)
        assert len(adjacency[1]) == 3  # neighbors: 0, 2, 5
        assert len(adjacency[2]) == 3  # neighbors: 1, 3, 6
        assert len(adjacency[4]) == 3  # neighbors: 0, 5, 8
        assert len(adjacency[7]) == 3  # neighbors: 3, 6, 11
        assert len(adjacency[9]) == 3  # neighbors: 5, 8, 10
        assert len(adjacency[10]) == 3  # neighbors: 6, 9, 11

    def test_center_cells_have_4_neighbors(self):
        """Interior cells have exactly 4 neighbors."""
        config = ModuleConfig(
            rows=3, cols=4, cell_type=CellType.cylindrical_21700, spacing_mm=2.0
        )
        geom = ModuleGeometry(config)
        adjacency = geom.get_adjacency()

        # Center cells: 5, 6
        assert len(adjacency[5]) == 4  # neighbors: 1, 4, 6, 9
        assert len(adjacency[6]) == 4  # neighbors: 2, 5, 7, 10

    def test_specific_neighbors(self):
        """Verify specific neighbor relationships."""
        config = ModuleConfig(
            rows=3, cols=3, cell_type=CellType.pouch, spacing_mm=5.0
        )
        geom = ModuleGeometry(config)
        adjacency = geom.get_adjacency()

        # 3x3 grid:
        # 0 1 2
        # 3 4 5
        # 6 7 8

        assert set(adjacency[0]) == {1, 3}
        assert set(adjacency[4]) == {1, 3, 5, 7}  # center has all 4
        assert set(adjacency[8]) == {5, 7}

    def test_1x1_module_no_neighbors(self):
        """Single cell has no neighbors."""
        config = ModuleConfig(
            rows=1, cols=1, cell_type=CellType.cylindrical_18650, spacing_mm=0.0
        )
        geom = ModuleGeometry(config)
        adjacency = geom.get_adjacency()

        assert len(adjacency[0]) == 0

    def test_1xN_module_linear_adjacency(self):
        """Single row has linear adjacency."""
        config = ModuleConfig(
            rows=1, cols=5, cell_type=CellType.cylindrical_21700, spacing_mm=1.0
        )
        geom = ModuleGeometry(config)
        adjacency = geom.get_adjacency()

        # 0 - 1 - 2 - 3 - 4
        assert adjacency[0] == [1]
        assert adjacency[1] == [0, 2]
        assert adjacency[2] == [1, 3]
        assert adjacency[3] == [2, 4]
        assert adjacency[4] == [3]

    def test_adjacency_pairs_unique(self):
        """Adjacency pairs are unique and ordered."""
        config = ModuleConfig(
            rows=3, cols=3, cell_type=CellType.prismatic, spacing_mm=2.0
        )
        geom = ModuleGeometry(config)
        pairs = geom.get_adjacency_pairs()

        # Check uniqueness
        assert len(pairs) == len(set(pairs))

        # Check ordering (i < j)
        for i, j in pairs:
            assert i < j

        # 3x3 grid should have 12 edges: 6 horizontal + 6 vertical
        assert len(pairs) == 12


class TestCellPositions:
    """Test cell position calculations."""

    def test_positions_correctly_spaced(self):
        """Cell centers are spaced by cell_width + spacing."""
        spacing = 3.0
        config = ModuleConfig(
            rows=2, cols=3, cell_type=CellType.cylindrical_21700, spacing_mm=spacing
        )
        geom = ModuleGeometry(config)
        positions = geom.get_cell_positions()

        cell_width = CELL_DIMENSIONS[CellType.cylindrical_21700][0]  # 21.0
        expected_pitch = cell_width + spacing  # 24.0

        # Check x spacing between adjacent cells in same row
        pos_0 = positions[0]["center"]
        pos_1 = positions[1]["center"]
        assert pos_1["x"] - pos_0["x"] == pytest.approx(expected_pitch)

        # Check y spacing between cells in adjacent rows
        pos_3 = positions[3]["center"]  # First cell of second row
        assert pos_3["y"] - pos_0["y"] == pytest.approx(expected_pitch)

    def test_first_cell_position(self):
        """First cell is positioned at half cell width from origin."""
        config = ModuleConfig(
            rows=2, cols=2, cell_type=CellType.cylindrical_18650, spacing_mm=2.0
        )
        geom = ModuleGeometry(config)
        positions = geom.get_cell_positions()

        cell_dim = CELL_DIMENSIONS[CellType.cylindrical_18650]

        pos_0 = positions[0]["center"]
        assert pos_0["x"] == pytest.approx(cell_dim[0] / 2)  # 9.0
        assert pos_0["y"] == pytest.approx(cell_dim[1] / 2)  # 9.0
        assert pos_0["z"] == pytest.approx(cell_dim[2] / 2)  # 32.5

    def test_cell_bounds_match_dimensions(self):
        """Cell bounds match cell dimensions."""
        config = ModuleConfig(
            rows=1, cols=1, cell_type=CellType.prismatic, spacing_mm=0.0
        )
        geom = ModuleGeometry(config)
        positions = geom.get_cell_positions()

        cell_dim = CELL_DIMENSIONS[CellType.prismatic]
        bounds = positions[0]["bounds"]

        assert bounds["x"]["max"] - bounds["x"]["min"] == pytest.approx(cell_dim[0])
        assert bounds["y"]["max"] - bounds["y"]["min"] == pytest.approx(cell_dim[1])
        assert bounds["z"]["max"] - bounds["z"]["min"] == pytest.approx(cell_dim[2])

    def test_cells_do_not_overlap(self):
        """Adjacent cells do not overlap (gap = spacing)."""
        spacing = 5.0
        config = ModuleConfig(
            rows=2, cols=2, cell_type=CellType.pouch, spacing_mm=spacing
        )
        geom = ModuleGeometry(config)
        positions = geom.get_cell_positions()

        # Check gap between cell 0 and cell 1 (horizontal neighbors)
        bounds_0 = positions[0]["bounds"]
        bounds_1 = positions[1]["bounds"]

        gap_x = bounds_1["x"]["min"] - bounds_0["x"]["max"]
        assert gap_x == pytest.approx(spacing)

    def test_zero_spacing(self):
        """Zero spacing means cells are touching."""
        config = ModuleConfig(
            rows=2, cols=2, cell_type=CellType.cylindrical_21700, spacing_mm=0.0
        )
        geom = ModuleGeometry(config)
        positions = geom.get_cell_positions()

        bounds_0 = positions[0]["bounds"]
        bounds_1 = positions[1]["bounds"]

        # Cell 1 should start exactly where cell 0 ends
        assert bounds_1["x"]["min"] == pytest.approx(bounds_0["x"]["max"])


class TestModuleBounds:
    """Test overall module bounding box."""

    def test_module_bounds_size(self):
        """Module bounds encompass all cells."""
        config = ModuleConfig(
            rows=3, cols=4, cell_type=CellType.cylindrical_21700, spacing_mm=2.0
        )
        geom = ModuleGeometry(config)
        bounds = geom.get_module_bounds()

        cell_dim = CELL_DIMENSIONS[CellType.cylindrical_21700]
        spacing = 2.0

        # Expected size: n_cells * cell_dim + (n_cells - 1) * spacing
        expected_x = 4 * cell_dim[0] + 3 * spacing  # 4*21 + 3*2 = 90
        expected_y = 3 * cell_dim[1] + 2 * spacing  # 3*21 + 2*2 = 67
        expected_z = cell_dim[2]  # 70

        assert bounds["x"][1] - bounds["x"][0] == pytest.approx(expected_x)
        assert bounds["y"][1] - bounds["y"][0] == pytest.approx(expected_y)
        assert bounds["z"][1] - bounds["z"][0] == pytest.approx(expected_z)


class TestJsonSerialization:
    """Test JSON serialization."""

    def test_to_json_has_required_keys(self):
        config = ModuleConfig(
            rows=2, cols=2, cell_type=CellType.cylindrical_21700, spacing_mm=1.0
        )
        geom = ModuleGeometry(config)
        data = geom.to_json()

        assert "config" in data
        assert "cell_dimensions" in data
        assert "n_cells" in data
        assert "cells" in data
        assert "adjacency" in data
        assert "module_bounds" in data

    def test_to_json_config_values(self):
        config = ModuleConfig(
            rows=3, cols=4, cell_type=CellType.pouch, spacing_mm=5.0
        )
        geom = ModuleGeometry(config)
        data = geom.to_json()

        assert data["config"]["rows"] == 3
        assert data["config"]["cols"] == 4
        assert data["config"]["cell_type"] == "pouch"
        assert data["config"]["spacing_mm"] == 5.0
        assert data["n_cells"] == 12

    def test_to_json_adjacency_string_keys(self):
        """Adjacency keys are strings for JSON compatibility."""
        config = ModuleConfig(
            rows=2, cols=2, cell_type=CellType.cylindrical_18650, spacing_mm=1.0
        )
        geom = ModuleGeometry(config)
        data = geom.to_json()

        # Keys should be strings
        assert all(isinstance(k, str) for k in data["adjacency"].keys())
        assert "0" in data["adjacency"]
