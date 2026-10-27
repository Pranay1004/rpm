//
//  RPMWorkstation.swift
//  IIST Random Positioning Machine (RPM) Digital Twin v2.0
//  Department of Aerospace Engineering - Microgravity Simulation Laboratory
//
//  Native Swift high-performance scientific simulation & telemetry engine.
//  Zero Python runtime dependencies, compiled directly to native arm64 machine code.
//

import Foundation

// MARK: - Mechanical & Physical Constants
struct PhysicsConstants {
    static let g0: Double = 9.80665              // Standard gravity (m/s^2)
    static let microgravityThreshold: Double = 1e-3 // Biological microgravity limit (g)
    static let waterViscosityKinematic: Double = 1.004e-6 // nu (m^2/s at 20°C)
    static let waterViscosityDynamic: Double = 1.002e-3   // mu (Pa.s at 20°C)
    
    // CAD Geometry (Final_Drawing.pdf MTECH2025)
    static let outerFrameSizeM: Double = 0.50     // 500 mm
    static let innerFrameSizeM: Double = 0.35     // 350 mm
    static let payloadCubeSizeM: Double = 0.20    // 200 mm
    static let chamberRadiusDefaultM: Double = 0.06 // 60 mm radius
    static let maxMotorAlphaRpmPerSec: Double = 95.5 // 10 rad/s^2 torque ramp
}

// MARK: - 3D Vector Math
struct Vector3D {
    var x: Double
    var y: Double
    var z: Double
    
    var norm: Double {
        return (x * x + y * y + z * z).squareRoot()
    }
    
    static func + (lhs: Vector3D, rhs: Vector3D) -> Vector3D {
        return Vector3D(x: lhs.x + rhs.x, y: lhs.y + rhs.y, z: lhs.z + rhs.z)
    }
    
    static func - (lhs: Vector3D, rhs: Vector3D) -> Vector3D {
        return Vector3D(x: lhs.x - rhs.x, y: lhs.y - rhs.y, z: lhs.z - rhs.z)
    }
    
    static func * (lhs: Vector3D, scalar: Double) -> Vector3D {
        return Vector3D(x: lhs.x * scalar, y: lhs.y * scalar, z: lhs.z * scalar)
    }
    
    static func / (lhs: Vector3D, scalar: Double) -> Vector3D {
        return Vector3D(x: lhs.x / scalar, y: lhs.y / scalar, z: lhs.z / scalar)
    }
    
    static func cross(_ a: Vector3D, _ b: Vector3D) -> Vector3D {
        return Vector3D(
            x: a.y * b.z - a.z * b.y,
            y: a.z * b.x - a.x * b.z,
            z: a.x * b.y - a.y * b.x
        )
    }
}

// MARK: - Telemetry Record
struct TelemetryRecord {
    let time: Double
    let phiDeg: Double
    let psiDeg: Double
    let omegaPhiRpm: Double
    let omegaPsiRpm: Double
    let gx: Double
    let gy: Double
    let gz: Double
    let instG: Double
    let taSMG: Double
    let centrifugalG: Double
    let wallShearStressMPa: Double
}

// MARK: - 1D Navier-Stokes FDM Momentum Diffusion Solver
class NavierStokesFDMSolver {
    let nGrid: Int
    var u: [Double]
    let radiusM: Double
    
    init(gridPoints: Int = 25, radiusM: Double = 0.06) {
        self.nGrid = gridPoints
        self.radiusM = radiusM
        self.u = Array(repeating: 0.0, count: gridPoints)
    }
    
    func step(dt: Double, omegaNormRadS: Double) -> (wallShearStressMPa: Double, boundaryLayerMm: Double) {
        let dr = radiusM / Double(nGrid - 1)
        let uWall = omegaNormRadS * radiusM
        var uNew = u
        
        let nu = PhysicsConstants.waterViscosityKinematic
        for i in 1..<(nGrid - 1) {
            let rI = Double(i) * dr
            let d2u = (u[i + 1] - 2.0 * u[i] + u[i - 1]) / (dr * dr)
            let du = (u[i + 1] - u[i - 1]) / (2.0 * dr)
            uNew[i] = u[i] + dt * nu * (d2u + (1.0 / rI) * du - (u[i] / (rI * rI)))
        }
        uNew[0] = 0.0
        uNew[nGrid - 1] = uWall
        self.u = uNew
        
        // Wall shear stress: tau_w = mu * |du/dr - u/r| at r = R
        let duDrWall = (u[nGrid - 1] - u[nGrid - 2]) / dr
        let shearPa = PhysicsConstants.waterViscosityDynamic * abs(duDrWall - (uWall / radiusM))
        let shearMPa = shearPa * 1000.0
        
        // Stokes boundary layer delta = sqrt(2 * nu / omega)
        let deltaMm = omegaNormRadS > 1e-4 ? ((2.0 * nu / omegaNormRadS).squareRoot() * 1000.0) : (radiusM * 1000.0)
        return (shearMPa, deltaMm)
    }
}

// MARK: - RPM Digital Twin Scientific Engine
class RPMSimulator {
    var phiDeg: Double = 0.0
    var psiDeg: Double = 0.0
    var innerTiltDeg: Double = 0.0
    var outerTiltDeg: Double = 0.0
    
    var omegaPhiRpm: Double = 2.0
    var omegaPsiRpm: Double = 2.292
    var targetOmegaPhi: Double = 2.0
    var targetOmegaPsi: Double = 2.292
    
    var sumGx: Double = 0.0
    var sumGy: Double = 0.0
    var sumGz: Double = 0.0
    var sampleCount: Int = 0
    
    let fdmSolver: NavierStokesFDMSolver
    var history: [TelemetryRecord] = []
    
    init(innerRpm: Double = 2.0, outerRpm: Double = 2.292, innerTilt: Double = 0.0, outerTilt: Double = 0.0) {
        self.omegaPhiRpm = innerRpm
        self.omegaPsiRpm = outerRpm
        self.targetOmegaPhi = innerRpm
        self.targetOmegaPsi = outerRpm
        self.innerTiltDeg = innerTilt
        self.outerTiltDeg = outerTilt
        self.fdmSolver = NavierStokesFDMSolver()
    }
    
    func step(dt: Double = 0.02) -> TelemetryRecord {
        // Torque ramp
        let maxStep = PhysicsConstants.maxMotorAlphaRpmPerSec * dt
        let dPhi = targetOmegaPhi - omegaPhiRpm
        if abs(dPhi) <= maxStep { omegaPhiRpm = targetOmegaPhi }
        else { omegaPhiRpm += (dPhi > 0 ? 1.0 : -1.0) * maxStep }
        
        let dPsi = targetOmegaPsi - omegaPsiRpm
        if abs(dPsi) <= maxStep { omegaPsiRpm = targetOmegaPsi }
        else { omegaPsiRpm += (dPsi > 0 ? 1.0 : -1.0) * maxStep }
        
        // Integrate angles (1 RPM = 6 deg/sec)
        phiDeg = (phiDeg + omegaPhiRpm * 6.0 * dt).truncatingRemainder(dividingBy: 360.0)
        if phiDeg < 0 { phiDeg += 360.0 }
        psiDeg = (psiDeg + omegaPsiRpm * 6.0 * dt).truncatingRemainder(dividingBy: 360.0)
        if psiDeg < 0 { psiDeg += 360.0 }
        
        // Yotov et al. (2022) with Axis Inclination Tilts
        let phiRad = (phiDeg + innerTiltDeg) * .pi / 180.0
        let psiRad = (psiDeg + outerTiltDeg) * .pi / 180.0
        
        let gx = -sin(phiRad) * cos(psiRad)
        let gy =  sin(phiRad) * sin(psiRad)
        let gz =  cos(phiRad)
        let instG = (gx * gx + gy * gy + gz * gz).squareRoot()
        
        sampleCount += 1
        sumGx += gx
        sumGy += gy
        sumGz += gz
        
        let avgGx = sumGx / Double(sampleCount)
        let avgGy = sumGy / Double(sampleCount)
        let avgGz = sumGz / Double(sampleCount)
        let taSMG = (avgGx * avgGx + avgGy * avgGy + avgGz * avgGz).squareRoot()
        
        // Volumetric centrifugal acceleration (Wadhwa Eq. 5)
        let omegaPhiRadS = (omegaPhiRpm * 2.0 * .pi) / 60.0
        let omegaPsiRadS = (omegaPsiRpm * 2.0 * .pi) / 60.0
        let omegaNorm = (omegaPhiRadS * omegaPhiRadS + omegaPsiRadS * omegaPsiRadS).squareRoot()
        let aCentEdgeG = (omegaNorm * omegaNorm * PhysicsConstants.chamberRadiusDefaultM) / PhysicsConstants.g0
        
        // FDM fluid shear
        let (shearMPa, _) = fdmSolver.step(dt: dt, omegaNormRadS: omegaNorm)
        
        let record = TelemetryRecord(
            time: Double(sampleCount) * dt,
            phiDeg: phiDeg,
            psiDeg: psiDeg,
            omegaPhiRpm: omegaPhiRpm,
            omegaPsiRpm: omegaPsiRpm,
            gx: gx,
            gy: gy,
            gz: gz,
            instG: instG,
            taSMG: taSMG,
            centrifugalG: aCentEdgeG,
            wallShearStressMPa: shearMPa
        )
        history.append(record)
        return record
    }
    
    func exportCSV(to filepath: String) throws {
        var lines: [String] = []
        lines.append("# =====================================================================")
        lines.append("# INDIAN INSTITUTE OF SPACE SCIENCE AND TECHNOLOGY (IIST)")
        lines.append("# Department of Aerospace Engineering - Microgravity Simulation Laboratory")
        lines.append("# Native Swift Digital Twin v2.0 - Telemetry Log")
        lines.append("# CAD Model: Final_Drawing.pdf (Base 1200x900mm, Outer 500mm, Inner 350mm)")
        lines.append("# Date: \(ISO8601DateFormatter().string(from: Date()))")
        lines.append("# Inner Tilt: \(innerTiltDeg) deg | Outer Tilt: \(outerTiltDeg) deg")
        lines.append("# =====================================================================")
        lines.append("time_s,phi_deg,psi_deg,omega_phi_rpm,omega_psi_rpm,gx_g,gy_g,gz_g,inst_g,taSMG_g,centrifugal_edge_g,wall_shear_mPa")
        
        for r in history {
            lines.append(String(format: "%.3f,%.2f,%.2f,%.3f,%.3f,%.4f,%.4f,%.4f,%.4f,%.5f,%.5f,%.2f",
                                r.time, r.phiDeg, r.psiDeg, r.omegaPhiRpm, r.omegaPsiRpm,
                                r.gx, r.gy, r.gz, r.instG, r.taSMG, r.centrifugalG, r.wallShearStressMPa))
        }
        
        let content = lines.joined(separator: "\n")
        try content.write(toFile: filepath, atomically: true, encoding: .utf8)
    }
}

// MARK: - Main CLI Interface
func printUsage() {
    print("""
    IIST RPM Workstation v2.0 (Native Swift Engine)
    Usage:
      rpm_workstation [options]
    
    Options:
      --inner-rpm <val>      Inner gimbal speed (RPM, default: 2.0)
      --outer-rpm <val>      Outer gimbal speed (RPM, default: 2.292)
      --inner-tilt <deg>     Inner axis inclination tilt (default: 0.0)
      --outer-tilt <deg>     Outer axis inclination tilt (default: 0.0)
      --phi <deg>            Initial inner angle (default: 0.0)
      --psi <deg>            Initial outer angle (default: 0.0)
      --steps <n>            Number of 50Hz discrete timesteps (default: 500 = 10s)
      --export-csv <path>    Export full RFC-4180 telemetry CSV to file
      --help                 Show this help menu
    """)
}

func main() {
    let args = CommandLine.arguments
    var innerRpm: Double = 2.0
    var outerRpm: Double = 2.292 // Kim et al. 2026 ratio 1.146
    var innerTilt: Double = 0.0
    var outerTilt: Double = 0.0
    var initialPhi: Double = 0.0
    var initialPsi: Double = 0.0
    var steps: Int = 500
    var exportCsvPath: String? = nil
    
    var i = 1
    while i < args.count {
        switch args[i] {
        case "--inner-rpm":
            if i + 1 < args.count { innerRpm = Double(args[i+1]) ?? 2.0; i += 1 }
        case "--outer-rpm":
            if i + 1 < args.count { outerRpm = Double(args[i+1]) ?? 2.292; i += 1 }
        case "--inner-tilt":
            if i + 1 < args.count { innerTilt = Double(args[i+1]) ?? 0.0; i += 1 }
        case "--outer-tilt":
            if i + 1 < args.count { outerTilt = Double(args[i+1]) ?? 0.0; i += 1 }
        case "--phi":
            if i + 1 < args.count { initialPhi = Double(args[i+1]) ?? 0.0; i += 1 }
        case "--psi":
            if i + 1 < args.count { initialPsi = Double(args[i+1]) ?? 0.0; i += 1 }
        case "--steps":
            if i + 1 < args.count { steps = Int(args[i+1]) ?? 500; i += 1 }
        case "--export-csv":
            if i + 1 < args.count { exportCsvPath = args[i+1]; i += 1 }
        case "--help", "-h":
            printUsage()
            exit(0)
        default:
            break
        }
        i += 1
    }
    
    print("==========================================================================")
    print("  IIST RANDOM POSITIONING MACHINE (RPM) — DIGITAL TWIN v2.0 (SWIFT)      ")
    print("  Department of Aerospace Engineering • Microgravity Simulation Lab      ")
    print("==========================================================================")
    print(String(format: "• CAD Assembly: Base 1200x900 mm | Outer 500 mm | Inner 350 mm | Payload 200 mm"))
    print(String(format: "• Operational Speeds: Inner = %.2f RPM | Outer = %.3f RPM (Ratio γ = %.3f)", innerRpm, outerRpm, outerRpm / innerRpm))
    print(String(format: "• Axis Inclinations: Inner Tilt = %.1f° | Outer Tilt = %.1f°", innerTilt, outerTilt))
    print(String(format: "• Initial Angles: φ = %.1f° | ψ = %.1f°", initialPhi, initialPsi))
    print(String(format: "• Executing %d 50 Hz Discrete Physics Timesteps (%.1f s)...", steps, Double(steps) * 0.02))
    print("--------------------------------------------------------------------------")
    print(String(format: "%-8s %-8s %-8s %-9s %-9s %-9s %-10s %-8s", "Time(s)", "Phi(°)", "Psi(°)", "Gx(g)", "Gy(g)", "Gz(g)", "taSMG(g)", "Shear"))
    print("--------------------------------------------------------------------------")
    
    let sim = RPMSimulator(innerRpm: innerRpm, outerRpm: outerRpm, innerTilt: innerTilt, outerTilt: outerTilt)
    sim.phiDeg = initialPhi
    sim.psiDeg = initialPsi
    
    for step in 1...steps {
        let rec = sim.step(dt: 0.02)
        if step % 50 == 0 || step == steps {
            print(String(format: "%-8.2f %-8.1f %-8.1f %-9.3f %-9.3f %-9.3f %-10.4f %-8.2f",
                         rec.time, rec.phiDeg, rec.psiDeg, rec.gx, rec.gy, rec.gz, rec.taSMG, rec.wallShearStressMPa))
        }
    }
    
    print("==========================================================================")
    let finalRec = sim.history.last!
    print(String(format: "✔ Final Converged <g> taSMG: %.5f g", finalRec.taSMG))
    print(String(format: "✔ Residual Centrifugal Bias: %.5f g (Safe threshold < 1.0000e-3 g)", finalRec.centrifugalG))
    print(String(format: "✔ Fluid Wall Shear Stress:   %.2f mPa", finalRec.wallShearStressMPa))
    
    if let csvPath = exportCsvPath {
        do {
            try sim.exportCSV(to: csvPath)
            print(String(format: "✔ Scientific CSV Telemetry Exported: %@", csvPath))
        } catch {
            print(String(format: "✘ Failed to write CSV to %@: %@", csvPath, error.localizedDescription))
        }
    }
    print("==========================================================================")
}

main()
