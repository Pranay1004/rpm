# Binary Communication Protocol - RPM Digital Twin

## Overview

Efficient binary protocol for Arduino ↔ C++ Engine communication

## Frame Structure

```
┌────┬─────┬──────────┬──────┬─────┐
│SOF │ CMD │   DATA   │ CRC  │ EOF │
│ 1B │ 1B  │  nB      │ 2B   │ 1B  │
└────┴─────┴──────────┴──────┴─────┘
```

- **SOF** (Start of Frame): 0xAA
- **CMD** (Command): See command table below
- **DATA**: Variable length payload
- **CRC**: 16-bit CRC-16 (CCITT)
- **EOF** (End of Frame): 0x55

## Command Reference

### Motor Commands

#### CMD 0x01: Start Motor
```
DATA:
  [0]: Motor ID (0=inner, 1=outer)
  [1-2]: Velocity (uint16, RPM × 10)
  [3-4]: Acceleration (uint16, RPM/s × 10)
  [5]: Mode (0=constant, 1=ramp, 2=profile)

Example: Start inner motor at 100 RPM
0xAA 0x01 0x00 0x03 0xE8 0x01 0xF4 0x00 [CRC] 0x55
```

#### CMD 0x02: Stop Motor
```
DATA:
  [0]: Motor ID (0=inner, 1=outer)
  [1-2]: Deceleration (uint16, RPM/s × 10)

Example: Stop inner motor with 100 RPM/s decel
0xAA 0x02 0x00 0x01 0xF4 [CRC] 0x55
```

#### CMD 0x03: Emergency Stop
```
DATA: None (immediate stop, max deceleration)

Example:
0xAA 0x03 [CRC] 0x55
```

### Query Commands

#### CMD 0x10: Request Status
```
DATA: None

Response: Status frame (CMD 0xA0)
```

#### CMD 0x11: Request Sensor Data
```
DATA:
  [0]: Sensor ID (0=IMU, 1=accel_x, 2=accel_y, 3=accel_z, 4=gyro_x, etc.)

Response: Sensor frame (CMD 0xA1)
```

### Response Frames

#### CMD 0xA0: Status Response
```
DATA:
  [0]: Status code (see below)
  [1]: Motor inner status
  [2]: Motor outer status
  [3-4]: Temperature (uint16, °C × 10)
  [5-6]: Battery voltage (uint16, V × 100)

Status Codes:
  0x00: OK
  0x01: Warning
  0x02: Error
  0x03: Hardware Error
```

#### CMD 0xA1: Sensor Data Response
```
DATA:
  [0-3]: Value (int32 or float32, format depends on sensor)
  [4-5]: Quality (uint16, 0-1000)

Example: IMU X acceleration = 0.5 m/s²
0xAA 0xA1 0x3F 0x00 0x00 0x00 0x03 0xE8 [CRC] 0x55
```

#### CMD 0xA2: Acknowledgment
```
DATA:
  [0]: Command that was acknowledged
  [1]: Success (0=success, 1=failure)
  [2-3]: Error code if failure
```

## CRC-16 Calculation

CCITT CRC-16 algorithm:
- Polynomial: 0x1021
- Initial value: 0x0000
- Final XOR: 0x0000

```c
uint16_t crc16(uint8_t* data, size_t length) {
    uint16_t crc = 0;
    for (size_t i = 0; i < length; i++) {
        crc ^= (uint16_t)data[i] << 8;
        for (int j = 0; j < 8; j++) {
            crc <<= 1;
            if (crc & 0x10000) crc ^= 0x1021;
        }
    }
    return crc;
}
```

## Example Sequences

### Start Both Motors

```
Computer → Arduino:
0xAA 0x01 0x00 0x03 0xE8 0x01 0xF4 0x00 [CRC] 0x55  (inner: 100 RPM, 50 RPM/s)

Arduino → Computer:
0xAA 0xA2 0x01 0x00 [CRC] 0x55  (ACK success)

Computer → Arduino:
0xAA 0x01 0x01 0x01 0xF4 0x00 0xF4 0x00 [CRC] 0x55  (outer: 50 RPM, 50 RPM/s)

Arduino → Computer:
0xAA 0xA2 0x01 0x00 [CRC] 0x55  (ACK success)
```

### Query Sensor Data

```
Computer → Arduino:
0xAA 0x11 0x00 [CRC] 0x55  (Request IMU data)

Arduino → Computer:
0xAA 0xA1 [4-byte accel] [2-byte quality] [CRC] 0x55
```

### Emergency Stop

```
Computer → Arduino:
0xAA 0x03 [CRC] 0x55

Arduino → Computer:
0xAA 0xA2 0x03 0x00 [CRC] 0x55  (ACK)

System enters safe state with all motors decelerated at max rate
```

## Timing Constraints

- **Command Response Time**: < 5ms
- **Sensor Data Rate**: 100 Hz (10ms period)
- **Motor Update Rate**: 1 kHz (1ms period)
- **Watchdog Timeout**: 500ms

## Error Handling

If no ACK received within 100ms:
1. Retry up to 3 times
2. Log failed transmission
3. Trigger diagnostic sequence

If CRC invalid:
1. Discard frame
2. Send NACK
3. Request retransmission

## Future Extensions

- Variable payload compression
- Encrypted commands (for secure deployment)
- Streaming mode for continuous data
- Multi-device support (device ID in frame)

---

For implementation details, see `src/rt_engine/include/protocol.h`
