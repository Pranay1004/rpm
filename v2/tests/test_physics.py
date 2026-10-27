"""
Unit tests for v2 scientific physics and kinematics engine.
"""

import sys
import os
import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from simulation.kinematics import RPMKinematics
from simulation.volumetric_field import VolumetricFieldSolver
from simulation.fdm_fluid_solver import FluidShearStressFDMSolver
from simulation.trajectory_modes import TrajectoryController, TrajectoryMode


def test_gravity_unit_norm():
    """Verify that projected gravity vector always has norm 1.0."""
    kinematics = RPMKinematics()
    for phi in [0.0, 45.0, 90.0, 180.0, 270.0]:
        for psi in [0.0, 30.0, 60.0, 120.0, 315.0]:
            e_g = kinematics.compute_gravity_projection(phi, psi)
            norm = np.linalg.norm(e_g)
            assert np.isclose(norm, 1.0, atol=1e-6), f"Norm failed at phi={phi}, psi={psi}: {norm}"


def test_tasmg_convergence():
    """Verify that time-averaging drives taSMG downwards."""
    kinematics = RPMKinematics()
    dt = 0.02
    phi = 0.0
    psi = 0.0
    # Run 500 steps at 2 RPM
    for _ in range(500):
        phi = (phi + 2.0 * 6.0 * dt) % 360.0
        psi = (psi + 2.292 * 6.0 * dt) % 360.0
        state = kinematics.step(dt, phi, psi, 2.0, 2.292)
    assert kinematics.samples == 500
    assert state.taSMG < 1.0, f"taSMG should decrease, got {state.taSMG}"


def test_volumetric_centrifugal_accel():
    """Verify Wadhwa et al. (2026) centrifugal acceleration: ||omega||^2 * r."""
    solver = VolumetricFieldSolver(default_chamber_radius_m=0.05)
    # At 2 RPM inner & 0 RPM outer: omega = 2 * 2*pi / 60 ~ 0.20944 rad/s
    # ||a_cent|| = omega^2 * r = 0.20944^2 * 0.05 = 0.002193 m/s^2 = 0.0002237 g
    a_cent_g, _, r_safe_cm, _ = solver.compute_field(
        g_payload_unit=np.array([0, 0, 1.0]),
        omega_phi_rpm=2.0,
        omega_psi_rpm=0.0
    )
    expected_g = (0.20944**2 * 0.05) / 9.80665
    assert np.isclose(a_cent_g, expected_g, atol=1e-5)
    # Safe radius r_safe for 2 RPM:
    # r_safe = (10^-3 * 9.80665) / (0.20944^2) = 0.22356 m = 22.36 cm
    assert np.isclose(r_safe_cm, 22.36, atol=0.2)


def test_fdm_fluid_shear():
    """Verify Hasenstein & van Loon FDM solver advances stably and produces non-negative shear stress."""
    solver = FluidShearStressFDMSolver(radius_m=0.05, num_radial_nodes=25)
    dt = 0.02
    omega = 0.20944
    for _ in range(100):
        tau = solver.step(dt, omega)
    assert tau >= 0.0
    assert solver.stokes_boundary_layer_mm > 0.0
    assert np.all(solver.u_theta >= 0.0)


def test_trajectory_optimal_mode():
    """Verify Kim et al. optimal ratio gamma = 1.146."""
    controller = TrajectoryController(default_mode=TrajectoryMode.CLINOSTAT_OPTIMAL, base_inner_rpm=2.0)
    assert np.isclose(controller.target_omega_psi_rpm / controller.target_omega_phi_rpm, 1.146, atol=1e-3)
