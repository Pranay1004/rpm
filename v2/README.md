# IIST RPM Digital Twin — Architecture v2.0

**Indian Institute of Space Science and Technology (IIST)**  
**Department of Aerospace Engineering — Microgravity Simulation Laboratory**  
**Project Guide:** Dr. V S Sooraj  
**M.Tech Manufacturing Technology (Batch 2025–2027)**  
**Live Scientific Workbench:** [https://rpmiist.vercel.app](https://rpmiist.vercel.app)

---

## 1. Overview & Architectural Philosophy

Version 2.0 is a complete ground-up revamp engineered specifically to eliminate "AI slop", neon cyberpunk aesthetics, and arbitrary geometries. It replaces them with:
1. **Mechanical Design Conformance:** 1:1 scale parametric 3D assembly strictly matching [Final_Drawing.pdf](file:///Users/pandeyji/Desktop/IIST/Microgravity/RPM/Final_Drawing.pdf) (DWG No. 01, 02, 03).
2. **Scientific Laboratory Interface:** Clean light-neutral instrument aesthetic (`#f8fafc` / `#ffffff`) with crisp typography, dark slate accents, and standard engineering notation.
3. **Publication-Quality White-Background Plots:** Pure white-background vector graphs with standard axes lines and grid lines matching Figures 1B, 2B, 3B of [Microgravity_Simulation.pptx](file:///Users/pandeyji/Desktop/IIST/Microgravity/RPM/Microgravity_Simulation.pptx).
4. **Comprehensive RFC-4180 CSV Data Export:** One-click export of complete 50 Hz kinematic, volumetric, and fluid-shear time series with full metadata headers and SI units.
5. **Dual-Tier Engineering Deployment:**
   * **Desktop Native Workstation:** Python 3 + PyQt6 + Matplotlib + PySerial ([v2/desktop/rpm_workstation.py](file:///Users/pandeyji/Desktop/IIST/Microgravity/RPM/v2/desktop/rpm_workstation.py)) for physical hardware test benches.
   * **Scientific Web Workbench:** Three.js CAD + Chart.js ([v2/web/](file:///Users/pandeyji/Desktop/IIST/Microgravity/RPM/v2/web/)) deployed directly to Vercel.

---

## 2. Mechanical Design Specifications (Final_Drawing.pdf)

| Part | Component Name | Dimensions | Material / Specification |
| :--- | :--- | :--- | :--- |
| **1** | **Base Plate** | `1200 ± 5 × 900 ± 5 × 45 ± 1 mm` | IS2062 E250 Structural Steel |
| **2** | **Side Supports (2x)** | Inverted-V A-Frame, `H = 490.9 mm`, `T = 25.4 mm` (1 inch) | IS2062 E250 Structural Steel |
| **3** | **Payload Holder** | Outer `200 ± 1 × 200 ± 1 mm`, Cavity `120 × 120 mm` | Optical Polycarbonate (Transparent) |
| **4** | **Outer Shafts (2x)** | `Ø20 p6 mm × 151 ± 5 mm` | IS2062 E250 Ground Steel |
| **5** | **Outer Frame** | Outside `500 ± 1 × 500 ± 1 × 50.8 mm`, Profile `50 mm` | Al6061-T6 Aluminum Alloy |
| **6** | **Inner Frame** | Outside `350 ± 1 × 350 ± 1 × 50.8 mm`, Profile `45 mm` | Al6061-T6 Aluminum Alloy |
| **7** | **Inner Shafts (2x)** | `Ø20 p6 mm × 160 ± 0.05 mm` | IS2062 E250 Ground Steel |
| **8** | **Bearings (4x)** | Flanged Pillow Block Ball Bearings (`Ø20 H7`) | Sealed Industrial Bearing Steel |
| **9** | **Payload Support (2x)**| `Ø10 p6 mm × 350 ± 0.5 mm` Dual Mounting Rods | Precision Stainless Steel |
| — | **Outer Motor** | NEMA 34 Stepper (`86 × 86 mm`, `I_zz = 0.614 kg·m²`) | Slide 11 & 13 of Presentation |
| — | **Inner Motor** | NEMA 23 Stepper (`57 × 57 mm`, `I_yy = 0.172 kg·m²`) | Slide 11 & 13 of Presentation |
| — | **Slip Rings (2x)** | Multi-channel Continuous Rotation Slip Rings | Slide 13 of Presentation |

---

## 3. Directory Structure

```
v2/
├── desktop/
│   ├── main.py                  # Desktop application launcher
│   ├── rpm_workstation.py       # PyQt6 scientific workbench with Matplotlib
│   └── data_exporter.py         # RFC-4180 CSV & 300 DPI plot exporter
├── simulation/
│   ├── kinematics.py            # Yotov et al. (2022) gimbal transformations
│   ├── volumetric_field.py      # Wadhwa et al. (2026) spatial acceleration & r_safe
│   ├── fdm_fluid_solver.py      # Hasenstein & van Loon (2015) 1D Navier-Stokes FDM
│   └── trajectory_modes.py      # Clinostat Optimal, 3D, and Stochastic Mode A
├── web/
│   ├── index.html               # Clean laboratory UI without AI clutter
│   ├── app.js                   # 50 Hz physics controller & CSV download
│   ├── cad_model.js             # 3D Three.js model matching Final_Drawing.pdf
│   └── style.css                # Professional laboratory CSS
├── tests/
│   └── test_physics.py          # Pytest verification suite (100% passing)
└── README.md                    # This document
```

---

## 4. How to Run

### A. Desktop Workstation (PyQt6 + Matplotlib)
```bash
cd /Users/pandeyji/Desktop/IIST/Microgravity/RPM
/Users/pandeyji/py314env/bin/python3 v2/desktop/main.py
```

### B. Scientific Web Workbench (Local & Cloud)
* **Live Vercel Deployment:** [https://rpmiist.vercel.app](https://rpmiist.vercel.app)
* **Local Python HTTP Server:**
  ```bash
  cd /Users/pandeyji/Desktop/IIST/Microgravity/RPM/v2/web
  python3 -m http.server 8080
  ```
