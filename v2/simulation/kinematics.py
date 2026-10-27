"""
Kinematics and Coordinate Transformations for 2-Axis Concentric RPM.
Based on Yotov et al. (Inventions 2022) and IIST M.Tech Manufacturing Technology Project.
"""

from dataclasses import dataclass
import numpy as np


@dataclass
class KinematicState:
    timestamp: float
    phi_deg: float              # Inner gimbal angle (degrees)
    psi_deg: float              # Outer gimbal angle (degrees)
    omega_phi_rpm: float        # Inner gimbal angular velocity (RPM)
    omega_psi_rpm: float        # Outer gimbal angular velocity (RPM)
    alpha_phi_rad_s2: float     # Inner gimbal angular acceleration (rad/s^2)
    alpha_psi_rad_s2: float     # Outer gimbal angular acceleration (rad/s^2)
    e_g: np.ndarray             # Normalized gravity vector in payload frame [gx, gy, gz]
    instantaneous_g: float      # Magnitude of current gravity vector (g)
    taSMG: float                # Time-Averaged Simulated Microgravity magnitude (g)
    mean_gx: float              # Running mean Gx component (g)
    mean_gy: float              # Running mean Gy component (g)
    mean_gz: float              # Running mean Gz component (g)


class RPMKinematics:
    """
    Computes exact gimbal rotation matrices, sample frame gravity projections,
    and cumulative vector time-averaging (taSMG).
    """

    def __init__(self, g0: float = 9.80665):
        self.g0 = g0
        self.reset()

    def reset(self):
        self.samples = 0
        self.elapsed_time = 0.0
        self.sum_gx = 0.0
        self.sum_gy = 0.0
        self.sum_gz = 0.0
        self.min_g = 1.0
        self.max_g = 1.0

    @staticmethod
    def rotation_outer_y(psi_rad: float) -> np.ndarray:
        """Rotation about laboratory Y-axis by angle psi (outer gimbal)."""
        c = np.cos(psi_rad)
        s = np.sin(psi_rad)
        return np.array([
            [ c, 0.0,  s],
            [0.0, 1.0, 0.0],
            [-s, 0.0,  c]
        ], dtype=np.float64)

    @staticmethod
    def rotation_inner_z(phi_rad: float) -> np.ndarray:
        """Rotation about inner gimbal Z-axis by angle phi (inner gimbal)."""
        c = np.cos(phi_rad)
        s = np.sin(phi_rad)
        return np.array([
            [ c,  s, 0.0],
            [-s,  c, 0.0],
            [0.0, 0.0, 1.0]
        ], dtype=np.float64)

    def compute_gravity_projection(self, phi_deg: float, psi_deg: float) -> np.ndarray:
        """
        Calculates normalized gravity vector in payload frame (Yotov et al. Eq. 1-2):
        e_g = -sin(phi)*cos(psi) ex + sin(phi)*sin(psi) ey + cos(phi) ez
        """
        phi = np.radians(phi_deg)
        psi = np.radians(psi_deg)
        
        gx = -np.sin(phi) * np.cos(psi)
        gy =  np.sin(phi) * np.sin(psi)
        gz =  np.cos(phi)
        
        return np.array([gx, gy, gz], dtype=np.float64)

    def step(
        self,
        dt: float,
        phi_deg: float,
        psi_deg: float,
        omega_phi_rpm: float,
        omega_psi_rpm: float,
        alpha_phi_rad_s2: float = 0.0,
        alpha_psi_rad_s2: float = 0.0
    ) -> KinematicState:
        """
        Integrates kinematics forward by time step dt.
        """
        self.elapsed_time += dt
        self.samples += 1

        e_g = self.compute_gravity_projection(phi_deg, psi_deg)
        inst_g = float(np.linalg.norm(e_g))

        self.sum_gx += e_g[0]
        self.sum_gy += e_g[1]
        self.sum_gz += e_g[2]

        avg_gx = self.sum_gx / self.samples
        avg_gy = self.sum_gy / self.samples
        avg_gz = self.sum_gz / self.samples

        tasmg = float(np.sqrt(avg_gx**2 + avg_gy**2 + avg_gz**2))

        if self.samples > 5:
            self.min_g = min(self.min_g, tasmg)
            self.max_g = max(self.max_g, tasmg)

        return KinematicState(
            timestamp=self.elapsed_time,
            phi_deg=float(phi_deg % 360.0),
            psi_deg=float(psi_deg % 360.0),
            omega_phi_rpm=float(omega_phi_rpm),
            omega_psi_rpm=float(omega_psi_rpm),
            alpha_phi_rad_s2=float(alpha_phi_rad_s2),
            alpha_psi_rad_s2=float(alpha_psi_rad_s2),
            e_g=e_g,
            instantaneous_g=inst_g,
            taSMG=tasmg,
            mean_gx=float(avg_gx),
            mean_gy=float(avg_gy),
            mean_gz=float(avg_gz)
        )
