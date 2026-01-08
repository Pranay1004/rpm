#[derive(Debug, Default, Clone, Copy)]
pub struct RunningStats {
    pub n: u64,
    pub mean: f64,
    pub m2: f64,
}

impl RunningStats {
    pub fn push(&mut self, x: f64) {
        self.n += 1;
        let delta = x - self.mean;
        self.mean += delta / self.n as f64;
        let delta2 = x - self.mean;
        self.m2 += delta * delta2;
    }

    pub fn variance(&self) -> f64 {
        if self.n < 2 {
            0.0
        } else {
            self.m2 / (self.n as f64 - 1.0)
        }
    }

    pub fn stddev(&self) -> f64 {
        self.variance().sqrt()
    }

    pub fn rms_from_sum_squares(&self, sumsq: f64) -> f64 {
        if self.n == 0 {
            0.0
        } else {
            (sumsq / self.n as f64).sqrt()
        }
    }
}
