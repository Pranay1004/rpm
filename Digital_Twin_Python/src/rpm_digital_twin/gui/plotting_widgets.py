"""
Live Plotting Widgets - Real-time Data Visualization

High-performance plotting widgets using PyQtGraph for:
- Time-series sensor data
- 3D trajectory visualization
- Gravity vector sphere coverage
- Microgravity metrics plots

Copyright (c) 2026 Space Research Laboratory
"""

import numpy as np
from numpy.typing import NDArray
from typing import Optional, Dict, List, Tuple, Any
import time

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QCheckBox, QGroupBox, QSplitter,
    QFrame, QPushButton, QSpinBox,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont

import pyqtgraph as pg
import pyqtgraph.opengl as gl

# Configure PyQtGraph for dark theme
pg.setConfigOptions(
    antialias=True,
    background='#1E1E2E',
    foreground='#CDD6F4',
)


class LivePlotWidget(QWidget):
    """
    Real-time scrolling plot for sensor data.
    
    Features:
    - Multiple data channels with legend
    - Auto-scaling Y-axis
    - Configurable time window
    - High frame rate updates (30-60 FPS)
    """
    
    def __init__(
        self,
        title: str = "Live Data",
        y_label: str = "Value",
        y_unit: str = "",
        time_window: float = 60.0,
        update_rate: float = 30.0,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        
        self.title = title
        self.y_label = y_label
        self.y_unit = y_unit
        self.time_window = time_window
        self.update_rate = update_rate
        
        # Data storage
        self._channels: Dict[str, Dict[str, Any]] = {}
        self._start_time = time.time()
        
        self._setup_ui()
        
        # Update timer
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_plot)
        self._timer.start(int(1000 / update_rate))
    
    def _setup_ui(self):
        """Set up the plot widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setTitle(self.title, color='#CDD6F4', size='12pt')
        self.plot_widget.setLabel('left', self.y_label, units=self.y_unit, color='#CDD6F4')
        self.plot_widget.setLabel('bottom', 'Time', units='s', color='#CDD6F4')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setMouseEnabled(x=True, y=True)
        self.plot_widget.enableAutoRange(axis='y')
        
        # Add legend
        self.legend = self.plot_widget.addLegend(offset=(10, 10))
        
        layout.addWidget(self.plot_widget)
    
    def add_channel(
        self,
        name: str,
        color: str = '#89B4FA',
        width: int = 2,
        max_points: int = 10000,
    ) -> None:
        """Add a data channel to the plot."""
        pen = pg.mkPen(color=color, width=width)
        curve = self.plot_widget.plot([], [], pen=pen, name=name)
        
        self._channels[name] = {
            'curve': curve,
            'times': np.zeros(max_points),
            'values': np.zeros(max_points),
            'index': 0,
            'count': 0,
            'max_points': max_points,
            'color': color,
        }
    
    def update_data(self, channel: str, timestamp: float, value: float) -> None:
        """Update data for a channel."""
        if channel not in self._channels:
            return
        
        ch = self._channels[channel]
        idx = ch['index']
        
        ch['times'][idx] = timestamp - self._start_time
        ch['values'][idx] = value
        ch['index'] = (idx + 1) % ch['max_points']
        ch['count'] = min(ch['count'] + 1, ch['max_points'])
    
    def update_batch(self, channel: str, timestamps: NDArray, values: NDArray) -> None:
        """Update multiple data points at once."""
        if channel not in self._channels:
            return
        
        for t, v in zip(timestamps, values):
            self.update_data(channel, t, v)
    
    def _update_plot(self) -> None:
        """Update plot display (called by timer)."""
        current_time = time.time() - self._start_time
        x_min = max(0, current_time - self.time_window)
        
        for name, ch in self._channels.items():
            if ch['count'] == 0:
                continue
            
            # Get valid data
            if ch['count'] < ch['max_points']:
                times = ch['times'][:ch['count']]
                values = ch['values'][:ch['count']]
            else:
                # Handle wrap-around
                idx = ch['index']
                times = np.concatenate([ch['times'][idx:], ch['times'][:idx]])
                values = np.concatenate([ch['values'][idx:], ch['values'][:idx]])
            
            # Filter to visible window
            mask = times >= x_min
            ch['curve'].setData(times[mask], values[mask])
        
        # Update X range
        self.plot_widget.setXRange(x_min, current_time, padding=0.02)
    
    def clear(self) -> None:
        """Clear all data."""
        for ch in self._channels.values():
            ch['times'].fill(0)
            ch['values'].fill(0)
            ch['index'] = 0
            ch['count'] = 0
        self._start_time = time.time()
    
    def set_time_window(self, seconds: float) -> None:
        """Set the visible time window."""
        self.time_window = seconds


class MultiChannelPlot(QWidget):
    """
    Multi-channel plot widget with channel selector.
    
    Displays multiple synchronized data channels with
    individual visibility toggles.
    """
    
    CHANNEL_COLORS = [
        '#89B4FA',  # Blue
        '#A6E3A1',  # Green
        '#F38BA8',  # Red
        '#F9E2AF',  # Yellow
        '#CBA6F7',  # Purple
        '#94E2D5',  # Cyan
        '#FAB387',  # Orange
        '#F5C2E7',  # Pink
    ]
    
    def __init__(
        self,
        title: str = "Multi-Channel Plot",
        channels: Optional[List[str]] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        
        self.title = title
        self._setup_ui(channels or [])
    
    def _setup_ui(self, channels: List[str]):
        """Set up the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Channel controls
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Channels:"))
        
        self._checkboxes: Dict[str, QCheckBox] = {}
        for i, name in enumerate(channels):
            color = self.CHANNEL_COLORS[i % len(self.CHANNEL_COLORS)]
            cb = QCheckBox(name)
            cb.setChecked(True)
            cb.setStyleSheet(f"color: {color};")
            cb.stateChanged.connect(self._on_channel_toggle)
            controls.addWidget(cb)
            self._checkboxes[name] = cb
        
        controls.addStretch()
        layout.addLayout(controls)
        
        # Plot
        self.plot = LivePlotWidget(title=self.title)
        for i, name in enumerate(channels):
            color = self.CHANNEL_COLORS[i % len(self.CHANNEL_COLORS)]
            self.plot.add_channel(name, color=color)
        
        layout.addWidget(self.plot)
    
    def _on_channel_toggle(self):
        """Handle channel visibility toggle."""
        for name, cb in self._checkboxes.items():
            if name in self.plot._channels:
                self.plot._channels[name]['curve'].setVisible(cb.isChecked())
    
    def update_data(self, channel: str, timestamp: float, value: float):
        """Update channel data."""
        self.plot.update_data(channel, timestamp, value)


class TrajectoryPlot3D(QWidget):
    """
    3D trajectory visualization using OpenGL.
    
    Displays:
    - Sample point trajectory in inertial frame
    - Gravity vector on unit sphere
    - Coordinate axes
    - Real-time animation
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._trajectory_points: List[Tuple[float, float, float]] = []
        self._max_points = 10000
        
        self._setup_ui()
        
        # Update timer
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_display)
        self._timer.start(33)  # ~30 FPS
    
    def _setup_ui(self):
        """Set up the 3D view."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create OpenGL widget
        self.gl_widget = gl.GLViewWidget()
        self.gl_widget.setCameraPosition(distance=0.5, elevation=30, azimuth=45)
        self.gl_widget.setBackgroundColor('#1E1E2E')
        
        layout.addWidget(self.gl_widget)
        
        # Add coordinate axes
        self._add_axes()
        
        # Add unit sphere (wireframe)
        self._add_sphere()
        
        # Trajectory line
        self.trajectory_line = gl.GLLinePlotItem(
            pos=np.zeros((1, 3)),
            color=(0.54, 0.71, 0.98, 0.8),
            width=2,
            antialias=True,
        )
        self.gl_widget.addItem(self.trajectory_line)
        
        # Current position marker
        self.current_pos = gl.GLScatterPlotItem(
            pos=np.array([[0, 0, 0]]),
            color=(0.95, 0.55, 0.66, 1.0),
            size=15,
        )
        self.gl_widget.addItem(self.current_pos)
        
        # Gravity vector arrow
        self.gravity_arrow = gl.GLLinePlotItem(
            pos=np.array([[0, 0, 0], [0, -0.2, 0]]),
            color=(0.65, 0.89, 0.63, 1.0),
            width=3,
        )
        self.gl_widget.addItem(self.gravity_arrow)
    
    def _add_axes(self):
        """Add coordinate axes."""
        axis_length = 0.15
        
        # X-axis (red)
        x_axis = gl.GLLinePlotItem(
            pos=np.array([[0, 0, 0], [axis_length, 0, 0]]),
            color=(1.0, 0.4, 0.4, 1.0),
            width=2,
        )
        self.gl_widget.addItem(x_axis)
        
        # Y-axis (green)
        y_axis = gl.GLLinePlotItem(
            pos=np.array([[0, 0, 0], [0, axis_length, 0]]),
            color=(0.4, 1.0, 0.4, 1.0),
            width=2,
        )
        self.gl_widget.addItem(y_axis)
        
        # Z-axis (blue)
        z_axis = gl.GLLinePlotItem(
            pos=np.array([[0, 0, 0], [0, 0, axis_length]]),
            color=(0.4, 0.4, 1.0, 1.0),
            width=2,
        )
        self.gl_widget.addItem(z_axis)
    
    def _add_sphere(self):
        """Add wireframe unit sphere."""
        # Create sphere mesh
        md = gl.MeshData.sphere(rows=20, cols=20, radius=0.1)
        
        sphere = gl.GLMeshItem(
            meshdata=md,
            smooth=True,
            color=(0.5, 0.5, 0.5, 0.1),
            shader='shaded',
            glOptions='translucent',
        )
        self.gl_widget.addItem(sphere)
    
    def add_trajectory_point(self, x: float, y: float, z: float) -> None:
        """Add a point to the trajectory."""
        self._trajectory_points.append((x, y, z))
        if len(self._trajectory_points) > self._max_points:
            self._trajectory_points.pop(0)
    
    def update_gravity_vector(self, gx: float, gy: float, gz: float) -> None:
        """Update the gravity vector display."""
        scale = 0.15  # Visual scale
        self.gravity_arrow.setData(
            pos=np.array([[0, 0, 0], [gx * scale, gy * scale, gz * scale]])
        )
    
    def update_current_position(self, x: float, y: float, z: float) -> None:
        """Update the current position marker."""
        self.current_pos.setData(pos=np.array([[x, y, z]]))
    
    def _update_display(self) -> None:
        """Update the display."""
        if len(self._trajectory_points) > 1:
            pos = np.array(self._trajectory_points)
            self.trajectory_line.setData(pos=pos)
    
    def clear(self) -> None:
        """Clear the trajectory."""
        self._trajectory_points.clear()
        self.trajectory_line.setData(pos=np.zeros((1, 3)))


class GravityVectorPlot(QWidget):
    """
    Gravity vector visualization on unit sphere.
    
    Shows the coverage of the gravity vector direction
    over time, visualizing how well the RPM randomizes
    the gravity direction.
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._gravity_points: List[Tuple[float, float, float]] = []
        self._max_points = 50000
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the visualization."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header with stats
        header = QHBoxLayout()
        header.addWidget(QLabel("Gravity Vector Coverage"))
        self.coverage_label = QLabel("Coverage: 0%")
        self.coverage_label.setStyleSheet("color: #A6E3A1;")
        header.addWidget(self.coverage_label)
        header.addStretch()
        layout.addLayout(header)
        
        # 3D view
        self.gl_widget = gl.GLViewWidget()
        self.gl_widget.setCameraPosition(distance=3, elevation=30, azimuth=45)
        self.gl_widget.setBackgroundColor('#1E1E2E')
        
        layout.addWidget(self.gl_widget)
        
        # Add unit sphere
        self._add_unit_sphere()
        
        # Add axes
        self._add_axes()
        
        # Gravity points scatter
        self.gravity_scatter = gl.GLScatterPlotItem(
            pos=np.array([[0, 0, 1]]),
            color=(0.54, 0.71, 0.98, 0.6),
            size=3,
        )
        self.gl_widget.addItem(self.gravity_scatter)
        
        # Current gravity direction
        self.current_gravity = gl.GLScatterPlotItem(
            pos=np.array([[0, 0, 1]]),
            color=(0.95, 0.55, 0.66, 1.0),
            size=15,
        )
        self.gl_widget.addItem(self.current_gravity)
    
    def _add_unit_sphere(self):
        """Add transparent unit sphere."""
        md = gl.MeshData.sphere(rows=30, cols=30, radius=1.0)
        
        sphere = gl.GLMeshItem(
            meshdata=md,
            smooth=True,
            color=(0.5, 0.5, 0.5, 0.15),
            shader='shaded',
            glOptions='translucent',
        )
        self.gl_widget.addItem(sphere)
    
    def _add_axes(self):
        """Add coordinate axes."""
        axis_length = 1.3
        
        axes_data = [
            ([0, 0, 0], [axis_length, 0, 0], (1.0, 0.4, 0.4, 1.0)),  # X
            ([0, 0, 0], [0, axis_length, 0], (0.4, 1.0, 0.4, 1.0)),  # Y
            ([0, 0, 0], [0, 0, axis_length], (0.4, 0.4, 1.0, 1.0)),  # Z
        ]
        
        for start, end, color in axes_data:
            axis = gl.GLLinePlotItem(
                pos=np.array([start, end]),
                color=color,
                width=2,
            )
            self.gl_widget.addItem(axis)
    
    def add_gravity_direction(self, gx: float, gy: float, gz: float) -> None:
        """Add a gravity direction point."""
        # Normalize to unit sphere
        mag = np.sqrt(gx**2 + gy**2 + gz**2)
        if mag > 0:
            gx, gy, gz = gx/mag, gy/mag, gz/mag
        
        self._gravity_points.append((gx, gy, gz))
        if len(self._gravity_points) > self._max_points:
            self._gravity_points.pop(0)
        
        # Update scatter plot
        if len(self._gravity_points) > 0:
            pos = np.array(self._gravity_points)
            self.gravity_scatter.setData(pos=pos)
        
        # Update current position
        self.current_gravity.setData(pos=np.array([[gx, gy, gz]]))
    
    def calculate_coverage(self) -> float:
        """
        Calculate sphere coverage percentage.
        
        Uses a simple binning approach to estimate what
        fraction of the unit sphere has been covered.
        """
        if len(self._gravity_points) < 10:
            return 0.0
        
        # Bin the sphere into regions
        n_bins_theta = 18  # Polar angle bins
        n_bins_phi = 36    # Azimuthal angle bins
        
        covered = set()
        
        for gx, gy, gz in self._gravity_points:
            # Convert to spherical coordinates
            theta = np.arccos(np.clip(gz, -1, 1))  # 0 to π
            phi = np.arctan2(gy, gx)  # -π to π
            
            # Bin indices
            theta_bin = int(theta / np.pi * n_bins_theta)
            phi_bin = int((phi + np.pi) / (2 * np.pi) * n_bins_phi)
            
            covered.add((theta_bin, phi_bin))
        
        total_bins = n_bins_theta * n_bins_phi
        coverage = len(covered) / total_bins * 100
        
        self.coverage_label.setText(f"Coverage: {coverage:.1f}%")
        return coverage
    
    def clear(self) -> None:
        """Clear all gravity points."""
        self._gravity_points.clear()
        self.gravity_scatter.setData(pos=np.array([[0, 0, 1]]))


class AccelerationPlot(LivePlotWidget):
    """Specialized plot for acceleration data with g-level reference lines."""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(
            title="Acceleration",
            y_label="Acceleration",
            y_unit="g",
            parent=parent,
        )
        
        # Add reference lines
        self._add_reference_lines()
        
        # Add channels
        self.add_channel('Centripetal', color='#89B4FA')
        self.add_channel('Effective', color='#A6E3A1')
        self.add_channel('Total', color='#F9E2AF')
    
    def _add_reference_lines(self):
        """Add reference lines for microgravity levels."""
        # 1g reference
        line_1g = pg.InfiniteLine(
            pos=1.0,
            angle=0,
            pen=pg.mkPen('#F38BA8', width=1, style=Qt.PenStyle.DashLine),
            label='1g',
            labelOpts={'color': '#F38BA8', 'position': 0.95},
        )
        self.plot_widget.addItem(line_1g)
        
        # 0.01g target (microgravity threshold)
        line_ug = pg.InfiniteLine(
            pos=0.01,
            angle=0,
            pen=pg.mkPen('#A6E3A1', width=1, style=Qt.PenStyle.DashLine),
            label='0.01g (µg target)',
            labelOpts={'color': '#A6E3A1', 'position': 0.95},
        )
        self.plot_widget.addItem(line_ug)


class AngularVelocityPlot(LivePlotWidget):
    """Specialized plot for angular velocity data."""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(
            title="Angular Velocity",
            y_label="Angular Velocity",
            y_unit="rad/s",
            parent=parent,
        )
        
        # Add channels
        self.add_channel('ω_outer (φ̇)', color='#89B4FA')
        self.add_channel('ω_inner (ψ̇)', color='#F9E2AF')
        
        # Add max velocity reference
        line_max = pg.InfiniteLine(
            pos=1.047,
            angle=0,
            pen=pg.mkPen('#F38BA8', width=1, style=Qt.PenStyle.DashLine),
            label='Max (10 RPM)',
            labelOpts={'color': '#F38BA8', 'position': 0.95},
        )
        self.plot_widget.addItem(line_max)
        
        line_min = pg.InfiniteLine(
            pos=-1.047,
            angle=0,
            pen=pg.mkPen('#F38BA8', width=1, style=Qt.PenStyle.DashLine),
        )
        self.plot_widget.addItem(line_min)
