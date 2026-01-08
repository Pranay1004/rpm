"""
Unit tests for RPM Digital Twin core modules.

Tests physics engine, data acquisition, and microgravity calculations.
"""

import unittest
import numpy as np
from pathlib import Path
import tempfile
import time

from rpm_digital_twin.core.microgravity import (
    rotation_z, rotation_y,
    gravity_in_payload_frame,
    centripetal_acceleration_at_point,
    taSMG_metric,
)
from rpm_digital_twin.core.data_acquisition import (
    DataBuffer, SignalProcessor, DataChannel,
)
from rpm_digital_twin.core.sensor_interface import SensorPacket


class TestMicrogravity(unittest.TestCase):
    """Test microgravity calculations."""
    
    def test_rotation_matrices_identity(self):
        """Test that zero rotations give identity."""
        R = rotation_z(0) @ rotation_y(0)
        np.testing.assert_array_almost_equal(R, np.eye(3))
    
    def test_gravity_at_zero_rotation(self):
        """At zero rotation, gravity should be [0, -g, 0]."""
        g = gravity_in_payload_frame(0, 0)
        np.testing.assert_array_almost_equal(g, [0, -9.81, 0], decimal=2)
    
    def test_gravity_magnitude(self):
        """Gravity magnitude should always be g."""
        for theta_o in np.linspace(0, 2*np.pi, 10):
            for theta_i in np.linspace(0, 2*np.pi, 10):
                g = gravity_in_payload_frame(theta_o, theta_i)
                mag = np.linalg.norm(g)
                self.assertAlmostEqual(mag, 9.81, places=5)
    
    def test_centripetal_at_center(self):
        """Centripetal at center should be near zero."""
        a = centripetal_acceleration_at_point(1.0, 1.0, 0, 0, np.array([0, 0, 0]))
        np.testing.assert_array_almost_equal(a, [0, 0, 0], decimal=5)
    
    def test_taSMG_metric(self):
        """taSMG should be between 0 and 1 for gravity-only."""
        g_const = np.tile([0, -9.81, 0], (100, 1))
        metric = taSMG_metric(g_const)
        self.assertAlmostEqual(metric, 1.0, places=5)


class TestDataBuffer(unittest.TestCase):
    """Test data buffering."""
    
    def test_buffer_append_retrieve(self):
        """Test appending and retrieving data."""
        buf = DataBuffer(max_samples=100, num_channels=3)
        
        ts = 0.0
        for i in range(10):
            data = np.array([i, i+1, i+2], dtype=np.float64)
            buf.append(ts + i*0.1, data)
        
        ts_out, data_out = buf.get_latest(10)
        self.assertEqual(len(ts_out), 10)
        self.assertEqual(data_out.shape[0], 10)
        self.assertEqual(data_out.shape[1], 3)
    
    def test_buffer_wraparound(self):
        """Test circular buffer wraparound."""
        buf = DataBuffer(max_samples=10, num_channels=2)
        
        # Fill buffer
        for i in range(15):
            data = np.array([float(i), float(i+1)])
            buf.append(float(i), data)
        
        # Should still get max 10 samples
        ts_out, data_out = buf.get_latest(15)
        self.assertLessEqual(len(ts_out), 10)
        self.assertTrue(buf.is_full)
    
    def test_buffer_time_range(self):
        """Test retrieving data by time range."""
        buf = DataBuffer(max_samples=100, num_channels=1)
        
        for i in range(20):
            data = np.array([float(i)])
            buf.append(float(i), data)
        
        ts_out, data_out = buf.get_time_range(5.0, 15.0)
        self.assertGreater(len(ts_out), 0)
        self.assertTrue(np.all(ts_out >= 5.0))
        self.assertTrue(np.all(ts_out <= 15.0))


class TestSignalProcessor(unittest.TestCase):
    """Test signal processing utilities."""
    
    def test_processor_creation(self):
        """Test processor initialization."""
        proc = SignalProcessor(sample_rate=100, cutoff_frequency=10)
        self.assertEqual(proc.sample_rate, 100)
        self.assertEqual(proc.cutoff_frequency, 10)
    
    def test_single_sample_filter(self):
        """Test filtering a single sample."""
        proc = SignalProcessor(sample_rate=100, cutoff_frequency=10)
        result = proc.filter_sample('ch1', 1.0)
        self.assertIsInstance(result, float)
    
    def test_array_filter(self):
        """Test filtering an array."""
        proc = SignalProcessor(sample_rate=100, cutoff_frequency=10)
        data = np.sin(np.linspace(0, 2*np.pi, 1000))
        filtered = proc.filter_array(data)
        self.assertEqual(len(filtered), len(data))
    
    def test_rms_computation(self):
        """Test RMS computation."""
        proc = SignalProcessor()
        data = np.ones(100) * 5.0
        rms = proc.compute_rms(data, window_size=10)
        # Middle samples show steady-state behavior (transient at edges from windowing)
        np.testing.assert_array_almost_equal(rms[25:75], 5.0, decimal=5)
    
    def test_spike_detection(self):
        """Test spike detection."""
        proc = SignalProcessor()
        data = np.zeros(100)
        data[50] = 10.0  # Add spike
        spikes = proc.detect_spikes(data, threshold_sigma=2.0)
        self.assertTrue(spikes[50])


class TestSensorPacket(unittest.TestCase):
    """Test sensor packet functionality."""
    
    def test_packet_creation(self):
        """Test creating a sensor packet."""
        p = SensorPacket(
            timestamp=1.0,
            sequence_number=1,
            accel_x=0.1, accel_y=0.2, accel_z=0.3,
            gyro_x=0.01, gyro_y=0.02, gyro_z=0.03,
            encoder_outer=100, encoder_inner=200,
            omega_outer=1.0, omega_inner=2.0,
            temperature=25.0,
        )
        self.assertEqual(p.timestamp, 1.0)
        self.assertEqual(p.accel_x, 0.1)
    
    def test_magnitude_computation(self):
        """Test acceleration magnitude."""
        p = SensorPacket(
            timestamp=0, sequence_number=0,
            accel_x=3, accel_y=4, accel_z=0,
            gyro_x=0, gyro_y=0, gyro_z=0,
        )
        mag = p.get_accel_magnitude()
        self.assertAlmostEqual(mag, 5.0)


if __name__ == '__main__':
    unittest.main()
