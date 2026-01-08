"""Microgravity analysis utilities.

Provides functions to compute gravity vector in the payload frame,
centripetal acceleration at a point, and simple numerical metrics
used by the Digital Twin.
"""
from __future__ import annotations

import numpy as np
from typing import Tuple


def rotation_z(theta: float) -> np.ndarray:
    c = np.cos(theta)
    s = np.sin(theta)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def rotation_y(theta: float) -> np.ndarray:
    c = np.cos(theta)
    s = np.sin(theta)
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])


def gravity_in_payload_frame(theta_outer: float, theta_inner: float, g: float = 9.81) -> np.ndarray:
    """Return gravity vector components in the payload (inner) frame.

    theta_outer: rotation of outer frame about Z (rad)
    theta_inner: rotation of inner frame about Y (rad)

    The convention matches the MATLAB reference code: R_total = R_outer * R_inner
    and g_payload = R_total.T * g_inertial (where g_inertial = [0; -g; 0]).
    """
    Rz = rotation_z(theta_outer)
    Ry = rotation_y(theta_inner)
    R_total = Rz @ Ry
    g_inertial = np.array([0.0, -g, 0.0])
    return R_total.T @ g_inertial


def centripetal_acceleration_at_point(
    w_outer: float,
    w_inner: float,
    theta_outer: float,
    theta_inner: float,
    r_payload: np.ndarray,
) -> np.ndarray:
    """Compute centripetal acceleration vector at a point expressed in payload frame.

    w_outer, w_inner: angular velocities in rad/s for outer (about Z) and inner (about Y)
    theta_outer, theta_inner: current angles (rad)
    r_payload: 3-vector position of the sample in payload-local coordinates (meters)

    Uses the expression a_c = - w_p x (w_p x r) where w_p is angular velocity in payload frame.
    """
    # Angular velocities in inertial frame
    w1_i = np.array([0.0, 0.0, w_outer])
    w2_i = rotation_z(theta_outer) @ np.array([0.0, w_inner, 0.0])
    w_i = w1_i + w2_i

    # Total rotation matrix payload->inertial
    R_total = rotation_z(theta_outer) @ rotation_y(theta_inner)
    # Angular velocity in payload frame
    w_p = R_total.T @ w_i

    # compute centripetal acceleration (note negative sign for inward)
    return -np.cross(w_p, np.cross(w_p, r_payload))


def taSMG_metric(gravity_vectors: np.ndarray) -> float:
    """Compute a simple time-averaged scalar microgravity metric (taSMG).

    gravity_vectors: array shape (N,3) containing instantaneous gravity vectors (m/s^2)
    returns RMS of |g| normalized by 9.81 (unitless g)
    """
    mags = np.linalg.norm(gravity_vectors, axis=1)
    return np.sqrt(np.mean(mags ** 2)) / 9.81


def sample_point_compare(
    timestamps: np.ndarray,
    gravity_time_series: np.ndarray,
    point_r: np.ndarray,
) -> dict:
    """Given a time series of gravity vectors in payload frame and a spatial point,
    return summarized microgravity metrics for that point.
    This is a placeholder for more advanced spatial interpolation.
    """
    # For now, we assume gravity_time_series are gravity at the origin; centripetal
    # contributions must be added externally if needed. Return RMS and mean.
    mags = np.linalg.norm(gravity_time_series, axis=1)
    return {
        'samples': int(len(mags)),
        'g_rms': float(np.sqrt(np.mean(mags**2))),
        'g_mean': float(np.mean(mags)),
        'g_rms_g': float(np.sqrt(np.mean(mags**2)) / 9.81),
    }
