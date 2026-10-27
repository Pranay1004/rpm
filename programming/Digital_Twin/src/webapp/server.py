"""
RPM Digital Twin - Real-Time Web Dashboard Server v2.0
======================================================
SpaceX Dragon / Tesla Autopilot inspired UI backend.

Fixed gravity calculations based on proper microgravity science:
- Time-averaged gravity VECTOR (not magnitude)
- Proper rotation matrices from research paper
- Rectangular frame support with configurable dimensions

Commercial-grade WebSocket streaming for live visualization.
"""

import asyncio
import json
import subprocess
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Optional
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger
from pydantic import BaseModel

# Import hardware tests router
try:
    from webapp.hardware_tests import router as hardware_router
    HAS_HARDWARE_TESTS = True
except ImportError as e:
    logger.warning(f"Could not import hardware tests router: {e}")
    HAS_HARDWARE_TESTS = False


# =============================================================================
# CONSTANTS
# =============================================================================
EARTH_GRAVITY = 9.80665  # m/s²


def _open_dashboard_in_browser(url: str) -> None:
    """Open the local dashboard in a browser after the server starts."""
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", "-a", "Safari", url], check=False)
        else:
            import webbrowser

            webbrowser.open(url)
    except Exception as exc:
        logger.warning(f"Could not open browser automatically: {exc}")


# =============================================================================
# DATA MODELS
# =============================================================================

class FrameDimensions(BaseModel):
    """Rectangular frame dimensions."""
    inner_length: float = 0.30  # m
    inner_breadth: float = 0.20  # m
    outer_length: float = 0.50  # m
    outer_breadth: float = 0.35  # m


class AxisInclination(BaseModel):
    """Axis inclination angles (degrees) - tilt of rotation axes."""
    inner_axis_tilt: float = 0.0  # Tilt of inner frame rotation axis from Z
    outer_axis_tilt: float = 0.0  # Tilt of outer frame rotation axis from Y


class SimulationConfig(BaseModel):
    inner_rpm: float = 2.0
    outer_rpm: float = 2.292  # Default to non-harmonic ratio (Kim et al. 2026) to prevent pole locks
    mode: str = "clinostat_3d"  # clinostat_3d, clinostat_optimal, rpm_stochastic
    sample_radius_cm: float = 5.0
    frame_dimensions: Optional[FrameDimensions] = None
    axis_inclination: Optional[AxisInclination] = None


class ConnectionInfo(BaseModel):
    """Hardware connection information."""
    type: str  # serial, network, usb, gpio
    port: str
    status: str  # connected, disconnected, error
    device_name: str
    baudrate: Optional[int] = None
    ip_address: Optional[str] = None


class SimulationState(BaseModel):
    timestamp: float
    time_elapsed: float
    # Frame rotation angles (phi and psi from paper)
    phi_deg: float  # Inner frame angle (Z-axis rotation)
    psi_deg: float  # Outer frame angle (Y-axis rotation)
    omega_phi_rpm: float  # Inner frame angular velocity
    omega_psi_rpm: float  # Outer frame angular velocity
    # Axis inclination angles
    inner_axis_tilt_deg: float
    outer_axis_tilt_deg: float
    # Gravity vector components (normalized, in sample frame) - from Eq. (2)
    gravity_x: float
    gravity_y: float
    gravity_z: float
    # Time-averaged gravity vector (Center COR)
    avg_gravity_x: float
    avg_gravity_y: float
    avg_gravity_z: float
    # Microgravity quality metrics (Center COR)
    instantaneous_g: float
    mean_g: float  # ||time-averaged gravity vector|| at center (taSMG)
    min_g: float
    max_g: float
    samples: int
    status: str
    # Frame dimensions
    inner_length: float
    inner_breadth: float
    outer_length: float
    outer_breadth: float
    # Velocity ratio gamma = omega_phi / omega_psi (Eq. 5)
    gamma: float

    # Volumetric / Spatial Acceleration Field (Wadhwa et al., MIT/Harvard 2026)
    sample_radius_cm: float = 5.0
    instantaneous_g_edge: float = 1.0  # Total acceleration magnitude at sample edge (g)
    mean_g_edge: float = 0.0           # Time-averaged acceleration magnitude at sample edge (g)
    centrifugal_accel_edge_g: float = 0.0 # Instantaneous centrifugal acceleration at edge (g)
    safe_sample_radius_cm: float = 2.5 # Maximum radius where mean residual g < 0.001 g (10^-3 g)
    shear_stress_mPa: float = 0.0      # Stokes fluid shear stress in cell culture wells (mPa)
    operation_mode: str = "clinostat_3d" # clinostat_3d, clinostat_optimal, rpm_stochastic
    direction_changes_count: int = 0   # Zero-crossing count (Pica et al. 2026)

    # Real Physical Hardware Telemetry Coupling (Digital Shadow)
    hardware_connected: bool = False
    hardware_device: Optional[str] = None
    imu_accel_x: Optional[float] = None
    imu_accel_y: Optional[float] = None
    imu_accel_z: Optional[float] = None
    telemetry_residual_g: Optional[float] = None  # ||a_measured - a_simulated||


# =============================================================================
# ROTATION MATRIX CALCULATIONS - FROM PAPER Eq. (1)
# =============================================================================

class RotationMatrices:
    """
    Proper rotation matrices based on research paper equations.
    
    From the paper:
    - R_Y (outer frame): rotation around Y-axis by angle φ (psi)
    - R_Z (inner frame): rotation around Z-axis by angle φ (phi)
    
    R_Y = | cos(ψ)   0   sin(ψ) |    R_Z = | cos(φ)  -sin(φ)  0 |
          |   0      1     0    |          | sin(φ)   cos(φ)  0 |
          |-sin(ψ)   0   cos(ψ) |          |   0        0     1 |
    
    The gravity vector in sample frame (Eq. 2):
    ē_g = -sin(φ)cos(ψ)ē_x + sin(φ)sin(ψ)ē_y + cos(φ)ē_z
    
    Where gravity in lab frame points along -Z direction.
    """
    
    @staticmethod
    def R_Y(psi: float) -> np.ndarray:
        """
        Rotation around Y-axis (outer frame) - Eq from paper.
        psi (ψ): outer frame angle in radians
        """
        c, s = np.cos(psi), np.sin(psi)
        return np.array([
            [c,  0, s],
            [0,  1, 0],
            [-s, 0, c]
        ], dtype=np.float64)
    
    @staticmethod
    def R_Z(phi: float) -> np.ndarray:
        """
        Rotation around Z-axis (inner frame) - Eq from paper.
        phi (φ): inner frame angle in radians
        """
        c, s = np.cos(phi), np.sin(phi)
        return np.array([
            [c, -s, 0],
            [s,  c, 0],
            [0,  0, 1]
        ], dtype=np.float64)
    
    @staticmethod
    def R_X(theta: float) -> np.ndarray:
        """Rotation around X-axis (for axis tilting)."""
        c, s = np.cos(theta), np.sin(theta)
        return np.array([
            [1,  0,  0],
            [0,  c, -s],
            [0,  s,  c]
        ], dtype=np.float64)
    
    @staticmethod
    def compute_gravity_vector(phi: float, psi: float) -> np.ndarray:
        """
        Compute gravity vector in sample frame using Eq. (2) from paper.
        
        ē_g = -sin(φ)cos(ψ)ē_x + sin(φ)sin(ψ)ē_y + cos(φ)ē_z
        
        Args:
            phi: inner frame angle (radians)
            psi: outer frame angle (radians)
        
        Returns:
            Normalized gravity vector [gx, gy, gz]
        """
        sin_phi = np.sin(phi)
        cos_phi = np.cos(phi)
        sin_psi = np.sin(psi)
        cos_psi = np.cos(psi)
        
        gx = -sin_phi * cos_psi
        gy = sin_phi * sin_psi
        gz = cos_phi
        
        return np.array([gx, gy, gz], dtype=np.float64)


# =============================================================================
# MICROGRAVITY PHYSICS ENGINE - Based on Paper Equations
# =============================================================================

class MicrogravitySimulator:
    """
    Proper microgravity simulation based on RPM physics from the paper.
    
    Key equations:
    - Gravity vector (Eq. 2): ē_g = -sin(φ)cos(ψ)ē_x + sin(φ)sin(ψ)ē_y + cos(φ)ē_z
    - Angular velocities: ω_φ = dφ/dt (inner), ω_ψ = dψ/dt (outer)
    - Velocity ratio (Eq. 5): γ = ω_φ / ω_ψ
    
    For good microgravity (low taSMG):
    - γ should be irrational (e.g., √2, π/e) to avoid repetitive paths
    - Velocities between 0.05-0.4 rad/s (0.5-4 RPM)
    
    Critical: The INSTANTANEOUS gravity magnitude is ALWAYS 1g.
    Microgravity is achieved through TIME-AVERAGED VECTOR approaching zero.
    """
    
class RealTimeFluidFDMSolver:
    """
    Real-Time 1D Finite Difference Method (FDM) Navier-Stokes solver.
    
    Solves the transient azimuthal momentum diffusion equation in cylindrical coordinates
    for cell culture vessels (petri dishes, microwells, T-flasks) mounted on the RPM:
        ∂u_θ/∂t = ν [ ∂²u_θ/∂r² + (1/r) ∂u_θ/∂r - u_θ/r² ]
    
    Boundary conditions:
        r = 0: u_θ(0, t) = 0 (symmetry at vessel axis)
        r = R: u_θ(R, t) = ω_eff(t) * R (no-slip rotating vessel wall)
    
    Computes exact real-time unsteady fluid velocity profile u(r, t) and wall shear stress:
        τ_w = μ | ∂u_θ/∂r - u_θ/r |_{r=R} (mPa)
    
    Captures transient shear spikes during motor accelerations and directional reversals
    (Pica et al. 2026, Hasenstein & van Loon).
    """
    def __init__(
        self,
        vessel_radius_m: float = 0.0175,  # 35mm dish / 6-well plate radius (17.5 mm)
        num_grid_points: int = 25,
        kinematic_viscosity: float = 1.0e-6,  # m²/s (standard culture medium at 37°C)
        dynamic_viscosity: float = 1.0e-3,   # Pa·s
    ):
        self.R = vessel_radius_m
        self.N = num_grid_points
        self.nu = kinematic_viscosity
        self.mu = dynamic_viscosity
        self.r = np.linspace(0.0, self.R, self.N)
        self.dr = self.r[1] - self.r[0]
        self.u = np.zeros(self.N, dtype=np.float64)  # Fluid velocity profile (m/s)
        self.wall_shear_stress_mPa: float = 0.0
        self.max_shear_stress_mPa: float = 0.0

    def reset(self) -> None:
        self.u.fill(0.0)
        self.wall_shear_stress_mPa = 0.0
        self.max_shear_stress_mPa = 0.0

    def step(self, omega_eff_rad_s: float, dt: float = 0.02) -> float:
        """
        Advance the fluid momentum diffusion by dt using Finite Difference Method.
        Returns the instantaneous wall shear stress in mPa.
        """
        if dt <= 0:
            return self.wall_shear_stress_mPa
            
        u_new = self.u.copy()
        
        # Vectorized internal FDM diffusion for r in (0, R)
        r_int = self.r[1:-1]
        u_int = self.u[1:-1]
        u_plus = self.u[2:]
        u_minus = self.u[:-2]
        
        d2u_dr2 = (u_plus - 2.0 * u_int + u_minus) / (self.dr ** 2)
        du_dr = (u_plus - u_minus) / (2.0 * self.dr)
        
        # Laplacian in cylindrical coordinates for azimuthal velocity
        laplacian = d2u_dr2 + (1.0 / r_int) * du_dr - (u_int / (r_int ** 2))
        
        # Update interior velocity profile
        u_new[1:-1] = u_int + dt * self.nu * laplacian
        
        # Boundary conditions
        u_new[0] = 0.0
        u_new[-1] = omega_eff_rad_s * self.R
        
        self.u = u_new
        
        # Compute wall shear stress via 2nd-order one-sided derivative at wall
        dudr_wall = (3.0 * self.u[-1] - 4.0 * self.u[-2] + self.u[-3]) / (2.0 * self.dr)
        rate_of_strain_wall = abs(dudr_wall - self.u[-1] / self.R)
        self.wall_shear_stress_mPa = float(self.mu * rate_of_strain_wall * 1000.0)
        self.max_shear_stress_mPa = max(self.max_shear_stress_mPa, self.wall_shear_stress_mPa)
        
        return self.wall_shear_stress_mPa


class MicrogravitySimulator:
    """
    Volumetric Microgravity & Biomechanical Simulation Engine.
    
    Based on peer-reviewed literature:
    1. Yotov et al. (Inventions 2022) - Kinematic rotation matrices Eq. (1)-(2)
    2. Wadhwa et al. (Scientific Reports 2026, MIT/Harvard) - Volumetric acceleration field Eq. (5)
       including centrifugal a_cent = ω × (ω × r) and Euler a_euler = α × r
    3. Kim, Park, Kim (npj Microgravity 2026) - Spherical S² uniformity & pole avoidance
    4. Hasenstein & van Loon - Stokes fluid shear stress bounds (180-320 mPa)
    5. Pica et al. (PLoS ONE 2026) - Mode A zero-crossing stochastic profile
    """
    
    def __init__(self):
        # Frame angles (radians)
        self.phi = 0.0      # Inner frame angle (Z-axis rotation)
        self.psi = 0.0      # Outer frame angle (Y-axis rotation)
        
        # Angular velocities (rad/s)
        self.omega_phi = 0.0    # Inner frame angular velocity
        self.omega_psi = 0.0    # Outer frame angular velocity
        self.alpha_phi = 0.0    # Inner frame angular acceleration (rad/s²)
        self.alpha_psi = 0.0    # Outer frame angular acceleration (rad/s²)
        
        # Setpoints
        self.omega_phi_setpoint = 0.0
        self.omega_psi_setpoint = 0.0
        self.nominal_inner_rpm = 2.0
        self.nominal_outer_rpm = 2.292  # Default non-harmonic ratio (Kim et al. 2026)
        
        # Operation mode & sample parameters
        self.mode = "clinostat_3d"  # clinostat_3d, clinostat_optimal, rpm_stochastic
        self.sample_radius_m = 0.05 # 5.0 cm default sample enclosure offset
        self.well_radius_m = 0.015  # 15 mm standard cell culture well
        
        # Real-time FDM Navier-Stokes fluid shear stress solver
        self.fdm_solver = RealTimeFluidFDMSolver(vessel_radius_m=self.well_radius_m)
        
        # Stochastic RPM state (Pica et al. 2026 Mode A)
        self.next_switch_time = 25.0
        self.direction_changes_count = 0
        self.rng = np.random.default_rng(42)
        
        # Axis inclination angles (for tilted rotation axes)
        self.inner_axis_tilt = 0.0  # radians
        self.outer_axis_tilt = 0.0  # radians
        
        # Time tracking
        self.time = 0.0
        self.start_time = 0.0
        
        # Gravity vector history at Center of Rotation (COR)
        self.gravity_history: List[np.ndarray] = []
        self.max_history = 6000  # 2 minutes at 50Hz
        self.gravity_sum = np.zeros(3)
        
        # Edge acceleration history (Wadhwa et al. 2026 Eq. 5)
        self.edge_gravity_history: List[np.ndarray] = []
        self.edge_gravity_sum = np.zeros(3)
        
        # Frame dimensions (rectangular)
        self.inner_length = 0.30
        self.inner_breadth = 0.20
        self.outer_length = 0.50
        self.outer_breadth = 0.35
        
        # Min/Max tracking for center taSMG
        self.min_g = float('inf')
        self.max_g = 0.0
        
        logger.info("Volumetric Microgravity Simulator initialized (Yotov + Wadhwa + Kim + van Loon)")
    
    def set_mode(self, mode: str):
        """Set operation mode (clinostat_3d, clinostat_optimal, rpm_stochastic)."""
        self.mode = mode
        if mode == "clinostat_optimal":
            self.set_velocities(2.0, 2.292)
        elif mode == "rpm_stochastic":
            self.next_switch_time = self.time + float(self.rng.uniform(20.0, 45.0))
        logger.info(f"Simulator operation mode set to: {mode}")

    def set_sample_radius(self, radius_cm: float):
        """Set sample chamber radius in cm."""
        self.sample_radius_m = max(0.001, float(radius_cm) / 100.0)
        logger.info(f"Sample chamber radius set to {radius_cm:.1f} cm ({self.sample_radius_m:.3f} m)")

    def set_velocities(self, inner_rpm: float, outer_rpm: float):
        """Set target velocities in RPM."""
        self.nominal_inner_rpm = abs(inner_rpm) if abs(inner_rpm) > 1e-4 else 2.0
        self.nominal_outer_rpm = abs(outer_rpm) if abs(outer_rpm) > 1e-4 else 2.292
        self.omega_phi_setpoint = inner_rpm * 2 * np.pi / 60  # rad/s
        self.omega_psi_setpoint = outer_rpm * 2 * np.pi / 60
        logger.info(f"Velocities set: ω_φ={inner_rpm:.2f} RPM, ω_ψ={outer_rpm:.2f} RPM")
    
    def set_axis_inclination(self, inner_tilt_deg: float, outer_tilt_deg: float):
        """Set axis inclination angles in degrees."""
        self.inner_axis_tilt = np.radians(inner_tilt_deg)
        self.outer_axis_tilt = np.radians(outer_tilt_deg)
        logger.info(f"Axis inclination: inner={inner_tilt_deg}°, outer={outer_tilt_deg}°")
    
    def set_frame_dimensions(self, inner_l: float, inner_b: float, 
                             outer_l: float, outer_b: float):
        """Set rectangular frame dimensions in meters."""
        self.inner_length = inner_l
        self.inner_breadth = inner_b
        self.outer_length = outer_l
        self.outer_breadth = outer_b
    
    def reset(self):
        """Reset simulation state."""
        self.phi = 0.0
        self.psi = 0.0
        self.omega_phi = 0.0
        self.omega_psi = 0.0
        self.alpha_phi = 0.0
        self.alpha_psi = 0.0
        self.time = 0.0
        self.start_time = time.time()
        self.gravity_history.clear()
        self.gravity_sum = np.zeros(3)
        self.edge_gravity_history.clear()
        self.edge_gravity_sum = np.zeros(3)
        self.min_g = float('inf')
        self.max_g = 0.0
        self.direction_changes_count = 0
        self.fdm_solver.reset()
        logger.info("Simulation reset")
    
    def get_gamma(self) -> float:
        """Calculate velocity ratio γ = ω_φ / ω_ψ (Eq. 5)."""
        if abs(self.omega_psi) < 1e-9:
            return float('inf') if self.omega_phi > 0 else 0.0
        return self.omega_phi / self.omega_psi
    
    def step(self, dt: float) -> dict:
        """
        Advance simulation by dt seconds with full volumetric kinematics,
        Euler acceleration, centrifugal gradient, and Stokes fluid shear stress.
        """
        # Handle stochastic RPM mode behavior (direction zero-crossings per Pica et al. 2026 Mode A)
        if self.mode == "rpm_stochastic":
            if self.time >= self.next_switch_time:
                sign_phi = float(self.rng.choice([-1.0, 1.0]))
                sign_psi = float(self.rng.choice([-1.0, 1.0]))
                factor_phi = float(self.rng.uniform(0.80, 1.0))
                factor_psi = float(self.rng.uniform(0.80, 1.0))
                
                target_phi_rpm = self.nominal_inner_rpm * factor_phi * sign_phi
                target_psi_rpm = self.nominal_outer_rpm * factor_psi * sign_psi
                self.set_velocities(target_phi_rpm, target_psi_rpm)
                
                self.direction_changes_count += 1
                self.next_switch_time = self.time + float(self.rng.uniform(20.0, 45.0))
                logger.debug(f"Stochastic zero-crossing switch #{self.direction_changes_count}: inner={target_phi_rpm:.2f} RPM, outer={target_psi_rpm:.2f} RPM")
        elif self.mode == "clinostat_optimal":
            if abs(self.omega_phi_setpoint) < 1e-4 and abs(self.omega_psi_setpoint) < 1e-4:
                self.set_velocities(2.0, 2.292)

        # First-order motor response & angular acceleration computation
        tau = 0.3  # Motor response time constant
        new_omega_phi = self.omega_phi + (self.omega_phi_setpoint - self.omega_phi) * dt / tau
        new_omega_psi = self.omega_psi + (self.omega_psi_setpoint - self.omega_psi) * dt / tau
        
        self.alpha_phi = (new_omega_phi - self.omega_phi) / dt if dt > 0 else 0.0
        self.alpha_psi = (new_omega_psi - self.omega_psi) / dt if dt > 0 else 0.0
        self.omega_phi = new_omega_phi
        self.omega_psi = new_omega_psi
        
        # Update angles (continuous rotation - don't wrap)
        self.phi += self.omega_phi * dt
        self.psi += self.omega_psi * dt
        
        # 1. CENTER OF ROTATION (COR, r = 0,0,0) KINEMATICS (Yotov et al. 2022)
        if abs(self.inner_axis_tilt) > 1e-6 or abs(self.outer_axis_tilt) > 1e-6:
            R_tilt_outer = RotationMatrices.R_X(self.outer_axis_tilt)
            R_outer = R_tilt_outer @ RotationMatrices.R_Y(self.psi) @ R_tilt_outer.T
            R_tilt_inner = RotationMatrices.R_X(self.inner_axis_tilt)
            R_inner = R_tilt_inner @ RotationMatrices.R_Z(self.phi) @ R_tilt_inner.T
            R_total = R_inner @ R_outer
            g_sample = R_total @ np.array([0, 0, -1], dtype=np.float64)
        else:
            R_outer = RotationMatrices.R_Y(self.psi)
            R_inner = RotationMatrices.R_Z(self.phi)
            R_total = R_outer @ R_inner
            g_sample = RotationMatrices.compute_gravity_vector(self.phi, self.psi)
        
        g_mag = np.linalg.norm(g_sample)
        if g_mag > 0:
            g_sample = g_sample / g_mag
        
        # Center history accumulation (taSMG at COR)
        self.gravity_sum += g_sample
        self.gravity_history.append(g_sample.copy())
        if len(self.gravity_history) > self.max_history:
            self.gravity_sum -= self.gravity_history.pop(0)
        
        n_samples = len(self.gravity_history)
        avg_gravity = self.gravity_sum / n_samples if n_samples > 0 else np.zeros(3)
        mean_g = float(np.linalg.norm(avg_gravity))
        
        if n_samples > 50:
            self.min_g = min(self.min_g, mean_g)
            self.max_g = max(self.max_g, mean_g)
        
        # 2. VOLUMETRIC ACCELERATION FIELD AT SAMPLE EDGE (Wadhwa et al., MIT/Harvard 2026 Eq. 5)
        omega_outer_lab = np.array([0.0, self.omega_psi, 0.0], dtype=np.float64)
        omega_inner_lab = R_outer @ np.array([0.0, 0.0, self.omega_phi], dtype=np.float64)
        omega_total_lab = omega_outer_lab + omega_inner_lab
        omega_total_mag = float(np.linalg.norm(omega_total_lab))
        
        alpha_outer_lab = np.array([0.0, self.alpha_psi, 0.0], dtype=np.float64)
        alpha_inner_lab = R_outer @ np.array([0.0, 0.0, self.alpha_phi], dtype=np.float64)
        alpha_total_lab = alpha_outer_lab + alpha_inner_lab
        
        r_edge_sample = np.array([self.sample_radius_m, 0.0, 0.0], dtype=np.float64)
        r_edge_lab = R_total @ r_edge_sample
        
        # Centripetal acceleration in lab frame: a_cent = -ω × (ω × r)
        a_cent_lab = -np.cross(omega_total_lab, np.cross(omega_total_lab, r_edge_lab))
        a_cent_sample = R_total.T @ a_cent_lab
        centrifugal_accel_edge_g = float(np.linalg.norm(a_cent_sample) / EARTH_GRAVITY)
        
        # Euler acceleration in lab frame: a_euler = α × r
        a_euler_lab = np.cross(alpha_total_lab, r_edge_lab)
        a_euler_sample = R_total.T @ a_euler_lab
        
        # Total effective acceleration at sample edge in m/s²
        g_sample_ms2 = g_sample * EARTH_GRAVITY
        a_edge_sample_ms2 = g_sample_ms2 + a_cent_sample - a_euler_sample
        instantaneous_g_edge = float(np.linalg.norm(a_edge_sample_ms2) / EARTH_GRAVITY)
        
        # Accumulate edge acceleration vector in normalized g
        a_edge_g = a_edge_sample_ms2 / EARTH_GRAVITY
        self.edge_gravity_sum += a_edge_g
        self.edge_gravity_history.append(a_edge_g.copy())
        if len(self.edge_gravity_history) > self.max_history:
            self.edge_gravity_sum -= self.edge_gravity_history.pop(0)
        mean_g_edge = float(np.linalg.norm(self.edge_gravity_sum / len(self.edge_gravity_history)))
        
        # 3. MAXIMUM SAFE SAMPLE RADIUS FOR < 10^-3 g (Hasenstein & van Loon)
        if omega_total_mag > 1e-4:
            r_safe_m = (0.001 * EARTH_GRAVITY) / (omega_total_mag ** 2)
            safe_sample_radius_cm = float(min(50.0, r_safe_m * 100.0))
        else:
            safe_sample_radius_cm = 50.0
            
        # 4. REAL-TIME FINITE DIFFERENCE METHOD (FDM) UNSTEADY FLUID DYNAMICS (mPa)
        # Solves transient Navier-Stokes momentum diffusion equation at 50Hz, capturing reversal spikes
        shear_stress_mPa = self.fdm_solver.step(omega_total_mag, dt)
            
        self.time += dt
        gamma = self.get_gamma()
        
        return {
            "phi": self.phi,
            "psi": self.psi,
            "omega_phi": self.omega_phi,
            "omega_psi": self.omega_psi,
            "inner_axis_tilt": self.inner_axis_tilt,
            "outer_axis_tilt": self.outer_axis_tilt,
            "gravity_sample": g_sample,
            "avg_gravity": avg_gravity,
            "instant_g": 1.0,
            "mean_g": mean_g,
            "min_g": self.min_g if self.min_g != float('inf') else mean_g,
            "max_g": self.max_g if self.max_g > 0 else mean_g,
            "n_samples": n_samples,
            "time": self.time,
            "gamma": gamma,
            # Volumetric & Biomechanical metrics
            "sample_radius_cm": float(self.sample_radius_m * 100.0),
            "instantaneous_g_edge": instantaneous_g_edge,
            "mean_g_edge": mean_g_edge,
            "centrifugal_accel_edge_g": centrifugal_accel_edge_g,
            "safe_sample_radius_cm": safe_sample_radius_cm,
            "shear_stress_mPa": shear_stress_mPa,
            "operation_mode": self.mode,
            "direction_changes_count": self.direction_changes_count
        }


# =============================================================================
# CONNECTION MANAGER
# =============================================================================

class HardwareCommandQueue:
    """
    Thread-safe command queue for hardware communication.
    Prevents bottlenecks by batching/throttling commands.
    """
    
    def __init__(self, max_rate: float = 50.0):
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self.max_rate = max_rate  # Max commands per second
        self.min_interval = 1.0 / max_rate
        self.last_send_time = 0.0
        self._running = False
        self._task = None
        
        # Latest values (for coalescing rapid updates)
        self._latest_velocities = None
        self._latest_tilt = None
        
    async def start(self):
        """Start the command processor."""
        self._running = True
        self._task = asyncio.create_task(self._process_queue())
        logger.info("Hardware command queue started")
    
    async def stop(self):
        """Stop the command processor."""
        self._running = False
        if self._task:
            self._task.cancel()
            
    async def _process_queue(self):
        """Process commands from queue with rate limiting."""
        while self._running:
            try:
                # Wait for command
                cmd = await asyncio.wait_for(self.queue.get(), timeout=0.1)
                
                # Rate limiting
                now = time.time()
                elapsed = now - self.last_send_time
                if elapsed < self.min_interval:
                    await asyncio.sleep(self.min_interval - elapsed)
                
                # Send to hardware
                await self._send_to_hardware(cmd)
                self.last_send_time = time.time()
                
            except asyncio.TimeoutError:
                # Check for coalesced commands
                await self._send_coalesced_commands()
            except Exception as e:
                logger.error(f"Command queue error: {e}")
    
    async def _send_coalesced_commands(self):
        """Send any coalesced (batched) commands."""
        if self._latest_velocities:
            await self._send_to_hardware({
                'type': 'velocity',
                'data': self._latest_velocities
            })
            self._latest_velocities = None
            
        if self._latest_tilt:
            await self._send_to_hardware({
                'type': 'tilt',
                'data': self._latest_tilt
            })
            self._latest_tilt = None
    
    async def _send_to_hardware(self, cmd: dict):
        """
        Actual hardware communication.
        Override this for real hardware integration.
        """
        cmd_type = cmd.get('type', 'unknown')
        data = cmd.get('data', {})
        
        # Log the command (in production, send to serial/network)
        logger.debug(f"HW CMD [{cmd_type}]: {data}")
        
        # Placeholder for real hardware communication:
        # if self.serial_connection:
        #     self.serial_connection.write(json.dumps(cmd).encode())
        # elif self.network_connection:
        #     await self.network_connection.send(json.dumps(cmd))
    
    def queue_velocity(self, inner_rpm: float, outer_rpm: float):
        """Queue velocity command (coalesces rapid updates)."""
        self._latest_velocities = {
            'inner_rpm': inner_rpm,
            'outer_rpm': outer_rpm,
            'timestamp': time.time()
        }
        
    def queue_tilt(self, inner_tilt: float, outer_tilt: float):
        """Queue tilt command (coalesces rapid updates)."""
        self._latest_tilt = {
            'inner_tilt': inner_tilt,
            'outer_tilt': outer_tilt,
            'timestamp': time.time()
        }
        
    async def queue_immediate(self, cmd_type: str, data: dict):
        """Queue a command that needs immediate processing."""
        try:
            self.queue.put_nowait({
                'type': cmd_type,
                'data': data,
                'timestamp': time.time()
            })
        except asyncio.QueueFull:
            logger.warning(f"Command queue full, dropping {cmd_type}")


class ConnectionManager:
    """Manages hardware connections (serial, network, etc.)."""
    
    def __init__(self):
        self.connections: Dict[str, ConnectionInfo] = {}
        self._scan_interval = 5.0  # seconds
        self._last_scan = 0.0
        self.command_queue = HardwareCommandQueue()
        self.latest_imu: Dict[str, float] = {}
        self.active_device_name: Optional[str] = None
        self._hardware_connected: bool = False
    
    def is_hardware_connected(self) -> bool:
        return self._hardware_connected
        
    def get_latest_imu(self) -> Dict[str, float]:
        return self.latest_imu
        
    def update_telemetry(self, accel_x: float, accel_y: float, accel_z: float, device: str = "Hardware IMU"):
        self.latest_imu = {"accel_x": accel_x, "accel_y": accel_y, "accel_z": accel_z}
        self.active_device_name = device
        self._hardware_connected = True
    
    async def scan_connections(self) -> Dict[str, ConnectionInfo]:
        """Scan for available hardware connections."""
        import os
        import glob
        
        connections = {}
        
        # Scan serial ports
        try:
            if sys.platform == 'darwin':
                serial_ports = glob.glob('/dev/tty.usb*') + glob.glob('/dev/cu.usb*')
            elif sys.platform.startswith('linux'):
                serial_ports = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
            else:
                serial_ports = [f'COM{i}' for i in range(1, 20)]
            
            for port in serial_ports:
                conn_id = f"serial_{port.replace('/', '_')}"
                connections[conn_id] = ConnectionInfo(
                    type="serial",
                    port=port,
                    status="available",
                    device_name="Serial Device",
                    baudrate=115200
                )
        except Exception as e:
            logger.warning(f"Serial scan error: {e}")
        
        # Scan network (localhost RPM service)
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex(('localhost', 5000))
            sock.close()
            
            connections["network_localhost_5000"] = ConnectionInfo(
                type="network",
                port="5000",
                status="connected" if result == 0 else "disconnected",
                device_name="RPM Control Service",
                ip_address="127.0.0.1"
            )
        except Exception as e:
            logger.debug(f"Network scan: {e}")
        
        # gRPC service check
        connections["grpc_localhost_50051"] = ConnectionInfo(
            type="network",
            port="50051",
            status="disconnected",  # Would need actual check
            device_name="gRPC Streaming Service",
            ip_address="127.0.0.1"
        )
        
        # Simulated hardware connections
        connections["usb_rpm_controller"] = ConnectionInfo(
            type="usb",
            port="USB0",
            status="simulated",
            device_name="RPM Motor Controller (Simulated)"
        )
        
        connections["gpio_raspberry_pi"] = ConnectionInfo(
            type="gpio",
            port="GPIO",
            status="not_available",
            device_name="Raspberry Pi GPIO"
        )
        
        self.connections = connections
        return connections
    
    def get_connections_list(self) -> List[dict]:
        """Get connections as list of dicts."""
        return [conn.model_dump() for conn in self.connections.values()]


# =============================================================================
# SIMULATION ENGINE
# =============================================================================

class SimulationEngine:
    """
    Real-time simulation manager with WebSocket broadcasting.
    
    Features:
    - 50Hz physics simulation
    - 20Hz client broadcast (reduces network load)
    - Hardware command queueing (prevents bottlenecks)
    - Thread-safe state management
    """
    
    def __init__(self):
        self.simulator = MicrogravitySimulator()
        self.connection_manager = ConnectionManager()
        
        self.running = False
        self.dt = 0.02  # 50 Hz simulation
        self.broadcast_rate = 20  # 20 Hz to clients
        
        # Connected clients
        self.clients: Set[WebSocket] = set()
        
        # Current config - using paper notation
        self.omega_phi_rpm = 2.0   # Inner frame velocity (φ rotation around Z)
        self.omega_psi_rpm = 2.0   # Outer frame velocity (ψ rotation around Y)
        
        # Axis inclination
        self.inner_tilt_deg = 0.0
        self.outer_tilt_deg = 0.0
        
        # Target values for smooth transitions (server-side too)
        self._target_inner_rpm = 2.0
        self._target_outer_rpm = 2.0
        self._target_inner_tilt = 0.0
        self._target_outer_tilt = 0.0
        
        self.start_time = 0.0
        
        logger.info("Simulation engine initialized with paper equations (Eq. 2)")
    
    async def start_hardware_queue(self):
        """Start the hardware command queue processor."""
        await self.connection_manager.command_queue.start()
    
    async def stop_hardware_queue(self):
        """Stop the hardware command queue processor."""
        await self.connection_manager.command_queue.stop()
    
    def set_velocities(self, inner_rpm: float, outer_rpm: float):
        """
        Update target velocities in RPM.
        Queues command to hardware to prevent bottlenecks.
        """
        self.omega_phi_rpm = inner_rpm
        self.omega_psi_rpm = outer_rpm
        self.simulator.set_velocities(inner_rpm, outer_rpm)
        
        # Queue for hardware (coalesces rapid updates)
        self.connection_manager.command_queue.queue_velocity(inner_rpm, outer_rpm)
        logger.info(f"Velocities set: ω_φ={inner_rpm:.2f} RPM, ω_ψ={outer_rpm:.2f} RPM")
    
    def set_axis_inclination(self, inner_tilt: float, outer_tilt: float):
        """
        Set axis inclination angles in degrees.
        Queues command to hardware to prevent bottlenecks.
        """
        self.inner_tilt_deg = inner_tilt
        self.outer_tilt_deg = outer_tilt
        self.simulator.set_axis_inclination(inner_tilt, outer_tilt)
        
        # Queue for hardware (coalesces rapid updates)
        self.connection_manager.command_queue.queue_tilt(inner_tilt, outer_tilt)
        logger.info(f"Axis inclination: inner={inner_tilt}°, outer={outer_tilt}°")
    
    def set_operation_mode(self, mode: str):
        """Set operation mode (clinostat_3d, clinostat_optimal, rpm_stochastic)."""
        self.simulator.set_mode(mode)
        logger.info(f"Engine operation mode set to: {mode}")

    def set_sample_radius(self, radius_cm: float):
        """Set sample radius in cm for volumetric calculations."""
        self.simulator.set_sample_radius(radius_cm)
        logger.info(f"Engine sample radius set to: {radius_cm:.1f} cm")

    def set_frame_dimensions(self, inner_l: float, inner_b: float,
                            outer_l: float, outer_b: float):
        """Set frame dimensions."""
        self.simulator.set_frame_dimensions(inner_l, inner_b, outer_l, outer_b)
    
    def start(self):
        """Start simulation."""
        self.running = True
        self.start_time = time.time()
        self.simulator.start_time = self.start_time
        self.set_velocities(self.omega_phi_rpm, self.omega_psi_rpm)
        logger.info("Simulation started")
    
    def stop(self):
        """Stop simulation."""
        self.running = False
        logger.info("Simulation stopped")
    
    def reset(self):
        """Reset simulation state."""
        self.simulator.reset()
        self.start_time = time.time()
        self.set_velocities(self.omega_phi_rpm, self.omega_psi_rpm)
        logger.info("Simulation reset")
    
    def step(self) -> SimulationState:
        """Execute one simulation step using paper physics."""
        result = self.simulator.step(self.dt)
        
        # Convert angles to display degrees (mod 360 for display)
        phi_display = float(np.degrees(result["phi"])) % 360
        psi_display = float(np.degrees(result["psi"])) % 360
        
        # Real-time hardware telemetry discrepancy check
        hw_connected = self.connection_manager.is_hardware_connected()
        latest_imu = self.connection_manager.get_latest_imu()
        imu_ax = latest_imu.get("accel_x", None)
        imu_ay = latest_imu.get("accel_y", None)
        imu_az = latest_imu.get("accel_z", None)
        
        telemetry_residual_g = None
        if hw_connected and imu_ax is not None and imu_ay is not None and imu_az is not None:
            a_imu = np.array([imu_ax, imu_ay, imu_az], dtype=np.float64) / EARTH_GRAVITY
            a_sim = result["gravity_sample"]
            telemetry_residual_g = float(np.linalg.norm(a_imu - a_sim))

        return SimulationState(
            timestamp=time.time(),
            time_elapsed=time.time() - self.start_time,
            # Use phi/psi notation from paper
            phi_deg=phi_display,
            psi_deg=psi_display,
            omega_phi_rpm=float(result["omega_phi"] * 30 / np.pi),
            omega_psi_rpm=float(result["omega_psi"] * 30 / np.pi),
            # Axis inclination
            inner_axis_tilt_deg=float(np.degrees(result["inner_axis_tilt"])),
            outer_axis_tilt_deg=float(np.degrees(result["outer_axis_tilt"])),
            # Gravity components
            gravity_x=float(result["gravity_sample"][0]),
            gravity_y=float(result["gravity_sample"][1]),
            gravity_z=float(result["gravity_sample"][2]),
            avg_gravity_x=float(result["avg_gravity"][0]),
            avg_gravity_y=float(result["avg_gravity"][1]),
            avg_gravity_z=float(result["avg_gravity"][2]),
            # Microgravity metrics (COR center)
            instantaneous_g=float(result["instant_g"]),
            mean_g=float(result["mean_g"]),
            min_g=float(result["min_g"]),
            max_g=float(result["max_g"]),
            # Velocity ratio γ = ω_φ/ω_ψ
            gamma=float(result["gamma"]) if result["gamma"] != float('inf') else 999.9,
            samples=int(result["n_samples"]),
            status="running" if self.running else "stopped",
            # Frame dimensions
            inner_length=self.simulator.inner_length,
            inner_breadth=self.simulator.inner_breadth,
            outer_length=self.simulator.outer_length,
            outer_breadth=self.simulator.outer_breadth,
            # Volumetric & Biomechanical metrics (Wadhwa et al. & van Loon)
            sample_radius_cm=float(result["sample_radius_cm"]),
            instantaneous_g_edge=float(result["instantaneous_g_edge"]),
            mean_g_edge=float(result["mean_g_edge"]),
            centrifugal_accel_edge_g=float(result["centrifugal_accel_edge_g"]),
            safe_sample_radius_cm=float(result["safe_sample_radius_cm"]),
            shear_stress_mPa=float(result["shear_stress_mPa"]),
            operation_mode=str(result["operation_mode"]),
            direction_changes_count=int(result["direction_changes_count"]),
            # Hardware Telemetry Coupling
            hardware_connected=hw_connected,
            hardware_device=self.connection_manager.active_device_name,
            imu_accel_x=imu_ax,
            imu_accel_y=imu_ay,
            imu_accel_z=imu_az,
            telemetry_residual_g=telemetry_residual_g
        )
    
    async def broadcast(self, state: SimulationState):
        """Send state to all connected clients."""
        if not self.clients:
            return
        
        message = json.dumps(state.model_dump())
        disconnected = set()
        
        for client in self.clients:
            try:
                await client.send_text(message)
            except Exception:
                disconnected.add(client)
        
        self.clients -= disconnected
    
    async def run_loop(self):
        """Main simulation loop with broadcasting."""
        broadcast_interval = 1.0 / self.broadcast_rate
        last_broadcast = 0.0
        
        while True:
            if self.running:
                state = self.step()
                
                now = time.time()
                if now - last_broadcast >= broadcast_interval:
                    await self.broadcast(state)
                    last_broadcast = now
                
                await asyncio.sleep(self.dt)
            else:
                await asyncio.sleep(0.1)


# Global simulation engine
engine = SimulationEngine()


# =============================================================================
# APPLICATION LIFESPAN
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    # Startup
    await engine.start_hardware_queue()
    asyncio.create_task(engine.run_loop())
    logger.info("RPM Digital Twin server started")
    logger.info("Hardware command queue active - ready for sensor connections")
    yield
    # Shutdown
    await engine.stop_hardware_queue()
    logger.info("RPM Digital Twin server stopped")


app = FastAPI(
    title="RPM Digital Twin",
    description="Commercial-grade Random Positioning Machine Control System",
    version="2.0.0",
    lifespan=lifespan
)

# CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include hardware tests router
if HAS_HARDWARE_TESTS:
    app.include_router(hardware_router)
    logger.info("Hardware tests API mounted at /api/hardware")


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve main dashboard."""
    html_path = Path(__file__).parent / "static" / "index.html"
    return FileResponse(html_path)


@app.get("/api/status")
async def get_status():
    """Get current simulation status."""
    return {
        "running": engine.running,
        "inner_rpm": engine.omega_phi_rpm,
        "outer_rpm": engine.omega_psi_rpm,
        "mode": engine.simulator.mode,
        "sample_radius_cm": float(engine.simulator.sample_radius_m * 100.0),
        "samples": len(engine.simulator.gravity_history),
        "clients": len(engine.clients)
    }


@app.get("/api/connections")
async def get_connections():
    """Get available hardware connections."""
    connections = await engine.connection_manager.scan_connections()
    return {
        "connections": engine.connection_manager.get_connections_list(),
        "timestamp": time.time()
    }


@app.post("/api/start")
async def start_simulation():
    """Start the simulation."""
    engine.start()
    return {"status": "started"}


@app.post("/api/stop")
async def stop_simulation():
    """Stop the simulation."""
    engine.stop()
    return {"status": "stopped"}


@app.post("/api/reset")
async def reset_simulation():
    """Reset the simulation."""
    engine.reset()
    return {"status": "reset"}


@app.post("/api/config")
async def update_config(config: SimulationConfig):
    """Update simulation configuration."""
    engine.set_velocities(config.inner_rpm, config.outer_rpm)
    if config.mode:
        engine.set_operation_mode(config.mode)
    if config.sample_radius_cm:
        engine.set_sample_radius(config.sample_radius_cm)
    
    if config.frame_dimensions:
        engine.set_frame_dimensions(
            config.frame_dimensions.inner_length,
            config.frame_dimensions.inner_breadth,
            config.frame_dimensions.outer_length,
            config.frame_dimensions.outer_breadth
        )
    
    if config.axis_inclination:
        engine.set_axis_inclination(
            config.axis_inclination.inner_axis_tilt,
            config.axis_inclination.outer_axis_tilt
        )
    
    return {"status": "updated", "config": config.model_dump()}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time data streaming."""
    await websocket.accept()
    engine.clients.add(websocket)
    logger.info(f"Client connected. Total clients: {len(engine.clients)}")
    
    try:
        while True:
            # Handle incoming commands
            data = await websocket.receive_text()
            try:
                cmd = json.loads(data)
                action = cmd.get("action")
                
                if action == "start":
                    engine.start()
                elif action == "stop":
                    engine.stop()
                elif action == "reset":
                    engine.reset()
                elif action == "config":
                    if "inner_rpm" in cmd and "outer_rpm" in cmd:
                        engine.set_velocities(
                            float(cmd.get("inner_rpm", 2.0)),
                            float(cmd.get("outer_rpm", 2.0))
                        )
                    if "mode" in cmd:
                        engine.set_operation_mode(cmd.get("mode"))
                    if "sample_radius_cm" in cmd:
                        engine.set_sample_radius(float(cmd.get("sample_radius_cm")))
                elif action == "mode" or action == "operation_mode":
                    mode = cmd.get("mode") or cmd.get("operation_mode", "clinostat_3d")
                    engine.set_operation_mode(mode)
                elif action == "sample_radius":
                    radius = float(cmd.get("radius_cm", 5.0))
                    engine.set_sample_radius(radius)
                elif action == "frame_dimensions":
                    engine.set_frame_dimensions(
                        cmd.get("inner_length", 0.30),
                        cmd.get("inner_breadth", 0.20),
                        cmd.get("outer_length", 0.50),
                        cmd.get("outer_breadth", 0.35)
                    )
                elif action == "axis_inclination":
                    engine.set_axis_inclination(
                        cmd.get("inner_tilt", 0.0),
                        cmd.get("outer_tilt", 0.0)
                    )
                elif action == "scan_connections":
                    connections = await engine.connection_manager.scan_connections()
                    await websocket.send_text(json.dumps({
                        "type": "connections",
                        "data": engine.connection_manager.get_connections_list()
                    }))
                    
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        engine.clients.discard(websocket)
        logger.info(f"Client disconnected. Total clients: {len(engine.clients)}")


# =============================================================================
# MAIN ENTRY
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    threading.Timer(1.0, _open_dashboard_in_browser, args=("http://localhost:8080",)).start()
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )
