# RPM - Random Positioning Machine Digital Twin

A web-based simulator for Random Positioning Machines (RPM) used in microgravity research. Real-time 3D visualization, paper-accurate physics, and comprehensive analytics.

## 🚀 Features

- **Real-time 3D visualization** with Three.js
- **Paper-accurate physics** based on published research (Yotov et al.)
- **Live microgravity metrics** (taSMG, time-averaged gravity)
- **Interactive controls** for motor speeds and frame dimensions
- **WebSocket streaming** for low-latency updates (50 Hz physics, 20 Hz display)
- **Responsive dark-theme UI** with SpaceX/Tesla aesthetic

## 📋 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
python src/main.py

# Open browser
http://localhost:8080
```

## 📚 Documentation

See `docs/` folder:
- `README.txt` - Comprehensive guide (includes SAMPLE metric explanation)
- `formulas.txt` - All physics equations explained
- `MATLAB_ANALYSIS.txt` - MATLAB comparison and roadmap
- `REFERENCES.txt` - Research citations and sources
- `SAMPLES_METRIC_EXPLAINED.txt` - Deep dive on SAMPLE convergence metric

## ⚖️ AI-Generated Code Disclosure

**This project was developed with assistance from AI tools:**
- GitHub Copilot for code completion
- Claude (Anthropic) for architecture and documentation  
- Human direction for requirements, physics equations, and testing

**Estimated contribution:** ~80% AI-generated, ~20% human-directed

See [DISCLAIMER.md](DISCLAIMER.md) for full licensing and legal information.

## 🔬 Research Citation

Physics implementation based on:

> Yotov et al., "A New Random Positioning Machine Modification Applied for Microgravity Simulation in Laboratory Experiments with Rats"

Key equations used: Rotation matrices (Eq. 2), time-averaged microgravity (taSMG)

## 📄 License

[MIT License](LICENSE) - Free for commercial and non-commercial use

**Important:** This software is provided "AS-IS" without warranty. For research and educational use only. Not validated for medical or safety-critical applications.

## ⚠️ Disclaimers

- **No warranty** of accuracy or fitness for purpose
- **Research/educational use only** - not for medical applications
- **Not FDA approved** or medically validated
- **AI-generated code** - may contain bugs, use at your own risk

See [DISCLAIMER.txt](DISCLAIMER.txt) for complete legal information.

## 🛠️ Tech Stack

- **Backend:** Python 3.10+, FastAPI, NumPy, SciPy
- **Frontend:** HTML5, JavaScript (ES6+), Three.js, Chart.js
- **Communication:** WebSocket (real-time streaming)
- **Physics:** 50 Hz simulation, paper-accurate rotation matrices

## 📊 Current Status

**Version:** v3.1.1 (Physics Fix Release)
- ✅ Paper-accurate physics implemented
- ✅ Real-time 3D visualization
- ✅ taSMG recovery bug fixed
- ⚠️ Random motor controller (planned v3.2.0)
- ⚠️ Centripetal acceleration (planned v3.2.0)

## 🤝 Contributing

Contributions welcome! This is an open source research project.

Please:
- Cite any research sources you use
- Add tests for new physics features
- Update documentation
- Follow existing code style

## 📞 Contact

- **GitHub:** [IIST-Aero/rpm](https://github.com/iist-aero/rpm)
- **Issues:** [Report bugs here](https://github.com/iist-aero/rpm/issues)

## 🙏 Acknowledgments

- Research by Yotov et al. for RPM physics
- GitHub Copilot & Claude AI for development assistance
- Open source community for libraries (Three.js, FastAPI, NumPy)

---

**⚠️ IMPORTANT:** Read [DISCLAIMER.md](DISCLAIMER.md) before commercial use or redistribution.
