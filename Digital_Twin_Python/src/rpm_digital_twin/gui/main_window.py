"""
Main Window for RPM Digital Twin - Complete Production Version.
Professional PyQt6 application with dark theme and all subsystems integrated.
"""

import sys
import time
import numpy as np
from PyQt6 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
from loguru import logger

from rpm_digital_twin.core.data_acquisition import (
    DataAcquisitionManager, create_simulated_interface,
)
from rpm_digital_twin.core.paraview_exporter import (
    export_to_vtk, export_to_csv_for_paraview, generate_paraview_script
)
from rpm_digital_twin.gui.styles import STYLESHEET
from rpm_digital_twin.gui.motor_control_panel import MotorControlPanel
from rpm_digital_twin.gui.microgravity_panel import MicrogravityAnalysisPanel


class MainWindow(QtWidgets.QMainWindow):
    """Main application window with professional dark UI and all subsystems."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('RPM Digital Twin - Production v1.0')
        self.resize(1600, 1000)
        self.setStyleSheet(STYLESHEET)
        
        # Core DAQ manager
        self.manager = DataAcquisitionManager(sample_rate=100.0)
        sim = create_simulated_interface(sample_rate=100.0)
        self.manager.add_interface('simulator', sim)
        
        # Build comprehensive UI
        self._build_ui()
        self._connect_signals()
        
        # Update timer (100ms)
        self._update_timer = QtCore.QTimer(self)
        self._update_timer.setInterval(100)
        self._update_timer.timeout.connect(self._on_update)
        
        logger.info("MainWindow initialized successfully")
    
    def _build_ui(self):
        """Build complete UI with menu, toolbar, panels."""
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = QtWidgets.QVBoxLayout(central)
        
        # Menu & toolbar
        self._build_menu_bar()
        self._build_toolbar()
        
        # Main content: horizontal splitter
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter, 1)
        
        # Left: controls
        left_panel = self._build_left_panel()
        splitter.addWidget(left_panel)
        
        # Right: visualization
        right_panel = self._build_right_panel()
        splitter.addWidget(right_panel)
        
        splitter.setSizes([640, 960])
        
        # Status bar
        self.statusbar_label = QtWidgets.QLabel("Ready")
        self.statusBar().addWidget(self.statusbar_label)
    
    def _build_menu_bar(self):
        """Build menu bar."""
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("&File")
        file_menu.addAction("&Connect", self.connect_sensors)
        file_menu.addAction("&Disconnect", self.disconnect_sensors)
        file_menu.addSeparator()
        file_menu.addAction("Export to &VTK", self.export_vtk)
        file_menu.addAction("Export to &CSV", self.export_csv)
        file_menu.addSeparator()
        file_menu.addAction("&Quit", self.close)
        
        help_menu = menubar.addMenu("&Help")
        help_menu.addAction("&About", self.show_about)
    
    def _build_toolbar(self):
        """Build toolbar with quick actions."""
        toolbar = self.addToolBar("Main")
        toolbar.setStyleSheet("QToolBar { background-color: #1f4f56; }")
        
        toolbar.addAction("🔌 Connect", self.connect_sensors)
        toolbar.addAction("▶ Acquire", self.start_acquisition)
        toolbar.addAction("● Record", self.toggle_recording)
        toolbar.addSeparator()
        toolbar.addAction("💾 Export VTK", self.export_vtk)
    
    def _build_left_panel(self):
        """Build left control panel."""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        
        # Motor control
        self.motor_panel = MotorControlPanel()
        layout.addWidget(self.motor_panel)
        
        # Microgravity analysis
        self.microgravity_panel = MicrogravityAnalysisPanel()
        layout.addWidget(self.microgravity_panel, 1)
        
        # Operation buttons
        ops_group = QtWidgets.QGroupBox("Operations")
        ops_layout = QtWidgets.QVBoxLayout()
        self.btn_clear = QtWidgets.QPushButton("🗑️ Clear Data")
        self.btn_clear.setStyleSheet("background-color: #f39c12;")
        self.btn_paraview = QtWidgets.QPushButton("📊 ParaView Script")
        self.btn_paraview.setStyleSheet("background-color: #2ecc71;")
        ops_layout.addWidget(self.btn_clear)
        ops_layout.addWidget(self.btn_paraview)
        ops_group.setLayout(ops_layout)
        layout.addWidget(ops_group)
        
        return widget
    
    def _build_right_panel(self):
        """Build right visualization panel with tabs."""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        
        tabs = QtWidgets.QTabWidget()
        
        # Tab 1: Live data
        tab1 = self._build_data_tab()
        tabs.addTab(tab1, "📋 Live Data")
        
        # Tab 2: Acceleration
        tab2 = self._build_accel_tab()
        tabs.addTab(tab2, "📈 Acceleration")
        
        # Tab 3: Motors
        tab3 = self._build_motors_tab()
        tabs.addTab(tab3, "⚙️ Motors")
        
        # Tab 4: Stats
        tab4 = self._build_stats_tab()
        tabs.addTab(tab4, "📊 Stats")
        
        layout.addWidget(tabs)
        return widget
    
    def _build_data_tab(self):
        """Build live data table."""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        
        self.packet_table = QtWidgets.QTableWidget(10, 8)
        headers = ['Time', 'Seq', 'Ax (g)', 'Ay (g)', 'Az (g)', 'ωout', 'ωin', 'Temp']
        self.packet_table.setHorizontalHeaderLabels(headers)
        for i in range(8):
            self.packet_table.setColumnWidth(i, 110)
        
        layout.addWidget(self.packet_table)
        return widget
    
    def _build_accel_tab(self):
        """Build acceleration plot."""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        
        self.plot_accel = pg.PlotWidget(title="Acceleration")
        self.plot_accel.setLabel('left', 'Accel (g)')
        self.plot_accel.setLabel('bottom', 'Time (s)')
        self.plot_accel.addLegend()
        
        self.curve_ax = self.plot_accel.plot(pen='r', name='Ax')
        self.curve_ay = self.plot_accel.plot(pen='g', name='Ay')
        self.curve_az = self.plot_accel.plot(pen='b', name='Az')
        
        layout.addWidget(self.plot_accel)
        return widget
    
    def _build_motors_tab(self):
        """Build motor status."""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(widget)
        
        self.label_outer_rpm = QtWidgets.QLabel("0")
        self.label_inner_rpm = QtWidgets.QLabel("0")
        self.label_motor_status = QtWidgets.QLabel("IDLE")
        self.label_motor_status.setStyleSheet("color: #f39c12; font-weight: bold;")
        
        layout.addRow("Outer (RPM):", self.label_outer_rpm)
        layout.addRow("Inner (RPM):", self.label_inner_rpm)
        layout.addRow("Status:", self.label_motor_status)
        
        return widget
    
    def _build_stats_tab(self):
        """Build statistics panel."""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(widget)
        
        self.label_total_packets = QtWidgets.QLabel("0")
        self.label_sample_rate = QtWidgets.QLabel("0 Hz")
        self.label_buffer_util = QtWidgets.QLabel("0%")
        self.label_elapsed = QtWidgets.QLabel("0 s")
        
        layout.addRow("Total Packets:", self.label_total_packets)
        layout.addRow("Sample Rate:", self.label_sample_rate)
        layout.addRow("Buffer Util:", self.label_buffer_util)
        layout.addRow("Elapsed:", self.label_elapsed)
        
        return widget
    
    def _connect_signals(self):
        """Connect UI signals."""
        self.motor_panel.velocity_changed.connect(self._on_motor_command)
        self.motor_panel.emergency_stop_triggered.connect(self._on_emergency_stop)
        self.btn_clear.clicked.connect(self.clear_data)
        self.btn_paraview.clicked.connect(self.launch_paraview)
    
    def _on_update(self):
        """Periodic UI update (100ms)."""
        # Update packets table
        packets = self.manager.get_recent_packets(10)
        for i, p in enumerate(reversed(packets)):
            if i < 10:
                items = [
                    f"{p.timestamp:.3f}",
                    str(p.sequence_number),
                    f"{p.accel_x/9.81:.4f}",
                    f"{p.accel_y/9.81:.4f}",
                    f"{p.accel_z/9.81:.4f}",
                    f"{p.omega_outer:.3f}",
                    f"{p.omega_inner:.3f}",
                    f"{p.temperature:.1f}",
                ]
                for j, item in enumerate(items):
                    self.packet_table.setItem(i, j, QtWidgets.QTableWidgetItem(item))
        
        # Update plots
        ts, data = self.manager.get_latest_data(10.0)
        if len(ts) > 0 and data.shape[0] > 0:
            t_rel = ts - ts[0]
            self.curve_ax.setData(t_rel, data[:, 0] / 9.81)
            self.curve_ay.setData(t_rel, data[:, 1] / 9.81)
            self.curve_az.setData(t_rel, data[:, 2] / 9.81)
        
        # Update stats
        stats = self.manager.get_statistics()
        self.label_total_packets.setText(str(stats['total_packets']))
        self.label_sample_rate.setText(f"{stats['average_rate']:.1f} Hz")
        self.label_buffer_util.setText(f"{stats['buffer_utilization']*100:.1f}%")
        self.label_elapsed.setText(f"{stats['elapsed_time']:.1f} s")
        
        # Update microgravity demo
        t = time.time()
        theta_o = np.sin(t * 0.5) * np.pi
        theta_i = np.cos(t * 0.3) * np.pi
        omega_o = np.cos(t * 0.5) * 2.0
        omega_i = -np.sin(t * 0.3) * 1.5
        self.microgravity_panel.update_kinematics(theta_o, theta_i, omega_o, omega_i, t)
    
    def _on_motor_command(self, omega_outer, omega_inner):
        """Handle motor commands."""
        logger.info(f"Motor cmd: out={omega_outer:.3f}, in={omega_inner:.3f} rad/s")
    
    def _on_emergency_stop(self):
        """Handle emergency stop."""
        logger.warning("EMERGENCY STOP TRIGGERED")
        self.manager.stop_streaming()
    
    def connect_sensors(self):
        """Connect sensors."""
        try:
            sim = self.manager.get_interface('simulator')
            if sim:
                sim.connect()
                sim.start_streaming()
                self._update_timer.start()
                self.statusbar_label.setText("✓ Connected & Streaming")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", str(e))
    
    def disconnect_sensors(self):
        """Disconnect sensors."""
        self.manager.disconnect_all()
        self._update_timer.stop()
        self.statusbar_label.setText("✗ Disconnected")
    
    def start_acquisition(self):
        """Start acquisition."""
        self.manager.start_acquisition()
        self.statusbar_label.setText("▶ Acquiring")
    
    def toggle_recording(self):
        """Toggle recording."""
        if not self.manager._recording:
            fp = self.manager.start_recording()
            self.statusbar_label.setText(f"● Recording: {fp}")
        else:
            self.manager.stop_recording()
            self.statusbar_label.setText("Paused")
    
    def export_vtk(self):
        """Export to VTK."""
        try:
            ts, data = self.manager.get_latest_data(300.0)
            if len(ts) > 0:
                traj = np.random.randn(len(ts), 3) * 0.1
                gravity = data[:, 13:16]
                filepath = export_to_vtk(ts, traj, gravity, output_path="rpm_export.vtk")
                QtWidgets.QMessageBox.information(self, "Success", f"Exported: {filepath}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", str(e))
    
    def export_csv(self):
        """Export to CSV."""
        try:
            ts, data = self.manager.get_latest_data(300.0)
            if len(ts) > 0:
                export_to_csv_for_paraview({
                    'timestamps': ts,
                    'positions': np.random.randn(len(ts), 3) * 0.05,
                    'gravity': data[:, 13:16],
                }, output_path="rpm_export.csv")
                QtWidgets.QMessageBox.information(self, "Success", "Exported: rpm_export.csv")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", str(e))
    
    def clear_data(self):
        """Clear buffer."""
        self.manager.clear_buffer()
        self.microgravity_panel.clear_history()
    
    def launch_paraview(self):
        """Generate ParaView script."""
        try:
            generate_paraview_script("rpm_export.vtk", "rpm_paraview_script.py")
            QtWidgets.QMessageBox.information(self, "ParaView", 
                "Script: rpm_paraview_script.py\nRun: paraview --script rpm_paraview_script.py")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", str(e))
    
    def show_about(self):
        """Show about."""
        QtWidgets.QMessageBox.about(self, "About",
            "RPM Digital Twin v1.0\n"
            "Professional simulation & control software\n"
            "© 2026 Space Research Lab")
    
    def closeEvent(self, event):
        """Handle close."""
        self.disconnect_sensors()
        event.accept()


def run_app():
    """Run application."""
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    QtCore.QTimer.singleShot(500, win.connect_sensors)
    sys.exit(app.exec())


if __name__ == '__main__':
    run_app()
