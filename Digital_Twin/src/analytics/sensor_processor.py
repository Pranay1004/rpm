"""
Sensor Data Processor - Real-time and batch data processing
Handles filtering, calibration, and preliminary analysis
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Optional
from scipy import signal


@dataclass
class SensorReading:
    """Raw sensor data reading"""
    timestamp: float
    accel_x: float
    accel_y: float
    accel_z: float
    gyro_x: float
    gyro_y: float
    gyro_z: float
    temperature: float


class SensorProcessor:
    """Processes raw sensor data for analysis and visualization"""

    def __init__(self, sampling_rate: float = 100.0):
        """
        Initialize processor
        
        Args:
            sampling_rate: Sampling frequency in Hz
        """
        self.sampling_rate = sampling_rate
        self.calibration_offset = np.array([0, 0, 0])

    def calibrate(self, neutral_readings: List[SensorReading]) -> None:
        """
        Calibrate sensor using neutral (stationary) readings
        
        Args:
            neutral_readings: List of readings with RPM at rest
        """
        # Calculate mean of neutral readings
        accels = np.array([
            [r.accel_x, r.accel_y, r.accel_z]
            for r in neutral_readings
        ])
        self.calibration_offset = np.mean(accels, axis=0)

    def apply_low_pass_filter(
        self, data: np.ndarray, cutoff_freq: float = 10.0
    ) -> np.ndarray:
        """
        Apply Butterworth low-pass filter
        
        Args:
            data: Input signal [N, 3] for 3-axis data
            cutoff_freq: Cutoff frequency in Hz
            
        Returns:
            Filtered data with same shape
        """
        nyquist = self.sampling_rate / 2
        normalized_cutoff = cutoff_freq / nyquist
        
        b, a = signal.butter(4, normalized_cutoff)
        
        if data.ndim == 1:
            return signal.filtfilt(b, a, data)
        else:
            # Apply filter to each axis
            filtered = np.zeros_like(data)
            for i in range(data.shape[1]):
                filtered[:, i] = signal.filtfilt(b, a, data[:, i])
            return filtered

    def detect_outliers(
        self, data: np.ndarray, threshold: float = 3.0
    ) -> np.ndarray:
        """
        Detect outliers using z-score method
        
        Args:
            data: Input data
            threshold: Z-score threshold (default 3.0 for 3-sigma)
            
        Returns:
            Boolean array marking outliers
        """
        z_scores = np.abs((data - np.mean(data)) / np.std(data))
        return z_scores > threshold

    def compute_statistics(
        self, readings: List[SensorReading]
    ) -> dict:
        """
        Compute statistical summary of sensor readings
        
        Returns:
            Dictionary with mean, std, min, max for each axis
        """
        accels = np.array([
            [r.accel_x, r.accel_y, r.accel_z]
            for r in readings
        ])
        
        gyros = np.array([
            [r.gyro_x, r.gyro_y, r.gyro_z]
            for r in readings
        ])
        
        temps = np.array([r.temperature for r in readings])
        
        return {
            "accel": {
                "mean": np.mean(accels, axis=0).tolist(),
                "std": np.std(accels, axis=0).tolist(),
                "min": np.min(accels, axis=0).tolist(),
                "max": np.max(accels, axis=0).tolist(),
            },
            "gyro": {
                "mean": np.mean(gyros, axis=0).tolist(),
                "std": np.std(gyros, axis=0).tolist(),
                "min": np.min(gyros, axis=0).tolist(),
                "max": np.max(gyros, axis=0).tolist(),
            },
            "temperature": {
                "mean": float(np.mean(temps)),
                "std": float(np.std(temps)),
                "min": float(np.min(temps)),
                "max": float(np.max(temps)),
            },
        }

    def compute_fft(self, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute FFT for frequency domain analysis
        
        Args:
            data: Time-domain signal
            
        Returns:
            (frequencies, magnitudes)
        """
        n = len(data)
        frequencies = np.fft.fftfreq(n, 1 / self.sampling_rate)
        magnitudes = np.abs(np.fft.fft(data))
        
        # Return only positive frequencies
        positive_idx = frequencies > 0
        return frequencies[positive_idx], magnitudes[positive_idx]


if __name__ == "__main__":
    # Example usage
    processor = SensorProcessor(sampling_rate=100.0)
    
    # Create sample data
    readings = [
        SensorReading(
            timestamp=i * 0.01,
            accel_x=0.1 * np.sin(2 * np.pi * i * 0.01),
            accel_y=0.1 * np.cos(2 * np.pi * i * 0.01),
            accel_z=-9.81,
            gyro_x=0.05,
            gyro_y=0.05,
            gyro_z=0.1,
            temperature=25.0,
        )
        for i in range(100)
    ]
    
    stats = processor.compute_statistics(readings)
    print("Sensor Statistics:", stats)
