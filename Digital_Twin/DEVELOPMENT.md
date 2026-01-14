# Development Guide

## Setting Up Development Environment

### System Requirements
- macOS 11+ / Ubuntu 20.04+ / Windows 10+
- Node.js 18.x or higher
- Python 3.9+
- C++17 compatible compiler
- Git

### Initial Setup

```bash
# Clone the repository
git clone <repo-url>
cd Digital_Twin

# Create development branch
git checkout -b feature/your-feature

# Set up all components
./scripts/setup-dev-env.sh
```

## Project Structure Explanation

### `/src/frontend`
React + Electron GUI application
- **components/**: Reusable React components
- **views/**: Full-page views
- **hooks/**: Custom React hooks
- **styles/**: Global and component styles
- **main.ts**: Electron main process

### `/src/backend`
Node.js REST API and services
- **api/**: Express route handlers
- **services/**: Business logic
- **models/**: Data models
- **middleware/**: Express middleware
- **utils/**: Utility functions

### `/src/rt_engine`
C++ real-time control engine
- **hardware/**: Device communication (Arduino, RPi)
- **control/**: Motor control algorithms
- **safety/**: Safety interlocks
- **protocols/**: Communication protocols
- **tests/**: Unit tests

### `/src/analytics`
Python analytics and simulation
- **processors/**: Data processing modules
- **simulators/**: Microgravity simulator
- **validators/**: Comparison & validation
- **utils/**: Helper functions

### `/src/shared`
Shared code across components
- **protocols/**: Binary protocol definitions
- **types/**: Common TypeScript types
- **constants/**: Global constants

## Development Workflow

### Frontend Development

```bash
cd src/frontend

# Install dependencies
npm install

# Start dev server (hot reload)
npm run dev

# Build for production
npm run build

# Run tests
npm run test

# Lint & format
npm run lint
npm run format
```

### Backend Development

```bash
cd src/backend

npm install
npm run dev        # nodemon auto-reload
npm run build
npm test
npm run lint
```

### C++ Real-Time Engine

```bash
cd src/rt_engine

# Debug build
mkdir -p build-debug && cd build-debug
cmake -DCMAKE_BUILD_TYPE=Debug ..
make -j$(nproc)

# Release build
mkdir -p build-release && cd build-release
cmake -DCMAKE_BUILD_TYPE=Release ..
make -j$(nproc)

# Run tests
ctest --output-on-failure
```

### Python Analytics

```bash
cd src/analytics

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Type checking
mypy .

# Linting
flake8 .
```

## Coding Standards

### TypeScript
- ESLint + Prettier configuration in place
- Strict mode enabled
- No `any` types without explicit reason
- Proper error handling

### Python
- PEP 8 compliance
- Type hints required
- Docstrings for all functions
- pytest for testing

### C++
- Modern C++17 features
- Google C++ Style Guide
- Const-correctness
- RAII principles

## Git Workflow

```bash
# Create feature branch
git checkout -b feature/amazing-feature

# Make changes and commit
git add .
git commit -m "feat: describe your changes"

# Push to remote
git push origin feature/amazing-feature

# Create Pull Request on GitHub
```

### Commit Message Format
```
<type>(<scope>): <subject>

<body>

<footer>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

## Testing

### Frontend Tests
```bash
cd src/frontend
npm run test:watch
npm run test:coverage
```

### Backend Tests
```bash
cd src/backend
npm test
npm run test:coverage
```

### C++ Tests
```bash
cd src/rt_engine/build
ctest -VV
```

### Python Tests
```bash
cd src/analytics
pytest -v --cov=.
```

## Database Setup

### Local Development
```bash
# Using Docker
docker run --name rpm-db -e POSTGRES_PASSWORD=dev \
  -e POSTGRES_DB=rpm_dev \
  -p 5432:5432 \
  -d timescale/timescaledb:latest-pg14

# Run migrations
cd src/backend
npm run migrate:latest
```

## Debugging

### Frontend (Electron)
- Open DevTools: `Ctrl+Shift+I` (Windows/Linux) or `Cmd+Option+I` (macOS)
- Use Chrome DevTools
- Check `console`, `Network`, `Application` tabs

### Backend (Node.js)
```bash
# Use built-in debugger
node --inspect-brk src/backend/dist/index.js

# Open chrome://inspect in Chrome
```

### C++ (Real-Time Engine)
```bash
# Debug build with GDB
gdb ./build-debug/rpm_rt_engine

# Or use LLDB on macOS
lldb ./build-debug/rpm_rt_engine
```

### Python
```bash
# Use pdb debugger
python -m pdb src/analytics/main.py

# Or use ipdb for better UX
ipython --pdb src/analytics/main.py
```

## Performance Profiling

### Frontend
```bash
# Chrome DevTools Performance tab
# Record timeline, check FPS
```

### Backend
```bash
# Memory profiling
npm install -g clinic
clinic doctor -- npm run dev
```

### C++
```bash
# Using perf on Linux
perf record ./build-release/rpm_rt_engine
perf report

# Using Instruments on macOS
xcrun instruments -t 'System Trace' ./build-release/rpm_rt_engine
```

### Python
```bash
python -m cProfile -o stats.prof src/analytics/main.py
python -m pstats stats.prof
```

## Common Tasks

### Adding a New API Endpoint
1. Create handler in `src/backend/api/`
2. Define types in `src/shared/types/`
3. Add route in `src/backend/app.ts`
4. Write tests in `tests/backend/`

### Adding a UI Component
1. Create component in `src/frontend/components/`
2. Add styles in `src/frontend/styles/`
3. Export from `src/frontend/components/index.ts`
4. Write tests in `tests/frontend/`

### Adding a C++ Module
1. Create source in `src/rt_engine/`
2. Add header in `src/rt_engine/include/`
3. Update `CMakeLists.txt`
4. Add tests in `src/rt_engine/tests/`

### Adding Python Analysis
1. Create module in `src/analytics/processors/`
2. Add tests in `tests/analytics/`
3. Document in `docs/analytics/`

## Troubleshooting

### Frontend won't start
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Backend port conflict
```bash
# Find process using port 3000
lsof -i :3000
kill -9 <PID>
```

### C++ build issues
```bash
# Clean build
rm -rf build-debug build-release
mkdir build-debug && cd build-debug
cmake ..
make clean
make
```

### Database connection issues
```bash
# Check if database is running
psql -U postgres -h localhost

# Reset migrations
npm run migrate:rollback:all
npm run migrate:latest
```

## Environment Variables

Create `.env.local` in project root:
```
# Backend
NODE_ENV=development
PORT=3000
DATABASE_URL=postgresql://user:pass@localhost:5432/rpm_dev
REDIS_URL=redis://localhost:6379

# Frontend (Electron)
REACT_APP_API_URL=http://localhost:3000
REACT_APP_WS_URL=ws://localhost:3000

# C++ Engine
CPP_SERIAL_PORT=/dev/ttyUSB0
CPP_BAUD_RATE=115200
```

## Release Process

```bash
# 1. Update version
npm version patch  # or minor, major

# 2. Build all components
npm run build:all

# 3. Run full test suite
npm run test:all

# 4. Create release notes
git log --oneline <last-version>..HEAD > RELEASE_NOTES.md

# 5. Tag release
git tag v<version>
git push origin v<version>

# 6. Build installers
npm run package:win
npm run package:mac
npm run package:linux
```

## Contributing Guidelines

1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Ensure all tests pass
5. Submit Pull Request
6. Wait for review

## Resources

- [Node.js Documentation](https://nodejs.org/docs/)
- [React Documentation](https://react.dev/)
- [Electron Documentation](https://www.electronjs.org/docs)
- [Python Best Practices](https://peps.python.org/)
- [C++ Reference](https://en.cppreference.com/)

## Getting Help

- Create an issue for bugs
- Use discussions for questions
- Check existing issues first
- Provide minimal reproducible example

---

Happy coding! 🚀
