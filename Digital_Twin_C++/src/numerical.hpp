#pragma once

#include <string>

namespace rpmdt {

struct NumericalConfig {
  double outer_rpm{0.0};
  double inner_rpm{0.0};
  double duration_s{60.0};
  double dt_s{0.1};
  double x_m{0.0};
  double y_m{0.0};
  double z_m{0.0};
  std::string out_csv{"out.csv"};
};

int run_numerical(const NumericalConfig &cfg);

}  // namespace rpmdt
