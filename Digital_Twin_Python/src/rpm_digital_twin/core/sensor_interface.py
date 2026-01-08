"""
Sensor Interface Module - Arduino, Raspberry Pi, and Generic Serial Communication

This module handles real-time communication with:
- Arduino Uno (via USB Serial)
- Raspberry Pi Pico (via USB Serial or TCP)
- IMU sensors (MPU6050, BNO055, etc.)
- Motor encoders and position feedback

Supports cross-platform operation (macOS M4 / Windows 11).

Copyright (c) 2026 Space Research Laboratory
"""

import serial
import serial.tools.list_ports
import socket
import threading
import queue
import time
import struct
import json
from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, List, Any, Tuple
from enum import Enum
from abc import ABC, abstractmethod
import numpy as np
from loguru import logger


class ConnectionStatus(Enum):
    """Connection status states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    RECONNECTING = "reconnecting"


class DeviceType(Enum):
    """Supported device types."""
    ARDUINO_UNO = "arduino_uno"
    ARDUINO_MEGA = "arduino_mega"
    RASPBERRY_PI_PICO = "rpi_pico"
    RASPBERRY_PI = "rpi"
    ESP32 = "esp32"
    GENERIC_SERIAL = "generic_serial"
    TCP_CLIENT = "tcp_client"
    UDP_CLIENT = "udp_client"


@dataclass
class SensorPacket:
    """
    Standardized sensor data packet.
    
    All incoming sensor data is parsed into this format for
    consistent processing throughout the application.
    """
    timestamp: float  # Unix timestamp (seconds)
    sequence_number: int = 0
    
    # Accelerometer data (m/s²)
    accel_x: float = 0.0
    accel_y: float = 0.0
    accel_z: float = 0.0
    
    # Gyroscope data (rad/s)
    gyro_x: float = 0.0
    gyro_y: float = 0.0
    gyro_z: float = 0.0
    
    # Magnetometer data (µT)
    mag_x: float = 0.0
    mag_y: float = 0.0
    mag_z: float = 0.0
    
    # Motor encoder positions (radians)
    encoder_outer: float = 0.0
    encoder_inner: float = 0.0
    
    # Motor angular velocities (rad/s)
    omega_outer: float = 0.0
    omega_inner: float = 0.0
    
    # Temperature (°C)
    temperature: float = 25.0
    
    # Device-specific raw data
    raw_data: bytes = field(default_factory=bytes)
    device_id: str = ""
    
    # Validity flags
    is_valid: bool = True
    error_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert packet to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp,
            "sequence": self.sequence_number,
            "accel": [self.accel_x, self.accel_y, self.accel_z],
            "gyro": [self.gyro_x, self.gyro_y, self.gyro_z],
            "mag": [self.mag_x, self.mag_y, self.mag_z],
            "encoder": [self.encoder_outer, self.encoder_inner],
            "omega": [self.omega_outer, self.omega_inner],
            "temperature": self.temperature,
            "device_id": self.device_id,
            "is_valid": self.is_valid,
        }
    
    def get_accel_magnitude(self) -> float:
        """Get acceleration magnitude in m/s²."""
        return np.sqrt(self.accel_x**2 + self.accel_y**2 + self.accel_z**2)
    
    def get_gyro_magnitude(self) -> float:
        """Get angular velocity magnitude in rad/s."""
        return np.sqrt(self.gyro_x**2 + self.gyro_y**2 + self.gyro_z**2)


class BaseSensorInterface(ABC):
    """Abstract base class for sensor interfaces."""
    
    def __init__(self, device_id: str = ""):
        self.device_id = device_id
        self.status = ConnectionStatus.DISCONNECTED
        self._callbacks: List[Callable[[SensorPacket], None]] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._packet_queue: queue.Queue = queue.Queue(maxsize=1000)
        self._packet_count = 0
        self._error_count = 0
        self._last_packet_time = 0.0
    
    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the device."""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to the device."""
        pass
    
    @abstractmethod
    def read_packet(self) -> Optional[SensorPacket]:
        """Read a single data packet from the device."""
        pass
    
    @abstractmethod
    def send_command(self, command: str) -> bool:
        """Send a command to the device."""
        pass
    
    def add_callback(self, callback: Callable[[SensorPacket], None]) -> None:
        """Register a callback for incoming packets."""
        with self._lock:
            self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[SensorPacket], None]) -> None:
        """Remove a registered callback."""
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)
    
    def start_streaming(self) -> None:
        """Start continuous data streaming in background thread."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._stream_loop, daemon=True)
        self._thread.start()
        logger.info(f"Started streaming from {self.device_id}")
    
    def stop_streaming(self) -> None:
        """Stop continuous data streaming."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info(f"Stopped streaming from {self.device_id}")
    
    def _stream_loop(self) -> None:
        """Background thread for continuous data reading."""
        while self._running:
            try:
                packet = self.read_packet()
                if packet is not None:
                    self._packet_count += 1
                    self._last_packet_time = time.time()
                    
                    # Add to queue (non-blocking)
                    try:
                        self._packet_queue.put_nowait(packet)
                    except queue.Full:
                        self._packet_queue.get_nowait()  # Remove oldest
                        self._packet_queue.put_nowait(packet)
                    
                    # Notify callbacks
                    with self._lock:
                        for callback in self._callbacks:
                            try:
                                callback(packet)
                            except Exception as e:
                                logger.error(f"Callback error: {e}")
            except Exception as e:
                self._error_count += 1
                logger.error(f"Stream error on {self.device_id}: {e}")
                time.sleep(0.1)
    
    def get_packet(self, timeout: float = 0.1) -> Optional[SensorPacket]:
        """Get a packet from the queue."""
        try:
            return self._packet_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get connection and streaming statistics."""
        return {
            "device_id": self.device_id,
            "status": self.status.value,
            "packet_count": self._packet_count,
            "error_count": self._error_count,
            "queue_size": self._packet_queue.qsize(),
            "last_packet_time": self._last_packet_time,
            "data_rate": self._calculate_data_rate(),
        }
    
    def _calculate_data_rate(self) -> float:
        """Calculate current data rate in Hz."""
        # Simplified - would need proper timing in production
        return 0.0


class SerialSensorInterface(BaseSensorInterface):
    """
    Serial port sensor interface for Arduino and similar devices.
    
    Protocol format (binary, little-endian):
    - Header: 2 bytes (0xAA, 0x55)
    - Sequence: 4 bytes (uint32)
    - Accel X/Y/Z: 3 x 4 bytes (float32)
    - Gyro X/Y/Z: 3 x 4 bytes (float32)
    - Encoder Outer/Inner: 2 x 4 bytes (float32)
    - Omega Outer/Inner: 2 x 4 bytes (float32)
    - Temperature: 4 bytes (float32)
    - Checksum: 1 byte (XOR of all data bytes)
    - Footer: 2 bytes (0x55, 0xAA)
    
    Total: 55 bytes per packet
    
    Also supports JSON-based ASCII protocol for debugging.
    """
    
    PACKET_HEADER = bytes([0xAA, 0x55])
    PACKET_FOOTER = bytes([0x55, 0xAA])
    BINARY_PACKET_SIZE = 55
    
    def __init__(
        self,
        port: Optional[str] = None,
        baud_rate: int = 115200,
        timeout: float = 1.0,
        device_type: DeviceType = DeviceType.ARDUINO_UNO,
        device_id: str = "",
        use_binary_protocol: bool = True,
    ):
        super().__init__(device_id or f"serial_{port}")
        
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.device_type = device_type
        self.use_binary_protocol = use_binary_protocol
        
        self._serial: Optional[serial.Serial] = None
        self._buffer = bytearray()
    
    @staticmethod
    def list_ports() -> List[Dict[str, str]]:
        """List available serial ports."""
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append({
                "device": port.device,
                "description": port.description,
                "hwid": port.hwid,
                "manufacturer": port.manufacturer or "",
            })
        return ports
    
    @staticmethod
    def auto_detect_arduino() -> Optional[str]:
        """Auto-detect Arduino port based on common identifiers."""
        arduino_identifiers = [
            "Arduino",
            "CH340",
            "FTDI",
            "USB Serial",
            "ACM",  # Linux
            "usbmodem",  # macOS
        ]
        
        for port in serial.tools.list_ports.comports():
            for identifier in arduino_identifiers:
                if identifier.lower() in port.description.lower():
                    logger.info(f"Auto-detected Arduino on {port.device}")
                    return port.device
        
        return None
    
    def connect(self) -> bool:
        """Connect to the serial device."""
        try:
            self.status = ConnectionStatus.CONNECTING
            
            # Auto-detect if port not specified
            if self.port is None or self.port == "auto":
                self.port = self.auto_detect_arduino()
                if self.port is None:
                    self.status = ConnectionStatus.ERROR
                    logger.error("No Arduino device found")
                    return False
            
            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                timeout=self.timeout,
                write_timeout=self.timeout,
            )
            
            # Wait for device initialization
            time.sleep(2.0)
            
            # Clear any buffered data
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()
            
            self.status = ConnectionStatus.CONNECTED
            logger.info(f"Connected to {self.device_type.value} on {self.port} @ {self.baud_rate} baud")
            return True
            
        except serial.SerialException as e:
            self.status = ConnectionStatus.ERROR
            logger.error(f"Serial connection failed: {e}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from the serial device."""
        self.stop_streaming()
        
        if self._serial and self._serial.is_open:
            self._serial.close()
        
        self._serial = None
        self.status = ConnectionStatus.DISCONNECTED
        logger.info(f"Disconnected from {self.port}")
    
    def read_packet(self) -> Optional[SensorPacket]:
        """Read and parse a data packet."""
        if not self._serial or not self._serial.is_open:
            return None
        
        try:
            if self.use_binary_protocol:
                return self._read_binary_packet()
            else:
                return self._read_json_packet()
        except Exception as e:
            logger.debug(f"Packet read error: {e}")
            return None
    
    def _read_binary_packet(self) -> Optional[SensorPacket]:
        """Read and parse binary protocol packet."""
        # Read available data
        if self._serial.in_waiting > 0:
            data = self._serial.read(self._serial.in_waiting)
            self._buffer.extend(data)
        
        # Search for packet header
        while len(self._buffer) >= self.BINARY_PACKET_SIZE:
            header_pos = self._buffer.find(self.PACKET_HEADER)
            
            if header_pos == -1:
                # No header found, clear buffer
                self._buffer.clear()
                return None
            
            if header_pos > 0:
                # Remove data before header
                self._buffer = self._buffer[header_pos:]
            
            if len(self._buffer) < self.BINARY_PACKET_SIZE:
                return None
            
            # Extract packet
            packet_data = bytes(self._buffer[:self.BINARY_PACKET_SIZE])
            
            # Verify footer
            if packet_data[-2:] != self.PACKET_FOOTER:
                self._buffer = self._buffer[2:]  # Skip header and try again
                continue
            
            # Verify checksum
            calculated_checksum = 0
            for byte in packet_data[2:-3]:  # Exclude header, checksum, footer
                calculated_checksum ^= byte
            
            if calculated_checksum != packet_data[-3]:
                self._buffer = self._buffer[2:]
                continue
            
            # Parse packet
            self._buffer = self._buffer[self.BINARY_PACKET_SIZE:]
            return self._parse_binary_packet(packet_data)
        
        return None
    
    def _parse_binary_packet(self, data: bytes) -> SensorPacket:
        """Parse binary packet data into SensorPacket."""
        # Unpack binary data (little-endian)
        # Skip header (2 bytes)
        offset = 2
        
        sequence = struct.unpack_from('<I', data, offset)[0]
        offset += 4
        
        accel = struct.unpack_from('<3f', data, offset)
        offset += 12
        
        gyro = struct.unpack_from('<3f', data, offset)
        offset += 12
        
        encoder = struct.unpack_from('<2f', data, offset)
        offset += 8
        
        omega = struct.unpack_from('<2f', data, offset)
        offset += 8
        
        temperature = struct.unpack_from('<f', data, offset)[0]
        
        return SensorPacket(
            timestamp=time.time(),
            sequence_number=sequence,
            accel_x=accel[0],
            accel_y=accel[1],
            accel_z=accel[2],
            gyro_x=gyro[0],
            gyro_y=gyro[1],
            gyro_z=gyro[2],
            encoder_outer=encoder[0],
            encoder_inner=encoder[1],
            omega_outer=omega[0],
            omega_inner=omega[1],
            temperature=temperature,
            raw_data=data,
            device_id=self.device_id,
            is_valid=True,
        )
    
    def _read_json_packet(self) -> Optional[SensorPacket]:
        """Read and parse JSON/ASCII protocol packet."""
        try:
            line = self._serial.readline().decode('utf-8').strip()
            if not line:
                return None
            
            data = json.loads(line)
            
            return SensorPacket(
                timestamp=time.time(),
                sequence_number=data.get('seq', 0),
                accel_x=data.get('ax', 0.0),
                accel_y=data.get('ay', 0.0),
                accel_z=data.get('az', 0.0),
                gyro_x=data.get('gx', 0.0),
                gyro_y=data.get('gy', 0.0),
                gyro_z=data.get('gz', 0.0),
                encoder_outer=data.get('eo', 0.0),
                encoder_inner=data.get('ei', 0.0),
                omega_outer=data.get('wo', 0.0),
                omega_inner=data.get('wi', 0.0),
                temperature=data.get('temp', 25.0),
                device_id=self.device_id,
                is_valid=True,
            )
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None
    
    def send_command(self, command: str) -> bool:
        """Send a command to the device."""
        if not self._serial or not self._serial.is_open:
            return False
        
        try:
            cmd_bytes = (command + '\n').encode('utf-8')
            self._serial.write(cmd_bytes)
            self._serial.flush()
            logger.debug(f"Sent command: {command}")
            return True
        except serial.SerialException as e:
            logger.error(f"Failed to send command: {e}")
            return False
    
    def set_motor_velocity(self, omega_outer: float, omega_inner: float) -> bool:
        """Send motor velocity command."""
        command = f"SET_VEL {omega_outer:.4f} {omega_inner:.4f}"
        return self.send_command(command)
    
    def emergency_stop(self) -> bool:
        """Send emergency stop command."""
        return self.send_command("ESTOP")


class TCPSensorInterface(BaseSensorInterface):
    """
    TCP socket interface for Raspberry Pi and networked sensors.
    
    Supports both binary and JSON protocols over TCP/IP.
    """
    
    def __init__(
        self,
        host: str = "192.168.1.100",
        port: int = 5000,
        timeout: float = 5.0,
        device_id: str = "",
    ):
        super().__init__(device_id or f"tcp_{host}:{port}")
        
        self.host = host
        self.port = port
        self.timeout = timeout
        
        self._socket: Optional[socket.socket] = None
        self._buffer = bytearray()
    
    def connect(self) -> bool:
        """Connect to the TCP server."""
        try:
            self.status = ConnectionStatus.CONNECTING
            
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(self.timeout)
            self._socket.connect((self.host, self.port))
            
            self.status = ConnectionStatus.CONNECTED
            logger.info(f"Connected to TCP server at {self.host}:{self.port}")
            return True
            
        except socket.error as e:
            self.status = ConnectionStatus.ERROR
            logger.error(f"TCP connection failed: {e}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from the TCP server."""
        self.stop_streaming()
        
        if self._socket:
            try:
                self._socket.close()
            except:
                pass
        
        self._socket = None
        self.status = ConnectionStatus.DISCONNECTED
        logger.info(f"Disconnected from {self.host}:{self.port}")
    
    def read_packet(self) -> Optional[SensorPacket]:
        """Read and parse a data packet from TCP."""
        if not self._socket:
            return None
        
        try:
            # Read newline-delimited JSON
            data = b""
            while True:
                chunk = self._socket.recv(1)
                if not chunk:
                    return None
                if chunk == b'\n':
                    break
                data += chunk
            
            packet_data = json.loads(data.decode('utf-8'))
            
            return SensorPacket(
                timestamp=time.time(),
                sequence_number=packet_data.get('seq', 0),
                accel_x=packet_data.get('ax', 0.0),
                accel_y=packet_data.get('ay', 0.0),
                accel_z=packet_data.get('az', 0.0),
                gyro_x=packet_data.get('gx', 0.0),
                gyro_y=packet_data.get('gy', 0.0),
                gyro_z=packet_data.get('gz', 0.0),
                encoder_outer=packet_data.get('eo', 0.0),
                encoder_inner=packet_data.get('ei', 0.0),
                omega_outer=packet_data.get('wo', 0.0),
                omega_inner=packet_data.get('wi', 0.0),
                temperature=packet_data.get('temp', 25.0),
                device_id=self.device_id,
                is_valid=True,
            )
            
        except (socket.timeout, socket.error, json.JSONDecodeError) as e:
            logger.debug(f"TCP read error: {e}")
            return None
    
    def send_command(self, command: str) -> bool:
        """Send a command to the TCP server."""
        if not self._socket:
            return False
        
        try:
            cmd_bytes = (command + '\n').encode('utf-8')
            self._socket.sendall(cmd_bytes)
            return True
        except socket.error as e:
            logger.error(f"Failed to send TCP command: {e}")
            return False


class SimulatedSensorInterface(BaseSensorInterface):
    """
    Simulated sensor interface for testing without hardware.
    
    Generates realistic sensor data based on the physics engine state.
    """
    
    def __init__(
        self,
        sample_rate: float = 100.0,  # Hz
        noise_level: float = 0.01,  # Standard deviation of noise
        device_id: str = "simulated",
    ):
        super().__init__(device_id)
        
        self.sample_rate = sample_rate
        self.noise_level = noise_level
        self._period = 1.0 / sample_rate
        self._sequence = 0
        self._start_time = 0.0
        self._last_read_time = 0.0
        
        # Simulated state
        self._theta_outer = 0.0
        self._theta_inner = 0.0
        self._omega_outer = 0.0
        self._omega_inner = 0.0
    
    def connect(self) -> bool:
        """Initialize simulated connection."""
        self.status = ConnectionStatus.CONNECTED
        self._start_time = time.time()
        self._last_read_time = self._start_time
        logger.info("Simulated sensor interface connected")
        return True
    
    def disconnect(self) -> None:
        """Disconnect simulated interface."""
        self.stop_streaming()
        self.status = ConnectionStatus.DISCONNECTED
    
    def set_rpm_state(
        self,
        theta_outer: float,
        theta_inner: float,
        omega_outer: float,
        omega_inner: float
    ) -> None:
        """Update simulated RPM state from physics engine."""
        self._theta_outer = theta_outer
        self._theta_inner = theta_inner
        self._omega_outer = omega_outer
        self._omega_inner = omega_inner
    
    def read_packet(self) -> Optional[SensorPacket]:
        """Generate a simulated sensor packet."""
        current_time = time.time()
        
        # Rate limiting
        elapsed = current_time - self._last_read_time
        if elapsed < self._period:
            time.sleep(self._period - elapsed)
            current_time = time.time()
        
        self._last_read_time = current_time
        self._sequence += 1
        
        # Generate simulated accelerometer data
        # Based on gravity vector in payload frame
        phi = self._theta_outer
        psi = self._theta_inner
        
        g = 9.81
        ax = -g * np.sin(phi) * np.cos(psi) + np.random.normal(0, self.noise_level)
        ay = g * np.sin(phi) * np.sin(psi) + np.random.normal(0, self.noise_level)
        az = g * np.cos(phi) + np.random.normal(0, self.noise_level)
        
        # Simulated gyroscope data
        gx = self._omega_inner * np.sin(phi) + np.random.normal(0, self.noise_level * 0.1)
        gy = self._omega_inner * np.cos(phi) + np.random.normal(0, self.noise_level * 0.1)
        gz = self._omega_outer + np.random.normal(0, self.noise_level * 0.1)
        
        return SensorPacket(
            timestamp=current_time,
            sequence_number=self._sequence,
            accel_x=ax,
            accel_y=ay,
            accel_z=az,
            gyro_x=gx,
            gyro_y=gy,
            gyro_z=gz,
            encoder_outer=self._theta_outer,
            encoder_inner=self._theta_inner,
            omega_outer=self._omega_outer,
            omega_inner=self._omega_inner,
            temperature=25.0 + np.random.normal(0, 0.1),
            device_id=self.device_id,
            is_valid=True,
        )
    
    def send_command(self, command: str) -> bool:
        """Simulated command (always succeeds)."""
        logger.debug(f"Simulated command: {command}")
        return True


# Alias for backward compatibility
SensorInterface = SerialSensorInterface
