"""
Sensor Panel - Live Sensor Data Display

GUI panel showing real-time data from Arduino, Raspberry Pi,
and other connected sensors with live packet display.

Copyright (c) 2026 Space Research Laboratory
"""

from typing import Optional, Dict, List, Any
import time
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGroupBox, QGridLayout, QPushButton, QComboBox,
    QTextEdit, QFrame, QScrollArea, QSpinBox,
    QProgressBar, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QFont, QColor

from rpm_digital_twin.core.sensor_interface import (
    SensorPacket,
    SerialSensorInterface,
    TCPSensorInterface,
    SimulatedSensorInterface,
    ConnectionStatus,
    DeviceType,
)


class ConnectionStatusWidget(QWidget):
    """Widget showing connection status for a device."""
    
    STATUS_COLORS = {
        ConnectionStatus.DISCONNECTED: '#6C7086',
        ConnectionStatus.CONNECTING: '#F9E2AF',
        ConnectionStatus.CONNECTED: '#A6E3A1',
        ConnectionStatus.ERROR: '#F38BA8',
        ConnectionStatus.RECONNECTING: '#FAB387',
    }
    
    def __init__(self, device_name: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.device_name = device_name
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the status widget."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        
        # Status indicator (colored circle)
        self.indicator = QLabel("●")
        self.indicator.setStyleSheet("color: #6C7086; font-size: 14px;")
        layout.addWidget(self.indicator)
        
        # Device name
        self.name_label = QLabel(self.device_name)
        self.name_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.name_label)
        
        # Status text
        self.status_label = QLabel("Disconnected")
        self.status_label.setStyleSheet("color: #6C7086;")
        layout.addWidget(self.status_label)
        
        # Data rate
        self.rate_label = QLabel("0 Hz")
        self.rate_label.setStyleSheet("color: #89B4FA;")
        layout.addWidget(self.rate_label)
        
        layout.addStretch()
    
    def update_status(self, status: ConnectionStatus, data_rate: float = 0.0):
        """Update the displayed status."""
        color = self.STATUS_COLORS.get(status, '#6C7086')
        self.indicator.setStyleSheet(f"color: {color}; font-size: 14px;")
        self.status_label.setText(status.value.capitalize())
        self.status_label.setStyleSheet(f"color: {color};")
        self.rate_label.setText(f"{data_rate:.1f} Hz")


class LiveDataPacketView(QWidget):
    """
    Live scrolling view of incoming data packets.
    
    Shows the last N packets with timestamp, device ID,
    and formatted data values.
    """
    
    def __init__(
        self,
        max_lines: int = 10,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        
        self.max_lines = max_lines
        self._packets: List[str] = []
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the packet view."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header = QLabel("Live Data Packets")
        header.setStyleSheet("font-weight: bold; color: #CDD6F4;")
        layout.addWidget(header)
        
        # Text display
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        self.text_display.setFont(QFont("Consolas", 9))
        self.text_display.setStyleSheet("""
            QTextEdit {
                background-color: #181825;
                color: #CDD6F4;
                border: 1px solid #313244;
                border-radius: 4px;
            }
        """)
        self.text_display.setMaximumHeight(200)
        layout.addWidget(self.text_display)
    
    def add_packet(self, packet: SensorPacket):
        """Add a packet to the display."""
        timestamp = datetime.fromtimestamp(packet.timestamp).strftime("%H:%M:%S.%f")[:-3]
        
        # Format packet as single line
        line = (
            f"[{timestamp}] {packet.device_id:12s} | "
            f"A: [{packet.accel_x:7.2f}, {packet.accel_y:7.2f}, {packet.accel_z:7.2f}] | "
            f"G: [{packet.gyro_x:6.3f}, {packet.gyro_y:6.3f}, {packet.gyro_z:6.3f}] | "
            f"ω: [{packet.omega_outer:6.3f}, {packet.omega_inner:6.3f}]"
        )
        
        self._packets.append(line)
        if len(self._packets) > self.max_lines:
            self._packets.pop(0)
        
        self.text_display.setText('\n'.join(self._packets))
        
        # Scroll to bottom
        scrollbar = self.text_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear(self):
        """Clear all packets."""
        self._packets.clear()
        self.text_display.clear()


class SensorDataTable(QWidget):
    """
    Table showing current sensor values.
    
    Displays all sensor channels with their current
    values, units, and status indicators.
    """
    
    CHANNELS = [
        ('Accel X', 'accel_x', 'm/s²'),
        ('Accel Y', 'accel_y', 'm/s²'),
        ('Accel Z', 'accel_z', 'm/s²'),
        ('Accel Mag', 'accel_mag', 'm/s²'),
        ('Gyro X', 'gyro_x', 'rad/s'),
        ('Gyro Y', 'gyro_y', 'rad/s'),
        ('Gyro Z', 'gyro_z', 'rad/s'),
        ('Encoder Outer', 'encoder_outer', 'rad'),
        ('Encoder Inner', 'encoder_inner', 'rad'),
        ('ω Outer', 'omega_outer', 'rad/s'),
        ('ω Inner', 'omega_inner', 'rad/s'),
        ('Temperature', 'temperature', '°C'),
    ]
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the data table."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create table
        self.table = QTableWidget(len(self.CHANNELS), 3)
        self.table.setHorizontalHeaderLabels(['Channel', 'Value', 'Unit'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #181825;
                color: #CDD6F4;
                border: 1px solid #313244;
                gridline-color: #313244;
            }
            QHeaderView::section {
                background-color: #1E1E2E;
                color: #CDD6F4;
                padding: 4px;
                border: 1px solid #313244;
            }
        """)
        
        # Populate initial values
        for i, (name, _, unit) in enumerate(self.CHANNELS):
            self.table.setItem(i, 0, QTableWidgetItem(name))
            self.table.setItem(i, 1, QTableWidgetItem('--'))
            self.table.setItem(i, 2, QTableWidgetItem(unit))
        
        layout.addWidget(self.table)
    
    def update_from_packet(self, packet: SensorPacket):
        """Update table values from a packet."""
        values = {
            'accel_x': packet.accel_x,
            'accel_y': packet.accel_y,
            'accel_z': packet.accel_z,
            'accel_mag': packet.get_accel_magnitude(),
            'gyro_x': packet.gyro_x,
            'gyro_y': packet.gyro_y,
            'gyro_z': packet.gyro_z,
            'encoder_outer': packet.encoder_outer,
            'encoder_inner': packet.encoder_inner,
            'omega_outer': packet.omega_outer,
            'omega_inner': packet.omega_inner,
            'temperature': packet.temperature,
        }
        
        for i, (_, key, _) in enumerate(self.CHANNELS):
            value = values.get(key, 0.0)
            item = self.table.item(i, 1)
            if item:
                item.setText(f'{value:.4f}')


class SensorPanel(QWidget):
    """
    Main sensor panel combining all sensor-related widgets.
    
    Features:
    - Device connection controls
    - Connection status indicators
    - Live packet display
    - Current values table
    - Recording controls
    """
    
    # Signals
    packet_received = pyqtSignal(object)  # SensorPacket
    connection_changed = pyqtSignal(str, object)  # device_name, status
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._interfaces: Dict[str, Any] = {}
        self._setup_ui()
        
        # Update timer for statistics
        self._stats_timer = QTimer()
        self._stats_timer.timeout.connect(self._update_statistics)
        self._stats_timer.start(1000)  # Update every second
    
    def _setup_ui(self):
        """Set up the sensor panel UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Connection Controls
        conn_group = QGroupBox("Device Connections")
        conn_layout = QGridLayout(conn_group)
        
        # Arduino section
        conn_layout.addWidget(QLabel("Arduino:"), 0, 0)
        self.arduino_port_combo = QComboBox()
        self.arduino_port_combo.addItem("Auto-detect")
        self._refresh_serial_ports()
        conn_layout.addWidget(self.arduino_port_combo, 0, 1)
        
        self.arduino_connect_btn = QPushButton("Connect")
        self.arduino_connect_btn.clicked.connect(self._on_arduino_connect)
        conn_layout.addWidget(self.arduino_connect_btn, 0, 2)
        
        # Raspberry Pi section
        conn_layout.addWidget(QLabel("Raspberry Pi:"), 1, 0)
        self.rpi_host_combo = QComboBox()
        self.rpi_host_combo.setEditable(True)
        self.rpi_host_combo.addItems(["192.168.1.100", "raspberrypi.local"])
        conn_layout.addWidget(self.rpi_host_combo, 1, 1)
        
        self.rpi_connect_btn = QPushButton("Connect")
        self.rpi_connect_btn.clicked.connect(self._on_rpi_connect)
        conn_layout.addWidget(self.rpi_connect_btn, 1, 2)
        
        # Simulator section
        conn_layout.addWidget(QLabel("Simulator:"), 2, 0)
        self.sim_rate_spin = QSpinBox()
        self.sim_rate_spin.setRange(10, 1000)
        self.sim_rate_spin.setValue(100)
        self.sim_rate_spin.setSuffix(" Hz")
        conn_layout.addWidget(self.sim_rate_spin, 2, 1)
        
        self.sim_connect_btn = QPushButton("Start Simulator")
        self.sim_connect_btn.clicked.connect(self._on_simulator_toggle)
        conn_layout.addWidget(self.sim_connect_btn, 2, 2)
        
        # Refresh ports button
        refresh_btn = QPushButton("↻ Refresh Ports")
        refresh_btn.clicked.connect(self._refresh_serial_ports)
        conn_layout.addWidget(refresh_btn, 0, 3)
        
        layout.addWidget(conn_group)
        
        # Status indicators
        status_group = QGroupBox("Connection Status")
        status_layout = QVBoxLayout(status_group)
        
        self.arduino_status = ConnectionStatusWidget("Arduino Uno")
        status_layout.addWidget(self.arduino_status)
        
        self.rpi_status = ConnectionStatusWidget("Raspberry Pi")
        status_layout.addWidget(self.rpi_status)
        
        self.sim_status = ConnectionStatusWidget("Simulator")
        status_layout.addWidget(self.sim_status)
        
        layout.addWidget(status_group)
        
        # Data display splitter
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Live packet view
        self.packet_view = LiveDataPacketView(max_lines=10)
        splitter.addWidget(self.packet_view)
        
        # Current values table
        self.data_table = SensorDataTable()
        splitter.addWidget(self.data_table)
        
        splitter.setSizes([200, 300])
        layout.addWidget(splitter)
        
        # Recording controls
        rec_group = QGroupBox("Data Recording")
        rec_layout = QHBoxLayout(rec_group)
        
        self.record_btn = QPushButton("⏺ Start Recording")
        self.record_btn.clicked.connect(self._on_record_toggle)
        rec_layout.addWidget(self.record_btn)
        
        self.record_status = QLabel("Not recording")
        self.record_status.setStyleSheet("color: #6C7086;")
        rec_layout.addWidget(self.record_status)
        
        self.record_progress = QProgressBar()
        self.record_progress.setMaximum(0)  # Indeterminate
        self.record_progress.setVisible(False)
        rec_layout.addWidget(self.record_progress)
        
        rec_layout.addStretch()
        layout.addWidget(rec_group)
    
    def _refresh_serial_ports(self):
        """Refresh the list of available serial ports."""
        current = self.arduino_port_combo.currentText()
        self.arduino_port_combo.clear()
        self.arduino_port_combo.addItem("Auto-detect")
        
        ports = SerialSensorInterface.list_ports()
        for port in ports:
            self.arduino_port_combo.addItem(
                f"{port['device']} - {port['description']}"
            )
        
        # Restore selection if possible
        idx = self.arduino_port_combo.findText(current)
        if idx >= 0:
            self.arduino_port_combo.setCurrentIndex(idx)
    
    def _on_arduino_connect(self):
        """Handle Arduino connect/disconnect."""
        if 'arduino' in self._interfaces:
            self._disconnect_device('arduino')
            self.arduino_connect_btn.setText("Connect")
            return
        
        # Get port
        port_text = self.arduino_port_combo.currentText()
        if "Auto-detect" in port_text:
            port = "auto"
        else:
            port = port_text.split(" - ")[0]
        
        # Create interface
        interface = SerialSensorInterface(
            port=port,
            device_id="arduino_main",
            use_binary_protocol=False,  # Use JSON for easier debugging
        )
        
        if interface.connect():
            self._interfaces['arduino'] = interface
            interface.add_callback(self._on_packet)
            interface.start_streaming()
            self.arduino_connect_btn.setText("Disconnect")
            self.arduino_status.update_status(ConnectionStatus.CONNECTED)
        else:
            self.arduino_status.update_status(ConnectionStatus.ERROR)
    
    def _on_rpi_connect(self):
        """Handle Raspberry Pi connect/disconnect."""
        if 'rpi' in self._interfaces:
            self._disconnect_device('rpi')
            self.rpi_connect_btn.setText("Connect")
            return
        
        host = self.rpi_host_combo.currentText()
        
        interface = TCPSensorInterface(
            host=host,
            port=5000,
            device_id="rpi_main",
        )
        
        if interface.connect():
            self._interfaces['rpi'] = interface
            interface.add_callback(self._on_packet)
            interface.start_streaming()
            self.rpi_connect_btn.setText("Disconnect")
            self.rpi_status.update_status(ConnectionStatus.CONNECTED)
        else:
            self.rpi_status.update_status(ConnectionStatus.ERROR)
    
    def _on_simulator_toggle(self):
        """Handle simulator start/stop."""
        if 'simulator' in self._interfaces:
            self._disconnect_device('simulator')
            self.sim_connect_btn.setText("Start Simulator")
            return
        
        rate = self.sim_rate_spin.value()
        
        interface = SimulatedSensorInterface(
            sample_rate=rate,
            device_id="simulator",
        )
        
        interface.connect()
        self._interfaces['simulator'] = interface
        interface.add_callback(self._on_packet)
        interface.start_streaming()
        
        self.sim_connect_btn.setText("Stop Simulator")
        self.sim_status.update_status(ConnectionStatus.CONNECTED, rate)
    
    def _disconnect_device(self, name: str):
        """Disconnect a device by name."""
        if name in self._interfaces:
            interface = self._interfaces.pop(name)
            interface.disconnect()
            
            # Update status widget
            status_widget = {
                'arduino': self.arduino_status,
                'rpi': self.rpi_status,
                'simulator': self.sim_status,
            }.get(name)
            
            if status_widget:
                status_widget.update_status(ConnectionStatus.DISCONNECTED)
    
    def _on_packet(self, packet: SensorPacket):
        """Handle incoming packet."""
        # Update displays (using signal for thread safety)
        self.packet_view.add_packet(packet)
        self.data_table.update_from_packet(packet)
        
        # Emit signal for other components
        self.packet_received.emit(packet)
    
    def _on_record_toggle(self):
        """Toggle recording."""
        # TODO: Integrate with DataAcquisitionManager
        pass
    
    def _update_statistics(self):
        """Update connection statistics."""
        for name, interface in self._interfaces.items():
            stats = interface.get_statistics()
            rate = stats.get('data_rate', 0)
            
            status_widget = {
                'arduino': self.arduino_status,
                'rpi': self.rpi_status,
                'simulator': self.sim_status,
            }.get(name)
            
            if status_widget:
                status_widget.update_status(interface.status, rate)
    
    def get_simulated_interface(self) -> Optional[SimulatedSensorInterface]:
        """Get the simulated sensor interface if running."""
        return self._interfaces.get('simulator')
    
    def disconnect_all(self):
        """Disconnect all devices."""
        for name in list(self._interfaces.keys()):
            self._disconnect_device(name)
