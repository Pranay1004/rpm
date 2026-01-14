# Getting Started Guide

## Quick Overview

The RPM Digital Twin is a professional-grade software system for controlling and analyzing rotating platform machines. It consists of four main components:

1. **GUI** (Electron + React) - User interface running on your computer
2. **Backend API** (Node.js) - REST API and real-time data streaming
3. **Real-Time Engine** (C++) - Low-latency hardware control
4. **Analytics** (Python) - Physics simulation and data analysis

## 5-Minute Quick Start

### 1. Install Prerequisites

```bash
# macOS
brew install node python cmake

# Ubuntu/Debian
sudo apt-get install nodejs python3 cmake

# Windows
# Download and install from: nodejs.org, python.org, cmake.org
```

Verify installation:
```bash
node --version      # Should be 18+
python3 --version   # Should be 3.9+
```

### 2. Setup Project

```bash
cd /path/to/Digital_Twin

# Run setup script (macOS/Linux)
bash scripts/setup-dev-env.sh

# OR manual setup (Windows / if script fails)
cd src/frontend && npm install && cd ../..
cd src/backend && npm install && cd ../..
cd src/analytics && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && cd ../..
```

### 3. Start Services

Open three terminal windows:

**Terminal 1 - Backend API**
```bash
cd src/backend
npm run dev
# Should see: "Server running on port 3000"
```

**Terminal 2 - Frontend GUI**
```bash
cd src/frontend
npm run dev
# Should see: "http://localhost:5173"
```

**Terminal 3 - Analytics**
```bash
cd src/analytics
source venv/bin/activate
python app.py
# Should see: "Running on http://localhost:5000"
```

### 4. Open Application

Go to: **http://localhost:5173**

You should see the RPM Digital Twin dashboard!

---

## Detailed Setup

### System Requirements

| Component | Requirement |
|-----------|-------------|
| OS | macOS 11+, Ubuntu 20.04+, or Windows 10+ |
| Node.js | 18.0 or higher |
| Python | 3.9 or higher |
| RAM | 4GB minimum (8GB recommended) |
| Disk | 2GB free space |
| C++ Compiler | GCC, Clang, or MSVC (for building RT engine) |

### Database Setup (Optional for Development)

The system works without a database initially, but for full functionality:

```bash
# Using Docker (easiest)
docker run --name rpm-db \
  -e POSTGRES_PASSWORD=dev \
  -e POSTGRES_DB=rpm_dev \
  -p 5432:5432 \
  -d timescale/timescaledb:latest-pg14

# Or install PostgreSQL locally
# macOS: brew install postgresql
# Ubuntu: sudo apt-get install postgresql postgresql-contrib

# Create database
createdb -U postgres rpm_dev

# Run migrations
cd src/backend
npm run migrate:latest
```

### C++ Real-Time Engine (Optional)

The C++ engine is optional for initial development:

```bash
cd src/rt_engine
mkdir build && cd build
cmake ..
make
./rpm_rt_engine  # Binary ready to use
```

---

## Project Structure at a Glance

```
Digital_Twin/
├── src/
│   ├── frontend/          # React + Electron GUI
│   │   └── src/
│   │       ├── views/     # Dashboard, Control, Analysis screens
│   │       └── components/# Reusable UI components
│   ├── backend/           # Node.js REST API
│   │   └── src/
│   │       └── api/       # Route handlers
│   ├── rt_engine/         # C++ real-time engine
│   │   ├── src/           # Implementation
│   │   ├── include/       # Header files
│   │   └── CMakeLists.txt # Build configuration
│   └── analytics/         # Python analysis
│       ├── microgravity_simulator.py
│       ├── sensor_processor.py
│       └── data_validator.py
├── docs/
│   ├── architecture.md    # System design
│   ├── api_reference.md   # API documentation
│   └── binary_protocol.md # Hardware communication
├── tests/                 # Test suites
├── scripts/               # Build & automation
└── deployment/            # Docker configs
```

---

## Common Tasks

### Add a New API Endpoint

1. Create handler in `src/backend/src/api/routes.ts`
2. Define request/response types
3. Add route to Express app
4. Document in `docs/api_reference.md`

Example:
```typescript
// src/backend/src/api/routes.ts
router.post('/api/my-endpoint', async (req: Request, res: Response) => {
  try {
    // Your logic here
    res.json({ success: true, data: ... });
  } catch (error) {
    res.status(500).json({ error: 'Operation failed' });
  }
});
```

### Add a GUI Component

1. Create React component in `src/frontend/src/components/`
2. Add CSS styling in `src/frontend/src/styles/`
3. Import and use in views

Example:
```typescript
// src/frontend/src/components/StatusIndicator.tsx
import React from 'react';

interface Props {
  status: 'connected' | 'disconnected';
}

export const StatusIndicator: React.FC<Props> = ({ status }) => {
  return (
    <div className={`status-indicator ${status}`}>
      <span className="status-dot"></span>
      <span>{status === 'connected' ? 'Connected' : 'Disconnected'}</span>
    </div>
  );
};
```

### Add a Python Analysis Function

1. Create function in `src/analytics/` module
2. Add unit tests
3. Create endpoint in `src/analytics/app.py`

Example:
```python
# src/analytics/my_analyzer.py
def analyze_data(readings):
    """Analyze sensor readings"""
    mean = np.mean(readings)
    std = np.std(readings)
    return {"mean": mean, "std": std}
```

### Run Tests

```bash
# Frontend tests
cd src/frontend
npm test

# Backend tests
cd src/backend
npm test

# Analytics tests
cd src/analytics
pytest

# C++ tests
cd src/rt_engine/build
ctest --output-on-failure
```

### Build for Production

```bash
# Build all components
npm run build:all

# Package as installers
npm run package:mac      # macOS .dmg
npm run package:win      # Windows .exe
npm run package:linux    # Linux AppImage
```

---

## Troubleshooting

### Port Already in Use

```bash
# Find and kill process using port 3000
lsof -i :3000
kill -9 <PID>

# Or use different port
PORT=3001 npm run dev
```

### Python Virtual Environment Issues

```bash
# Recreate venv
cd src/analytics
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Node Modules Corrupted

```bash
# Clean reinstall
rm -rf node_modules package-lock.json
npm install
```

### C++ Build Fails

```bash
# Check compiler
g++ --version
clang --version

# Clean build
cd src/rt_engine
rm -rf build
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Debug ..
make -j$(nproc)
```

### Database Connection Error

```bash
# Test PostgreSQL connection
psql -U postgres -h localhost -d rpm_dev

# If connection fails, check:
# 1. Is PostgreSQL running?
# 2. Is port 5432 open?
# 3. Are credentials correct in .env?
```

---

## Development Workflow

### 1. Create Feature Branch

```bash
git checkout -b feature/my-feature
```

### 2. Make Changes

Edit files in `src/` directories. Changes auto-reload in dev mode.

### 3. Run Tests

```bash
npm run test        # Run all tests
npm run test:watch  # Watch mode
```

### 4. Commit Changes

```bash
git add .
git commit -m "feat: add my awesome feature"
```

### 5. Push & Create Pull Request

```bash
git push origin feature/my-feature
# Then create PR on GitHub
```

---

## Performance Tips

### Frontend Optimization
- Use React DevTools to check renders
- Profile with Chrome DevTools Performance tab
- Lazy load components with React.lazy()

### Backend Optimization
- Enable query caching with Redis
- Use connection pooling for database
- Monitor with `clinic` tool

### Python Optimization
- Use NumPy vectorization instead of loops
- Profile with `cProfile`
- Use PyPy for CPU-bound tasks

### C++ Optimization
- Compile with `-O3` flag for Release builds
- Profile with `perf` (Linux) or Instruments (macOS)
- Use move semantics, avoid copies

---

## Next Steps

1. **Explore the Codebase**
   - Read [architecture.md](docs/architecture.md)
   - Check [api_reference.md](docs/api_reference.md)

2. **Implement Features**
   - Pick a task from [ROADMAP.md](ROADMAP.md)
   - Follow development guidelines in [DEVELOPMENT.md](DEVELOPMENT.md)

3. **Test Your Changes**
   - Write unit tests
   - Test manually in GUI
   - Check console for errors

4. **Contribute**
   - Submit pull requests
   - Help with documentation
   - Report bugs

---

## Getting Help

- **Questions?** Check [docs/](docs/) folder
- **Found a bug?** Open an issue on GitHub
- **Want to contribute?** See [CONTRIBUTING.md](CONTRIBUTING.md)
- **Need advice?** Start a discussion on GitHub

---

## Architecture Overview

```
[Electron GUI] 
    ↓ REST/WebSocket
[Node.js Backend] ← Real-time data
    ↓ API calls
[Python Analytics] - Numerical simulation
    ↑ Serial protocol
[C++ Engine] → Arduino/RPi → Physical Motors & Sensors
```

Every component can be developed and tested independently!

---

Happy coding! 🚀
