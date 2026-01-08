#[derive(Clone, Copy, Debug, Default)]
pub struct Vec3 {
    pub x: f64,
    pub y: f64,
    pub z: f64,
}

#[derive(Clone, Copy, Debug, Default)]
pub struct Mat3 {
    // Row-major 3x3
    pub m: [f64; 9],
}

impl Mat3 {
    pub fn at(&self, r: usize, c: usize) -> f64 {
        self.m[r * 3 + c]
    }

    pub fn at_mut(&mut self, r: usize, c: usize) -> &mut f64 {
        &mut self.m[r * 3 + c]
    }
}

pub fn rot_z(theta: f64) -> Mat3 {
    let c = theta.cos();
    let s = theta.sin();

    let mut r = Mat3::default();
    *r.at_mut(0, 0) = c;
    *r.at_mut(0, 1) = -s;
    *r.at_mut(0, 2) = 0.0;

    *r.at_mut(1, 0) = s;
    *r.at_mut(1, 1) = c;
    *r.at_mut(1, 2) = 0.0;

    *r.at_mut(2, 0) = 0.0;
    *r.at_mut(2, 1) = 0.0;
    *r.at_mut(2, 2) = 1.0;
    r
}

pub fn rot_y(theta: f64) -> Mat3 {
    let c = theta.cos();
    let s = theta.sin();

    let mut r = Mat3::default();
    *r.at_mut(0, 0) = c;
    *r.at_mut(0, 1) = 0.0;
    *r.at_mut(0, 2) = s;

    *r.at_mut(1, 0) = 0.0;
    *r.at_mut(1, 1) = 1.0;
    *r.at_mut(1, 2) = 0.0;

    *r.at_mut(2, 0) = -s;
    *r.at_mut(2, 1) = 0.0;
    *r.at_mut(2, 2) = c;
    r
}

pub fn mul_mm(a: Mat3, b: Mat3) -> Mat3 {
    let mut r = Mat3::default();
    for i in 0..3 {
        for j in 0..3 {
            let mut acc = 0.0;
            for k in 0..3 {
                acc += a.at(i, k) * b.at(k, j);
            }
            *r.at_mut(i, j) = acc;
        }
    }
    r
}

pub fn mul_mv(a: Mat3, v: Vec3) -> Vec3 {
    Vec3 {
        x: a.at(0, 0) * v.x + a.at(0, 1) * v.y + a.at(0, 2) * v.z,
        y: a.at(1, 0) * v.x + a.at(1, 1) * v.y + a.at(1, 2) * v.z,
        z: a.at(2, 0) * v.x + a.at(2, 1) * v.y + a.at(2, 2) * v.z,
    }
}

pub fn norm(v: Vec3) -> f64 {
    (v.x * v.x + v.y * v.y + v.z * v.z).sqrt()
}
