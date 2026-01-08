#pragma once

#include <fstream>
#include <string>

namespace rpmdt {

class CsvWriter {
 public:
  explicit CsvWriter(const std::string &path);

  void write_header(const std::string &line);
  void write_row(const std::string &line);
  bool ok() const;

 private:
  std::ofstream out_;
};

}  // namespace rpmdt
