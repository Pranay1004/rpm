#include "math.hpp"

namespace rpmdt {

Mat3 identity3() {
  Mat3 r{};
  r.at(0, 0) = 1.0;
  r.at(1, 1) = 1.0;
  r.at(2, 2) = 1.0;
  return r;
}

Mat3 rot_z(double theta) {
  const double c = std::cos(theta);
  const double s = std::sin(theta);

  Mat3 r{};
  r.at(0, 0) = c;
  r.at(0, 1) = -s;
  r.at(0, 2) = 0.0;

  r.at(1, 0) = s;
  r.at(1, 1) = c;
  r.at(1, 2) = 0.0;

  r.at(2, 0) = 0.0;
  r.at(2, 1) = 0.0;
  r.at(2, 2) = 1.0;
  return r;
}

Mat3 rot_y(double theta) {
  const double c = std::cos(theta);
  const double s = std::sin(theta);

  Mat3 r{};
  r.at(0, 0) = c;
  r.at(0, 1) = 0.0;
  r.at(0, 2) = s;

  r.at(1, 0) = 0.0;
  r.at(1, 1) = 1.0;
  r.at(1, 2) = 0.0;

  r.at(2, 0) = -s;
  r.at(2, 1) = 0.0;
  r.at(2, 2) = c;
  return r;
}

Mat3 mul(const Mat3 &a, const Mat3 &b) {
  Mat3 r{};
  for (int i = 0; i < 3; ++i) {
    for (int j = 0; j < 3; ++j) {
      double acc = 0.0;
      for (int k = 0; k < 3; ++k) {
        acc += a.at(i, k) * b.at(k, j);
      }
      r.at(i, j) = acc;
    }
  }
  return r;
}

Vec3 mul(const Mat3 &a, const Vec3 &v) {
  return Vec3{
      a.at(0, 0) * v.x + a.at(0, 1) * v.y + a.at(0, 2) * v.z,
      a.at(1, 0) * v.x + a.at(1, 1) * v.y + a.at(1, 2) * v.z,
      a.at(2, 0) * v.x + a.at(2, 1) * v.y + a.at(2, 2) * v.z,
  };
}

double norm(const Vec3 &v) {
  return std::sqrt(v.x * v.x + v.y * v.y + v.z * v.z);
}

}  // namespace rpmdt
