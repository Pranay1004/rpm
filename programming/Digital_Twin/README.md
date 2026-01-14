# 🌌 RPM DIGITAL TWIN - Commercial Grade Software Suite

## Random Positioning Machine Controller & Digital Twin Platform
### For Microgravity Simulation Research

[![License](https://img.shields.io/badge/License-Commercial-blue.svg)]()
[![Platform](https://img.shields.io/badge/Platform-macOS%20|%20Windows-green.svg)]()
[![Status](https://img.shields.io/badge/Status-Development-orange.svg)]()

---

## 🎯 Overview

A commercial-grade software suite for Random Positioning Machine (RPM) control and digital twin simulation. Designed for space research institutions including ISRO, NASA, AXIOM SPACE, and leading research universities.

### Key Features
- **Real-time Hardware Control**: Arduino, Raspberry Pi, NEMA motor integration
- **Live Data Acquisition**: Multi-sensor fusion with 1kHz+ sampling
- **Digital Twin Simulation**: Physics-based RPM simulation with FEA validation
- **Microgravity Analysis**: Numerical gravity vector computation and validation
- **SpaceX-Grade UI**: Tesla Autopilot inspired dashboard with Unity 3D
- **HIL/SIL Testing**: Hardware-in-Loop and Software-in-Loop validation
- **Cross-Platform**: Native support for macOS (Apple Silicon) and Windows 11

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        RPM DIGITAL TWIN ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐ │
│  │   UNITY 3D UI   │◄──►│  MATLAB ENGINE  │◄──►│   HARDWARE INTERFACE    │ │
│  │  (C# Frontend)  │    │   (Scientific)  │    │   (Python/C++ Bridge)   │ │
│  └────────┬────────┘    └────────┬────────┘    └───────────┬─────────────┘ │
│           │                      │                         │               │
│           │              ┌───────▼───────┐                 │               │
│           │              │   SIMULINK    │                 │               │
│           │              │  (Real-Time)  │                 │               │
│           │              └───────┬───────┘                 │               │
│           │                      │                         │               │
│           ▼                      ▼                         ▼               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         gRPC MESSAGE BUS                            │   │
│  │              (Real-time bidirectional communication)                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│           │                      │                         │               │
│           ▼                      ▼                         ▼               │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐ │
│  │    InfluxDB     │    │   PostgreSQL    │    │      Redis Cache        │ │
│  │  (Time Series)  │    │   (Metadata)    │    │    (Real-time State)    │ │
│  └─────────────────┘    └─────────────────┘    └─────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
Digital_Twin/
├── 📂 docs/                          # Documentation
│   ├── architecture/                 # System design docs
│   ├── api/                          # API documentation
│   ├── user_manual/                  # End-user documentation
│   └── theory/                       # Scientific background
│
├── 📂 src/                           # Source Code
│   ├── 📂 unity_ui/                  # Unity 3D Dashboard (C#)
│   │   ├── Assets/
│   │   ├── Scenes/
│   │   └── Scripts/
│   │
│   ├── 📂 matlab_engine/             # MATLAB/Simulink Core
│   │   ├── models/                   # Simulink models
│   │   ├── scripts/                  # MATLAB scripts
│   │   ├── functions/                # MATLAB functions
│   │   └── mex/                      # MEX C/C++ interfaces
│   │
│   ├── 📂 hardware_interface/        # Hardware Communication
│   │   ├── arduino/                  # Arduino firmware
│   │   ├── raspberry_pi/             # RPi scripts
│   │   ├── drivers/                  # Motor drivers
│   │   └── protocols/                # Communication protocols
│   │
│   ├── 📂 data_pipeline/             # Data Management
│   │   ├── acquisition/              # Data acquisition
│   │   ├── processing/               # Real-time processing
│   │   ├── storage/                  # Database schemas
│   │   └── streaming/                # gRPC services
│   │
│   └── 📂 postprocessing/            # Advanced Analysis
│       ├── paraview/                 # ParaView scripts
│       ├── numerical/                # Numerical analysis
│       └── visualization/            # Advanced plots
│
├── 📂 config/                        # Configuration Files
│   ├── hardware/                     # Hardware configs
│   ├── simulation/                   # Simulation parameters
│   └── ui/                           # UI settings
│
├── 📂 tests/                         # Test Suite
│   ├── unit/                         # Unit tests
│   ├── integration/                  # Integration tests
│   ├── hil/                          # Hardware-in-Loop tests
│   └── sil/                          # Software-in-Loop tests
│
├── 📂 data/                          # Data Storage
│   ├── experiments/                  # Experiment data
│   ├── simulations/                  # Simulation results
│   └── calibration/                  # Calibration data
│
├── 📂 build/                         # Build Artifacts
│   ├── windows/                      # Windows builds
│   ├── macos/                        # macOS builds
│   └── installers/                   # Distribution packages
│
└── 📂 external/                      # External Dependencies
    ├── libraries/                    # Third-party libs
    └── tools/                        # External tools
```

---

## 🔧 Technology Stack

### Core Technologies

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| UI Framework | Unity 3D | 2023.x LTS | SpaceX-grade dashboard |
| Scientific Core | MATLAB | R2024a | Numerical computing |
| Real-time Sim | Simulink | R2024a | HIL/SIL simulation |
| Hardware Bridge | Python | 3.11+ | Serial/I2C/SPI protocols |
| Native Drivers | C++ | C++20 | High-performance MEX |
| Message Bus | gRPC | 1.60+ | Real-time IPC |
| Time-series DB | InfluxDB | 2.7+ | Sensor data storage |
| State Cache | Redis | 7.2+ | Real-time state |
| Metadata DB | PostgreSQL | 16+ | Experiment metadata |

### Hardware Support

| Device | Interface | Protocol | Purpose |
|--------|-----------|----------|---------|
| Arduino Mega/Due | USB Serial | Custom Protocol | Sensor hub |
| Raspberry Pi 4/5 | Ethernet/USB | TCP/IP + Serial | Edge compute |
| NEMA 17/23/34 | RS-485/CAN | Modbus RTU | Motor control |
| IMU (MPU9250) | I2C/SPI | Direct | Orientation sensing |
| Load Cells | Analog | ADC | Force measurement |
| Encoders | Quadrature | GPIO | Position feedback |

---

## 🚀 Quick Start

### Prerequisites

```bash
# macOS (Apple Silicon)
brew install python@3.11 postgresql redis influxdb

# Windows 11
winget install Python.Python.3.11 PostgreSQL.PostgreSQL Redis.Redis InfluxData.InfluxDB
```

### Installation

```bash
# Clone repository
git clone https://github.com/your-org/rpm-digital-twin.git
cd rpm-digital-twin

# Setup Python environment
python -m venv .venv
source .venv/bin/activate  # macOS
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Initialize databases
./scripts/init_databases.sh
```

### Launch Application

```bash
# Start all services
./scripts/launch.sh

# Or individual components
python src/data_pipeline/main.py &
matlab -r "run('src/matlab_engine/startup.m')"
# Unity app launches from build
```

---

## 📊 Feature Modules

### 1. Hardware Data Acquisition
- Multi-device sensor fusion
- 1kHz+ sampling rate
- Real-time packet visualization
- Connection health monitoring

### 2. Motor Control System
- NEMA stepper/servo support
- Inner/Outer frame control
- RPM/rad/s unit conversion
- Motion profile generation

### 3. Live Data Processing
- Real-time FFT analysis
- Statistical processing
- Anomaly detection
- High-quality plotting

### 4. Microgravity Computation
- Gravity vector simulation
- Time-averaged g calculation
- 3D point analysis
- Experimental validation

### 5. Digital Twin Simulation
- Physics-based RPM model
- FEA structural analysis
- Thermal simulation
- Lifecycle prediction

---

## 🎨 UI Design Philosophy

Inspired by **SpaceX Dragon Crew Display** and **Tesla Autopilot Dashboard**:

- **Dark Mode**: Reduces eye strain, aerospace standard
- **Real-time Gauges**: Animated circular gauges
- **3D Visualization**: Live RPM model rendering
- **Data Streams**: Matrix-style live data feeds
- **Alert System**: Color-coded status indicators
- **Touch Optimized**: Large touch targets

---

## 📄 License

Commercial License - All Rights Reserved
For licensing inquiries: contact@rpm-digitaltwin.com

---

## 🤝 Support

- **Technical Support**: support@rpm-digitaltwin.com
- **Documentation**: [docs.rpm-digitaltwin.com](https://docs.rpm-digitaltwin.com)
- **Training**: Available upon request

---

*Built for the future of space research* 🌟
