# API Reference - RPM Digital Twin

## Base URL
```
http://localhost:3000/api
```

## Authentication
Currently no authentication required. Production deployment should add JWT/OAuth.

## Hardware Endpoints

### Get Hardware Status
```
GET /hardware/status

Response:
{
  "arduino": {
    "connected": bool,
    "status": "connected" | "disconnected" | "error",
    "last_ping_ms": number
  },
  "rpi": {
    "connected": bool,
    "status": "connected" | "disconnected" | "error"
  },
  "motors": {
    "inner_running": bool,
    "outer_running": bool
  },
  "timestamp": "2024-01-11T12:34:56.000Z"
}
```

## Motor Control Endpoints

### Start Inner Frame Motor
```
POST /motors/inner/start

Body:
{
  "velocity": 100,              // RPM
  "acceleration": 50,           // RPM/s
  "mode": "constant" | "ramp" | "programmed"
}

Response:
{
  "success": bool,
  "message": string,
  "motor_id": "inner"
}
```

### Stop Inner Frame Motor
```
POST /motors/inner/stop

Response:
{
  "success": bool,
  "message": string
}
```

### Start Outer Frame Motor
```
POST /motors/outer/start

Body: Same as inner/start

Response: Same as inner/start
```

### Stop Outer Frame Motor
```
POST /motors/outer/stop

Response: Same as inner/stop
```

### Emergency Stop
```
POST /motors/emergency-stop

Response:
{
  "success": bool,
  "message": "All motors emergency stopped"
}
```

## Sensor Endpoints

### Get Latest Sensor Data
```
GET /sensors/data/latest

Response:
{
  "timestamp_us": 1234567890,
  "accel": {
    "x": -0.05,
    "y": 0.02,
    "z": -9.81
  },
  "gyro": {
    "x": 0.01,
    "y": 0.02,
    "z": 0.5
  },
  "temperature": 25.3
}
```

### Get Sensor Data History
```
GET /sensors/data/history?limit=100&offset=0

Query Parameters:
- limit: number of records (default: 100, max: 10000)
- offset: pagination offset (default: 0)
- start_time: ISO timestamp (optional)
- end_time: ISO timestamp (optional)

Response:
{
  "data": [
    {
      "timestamp_us": number,
      "accel": { x, y, z },
      "gyro": { x, y, z },
      "temperature": number
    },
    ...
  ],
  "total": number,
  "limit": number,
  "offset": number
}
```

## Data Analysis Endpoints

### Calculate Theoretical Gravity
```
POST /analysis/gravity/calculate

Body:
{
  "x": 0.1,           // meters
  "y": 0.0,
  "z": 0.05,
  "duration_s": 10.0,
  "rpm_params": {
    "inner_velocity_rpm": 100,
    "outer_velocity_rpm": 50,
    "inner_radius": 0.2,
    "outer_radius": 0.3
  }
}

Response:
{
  "theoretical_gravity_ms2": [0.01, -0.02, 0.05],
  "magnitude_ms2": 0.058,
  "quality_factor": 0.006,
  "time_window_s": 10.0
}
```

### Validate Experiment
```
POST /analysis/validate

Body:
{
  "x": 0.1,
  "y": 0.0,
  "z": 0.05,
  "duration_s": 10.0,
  "sensor_data": [
    [0.01, -0.02, 0.05],
    [0.02, -0.01, 0.04],
    ...
  ]
}

Response:
{
  "status": "PASS" | "NEEDS_REVIEW",
  "quality_factor": 0.008,
  "theoretical": {
    "gravity_vector_ms2": [0.01, -0.02, 0.05],
    "magnitude_ms2": 0.058
  },
  "experimental": {
    "gravity_vector_ms2": [0.015, -0.025, 0.048],
    "magnitude_ms2": 0.062
  },
  "error": {
    "absolute_magnitude_ms2": 0.008,
    "relative_error_percent": 1.2
  }
}
```

## Configuration Endpoints

### Get Current Configuration
```
GET /config

Response:
{
  "serial_port": "/dev/ttyUSB0",
  "baud_rate": 115200,
  "sampling_rate_hz": 100,
  "motor_limits": {
    "max_velocity_rpm": 500,
    "max_acceleration_rpms": 200
  }
}
```

### Update Configuration
```
PUT /config

Body: Partial config update (only fields to change)

Response: Updated configuration
```

## Experiment Management

### List Experiments
```
GET /experiments?limit=20&offset=0

Response:
{
  "experiments": [
    {
      "id": "exp-001",
      "name": "Cell Culture Test",
      "start_time": "2024-01-11T10:00:00Z",
      "duration_s": 3600,
      "status": "completed" | "running" | "failed",
      "data_points": 360000
    }
  ],
  "total": number
}
```

### Create Experiment
```
POST /experiments

Body:
{
  "name": "Cell Culture Test",
  "description": "Microgravity environment for cell culture",
  "rpm_profile": {
    "inner_velocity_rpm": 100,
    "outer_velocity_rpm": 50
  }
}

Response:
{
  "id": "exp-001",
  "created_at": "2024-01-11T10:00:00Z"
}
```

### Get Experiment Details
```
GET /experiments/:id

Response:
{
  "id": "exp-001",
  "name": string,
  "description": string,
  "start_time": ISO datetime,
  "end_time": ISO datetime,
  "duration_s": number,
  "status": string,
  "data_points": number,
  "rpm_profile": object,
  "quality_metrics": {
    "mean_quality_factor": number,
    "max_residual_g_ms2": number,
    "temperature_stability": number
  }
}
```

## WebSocket Real-Time Data

### Connection
```
ws://localhost:3000/api/ws/data
```

### Message Format
Messages are sent as JSON every 100ms (10Hz) or 10ms (100Hz) depending on config

```json
{
  "type": "sensor_data",
  "data": {
    "timestamp_us": number,
    "accel": { "x": number, "y": number, "z": number },
    "gyro": { "x": number, "y": number, "z": number },
    "temperature": number
  }
}
```

### Subscribe to Channel
```json
{
  "action": "subscribe",
  "channel": "sensors:accel" | "motors:status" | "temperature"
}
```

## Error Responses

All errors follow this format:

```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "details": {}
}
```

### Common Error Codes
- `HARDWARE_NOT_CONNECTED`: Hardware unavailable
- `INVALID_PARAMETER`: Bad request parameter
- `OPERATION_FAILED`: Command execution failed
- `DATABASE_ERROR`: Database query failed
- `RATE_LIMITED`: Too many requests

## Rate Limiting

- General API: 100 requests/15 minutes per IP
- WebSocket: 1000 messages/minute per connection

Headers in response:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1234567890
```

---

For more information, see [architecture.md](architecture.md)
