#pragma once

#include <array>
#include <cmath>

namespace rpmdt {

struct Vec3 {
  double x{0.0};
  double y{0.0};
  double z{0.0};
};

struct Mat3 {
  // Row-major 3x3
  std::array<double, 9> m{};

  constexpr double at(int r, int c) const { return m[static_cast<size_t>(r * 3 + c)]; }
  constexpr double &at(int r, int c) { return m[static_cast<size_t>(r * 3 + c)]; }
};

Mat3 identity3();
Mat3 rot_z(double theta);
Mat3 rot_y(double theta);
Mat3 mul(const Mat3 &a, const Mat3 &b);
Vec3 mul(const Mat3 &a, const Vec3 &v);

double norm(const Vec3 &v);

}  // namespace rpmdt
