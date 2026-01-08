#pragma once

#include <string>

namespace rpmdt {

struct LiveConfig {
  std::string tcp;       // host:port
  std::string serial;    // device path
  int baud{115200};
  std::string out_csv{"live.csv"};
};

int run_live(const LiveConfig &cfg);

}  // namespace rpmdt
