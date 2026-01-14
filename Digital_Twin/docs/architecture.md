# Architecture Guide - RPM Digital Twin

## System Overview

The RPM Digital Twin is a distributed, multi-language system designed for real-time control and analysis of rotating platform machines in microgravity research.

## Architecture Layers

### 1. Presentation Layer (Electron + React)
**Purpose**: User interface and visualization
- Cross-platform desktop application
- Real-time data visualization
- Motor control interface
- Experiment management

**Key Components**:
- Dashboard: System overview & live metrics
- Control Panel: Motor command interface
- Analysis View: Data analysis & reports
- 3D Visualization: RPM model animation

**Technologies**:
- Electron: Native desktop experience
- React: Component-based UI
- Three.js: 3D graphics
- Plotly: Scientific plots

### 2. Application Layer (Node.js + Python + C++)

#### Node.js Backend
**Responsibilities**:
- REST API for GUI communication
- WebSocket for real-time data streaming
- Database abstraction
- Business logic coordination

**Key Modules**:
- `/api/`: Express route handlers
- `/services/`: Business logic
- `/models/`: Data models

#### Python Analytics
**Responsibilities**:
- Numerical microgravity simulation
- Sensor data processing
- Statistical analysis
- Report generation

**Key Modules**:
- `microgravity_simulator.py`: Gravity calculation
- `sensor_processor.py`: Data filtering & analysis
- `data_validator.py`: Experimental validation

#### C++ Real-Time Engine
**Responsibilities**:
- Hardware communication (Arduino/RPi)
- Motor control with <1ms latency
- Sensor data acquisition
- Safety interlocks

**Key Modules**:
- `hardware/`: Serial communication
- `control/`: Motor control algorithms
- `safety/`: Safety monitoring

### 3. Data Layer (TimescaleDB + Redis + HDF5)

**TimescaleDB** (PostgreSQL extension):
- Time-series sensor data
- Experiment metadata
- User configuration
- Query optimization for time-range

**Redis**:
- Real-time metric caching
- Session management
- Rate limiting

**HDF5**:
- Large experimental datasets
- Raw sensor dumps
- Offline analysis

### 4. Hardware Layer
- Arduino (motor control, I/O)
- Raspberry Pi (coordination, logging)
- NEMA steppers (dual-axis motors)
- IMU/Accelerometers (sensor suite)

## Communication Protocols

### REST API (Node.js ↔ Electron)

```
GET  /api/hardware/status        - System health
GET  /api/sensors/data/latest    - Current readings
POST /api/motors/inner/start     - Motor control
POST /api/motors/outer/start     - Motor control
GET  /api/data/history           - Fetch archived data
```

### WebSocket (Node.js ↔ Electron)
Real-time data streaming at 10-100 Hz

### Binary Protocol (C++ ↔ Arduino)
Efficient serial communication:
```
[SOF: 1B][CMD: 1B][DATA: nB][CRC: 2B][EOF: 1B]
```

### Inter-Process Communication (IPC)
Python analytics receives requests from Node.js backend

## Data Flow

### Real-Time Loop (1kHz)
```
Arduino → Serial → C++ Engine → Node.js → WebSocket → Electron
                 ↓
              Redis (cache)
                 ↓
              TimescaleDB
```

### Analysis Loop (Batch)
```
TimescaleDB ← Node.js ← Python Analytics
                           ↓
                      Reports/Visualizations
```

## Directory Structure

```
src/
├── frontend/           # Electron + React (GUI)
│   ├── components/     # Reusable React components
│   ├── views/          # Full-page views
│   ├── styles/         # CSS modules
│   └── hooks/          # Custom hooks
├── backend/            # Node.js API server
│   ├── api/            # Express routes
│   ├── services/       # Business logic
│   ├── models/         # Database models
│   └── middleware/     # Express middleware
├── rt_engine/          # C++ Real-time engine
│   ├── hardware/       # Device drivers
│   ├── control/        # Control algorithms
│   ├── safety/         # Safety systems
│   └── include/        # Header files
├── analytics/          # Python analytics
│   ├── simulators/     # Physics simulation
│   ├── processors/     # Data processing
│   ├── validators/     # Validation logic
│   └── tests/          # Unit tests
└── shared/             # Shared definitions
    ├── protocols/      # Binary protocol specs
    └── types/          # Common types
```

## Deployment Architecture

### Development
- Each component runs in separate terminal
- Hot reload enabled for frontend & backend
- Direct serial port access to hardware

### Production
- Containerized with Docker
- Node.js + Python in separate containers
- C++ engine as native binary
- Electron packaged as cross-platform installer

## Performance Targets

| Metric | Target | Achieved |
|--------|--------|----------|
| GUI Response | <100ms | - |
| RT Loop Freq | 1kHz | - |
| Sensor Latency | <10ms | - |
| Data Throughput | 10k+ samples/s | - |
| DB Query | <500ms | - |
| Render FPS | 60fps | - |

## Security Considerations

1. **Hardware Access**: Restricted serial port permissions
2. **API**: Rate limiting, input validation
3. **Database**: User authentication, encryption at rest
4. **Code**: Type safety (TypeScript, Python type hints)
5. **Dependencies**: Regular security audits

## Scalability

- **Horizontal**: Multiple RPM units can be managed via cloud
- **Vertical**: Database can handle 1M+ readings/hour
- **Network**: WebSocket with reconnection logic
- **Storage**: HDF5 for efficient large dataset access

## Future Extensions

1. **Cloud Integration**: Upload to central analysis platform
2. **AI/ML**: Anomaly detection, optimization
3. **VR/AR**: Immersive visualization
4. **IoT**: Multi-device fleet management
5. **ParaView**: CFD/FEA coupling

---

## Key Architectural Decisions

### Why Electron for GUI?
- Cross-platform (macOS, Windows, Linux)
- Modern web technologies (React)
- Native performance for critical sections
- Easy to distribute

### Why C++ for Real-Time?
- Deterministic performance
- Direct hardware access
- Minimal latency
- Proven for robotics/control

### Why Python for Analytics?
- Scientific libraries (NumPy, SciPy)
- Easy to extend
- Great visualization
- Data science ecosystem

### Why Node.js for Backend?
- Event-driven (perfect for IoT)
- JavaScript ecosystem
- WebSocket support out-of-box
- Easy integration with Electron

---

For detailed API documentation, see [api_reference.md](api_reference.md)
