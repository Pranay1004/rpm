#ifndef RPM_SERIAL_INTERFACE_H
#define RPM_SERIAL_INTERFACE_H

#include "types.h"
#include <string>
#include <vector>
#include <memory>
#include <functional>

namespace rpm {

class SerialInterface {
public:
  SerialInterface(const std::string& port, uint32_t baudrate);
  ~SerialInterface();

  bool connect();
  void disconnect();
  bool is_connected() const;

  // Send data to device
  bool send(const std::vector<uint8_t>& data);
  
  // Receive data from device
  std::vector<uint8_t> receive(size_t max_bytes);

  // Set callback for received data
  void set_receive_callback(std::function<void(const std::vector<uint8_t>&)> callback);

private:
  std::string port_;
  uint32_t baudrate_;
  bool connected_;
  int file_descriptor_;

  bool open_port();
  void close_port();
};

} // namespace rpm

#endif // RPM_SERIAL_INTERFACE_H
