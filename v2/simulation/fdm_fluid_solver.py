"""
Real-Time 1D Navier-Stokes Cylindrical Finite Difference Method (FDM) Fluid Solver.
Based on Hasenstein & van Loon (River Publishers 2015, ISBN: 978-87-93237-54-4).
"""

import numpy as np


class FluidShearStressFDMSolver:
    """
    Solves unsteady viscous momentum diffusion in rotating culture vessels:
    ∂u_θ/∂t = ν · [ ∂²u_θ/∂r² + (1/r)·(∂u_θ/∂r) - u_θ/r² ]
    Evaluates dynamic wall shear stress:
    τ_w = μ · |∂u_θ/∂r - u_θ/r|_{r=R} (mPa)
    """

    def __init__(
        self,
        radius_m: float = 0.06,
        num_radial_nodes: int = 30,
        dynamic_viscosity_pa_s: float = 1.002e-3,  # Water at 20°C
        density_kg_m3: float = 998.2                # Water density
    ):
        self.R = radius_m
        self.N = max(15, num_radial_nodes)
        self.mu = dynamic_viscosity_pa_s
        self.rho = density_kg_m3
        self.nu = self.mu / self.rho               # Kinematic viscosity ~ 1.004e-6 m^2/s

        self.r_nodes = np.linspace(0.0, self.R, self.N, dtype=np.float64)
        self.dr = self.R / (self.N - 1)
        self.u_theta = np.zeros(self.N, dtype=np.float64)
        self.current_shear_stress_mPa = 0.0
        self.stokes_boundary_layer_mm = 0.0

    def reset(self, new_radius_m: float = None):
        if new_radius_m is not None:
            self.R = max(0.005, min(0.20, new_radius_m))
            self.r_nodes = np.linspace(0.0, self.R, self.N, dtype=np.float64)
            self.dr = self.R / (self.N - 1)
        self.u_theta.fill(0.0)
        self.current_shear_stress_mPa = 0.0
        self.stokes_boundary_layer_mm = 0.0

    def step(self, dt: float, omega_norm_rad_s: float) -> float:
        """
        Advances the 1D momentum diffusion equation forward by dt.
        Returns: dynamic wall shear stress tau_w in mPa.
        """
        # Stokes boundary layer thickness delta = sqrt(2 * nu / ||omega||)
        if omega_norm_rad_s > 1e-4:
            delta_m = np.sqrt(2.0 * self.nu / omega_norm_rad_s)
            self.stokes_boundary_layer_mm = float(delta_m * 1000.0)
        else:
            self.stokes_boundary_layer_mm = float(self.R * 1000.0)

        # Wall velocity boundary condition u(R) = omega * R
        u_wall = omega_norm_rad_s * self.R

        # Explicit finite difference step
        u_new = np.zeros_like(self.u_theta)
        dr2 = self.dr * self.dr

        for i in range(1, self.N - 1):
            r_i = self.r_nodes[i]
            d2u = (self.u_theta[i + 1] - 2.0 * self.u_theta[i] + self.u_theta[i - 1]) / dr2
            du = (self.u_theta[i + 1] - self.u_theta[i - 1]) / (2.0 * self.dr)
            diff_term = d2u + (1.0 / r_i) * du - (self.u_theta[i] / (r_i * r_i))
            u_new[i] = self.u_theta[i] + dt * self.nu * diff_term

        # Boundary conditions
        u_new[0] = 0.0          # Axisymmetry at r = 0
        u_new[-1] = u_wall      # Wall no-slip condition

        self.u_theta = u_new

        # Dynamic shear stress at the vessel wall:
        # tau_w = mu * |du_theta/dr - u_theta/r|_{r=R}
        du_dr_wall = (self.u_theta[-1] - self.u_theta[-2]) / self.dr
        shear_rate_wall = abs(du_dr_wall - (self.u_theta[-1] / self.R))
        tau_w_Pa = self.mu * shear_rate_wall
        self.current_shear_stress_mPa = float(tau_w_Pa * 1000.0)

        return self.current_shear_stress_mPa
