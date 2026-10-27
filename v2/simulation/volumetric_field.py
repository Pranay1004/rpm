"""
Volumetric Spatial Acceleration Field and Critical Radius Solver.
Based on Wadhwa et al. (Scientific Reports 2026, Nature Portfolio, DOI: 10.1038/s41598-026-39316-7).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import numpy as np


@dataclass
class VolumetricProbePoint:
    label: str
    r_coords_m: np.ndarray       # Coordinates [x, y, z] in meters relative to payload origin
    history_g: List[float] = field(default_factory=list)
    sum_accel_m_s2: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=np.float64))
    samples: int = 0
    current_accel_g: float = 1.0
    taSMG_point: float = 1.0


class VolumetricFieldSolver:
    """
    Computes complete 3D spatial acceleration fields:
    a_total(r, t) = g(t) - omega(t) x (omega(t) x r) - alpha(t) x r
    and assesses compliance with the 10^-3 g biological microgravity threshold.
    """

    def __init__(self, g0: float = 9.80665, default_chamber_radius_m: float = 0.06):
        self.g0 = g0
        self.chamber_radius_m = default_chamber_radius_m
        self.probes: Dict[str, VolumetricProbePoint] = {}
        self.reset()
        # Add default probe points (Center, Chamber Edge, and Corners)
        self.add_probe("Center", np.array([0.0, 0.0, 0.0]))
        self.add_probe("Edge-X", np.array([default_chamber_radius_m, 0.0, 0.0]))
        self.add_probe("Edge-Y", np.array([0.0, default_chamber_radius_m, 0.0]))
        self.add_probe("Edge-Z", np.array([0.0, 0.0, default_chamber_radius_m]))

    def reset(self):
        for probe in self.probes.values():
            probe.history_g.clear()
            probe.sum_accel_m_s2.fill(0.0)
            probe.samples = 0
            probe.current_accel_g = 1.0
            probe.taSMG_point = 1.0

    def set_chamber_radius(self, radius_m: float):
        self.chamber_radius_m = max(0.005, min(0.15, radius_m))
        if "Edge-X" in self.probes:
            self.probes["Edge-X"].r_coords_m = np.array([self.chamber_radius_m, 0.0, 0.0])
        if "Edge-Y" in self.probes:
            self.probes["Edge-Y"].r_coords_m = np.array([0.0, self.chamber_radius_m, 0.0])
        if "Edge-Z" in self.probes:
            self.probes["Edge-Z"].r_coords_m = np.array([0.0, 0.0, self.chamber_radius_m])

    def add_probe(self, label: str, coords_m: np.ndarray):
        self.probes[label] = VolumetricProbePoint(label=label, r_coords_m=np.array(coords_m, dtype=np.float64))

    def compute_field(
        self,
        g_payload_unit: np.ndarray,
        omega_phi_rpm: float,
        omega_psi_rpm: float,
        alpha_phi_rad_s2: float = 0.0,
        alpha_psi_rad_s2: float = 0.0
    ) -> Tuple[float, float, float, float]:
        """
        Computes volumetric field quantities:
        Returns:
            (a_centrifugal_edge_g, a_euler_edge_g, safe_radius_cm, mean_edge_g)
        """
        omega_phi = omega_phi_rpm * (2.0 * np.pi / 60.0)
        omega_psi = omega_psi_rpm * (2.0 * np.pi / 60.0)
        
        # Angular velocity vector in inner payload frame (roll about Z, yaw coupled via pitch)
        omega_vec = np.array([0.0, omega_psi, omega_phi], dtype=np.float64)
        alpha_vec = np.array([0.0, alpha_psi_rad_s2, alpha_phi_rad_s2], dtype=np.float64)
        
        omega_norm = float(np.linalg.norm(omega_vec))
        
        # Safe radius threshold for centrifugal acceleration < 10^-3 g0 (Wadhwa 2026 Eq 5)
        # r_safe = (10^-3 * g0) / ||omega||^2
        safe_radius_m = (0.001 * self.g0) / (omega_norm**2 + 1e-12)
        safe_radius_cm = safe_radius_m * 100.0

        # Centrifugal acceleration at chamber boundary (R)
        a_cent_edge_m_s2 = (omega_norm**2) * self.chamber_radius_m
        a_cent_edge_g = a_cent_edge_m_s2 / self.g0

        # Euler acceleration at boundary
        alpha_norm = float(np.linalg.norm(alpha_vec))
        a_euler_edge_m_s2 = alpha_norm * self.chamber_radius_m
        a_euler_edge_g = a_euler_edge_m_s2 / self.g0

        # Base gravity vector in m/s^2
        g_base_m_s2 = g_payload_unit * self.g0

        # Update all probe points
        for probe in self.probes.values():
            r = probe.r_coords_m
            # Centrifugal term: - omega x (omega x r)
            a_cent = -np.cross(omega_vec, np.cross(omega_vec, r))
            # Euler term: - alpha x r
            a_euler = -np.cross(alpha_vec, r)
            
            # Total spatial acceleration vector (Wadhwa et al. Eq 5)
            a_total = g_base_m_s2 + a_cent + a_euler
            accel_mag_g = float(np.linalg.norm(a_total) / self.g0)
            
            probe.current_accel_g = accel_mag_g
            probe.sum_accel_m_s2 += a_total
            probe.samples += 1
            avg_accel_vec = probe.sum_accel_m_s2 / probe.samples
            probe.taSMG_point = float(np.linalg.norm(avg_accel_vec) / self.g0)

        edge_probe = self.probes.get("Edge-X")
        mean_edge_g = edge_probe.taSMG_point if edge_probe else a_cent_edge_g

        return a_cent_edge_g, a_euler_edge_g, safe_radius_cm, mean_edge_g
