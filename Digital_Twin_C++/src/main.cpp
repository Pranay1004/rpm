#include "live.hpp"
#include "numerical.hpp"

#include <iostream>
#include <string>

namespace {

static void print_usage() {
  std::cout <<
      "rpm_digital_twin_cpp\n\n"
      "USAGE:\n"
      "  rpm_digital_twin_cpp numerical --outer-rpm <rpm> --inner-rpm <rpm> --duration <sec> --x <m> --y <m> --z <m> --out <csv>\n"
      "  rpm_digital_twin_cpp live (--tcp host:port | --serial <device> --baud <baud>) --out <csv>\n";
}

static bool arg_eq(const char *a, const char *b) {
  return std::string(a) == std::string(b);
}

}  // namespace

int main(int argc, char **argv) {
  if (argc < 2) {
    print_usage();
    return 2;
  }

  const std::string mode = argv[1];

  if (mode == "numerical") {
    rpmdt::NumericalConfig cfg;

    for (int i = 2; i < argc; ++i) {
      if (i + 1 >= argc) break;
      if (arg_eq(argv[i], "--outer-rpm")) cfg.outer_rpm = std::stod(argv[++i]);
      else if (arg_eq(argv[i], "--inner-rpm")) cfg.inner_rpm = std::stod(argv[++i]);
      else if (arg_eq(argv[i], "--duration")) cfg.duration_s = std::stod(argv[++i]);
      else if (arg_eq(argv[i], "--dt")) cfg.dt_s = std::stod(argv[++i]);
      else if (arg_eq(argv[i], "--x")) cfg.x_m = std::stod(argv[++i]);
      else if (arg_eq(argv[i], "--y")) cfg.y_m = std::stod(argv[++i]);
      else if (arg_eq(argv[i], "--z")) cfg.z_m = std::stod(argv[++i]);
      else if (arg_eq(argv[i], "--out")) cfg.out_csv = argv[++i];
      else if (arg_eq(argv[i], "--help")) {
        print_usage();
        return 0;
      }
    }

    if (cfg.dt_s <= 0.0) cfg.dt_s = 0.1;

    return rpmdt::run_numerical(cfg);
  }

  if (mode == "live") {
    rpmdt::LiveConfig cfg;

    for (int i = 2; i < argc; ++i) {
      if (i + 1 >= argc) break;
      if (arg_eq(argv[i], "--tcp")) cfg.tcp = argv[++i];
      else if (arg_eq(argv[i], "--serial")) cfg.serial = argv[++i];
      else if (arg_eq(argv[i], "--baud")) cfg.baud = std::stoi(argv[++i]);
      else if (arg_eq(argv[i], "--out")) cfg.out_csv = argv[++i];
      else if (arg_eq(argv[i], "--help")) {
        print_usage();
        return 0;
      }
    }

    return rpmdt::run_live(cfg);
  }

  print_usage();
  return 2;
}
