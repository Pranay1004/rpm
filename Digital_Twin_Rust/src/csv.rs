use std::fs::File;
use std::io::{BufWriter, Write};

pub struct CsvWriter {
    w: BufWriter<File>,
}

impl CsvWriter {
    pub fn new(path: &str) -> std::io::Result<Self> {
        let f = File::create(path)?;
        Ok(Self {
            w: BufWriter::new(f),
        })
    }

    pub fn write_line(&mut self, line: &str) -> std::io::Result<()> {
        self.w.write_all(line.as_bytes())?;
        self.w.write_all(b"\n")?;
        Ok(())
    }
}
