RPM Digital Twin (C++)

This is a from-scratch C++ implementation with two modes:

1) Numerical mode (offline simulation)
   - Runs the RPM kinematics/rotation-matrix math at dt = 0.1s
   - Computes gravity in payload frame, centripetal acceleration at a point,
     and aggregate microgravity metrics (taSMG + basic stats)
   - Writes a CSV time series + a summary to stdout

2) Live mode (connected)
   - Reads sensor packets from TCP or Serial
   - Logs raw samples to CSV and computes running stats

Build

  mkdir -p build
  cd build
  cmake ..
  cmake --build . -j

Run (Numerical)

  ./build/rpm_digital_twin_cpp \
    numerical --outer-rpm 10 --inner-rpm 5 --duration 120 \
    --x 0.5 --y 0.2 --z 0.0 --out out.csv

Run (Live, TCP)

  ./build/rpm_digital_twin_cpp live --tcp 127.0.0.1:5005 --out live.csv

Run (Live, Serial)

  ./build/rpm_digital_twin_cpp live --serial /dev/cu.usbserial-1410 --baud 115200 --out live.csv

Packet format expectations (live)

- Each sample is one line of ASCII text, comma-separated.
- Minimum supported: ax,ay,az
- Optional: omega_outer,omega_inner,timestamp

Examples:
  0.01,0.02,-9.80
  0.01,0.02,-9.80,1.0,0.5,1700000000.123
