# RPM Digital Twin - Commercial-Grade Microgravity Simulation System

A next-generation digital twin platform for the Rotating Platform Machine (RPM), enabling real-time monitoring, control, and analysis of dual-axis rotation experiments in microgravity simulation environments.

## 🎯 Project Vision

This platform is designed for:
- **Space Agencies**: NASA, ISRO - Flight experiment validation
- **Research Institutions**: University researchers in microgravity science
- **Industrial Partners**: Commercial space ventures
- **Educational Organizations**: STEM outreach and training

## 🏗️ Architecture Overview

### Tech Stack
- **Frontend**: Electron + React + TypeScript
- **Backend**: Node.js + Express
- **Real-Time Engine**: C++17 with Boost
- **Analytics**: Python (NumPy, SciPy, pandas)
- **Database**: TimescaleDB (PostgreSQL)
- **3D Visualization**: Three.js
- **Data Plotting**: Plotly, D3.js

### System Layers

```
┌─────────────────────────────────────┐
│   Presentation (GUI)                │
│   Electron + React                  │
└────────────────┬────────────────────┘
┌────────────────┴────────────────────┐
│   Application Layer                 │
│   Node.js + Python + C++            │
└────────────────┬────────────────────┘
┌────────────────┴────────────────────┐
│   Data Layer                        │
│   TimescaleDB + Redis + HDF5        │
└────────────────┬────────────────────┘
┌────────────────┴────────────────────┐
│   Hardware Layer                    │
│   Arduino + RPi + Motors + Sensors  │
└─────────────────────────────────────┘
```

## 📋 Project Structure

```
Digital_Twin/
├── src/
│   ├── frontend/          # Electron + React GUI
│   ├── backend/           # Node.js API & services
│   ├── rt_engine/         # C++ Real-Time Engine
│   ├── analytics/         # Python Analytics
│   └── shared/            # Shared protocols & utilities
├── docs/                  # Documentation
├── tests/                 # Test suites
├── scripts/               # Build & deployment scripts
├── config/                # Configuration files
└── deployment/            # Docker & deployment configs
```

## 🚀 Quick Start (Phase 1)

### Prerequisites
- Node.js 18+
- Python 3.9+
- C++17 compiler (clang/gcc)
- CMake 3.20+
- PostgreSQL 14+

### Installation

```bash
# Clone and navigate
cd Digital_Twin

# Install frontend dependencies
cd src/frontend && npm install && cd ../..

# Install backend dependencies
cd src/backend && npm install && cd ../..

# Setup Python analytics environment
cd src/analytics && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && cd ../..

# Build C++ engine
cd src/rt_engine && mkdir -p build && cd build && cmake .. && make && cd ../../..
```

### Running the System

```bash
# Terminal 1: Start backend
cd src/backend && npm run dev

# Terminal 2: Start frontend (in dev mode)
cd src/frontend && npm run dev

# Terminal 3: Start analytics service
cd src/analytics && source venv/bin/activate && python app.py
```

## 📚 Documentation

- [Architecture Guide](docs/architecture.md) - Deep dive into system design
- [API Reference](docs/api_reference.md) - Backend API endpoints
- [Hardware Interface](docs/hardware_interface.md) - Communication protocols
- [User Manual](docs/user_manual.md) - GUI walkthrough
- [Development Guide](DEVELOPMENT.md) - Contributing guidelines

## 🎯 Implementation Roadmap

### Phase 1: Core Infrastructure (Weeks 1-3) ✓ Starting
- Development environment setup
- Hardware communication layer
- Basic GUI framework
- Database schema

### Phase 2: Motor Control & Data Acquisition (Weeks 4-6)
- Motor control interface
- Real-time sensor streaming
- Live visualization
- Safety interlocks

### Phase 3: Digital Twin (Weeks 7-10)
- Microgravity simulator
- Experimental validation
- 3D visualization
- Quality metrics

### Phase 4: Advanced Features (Weeks 11-14)
- AI optimization
- ParaView integration
- Report generation
- Cloud connectivity

### Phase 5: Polish & Deploy (Weeks 15-16)
- Performance optimization
- User testing
- Production packaging
- Distribution setup

## 🔧 Key Features

### Real-Time Control
- Dual-axis motor control
- Precise synchronization (<1ms latency)
- Programmable rotation profiles
- Emergency stop mechanisms

### Data Acquisition
- Multi-sensor integration
- High-frequency sampling (10Hz-10kHz)
- Time-series database
- Real-time streaming

### Digital Twin
- Numerical gravity calculation
- Experimental comparison
- Residual g-force analysis
- Quality factor computation

### Advanced Analytics
- FFT & frequency domain analysis
- Statistical characterization
- Anomaly detection
- Predictive maintenance

### Visualization
- 3D RPM model animation
- Real-time plots
- Gravity field heatmaps
- Trajectory tracking

## 📊 Data Pipeline

```
Raw Sensor Data
    ↓
Validation & Filtering
    ↓
Real-time Display + Database Storage
    ↓
Batch Analysis & Post-processing
    ↓
Reports & Visualizations
```

## 🔐 Safety & Reliability

- Hardware safety interlocks
- Rate-limiting on all commands
- Data integrity checks (CRC)
- Redundant communication
- Automatic error recovery
- Comprehensive logging

## 📈 Performance Targets

- **GUI Response Time**: <100ms
- **Real-Time Loop Frequency**: 1kHz
- **Data Throughput**: 10,000+ samples/sec
- **Sensor Latency**: <10ms
- **Database Query Time**: <500ms
- **3D Render FPS**: 60fps

## 📄 License

MIT License - See LICENSE file

## 🙏 Acknowledgments

Built for the global microgravity research community, with inspiration from leading space agencies and research institutions worldwide.

## 📧 Contact & Support

For questions, issues, or collaboration:
- Technical Issues: GitHub Issues
- Feature Requests: GitHub Discussions
- General Support: support@rpm-digital-twin.dev

---

**Status**: Phase 1 - Infrastructure Setup in Progress 🚀
