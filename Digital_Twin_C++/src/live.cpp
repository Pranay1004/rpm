#include "live.hpp"

#include "csv.hpp"
#include "stats.hpp"

#include <cerrno>
#include <cstring>
#include <iostream>
#include <optional>
#include <sstream>
#include <string>
#include <vector>

#include <fcntl.h>
#include <sys/socket.h>
#include <netdb.h>
#include <unistd.h>

#ifdef RPMDT_APPLE
#include <termios.h>
#endif

namespace rpmdt {

static std::optional<std::pair<std::string, std::string>> split_host_port(const std::string &s) {
  const auto pos = s.find(':');
  if (pos == std::string::npos) return std::nullopt;
  return std::make_pair(s.substr(0, pos), s.substr(pos + 1));
}

static int connect_tcp(const std::string &host, const std::string &port) {
  addrinfo hints{};
  hints.ai_family = AF_UNSPEC;
  hints.ai_socktype = SOCK_STREAM;

  addrinfo *res = nullptr;
  const int rc = getaddrinfo(host.c_str(), port.c_str(), &hints, &res);
  if (rc != 0) {
    std::cerr << "ERROR: getaddrinfo: " << gai_strerror(rc) << "\n";
    return -1;
  }

  int fd = -1;
  for (addrinfo *p = res; p != nullptr; p = p->ai_next) {
    fd = ::socket(p->ai_family, p->ai_socktype, p->ai_protocol);
    if (fd < 0) continue;
    if (::connect(fd, p->ai_addr, p->ai_addrlen) == 0) {
      break;
    }
    ::close(fd);
    fd = -1;
  }
  freeaddrinfo(res);
  return fd;
}

#ifdef RPMDT_APPLE
static speed_t baud_to_termios(int baud) {
  switch (baud) {
    case 9600: return B9600;
    case 19200: return B19200;
    case 38400: return B38400;
    case 57600: return B57600;
    case 115200: return B115200;
    default: return B115200;
  }
}

static int open_serial(const std::string &path, int baud) {
  const int fd = ::open(path.c_str(), O_RDWR | O_NOCTTY | O_NONBLOCK);
  if (fd < 0) {
    std::cerr << "ERROR: open serial failed: " << std::strerror(errno) << "\n";
    return -1;
  }

  termios tty{};
  if (tcgetattr(fd, &tty) != 0) {
    std::cerr << "ERROR: tcgetattr failed: " << std::strerror(errno) << "\n";
    ::close(fd);
    return -1;
  }

  cfmakeraw(&tty);
  const speed_t spd = baud_to_termios(baud);
  cfsetispeed(&tty, spd);
  cfsetospeed(&tty, spd);

  tty.c_cflag |= (CLOCAL | CREAD);
  tty.c_cflag &= ~CRTSCTS;
  tty.c_cflag &= ~CSTOPB;
  tty.c_cflag &= ~PARENB;
  tty.c_cflag &= ~CSIZE;
  tty.c_cflag |= CS8;

  tty.c_cc[VMIN] = 0;
  tty.c_cc[VTIME] = 1;

  if (tcsetattr(fd, TCSANOW, &tty) != 0) {
    std::cerr << "ERROR: tcsetattr failed: " << std::strerror(errno) << "\n";
    ::close(fd);
    return -1;
  }

  return fd;
}
#endif

static bool parse_csv_line_min3(const std::string &line, double &ax, double &ay, double &az) {
  // Accept: ax,ay,az,...
  std::stringstream ss(line);
  std::string item;
  std::vector<double> vals;
  while (std::getline(ss, item, ',')) {
    if (item.empty()) continue;
    try {
      vals.push_back(std::stod(item));
    } catch (...) {
      return false;
    }
  }
  if (vals.size() < 3) return false;
  ax = vals[0];
  ay = vals[1];
  az = vals[2];
  return true;
}

static std::optional<std::string> read_line_fd(int fd) {
  static std::string buffer;
  char tmp[512];
  const ssize_t n = ::read(fd, tmp, sizeof(tmp));
  if (n <= 0) return std::nullopt;
  buffer.append(tmp, tmp + n);
  const auto pos = buffer.find('\n');
  if (pos == std::string::npos) return std::nullopt;
  std::string line = buffer.substr(0, pos);
  buffer.erase(0, pos + 1);
  if (!line.empty() && line.back() == '\r') line.pop_back();
  return line;
}

int run_live(const LiveConfig &cfg) {
  if (cfg.tcp.empty() == cfg.serial.empty()) {
    std::cerr << "ERROR: choose exactly one of --tcp or --serial\n";
    return 2;
  }

  int fd = -1;
  if (!cfg.tcp.empty()) {
    const auto hp = split_host_port(cfg.tcp);
    if (!hp) {
      std::cerr << "ERROR: invalid --tcp value, expected host:port\n";
      return 2;
    }
    fd = connect_tcp(hp->first, hp->second);
    if (fd < 0) {
      std::cerr << "ERROR: TCP connect failed\n";
      return 3;
    }
    std::cout << "LIVE MODE (TCP) connected to " << cfg.tcp << "\n";
  } else {
#ifdef RPMDT_APPLE
    fd = open_serial(cfg.serial, cfg.baud);
    if (fd < 0) {
      std::cerr << "ERROR: serial open failed\n";
      return 3;
    }
    std::cout << "LIVE MODE (Serial) opened " << cfg.serial << " @ " << cfg.baud << "\n";
#else
    std::cerr << "ERROR: serial currently implemented for macOS/termios in this build\n";
    return 3;
#endif
  }

  CsvWriter csv(cfg.out_csv);
  if (!csv.ok()) {
    std::cerr << "ERROR: cannot open output CSV: " << cfg.out_csv << "\n";
    ::close(fd);
    return 4;
  }
  csv.write_header("ax,ay,az");

  RunningStats axs, ays, azs;
  std::size_t lines_ok = 0;
  std::size_t lines_bad = 0;

  std::cout << "Streaming... (Ctrl+C to stop)\n";

  while (true) {
    const auto line = read_line_fd(fd);
    if (!line) {
      // no data yet
      continue;
    }

    double ax = 0.0, ay = 0.0, az = 0.0;
    if (!parse_csv_line_min3(*line, ax, ay, az)) {
      lines_bad += 1;
      continue;
    }

    lines_ok += 1;
    axs.push(ax);
    ays.push(ay);
    azs.push(az);

    std::ostringstream row;
    row.setf(std::ios::fixed);
    row << ax << ',' << ay << ',' << az;
    csv.write_row(row.str());

    if (lines_ok % 100 == 0) {
      std::cout << "samples=" << lines_ok
                << " bad=" << lines_bad
                << " mean(ax,ay,az)= (" << axs.mean << "," << ays.mean << "," << azs.mean << ")"
                << " std(ax,ay,az)= (" << axs.stddev() << "," << ays.stddev() << "," << azs.stddev() << ")"
                << "\n";
    }
  }

  // unreachable
  // ::close(fd);
  // return 0;
}

}  // namespace rpmdt
