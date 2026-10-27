# Mathematical Formulations & Digital Twin Architecture

**Indian Institute of Space Science and Technology (IIST)**  
**Department of Aerospace Engineering — Microgravity Simulation Laboratory**  
**Digital Twin Architecture for Random Positioning Machine (RPM)**  
**Live Portal:** [https://rpm.iist.vercel.app](https://rpm.iist.vercel.app)

---

## 1. Kinematics of Dual-Gimbal RPM

The Random Positioning Machine consists of two independently driven, concentric orthogonal gimbals:
- **Outer Gimbal (Pitch/Yaw):** Rotates about the laboratory Y-axis with angle `ψ(t)` and angular speed `ω_ψ = dψ/dt`.
- **Inner Gimbal (Roll/Pitch):** Rotates about the inner gimbal Z-axis with angle `φ(t)` and angular speed `ω_φ = dφ/dt`.

### Coordinate Transformation
Following Yotov et al. (2022), the laboratory coordinate frame is denoted by `(X_0, Y_0, Z_0)` with the static gravity vector pointing downwards along the negative Z-axis:  
`g_lab = [0, 0, -g₀]ᵀ`, where `g₀ = 9.80665 m/s²`.

The total rotation matrix from the laboratory frame to the inner gimbal frame `(x, y, z)` is given by:  
`R(ψ, φ) = R_Z(φ) · R_Y(ψ)`

Evaluating the matrix product:
```
R_Y(ψ) = [  cos(ψ)   0   sin(ψ) ]
         [    0      1     0    ]
         [ -sin(ψ)   0   cos(ψ) ]

R_Z(φ) = [  cos(φ)  sin(φ)   0  ]
         [ -sin(φ)  cos(φ)   0  ]
         [    0       0      1  ]
```

Multiplying by `[0, 0, 1]ᵀ` gives the effective gravity unit vector `ē_g(t)` experienced inside the sample payload:
```
ē_g(t) = -sin(φ) · cos(ψ) ē_x + sin(φ) · sin(ψ) ē_y + cos(φ) ē_z
```

### Time-Averaged Simulated Microgravity (taSMG)
Simulated microgravity is quantified by the vector time-integral over duration `T`:
```
<g>(T) = || (1/T) ∫₀ᵀ ē_g(t) dt ||
```
When `<g>(T) → 0`, the omnidirectional net gravitational force vector cancels out across biological mechanosensitive response intervals (typically `T > 20 s`).

---

## 2. Volumetric Spatial Acceleration Field

As established by Wadhwa et al. (Scientific Reports 2026), true physical microgravity is only attained at the exact geometric center `r = 0`. At any off-center point `r = [x, y, z]ᵀ` in the sample payload volume, rotational accelerations introduce residual forces.

### Total Spatial Acceleration
The acceleration field is governed by Equation (5) of Wadhwa et al. (2026):
```
a_total(r, t) = g(t) - ω(t) × (ω(t) × r) - α(t) × r
```
Where:
- `g(t) = g₀ · ē_g(t)` is the orientation-dependent gravity vector.
- `a_cent(r, t) = -ω(t) × (ω(t) × r)` is the centrifugal acceleration.
- `a_euler(r, t) = -α(t) × r` is the Euler tangential acceleration, with `α(t) = dω/dt`.

### Centrifugal Bias and Safe Radius Threshold
The centrifugal acceleration magnitude depends quadratically on angular velocity:
```
||a_cent(r)|| = ||ω||² · r
```
For simulated microgravity to remain biologically valid without exceeding the standard international threshold `a_residual < 10⁻³ g₀` (1 milli-g):
```
r_safe = (10⁻³ · g₀) / ||ω||²
```
For typical operating speeds of `2.0 RPM` (`0.2094 rad/s`):
```
||ω||² = (0.2094)² = 0.04387 rad²/s²
r_safe = (0.001 · 9.80665) / 0.04387 = 0.2235 m = 22.35 cm
```
At `r = 5.0 cm` (standard Petri dish or flask radius), the centrifugal acceleration is:
```
||a_cent|| = 0.04387 · 0.05 = 0.00219 m/s² = 0.000223 g₀ = 0.22 milli-g
```
This confirms that the chamber operates strictly within the acceptable microgravity regime.

---

## 3. Ergodic S² Sphere Coverage & Pole Avoidance

Kim et al. (npj Microgravity 2026) demonstrated that standard clinostats with integer velocity ratios `γ = ω_φ / ω_ψ = 1` or `2` trap the gravity vector in fixed latitude orbits, causing severe accumulation at the poles:
- **Integer Ratio Trap:** The trajectory forms a closed 1D Lissajous curve on S². The integral does not average to zero across all axes, leading to uncancelled DC gravity components.
- **Optimal Non-Harmonic Ratio:**
```
γ_opt = 1.146
```
With `ω_φ = 2.000 RPM` and `ω_ψ = 2.292 RPM`, the trajectory is quasi-periodic and ergodic, densely filling the 2-sphere `S²` without closed orbits, eliminating directional gravity bias.

---

## 4. Mode A Stochastic Zero-Crossing Reversal

Pica et al. (PLOS ONE 2026) demonstrated that continuous unidirectional rotation causes cumulative fluid shear vorticity and unidirectional angular momentum drift.

The Digital Twin implements Mode A stochastic direction reversals:
- Switching interval: `T_switch ∈ [20.0, 45.0] seconds`
- Randomized angular velocity: `ω_target ∈ [0.80, 1.00] · ω_max · sign(random)`
- Motor torque ramp constraint: `|dω/dt| ≤ 1.5 RPM/s²`

This profile eliminates steady-state fluid vortex formation and continuously tests cellular mechanosensation.

---

## 5. 1D Navier-Stokes Fluid Shear Stress (FDM Solver)

Following Hasenstein & van Loon (River Publishers 2015), the fluid shear stress inside the sample container is governed by the 1D unsteady Navier-Stokes equation in cylindrical coordinates `(r, θ)`:

```
∂u_θ/∂t = ν · [ ∂²u_θ/∂r² + (1/r) · (∂u_θ/∂r) - u_θ/r² ]
```
Where:
- `u_θ(r, t)` is the azimuthal fluid velocity at radius `r` and time `t`.
- `ν = μ / ρ` is the kinematic viscosity (for water at 20°C: `ν = 1.004 × 10⁻⁶ m²/s`).
- `μ` is the dynamic viscosity (`1.002 × 10⁻³ Pa·s`).
- `ρ` is the fluid density (`998.2 kg/m³`).

### Numerical Discretization (50 Hz Finite Difference Method)
The cylindrical domain `r ∈ [0, R]` is discretized into `N = 25` radial nodes:
- Grid spacing: `Δr = R / (N - 1)`
- Time step: `Δt = 0.02 s` (50 Hz)

Using central difference approximations for spatial derivatives:
```
∂²u/∂r² ≈ (u_{i+1} - 2u_i + u_{i-1}) / (Δr)²
∂u/∂r   ≈ (u_{i+1} - u_{i-1}) / (2Δr)
```

The updated velocity field at interior nodes `i = 1, ..., N-2` is:
```
u_i^{n+1} = u_i^n + Δt · ν · [ (u_{i+1}^n - 2u_i^n + u_{i-1}^n)/(Δr)² + (1/r_i) · (u_{i+1}^n - u_{i-1}^n)/(2Δr) - u_i^n / r_i² ]
```

### Boundary Conditions
1. **Centerline Symmetry / No Slip:**  
   `u_0^{n+1} = 0` (zero velocity at cylinder axis).
2. **Container Wall Drive:**  
   `u_{N-1}^{n+1} = ||ω|| · R` (fluid matches container wall speed).

### Dynamic Wall Shear Stress
The shear stress at the inner vessel wall is computed dynamically:
```
τ_w = μ · | (∂u_θ/∂r) - (u_θ / r) |_{r=R}
```
In discrete form:
```
τ_w = μ · | (u_{N-1} - u_{N-2}) / Δr - u_{N-1} / R | · 1000  (expressed in mPa)
```

### Stokes Boundary Layer
The oscillatory Stokes boundary layer thickness is given by:
```
δ = √(2ν / ||ω||)
```
For `||ω|| = 0.2094 rad/s`:
```
δ = √(2 · 1.004 × 10⁻⁶ / 0.2094) = 0.00309 m = 3.09 mm
```
This indicates that high shear stresses are strictly confined to a narrow 3.1 mm zone adjacent to the container wall.

---

## 6. Digital Twin Telemetry & Discrepancy Formulation

A true Digital Twin continuously calculates the discrepancy residual between the analytical simulation model and real physical hardware telemetry:
```
e_discrepancy(t) = || a_IMU(t) - a_sim(t) ||
```
Where:
- `a_IMU(t)` is measured acceleration streamed over USB Web Serial (115200 baud) or WiFi UDP/WebSocket from the onboard 6-axis IMU (e.g. MPU6050 / ICM-20948).
- `a_sim(t)` is the instantaneous kinematic simulation vector.

When `e_discrepancy < 0.05 g`, the physical twin and mathematical model are declared in verified state synchronization.
