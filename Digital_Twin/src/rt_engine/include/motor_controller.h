#ifndef RPM_MOTOR_CONTROLLER_H
#define RPM_MOTOR_CONTROLLER_H

#include "types.h"
#include <memory>

namespace rpm {

class SerialInterface;

class MotorController {
public:
  MotorController(std::shared_ptr<SerialInterface> serial);
  
  // Motor control commands
  bool start_motor(bool inner_frame, const MotorCommand& cmd);
  bool stop_motor(bool inner_frame);
  bool emergency_stop();
  
  // Query motor status
  bool is_running(bool inner_frame) const;
  float get_velocity(bool inner_frame) const;

private:
  std::shared_ptr<SerialInterface> serial_;
  bool inner_running_;
  bool outer_running_;
  float inner_velocity_;
  float outer_velocity_;

  bool send_command(bool inner_frame, const MotorCommand& cmd);
};

} // namespace rpm

#endif // RPM_MOTOR_CONTROLLER_H
