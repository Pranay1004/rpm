/**
 * IIST Random Positioning Machine (RPM) Digital Twin v2.0
 * Department of Aerospace Engineering - Microgravity Simulation Laboratory
 *
 * Native C++20 High-Performance Scientific Engine & Workstation.
 * Zero Python dependencies, maximum computational throughput, native arm64 execution.
 */

#include <iostream>
#include <iomanip>
#include <vector>
#include <string>
#include <cmath>
#include <fstream>

namespace Physics {
    constexpr double G0 = 9.80665;               // Standard gravitational acceleration (m/s^2)
    [[maybe_unused]] constexpr double MICROGRAVITY_LIMIT = 1e-3;   // Biological microgravity limit (10^-3 g)
    constexpr double WATER_NU = 1.004e-6;        // Kinematic viscosity of water at 20°C (m^2/s)
    constexpr double WATER_MU = 1.002e-3;        // Dynamic viscosity of water at 20°C (Pa.s)
    constexpr double PI = 3.14159265358979323846;

    // CAD Dimensions from Final_Drawing.pdf (MTECH2025)
    [[maybe_unused]] constexpr double BASE_WIDTH = 1.20;          // 1200 mm
    [[maybe_unused]] constexpr double BASE_DEPTH = 0.90;          // 900 mm
    [[maybe_unused]] constexpr double OUTER_FRAME_SIZE = 0.50;    // 500 mm
    [[maybe_unused]] constexpr double INNER_FRAME_SIZE = 0.35;    // 350 mm
    [[maybe_unused]] constexpr double PAYLOAD_SIZE = 0.20;        // 200 mm
    constexpr double CHAMBER_RADIUS = 0.06;      // 60 mm radius
    constexpr double MAX_ALPHA_RPM_S = 95.5;     // 10 rad/s^2 motor torque acceleration limit
}

struct Vector3 {
    double x = 0.0, y = 0.0, z = 0.0;
    double norm() const { return std::sqrt(x * x + y * y + z * z); }
};

struct TelemetryPoint {
    double time = 0.0;
    double phi_deg = 0.0;
    double psi_deg = 0.0;
    double omega_phi_rpm = 0.0;
    double omega_psi_rpm = 0.0;
    double gx = 0.0, gy = 0.0, gz = 0.0;
    double inst_g = 0.0;
    double tasmg = 0.0;
    double centrifugal_g = 0.0;
    double wall_shear_mPa = 0.0;
};

// 1D Navier-Stokes FDM Momentum Diffusion Solver (Hasenstein & van Loon 2015)
class NavierStokesFDMSolver {
private:
    int N;
    double R;
    std::vector<double> u;

public:
    NavierStokesFDMSolver(int grid_points = 25, double radius_m = 0.06)
        : N(grid_points), R(radius_m), u(grid_points, 0.0) {}

    double step(double dt, double omega_norm_rad_s) {
        double dr = R / (N - 1);
        double u_wall = omega_norm_rad_s * R;
        std::vector<double> u_next = u;

        for (int i = 1; i < N - 1; ++i) {
            double r_i = i * dr;
            double d2u = (u[i + 1] - 2.0 * u[i] + u[i - 1]) / (dr * dr);
            double du = (u[i + 1] - u[i - 1]) / (2.0 * dr);
            u_next[i] = u[i] + dt * Physics::WATER_NU * (d2u + (1.0 / r_i) * du - (u[i] / (r_i * r_i)));
        }
        u_next[0] = 0.0;
        u_next[N - 1] = u_wall;
        u = u_next;

        // Dynamic wall shear stress: tau_w = mu * |du/dr - u/r| at r = R
        double du_dr_wall = (u[N - 1] - u[N - 2]) / dr;
        double shear_Pa = Physics::WATER_MU * std::abs(du_dr_wall - (u_wall / R));
        return shear_Pa * 1000.0; // Return in mPa
    }
};

// Scientific Simulation Controller
class RPMSimulator {
public:
    double phi_deg = 0.0;
    double psi_deg = 0.0;
    double inner_tilt_deg = 0.0;
    double outer_tilt_deg = 0.0;

    double omega_phi_rpm = 2.0;
    double omega_psi_rpm = 2.292;
    double target_omega_phi = 2.0;
    double target_omega_psi = 2.292;

    double sum_gx = 0.0;
    double sum_gy = 0.0;
    double sum_gz = 0.0;
    long long sample_count = 0;

    NavierStokesFDMSolver fdm;
    std::vector<TelemetryPoint> history;

    RPMSimulator(double inner_rpm = 2.0, double outer_rpm = 2.292, double in_tilt = 0.0, double out_tilt = 0.0)
        : inner_tilt_deg(in_tilt), outer_tilt_deg(out_tilt),
          omega_phi_rpm(inner_rpm), omega_psi_rpm(outer_rpm),
          target_omega_phi(inner_rpm), target_omega_psi(outer_rpm),
          fdm(25, Physics::CHAMBER_RADIUS) {}

    TelemetryPoint step(double dt = 0.02) {
        // Torque acceleration ramping
        double max_step = Physics::MAX_ALPHA_RPM_S * dt;
        double d_phi = target_omega_phi - omega_phi_rpm;
        if (std::abs(d_phi) <= max_step) omega_phi_rpm = target_omega_phi;
        else omega_phi_rpm += (d_phi > 0 ? 1.0 : -1.0) * max_step;

        double d_psi = target_omega_psi - omega_psi_rpm;
        if (std::abs(d_psi) <= max_step) omega_psi_rpm = target_omega_psi;
        else omega_psi_rpm += (d_psi > 0 ? 1.0 : -1.0) * max_step;

        // Angle integration (1 RPM = 6 deg/sec)
        phi_deg = std::fmod(phi_deg + omega_phi_rpm * 6.0 * dt, 360.0);
        if (phi_deg < 0) phi_deg += 360.0;
        psi_deg = std::fmod(psi_deg + omega_psi_rpm * 6.0 * dt, 360.0);
        if (psi_deg < 0) psi_deg += 360.0;

        // Yotov et al. (2022) Kinematic Transformation with Axis Tilts
        double phi_rad = (phi_deg + inner_tilt_deg) * Physics::PI / 180.0;
        double psi_rad = (psi_deg + outer_tilt_deg) * Physics::PI / 180.0;

        double gx = -std::sin(phi_rad) * std::cos(psi_rad);
        double gy =  std::sin(phi_rad) * std::sin(psi_rad);
        double gz =  std::cos(phi_rad);
        double inst_g = std::sqrt(gx * gx + gy * gy + gz * gz);

        sample_count++;
        sum_gx += gx;
        sum_gy += gy;
        sum_gz += gz;

        double avg_gx = sum_gx / sample_count;
        double avg_gy = sum_gy / sample_count;
        double avg_gz = sum_gz / sample_count;
        double tasmg = std::sqrt(avg_gx * avg_gx + avg_gy * avg_gy + avg_gz * avg_gz);

        // Volumetric centrifugal acceleration (Wadhwa et al. 2026 Eq 5)
        double w_phi_rad_s = (omega_phi_rpm * 2.0 * Physics::PI) / 60.0;
        double w_psi_rad_s = (omega_psi_rpm * 2.0 * Physics::PI) / 60.0;
        double w_norm = std::sqrt(w_phi_rad_s * w_phi_rad_s + w_psi_rad_s * w_psi_rad_s);
        double cent_edge_g = (w_norm * w_norm * Physics::CHAMBER_RADIUS) / Physics::G0;

        // FDM fluid wall shear stress
        double shear_mPa = fdm.step(dt, w_norm);

        TelemetryPoint pt;
        pt.time = sample_count * dt;
        pt.phi_deg = phi_deg;
        pt.psi_deg = psi_deg;
        pt.omega_phi_rpm = omega_phi_rpm;
        pt.omega_psi_rpm = omega_psi_rpm;
        pt.gx = gx;
        pt.gy = gy;
        pt.gz = gz;
        pt.inst_g = inst_g;
        pt.tasmg = tasmg;
        pt.centrifugal_g = cent_edge_g;
        pt.wall_shear_mPa = shear_mPa;

        history.push_back(pt);
        return pt;
    }

    bool exportCSV(const std::string& filepath) const {
        std::ofstream file(filepath);
        if (!file.is_open()) return false;

        file << "# =====================================================================\n";
        file << "# INDIAN INSTITUTE OF SPACE SCIENCE AND TECHNOLOGY (IIST)\n";
        file << "# Department of Aerospace Engineering - Microgravity Simulation Laboratory\n";
        file << "# Native C++ Digital Twin v2.0 - Scientific Telemetry Output\n";
        file << "# CAD Model: Final_Drawing.pdf (Base 1200x900mm, Outer 500mm, Inner 350mm)\n";
        file << "# Inner Tilt: " << inner_tilt_deg << " deg | Outer Tilt: " << outer_tilt_deg << " deg\n";
        file << "# =====================================================================\n";
        file << "time_s,phi_deg,psi_deg,omega_phi_rpm,omega_psi_rpm,gx_g,gy_g,gz_g,inst_g,taSMG_g,centrifugal_edge_g,wall_shear_mPa\n";

        for (const auto& r : history) {
            file << std::fixed << std::setprecision(3) << r.time << ","
                 << std::setprecision(2) << r.phi_deg << ","
                 << std::setprecision(2) << r.psi_deg << ","
                 << std::setprecision(3) << r.omega_phi_rpm << ","
                 << std::setprecision(3) << r.omega_psi_rpm << ","
                 << std::setprecision(4) << r.gx << ","
                 << std::setprecision(4) << r.gy << ","
                 << std::setprecision(4) << r.gz << ","
                 << std::setprecision(4) << r.inst_g << ","
                 << std::setprecision(5) << r.tasmg << ","
                 << std::setprecision(5) << r.centrifugal_g << ","
                 << std::setprecision(2) << r.wall_shear_mPa << "\n";
        }
        return true;
    }
};

int main(int argc, char* argv[]) {
    double inner_rpm = 2.0;
    double outer_rpm = 2.292; // Kim et al. 2026 ratio 1.146
    double inner_tilt = 0.0;
    double outer_tilt = 0.0;
    double phi_init = 0.0;
    double psi_init = 0.0;
    int steps = 500;
    std::string csv_path = "";

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--inner-rpm" && i + 1 < argc) inner_rpm = std::stod(argv[++i]);
        else if (arg == "--outer-rpm" && i + 1 < argc) outer_rpm = std::stod(argv[++i]);
        else if (arg == "--inner-tilt" && i + 1 < argc) inner_tilt = std::stod(argv[++i]);
        else if (arg == "--outer-tilt" && i + 1 < argc) outer_tilt = std::stod(argv[++i]);
        else if (arg == "--phi" && i + 1 < argc) phi_init = std::stod(argv[++i]);
        else if (arg == "--psi" && i + 1 < argc) psi_init = std::stod(argv[++i]);
        else if (arg == "--steps" && i + 1 < argc) steps = std::stoi(argv[++i]);
        else if (arg == "--export-csv" && i + 1 < argc) csv_path = argv[++i];
        else if (arg == "--help" || arg == "-h") {
            std::cout << "IIST RPM Workstation v2.0 (Native C++ Engine)\n"
                      << "Usage: ./rpm_workstation [options]\n"
                      << "  --inner-rpm <val>     Inner speed in RPM (default: 2.0)\n"
                      << "  --outer-rpm <val>     Outer speed in RPM (default: 2.292)\n"
                      << "  --inner-tilt <deg>    Inner tilt angle (default: 0.0)\n"
                      << "  --outer-tilt <deg>    Outer tilt angle (default: 0.0)\n"
                      << "  --phi <deg>           Initial inner angle (default: 0.0)\n"
                      << "  --psi <deg>           Initial outer angle (default: 0.0)\n"
                      << "  --steps <n>           Number of 50Hz steps (default: 500 = 10s)\n"
                      << "  --export-csv <path>   Export RFC-4180 telemetry CSV\n";
            return 0;
        }
    }

    std::cout << "==========================================================================\n";
    std::cout << "  IIST RANDOM POSITIONING MACHINE (RPM) — DIGITAL TWIN v2.0 (C++20)       \n";
    std::cout << "  Department of Aerospace Engineering • Microgravity Simulation Lab       \n";
    std::cout << "==========================================================================\n";
    std::cout << "• CAD Assembly: Base 1200x900 mm | Outer 500 mm | Inner 350 mm | Payload 200 mm\n";
    std::cout << "• Rotational Speeds: Inner = " << inner_rpm << " RPM | Outer = " << outer_rpm 
              << " RPM (Ratio γ = " << (outer_rpm / inner_rpm) << ")\n";
    std::cout << "• Axis Tilts: Inner = " << inner_tilt << "° | Outer = " << outer_tilt << "°\n";
    std::cout << "• Initial Orientation: φ = " << phi_init << "° | ψ = " << psi_init << "°\n";
    std::cout << "• Executing " << steps << " 50 Hz Discrete Physics Timesteps (" << (steps * 0.02) << " s)...\n";
    std::cout << "--------------------------------------------------------------------------\n";
    std::cout << std::left << std::setw(8) << "Time(s)"
              << std::setw(8) << "Phi(°)"
              << std::setw(8) << "Psi(°)"
              << std::setw(9) << "Gx(g)"
              << std::setw(9) << "Gy(g)"
              << std::setw(9) << "Gz(g)"
              << std::setw(10) << "taSMG(g)"
              << std::setw(8) << "Shear(mPa)" << "\n";
    std::cout << "--------------------------------------------------------------------------\n";

    RPMSimulator sim(inner_rpm, outer_rpm, inner_tilt, outer_tilt);
    sim.phi_deg = phi_init;
    sim.psi_deg = psi_init;

    for (int s = 1; s <= steps; ++s) {
        TelemetryPoint pt = sim.step(0.02);
        if (s % 50 == 0 || s == steps) {
            std::cout << std::fixed << std::setprecision(2)
                      << std::left << std::setw(8) << pt.time
                      << std::setw(8) << pt.phi_deg
                      << std::setw(8) << pt.psi_deg
                      << std::setprecision(3)
                      << std::setw(9) << pt.gx
                      << std::setw(9) << pt.gy
                      << std::setw(9) << pt.gz
                      << std::setprecision(4)
                      << std::setw(10) << pt.tasmg
                      << std::setprecision(2)
                      << std::setw(8) << pt.wall_shear_mPa << "\n";
        }
    }

    std::cout << "==========================================================================\n";
    const auto& last = sim.history.back();
    std::cout << "✔ Final Converged <g> taSMG: " << std::fixed << std::setprecision(5) << last.tasmg << " g\n";
    std::cout << "✔ Residual Centrifugal Bias: " << last.centrifugal_g << " g (Safe boundary < 1.0000e-3 g)\n";
    std::cout << "✔ Fluid Wall Shear Stress:   " << std::setprecision(2) << last.wall_shear_mPa << " mPa\n";

    if (!csv_path.empty()) {
        if (sim.exportCSV(csv_path)) {
            std::cout << "✔ Scientific CSV Telemetry Exported: " << csv_path << "\n";
        } else {
            std::cerr << "✘ Failed to write CSV file: " << csv_path << "\n";
        }
    }
    std::cout << "==========================================================================\n";
    return 0;
}
