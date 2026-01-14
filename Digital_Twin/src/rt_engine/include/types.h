#ifndef RPM_RT_ENGINE_TYPES_H
#define RPM_RT_ENGINE_TYPES_H

#include <cstdint>
#include <chrono>

namespace rpm {

// Motor command structure
struct MotorCommand {
  float velocity;      // RPM or rad/s
  float acceleration;  // rad/s²
  uint16_t duration_ms; // Duration in milliseconds
  enum class Mode {
    CONSTANT,
    RAMP,
    PROGRAMMABLE
  } mode;
};

// Sensor data structure
struct SensorData {
  int64_t timestamp_us;  // Microsecond timestamp
  float accel_x, accel_y, accel_z;  // m/s²
  float gyro_x, gyro_y, gyro_z;     // rad/s
  float temp;                        // Celsius
};

// Hardware status
struct HardwareStatus {
  bool arduino_connected;
  bool rpi_connected;
  bool motor_inner_running;
  bool motor_outer_running;
  float battery_voltage;
  float temperature;
};

// Safety limits
struct SafetyLimits {
  float max_velocity;
  float max_acceleration;
  float max_temperature;
  uint16_t watchdog_timeout_ms;
};

} // namespace rpm

#endif // RPM_RT_ENGINE_TYPES_H
