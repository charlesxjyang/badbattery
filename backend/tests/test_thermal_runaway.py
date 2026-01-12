"""Tests for thermal runaway model."""

import pytest
import numpy as np

from models.thermal_runaway import ThermalRunawayModel


class TestBelowOnsetTemp:
    """Test behavior below onset temperature."""

    def test_no_heat_below_onset(self):
        """No heat release when temperature is below onset."""
        model = ThermalRunawayModel(
            onset_temp_c=150.0,
            peak_heat_w=5000.0,
            total_energy_kj=100.0,
            duration_s=30.0,
        )

        # Check trigger at various temperatures below onset
        for temp in [25.0, 50.0, 100.0, 149.9]:
            model.check_trigger(temp, current_time_s=0.0)
            assert not model.triggered
            assert model.get_heat_generation(current_time_s=0.0) == 0.0

    def test_not_triggered_state(self):
        """Model state remains untriggered below onset."""
        model = ThermalRunawayModel(onset_temp_c=150.0)

        model.check_trigger(100.0, current_time_s=5.0)

        assert not model.triggered
        assert model.trigger_time is None
        assert not model.completed
        assert model.get_energy_released(10.0) == 0.0


class TestAboveOnsetTemp:
    """Test behavior above onset temperature."""

    def test_triggers_at_onset(self):
        """TR triggers exactly at onset temperature."""
        model = ThermalRunawayModel(onset_temp_c=150.0)

        triggered = model.check_trigger(150.0, current_time_s=10.0)

        assert triggered
        assert model.triggered
        assert model.trigger_time == 10.0

    def test_triggers_above_onset(self):
        """TR triggers above onset temperature."""
        model = ThermalRunawayModel(onset_temp_c=150.0)

        triggered = model.check_trigger(200.0, current_time_s=5.0)

        assert triggered
        assert model.triggered
        assert model.trigger_time == 5.0

    def test_returns_heat_after_trigger(self):
        """Heat is generated after triggering."""
        model = ThermalRunawayModel(
            onset_temp_c=150.0,
            total_energy_kj=100.0,
            duration_s=30.0,
        )

        model.check_trigger(160.0, current_time_s=0.0)

        heat = model.get_heat_generation(current_time_s=1.0)
        assert heat > 0.0

    def test_only_triggers_once(self):
        """TR only triggers once, subsequent checks return False."""
        model = ThermalRunawayModel(onset_temp_c=150.0)

        first_trigger = model.check_trigger(160.0, current_time_s=0.0)
        second_trigger = model.check_trigger(200.0, current_time_s=1.0)

        assert first_trigger
        assert not second_trigger
        assert model.trigger_time == 0.0  # Still original trigger time


class TestEnergyIntegration:
    """Test that energy integrates to total_energy_kj."""

    def test_total_energy_integration(self):
        """Integrated heat equals total_energy_kj."""
        total_energy_kj = 100.0
        duration_s = 30.0

        model = ThermalRunawayModel(
            onset_temp_c=150.0,
            total_energy_kj=total_energy_kj,
            duration_s=duration_s,
        )

        model.check_trigger(160.0, current_time_s=0.0)

        # Integrate heat over duration
        dt = 0.01
        total_energy_j = 0.0
        t = 0.0

        while t <= duration_s + dt:
            heat_w = model.get_heat_generation(t)
            total_energy_j += heat_w * dt
            t += dt

        total_energy_kj_integrated = total_energy_j / 1000.0

        # Should be approximately equal to total_energy_kj
        assert np.isclose(total_energy_kj_integrated, total_energy_kj, rtol=0.01)

    def test_energy_released_method(self):
        """get_energy_released returns correct cumulative energy."""
        total_energy_kj = 50.0
        duration_s = 20.0

        model = ThermalRunawayModel(
            onset_temp_c=150.0,
            total_energy_kj=total_energy_kj,
            duration_s=duration_s,
        )

        model.check_trigger(160.0, current_time_s=0.0)

        # At halfway point
        energy_halfway = model.get_energy_released(duration_s / 2)
        assert np.isclose(energy_halfway, total_energy_kj / 2, rtol=0.01)

        # At end
        energy_end = model.get_energy_released(duration_s)
        assert np.isclose(energy_end, total_energy_kj, rtol=0.01)

        # After end
        energy_after = model.get_energy_released(duration_s * 2)
        assert np.isclose(energy_after, total_energy_kj, rtol=0.01)

    def test_different_energy_values(self):
        """Test with various total energy values."""
        for total_energy in [10.0, 50.0, 200.0, 500.0]:
            model = ThermalRunawayModel(
                onset_temp_c=150.0,
                total_energy_kj=total_energy,
                duration_s=10.0,
            )

            model.check_trigger(160.0, current_time_s=0.0)

            # Integrate
            dt = 0.01
            integrated = sum(
                model.get_heat_generation(t) * dt
                for t in np.arange(0, 15.0, dt)
            ) / 1000.0

            assert np.isclose(integrated, total_energy, rtol=0.02)


class TestDurationBehavior:
    """Test heat release stops after duration."""

    def test_heat_drops_to_zero_after_duration(self):
        """Heat generation is zero after duration expires."""
        duration_s = 30.0

        model = ThermalRunawayModel(
            onset_temp_c=150.0,
            total_energy_kj=100.0,
            duration_s=duration_s,
        )

        model.check_trigger(160.0, current_time_s=0.0)

        # During TR - should have heat
        heat_during = model.get_heat_generation(duration_s / 2)
        assert heat_during > 0.0

        # Just before end - should still have heat
        heat_before_end = model.get_heat_generation(duration_s - 0.01)
        assert heat_before_end > 0.0

        # At end - should be zero
        heat_at_end = model.get_heat_generation(duration_s)
        assert heat_at_end == 0.0

        # After end - should be zero
        heat_after = model.get_heat_generation(duration_s + 10.0)
        assert heat_after == 0.0

    def test_completed_flag_set_after_duration(self):
        """completed flag is set after duration expires."""
        duration_s = 10.0

        model = ThermalRunawayModel(
            onset_temp_c=150.0,
            duration_s=duration_s,
        )

        model.check_trigger(160.0, current_time_s=0.0)

        # During TR
        model.get_heat_generation(5.0)
        assert not model.completed

        # After duration
        model.get_heat_generation(duration_s + 1.0)
        assert model.completed

    def test_different_durations(self):
        """Test with various duration values."""
        for duration in [5.0, 20.0, 60.0]:
            model = ThermalRunawayModel(
                onset_temp_c=150.0,
                duration_s=duration,
            )

            model.check_trigger(160.0, current_time_s=0.0)

            # Heat during
            assert model.get_heat_generation(duration / 2) > 0.0

            # No heat after
            assert model.get_heat_generation(duration + 1.0) == 0.0


class TestReset:
    """Test model reset functionality."""

    def test_reset_clears_state(self):
        """Reset returns model to initial state."""
        model = ThermalRunawayModel(onset_temp_c=150.0)

        # Trigger and run
        model.check_trigger(160.0, current_time_s=0.0)
        model.get_heat_generation(100.0)  # Complete the TR

        assert model.triggered
        assert model.completed

        # Reset
        model.reset()

        assert not model.triggered
        assert model.trigger_time is None
        assert not model.completed

    def test_can_retrigger_after_reset(self):
        """Model can be triggered again after reset."""
        model = ThermalRunawayModel(onset_temp_c=150.0)

        # First trigger
        model.check_trigger(160.0, current_time_s=0.0)
        assert model.trigger_time == 0.0

        model.reset()

        # Second trigger at different time
        model.check_trigger(170.0, current_time_s=50.0)
        assert model.trigger_time == 50.0
