#include "numerical.hpp"

#include "csv.hpp"
#include "math.hpp"
#include "stats.hpp"

#include <iomanip>
#include <iostream>
#include <sstream>

namespace rpmdt {

static constexpr double kPi = 3.14159265358979323846;

static double rpm_to_rad_s(double rpm) {
  return rpm * 2.0 * kPi / 60.0;
}

int run_numerical(const NumericalConfig &cfg) {
  CsvWriter csv(cfg.out_csv);
  if (!csv.ok()) {
    std::cerr << "ERROR: cannot open output CSV: " << cfg.out_csv << "\n";
    return 2;
  }

  csv.write_header(
      "t_s,theta_outer_rad,theta_inner_rad,omega_outer_rad_s,omega_inner_rad_s,"
      "gx,gy,gz,g_mag,ac_mag,tasmG_running");

  const double omega_outer = rpm_to_rad_s(cfg.outer_rpm);
  const double omega_inner = rpm_to_rad_s(cfg.inner_rpm);

  const Vec3 g_inertial{0.0, 0.0, -9.81};

  RunningStats gx_stats;
  RunningStats gy_stats;
  RunningStats gz_stats;
  RunningStats gmag_stats;

  double sumsq_g = 0.0;  // for taSMG = sqrt(mean(|g|^2))

  const double r_xy = std::sqrt(cfg.x_m * cfg.x_m + cfg.y_m * cfg.y_m);
  const double ac_mag = omega_outer * omega_outer * r_xy;

  const std::size_t steps = static_cast<std::size_t>(cfg.duration_s / cfg.dt_s) + 1;

  for (std::size_t i = 0; i < steps; ++i) {
    const double t = static_cast<double>(i) * cfg.dt_s;

    const double theta_outer = omega_outer * t;
    const double theta_inner = omega_inner * t;

    const Mat3 Rz = rot_z(theta_outer);
    const Mat3 Ry = rot_y(theta_inner);
    const Mat3 R = mul(Rz, Ry);

    const Vec3 g_payload = mul(R, g_inertial);
    const double g_mag = norm(g_payload);

    gx_stats.push(g_payload.x);
    gy_stats.push(g_payload.y);
    gz_stats.push(g_payload.z);
    gmag_stats.push(g_mag);

    sumsq_g += (g_payload.x * g_payload.x + g_payload.y * g_payload.y + g_payload.z * g_payload.z);
    const double taSMG_running = gx_stats.rms_from_sum_squares(sumsq_g);

    std::ostringstream line;
    line.setf(std::ios::fixed);
    line << std::setprecision(4)
         << t << ','
         << theta_outer << ','
         << theta_inner << ','
         << omega_outer << ','
         << omega_inner << ','
         << g_payload.x << ','
         << g_payload.y << ','
         << g_payload.z << ','
         << g_mag << ','
         << ac_mag << ','
         << taSMG_running;

    csv.write_row(line.str());
  }

  const double taSMG = gx_stats.rms_from_sum_squares(sumsq_g);

  std::cout << "NUMERICAL MODE COMPLETE\n";
  std::cout << "  dt_s: " << cfg.dt_s << "\n";
  std::cout << "  duration_s: " << cfg.duration_s << "\n";
  std::cout << "  outer_rpm: " << cfg.outer_rpm << " (" << omega_outer << " rad/s)\n";
  std::cout << "  inner_rpm: " << cfg.inner_rpm << " (" << omega_inner << " rad/s)\n";
  std::cout << "  point_m: (" << cfg.x_m << ", " << cfg.y_m << ", " << cfg.z_m << ")\n";
  std::cout << "  centripetal_ac_mag: " << ac_mag << " m/s^2\n";
  std::cout << "  taSMG: " << taSMG << " m/s^2\n";
  std::cout << "  g_mag mean: " << gmag_stats.mean << " std: " << gmag_stats.stddev() << "\n";
  std::cout << "  output_csv: " << cfg.out_csv << "\n";

  return 0;
}

}  // namespace rpmdt
