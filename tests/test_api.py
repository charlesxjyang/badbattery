"""Tests for the FastAPI endpoints."""

import sys
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the API."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client: TestClient) -> None:
        """Health endpoint should return ok status."""
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestCellPresetsEndpoints:
    """Tests for cell presets endpoints."""

    def test_list_cell_presets(self, client: TestClient) -> None:
        """Should list available cell presets."""
        response = client.get("/api/presets/cells")
        assert response.status_code == 200

        presets = response.json()
        assert isinstance(presets, list)
        assert "lfp_prismatic" in presets
        assert "nmc622_21700" in presets

    def test_get_cell_preset_nmc622(self, client: TestClient) -> None:
        """Should return NMC622 preset configuration."""
        response = client.get("/api/presets/cells/nmc622_21700")
        assert response.status_code == 200

        preset = response.json()
        assert preset["chemistry"] == "NMC622"
        assert preset["capacity_ah"] == 5.0
        assert "thermal_runaway" in preset

    def test_get_cell_preset_lfp(self, client: TestClient) -> None:
        """Should return LFP preset configuration."""
        response = client.get("/api/presets/cells/lfp_prismatic")
        assert response.status_code == 200

        preset = response.json()
        assert preset["chemistry"] == "LFP"
        assert preset["capacity_ah"] == 100.0

    def test_get_nonexistent_preset_returns_404(self, client: TestClient) -> None:
        """Should return 404 for nonexistent preset."""
        response = client.get("/api/presets/cells/nonexistent")
        assert response.status_code == 404


class TestModulePreviewEndpoint:
    """Tests for module preview endpoint."""

    def test_get_module_preview(self, client: TestClient) -> None:
        """Should return module geometry for preview."""
        response = client.get(
            "/api/module/preview",
            params={
                "rows": 2,
                "cols": 3,
                "cell_type": "cylindrical_21700",
                "spacing_mm": 2.0,
            },
        )
        assert response.status_code == 200

        geometry = response.json()
        assert geometry["n_cells"] == 6
        assert geometry["config"]["rows"] == 2
        assert geometry["config"]["cols"] == 3
        assert len(geometry["cells"]) == 6
        assert "adjacency" in geometry
        assert "module_bounds" in geometry

    def test_module_preview_validates_params(self, client: TestClient) -> None:
        """Should validate query parameters."""
        # Invalid rows (too large)
        response = client.get(
            "/api/module/preview",
            params={
                "rows": 100,
                "cols": 3,
                "cell_type": "cylindrical_21700",
                "spacing_mm": 2.0,
            },
        )
        assert response.status_code == 422  # Validation error


class TestSimulationEndpoint:
    """Tests for simulation endpoint."""

    def test_run_simulation(self, client: TestClient) -> None:
        """Should run simulation and return result."""
        config = {
            "module": {
                "rows": 2,
                "cols": 2,
                "cell_type": "cylindrical_21700",
                "spacing_mm": 2.0,
            },
            "cell": {
                "chemistry": "NMC811",
                "capacity_ah": 5.0,
                "mass_kg": 0.07,
                "specific_heat": 1000.0,
                "thermal_resistance": 2.0,
            },
            "thermal_runaway": {
                "onset_temp_c": 150.0,
                "peak_heat_w": 5000.0,
                "total_energy_kj": 100.0,
                "duration_s": 30.0,
            },
            "cooling": {
                "type": "none",
                "coolant_temp_c": 25.0,
                "htc": 50.0,
            },
            "abuse": {
                "type": "nail_penetration",
                "target_cell": 0,
            },
            "solver": {
                "thermal_model": "lumped",
                "time_end_s": 5.0,
                "dt_s": 0.01,
                "dt_output_s": 1.0,
            },
        }

        response = client.post("/api/simulations", json=config)
        assert response.status_code == 200

        result = response.json()
        assert result["completed"] is True
        assert len(result["frames"]) > 0
        assert len(result["tr_propagation_events"]) >= 1

    def test_simulation_invalid_target_cell(self, client: TestClient) -> None:
        """Should return 400 for invalid target cell."""
        config = {
            "module": {
                "rows": 2,
                "cols": 2,
                "cell_type": "cylindrical_21700",
                "spacing_mm": 2.0,
            },
            "cell": {
                "chemistry": "NMC811",
                "capacity_ah": 5.0,
                "mass_kg": 0.07,
                "specific_heat": 1000.0,
                "thermal_resistance": 2.0,
            },
            "thermal_runaway": {
                "onset_temp_c": 150.0,
                "peak_heat_w": 5000.0,
                "total_energy_kj": 100.0,
                "duration_s": 30.0,
            },
            "cooling": {
                "type": "none",
                "coolant_temp_c": 25.0,
                "htc": 50.0,
            },
            "abuse": {
                "type": "nail_penetration",
                "target_cell": 99,  # Invalid - only 4 cells
            },
            "solver": {
                "thermal_model": "lumped",
                "time_end_s": 5.0,
                "dt_s": 0.01,
                "dt_output_s": 1.0,
            },
        }

        response = client.post("/api/simulations", json=config)
        assert response.status_code == 400
