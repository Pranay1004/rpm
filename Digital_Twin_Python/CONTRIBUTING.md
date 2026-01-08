# Contributing to RPM Digital Twin

Thank you for your interest in contributing! This is a professional-grade project for ISRO, NASA, and commercial space applications. Please follow these guidelines.

## Code Quality Standards

### Python Style
- Follow PEP 8 (use `black` for formatting)
- Type hints required for all functions
- Docstrings for all public classes/methods (Google style)
- Max line length: 100 characters

### Example
```python
def gravity_in_payload_frame(
    theta_outer: np.ndarray,
    theta_inner: np.ndarray,
) -> np.ndarray:
    """
    Compute gravity vector in payload frame.
    
    Args:
        theta_outer: Outer frame rotation angles (rad), shape (N,)
        theta_inner: Inner frame rotation angles (rad), shape (N,)
    
    Returns:
        Gravity vector [gx, gy, gz] in payload frame, shape (N, 3)
    """
```

### Testing Requirements
- All new functions require unit tests
- Minimum 80% code coverage
- Tests in `tests/test_*.py`
- Run: `PYTHONPATH=src pytest tests/ -v --cov=src/rpm_digital_twin`

## Pull Request Process

1. **Create branch** from `main`:
   ```bash
   git checkout -b feature/your-feature
   ```

2. **Implement feature** with tests:
   ```bash
   # Make changes
   git add .
   git commit -m "feat: description of changes"
   ```

3. **Format code:**
   ```bash
   black src/ tests/
   flake8 src/ tests/
   mypy src/ --strict
   ```

4. **Run full test suite:**
   ```bash
   PYTHONPATH=src pytest tests/ -v
   ```

5. **Push and create PR:**
   ```bash
   git push origin feature/your-feature
   ```

## Areas for Contribution

### High Priority
- [ ] Real hardware integration tests (Arduino sketch examples)
- [ ] Performance optimization (large-scale data export)
- [ ] Additional sensor interfaces (CAN bus, GPIB)
- [ ] Advanced visualization (3D trajectory animation)

### Medium Priority
- [ ] CLI improvements (config file support, batch export)
- [ ] Documentation (API reference, tutorials)
- [ ] Linux/Windows binary builds
- [ ] Internationalization (multi-language support)

### Low Priority
- [ ] GUI theme variations
- [ ] Web-based monitoring dashboard
- [ ] Machine learning for anomaly detection
- [ ] Cloud data synchronization

## Development Setup

```bash
# Clone repository
git clone <repo>
cd rpm-digital-twin

# Create Python environment
python3.14 -m venv venv
source venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks (optional)
pip install pre-commit
pre-commit install
```

## Code Review Checklist

Reviewers check:
- ✅ Adheres to code style (black, flake8)
- ✅ Type hints complete
- ✅ Unit tests included (>80% coverage)
- ✅ Docstrings present
- ✅ No breaking changes to public APIs
- ✅ All tests pass locally
- ✅ Performance impact assessed
- ✅ Cross-platform compatibility (Windows, macOS, Linux)

## Performance Considerations

For real-time systems, ensure:
- GUI operations complete in <100ms
- DAQ buffer operations <1ms
- Physics calculations parallelized for large datasets
- Memory usage stable (no leaks over 1-hour runtime)

Test with:
```bash
python3 -m cProfile -s cumtime src/rpm_digital_twin/cli.py
```

## Security

- No hardcoded credentials or keys
- Use environment variables for sensitive data
- Sanitize user inputs (file paths, network data)
- Review dependencies for known vulnerabilities:
  ```bash
  pip install safety
  safety check
  ```

## Questions?

- Open an issue for bugs
- Start a discussion for feature ideas
- Contact: support@space-systems.org

Thank you for maintaining our quality standards! 🚀
