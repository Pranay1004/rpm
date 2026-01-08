"""
Motor Control Panel - NEMA Motor Control Interface

GUI panel for controlling the RPM's dual-axis motor system
with velocity input in RPM or rad/s units.

Copyright (c) 2026 Space Research Laboratory
"""

from typing import Optional, Dict, Any
import math

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGroupBox, QGridLayout, QPushButton, QComboBox,
    QDoubleSpinBox, QSlider, QFrame, QProgressBar,
    QDial, QCheckBox, QRadioButton, QButtonGroup,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QBrush

from rpm_digital_twin.core.motor_controller import (
    MotorController,
    VelocityUnit,
    ControlMode,
    MotorState,
)


class VelocityDial(QWidget):
    """
    Custom dial widget for velocity input.
    
    Shows current velocity with visual indicator
    and allows direct value input.
    """
    
    value_changed = pyqtSignal(float)
    
    def __init__(
        self,
        name: str = "Motor",
        min_value: float = -10.0,
        max_value: float = 10.0,
        unit: str = "RPM",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        
        self.name = name
        self.min_value = min_value
        self.max_value = max_value
        self.unit = unit
        self._current_value = 0.0
        self._target_value = 0.0
        
        self.setMinimumSize(150, 200)
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the dial UI."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel(self.name)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(title)
        
        # Dial
        self.dial = QDial()
        self.dial.setRange(int(self.min_value * 100), int(self.max_value * 100))
        self.dial.setValue(0)
        self.dial.setWrapping(False)
        self.dial.setNotchesVisible(True)
        self.dial.valueChanged.connect(self._on_dial_changed)
        layout.addWidget(self.dial)
        
        # Value display
        value_layout = QHBoxLayout()
        
        self.value_spin = QDoubleSpinBox()
        self.value_spin.setRange(self.min_value, self.max_value)
        self.value_spin.setDecimals(3)
        self.value_spin.setSingleStep(0.1)
        self.value_spin.setValue(0.0)
        self.value_spin.valueChanged.connect(self._on_spin_changed)
        value_layout.addWidget(self.value_spin)
        
        unit_label = QLabel(self.unit)
        value_layout.addWidget(unit_label)
        
        layout.addLayout(value_layout)
        
        # Current value indicator
        self.current_label = QLabel("Current: 0.000")
        self.current_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.current_label.setStyleSheet("color: #89B4FA;")
        layout.addWidget(self.current_label)
    
    def _on_dial_changed(self, value: int):
        """Handle dial value change."""
        self._target_value = value / 100.0
        self.value_spin.blockSignals(True)
        self.value_spin.setValue(self._target_value)
        self.value_spin.blockSignals(False)
        self.value_changed.emit(self._target_value)
    
    def _on_spin_changed(self, value: float):
        """Handle spinbox value change."""
        self._target_value = value
        self.dial.blockSignals(True)
        self.dial.setValue(int(value * 100))
        self.dial.blockSignals(False)
        self.value_changed.emit(value)
    
    def set_current_value(self, value: float):
        """Set the current (actual) value display."""
        self._current_value = value
        self.current_label.setText(f"Current: {value:.3f}")
    
    def set_target_value(self, value: float):
        """Set the target value."""
        self._target_value = value
        self.value_spin.blockSignals(True)
        self.dial.blockSignals(True)
        self.value_spin.setValue(value)
        self.dial.setValue(int(value * 100))
        self.value_spin.blockSignals(False)
        self.dial.blockSignals(False)
    
    def get_value(self) -> float:
        """Get the current target value."""
        return self._target_value


class MotorStatusWidget(QWidget):
    """Widget showing detailed motor status."""
    
    def __init__(self, name: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.name = name
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the status widget."""
        layout = QGridLayout(self)
        layout.setSpacing(5)
        
        # State
        layout.addWidget(QLabel("State:"), 0, 0)
        self.state_label = QLabel("IDLE")
        self.state_label.setStyleSheet("color: #A6E3A1; font-weight: bold;")
        layout.addWidget(self.state_label, 0, 1)
        
        # Position
        layout.addWidget(QLabel("Position:"), 1, 0)
        self.position_label = QLabel("0.000 rad (0.0°)")
        layout.addWidget(self.position_label, 1, 1)
        
        # Velocity
        layout.addWidget(QLabel("Velocity:"), 2, 0)
        self.velocity_label = QLabel("0.000 rad/s (0.0 RPM)")
        layout.addWidget(self.velocity_label, 2, 1)
        
        # Acceleration
        layout.addWidget(QLabel("Acceleration:"), 3, 0)
        self.accel_label = QLabel("0.000 rad/s²")
        layout.addWidget(self.accel_label, 3, 1)
        
        # Temperature
        layout.addWidget(QLabel("Temperature:"), 4, 0)
        self.temp_label = QLabel("25.0 °C")
        layout.addWidget(self.temp_label, 4, 1)
    
    def update_status(self, status: Dict[str, Any]):
        """Update the status display."""
        state = status.get('state', 'unknown')
        state_colors = {
            'idle': '#A6E3A1',
            'running': '#89B4FA',
            'accelerating': '#F9E2AF',
            'decelerating': '#FAB387',
            'error': '#F38BA8',
            'emergency_stop': '#F38BA8',
        }
        color = state_colors.get(state, '#6C7086')
        self.state_label.setText(state.upper())
        self.state_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        
        pos_rad = status.get('position_rad', 0.0)
        pos_deg = status.get('position_deg', 0.0)
        self.position_label.setText(f"{pos_rad:.3f} rad ({pos_deg:.1f}°)")
        
        vel_rad = status.get('velocity_rad_s', 0.0)
        vel_rpm = status.get('velocity_rpm', 0.0)
        self.velocity_label.setText(f"{vel_rad:.3f} rad/s ({vel_rpm:.2f} RPM)")
        
        accel = status.get('acceleration', 0.0)
        self.accel_label.setText(f"{accel:.3f} rad/s²")
        
        temp = status.get('temperature', 25.0)
        self.temp_label.setText(f"{temp:.1f} °C")


class MotorControlPanel(QWidget):
    """
    Main motor control panel.
    
    Features:
    - Dual velocity controls (outer/inner frame)
    - Unit selection (RPM, rad/s)
    - Control mode selection (Manual, Random)
    - Emergency stop button
    - Real-time motor status display
    """
    
    # Signals
    velocity_changed = pyqtSignal(float, float)  # omega_outer, omega_inner
    emergency_stop_triggered = pyqtSignal()
    mode_changed = pyqtSignal(str)  # control mode
    
    def __init__(
        self,
        motor_controller: Optional[MotorController] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        
        self.motor_controller = motor_controller or MotorController()
        self._unit = VelocityUnit.RPM
        
        self._setup_ui()
        
        # Update timer
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_status)
        self._timer.start(50)  # 20 Hz update
    
    def _setup_ui(self):
        """Set up the control panel UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Unit selection
        unit_group = QGroupBox("Velocity Units")
        unit_layout = QHBoxLayout(unit_group)
        
        self.unit_group = QButtonGroup(self)
        
        self.rpm_radio = QRadioButton("RPM")
        self.rpm_radio.setChecked(True)
        self.rpm_radio.toggled.connect(lambda: self._on_unit_changed(VelocityUnit.RPM))
        self.unit_group.addButton(self.rpm_radio)
        unit_layout.addWidget(self.rpm_radio)
        
        self.rads_radio = QRadioButton("rad/s")
        self.rads_radio.toggled.connect(lambda: self._on_unit_changed(VelocityUnit.RAD_PER_SEC))
        self.unit_group.addButton(self.rads_radio)
        unit_layout.addWidget(self.rads_radio)
        
        self.degs_radio = QRadioButton("deg/s")
        self.degs_radio.toggled.connect(lambda: self._on_unit_changed(VelocityUnit.DEG_PER_SEC))
        self.unit_group.addButton(self.degs_radio)
        unit_layout.addWidget(self.degs_radio)
        
        unit_layout.addStretch()
        layout.addWidget(unit_group)
        
        # Velocity controls
        velocity_group = QGroupBox("Velocity Control")
        velocity_layout = QHBoxLayout(velocity_group)
        
        # Outer frame dial
        self.outer_dial = VelocityDial(
            name="Outer Frame (NEMA 34)",
            min_value=-10.0,
            max_value=10.0,
            unit="RPM",
        )
        self.outer_dial.value_changed.connect(self._on_velocity_changed)
        velocity_layout.addWidget(self.outer_dial)
        
        # Inner frame dial
        self.inner_dial = VelocityDial(
            name="Inner Frame (NEMA 23)",
            min_value=-10.0,
            max_value=10.0,
            unit="RPM",
        )
        self.inner_dial.value_changed.connect(self._on_velocity_changed)
        velocity_layout.addWidget(self.inner_dial)
        
        layout.addWidget(velocity_group)
        
        # Quick velocity presets
        preset_group = QGroupBox("Velocity Presets")
        preset_layout = QGridLayout(preset_group)
        
        presets = [
            ("Stop All", 0, 0),
            ("1 RPM", 1, 1),
            ("5 RPM", 5, 5),
            ("10 RPM", 10, 10),
            ("Opposite 5", 5, -5),
            ("Slow/Fast", 2, 8),
        ]
        
        for i, (name, outer, inner) in enumerate(presets):
            btn = QPushButton(name)
            btn.clicked.connect(lambda _, o=outer, i=inner: self._apply_preset(o, i))
            preset_layout.addWidget(btn, i // 3, i % 3)
        
        layout.addWidget(preset_group)
        
        # Control mode
        mode_group = QGroupBox("Control Mode")
        mode_layout = QVBoxLayout(mode_group)
        
        mode_buttons = QHBoxLayout()
        
        self.manual_btn = QPushButton("Manual")
        self.manual_btn.setCheckable(True)
        self.manual_btn.setChecked(True)
        self.manual_btn.clicked.connect(lambda: self._set_mode(ControlMode.VELOCITY))
        mode_buttons.addWidget(self.manual_btn)
        
        self.random_btn = QPushButton("Random Positioning")
        self.random_btn.setCheckable(True)
        self.random_btn.clicked.connect(lambda: self._set_mode(ControlMode.RANDOM))
        mode_buttons.addWidget(self.random_btn)
        
        mode_layout.addLayout(mode_buttons)
        
        # Random mode parameters
        random_params = QHBoxLayout()
        random_params.addWidget(QLabel("P(change):"))
        self.prob_spin = QDoubleSpinBox()
        self.prob_spin.setRange(0.0001, 0.1)
        self.prob_spin.setDecimals(4)
        self.prob_spin.setValue(0.001)
        self.prob_spin.setSingleStep(0.0001)
        random_params.addWidget(self.prob_spin)
        random_params.addStretch()
        mode_layout.addLayout(random_params)
        
        layout.addWidget(mode_group)
        
        # Motor status
        status_group = QGroupBox("Motor Status")
        status_layout = QHBoxLayout(status_group)
        
        self.outer_status = MotorStatusWidget("Outer Frame")
        status_layout.addWidget(self.outer_status)
        
        self.inner_status = MotorStatusWidget("Inner Frame")
        status_layout.addWidget(self.inner_status)
        
        layout.addWidget(status_group)
        
        # Emergency stop
        self.estop_btn = QPushButton("⛔ EMERGENCY STOP")
        self.estop_btn.setMinimumHeight(50)
        self.estop_btn.setStyleSheet("""
            QPushButton {
                background-color: #F38BA8;
                color: #1E1E2E;
                font-weight: bold;
                font-size: 14pt;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #EBA0AC;
            }
            QPushButton:pressed {
                background-color: #E64553;
            }
        """)
        self.estop_btn.clicked.connect(self._on_emergency_stop)
        layout.addWidget(self.estop_btn)
        
        # Reset button (after E-stop)
        self.reset_btn = QPushButton("↻ Reset Emergency Stop")
        self.reset_btn.setVisible(False)
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #A6E3A1;
                color: #1E1E2E;
                font-weight: bold;
            }
        """)
        self.reset_btn.clicked.connect(self._on_reset)
        layout.addWidget(self.reset_btn)
    
    def _on_unit_changed(self, unit: VelocityUnit):
        """Handle unit change."""
        self._unit = unit
        
        # Update dial labels and ranges
        unit_str = {
            VelocityUnit.RPM: "RPM",
            VelocityUnit.RAD_PER_SEC: "rad/s",
            VelocityUnit.DEG_PER_SEC: "deg/s",
        }[unit]
        
        max_val = {
            VelocityUnit.RPM: 10.0,
            VelocityUnit.RAD_PER_SEC: 1.047,
            VelocityUnit.DEG_PER_SEC: 60.0,
        }[unit]
        
        self.outer_dial.unit = unit_str
        self.outer_dial.max_value = max_val
        self.outer_dial.min_value = -max_val
        
        self.inner_dial.unit = unit_str
        self.inner_dial.max_value = max_val
        self.inner_dial.min_value = -max_val
    
    def _on_velocity_changed(self, _):
        """Handle velocity dial change."""
        omega_outer = self.outer_dial.get_value()
        omega_inner = self.inner_dial.get_value()
        
        # Apply to motor controller
        self.motor_controller.set_velocities(omega_outer, omega_inner, self._unit)
        
        # Emit signal
        self.velocity_changed.emit(omega_outer, omega_inner)
    
    def _apply_preset(self, outer: float, inner: float):
        """Apply a velocity preset."""
        self.outer_dial.set_target_value(outer)
        self.inner_dial.set_target_value(inner)
        self._on_velocity_changed(None)
    
    def _set_mode(self, mode: ControlMode):
        """Set the control mode."""
        self.manual_btn.setChecked(mode == ControlMode.VELOCITY)
        self.random_btn.setChecked(mode == ControlMode.RANDOM)
        
        if mode == ControlMode.RANDOM:
            prob = self.prob_spin.value()
            self.motor_controller.start_random_positioning(
                velocity_change_prob=prob
            )
            self.outer_dial.setEnabled(False)
            self.inner_dial.setEnabled(False)
        else:
            self.motor_controller.stop_random_positioning()
            self.outer_dial.setEnabled(True)
            self.inner_dial.setEnabled(True)
        
        self.mode_changed.emit(mode.value)
    
    def _on_emergency_stop(self):
        """Handle emergency stop."""
        self.motor_controller.emergency_stop()
        self.estop_btn.setEnabled(False)
        self.reset_btn.setVisible(True)
        self.outer_dial.setEnabled(False)
        self.inner_dial.setEnabled(False)
        self.emergency_stop_triggered.emit()
    
    def _on_reset(self):
        """Reset after emergency stop."""
        self.motor_controller.reset_emergency_stop()
        self.estop_btn.setEnabled(True)
        self.reset_btn.setVisible(False)
        self.outer_dial.setEnabled(True)
        self.inner_dial.setEnabled(True)
        self._apply_preset(0, 0)
    
    def _update_status(self):
        """Update motor status displays."""
        status = self.motor_controller.get_status()
        self.outer_status.update_status(status['outer_motor'])
        self.inner_status.update_status(status['inner_motor'])
        
        # Update current values on dials
        self.outer_dial.set_current_value(
            status['outer_motor']['velocity_rpm'] if self._unit == VelocityUnit.RPM
            else status['outer_motor']['velocity_rad_s']
        )
        self.inner_dial.set_current_value(
            status['inner_motor']['velocity_rpm'] if self._unit == VelocityUnit.RPM
            else status['inner_motor']['velocity_rad_s']
        )
    
    def get_current_velocities(self) -> tuple:
        """Get current motor velocities."""
        return self.motor_controller.get_velocities(self._unit)
    
    def start_motors(self):
        """Start the motor control loops."""
        self.motor_controller.start()
    
    def stop_motors(self):
        """Stop the motor control loops."""
        self.motor_controller.stop()
