#include "csv.hpp"

namespace rpmdt {

CsvWriter::CsvWriter(const std::string &path) : out_(path) {}

void CsvWriter::write_header(const std::string &line) {
  out_ << line << "\n";
}

void CsvWriter::write_row(const std::string &line) {
  out_ << line << "\n";
}

bool CsvWriter::ok() const {
  return static_cast<bool>(out_);
}

}  // namespace rpmdt
