"""
Data Validator - Compares theoretical vs experimental data
Provides quality metrics and validation reports
"""

import numpy as np
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of validation comparison"""
    theoretical_gravity: np.ndarray
    experimental_gravity: np.ndarray
    error_magnitude: float
    relative_error: float
    quality_factor: float
    time_window: float


class DataValidator:
    """Validates experimental data against theoretical predictions"""

    def __init__(self, theoretical_simulator):
        """
        Initialize validator
        
        Args:
            theoretical_simulator: MicrogravitySimulator instance
        """
        self.simulator = theoretical_simulator

    def compare_gravity_vectors(
        self,
        theoretical: np.ndarray,
        experimental: np.ndarray,
    ) -> Tuple[float, float]:
        """
        Compare theoretical and experimental gravity vectors
        
        Returns:
            (error_magnitude, relative_error)
        """
        error_vector = experimental - theoretical
        error_magnitude = np.linalg.norm(error_vector)
        relative_error = error_magnitude / (np.linalg.norm(theoretical) + 1e-6)
        
        return error_magnitude, relative_error

    def validate_experiment(
        self,
        x: float,
        y: float,
        z: float,
        experimental_data: List[np.ndarray],
        duration: float,
    ) -> ValidationResult:
        """
        Validate experimental data against theoretical prediction
        
        Args:
            x, y, z: Sample location
            experimental_data: List of measured acceleration vectors
            duration: Time window of measurement
            
        Returns:
            ValidationResult with detailed comparison
        """
        # Calculate theoretical prediction
        theoretical_g, theoretical_residual = self.simulator.calculate_time_averaged_gravity(
            x, y, z, duration
        )
        
        # Calculate experimental mean
        experimental_g = np.mean(experimental_data, axis=0)
        experimental_residual = np.linalg.norm(experimental_g)
        
        # Compute error
        error_mag, rel_error = self.compare_gravity_vectors(theoretical_g, experimental_g)
        
        # Quality factor
        quality = rel_error
        
        return ValidationResult(
            theoretical_gravity=theoretical_g,
            experimental_gravity=experimental_g,
            error_magnitude=error_mag,
            relative_error=rel_error,
            quality_factor=quality,
            time_window=duration,
        )

    def generate_validation_report(
        self, result: ValidationResult
    ) -> Dict:
        """
        Generate comprehensive validation report
        
        Returns:
            Dictionary with report metrics
        """
        return {
            "summary": {
                "status": "PASS" if result.quality_factor < 0.1 else "NEEDS_REVIEW",
                "quality_factor": float(result.quality_factor),
                "time_window_s": result.time_window,
            },
            "theoretical": {
                "gravity_vector_ms2": result.theoretical_gravity.tolist(),
                "magnitude_ms2": float(np.linalg.norm(result.theoretical_gravity)),
            },
            "experimental": {
                "gravity_vector_ms2": result.experimental_gravity.tolist(),
                "magnitude_ms2": float(np.linalg.norm(result.experimental_gravity)),
            },
            "error": {
                "absolute_magnitude_ms2": float(result.error_magnitude),
                "relative_error_percent": float(result.relative_error * 100),
            },
        }


if __name__ == "__main__":
    print("Data Validator Module - Ready for integration")
