"""
Microgravity Analysis Panel for RPM Digital Twin.

Provides interactive 3D point-entry widget for numerical vs experimental
microgravity comparison, plus live gravity vector visualization.
"""

from PyQt6 import QtWidgets, QtCore, QtGui
import numpy as np
import pyqtgraph as pg
from typing import Optional

from rpm_digital_twin.core.microgravity import (
    gravity_in_payload_frame,
    centripetal_acceleration_at_point,
    taSMG_metric,
)


class MicrogravityAnalysisPanel(QtWidgets.QGroupBox):
    """Panel for microgravity analysis and comparison."""
    
    def __init__(self, parent=None):
        super().__init__("Microgravity Analysis", parent)
        self.setStyleSheet("QGroupBox { font-weight: bold; border: 2px solid #0d7377; }")
        
        layout = QtWidgets.QVBoxLayout(self)
        
        # 3D point input
        point_group = QtWidgets.QGroupBox("Sample Point (m)")
        point_layout = QtWidgets.QHBoxLayout()
        point_group.setLayout(point_layout)
        
        self.spin_x = QtWidgets.QDoubleSpinBox()
        self.spin_x.setRange(-0.2, 0.2)
        self.spin_x.setSuffix(" X")
        self.spin_x.setValue(0.0)
        self.spin_x.setSingleStep(0.01)
        
        self.spin_y = QtWidgets.QDoubleSpinBox()
        self.spin_y.setRange(-0.2, 0.2)
        self.spin_y.setSuffix(" Y")
        self.spin_y.setValue(0.0)
        self.spin_y.setSingleStep(0.01)
        
        self.spin_z = QtWidgets.QDoubleSpinBox()
        self.spin_z.setRange(-0.2, 0.2)
        self.spin_z.setSuffix(" Z")
        self.spin_z.setValue(0.0)
        self.spin_z.setSingleStep(0.01)
        
        point_layout.addWidget(self.spin_x)
        point_layout.addWidget(self.spin_y)
        point_layout.addWidget(self.spin_z)
        layout.addWidget(point_group)
        
        # Results display
        results_group = QtWidgets.QGroupBox("Numerical Results")
        results_layout = QtWidgets.QGridLayout()
        results_group.setLayout(results_layout)
        
        # Gravity metrics
        results_layout.addWidget(QtWidgets.QLabel("Gravity RMS (g):"), 0, 0)
        self.label_g_rms = QtWidgets.QLabel("0.000")
        self.label_g_rms.setStyleSheet("color: #14919b; font-weight: bold; font-size: 12px;")
        results_layout.addWidget(self.label_g_rms, 0, 1)
        
        results_layout.addWidget(QtWidgets.QLabel("Centripetal (g):"), 1, 0)
        self.label_accel_c = QtWidgets.QLabel("0.000")
        self.label_accel_c.setStyleSheet("color: #f39c12; font-weight: bold; font-size: 12px;")
        results_layout.addWidget(self.label_accel_c, 1, 1)
        
        results_layout.addWidget(QtWidgets.QLabel("Total (g):"), 2, 0)
        self.label_g_total = QtWidgets.QLabel("0.000")
        self.label_g_total.setStyleSheet("color: #2ecc71; font-weight: bold; font-size: 12px;")
        results_layout.addWidget(self.label_g_total, 2, 1)
        
        # Experimental input
        results_layout.addWidget(QtWidgets.QLabel("Exp. Gravity (g):"), 3, 0)
        self.spin_exp_g = QtWidgets.QDoubleSpinBox()
        self.spin_exp_g.setRange(0, 1)
        self.spin_exp_g.setValue(1.0)
        self.spin_exp_g.setSingleStep(0.01)
        results_layout.addWidget(self.spin_exp_g, 3, 1)
        
        # Difference
        results_layout.addWidget(QtWidgets.QLabel("Difference:"), 4, 0)
        self.label_diff = QtWidgets.QLabel("0.000")
        self.label_diff.setStyleSheet("color: #e74c3c; font-weight: bold; font-size: 12px;")
        results_layout.addWidget(self.label_diff, 4, 1)
        
        layout.addWidget(results_group)
        
        # 3D vector plot
        self.plot_3d = pg.PlotWidget(title="Gravity Vector Field")
        self.plot_3d.setLabel('left', 'Y (m/s²)')
        self.plot_3d.setLabel('bottom', 'Time (s)')
        layout.addWidget(self.plot_3d)
        
        # Store current state
        self._current_theta_outer = 0.0
        self._current_theta_inner = 0.0
        self._current_omega_outer = 0.0
        self._current_omega_inner = 0.0
        self._gravity_history = []
        self._timestamp_history = []
    
    def update_kinematics(
        self,
        theta_outer: float,
        theta_inner: float,
        omega_outer: float,
        omega_inner: float,
        timestamp: float,
    ) -> None:
        """Update kinematics and recalculate microgravity."""
        self._current_theta_outer = theta_outer
        self._current_theta_inner = theta_inner
        self._current_omega_outer = omega_outer
        self._current_omega_inner = omega_inner
        
        # Get sample point
        r = np.array([
            self.spin_x.value(),
            self.spin_y.value(),
            self.spin_z.value(),
        ])
        
        # Compute gravity in payload frame
        g_payload = gravity_in_payload_frame(theta_outer, theta_inner, g=9.81)
        g_mag = np.linalg.norm(g_payload) / 9.81
        
        # Compute centripetal acceleration
        a_c = centripetal_acceleration_at_point(
            omega_outer, omega_inner, theta_outer, theta_inner, r
        )
        a_c_mag = np.linalg.norm(a_c) / 9.81
        
        # Total
        g_total = np.linalg.norm(g_payload + a_c) / 9.81
        
        # Update labels
        self.label_g_rms.setText(f"{g_mag:.6f}")
        self.label_accel_c.setText(f"{a_c_mag:.6f}")
        self.label_g_total.setText(f"{g_total:.6f}")
        
        # Compute difference from experimental
        exp_g = self.spin_exp_g.value()
        diff = abs(g_mag - exp_g)
        self.label_diff.setText(f"{diff:.6f}")
        
        # Update history
        self._gravity_history.append(g_payload)
        self._timestamp_history.append(timestamp)
        
        # Keep last 1000 samples
        if len(self._gravity_history) > 1000:
            self._gravity_history = self._gravity_history[-1000:]
            self._timestamp_history = self._timestamp_history[-1000:]
        
        # Update plot
        if len(self._timestamp_history) > 0:
            t_arr = np.array(self._timestamp_history)
            g_arr = np.array(self._gravity_history)
            t_rel = t_arr - t_arr[0]
            
            self.plot_3d.clear()
            self.plot_3d.plot(t_rel, g_arr[:, 0] / 9.81, pen='r', name='gx')
            self.plot_3d.plot(t_rel, g_arr[:, 1] / 9.81, pen='g', name='gy')
            self.plot_3d.plot(t_rel, g_arr[:, 2] / 9.81, pen='b', name='gz')
    
    def get_analysis_state(self) -> dict:
        """Return current analysis state."""
        return {
            'point_x': self.spin_x.value(),
            'point_y': self.spin_y.value(),
            'point_z': self.spin_z.value(),
            'experimental_g': self.spin_exp_g.value(),
            'samples': len(self._gravity_history),
        }
    
    def clear_history(self) -> None:
        """Clear collected data."""
        self._gravity_history.clear()
        self._timestamp_history.clear()
        self.plot_3d.clear()
