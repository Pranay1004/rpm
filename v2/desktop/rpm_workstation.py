"""
IIST RPM Workstation v2.0 - Scientific Laboratory Interface.
Indian Institute of Space Science and Technology (IIST), Dept of Aerospace Engineering.
Clean, professional desktop workstation devoid of AI clutter.
Pure white-background publication-quality plots, true CAD metrics, and CSV export.
"""

import sys
import os
import time
from typing import List, Dict, Any
import numpy as np

# Ensure matplotlib writable config dir inside workspace
mpl_dir = os.path.join(os.path.dirname(__file__), "..", ".cache", "matplotlib")
os.makedirs(mpl_dir, exist_ok=True)
os.environ["MPLCONFIGDIR"] = os.path.abspath(mpl_dir)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QComboBox, QDoubleSpinBox,
    QSlider, QGroupBox, QFileDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QTabWidget, QSplitter
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont, QColor, QPalette

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D

# Add simulation path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from simulation.kinematics import RPMKinematics
from simulation.volumetric_field import VolumetricFieldSolver
from simulation.fdm_fluid_solver import FluidShearStressFDMSolver
from simulation.trajectory_modes import TrajectoryController, TrajectoryMode
from desktop.data_exporter import ScientificDataExporter


class ScientificMatplotlibCanvas(FigureCanvas):
    """Clean white-background canvas for scientific plots."""
    def __init__(self, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi, facecolor="#ffffff")
        super().__init__(self.fig)
        self.setStyleSheet("background-color: #ffffff; border: 1px solid #cbd5e1;")


class RPMWorkstationApp(QMainWindow):
    """Professional scientific desktop application for RPM simulation & hardware sync."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("IIST RPM Digital Twin v2.0 — Aerospace Laboratory Workstation")
        self.resize(1400, 900)

        # Scientific simulation instances
        self.kinematics = RPMKinematics()
        self.volumetric = VolumetricFieldSolver(default_chamber_radius_m=0.06)
        self.fdm = FluidShearStressFDMSolver(radius_m=0.06)
        self.controller = TrajectoryController()

        # Telemetry records for CSV export
        self.telemetry_history: List[Dict[str, Any]] = []
        self.is_running = True
        self.dt = 0.02  # 50 Hz loop

        # Kinematic state
        self.phi_deg = 0.0
        self.psi_deg = 0.0

        # Data buffers for live plotting
        self.buf_len = 300
        self.time_buf = []
        self.gx_buf = []
        self.gy_buf = []
        self.gz_buf = []
        self.tasmg_buf = []
        self.sphere_points = []

        self._init_ui()

        # 50 Hz physics timer
        self.timer = QTimer()
        self.timer.timeout.connect(self._physics_step)
        self.timer.start(20)

    def _init_ui(self):
        # Professional clean laboratory color palette (light neutral)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f1f5f9;
            }
            QWidget {
                color: #0f172a;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                font-size: 12px;
            }
            QGroupBox {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                margin-top: 10px;
                padding: 12px;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                color: #1e3a8a;
            }
            QPushButton {
                background-color: #e2e8f0;
                border: 1px solid #94a3b8;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: 500;
                color: #0f172a;
            }
            QPushButton:hover {
                background-color: #cbd5e1;
            }
            QPushButton#btn-start {
                background-color: #15803d;
                color: #ffffff;
                border: 1px solid #166534;
            }
            QPushButton#btn-start:hover {
                background-color: #166534;
            }
            QPushButton#btn-stop {
                background-color: #b91c1c;
                color: #ffffff;
                border: 1px solid #991b1b;
            }
            QPushButton#btn-stop:hover {
                background-color: #991b1b;
            }
            QPushButton#btn-export {
                background-color: #1e3a8a;
                color: #ffffff;
                border: 1px solid #1e40af;
            }
            QPushButton#btn-export:hover {
                background-color: #1e40af;
            }
            QComboBox, QDoubleSpinBox {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QLabel.metric-val {
                font-family: "JetBrains Mono", "SF Mono", Menlo, Consolas, monospace;
                font-size: 16px;
                font-weight: 600;
                color: #0f172a;
            }
            QLabel.metric-unit {
                color: #64748b;
                font-size: 11px;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # LEFT SIDE: Controls, CAD Metrics & Instrumentation (Width: 380px)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        left_panel.setFixedWidth(380)

        # Header Badge
        header_box = QGroupBox("IIST Aerospace Engineering")
        h_layout = QVBoxLayout(header_box)
        title_lbl = QLabel("RANDOM POSITIONING MACHINE")
        title_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #1e3a8a;")
        sub_lbl = QLabel("Microgravity Simulation Laboratory • Batch 2025-2027")
        sub_lbl.setStyleSheet("color: #475569; font-size: 11px;")
        h_layout.addWidget(title_lbl)
        h_layout.addWidget(sub_lbl)
        left_layout.addWidget(header_box)

        # Operation Mode
        mode_box = QGroupBox("Trajectory Mode")
        m_layout = QVBoxLayout(mode_box)
        self.mode_select = QComboBox()
        self.mode_select.addItem("Clinostat Optimal (Kim 2026, γ = 1.146)", TrajectoryMode.CLINOSTAT_OPTIMAL)
        self.mode_select.addItem("Clinostat 3D (Constant 2.0 / 2.0 RPM)", TrajectoryMode.CLINOSTAT_3D)
        self.mode_select.addItem("Stochastic RPM Mode A (Pica 2026)", TrajectoryMode.RPM_STOCHASTIC)
        self.mode_select.currentIndexChanged.connect(self._on_mode_changed)
        m_layout.addWidget(self.mode_select)
        left_layout.addWidget(mode_box)

        # Motor Speeds & Chamber Radius
        control_box = QGroupBox("Drive & Geometry Settings")
        c_layout = QGridLayout(control_box)
        
        c_layout.addWidget(QLabel("Inner Gimbal (φ):"), 0, 0)
        self.inner_rpm_spin = QDoubleSpinBox()
        self.inner_rpm_spin.setRange(0.0, 30.0)
        self.inner_rpm_spin.setValue(2.0)
        self.inner_rpm_spin.setSingleStep(0.1)
        self.inner_rpm_spin.valueChanged.connect(self._on_speeds_changed)
        c_layout.addWidget(self.inner_rpm_spin, 0, 1)
        c_layout.addWidget(QLabel("RPM"), 0, 2)

        c_layout.addWidget(QLabel("Outer Gimbal (ψ):"), 1, 0)
        self.outer_rpm_spin = QDoubleSpinBox()
        self.outer_rpm_spin.setRange(0.0, 30.0)
        self.outer_rpm_spin.setValue(2.292)
        self.outer_rpm_spin.setSingleStep(0.1)
        self.outer_rpm_spin.valueChanged.connect(self._on_speeds_changed)
        c_layout.addWidget(self.outer_rpm_spin, 1, 1)
        c_layout.addWidget(QLabel("RPM"), 1, 2)

        c_layout.addWidget(QLabel("Chamber Radius (r):"), 2, 0)
        self.radius_spin = QDoubleSpinBox()
        self.radius_spin.setRange(0.5, 15.0)
        self.radius_spin.setValue(6.0)
        self.radius_spin.setSingleStep(0.5)
        self.radius_spin.valueChanged.connect(self._on_radius_changed)
        c_layout.addWidget(self.radius_spin, 2, 1)
        c_layout.addWidget(QLabel("cm"), 2, 2)

        left_layout.addWidget(control_box)

        # Real CAD Specifications (from Final_Drawing.pdf)
        cad_box = QGroupBox("CAD Physical Specifications (Final_Drawing.pdf)")
        cad_layout = QGridLayout(cad_box)
        cad_specs = [
            ("Base Plate (Part 1):", "1200 × 900 × 45 mm (Steel)"),
            ("Side Supports (Part 2):", "A-Frame Height 491 mm (25.4 mm)"),
            ("Outer Frame (Part 5):", "500 × 500 × 50.8 mm (Al6061)"),
            ("Inner Frame (Part 6):", "350 × 350 × 50.8 mm (Al6061)"),
            ("Payload Cube (Part 3):", "200 × 200 mm (120 mm Chamber)"),
            ("Outer Drive (Slide 11):", "NEMA 34 Stepper (I_zz = 0.614)"),
            ("Inner Drive (Slide 11):", "NEMA 23 Stepper (I_yy = 0.172)")
        ]
        for row, (lbl, val) in enumerate(cad_specs):
            cad_layout.addWidget(QLabel(lbl), row, 0)
            v_lbl = QLabel(val)
            v_lbl.setStyleSheet("font-family: monospace; font-size: 11px; color: #334155;")
            cad_layout.addWidget(v_lbl, row, 1)
        left_layout.addWidget(cad_box)

        # Simulation Action Controls
        action_layout = QHBoxLayout()
        self.btn_start = QPushButton("▶ START")
        self.btn_start.setObjectName("btn-start")
        self.btn_start.clicked.connect(self._start_sim)
        self.btn_stop = QPushButton("⏹ STOP")
        self.btn_stop.setObjectName("btn-stop")
        self.btn_stop.clicked.connect(self._stop_sim)
        self.btn_reset = QPushButton("↺ RESET")
        self.btn_reset.clicked.connect(self._reset_sim)
        action_layout.addWidget(self.btn_start)
        action_layout.addWidget(self.btn_stop)
        action_layout.addWidget(self.btn_reset)
        left_layout.addLayout(action_layout)

        # Export Button (Scientific CSV and High-Res Plots)
        export_box = QGroupBox("Scientific Data Export")
        exp_layout = QVBoxLayout(export_box)
        self.btn_export_csv = QPushButton("📥 Export Telemetry Log (.CSV)")
        self.btn_export_csv.setObjectName("btn-export")
        self.btn_export_csv.clicked.connect(self._export_csv)
        self.btn_export_plot = QPushButton("📊 Export Publication Plot (.PNG)")
        self.btn_export_plot.clicked.connect(self._export_plot)
        exp_layout.addWidget(self.btn_export_csv)
        exp_layout.addWidget(self.btn_export_plot)
        left_layout.addWidget(export_box)

        left_layout.addStretch()
        main_layout.addWidget(left_panel)

        # RIGHT SIDE: Scientific Canvases & Instrumentation Metrics
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        # Metrics Summary Bar
        metrics_bar = QWidget()
        metrics_bar.setStyleSheet("background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px;")
        m_bar_layout = QHBoxLayout(metrics_bar)
        
        self.lbl_tasmg = self._create_metric_widget(m_bar_layout, "taSMG (Cumulative)", "1.0000", "g")
        self.lbl_inst_g = self._create_metric_widget(m_bar_layout, "Instantaneous Accel", "1.000", "g")
        self.lbl_centrifugal = self._create_metric_widget(m_bar_layout, "Centrifugal Bias (Edge)", "0.0000", "g")
        self.lbl_safe_radius = self._create_metric_widget(m_bar_layout, "Safe Radius (10⁻³g)", "22.3", "cm")
        self.lbl_shear = self._create_metric_widget(m_bar_layout, "Wall Shear Stress", "0.00", "mPa")
        self.lbl_samples = self._create_metric_widget(m_bar_layout, "Logged Samples", "0", "steps")
        
        right_layout.addWidget(metrics_bar)

        # Splitter with 2 Pure White Background Canvases
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Plot 1: Time Series of Gx, Gy, Gz and taSMG (Matching Fig 1B, 2B, 3B of PPTX)
        self.ts_canvas = ScientificMatplotlibCanvas(width=8, height=3.5)
        self.ts_ax = self.ts_canvas.fig.add_subplot(111)
        self._setup_timeseries_plot()
        splitter.addWidget(self.ts_canvas)

        # Plot 2: Lower row: Left = S^2 Sphere Trajectory (Fig 1C, 2C, 3C), Right = FDM Fluid Velocity Profile
        lower_widget = QWidget()
        lower_layout = QHBoxLayout(lower_widget)
        lower_layout.setContentsMargins(0, 0, 0, 0)
        
        self.sphere_canvas = ScientificMatplotlibCanvas(width=4, height=3.5)
        self.sphere_ax = self.sphere_canvas.fig.add_subplot(111, projection='3d')
        self._setup_sphere_plot()
        lower_layout.addWidget(self.sphere_canvas)

        self.fdm_canvas = ScientificMatplotlibCanvas(width=4, height=3.5)
        self.fdm_ax = self.fdm_canvas.fig.add_subplot(111)
        self._setup_fdm_plot()
        lower_layout.addWidget(self.fdm_canvas)

        splitter.addWidget(lower_widget)
        right_layout.addWidget(splitter)

        main_layout.addWidget(right_panel, stretch=1)

    def _create_metric_widget(self, parent_layout, label_text, default_val, unit_text):
        container = QWidget()
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(4, 2, 4, 2)
        c_layout.setSpacing(2)
        title = QLabel(label_text)
        title.setStyleSheet("font-size: 11px; color: #64748b; font-weight: 500;")
        val = QLabel(default_val)
        val.setObjectName("metric-val")
        val.setStyleSheet("font-family: monospace; font-size: 15px; font-weight: 700; color: #1e3a8a;")
        unit = QLabel(unit_text)
        unit.setObjectName("metric-unit")
        c_layout.addWidget(title)
        c_layout.addWidget(val)
        c_layout.addWidget(unit)
        parent_layout.addWidget(container)
        return val

    def _setup_timeseries_plot(self):
        self.ts_ax.clear()
        self.ts_ax.set_facecolor("#ffffff")
        self.ts_ax.grid(True, linestyle="--", linewidth=0.5, color="#e2e8f0")
        self.ts_ax.set_title("Gravity Vector Components & taSMG (Yotov et al. 2022)", fontsize=11, fontweight="bold", color="#0f172a")
        self.ts_ax.set_xlabel("Time (s)", fontsize=10, color="#334155")
        self.ts_ax.set_ylabel("Effective Acceleration (g)", fontsize=10, color="#334155")
        self.ts_ax.set_ylim(-1.25, 1.25)
        for spine in self.ts_ax.spines.values():
            spine.set_color("#64748b")
            spine.set_linewidth(0.8)

    def _setup_sphere_plot(self):
        self.sphere_ax.clear()
        self.sphere_ax.set_facecolor("#ffffff")
        self.sphere_ax.grid(False)
        self.sphere_ax.set_title("S² Unit Sphere Trajectory (Kim et al. 2026)", fontsize=11, fontweight="bold", color="#0f172a")
        # Draw wireframe sphere
        u = np.linspace(0, 2 * np.pi, 20)
        v = np.linspace(0, np.pi, 10)
        x = np.outer(np.cos(u), np.sin(v))
        y = np.outer(np.sin(u), np.sin(v))
        z = np.outer(np.ones(np.size(u)), np.cos(v))
        self.sphere_ax.plot_wireframe(x, y, z, color="#cbd5e1", linewidth=0.5, alpha=0.6)
        self.sphere_ax.set_xlim([-1.1, 1.1])
        self.sphere_ax.set_ylim([-1.1, 1.1])
        self.sphere_ax.set_zlim([-1.1, 1.1])
        self.sphere_ax.set_xlabel("Gx", fontsize=9)
        self.sphere_ax.set_ylabel("Gy", fontsize=9)
        self.sphere_ax.set_zlabel("Gz", fontsize=9)

    def _setup_fdm_plot(self):
        self.fdm_ax.clear()
        self.fdm_ax.set_facecolor("#ffffff")
        self.fdm_ax.grid(True, linestyle="--", linewidth=0.5, color="#e2e8f0")
        self.fdm_ax.set_title("1D Navier-Stokes Velocity Profile (Hasenstein & van Loon 2015)", fontsize=11, fontweight="bold", color="#0f172a")
        self.fdm_ax.set_xlabel("Radial Distance r (cm)", fontsize=10, color="#334155")
        self.fdm_ax.set_ylabel("Azimuthal Velocity u_θ (mm/s)", fontsize=10, color="#334155")
        for spine in self.fdm_ax.spines.values():
            spine.set_color("#64748b")
            spine.set_linewidth(0.8)

    def _on_mode_changed(self, idx):
        mode = self.mode_select.itemData(idx)
        self.controller.apply_mode(mode)
        if mode == TrajectoryMode.CLINOSTAT_OPTIMAL:
            self.outer_rpm_spin.setValue(self.inner_rpm_spin.value() * 1.146)
        elif mode == TrajectoryMode.CLINOSTAT_3D:
            self.outer_rpm_spin.setValue(self.inner_rpm_spin.value())

    def _on_speeds_changed(self):
        inner = self.inner_rpm_spin.value()
        outer = self.outer_rpm_spin.value()
        self.controller.set_base_speeds(inner, outer)

    def _on_radius_changed(self):
        r_m = self.radius_spin.value() / 100.0
        self.volumetric.set_chamber_radius(r_m)
        self.fdm.reset(r_m)

    def _start_sim(self):
        self.is_running = True

    def _stop_sim(self):
        self.is_running = False

    def _reset_sim(self):
        self.kinematics.reset()
        self.volumetric.reset()
        self.fdm.reset()
        self.time_buf.clear()
        self.gx_buf.clear()
        self.gy_buf.clear()
        self.gz_buf.clear()
        self.tasmg_buf.clear()
        self.sphere_points.clear()
        self.telemetry_history.clear()
        self._update_plots()

    def _physics_step(self):
        if not self.is_running:
            return

        # Advance controller
        omega_phi, omega_psi, alpha_phi, alpha_psi = self.controller.update(self.dt)

        # Integrate angles: 1 RPM = 6 deg/sec
        self.phi_deg = (self.phi_deg + omega_phi * 6.0 * self.dt) % 360.0
        self.psi_deg = (self.psi_deg + omega_psi * 6.0 * self.dt) % 360.0

        # Kinematic state
        state = self.kinematics.step(
            dt=self.dt,
            phi_deg=self.phi_deg,
            psi_deg=self.psi_deg,
            omega_phi_rpm=omega_phi,
            omega_psi_rpm=omega_psi,
            alpha_phi_rad_s2=alpha_phi,
            alpha_psi_rad_s2=alpha_psi
        )

        # Volumetric field
        a_cent, a_euler, r_safe, mean_edge_g = self.volumetric.compute_field(
            g_payload_unit=state.e_g,
            omega_phi_rpm=omega_phi,
            omega_psi_rpm=omega_psi,
            alpha_phi_rad_s2=alpha_phi,
            alpha_psi_rad_s2=alpha_psi
        )

        # FDM fluid shear stress
        omega_norm_rad_s = float(np.sqrt((omega_phi * np.pi / 30.0)**2 + (omega_psi * np.pi / 30.0)**2))
        shear_stress_mPa = self.fdm.step(self.dt, omega_norm_rad_s)

        # Update metric labels
        self.lbl_tasmg.setText(f"{state.taSMG:.5f}")
        self.lbl_inst_g.setText(f"{state.instantaneous_g:.3f}")
        self.lbl_centrifugal.setText(f"{a_cent:.5f}")
        self.lbl_safe_radius.setText(f"{r_safe:.1f}")
        self.lbl_shear.setText(f"{shear_stress_mPa:.2f}")
        self.lbl_samples.setText(f"{self.kinematics.samples:,}")

        # Record for CSV export
        record = {
            "timestamp": state.timestamp,
            "phi_deg": state.phi_deg,
            "psi_deg": state.psi_deg,
            "omega_phi_rpm": state.omega_phi_rpm,
            "omega_psi_rpm": state.omega_psi_rpm,
            "alpha_phi_rad_s2": state.alpha_phi_rad_s2,
            "alpha_psi_rad_s2": state.alpha_psi_rad_s2,
            "gx": state.e_g[0],
            "gy": state.e_g[1],
            "gz": state.e_g[2],
            "instant_g": state.instantaneous_g,
            "taSMG": state.taSMG,
            "centrifugal_edge_g": a_cent,
            "euler_edge_g": a_euler,
            "shear_stress_mPa": shear_stress_mPa,
            "telemetry_residual_g": ""
        }
        self.telemetry_history.append(record)

        # Data buffers
        self.time_buf.append(state.timestamp)
        self.gx_buf.append(state.e_g[0])
        self.gy_buf.append(state.e_g[1])
        self.gz_buf.append(state.e_g[2])
        self.tasmg_buf.append(state.taSMG)
        self.sphere_points.append(state.e_g)

        if len(self.time_buf) > self.buf_len:
            self.time_buf.pop(0)
            self.gx_buf.pop(0)
            self.gy_buf.pop(0)
            self.gz_buf.pop(0)
            self.tasmg_buf.pop(0)
        if len(self.sphere_points) > 300:
            self.sphere_points.pop(0)

        # Update plots every 5 steps (10 Hz refresh)
        if self.kinematics.samples % 5 == 0:
            self._update_plots()

    def _update_plots(self):
        # 1. Update Time-Series Plot
        self.ts_ax.clear()
        self._setup_timeseries_plot()
        if len(self.time_buf) > 1:
            self.ts_ax.plot(self.time_buf, self.gx_buf, label="Gx", color="#dc2626", linewidth=1.2)
            self.ts_ax.plot(self.time_buf, self.gy_buf, label="Gy", color="#2563eb", linewidth=1.2)
            self.ts_ax.plot(self.time_buf, self.gz_buf, label="Gz", color="#059669", linewidth=1.2)
            self.ts_ax.plot(self.time_buf, self.tasmg_buf, label="<g> taSMG", color="#0f172a", linewidth=1.8, linestyle="--")
            self.ts_ax.axhline(0.001, color="#d97706", linestyle=":", linewidth=1.0, label="10⁻³ g Threshold")
            self.ts_ax.legend(loc="upper right", framealpha=0.9, fontsize=9)
        self.ts_canvas.draw()

        # 2. Update S^2 Sphere Plot
        self.sphere_ax.clear()
        self._setup_sphere_plot()
        if len(self.sphere_points) > 1:
            pts = np.array(self.sphere_points)
            self.sphere_ax.plot(pts[:, 0], pts[:, 1], pts[:, 2], color="#2563eb", linewidth=0.8, alpha=0.8)
            # Current point
            curr = pts[-1]
            self.sphere_ax.scatter([curr[0]], [curr[1]], [curr[2]], color="#dc2626", s=35)
        self.sphere_canvas.draw()

        # 3. Update FDM Profile Plot
        self.fdm_ax.clear()
        self._setup_fdm_plot()
        r_cm = self.fdm.r_nodes * 100.0
        u_mm_s = self.fdm.u_theta * 1000.0
        self.fdm_ax.plot(r_cm, u_mm_s, color="#1e3a8a", linewidth=1.6, label="Velocity u_θ(r)")
        self.fdm_ax.axvline(self.fdm.stokes_boundary_layer_mm / 10.0, color="#d97706", linestyle=":", linewidth=1.2, label=f"Stokes Layer δ = {self.fdm.stokes_boundary_layer_mm:.1f} mm")
        self.fdm_ax.legend(loc="upper left", framealpha=0.9, fontsize=9)
        self.fdm_canvas.draw()

    def _export_csv(self):
        if not self.telemetry_history:
            QMessageBox.warning(self, "No Data", "No simulation data logged yet.")
            return

        default_name = f"iist_rpm_telemetry_{int(time.time())}.csv"
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Telemetry CSV", default_name, "CSV Files (*.csv)"
        )
        if filepath:
            metadata = {
                "Trajectory Mode": self.controller.mode.value,
                "Inner Frame Dimensions (CAD)": "350 x 350 x 50.8 mm (Al6061)",
                "Outer Frame Dimensions (CAD)": "500 x 500 x 50.8 mm (Al6061)",
                "Payload Holder (CAD)": "200 x 200 mm Polycarbonate (120 mm Cavity)",
                "Chamber Radius": f"{self.radius_spin.value():.1f} cm",
                "Inner Motor (φ)": f"{self.inner_rpm_spin.value():.2f} RPM",
                "Outer Motor (ψ)": f"{self.outer_rpm_spin.value():.2f} RPM",
                "Sampling Rate": "50 Hz (dt = 0.02 s)",
                "Total Samples Logged": len(self.telemetry_history)
            }
            ScientificDataExporter.export_telemetry_csv(filepath, self.telemetry_history, metadata)
            QMessageBox.information(
                self, "Export Complete",
                f"Successfully exported {len(self.telemetry_history):,} records to:\n{filepath}"
            )

    def _export_plot(self):
        default_name = f"iist_rpm_plot_{int(time.time())}.png"
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Publication Plot", default_name, "PNG Image (*.png);;PDF Document (*.pdf)"
        )
        if filepath:
            self.ts_canvas.fig.savefig(filepath, dpi=300, facecolor="#ffffff", bbox_inches="tight")
            QMessageBox.information(
                self, "Export Complete",
                f"Successfully saved 300 DPI publication figure to:\n{filepath}"
            )

RPMWorkstationWindow = RPMWorkstationApp


def main():
    app = QApplication(sys.argv)
    window = RPMWorkstationApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
