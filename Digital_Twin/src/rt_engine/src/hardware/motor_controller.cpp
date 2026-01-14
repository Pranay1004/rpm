#include "motor_controller.h"
#include "serial_interface.h"

namespace rpm {

MotorController::MotorController(std::shared_ptr<SerialInterface> serial)
    : serial_(serial), inner_running_(false), outer_running_(false),
      inner_velocity_(0), outer_velocity_(0) {}

bool MotorController::start_motor(bool inner_frame, const MotorCommand& cmd) {
  if (!serial_ || !serial_->is_connected()) {
    return false;
  }

  if (!send_command(inner_frame, cmd)) {
    return false;
  }

  if (inner_frame) {
    inner_running_ = true;
    inner_velocity_ = cmd.velocity;
  } else {
    outer_running_ = true;
    outer_velocity_ = cmd.velocity;
  }

  return true;
}

bool MotorController::stop_motor(bool inner_frame) {
  if (!serial_ || !serial_->is_connected()) {
    return false;
  }

  // TODO: Send stop command via serial

  if (inner_frame) {
    inner_running_ = false;
  } else {
    outer_running_ = false;
  }

  return true;
}

bool MotorController::emergency_stop() {
  if (!serial_ || !serial_->is_connected()) {
    return false;
  }

  // TODO: Send emergency stop command (highest priority)

  inner_running_ = false;
  outer_running_ = false;
  inner_velocity_ = 0;
  outer_velocity_ = 0;

  return true;
}

bool MotorController::is_running(bool inner_frame) const {
  return inner_frame ? inner_running_ : outer_running_;
}

float MotorController::get_velocity(bool inner_frame) const {
  return inner_frame ? inner_velocity_ : outer_velocity_;
}

bool MotorController::send_command(bool inner_frame, const MotorCommand& cmd) {
  // TODO: Encode command into binary protocol and send via serial
  return true;
}

} // namespace rpm
