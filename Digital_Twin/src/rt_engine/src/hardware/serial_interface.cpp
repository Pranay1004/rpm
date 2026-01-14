#include "serial_interface.h"
#include <iostream>

namespace rpm {

SerialInterface::SerialInterface(const std::string& port, uint32_t baudrate)
    : port_(port), baudrate_(baudrate), connected_(false), file_descriptor_(-1) {}

SerialInterface::~SerialInterface() {
  if (connected_) {
    disconnect();
  }
}

bool SerialInterface::connect() {
  // TODO: Implement actual serial port connection using termios or Windows API
  connected_ = true;
  return true;
}

void SerialInterface::disconnect() {
  if (connected_) {
    // TODO: Implement port closure
    connected_ = false;
  }
}

bool SerialInterface::is_connected() const {
  return connected_;
}

bool SerialInterface::send(const std::vector<uint8_t>& data) {
  if (!connected_) {
    return false;
  }
  // TODO: Implement actual send
  return true;
}

std::vector<uint8_t> SerialInterface::receive(size_t max_bytes) {
  // TODO: Implement actual receive
  return std::vector<uint8_t>();
}

void SerialInterface::set_receive_callback(
    std::function<void(const std::vector<uint8_t>&)> callback) {
  // TODO: Implement callback system
}

} // namespace rpm
