"""Thermal runaway heat release model.

Models the heat generation during a thermal runaway event using
a simple time-based profile triggered by temperature threshold.
"""

from typing import Optional


class ThermalRunawayModel:
    """Single-step thermal runaway model with temperature trigger.

    Heat release follows a simple profile:
    - No heat below onset temperature
    - Constant heat release rate once triggered
    - Heat release stops after duration

    Args:
        onset_temp_c: Temperature threshold to trigger TR (°C)
        peak_heat_w: Heat generation rate during TR (W)
        total_energy_kj: Total energy released during TR (kJ)
        duration_s: Duration of heat release (s)
    """

    def __init__(
        self,
        onset_temp_c: float = 150.0,
        peak_heat_w: float = 5000.0,
        total_energy_kj: float = 100.0,
        duration_s: float = 30.0,
    ) -> None:
        self.onset_temp_c = onset_temp_c
        self.peak_heat_w = peak_heat_w
        self.total_energy_kj = total_energy_kj
        self.duration_s = duration_s

        # Derived: average heat rate to deliver total energy over duration
        # total_energy_kj * 1000 = average_heat_w * duration_s
        self._average_heat_w = (total_energy_kj * 1000.0) / duration_s

        # State
        self._triggered = False
        self._trigger_time: Optional[float] = None
        self._completed = False

    @property
    def triggered(self) -> bool:
        """Whether thermal runaway has been triggered."""
        return self._triggered

    @property
    def trigger_time(self) -> Optional[float]:
        """Time when TR was triggered (None if not triggered)."""
        return self._trigger_time

    @property
    def completed(self) -> bool:
        """Whether thermal runaway event has completed."""
        return self._completed

    def reset(self) -> None:
        """Reset the model to initial state."""
        self._triggered = False
        self._trigger_time = None
        self._completed = False

    def check_trigger(self, temperature_c: float, current_time_s: float) -> bool:
        """Check if temperature exceeds onset and trigger TR if so.

        Args:
            temperature_c: Current cell temperature in °C
            current_time_s: Current simulation time in seconds

        Returns:
            True if TR was just triggered, False otherwise
        """
        if self._triggered:
            return False

        if temperature_c >= self.onset_temp_c:
            self._triggered = True
            self._trigger_time = current_time_s
            return True

        return False

    def get_heat_generation(self, current_time_s: float) -> float:
        """Get current heat generation rate.

        Uses a constant heat release profile that delivers total_energy_kj
        over the duration period.

        Args:
            current_time_s: Current simulation time in seconds

        Returns:
            Heat generation rate in Watts (0 if not triggered or completed)
        """
        if not self._triggered or self._trigger_time is None:
            return 0.0

        elapsed = current_time_s - self._trigger_time

        if elapsed < 0:
            return 0.0

        if elapsed >= self.duration_s:
            self._completed = True
            return 0.0

        # Constant heat release to deliver total energy over duration
        return self._average_heat_w

    def get_energy_released(self, current_time_s: float) -> float:
        """Get total energy released so far.

        Args:
            current_time_s: Current simulation time in seconds

        Returns:
            Energy released in kJ
        """
        if not self._triggered or self._trigger_time is None:
            return 0.0

        elapsed = current_time_s - self._trigger_time

        if elapsed < 0:
            return 0.0

        if elapsed >= self.duration_s:
            return self.total_energy_kj

        # Energy = average_heat_w * elapsed_time / 1000 (convert J to kJ)
        return self._average_heat_w * elapsed / 1000.0
