"""
Data Acquisition Manager - Real-time Data Collection, Buffering, and Processing

This module orchestrates data collection from multiple sensors,
provides real-time filtering, and manages data storage.

Features:
- Multi-device support (Arduino, RPi, etc.)
- Ring buffer for efficient data storage
- Real-time signal processing (filtering, decimation)
- Thread-safe data access
- Export to multiple formats (CSV, HDF5, VTK)

Copyright (c) 2026 Space Research Laboratory
"""

import threading
import queue
import time
import numpy as np
from numpy.typing import NDArray
from scipy import signal
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable, Tuple
from pathlib import Path
import json
import csv
from datetime import datetime
from loguru import logger

from rpm_digital_twin.core.sensor_interface import (
    SensorPacket,
    BaseSensorInterface,
    SerialSensorInterface,
    TCPSensorInterface,
    SimulatedSensorInterface,
    ConnectionStatus,
)


@dataclass
class DataChannel:
    """Configuration for a single data channel."""
    name: str
    unit: str
    min_value: float = -np.inf
    max_value: float = np.inf
    calibration_offset: float = 0.0
    calibration_scale: float = 1.0
    filter_enabled: bool = True
    
    def apply_calibration(self, value: float) -> float:
        """Apply calibration to raw value."""
        return (value + self.calibration_offset) * self.calibration_scale


@dataclass
class DataBuffer:
    """
    Circular buffer for time-series data storage.
    
    Optimized for real-time data acquisition with fixed memory footprint.
    """
    max_samples: int = 100000
    num_channels: int = 16
    
    # Data arrays (pre-allocated)
    timestamps: NDArray[np.float64] = field(init=False)
    data: NDArray[np.float64] = field(init=False)
    
    # Buffer state
    write_index: int = field(default=0, init=False)
    sample_count: int = field(default=0, init=False)
    is_full: bool = field(default=False, init=False)
    
    # Thread safety
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    
    def __post_init__(self):
        self.timestamps = np.zeros(self.max_samples, dtype=np.float64)
        self.data = np.zeros((self.max_samples, self.num_channels), dtype=np.float64)
    
    def append(self, timestamp: float, values: NDArray[np.float64]) -> None:
        """Append a new sample to the buffer."""
        with self._lock:
            self.timestamps[self.write_index] = timestamp
            self.data[self.write_index, :len(values)] = values
            
            self.write_index = (self.write_index + 1) % self.max_samples
            self.sample_count += 1
            
            if self.sample_count >= self.max_samples:
                self.is_full = True
    
    def get_latest(self, n_samples: int = 1000) -> Tuple[NDArray[np.float64], NDArray[np.float64]]:
        """Get the most recent n samples."""
        with self._lock:
            if self.sample_count == 0:
                return np.array([]), np.array([])
            
            n = min(n_samples, self.sample_count, self.max_samples)
            
            if not self.is_full:
                return (
                    self.timestamps[:self.write_index][-n:].copy(),
                    self.data[:self.write_index][-n:].copy()
                )
            else:
                # Handle wrap-around
                indices = np.arange(self.write_index - n, self.write_index) % self.max_samples
                return (
                    self.timestamps[indices].copy(),
                    self.data[indices].copy()
                )
    
    def get_time_range(
        self, 
        start_time: float, 
        end_time: float
    ) -> Tuple[NDArray[np.float64], NDArray[np.float64]]:
        """Get samples within a time range."""
        with self._lock:
            if self.sample_count == 0:
                return np.array([]), np.array([])
            
            # Get all valid data
            if not self.is_full:
                ts = self.timestamps[:self.write_index]
                data = self.data[:self.write_index]
            else:
                # Reconstruct in order
                indices = np.arange(self.write_index, self.write_index + self.max_samples) % self.max_samples
                ts = self.timestamps[indices]
                data = self.data[indices]
            
            # Filter by time
            mask = (ts >= start_time) & (ts <= end_time)
            return ts[mask].copy(), data[mask].copy()
    
    def clear(self) -> None:
        """Clear all data from the buffer."""
        with self._lock:
            self.timestamps.fill(0)
            self.data.fill(0)
            self.write_index = 0
            self.sample_count = 0
            self.is_full = False


class SignalProcessor:
    """
    Real-time signal processing for sensor data.
    
    Implements:
    - Low-pass Butterworth filtering
    - Moving average smoothing
    - Decimation
    - Spike detection and removal
    """
    
    def __init__(
        self,
        sample_rate: float = 100.0,
        cutoff_frequency: float = 10.0,
        filter_order: int = 4,
        enable_filtering: bool = True,
    ):
        self.sample_rate = sample_rate
        self.cutoff_frequency = cutoff_frequency
        self.filter_order = filter_order
        self.enable_filtering = enable_filtering
        
        # Design Butterworth filter
        self._b, self._a = signal.butter(
            filter_order,
            cutoff_frequency / (sample_rate / 2),
            btype='low'
        )
        
        # Filter state for real-time filtering (per channel)
        self._zi: Dict[str, NDArray[np.float64]] = {}
        
        logger.info(
            f"SignalProcessor initialized: {sample_rate}Hz, "
            f"cutoff={cutoff_frequency}Hz, order={filter_order}"
        )
    
    def filter_sample(self, channel: str, value: float) -> float:
        """Apply real-time filtering to a single sample."""
        if not self.enable_filtering:
            return value
        
        # Initialize filter state for new channels
        if channel not in self._zi:
            self._zi[channel] = signal.lfilter_zi(self._b, self._a) * value
        
        # Apply filter
        filtered, self._zi[channel] = signal.lfilter(
            self._b, self._a, [value], zi=self._zi[channel]
        )
        
        return filtered[0]
    
    def filter_array(self, data: NDArray[np.float64]) -> NDArray[np.float64]:
        """Apply filtering to an array of samples."""
        if not self.enable_filtering:
            return data
        
        return signal.filtfilt(self._b, self._a, data, axis=0)
    
    def compute_rms(self, data: NDArray[np.float64], window_size: int = 100) -> NDArray[np.float64]:
        """Compute running RMS over a sliding window."""
        if len(data) < window_size:
            return np.sqrt(np.mean(data**2)) * np.ones(len(data))
        
        # Use convolution for efficient sliding window
        kernel = np.ones(window_size) / window_size
        squared = data ** 2
        mean_squared = np.convolve(squared, kernel, mode='same')
        return np.sqrt(mean_squared)
    
    def detect_spikes(
        self, 
        data: NDArray[np.float64], 
        threshold_sigma: float = 3.0
    ) -> NDArray[np.bool_]:
        """Detect spike outliers using sigma threshold."""
        mean = np.mean(data)
        std = np.std(data)
        return np.abs(data - mean) > threshold_sigma * std
    
    def reset(self) -> None:
        """Reset all filter states."""
        self._zi.clear()


class DataAcquisitionManager:
    """
    Central manager for all data acquisition operations.
    
    Coordinates:
    - Multiple sensor interfaces
    - Data buffering and storage
    - Real-time signal processing
    - Data export and logging
    - Synchronization with physics engine
    """
    
    # Channel indices in data buffer
    CHANNEL_MAP = {
        'accel_x': 0,
        'accel_y': 1,
        'accel_z': 2,
        'gyro_x': 3,
        'gyro_y': 4,
        'gyro_z': 5,
        'encoder_outer': 6,
        'encoder_inner': 7,
        'omega_outer': 8,
        'omega_inner': 9,
        'temperature': 10,
        'accel_mag': 11,
        'gyro_mag': 12,
        'gravity_x': 13,
        'gravity_y': 14,
        'gravity_z': 15,
    }
    
    def __init__(
        self,
        buffer_size: int = 100000,
        sample_rate: float = 100.0,
        enable_filtering: bool = True,
        data_directory: str = "./data",
    ):
        self.buffer_size = buffer_size
        self.sample_rate = sample_rate
        self.data_directory = Path(data_directory)
        self.data_directory.mkdir(parents=True, exist_ok=True)
        
        # Data buffer
        self.buffer = DataBuffer(
            max_samples=buffer_size,
            num_channels=len(self.CHANNEL_MAP)
        )
        
        # Signal processor
        self.processor = SignalProcessor(
            sample_rate=sample_rate,
            enable_filtering=enable_filtering
        )
        
        # Sensor interfaces
        self._interfaces: Dict[str, BaseSensorInterface] = {}
        
        # Packet history for live display (recent packets)
        self._recent_packets: deque = deque(maxlen=100)
        
        # Callbacks for new data
        self._data_callbacks: List[Callable[[SensorPacket], None]] = []
        
        # Recording state
        self._recording = False
        self._recording_file: Optional[Any] = None
        self._recording_start_time = 0.0
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Statistics
        self._stats = {
            'total_packets': 0,
            'dropped_packets': 0,
            'start_time': time.time(),
        }
        
        logger.info(f"DataAcquisitionManager initialized: buffer={buffer_size}, rate={sample_rate}Hz")
    
    def add_interface(self, name: str, interface: BaseSensorInterface) -> None:
        """Add a sensor interface to the manager."""
        with self._lock:
            self._interfaces[name] = interface
            interface.add_callback(self._on_packet_received)
            logger.info(f"Added sensor interface: {name}")
    
    def remove_interface(self, name: str) -> None:
        """Remove a sensor interface."""
        with self._lock:
            if name in self._interfaces:
                interface = self._interfaces.pop(name)
                interface.disconnect()
                logger.info(f"Removed sensor interface: {name}")
    
    def get_interface(self, name: str) -> Optional[BaseSensorInterface]:
        """Get a sensor interface by name."""
        return self._interfaces.get(name)
    
    def connect_all(self) -> Dict[str, bool]:
        """Connect all sensor interfaces."""
        results = {}
        for name, interface in self._interfaces.items():
            results[name] = interface.connect()
        return results
    
    def disconnect_all(self) -> None:
        """Disconnect all sensor interfaces."""
        for interface in self._interfaces.values():
            interface.disconnect()
    
    def start_acquisition(self) -> None:
        """Start data acquisition from all connected interfaces."""
        for name, interface in self._interfaces.items():
            if interface.status == ConnectionStatus.CONNECTED:
                interface.start_streaming()
                logger.info(f"Started acquisition from {name}")
    
    def stop_acquisition(self) -> None:
        """Stop data acquisition from all interfaces."""
        for interface in self._interfaces.values():
            interface.stop_streaming()
    
    def _on_packet_received(self, packet: SensorPacket) -> None:
        """Callback when a new packet is received from any interface."""
        with self._lock:
            self._stats['total_packets'] += 1
            
            # Store in recent packets
            self._recent_packets.append(packet)
            
            # Convert packet to array and store in buffer
            values = self._packet_to_array(packet)
            self.buffer.append(packet.timestamp, values)
            
            # Recording
            if self._recording and self._recording_file:
                self._write_to_recording(packet)
        
        # Notify callbacks (outside lock)
        for callback in self._data_callbacks:
            try:
                callback(packet)
            except Exception as e:
                logger.error(f"Data callback error: {e}")
    
    def _packet_to_array(self, packet: SensorPacket) -> NDArray[np.float64]:
        """Convert SensorPacket to numpy array for buffer storage."""
        accel_mag = packet.get_accel_magnitude()
        gyro_mag = packet.get_gyro_magnitude()
        
        return np.array([
            packet.accel_x,
            packet.accel_y,
            packet.accel_z,
            packet.gyro_x,
            packet.gyro_y,
            packet.gyro_z,
            packet.encoder_outer,
            packet.encoder_inner,
            packet.omega_outer,
            packet.omega_inner,
            packet.temperature,
            accel_mag,
            gyro_mag,
            0.0,  # gravity_x (computed later)
            0.0,  # gravity_y
            0.0,  # gravity_z
        ], dtype=np.float64)
    
    def add_data_callback(self, callback: Callable[[SensorPacket], None]) -> None:
        """Register a callback for new data."""
        with self._lock:
            self._data_callbacks.append(callback)
    
    def remove_data_callback(self, callback: Callable[[SensorPacket], None]) -> None:
        """Remove a data callback."""
        with self._lock:
            if callback in self._data_callbacks:
                self._data_callbacks.remove(callback)
    
    def get_recent_packets(self, n: int = 10) -> List[SensorPacket]:
        """Get the most recent n packets."""
        with self._lock:
            packets = list(self._recent_packets)
            return packets[-n:]
    
    def get_latest_data(
        self, 
        duration_seconds: float = 60.0
    ) -> Tuple[NDArray[np.float64], NDArray[np.float64]]:
        """Get data from the last N seconds."""
        n_samples = int(duration_seconds * self.sample_rate)
        return self.buffer.get_latest(n_samples)
    
    def get_channel_data(
        self, 
        channel: str, 
        duration_seconds: float = 60.0
    ) -> Tuple[NDArray[np.float64], NDArray[np.float64]]:
        """Get data for a specific channel."""
        if channel not in self.CHANNEL_MAP:
            raise ValueError(f"Unknown channel: {channel}")
        
        timestamps, data = self.get_latest_data(duration_seconds)
        channel_idx = self.CHANNEL_MAP[channel]
        
        return timestamps, data[:, channel_idx] if len(data) > 0 else np.array([])
    
    # Recording methods
    def start_recording(self, filename: Optional[str] = None) -> str:
        """Start recording data to file."""
        if self._recording:
            return ""
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"rpm_recording_{timestamp}.csv"
        
        filepath = self.data_directory / filename
        
        try:
            self._recording_file = open(filepath, 'w', newline='')
            self._csv_writer = csv.writer(self._recording_file)
            
            # Write header
            header = ['timestamp', 'sequence'] + list(self.CHANNEL_MAP.keys())[:11]
            self._csv_writer.writerow(header)
            
            self._recording = True
            self._recording_start_time = time.time()
            logger.info(f"Started recording to {filepath}")
            
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            return ""
    
    def stop_recording(self) -> str:
        """Stop recording and close file."""
        if not self._recording:
            return ""
        
        self._recording = False
        filepath = ""
        
        if self._recording_file:
            filepath = self._recording_file.name
            self._recording_file.close()
            self._recording_file = None
        
        duration = time.time() - self._recording_start_time
        logger.info(f"Stopped recording: {duration:.1f}s, file: {filepath}")
        
        return filepath
    
    def _write_to_recording(self, packet: SensorPacket) -> None:
        """Write a packet to the recording file."""
        if self._csv_writer:
            row = [
                packet.timestamp,
                packet.sequence_number,
                packet.accel_x,
                packet.accel_y,
                packet.accel_z,
                packet.gyro_x,
                packet.gyro_y,
                packet.gyro_z,
                packet.encoder_outer,
                packet.encoder_inner,
                packet.omega_outer,
                packet.omega_inner,
                packet.temperature,
            ]
            self._csv_writer.writerow(row)
    
    def export_to_hdf5(self, filename: str, duration_seconds: Optional[float] = None) -> str:
        """Export data to HDF5 format."""
        try:
            import h5py
        except ImportError:
            logger.error("h5py not installed. Run: pip install h5py")
            return ""
        
        filepath = self.data_directory / filename
        
        if duration_seconds:
            timestamps, data = self.get_latest_data(duration_seconds)
        else:
            timestamps, data = self.buffer.get_latest(self.buffer.max_samples)
        
        if len(timestamps) == 0:
            logger.warning("No data to export")
            return ""
        
        with h5py.File(filepath, 'w') as f:
            # Metadata
            f.attrs['created'] = datetime.now().isoformat()
            f.attrs['sample_rate'] = self.sample_rate
            f.attrs['channel_names'] = list(self.CHANNEL_MAP.keys())
            
            # Data
            f.create_dataset('timestamps', data=timestamps, compression='gzip')
            f.create_dataset('data', data=data, compression='gzip')
            
            # Individual channels for convenience
            for name, idx in self.CHANNEL_MAP.items():
                if idx < data.shape[1]:
                    f.create_dataset(f'channels/{name}', data=data[:, idx], compression='gzip')
        
        logger.info(f"Exported {len(timestamps)} samples to {filepath}")
        return str(filepath)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get acquisition statistics."""
        with self._lock:
            elapsed = time.time() - self._stats['start_time']
            total = self._stats['total_packets']
            
            interface_stats = {
                name: iface.get_statistics() 
                for name, iface in self._interfaces.items()
            }
            
            return {
                'total_packets': total,
                'dropped_packets': self._stats['dropped_packets'],
                'elapsed_time': elapsed,
                'average_rate': total / elapsed if elapsed > 0 else 0,
                'buffer_samples': self.buffer.sample_count,
                'buffer_utilization': self.buffer.sample_count / self.buffer.max_samples,
                'interfaces': interface_stats,
                'recording': self._recording,
            }
    
    def clear_buffer(self) -> None:
        """Clear all buffered data."""
        self.buffer.clear()
        self._recent_packets.clear()
        logger.info("Data buffer cleared")


# Convenience factory functions
def create_arduino_interface(port: str = "auto") -> SerialSensorInterface:
    """Create an Arduino sensor interface."""
    return SerialSensorInterface(port=port, device_id="arduino_main")


def create_rpi_interface(host: str, port: int = 5000) -> TCPSensorInterface:
    """Create a Raspberry Pi TCP interface."""
    return TCPSensorInterface(host=host, port=port, device_id="rpi_main")


def create_simulated_interface(sample_rate: float = 100.0) -> SimulatedSensorInterface:
    """Create a simulated sensor interface for testing."""
    return SimulatedSensorInterface(sample_rate=sample_rate, device_id="simulator")
