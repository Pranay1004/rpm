"""
Motor Controller - NEMA Motor Control Interface

This module handles motor control for the RPM's two-axis system:
- Outer Frame: NEMA 34 stepper motor (Z-axis rotation)
- Inner Frame: NEMA 23 stepper motor (Y-axis rotation)

Features:
- Velocity and position control modes
- RPM and rad/s unit conversion
- Acceleration limiting and ramping
- Safety interlocks and emergency stop
- Motor driver communication (via Arduino/driver board)

Hardware Configuration (from Bill of Materials):
- 2x NEMA 23 motors
- 2x NEMA 34 motors
- 2x Motor Drivers
- 2x Slip Rings (for continuous rotation power)

Copyright (c) 2026 Space Research Laboratory
"""

import threading
import time
import math
from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, Any, Tuple
from enum import Enum
import numpy as np
from loguru import logger


class MotorState(Enum):
    """Motor operational states."""
    IDLE = "idle"
    RUNNING = "running"
    ACCELERATING = "accelerating"
    DECELERATING = "decelerating"
    ERROR = "error"
    EMERGENCY_STOP = "emergency_stop"


class ControlMode(Enum):
    """Motor control modes."""
    VELOCITY = "velocity"
    POSITION = "position"
    RANDOM = "random"
    SYNCHRONIZED = "synchronized"


class VelocityUnit(Enum):
    """Velocity unit options."""
    RAD_PER_SEC = "rad/s"
    RPM = "rpm"
    DEG_PER_SEC = "deg/s"


@dataclass
class MotorConfig:
    """Configuration for a single motor."""
    name: str
    motor_type: str  # "NEMA23" or "NEMA34"
    steps_per_revolution: int = 200
    microstepping: int = 16
    gear_ratio: float = 1.0
    max_rpm: float = 10.0
    max_acceleration: float = 10.0  # rad/s²
    direction_inverted: bool = False
    
    # Computed properties
    @property
    def steps_per_rad(self) -> float:
        """Steps required for one radian of rotation."""
        return (self.steps_per_revolution * self.microstepping * self.gear_ratio) / (2 * math.pi)
    
    @property
    def max_omega(self) -> float:
        """Maximum angular velocity in rad/s."""
        return self.max_rpm * 2 * math.pi / 60
    
    def rpm_to_rads(self, rpm: float) -> float:
        """Convert RPM to rad/s."""
        return rpm * 2 * math.pi / 60
    
    def rads_to_rpm(self, rads: float) -> float:
        """Convert rad/s to RPM."""
        return rads * 60 / (2 * math.pi)


@dataclass
class MotorStatus:
    """Real-time motor status."""
    # Position and velocity
    position: float = 0.0  # radians
    velocity: float = 0.0  # rad/s
    target_velocity: float = 0.0  # rad/s
    acceleration: float = 0.0  # rad/s²
    
    # State
    state: MotorState = MotorState.IDLE
    mode: ControlMode = ControlMode.VELOCITY
    
    # Electrical
    current: float = 0.0  # Amps
    temperature: float = 25.0  # °C
    
    # Diagnostics
    step_count: int = 0
    error_count: int = 0
    last_error: str = ""
    
    # Timing
    last_update: float = 0.0


class Motor:
    """
    Single motor controller.
    
    Handles velocity control, acceleration ramping, and safety limits
    for one axis of the RPM.
    """
    
    def __init__(self, config: MotorConfig):
        self.config = config
        self.status = MotorStatus()
        
        # Control parameters
        self._target_velocity = 0.0
        self._current_velocity = 0.0
        self._position = 0.0
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Control loop
        self._running = False
        self._control_thread: Optional[threading.Thread] = None
        self._dt = 0.001  # 1ms control loop period
        
        logger.info(f"Motor initialized: {config.name} ({config.motor_type})")
    
    def set_velocity(self, velocity: float, unit: VelocityUnit = VelocityUnit.RAD_PER_SEC) -> bool:
        """
        Set target velocity.
        
        Args:
            velocity: Target velocity value
            unit: Velocity unit (rad/s, rpm, deg/s)
            
        Returns:
            True if command accepted
        """
        # Convert to rad/s
        if unit == VelocityUnit.RPM:
            velocity = self.config.rpm_to_rads(velocity)
        elif unit == VelocityUnit.DEG_PER_SEC:
            velocity = math.radians(velocity)
        
        # Apply limits
        if abs(velocity) > self.config.max_omega:
            velocity = math.copysign(self.config.max_omega, velocity)
            logger.warning(f"{self.config.name}: Velocity limited to {velocity:.3f} rad/s")
        
        # Apply direction inversion
        if self.config.direction_inverted:
            velocity = -velocity
        
        with self._lock:
            self._target_velocity = velocity
            self.status.target_velocity = velocity
            self.status.state = MotorState.ACCELERATING if velocity != 0 else MotorState.DECELERATING
        
        logger.debug(f"{self.config.name}: Set velocity to {velocity:.3f} rad/s")
        return True
    
    def get_velocity(self, unit: VelocityUnit = VelocityUnit.RAD_PER_SEC) -> float:
        """Get current velocity in specified units."""
        with self._lock:
            velocity = self._current_velocity
        
        if unit == VelocityUnit.RPM:
            return self.config.rads_to_rpm(velocity)
        elif unit == VelocityUnit.DEG_PER_SEC:
            return math.degrees(velocity)
        return velocity
    
    def get_position(self) -> float:
        """Get current position in radians."""
        with self._lock:
            return self._position
    
    def stop(self, emergency: bool = False) -> None:
        """
        Stop the motor.
        
        Args:
            emergency: If True, stop immediately without deceleration
        """
        with self._lock:
            if emergency:
                self._current_velocity = 0.0
                self._target_velocity = 0.0
                self.status.velocity = 0.0
                self.status.target_velocity = 0.0
                self.status.state = MotorState.EMERGENCY_STOP
                logger.warning(f"{self.config.name}: EMERGENCY STOP")
            else:
                self._target_velocity = 0.0
                self.status.target_velocity = 0.0
                self.status.state = MotorState.DECELERATING
    
    def start_control_loop(self) -> None:
        """Start the motor control loop in background thread."""
        if self._running:
            return
        
        self._running = True
        self._control_thread = threading.Thread(target=self._control_loop, daemon=True)
        self._control_thread.start()
        logger.info(f"{self.config.name}: Control loop started")
    
    def stop_control_loop(self) -> None:
        """Stop the motor control loop."""
        self._running = False
        if self._control_thread:
            self._control_thread.join(timeout=1.0)
        logger.info(f"{self.config.name}: Control loop stopped")
    
    def _control_loop(self) -> None:
        """Background control loop for velocity ramping."""
        last_time = time.perf_counter()
        
        while self._running:
            current_time = time.perf_counter()
            dt = current_time - last_time
            last_time = current_time
            
            with self._lock:
                # Velocity ramping with acceleration limit
                velocity_error = self._target_velocity - self._current_velocity
                
                if abs(velocity_error) > 1e-6:
                    # Calculate maximum velocity change this step
                    max_dv = self.config.max_acceleration * dt
                    
                    if abs(velocity_error) <= max_dv:
                        self._current_velocity = self._target_velocity
                    else:
                        self._current_velocity += math.copysign(max_dv, velocity_error)
                    
                    self.status.acceleration = velocity_error / dt if dt > 0 else 0
                else:
                    self.status.acceleration = 0.0
                    if self._current_velocity != 0:
                        self.status.state = MotorState.RUNNING
                    else:
                        self.status.state = MotorState.IDLE
                
                # Update position
                self._position += self._current_velocity * dt
                self._position = self._position % (2 * math.pi)  # Normalize to [0, 2π)
                
                # Update status
                self.status.velocity = self._current_velocity
                self.status.position = self._position
                self.status.last_update = current_time
            
            # Sleep for control loop period
            sleep_time = self._dt - (time.perf_counter() - current_time)
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def get_status(self) -> Dict[str, Any]:
        """Get complete motor status as dictionary."""
        with self._lock:
            return {
                'name': self.config.name,
                'type': self.config.motor_type,
                'position_rad': self.status.position,
                'position_deg': math.degrees(self.status.position),
                'velocity_rad_s': self.status.velocity,
                'velocity_rpm': self.config.rads_to_rpm(self.status.velocity),
                'target_velocity_rad_s': self.status.target_velocity,
                'target_velocity_rpm': self.config.rads_to_rpm(self.status.target_velocity),
                'acceleration': self.status.acceleration,
                'state': self.status.state.value,
                'temperature': self.status.temperature,
            }


class MotorController:
    """
    Dual-axis motor controller for the RPM.
    
    Manages both outer and inner frame motors with:
    - Coordinated velocity control
    - Random positioning algorithm
    - Safety monitoring
    - Communication with motor drivers
    """
    
    def __init__(
        self,
        outer_config: Optional[MotorConfig] = None,
        inner_config: Optional[MotorConfig] = None,
    ):
        # Default configurations based on Bill of Materials
        if outer_config is None:
            outer_config = MotorConfig(
                name="Outer Frame",
                motor_type="NEMA34",
                max_rpm=10.0,
                max_acceleration=10.0,
            )
        
        if inner_config is None:
            inner_config = MotorConfig(
                name="Inner Frame",
                motor_type="NEMA23",
                max_rpm=10.0,
                max_acceleration=10.0,
            )
        
        self.outer_motor = Motor(outer_config)
        self.inner_motor = Motor(inner_config)
        
        # Control mode
        self.mode = ControlMode.VELOCITY
        
        # Random positioning state
        self._random_enabled = False
        self._random_thread: Optional[threading.Thread] = None
        self._velocity_change_probability = 0.001
        
        # Safety
        self._emergency_stop_active = False
        self._safety_callbacks: list[Callable[[], None]] = []
        
        # Serial interface for motor driver communication
        self._serial_interface = None
        
        # Thread safety
        self._lock = threading.Lock()
        
        logger.info("MotorController initialized for dual-axis RPM")
    
    def connect(self, serial_interface=None) -> bool:
        """Connect to motor driver hardware."""
        if serial_interface:
            self._serial_interface = serial_interface
            logger.info("Connected to motor driver via serial interface")
        return True
    
    def start(self) -> None:
        """Start motor control loops."""
        self.outer_motor.start_control_loop()
        self.inner_motor.start_control_loop()
        logger.info("Motor control loops started")
    
    def stop(self) -> None:
        """Stop motor control loops."""
        self.outer_motor.stop_control_loop()
        self.inner_motor.stop_control_loop()
        logger.info("Motor control loops stopped")
    
    def set_velocities(
        self,
        omega_outer: float,
        omega_inner: float,
        unit: VelocityUnit = VelocityUnit.RAD_PER_SEC
    ) -> bool:
        """
        Set velocities for both motors.
        
        Args:
            omega_outer: Outer frame velocity
            omega_inner: Inner frame velocity
            unit: Velocity unit
            
        Returns:
            True if commands accepted
        """
        if self._emergency_stop_active:
            logger.warning("Cannot set velocities: Emergency stop active")
            return False
        
        success_outer = self.outer_motor.set_velocity(omega_outer, unit)
        success_inner = self.inner_motor.set_velocity(omega_inner, unit)
        
        # Send to hardware if connected
        if self._serial_interface:
            omega_outer_rads = omega_outer if unit == VelocityUnit.RAD_PER_SEC else self.outer_motor.config.rpm_to_rads(omega_outer)
            omega_inner_rads = omega_inner if unit == VelocityUnit.RAD_PER_SEC else self.inner_motor.config.rpm_to_rads(omega_inner)
            self._serial_interface.set_motor_velocity(omega_outer_rads, omega_inner_rads)
        
        return success_outer and success_inner
    
    def get_velocities(self, unit: VelocityUnit = VelocityUnit.RAD_PER_SEC) -> Tuple[float, float]:
        """Get current velocities for both motors."""
        return (
            self.outer_motor.get_velocity(unit),
            self.inner_motor.get_velocity(unit)
        )
    
    def get_positions(self) -> Tuple[float, float]:
        """Get current positions for both motors in radians."""
        return (
            self.outer_motor.get_position(),
            self.inner_motor.get_position()
        )
    
    def start_random_positioning(
        self,
        max_velocity: float = 1.047,  # rad/s (~10 RPM)
        max_acceleration: float = 10.0,
        velocity_change_prob: float = 0.001
    ) -> None:
        """
        Start random positioning mode.
        
        The algorithm randomly changes acceleration direction with low probability,
        ensuring uniform coverage of the gravity vector on a unit sphere.
        """
        if self._random_enabled:
            return
        
        self._velocity_change_probability = velocity_change_prob
        self._random_enabled = True
        self.mode = ControlMode.RANDOM
        
        self._random_thread = threading.Thread(target=self._random_positioning_loop, daemon=True)
        self._random_thread.start()
        
        logger.info(f"Started random positioning: max_v={max_velocity:.3f} rad/s, P_change={velocity_change_prob}")
    
    def stop_random_positioning(self) -> None:
        """Stop random positioning mode."""
        self._random_enabled = False
        if self._random_thread:
            self._random_thread.join(timeout=1.0)
        self.mode = ControlMode.VELOCITY
        logger.info("Stopped random positioning")
    
    def _random_positioning_loop(self) -> None:
        """Random positioning control loop."""
        dt = 0.01  # 10ms loop
        max_omega = 1.047  # rad/s
        max_alpha = 10.0  # rad/s²
        
        # Persistent accelerations
        alpha_outer = max_alpha * (2 * np.random.random() - 1)
        alpha_inner = max_alpha * (2 * np.random.random() - 1)
        
        omega_outer = 0.0
        omega_inner = 0.0
        
        while self._random_enabled and not self._emergency_stop_active:
            # Randomly change acceleration direction
            if np.random.random() < self._velocity_change_probability:
                alpha_outer = max_alpha * (2 * np.random.random() - 1)
            if np.random.random() < self._velocity_change_probability:
                alpha_inner = max_alpha * (2 * np.random.random() - 1)
            
            # Update velocities
            omega_outer += alpha_outer * dt
            omega_inner += alpha_inner * dt
            
            # Velocity limiting with direction reversal
            if omega_outer > max_omega:
                omega_outer = max_omega
                alpha_outer = -max_alpha
            elif omega_outer < -max_omega:
                omega_outer = -max_omega
                alpha_outer = max_alpha
            
            if omega_inner > max_omega:
                omega_inner = max_omega
                alpha_inner = -max_alpha
            elif omega_inner < -max_omega:
                omega_inner = -max_omega
                alpha_inner = max_alpha
            
            # Apply velocities
            self.set_velocities(omega_outer, omega_inner)
            
            time.sleep(dt)
    
    def emergency_stop(self) -> None:
        """
        Activate emergency stop.
        
        Immediately stops both motors and disables all control.
        """
        with self._lock:
            self._emergency_stop_active = True
            self._random_enabled = False
        
        self.outer_motor.stop(emergency=True)
        self.inner_motor.stop(emergency=True)
        
        # Notify hardware
        if self._serial_interface:
            self._serial_interface.emergency_stop()
        
        # Notify callbacks
        for callback in self._safety_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Safety callback error: {e}")
        
        logger.critical("EMERGENCY STOP ACTIVATED")
    
    def reset_emergency_stop(self) -> None:
        """Reset emergency stop state."""
        with self._lock:
            self._emergency_stop_active = False
        self.outer_motor.status.state = MotorState.IDLE
        self.inner_motor.status.state = MotorState.IDLE
        logger.info("Emergency stop reset")
    
    def is_emergency_stopped(self) -> bool:
        """Check if emergency stop is active."""
        return self._emergency_stop_active
    
    def add_safety_callback(self, callback: Callable[[], None]) -> None:
        """Register a callback for emergency stop events."""
        self._safety_callbacks.append(callback)
    
    def get_status(self) -> Dict[str, Any]:
        """Get complete controller status."""
        return {
            'mode': self.mode.value,
            'emergency_stop': self._emergency_stop_active,
            'random_enabled': self._random_enabled,
            'outer_motor': self.outer_motor.get_status(),
            'inner_motor': self.inner_motor.get_status(),
        }
    
    def get_state_for_physics(self) -> Tuple[float, float, float, float]:
        """
        Get state tuple for physics engine.
        
        Returns:
            (theta_outer, theta_inner, omega_outer, omega_inner)
        """
        return (
            self.outer_motor.get_position(),
            self.inner_motor.get_position(),
            self.outer_motor.get_velocity(),
            self.inner_motor.get_velocity(),
        )


# Unit conversion utilities
def rpm_to_rad_s(rpm: float) -> float:
    """Convert RPM to rad/s."""
    return rpm * 2 * math.pi / 60


def rad_s_to_rpm(rad_s: float) -> float:
    """Convert rad/s to RPM."""
    return rad_s * 60 / (2 * math.pi)


def deg_s_to_rad_s(deg_s: float) -> float:
    """Convert deg/s to rad/s."""
    return math.radians(deg_s)


def rad_s_to_deg_s(rad_s: float) -> float:
    """Convert rad/s to deg/s."""
    return math.degrees(rad_s)
