"""
RPM Digital Twin - Core Module
Physics Engine, Data Acquisition, Motor Control
"""

from rpm_digital_twin.core.physics_engine import RPMPhysicsEngine
from rpm_digital_twin.core.data_acquisition import DataAcquisitionManager
from rpm_digital_twin.core.motor_controller import MotorController
from rpm_digital_twin.core.sensor_interface import SensorInterface

__all__ = [
    "RPMPhysicsEngine",
    "DataAcquisitionManager",
    "MotorController",
    "SensorInterface",
]
