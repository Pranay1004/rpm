"""
RPM Digital Twin - Core Package
Random Positioning Machine Control & Analysis System

Copyright (c) 2026 Space Research Laboratory
For use by authorized space research organizations only.
"""

__version__ = "1.0.0"
__author__ = "RPM Digital Twin Team"
__license__ = "Proprietary - Space Research Applications"

from rpm_digital_twin.core.physics_engine import RPMPhysicsEngine
from rpm_digital_twin.core.data_acquisition import DataAcquisitionManager
from rpm_digital_twin.core.motor_controller import MotorController

__all__ = [
    "RPMPhysicsEngine",
    "DataAcquisitionManager", 
    "MotorController",
    "__version__",
]
