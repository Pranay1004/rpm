"""
RPM Physics Engine - Core Kinematics and Microgravity Calculations

This module implements the mathematical model for the Random Positioning Machine
based on the theoretical framework from peer-reviewed literature.

Coordinate Systems:
- O_XYZ: Fixed inertial frame (lab frame), origin at rotation center
- O_x'y'z': Outer frame coordinate system (î, ĵ, k̂)  
- O_xyz: Inner frame coordinate system (ē_x, ē_y, ē_z)

Rotation Conventions:
- Outer frame: Rotates about Y-axis at angle φ (phi)
- Inner frame: Rotates about Z-axis at angle ψ (psi) relative to outer frame

Key Equations from Reference Paper:
- R_Y (outer rotation matrix about Y-axis)
- R_Z (inner rotation matrix about Z-axis)
- Gravity vector transformation: ē_g = -sin(φ)cos(ψ)ē_x + sin(φ)sin(ψ)ē_y + cos(φ)ē_z
- Angular velocity: ω̄ = ω_ψ sin(φ)ē_x + ω_ψ cos(φ)ē_y + ω_φ ē_z
- Gravity vector tip velocity: v̄_g = ω̄ × ē_g

Copyright (c) 2026 Space Research Laboratory
"""

import numpy as np
from numpy.typing import NDArray
from scipy import signal
from scipy.integrate import cumulative_trapezoid
from dataclasses import dataclass, field
from typing import Tuple, Optional, List, Dict, Any
from enum import Enum
import threading
import time
from loguru import logger


class RotationMode(Enum):
    """RPM operation modes."""
    RANDOM = "random"
    CONSTANT = "constant"
    CLINOSTAT_2D = "clinostat_2d"
    CLINOSTAT_3D = "clinostat_3d"
    CUSTOM = "custom"


@dataclass
class RPMState:
    """Complete state of the RPM at a given instant."""
    timestamp: float = 0.0
    
    # Angular positions (radians)
    theta_outer: float = 0.0  # φ - Outer frame angle about Y-axis
    theta_inner: float = 0.0  # ψ - Inner frame angle about Z-axis
    
    # Angular velocities (rad/s)
    omega_outer: float = 0.0  # ω_φ = dφ/dt
    omega_inner: float = 0.0  # ω_ψ = dψ/dt
    
    # Angular accelerations (rad/s²)
    alpha_outer: float = 0.0
    alpha_inner: float = 0.0
    
    # Gravity vector in payload frame (normalized)
    gravity_vector: NDArray[np.float64] = field(default_factory=lambda: np.array([0.0, -1.0, 0.0]))
    
    # Centripetal acceleration at sample point (m/s²)
    centripetal_acceleration: NDArray[np.float64] = field(default_factory=lambda: np.zeros(3))
    
    # Total effective acceleration on sample (m/s²)
    effective_acceleration: NDArray[np.float64] = field(default_factory=lambda: np.zeros(3))
    
    # Rotation matrices
    R_outer: NDArray[np.float64] = field(default_factory=lambda: np.eye(3))
    R_inner: NDArray[np.float64] = field(default_factory=lambda: np.eye(3))
    R_total: NDArray[np.float64] = field(default_factory=lambda: np.eye(3))


@dataclass
class MicrogravityMetrics:
    """Microgravity quality metrics."""
    # Time-averaged simulated microgravity (taSMG)
    taSMG: float = 0.0
    
    # Time-averaged gravity vector magnitude
    g_avg_magnitude: float = 0.0
    g_avg_vector: NDArray[np.float64] = field(default_factory=lambda: np.zeros(3))
    
    # Centripetal residual acceleration
    centripetal_rms: float = 0.0
    centripetal_max: float = 0.0
    
    # Total effective acceleration metrics
    effective_rms: float = 0.0
    effective_max: float = 0.0
    
    # Angular velocity ratio γ = ω_ψ / ω_φ
    gamma: float = 0.0
    
    # Coverage metrics (sphere coverage)
    sphere_coverage_percentage: float = 0.0
    
    # Time parameters
    analysis_duration: float = 0.0
    sample_count: int = 0


class RPMPhysicsEngine:
    """
    Core physics engine for Random Positioning Machine simulation and analysis.
    
    Implements the complete kinematic model for a two-axis RPM including:
    - Rotation matrix calculations (R_Y, R_Z)
    - Gravity vector transformation to payload frame
    - Centripetal acceleration computation
    - Time-averaged microgravity (taSMG) calculation
    - Random motor control algorithm
    
    Based on: "Random Positioning Machine for Microgravity Simulation"
    Reference equations (1)-(5) from the theoretical framework.
    """
    
    # Physical constants
    G_MAGNITUDE = 9.81  # m/s²
    G_VECTOR_INERTIAL = np.array([0.0, -9.81, 0.0])  # Gravity in inertial frame (Y-down)
    
    def __init__(
        self,
        max_angular_velocity: float = 1.047,  # rad/s (≈10 RPM)
        max_angular_acceleration: float = 10.0,  # rad/s²
        sample_radius: float = 0.10,  # m (distance from center to sample point)
        dt: float = 0.01,  # Time step (s)
    ):
        """
        Initialize the RPM Physics Engine.
        
        Args:
            max_angular_velocity: Maximum angular velocity (rad/s), default ~10 RPM
            max_angular_acceleration: Maximum angular acceleration (rad/s²)
            sample_radius: Distance from rotation center to sample point (m)
            dt: Simulation time step (s)
        """
        self.omega_max = max_angular_velocity
        self.alpha_max = max_angular_acceleration
        self.sample_radius = sample_radius
        self.dt = dt
        
        # Sample point in payload frame (initial position)
        self.r_sample = np.array([sample_radius, 0.0, 0.0])
        
        # Current state
        self.state = RPMState()
        
        # State history for analysis
        self.state_history: List[RPMState] = []
        self.max_history_length = 100000  # ~1000s at 100Hz
        
        # Random controller state (persistent accelerations)
        self._alpha_outer_persistent = 0.0
        self._alpha_inner_persistent = 0.0
        self._velocity_change_probability = 0.001
        
        # Thread safety
        self._lock = threading.Lock()
        
        logger.info(
            f"RPM Physics Engine initialized: "
            f"ω_max={self.omega_max:.3f} rad/s ({self.omega_max * 60 / (2*np.pi):.1f} RPM), "
            f"α_max={self.alpha_max:.1f} rad/s², "
            f"r_sample={self.sample_radius:.3f} m"
        )
    
    def rotation_matrix_Y(self, phi: float) -> NDArray[np.float64]:
        """
        Rotation matrix for outer frame about Y-axis (pitch).
        
        R_Y = | cos(φ)   0   sin(φ) |
              |   0      1     0    |
              |-sin(φ)   0   cos(φ) |
        
        Args:
            phi: Rotation angle (radians)
            
        Returns:
            3x3 rotation matrix
        """
        c, s = np.cos(phi), np.sin(phi)
        return np.array([
            [c,  0, s],
            [0,  1, 0],
            [-s, 0, c]
        ], dtype=np.float64)
    
    def rotation_matrix_Z(self, psi: float) -> NDArray[np.float64]:
        """
        Rotation matrix for inner frame about Z-axis (yaw).
        
        R_Z = | cos(ψ)  -sin(ψ)  0 |
              | sin(ψ)   cos(ψ)  0 |
              |   0        0     1 |
        
        Args:
            psi: Rotation angle (radians)
            
        Returns:
            3x3 rotation matrix
        """
        c, s = np.cos(psi), np.sin(psi)
        return np.array([
            [c, -s, 0],
            [s,  c, 0],
            [0,  0, 1]
        ], dtype=np.float64)
    
    def compute_total_rotation(
        self, 
        theta_outer: float, 
        theta_inner: float
    ) -> Tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
        """
        Compute complete rotation matrices for current configuration.
        
        The total rotation from inertial frame to payload frame is:
        R_total = R_Z(ψ) · R_Y(φ)
        
        Args:
            theta_outer: Outer frame angle φ (radians)
            theta_inner: Inner frame angle ψ (radians)
            
        Returns:
            Tuple of (R_outer, R_inner, R_total)
        """
        R_outer = self.rotation_matrix_Y(theta_outer)
        R_inner = self.rotation_matrix_Z(theta_inner)
        R_total = R_inner @ R_outer
        return R_outer, R_inner, R_total
    
    def compute_gravity_in_payload_frame(
        self, 
        theta_outer: float, 
        theta_inner: float
    ) -> NDArray[np.float64]:
        """
        Compute gravity vector in payload (inner frame) coordinate system.
        
        From reference paper equation (2):
        ē_g = -sin(φ)cos(ψ)ē_x + sin(φ)sin(ψ)ē_y + cos(φ)ē_z
        
        Normalized to unit vector, multiply by G_MAGNITUDE for actual acceleration.
        
        Args:
            theta_outer: Outer frame angle φ (radians)  
            theta_inner: Inner frame angle ψ (radians)
            
        Returns:
            Gravity unit vector in payload frame [g_x, g_y, g_z]
        """
        phi, psi = theta_outer, theta_inner
        
        # Unit gravity vector in payload frame (equation 2)
        g_x = -np.sin(phi) * np.cos(psi)
        g_y = np.sin(phi) * np.sin(psi)
        g_z = np.cos(phi)
        
        return np.array([g_x, g_y, g_z], dtype=np.float64)
    
    def compute_angular_velocity_payload_frame(
        self,
        omega_outer: float,
        omega_inner: float,
        theta_outer: float
    ) -> NDArray[np.float64]:
        """
        Compute total angular velocity vector in payload frame.
        
        From reference paper equation (3):
        ω̄ = ω_ψ sin(φ)ē_x + ω_ψ cos(φ)ē_y + ω_φ ē_z
        
        Args:
            omega_outer: Outer frame angular velocity ω_φ (rad/s)
            omega_inner: Inner frame angular velocity ω_ψ (rad/s)
            theta_outer: Outer frame angle φ (radians)
            
        Returns:
            Angular velocity vector in payload frame [ω_x, ω_y, ω_z]
        """
        phi = theta_outer
        
        omega_x = omega_inner * np.sin(phi)
        omega_y = omega_inner * np.cos(phi)
        omega_z = omega_outer
        
        return np.array([omega_x, omega_y, omega_z], dtype=np.float64)
    
    def compute_gravity_tip_velocity(
        self,
        omega_outer: float,
        omega_inner: float,
        theta_outer: float,
        theta_inner: float
    ) -> NDArray[np.float64]:
        """
        Compute linear velocity of gravity vector tip on unit sphere.
        
        From reference paper equation (4):
        v̄_g = ω̄ × ē_g = (ω_φ cos(φ)cos(ψ) - ω_ψ sin(φ)sin(ψ))ē_x 
                        - (ω_φ sin(φ)cos(ψ) + ω_ψ sin(φ)cos(ψ))ē_y 
                        + ω_ψ sin(ψ)ē_z
        
        This velocity indicates how fast the gravity vector is moving,
        which affects the uniformity of sphere coverage.
        
        Args:
            omega_outer: ω_φ (rad/s)
            omega_inner: ω_ψ (rad/s)
            theta_outer: φ (radians)
            theta_inner: ψ (radians)
            
        Returns:
            Gravity tip velocity vector in payload frame
        """
        omega_vec = self.compute_angular_velocity_payload_frame(
            omega_outer, omega_inner, theta_outer
        )
        g_vec = self.compute_gravity_in_payload_frame(theta_outer, theta_inner)
        
        return np.cross(omega_vec, g_vec)
    
    def compute_centripetal_acceleration(
        self,
        omega_outer: float,
        omega_inner: float,
        theta_outer: float,
        r_sample: Optional[NDArray[np.float64]] = None
    ) -> NDArray[np.float64]:
        """
        Compute centripetal acceleration at a sample point.
        
        The centripetal acceleration is the main source of residual g in RPMs:
        a_c = -ω × (ω × r)
        
        This is the acceleration required to keep the sample moving in circular motion.
        
        Args:
            omega_outer: ω_φ (rad/s)
            omega_inner: ω_ψ (rad/s)
            theta_outer: φ (radians)
            r_sample: Sample position vector in payload frame (m)
            
        Returns:
            Centripetal acceleration vector (m/s²)
        """
        if r_sample is None:
            r_sample = self.r_sample
            
        omega_vec = self.compute_angular_velocity_payload_frame(
            omega_outer, omega_inner, theta_outer
        )
        
        # a_c = -ω × (ω × r)
        return -np.cross(omega_vec, np.cross(omega_vec, r_sample))
    
    def random_motor_controller(
        self,
        omega_curr_outer: float,
        omega_curr_inner: float,
    ) -> Tuple[float, float]:
        """
        Random positioning motor control algorithm.
        
        Generates next angular velocities for both motors using a random
        acceleration strategy. The acceleration direction changes randomly
        with low probability, bounded by maximum velocity and acceleration limits.
        
        Args:
            omega_curr_outer: Current outer frame angular velocity (rad/s)
            omega_curr_inner: Current inner frame angular velocity (rad/s)
            
        Returns:
            Tuple of (omega_next_outer, omega_next_inner)
        """
        # Initialize persistent accelerations if first call
        if self._alpha_outer_persistent == 0.0 and self._alpha_inner_persistent == 0.0:
            self._alpha_outer_persistent = self.alpha_max * (2 * np.random.random() - 1)
            self._alpha_inner_persistent = self.alpha_max * (2 * np.random.random() - 1)
        
        # --- Outer Frame Motor Control ---
        if np.random.random() < self._velocity_change_probability:
            self._alpha_outer_persistent = self.alpha_max * (2 * np.random.random() - 1)
        
        omega_next_outer = omega_curr_outer + self._alpha_outer_persistent * self.dt
        
        # Velocity limiting with acceleration reversal
        if omega_next_outer > self.omega_max:
            omega_next_outer = self.omega_max
            self._alpha_outer_persistent = -self.alpha_max
        elif omega_next_outer < -self.omega_max:
            omega_next_outer = -self.omega_max
            self._alpha_outer_persistent = self.alpha_max
            
        # --- Inner Frame Motor Control ---
        if np.random.random() < self._velocity_change_probability:
            self._alpha_inner_persistent = self.alpha_max * (2 * np.random.random() - 1)
        
        omega_next_inner = omega_curr_inner + self._alpha_inner_persistent * self.dt
        
        if omega_next_inner > self.omega_max:
            omega_next_inner = self.omega_max
            self._alpha_inner_persistent = -self.alpha_max
        elif omega_next_inner < -self.omega_max:
            omega_next_inner = -self.omega_max
            self._alpha_inner_persistent = self.alpha_max
        
        return omega_next_outer, omega_next_inner
    
    def step(
        self,
        omega_outer: Optional[float] = None,
        omega_inner: Optional[float] = None,
        mode: RotationMode = RotationMode.RANDOM
    ) -> RPMState:
        """
        Advance simulation by one time step.
        
        Args:
            omega_outer: Commanded outer frame velocity (rad/s), None for auto
            omega_inner: Commanded inner frame velocity (rad/s), None for auto
            mode: Rotation mode (RANDOM, CONSTANT, etc.)
            
        Returns:
            Updated RPM state
        """
        with self._lock:
            current_time = self.state.timestamp + self.dt
            
            # Get angular velocities based on mode
            if mode == RotationMode.RANDOM:
                omega_outer, omega_inner = self.random_motor_controller(
                    self.state.omega_outer,
                    self.state.omega_inner
                )
            elif mode == RotationMode.CONSTANT:
                if omega_outer is None:
                    omega_outer = self.state.omega_outer
                if omega_inner is None:
                    omega_inner = self.state.omega_inner
            else:
                omega_outer = omega_outer or 0.0
                omega_inner = omega_inner or 0.0
            
            # Compute accelerations
            alpha_outer = (omega_outer - self.state.omega_outer) / self.dt
            alpha_inner = (omega_inner - self.state.omega_inner) / self.dt
            
            # Update angular positions
            theta_outer = self.state.theta_outer + omega_outer * self.dt
            theta_inner = self.state.theta_inner + omega_inner * self.dt
            
            # Normalize angles to [0, 2π)
            theta_outer = theta_outer % (2 * np.pi)
            theta_inner = theta_inner % (2 * np.pi)
            
            # Compute rotation matrices
            R_outer, R_inner, R_total = self.compute_total_rotation(theta_outer, theta_inner)
            
            # Compute gravity in payload frame
            gravity_unit = self.compute_gravity_in_payload_frame(theta_outer, theta_inner)
            gravity_vector = gravity_unit * self.G_MAGNITUDE
            
            # Compute centripetal acceleration
            centripetal = self.compute_centripetal_acceleration(
                omega_outer, omega_inner, theta_outer
            )
            
            # Total effective acceleration on sample
            effective = gravity_vector + centripetal
            
            # Create new state
            self.state = RPMState(
                timestamp=current_time,
                theta_outer=theta_outer,
                theta_inner=theta_inner,
                omega_outer=omega_outer,
                omega_inner=omega_inner,
                alpha_outer=alpha_outer,
                alpha_inner=alpha_inner,
                gravity_vector=gravity_vector,
                centripetal_acceleration=centripetal,
                effective_acceleration=effective,
                R_outer=R_outer,
                R_inner=R_inner,
                R_total=R_total,
            )
            
            # Store in history
            self.state_history.append(self.state)
            if len(self.state_history) > self.max_history_length:
                self.state_history.pop(0)
            
            return self.state
    
    def compute_microgravity_metrics(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None
    ) -> MicrogravityMetrics:
        """
        Compute microgravity quality metrics over a time window.
        
        Metrics include:
        - taSMG: Time-averaged simulated microgravity
        - g_avg: Time-averaged gravity vector magnitude
        - Centripetal residual RMS and MAX
        - Angular velocity ratio γ
        
        Args:
            start_time: Analysis start time (s), None for beginning
            end_time: Analysis end time (s), None for end
            
        Returns:
            MicrogravityMetrics dataclass with computed values
        """
        with self._lock:
            if len(self.state_history) < 2:
                return MicrogravityMetrics()
            
            # Filter states by time window
            states = self.state_history
            if start_time is not None:
                states = [s for s in states if s.timestamp >= start_time]
            if end_time is not None:
                states = [s for s in states if s.timestamp <= end_time]
            
            if len(states) < 2:
                return MicrogravityMetrics()
            
            # Extract arrays for vectorized computation
            gravity_vectors = np.array([s.gravity_vector for s in states])
            centripetal_vectors = np.array([s.centripetal_acceleration for s in states])
            effective_vectors = np.array([s.effective_acceleration for s in states])
            omega_outers = np.array([s.omega_outer for s in states])
            omega_inners = np.array([s.omega_inner for s in states])
            
            # Time-averaged gravity vector
            g_avg_vector = np.mean(gravity_vectors, axis=0)
            g_avg_magnitude = np.linalg.norm(g_avg_vector)
            
            # Centripetal acceleration metrics
            centripetal_mags = np.linalg.norm(centripetal_vectors, axis=1)
            centripetal_rms = np.sqrt(np.mean(centripetal_mags**2))
            centripetal_max = np.max(centripetal_mags)
            
            # Effective acceleration metrics
            effective_mags = np.linalg.norm(effective_vectors, axis=1)
            effective_rms = np.sqrt(np.mean(effective_mags**2))
            effective_max = np.max(effective_mags)
            
            # taSMG: Time-averaged simulated microgravity
            # This is the RMS of the centripetal acceleration in units of g
            taSMG = centripetal_rms / self.G_MAGNITUDE
            
            # Angular velocity ratio γ = ω_ψ / ω_φ
            mean_omega_outer = np.mean(np.abs(omega_outers))
            mean_omega_inner = np.mean(np.abs(omega_inners))
            gamma = mean_omega_inner / mean_omega_outer if mean_omega_outer > 1e-6 else 0.0
            
            # Analysis duration
            duration = states[-1].timestamp - states[0].timestamp
            
            return MicrogravityMetrics(
                taSMG=taSMG,
                g_avg_magnitude=g_avg_magnitude / self.G_MAGNITUDE,  # in g units
                g_avg_vector=g_avg_vector / self.G_MAGNITUDE,
                centripetal_rms=centripetal_rms / self.G_MAGNITUDE,
                centripetal_max=centripetal_max / self.G_MAGNITUDE,
                effective_rms=effective_rms / self.G_MAGNITUDE,
                effective_max=effective_max / self.G_MAGNITUDE,
                gamma=gamma,
                analysis_duration=duration,
                sample_count=len(states),
            )
    
    def compute_microgravity_at_point(
        self,
        x: float,
        y: float,
        z: float,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Compute microgravity metrics at a specific 3D coordinate.
        
        This is the key function for comparing numerical predictions
        with experimental measurements at arbitrary sample positions.
        
        Args:
            x, y, z: Coordinates in payload frame (m)
            start_time: Analysis start time (s)
            end_time: Analysis end time (s)
            
        Returns:
            Dictionary with computed metrics at the specified point
        """
        r_point = np.array([x, y, z])
        r_magnitude = np.linalg.norm(r_point)
        
        with self._lock:
            if len(self.state_history) < 2:
                return {"error": "Insufficient data for analysis"}
            
            # Filter states
            states = self.state_history
            if start_time is not None:
                states = [s for s in states if s.timestamp >= start_time]
            if end_time is not None:
                states = [s for s in states if s.timestamp <= end_time]
            
            # Compute centripetal acceleration at the specified point for each state
            centripetal_at_point = []
            effective_at_point = []
            
            for state in states:
                omega_vec = self.compute_angular_velocity_payload_frame(
                    state.omega_outer, state.omega_inner, state.theta_outer
                )
                a_c = -np.cross(omega_vec, np.cross(omega_vec, r_point))
                centripetal_at_point.append(a_c)
                effective_at_point.append(state.gravity_vector + a_c)
            
            centripetal_array = np.array(centripetal_at_point)
            effective_array = np.array(effective_at_point)
            
            # Compute metrics
            centripetal_mags = np.linalg.norm(centripetal_array, axis=1)
            effective_mags = np.linalg.norm(effective_array, axis=1)
            
            return {
                "position": {"x": x, "y": y, "z": z},
                "distance_from_center": r_magnitude,
                "taSMG": np.sqrt(np.mean(centripetal_mags**2)) / self.G_MAGNITUDE,
                "centripetal_rms_g": np.sqrt(np.mean(centripetal_mags**2)) / self.G_MAGNITUDE,
                "centripetal_max_g": np.max(centripetal_mags) / self.G_MAGNITUDE,
                "effective_rms_g": np.sqrt(np.mean(effective_mags**2)) / self.G_MAGNITUDE,
                "effective_max_g": np.max(effective_mags) / self.G_MAGNITUDE,
                "analysis_duration_s": states[-1].timestamp - states[0].timestamp,
                "sample_count": len(states),
            }
    
    def reset(self):
        """Reset the physics engine to initial state."""
        with self._lock:
            self.state = RPMState()
            self.state_history.clear()
            self._alpha_outer_persistent = 0.0
            self._alpha_inner_persistent = 0.0
            logger.info("Physics engine reset to initial state")
    
    def set_velocity_change_probability(self, probability: float):
        """Set the probability of velocity change in random mode."""
        self._velocity_change_probability = np.clip(probability, 0.0, 1.0)
    
    def get_trajectory_data(self) -> Dict[str, NDArray[np.float64]]:
        """
        Get trajectory data for 3D visualization.
        
        Returns:
            Dictionary with time series data for plotting
        """
        with self._lock:
            if len(self.state_history) == 0:
                return {}
            
            states = self.state_history
            
            # Sample point trajectory in inertial frame
            r_inertial = []
            for s in states:
                r_payload = self.r_sample
                r_in = s.R_total @ r_payload
                r_inertial.append(r_in)
            
            return {
                "time": np.array([s.timestamp for s in states]),
                "theta_outer": np.array([s.theta_outer for s in states]),
                "theta_inner": np.array([s.theta_inner for s in states]),
                "omega_outer": np.array([s.omega_outer for s in states]),
                "omega_inner": np.array([s.omega_inner for s in states]),
                "gravity_x": np.array([s.gravity_vector[0] for s in states]),
                "gravity_y": np.array([s.gravity_vector[1] for s in states]),
                "gravity_z": np.array([s.gravity_vector[2] for s in states]),
                "centripetal_mag": np.array([np.linalg.norm(s.centripetal_acceleration) for s in states]),
                "effective_mag": np.array([np.linalg.norm(s.effective_acceleration) for s in states]),
                "trajectory_x": np.array([r[0] for r in r_inertial]),
                "trajectory_y": np.array([r[1] for r in r_inertial]),
                "trajectory_z": np.array([r[2] for r in r_inertial]),
            }


def run_simulation_demo():
    """Demonstration of the RPM Physics Engine."""
    logger.info("Starting RPM Physics Engine Demonstration")
    
    # Initialize engine
    engine = RPMPhysicsEngine(
        max_angular_velocity=1.047,  # ~10 RPM
        max_angular_acceleration=10.0,
        sample_radius=0.035,  # 3.5 cm from center (as in reference paper)
        dt=0.01
    )
    
    # Run simulation for 10 minutes
    simulation_time = 600  # seconds
    steps = int(simulation_time / engine.dt)
    
    logger.info(f"Running {simulation_time}s simulation ({steps} steps)...")
    
    start = time.time()
    for _ in range(steps):
        engine.step(mode=RotationMode.RANDOM)
    elapsed = time.time() - start
    
    logger.info(f"Simulation completed in {elapsed:.2f}s ({steps/elapsed:.0f} steps/s)")
    
    # Compute metrics
    metrics = engine.compute_microgravity_metrics()
    
    print("\n" + "="*60)
    print("MICROGRAVITY ANALYSIS RESULTS")
    print("="*60)
    print(f"Simulation Duration: {metrics.analysis_duration:.1f} s")
    print(f"Sample Count: {metrics.sample_count}")
    print(f"\n--- Microgravity Quality Metrics ---")
    print(f"taSMG (Time-Averaged Simulated Microgravity): {metrics.taSMG:.4f} g")
    print(f"Time-Averaged Gravity Vector Magnitude: {metrics.g_avg_magnitude:.2e} g")
    print(f"Centripetal Residual (RMS): {metrics.centripetal_rms:.4f} g")
    print(f"Centripetal Residual (MAX): {metrics.centripetal_max:.4f} g")
    print(f"Angular Velocity Ratio (γ): {metrics.gamma:.3f}")
    print("="*60)
    
    # Compute at specific point
    point_metrics = engine.compute_microgravity_at_point(0.035, 0.0, 0.0)
    print(f"\nMicrogravity at point (3.5cm, 0, 0):")
    print(f"  taSMG: {point_metrics['taSMG']:.4f} g")
    print(f"  Centripetal RMS: {point_metrics['centripetal_rms_g']:.4f} g")
    
    return engine, metrics


if __name__ == "__main__":
    run_simulation_demo()
