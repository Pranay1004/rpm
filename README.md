# IIST Random Positioning Machine (RPM) Digital Twin

[![Vercel Deployment](https://img.shields.io/badge/Vercel-Deployed-00e5ff?style=for-the-badge&logo=vercel&logoColor=white)](https://rpmiist.vercel.app)
[![License: Academic](https://img.shields.io/badge/License-IIST_Academic-bf5af2?style=for-the-badge)](https://github.com/Pranay1004/rpm)
[![Physics: 50Hz Real--Time FDM](https://img.shields.io/badge/Physics-50Hz_FDM_Diffusion-00ff9d?style=for-the-badge)](file:///Users/pandeyji/Desktop/IIST/Microgravity/RPM/CITATIONS.md)
[![Web Serial API](https://img.shields.io/badge/Hardware-Web_Serial_Sync-ffd60a?style=for-the-badge)](file:///Users/pandeyji/Desktop/IIST/Microgravity/RPM/index.html)

**Indian Institute of Space Science and Technology (IIST)**  
**Department of Aerospace Engineering — Microgravity Simulation Laboratory**  
**Live Digital Twin Web Application:** [https://rpmiist.vercel.app](https://rpmiist.vercel.app)  
**Vercel Project:** [https://vercel.com/pranays-projects-d8ef7548/rpm.iist/2hG5mKW31BneqpxmRhQ258ipqvf9](https://vercel.com/pranays-projects-d8ef7548/rpm.iist/2hG5mKW31BneqpxmRhQ258ipqvf9)  
**Source Repository:** [https://github.com/Pranay1004/rpm](https://github.com/Pranay1004/rpm)

---

## 1. Overview & Aim: The True Digital Twin

A true **Digital Twin** is not merely a 3D animation; it is an active bi-directional cyber-physical system combining:
1. **Kinematic & Mathematical Simulation:** Real-time 50 Hz physics engine modeling multi-axis gimbal rotations, gravity vector projections, volumetric centrifugal acceleration gradients, and Navier-Stokes fluid momentum diffusion.
2. **Physical Hardware Synchronization:** Live telemetry synchronization with physical microcontrollers, stepper motor encoders, and 6-DOF IMU sensors via direct browser Web Serial (USB) and FastAPI WebSockets.
3. **Discrepancy Residual Computation:** Real-time state verification evaluating `e_residual = ||a_IMU(t) - a_sim(t)||` to detect mechanical slip, vibration, or sensor bias.
4. **Peer-Reviewed Scientific Rigor:** Complete adherence to published microgravity research literature.

---

## 2. Peer-Reviewed Academic Citations & Formulations

The digital twin algorithms directly implement equations from primary literature:

| Research Paper | Formulation & Contribution | Implemented Equation |
| :--- | :--- | :--- |
| **Wadhwa et al.**<br>*Scientific Reports* 16, 39316 (2026)<br>Harvard-MIT HST / UC San Diego<br>DOI: [10.1038/s41598-026-39316-7](https://doi.org/10.1038/s41598-026-39316-7) | **Volumetric Spatial Field & Safe Radius:** Disproved uniform microgravity across sample volumes; derived centrifugal bias gradient and critical safe payload radius. | `a(r, t) = g(t) - ω × (ω × r) - α × r`<br>`r_safe = (10⁻³ · g₀) / \|\|ω\|\|²` |
| **Kim, Park, & Kim**<br>*npj Microgravity* 12, 570 (2026)<br>Nature Portfolio / NASA<br>DOI: [10.1038/s41526-026-00570-8](https://doi.org/10.1038/s41526-026-00570-8) | **S² Ergodic Coverage & Pole-Avoidance:** Proved integer speed ratios trap gravity vectors in closed orbits; identified optimal non-harmonic velocity ratio `γ = 1.146`. | `γ = ω_φ / ω_ψ = 1.146`<br>(e.g. Inner = 2.0 RPM, Outer = 2.292 RPM) |
| **Pica et al.**<br>*PLOS ONE* 21(6), e0351320 (2026)<br>Univ of Sassari<br>DOI: [10.1371/journal.pone.0351320](https://doi.org/10.1371/journal.pone.0351320) | **Mode A Stochastic Zero-Crossing:** Reverses rotation directions periodically to cancel cumulative angular momentum drift and fluid vortex circulation. | `T_switch ∈ [20, 45] s`<br>`ω ∈ [0.80, 1.00] · ω_max · sign(random)` |
| **Yotov et al.**<br>*Inventions* 7(3), 85 (2022)<br>Sofia University<br>DOI: [10.3390/inventions7030085](https://doi.org/10.3390/inventions7030085) | **Gimbal Rotation Matrices & taSMG:** Rotational transformation equations projecting Earth gravity into rotating sample payload coordinates. | `ē_g(t) = -sin(φ)cos(ψ)ē_x + sin(φ)sin(ψ)ē_y + cos(φ)ē_z`<br>`taSMG = \|\| (1/T) ∫₀ᵀ ē_g(t) dt \|\|` |
| **Hasenstein & van Loon**<br>*River Publishers* pp. 147–160 (2015)<br>Univ of Louisiana / DESC<br>ISBN: 978-87-93237-54-4 | **1D Navier-Stokes Fluid Shear Stress:** Finite Difference Method (FDM) modeling viscous momentum diffusion in culture vessels and dynamic wall shear stress. | `∂u_θ/∂t = ν · [ ∂²u_θ/∂r² + (1/r)(∂u_θ/∂r) - u_θ/r² ]`<br>`τ_w = μ · \|∂u_θ/∂r - u_θ/r\|_{r=R}` |

For BibTeX entries and full mathematical derivations, see [CITATIONS.md](file:///Users/pandeyji/Desktop/IIST/Microgravity/RPM/CITATIONS.md) and [REFERENCES.md](file:///Users/pandeyji/Desktop/IIST/Microgravity/RPM/REFERENCES.md).

---

## 3. Architecture & Operational Modes

```
+---------------------------------------------------------------------------+
|                          IIST RPM DIGITAL TWIN                            |
+---------------------------------------------------------------------------+
            |                                           |
            v                                           v
+-------------------------------+           +-------------------------------+
|     CLOUD RUNTIME (VERCEL)    |           |    LOCAL PHYSICAL WORKBENCH   |
|   https://rpmiist.vercel.app |           |     Python 3 + Hardware Rig   |
+-------------------------------+           +-------------------------------+
| • In-Browser 50 Hz Physics    |           | • FastAPI Asynchronous Server |
| • 1D Navier-Stokes FDM Solver |           | • Real-Time FDM Fluid Solver  |
| • Three.js 3D Gimbal Render   |           | • Serial / UDP / WebSocket    |
| • S² Spherical Ergodicity     |           | • Hardware Discrepancy Filter |
| • Web Serial USB Direct Sync  |           | • Port: localhost:8080        |
+-------------------------------+           +-------------------------------+
            |                                           |
            +---------------------+---------------------+
                                  |
                                  v
+---------------------------------------------------------------------------+
|                          PHYSICAL HARDWARE RIG                            |
| • Concentric Gimbal Frame (Outer: 150 cm, Inner: 80 cm)                   |
| • Dual NEMA 23 Stepper Motors + Closed-Loop Encoders                     |
| • Microcontroller (ESP32 / Arduino / Teensy 4.1)                          |
| • 6-DOF IMU (MPU-6050 / ICM-20948) mounted on Sample Chamber               |
+---------------------------------------------------------------------------+
```

### Operation Modes
1. **Clinostat 3D:** Constant speed rotation (`2.0 / 2.0 RPM`) for basic demonstration.
2. **Clinostat Optimal (Kim et al. 2026):** Non-harmonic irrational velocity ratio (`γ = 1.146`) ensuring uniform S² coverage and preventing polar clustering.
3. **Stochastic RPM Mode A (Pica et al. 2026):** Stochastic zero-crossings every `20–45 s` with randomized velocities in `[0.80, 1.00] · ω_max` to cancel angular momentum bias.

---

## 4. Quick Start & Execution

### Option A: Cloud Web Application (Zero Installation)
Visit the live deployment directly in any modern browser:
[https://rpmiist.vercel.app](https://rpmiist.vercel.app)

* Click **`🔌 Connect HW (WebSerial)`** to link your physical microcontroller over USB.
* Click **`📚 Citations & Equations`** to inspect the mathematical provenance modal.

### Option B: Local Python Development Server
```bash
# Clone the repository
git clone https://github.com/Pranay1004/rpm.git
cd rpm

# Install dependencies
pip install -r programming/Digital_Twin/requirements.txt

# Launch FastAPI Digital Twin server
cd programming/Digital_Twin
python src/main.py --mode hybrid
```
Open [http://localhost:8080](http://localhost:8080) in your browser.

---

## 5. Repository Structure

```
├── CITATIONS.md              # Complete BibTeX and peer-reviewed citations
├── REFERENCES.md             # Detailed mathematical proofs and FDM equations
├── README.md                 # Project documentation and guide
├── index.html                # Vercel deployment root entrypoint (Three.js + FDM engine)
├── vercel.json               # Vercel deployment routes and security headers
├── LITERATURE/               # Peer-reviewed research papers (PDFs)
├── Matlab/                   # MATLAB simulation models and analytical scripts
├── Model/                    # CAD models and mechanical drawings
└── programming/
    └── Digital_Twin/
        ├── src/
        │   ├── simulation/
        │   │   ├── physics_engine.py  # RPMSimulator + RealTimeFluidFDMSolver
        │   │   ├── kinematics.py      # Gimbal coordinate transformations
        │   │   └── trajectory.py      # Random walk and ergodic algorithms
        │   ├── webapp/
        │   │   ├── server.py          # FastAPI WebSocket backend
        │   │   └── static/
        │   │       └── index.html     # Web application frontend
        │   └── main.py                # Local execution entrypoint
        └── requirements.txt           # Python dependencies
```

---

## 6. Institutional Attribution

**Indian Institute of Space Science and Technology (IIST)**  
Department of Aerospace Engineering  
Valiamala, Thiruvananthapuram, Kerala 695547, India  

Lead Developer: Pranay ([@Pranay1004](https://github.com/Pranay1004))  
Platform URL: [https://rpmiist.vercel.app](https://rpmiist.vercel.app)
