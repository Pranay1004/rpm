mod csv;
mod live;
mod math;
mod numerical;
mod stats;

use clap::{Parser, Subcommand};

#[derive(Parser, Debug)]
#[command(name = "rpm_digital_twin_rust")]
#[command(about = "RPM Digital Twin (Rust) - numerical + live modes", long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand, Debug)]
enum Command {
    /// Offline simulation at fixed timestep (default dt=0.1s)
    Numerical {
        #[arg(long)]
        outer_rpm: f64,
        #[arg(long)]
        inner_rpm: f64,
        #[arg(long, default_value_t = 60.0)]
        duration: f64,
        #[arg(long, default_value_t = 0.1)]
        dt: f64,
        #[arg(long, default_value_t = 0.0)]
        x: f64,
        #[arg(long, default_value_t = 0.0)]
        y: f64,
        #[arg(long, default_value_t = 0.0)]
        z: f64,
        #[arg(long, default_value = "out.csv")]
        out: String,
    },

    /// Connected acquisition via TCP or Serial
    Live {
        #[arg(long, default_value = "")]
        tcp: String,
        #[arg(long, default_value = "")]
        serial: String,
        #[arg(long, default_value_t = 115200)]
        baud: u32,
        #[arg(long, default_value = "live.csv")]
        out: String,
    },
}

fn main() {
    let cli = Cli::parse();

    let exit_code = match cli.command {
        Command::Numerical {
            outer_rpm,
            inner_rpm,
            duration,
            dt,
            x,
            y,
            z,
            out,
        } => {
            let cfg = numerical::NumericalConfig {
                outer_rpm,
                inner_rpm,
                duration_s: duration,
                dt_s: dt,
                x_m: x,
                y_m: y,
                z_m: z,
                out_csv: out,
            };
            numerical::run_numerical(&cfg)
        }
        Command::Live {
            tcp,
            serial,
            baud,
            out,
        } => {
            let cfg = live::LiveConfig {
                tcp,
                serial,
                baud,
                out_csv: out,
            };
            live::run_live(&cfg)
        }
    };

    std::process::exit(exit_code);
}
