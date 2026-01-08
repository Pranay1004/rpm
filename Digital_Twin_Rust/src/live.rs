use crate::csv::CsvWriter;
use crate::stats::RunningStats;

use std::io::{BufRead, BufReader};
use std::net::TcpStream;

pub struct LiveConfig {
    pub tcp: String,
    pub serial: String,
    pub baud: u32,
    pub out_csv: String,
}

fn parse_min3(line: &str) -> Option<(f64, f64, f64)> {
    let mut vals = Vec::new();
    for part in line.split(',') {
        let p = part.trim();
        if p.is_empty() {
            continue;
        }
        let v: f64 = p.parse().ok()?;
        vals.push(v);
    }
    if vals.len() < 3 {
        None
    } else {
        Some((vals[0], vals[1], vals[2]))
    }
}

pub fn run_live(cfg: &LiveConfig) -> i32 {
    let use_tcp = !cfg.tcp.is_empty();
    let use_serial = !cfg.serial.is_empty();
    if use_tcp == use_serial {
        eprintln!("ERROR: choose exactly one of --tcp or --serial");
        return 2;
    }

    let mut csv = match CsvWriter::new(&cfg.out_csv) {
        Ok(w) => w,
        Err(e) => {
            eprintln!("ERROR: cannot open output CSV: {} ({})", cfg.out_csv, e);
            return 2;
        }
    };
    let _ = csv.write_line("ax,ay,az");

    let mut axs = RunningStats::default();
    let mut ays = RunningStats::default();
    let mut azs = RunningStats::default();

    let mut lines_ok: u64 = 0;
    let mut lines_bad: u64 = 0;

    if use_tcp {
        println!("LIVE MODE (TCP) connecting to {}", cfg.tcp);
        let stream = match TcpStream::connect(&cfg.tcp) {
            Ok(s) => s,
            Err(e) => {
                eprintln!("ERROR: TCP connect failed: {}", e);
                return 3;
            }
        };

        let reader = BufReader::new(stream);
        println!("Streaming... (Ctrl+C to stop)");

        for line in reader.lines() {
            let line = match line {
                Ok(l) => l,
                Err(_) => break,
            };

            let (ax, ay, az) = match parse_min3(&line) {
                Some(v) => v,
                None => {
                    lines_bad += 1;
                    continue;
                }
            };

            lines_ok += 1;
            axs.push(ax);
            ays.push(ay);
            azs.push(az);

            let _ = csv.write_line(&format!("{},{},{}", ax, ay, az));

            if lines_ok % 100 == 0 {
                println!(
                    "samples={} bad={} mean(ax,ay,az)=({:.4},{:.4},{:.4}) std(ax,ay,az)=({:.4},{:.4},{:.4})",
                    lines_ok,
                    lines_bad,
                    axs.mean,
                    ays.mean,
                    azs.mean,
                    axs.stddev(),
                    ays.stddev(),
                    azs.stddev()
                );
            }
        }

        return 0;
    }

    // Serial via serialport crate
    println!("LIVE MODE (Serial) opening {} @ {}", cfg.serial, cfg.baud);
    let port = match serialport::new(&cfg.serial, cfg.baud).timeout(std::time::Duration::from_millis(250)).open() {
        Ok(p) => p,
        Err(e) => {
            eprintln!("ERROR: serial open failed: {}", e);
            return 3;
        }
    };

    let mut reader = BufReader::new(port);
    println!("Streaming... (Ctrl+C to stop)");

    loop {
        let mut line = String::new();
        match reader.read_line(&mut line) {
            Ok(0) => continue,
            Ok(_) => {}
            Err(_) => continue,
        }

        let (ax, ay, az) = match parse_min3(line.trim()) {
            Some(v) => v,
            None => {
                lines_bad += 1;
                continue;
            }
        };

        lines_ok += 1;
        axs.push(ax);
        ays.push(ay);
        azs.push(az);
        let _ = csv.write_line(&format!("{},{},{}", ax, ay, az));

        if lines_ok % 100 == 0 {
            println!(
                "samples={} bad={} mean(ax,ay,az)=({:.4},{:.4},{:.4}) std(ax,ay,az)=({:.4},{:.4},{:.4})",
                lines_ok,
                lines_bad,
                axs.mean,
                ays.mean,
                azs.mean,
                axs.stddev(),
                ays.stddev(),
                azs.stddev()
            );
        }
    }
}
