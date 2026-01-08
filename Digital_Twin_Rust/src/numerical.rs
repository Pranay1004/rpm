use crate::csv::CsvWriter;
use crate::math::{mul_mm, mul_mv, norm, rot_y, rot_z, Vec3};
use crate::stats::RunningStats;

const PI: f64 = 3.14159265358979323846;

pub struct NumericalConfig {
    pub outer_rpm: f64,
    pub inner_rpm: f64,
    pub duration_s: f64,
    pub dt_s: f64,
    pub x_m: f64,
    pub y_m: f64,
    pub z_m: f64,
    pub out_csv: String,
}

fn rpm_to_rad_s(rpm: f64) -> f64 {
    rpm * 2.0 * PI / 60.0
}

pub fn run_numerical(cfg: &NumericalConfig) -> i32 {
    let mut csv = match CsvWriter::new(&cfg.out_csv) {
        Ok(w) => w,
        Err(e) => {
            eprintln!("ERROR: cannot open output CSV: {} ({})", cfg.out_csv, e);
            return 2;
        }
    };

    let header = "t_s,theta_outer_rad,theta_inner_rad,omega_outer_rad_s,omega_inner_rad_s,gx,gy,gz,g_mag,ac_mag,tasmG_running";
    if csv.write_line(header).is_err() {
        eprintln!("ERROR: cannot write header");
        return 2;
    }

    let omega_outer = rpm_to_rad_s(cfg.outer_rpm);
    let omega_inner = rpm_to_rad_s(cfg.inner_rpm);

    let g_inertial = Vec3 { x: 0.0, y: 0.0, z: -9.81 };

    let mut gx = RunningStats::default();
    let mut sumsq_g = 0.0f64;
    let mut gmag = RunningStats::default();

    let r_xy = (cfg.x_m * cfg.x_m + cfg.y_m * cfg.y_m).sqrt();
    let ac_mag = omega_outer * omega_outer * r_xy;

    let steps = (cfg.duration_s / cfg.dt_s).floor() as u64 + 1;

    for i in 0..steps {
        let t = i as f64 * cfg.dt_s;
        let theta_outer = omega_outer * t;
        let theta_inner = omega_inner * t;

        let r = mul_mm(rot_z(theta_outer), rot_y(theta_inner));
        let g_payload = mul_mv(r, g_inertial);
        let g_mag = norm(g_payload);

        gx.push(g_payload.x);
        gmag.push(g_mag);
        sumsq_g += g_payload.x * g_payload.x + g_payload.y * g_payload.y + g_payload.z * g_payload.z;
        let tasm_running = gx.rms_from_sum_squares(sumsq_g);

        let row = format!(
            "{:.4},{:.4},{:.4},{:.4},{:.4},{:.4},{:.4},{:.4},{:.4},{:.4},{:.4}",
            t,
            theta_outer,
            theta_inner,
            omega_outer,
            omega_inner,
            g_payload.x,
            g_payload.y,
            g_payload.z,
            g_mag,
            ac_mag,
            tasm_running
        );
        if csv.write_line(&row).is_err() {
            eprintln!("ERROR: CSV write failed");
            return 2;
        }
    }

    let tasm = gx.rms_from_sum_squares(sumsq_g);

    println!("NUMERICAL MODE COMPLETE");
    println!("  dt_s: {}", cfg.dt_s);
    println!("  duration_s: {}", cfg.duration_s);
    println!("  outer_rpm: {} ({} rad/s)", cfg.outer_rpm, omega_outer);
    println!("  inner_rpm: {} ({} rad/s)", cfg.inner_rpm, omega_inner);
    println!("  point_m: ({}, {}, {})", cfg.x_m, cfg.y_m, cfg.z_m);
    println!("  centripetal_ac_mag: {} m/s^2", ac_mag);
    println!("  taSMG: {} m/s^2", tasm);
    println!("  g_mag mean: {} std: {}", gmag.mean, gmag.stddev());
    println!("  output_csv: {}", cfg.out_csv);

    0
}
