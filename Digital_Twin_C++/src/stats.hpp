#pragma once

#include <cstddef>
#include <cmath>

namespace rpmdt {

struct RunningStats {
  std::size_t n{0};
  double mean{0.0};
  double m2{0.0};

  void push(double x) {
    n += 1;
    const double delta = x - mean;
    mean += delta / static_cast<double>(n);
    const double delta2 = x - mean;
    m2 += delta * delta2;
  }

  double variance() const {
    if (n < 2) return 0.0;
    return m2 / static_cast<double>(n - 1);
  }

  double stddev() const { return std::sqrt(variance()); }

  double rms_from_sum_squares(double sumsq) const {
    if (n == 0) return 0.0;
    return std::sqrt(sumsq / static_cast<double>(n));
  }
};

}  // namespace rpmdt
