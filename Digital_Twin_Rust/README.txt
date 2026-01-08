RPM Digital Twin (Rust)

This is a from-scratch Rust implementation with two modes:

1) Numerical mode (offline simulation)
   - Runs dt = 0.1s by default
   - Computes gravity in payload frame via rotation matrices
   - Computes centripetal acceleration magnitude at a chosen point
   - Computes taSMG and prints summary stats
   - Writes CSV time series

2) Live mode (connected)
   - Reads sensor packets from TCP or Serial
   - Logs raw samples to CSV and computes running stats

Build (requires Rust toolchain)

  # Install Rust if needed: https://rustup.rs
  cd Digital_Twin_Rust
  cargo build --release

Run (Numerical)

  cargo run --release -- \
    numerical --outer-rpm 10 --inner-rpm 5 --duration 120 \
    --x 0.5 --y 0.2 --z 0.0 --out out.csv

Run (Live, TCP)

  cargo run --release -- live --tcp 127.0.0.1:5005 --out live.csv

Run (Live, Serial)

  cargo run --release -- live --serial /dev/cu.usbserial-1410 --baud 115200 --out live.csv

Packet format expectations (live)

- Each sample is one line of ASCII text, comma-separated.
- Minimum supported: ax,ay,az
- Optional: omega_outer,omega_inner,timestamp
