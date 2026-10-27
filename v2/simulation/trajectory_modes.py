"""
Operational Trajectory Modes and Motor Acceleration Controllers.
Implements:
1. Clinostat 3D (Constant ratio)
2. Clinostat Optimal S^2 Ergodic (Kim et al. npj Microgravity 2026, gamma = 1.146)
3. Stochastic RPM Mode A (Pica et al. PLOS ONE 2026, 20-45s reversals)
Based on IIST Manufacturing Technology specifications (I_zz = 0.614 kg.m^2, alpha = 10 rad/s^2).
"""

from enum import Enum
import random
import numpy as np


class TrajectoryMode(str, Enum):
    CLINOSTAT_3D = "clinostat_3d"
    CLINOSTAT_OPTIMAL = "clinostat_optimal"
    RPM_STOCHASTIC = "rpm_stochastic"


class TrajectoryController:
    """
    Controls inner (phi) and outer (psi) gimbal speeds, direction reversals,
    and motor torque-constrained acceleration ramping.
    """

    def __init__(
        self,
        default_mode: TrajectoryMode = TrajectoryMode.CLINOSTAT_OPTIMAL,
        base_inner_rpm: float = 2.0,
        base_outer_rpm: float = 2.0,
        max_alpha_rad_s2: float = 10.0      # From CAD motor calculations (Slides 9, 11)
    ):
        self.mode = default_mode
        self.base_inner_rpm = base_inner_rpm
        self.base_outer_rpm = base_outer_rpm
        # Convert rad/s^2 to RPM/s: 1 rad/s^2 = 60 / (2 * pi) ~ 9.549 RPM/s
        self.max_alpha_rpm_s = max_alpha_rad_s2 * (60.0 / (2.0 * np.pi))

        # Current actual speeds
        self.current_omega_phi_rpm = 0.0
        self.current_omega_psi_rpm = 0.0

        # Commanded targets
        self.target_omega_phi_rpm = 2.0
        self.target_omega_psi_rpm = 2.292 if default_mode == TrajectoryMode.CLINOSTAT_OPTIMAL else 2.0

        # Stochastic reversal timer (Pica et al. 2026)
        self.stochastic_timer = 0.0
        self.next_stochastic_switch = 25.0
        self.direction_changes_count = 0

        self.apply_mode(default_mode)

    def set_base_speeds(self, inner_rpm: float, outer_rpm: float):
        self.base_inner_rpm = max(0.0, min(30.0, inner_rpm))
        self.base_outer_rpm = max(0.0, min(30.0, outer_rpm))
        self.apply_mode(self.mode)

    def apply_mode(self, mode: TrajectoryMode):
        self.mode = mode
        if mode == TrajectoryMode.CLINOSTAT_3D:
            self.target_omega_phi_rpm = self.base_inner_rpm
            self.target_omega_psi_rpm = self.base_outer_rpm
        elif mode == TrajectoryMode.CLINOSTAT_OPTIMAL:
            # Kim et al. (2026): gamma = 1.146 for uniform S^2 coverage
            self.target_omega_phi_rpm = self.base_inner_rpm
            self.target_omega_psi_rpm = self.base_inner_rpm * 1.146
        elif mode == TrajectoryMode.RPM_STOCHASTIC:
            self.stochastic_timer = 0.0
            self.next_stochastic_switch = random.uniform(20.0, 45.0)
            self._trigger_stochastic_step()

    def _trigger_stochastic_step(self):
        """Generates random speed between 80% and 100% of base and random direction."""
        factor_phi = random.uniform(0.80, 1.00) * (1.0 if random.random() > 0.5 else -1.0)
        factor_psi = random.uniform(0.80, 1.00) * (1.0 if random.random() > 0.5 else -1.0)
        self.target_omega_phi_rpm = self.base_inner_rpm * factor_phi
        self.target_omega_psi_rpm = self.base_outer_rpm * factor_psi
        self.direction_changes_count += 1

    def update(self, dt: float) -> tuple[float, float, float, float]:
        """
        Updates controller by dt.
        Returns:
            (omega_phi_rpm, omega_psi_rpm, alpha_phi_rad_s2, alpha_psi_rad_s2)
        """
        if self.mode == TrajectoryMode.RPM_STOCHASTIC:
            self.stochastic_timer += dt
            if self.stochastic_timer >= self.next_stochastic_switch:
                self.stochastic_timer = 0.0
                self.next_stochastic_switch = random.uniform(20.0, 45.0)
                self._trigger_stochastic_step()

        # Ramp phi speed
        d_phi = self.target_omega_phi_rpm - self.current_omega_phi_rpm
        max_step = self.max_alpha_rpm_s * dt
        if abs(d_phi) <= max_step:
            actual_step_phi = d_phi
            self.current_omega_phi_rpm = self.target_omega_phi_rpm
        else:
            actual_step_phi = np.sign(d_phi) * max_step
            self.current_omega_phi_rpm += actual_step_phi

        alpha_phi_rad_s2 = (actual_step_phi / dt) * ((2.0 * np.pi) / 60.0) if dt > 0 else 0.0

        # Ramp psi speed
        d_psi = self.target_omega_psi_rpm - self.current_omega_psi_rpm
        if abs(d_psi) <= max_step:
            actual_step_psi = d_psi
            self.current_omega_psi_rpm = self.target_omega_psi_rpm
        else:
            actual_step_psi = np.sign(d_psi) * max_step
            self.current_omega_psi_rpm += actual_step_psi

        alpha_psi_rad_s2 = (actual_step_psi / dt) * ((2.0 * np.pi) / 60.0) if dt > 0 else 0.0

        return (
            float(self.current_omega_phi_rpm),
            float(self.current_omega_psi_rpm),
            float(alpha_phi_rad_s2),
            float(alpha_psi_rad_s2)
        )
