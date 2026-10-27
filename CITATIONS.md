# Academic Citations and Theoretical Provenance

**Indian Institute of Space Science and Technology (IIST)**  
**Department of Aerospace Engineering — Microgravity Simulation Laboratory**  
**Digital Twin Architecture for Random Positioning Machine (RPM)**  
**Live Portal:** [https://rpmiist.vercel.app](https://rpmiist.vercel.app)  
**Source Repository:** [https://github.com/Pranay1004/rpm](https://github.com/Pranay1004/rpm)

---

## 1. Primary Peer-Reviewed References

This Digital Twin implements mathematical formulations, kinematic algorithms, and fluid-dynamic shear stress models derived directly from the primary microgravity and spaceflight literature. Every equation implemented in [physics_engine.py](file:///Users/pandeyji/Desktop/IIST/Microgravity/RPM/programming/Digital_Twin/src/simulation/physics_engine.py), [server.py](file:///Users/pandeyji/Desktop/IIST/Microgravity/RPM/programming/Digital_Twin/src/webapp/server.py), and [index.html](file:///Users/pandeyji/Desktop/IIST/Microgravity/RPM/index.html) maps to the peer-reviewed sources below.

### [1] Wadhwa et al. (Scientific Reports, Nature Portfolio, 2026)
* **Title:** *Guidelines for use of the random positioning machine as a reduced-gravity analog*
* **Authors:** Anna Wadhwa, Lasse Bruun, Johan C. G. Petersen, Lonnie G. Petersen
* **Journal:** *Scientific Reports* (Nature Portfolio), Volume 16, Article 39316, 2026.
* **Affiliations:** Harvard-MIT Division of Health Sciences and Technology (HST), Massachusetts Institute of Technology, Cambridge, MA, USA; Department of Orthopaedic Surgery, University of California San Diego, La Jolla, CA, USA.
* **DOI:** [10.1038/s41598-026-39316-7](https://doi.org/10.1038/s41598-026-39316-7)
* **Exact Implemented Formulation (Equation 5):**
  * Volumetric 3D Acceleration Field:  
    `a_total(r, t) = g(t) - ω(t) × (ω(t) × r) - α(t) × r`
  * Centrifugal Acceleration Bias:  
    `a_cent(r, t) = -ω(t) × (ω(t) × r)`  
    Magnitude: `||a_cent(r)|| = ||ω||² · r`
  * Euler Acceleration:  
    `a_euler(r, t) = α(t) × r = (dω/dt) × r`
  * Critical Sample Radius Safe Threshold (for residual centrifugal bias < 10⁻³ g₀):  
    `r_safe = (10⁻³ · g₀) / ||ω||²`
* **Implementation Location in Code:**
  * Backend: [RPMSimulator.get_spatial_acceleration](file:///Users/pandeyji/Desktop/IIST/Microgravity/RPM/programming/Digital_Twin/src/simulation/physics_engine.py#L380-L420)
  * In-Browser Engine: [BrowserDigitalTwinEngine.step](file:///Users/pandeyji/Desktop/IIST/Microgravity/RPM/index.html#L2890-L2930)

### [2] Kim, Park, & Kim (npj Microgravity, Nature Portfolio / NASA, 2026)
* **Title:** *Comparison of clinostat control strategies to achieve simulated microgravity with uniform gravity vector distribution*
* **Authors:** S. Y. Kim, J. H. Park, C. H. Kim
* **Journal:** *npj Microgravity* (Nature Portfolio / NASA-supported), Volume 12, Article 570, 2026.
* **Affiliations:** Division of Mechanical Engineering, School of Mechanical & Aerospace Engineering, Seoul National University, Seoul, Republic of Korea.
* **DOI:** [10.1038/s41526-026-00570-8](https://doi.org/10.1038/s41526-026-00570-8)
* **Exact Implemented Formulation:**
  * Velocity Ratio Parameter:  
    `γ = ω_φ / ω_ψ`
  * Optimal Irrational Ratio for S² Spherical Ergodicity:  
    `γ_opt = 1.146` (e.g., Inner Gimbal = 2.000 RPM, Outer Gimbal = 2.292 RPM)
  * Analytical Proof: Harmonic integer ratios (1:1, 1:2, 2:1) trap the gravity vector into closed 1D periodic orbits with extreme polar clustering, whereas the irrational ratio `γ = 1.146` produces uniform ergodic coverage of the unit sphere S², preventing directional mechanosensitive bias in cell cultures.
* **Implementation Location in Code:**
  * Mode Selection: `clinostat_optimal` in [server.py](file:///Users/pandeyji/Desktop/IIST/Microgravity/RPM/programming/Digital_Twin/src/webapp/server.py#L75-L105) and [index.html](file:///Users/pandeyji/Desktop/IIST/Microgravity/RPM/index.html#L2860-L2875)

### [3] Pica et al. (PLOS ONE, 2026)
* **Title:** *Characterization of the random positioning machine as a microgravity simulator for biological applications*
* **Authors:** A. Pica, G. Uras, I. G. Porco, A. Manca, A. Pantaleo, U. Della Croce
* **Journal:** *PLOS ONE*, Volume 21, Issue 6, Article e0351320, 2026.
* **Affiliations:** Department of Biomedical Sciences, University of Sassari, Sassari, Italy; Department of Chemistry and Pharmacy, University of Sassari, Sassari, Italy.
* **DOI:** [10.1371/journal.pone.0351320](https://doi.org/10.1371/journal.pone.0351320)
* **Exact Implemented Formulation (Mode A Algorithm):**
  * Zero-Crossing Stochastic Reversal:  
    `T_switch ∈ [20.0, 45.0] seconds`  
    `ω_target ∈ [0.80, 1.00] · ω_max · sign(random)`
  * Reversal Function: Regular stochastic direction reversals eliminate cumulative DC angular momentum drift and prevent steady centrifugal fluid recirculation patterns.
* **Implementation Location in Code:**
  * Backend: Mode `rpm_stochastic` in [server.py](file:///Users/pandeyji/Desktop/IIST/Microgravity/RPM/programming/Digital_Twin/src/webapp/server.py#L85-L125)
  * In-Browser Engine: [BrowserDigitalTwinEngine.step](file:///Users/pandeyji/Desktop/IIST/Microgravity/RPM/index.html#L2870-L2900)

### [4] Yotov et al. (Inventions, 2022)
* **Title:** *A New Random Positioning Machine Modification Applied for Microgravity Simulation in Laboratory Experiments with Rats*
* **Authors:** Vladimir V. Yotov, Julia Marovska, Valentin Turiyski, Stefan I. Ivanov
* **Journal:** *Inventions*, Volume 7, Issue 3, Article 85, 2022.
* **Affiliations:** Department of Physics and Astronomy, Faculty of Physics, Sofia University, Sofia, Bulgaria; Department of Medical Physics and Biophysics, Medical University of Plovdiv, Plovdiv, Bulgaria.
* **DOI:** [10.3390/inventions7030085](https://doi.org/10.3390/inventions7030085)
* **Exact Implemented Formulation (Equations 1–2):**
  * Yaw Gimbal Rotation (Outer, Y-axis): `R_Y(ψ)`
  * Pitch Gimbal Rotation (Inner, Z-axis): `R_Z(φ)`
  * Transformed Gravity Unit Vector in Sample Reference Frame:  
    `ē_g(t) = -sin(φ) · cos(ψ) ē_x + sin(φ) · sin(ψ) ē_y + cos(φ) ē_z`
  * Time-Averaged Simulated Microgravity (taSMG):  
    `<g>(T) = || (1/T) ∫₀ᵀ ē_g(t) dt ||`
* **Implementation Location in Code:**
  * Backend: [RPMSimulator.step](file:///Users/pandeyji/Desktop/IIST/Microgravity/RPM/programming/Digital_Twin/src/simulation/physics_engine.py#L425-L485)
  * In-Browser Engine: [BrowserDigitalTwinEngine.step](file:///Users/pandeyji/Desktop/IIST/Microgravity/RPM/index.html#L2905-L2925)

### [5] Hasenstein & van Loon (River Publishers, 2015)
* **Title:** *Clinostats and Other Rotating Systems—Design, Function, and Limitations*
* **Authors:** Karl H. Hasenstein & Jack J. W. A. van Loon
* **Book:** *Generation and Applications of Extra-Terrestrial Environments on Earth*, Chapter 14, pp. 147–160. River Publishers, 2015.
* **Affiliations:** Biology Department, University of Louisiana at Lafayette, Lafayette, LA, USA; DESC (Dutch Experiment Support Center), Department of Oral and Maxillofacial Surgery / Oral Pathology, VU University Medical Center & ACTA, Amsterdam, The Netherlands.
* **ISBN:** 978-87-93237-54-4 (Hardback), 978-87-93237-53-7 (eBook).
* **Exact Implemented Formulation:**
  * Unsteady 1D Cylindrical Navier-Stokes Momentum Diffusion:  
    `∂u_θ/∂t = ν · [ ∂²u_θ/∂r² + (1/r) · (∂u_θ/∂r) - u_θ/r² ]`
  * Dynamic Wall Shear Stress:  
    `τ_w = μ · | ∂u_θ/∂r - u_θ/r |_{r=R}` (expressed in mPa)
  * Stokes Oscillatory Boundary Layer Thickness:  
    `δ = √(2ν / ||ω||)`
* **Implementation Location in Code:**
  * Backend: [RealTimeFluidFDMSolver](file:///Users/pandeyji/Desktop/IIST/Microgravity/RPM/programming/Digital_Twin/src/simulation/physics_engine.py#L35-L120)
  * In-Browser Engine: [BrowserDigitalTwinEngine.step](file:///Users/pandeyji/Desktop/IIST/Microgravity/RPM/index.html#L2935-L2965)

---

## 2. Standard BibTeX Entries

```bibtex
@article{wadhwa2026guidelines,
  author    = {Wadhwa, Anna and Bruun, Lasse and Petersen, Johan C. G. and Petersen, Lonnie G.},
  title     = {Guidelines for use of the random positioning machine as a reduced-gravity analog},
  journal   = {Scientific Reports},
  volume    = {16},
  pages     = {39316},
  year      = {2026},
  publisher = {Nature Publishing Group},
  doi       = {10.1038/s41598-026-39316-7}
}

@article{kim2026clinostat,
  author    = {Kim, S. Y. and Park, J. H. and Kim, C. H.},
  title     = {Comparison of clinostat control strategies to achieve simulated microgravity with uniform gravity vector distribution},
  journal   = {npj Microgravity},
  volume    = {12},
  pages     = {570},
  year      = {2026},
  publisher = {Nature Publishing Group},
  doi       = {10.1038/s41526-026-00570-8}
}

@article{pica2026characterization,
  author    = {Pica, A. and Uras, G. and Porco, I. G. and Manca, A. and Pantaleo, A. and Della Croce, U.},
  title     = {Characterization of the random positioning machine as a microgravity simulator for biological applications},
  journal   = {PLOS ONE},
  volume    = {21},
  number    = {6},
  pages     = {e0351320},
  year      = {2026},
  publisher = {Public Library of Science},
  doi       = {10.1371/journal.pone.0351320}
}

@article{yotov2022new,
  author    = {Yotov, Vladimir V. and Marovska, Julia and Turiyski, Valentin and Ivanov, Stefan I.},
  title     = {A New Random Positioning Machine Modification Applied for Microgravity Simulation in Laboratory Experiments with Rats},
  journal   = {Inventions},
  volume    = {7},
  number    = {3},
  pages     = {85},
  year      = {2022},
  publisher = {MDPI},
  doi       = {10.3390/inventions7030085}
}

@incollection{hasenstein2015clinostats,
  author    = {Hasenstein, Karl H. and van Loon, Jack J. W. A.},
  title     = {Clinostats and Other Rotating Systems---Design, Function, and Limitations},
  booktitle = {Generation and Applications of Extra-Terrestrial Environments on Earth},
  chapter   = {14},
  pages     = {147--160},
  year      = {2015},
  publisher = {River Publishers},
  isbn      = {978-87-93237-54-4}
}
```

---

## 3. Institutional Provenance & Attribution

This Digital Twin platform is developed for the **Indian Institute of Space Science and Technology (IIST)**, Department of Aerospace Engineering, Valiamala, Thiruvananthapuram, Kerala 695547, India.

All rights reserved © 2026 IIST Microgravity Simulation Laboratory.
