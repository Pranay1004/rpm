/**
 * IIST RPM Digital Twin v2.0 - Scientific Controller & Instrumentation.
 * Handles 50Hz physics, CAD rendering, CSV logging, and scientific white-bg plots.
 */

class RPMScientificApp {
    constructor() {
        this.isRunning = true;
        this.dt = 0.02; // 50 Hz

        // Kinematics & Mechanics
        this.phi_deg = 0.0;
        this.psi_deg = 0.0;
        this.omega_phi_rpm = 2.0;
        this.omega_psi_rpm = 2.292;
        this.target_omega_phi = 2.0;
        this.target_omega_psi = 2.292;
        this.base_inner_rpm = 2.0;
        this.base_outer_rpm = 2.0;

        // Acceleration limit (10 rad/s^2 per Slide 9/11) ~ 95.5 RPM/s
        this.max_alpha_rpm_s = 95.5;

        // Trajectory mode
        this.operation_mode = 'clinostat_optimal';
        this.chamber_radius_m = 0.06; // 6 cm (chamber radius)

        // Stochastic state (Pica 2026)
        this.stochastic_timer = 0.0;
        this.next_stochastic_switch = 25.0;
        this.direction_changes_count = 0;

        // Statistics
        this.elapsed_time = 0.0;
        this.samples = 0;
        this.sum_gx = 0.0;
        this.sum_gy = 0.0;
        this.sum_gz = 0.0;
        this.min_g = 1.0;
        this.max_g = 1.0;

        // 1D Navier-Stokes FDM
        this.fluid_N = 25;
        this.fluid_u = new Float64Array(this.fluid_N);
        this.fluid_nu = 1.004e-6; // m^2/s
        this.fluid_mu = 1.002e-3; // Pa.s
        this.last_shear_stress = 0.0;
        this.stokes_delta_mm = 0.0;

        // Telemetry history for CSV export
        this.telemetry_history = [];
        this.max_history_records = 20000;

        // Plot history buffers
        this.plot_time = [];
        this.plot_gx = [];
        this.plot_gy = [];
        this.plot_gz = [];
        this.plot_tasmg = [];
        this.max_plot_points = 250;

        // Web Serial
        this.serialPort = null;
        this.serialReader = null;
        this.serialConnected = false;
        this.lastHwG = null;

        // Three.js instances
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.cadAssembly = null;

        this.init();
    }

    init() {
        this.init3D();
        this.initPlots();
        this.bindEvents();
        this.updateModeUI();

        // 50 Hz Physics Interval
        setInterval(() => this.step(this.dt), 20);
    }

    init3D() {
        const container = document.getElementById('cad-canvas-container');
        if (!container) return;

        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0xf8fafc); // Clean laboratory light background

        this.camera = new THREE.PerspectiveCamera(40, container.clientWidth / container.clientHeight, 0.05, 50);
        this.camera.position.set(1.4, 1.1, 1.6);
        this.camera.lookAt(0.0, 0.45, 0.0);

        this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
        this.renderer.setSize(container.clientWidth, container.clientHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio || 1);
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        container.appendChild(this.renderer.domElement);

        // Lighting (Clean engineering laboratory lighting)
        const hemiLight = new THREE.HemisphereLight(0xffffff, 0xe2e8f0, 0.85);
        this.scene.add(hemiLight);

        const dirLight = new THREE.DirectionalLight(0xffffff, 0.7);
        dirLight.position.set(2.5, 4.0, 3.0);
        dirLight.castShadow = true;
        dirLight.shadow.mapSize.width = 2048;
        dirLight.shadow.mapSize.height = 2048;
        this.scene.add(dirLight);

        const backLight = new THREE.DirectionalLight(0x94a3b8, 0.3);
        backLight.position.set(-2.5, 2.0, -2.0);
        this.scene.add(backLight);

        // Grid plane on floor
        const grid = new THREE.GridHelper(2.0, 20, 0xcbd5e1, 0xe2e8f0);
        grid.position.y = 0.0;
        this.scene.add(grid);

        // Build exact CAD assembly from Final_Drawing.pdf
        this.cadAssembly = new RPMCadAssembly(this.scene);

        // Mouse orbit controls
        this.setupOrbitInteraction(container);

        // Animation loop
        const animate = () => {
            requestAnimationFrame(animate);
            this.renderer.render(this.scene, this.camera);
        };
        animate();

        window.addEventListener('resize', () => {
            if (!container) return;
            this.camera.aspect = container.clientWidth / container.clientHeight;
            this.camera.updateProjectionMatrix();
            this.renderer.setSize(container.clientWidth, container.clientHeight);
        });
    }

    setupOrbitInteraction(elem) {
        let isDragging = false;
        let prevX = 0, prevY = 0;
        let rotY = 0.7, rotX = 0.4;
        let dist = 2.4;

        elem.addEventListener('mousedown', (e) => {
            isDragging = true;
            prevX = e.clientX;
            prevY = e.clientY;
        });

        window.addEventListener('mouseup', () => isDragging = false);

        window.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            const deltaX = e.clientX - prevX;
            const deltaY = e.clientY - prevY;
            prevX = e.clientX;
            prevY = e.clientY;

            rotY -= deltaX * 0.008;
            rotX = Math.max(-0.2, Math.min(1.4, rotX + deltaY * 0.008));

            this.updateCameraOrbit(rotX, rotY, dist);
        });

        elem.addEventListener('wheel', (e) => {
            e.preventDefault();
            dist = Math.max(0.8, Math.min(5.0, dist + e.deltaY * 0.002));
            this.updateCameraOrbit(rotX, rotY, dist);
        });

        this.updateCameraOrbit(rotX, rotY, dist);
    }

    updateCameraOrbit(rotX, rotY, dist) {
        const targetY = 0.45;
        this.camera.position.x = dist * Math.sin(rotY) * Math.cos(rotX);
        this.camera.position.y = targetY + dist * Math.sin(rotX);
        this.camera.position.z = dist * Math.cos(rotY) * Math.cos(rotX);
        this.camera.lookAt(0.0, targetY, 0.0);
    }

    initPlots() {
        // 1. Time-series Canvas (Clean white background, scientific styling)
        const tsCtx = document.getElementById('timeseries-canvas').getContext('2d');
        this.tsChart = new Chart(tsCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    { label: 'Gx (g)', data: [], borderColor: '#dc2626', borderWidth: 1.5, pointRadius: 0, fill: false },
                    { label: 'Gy (g)', data: [], borderColor: '#2563eb', borderWidth: 1.5, pointRadius: 0, fill: false },
                    { label: 'Gz (g)', data: [], borderColor: '#059669', borderWidth: 1.5, pointRadius: 0, fill: false },
                    { label: '<g> taSMG', data: [], borderColor: '#0f172a', borderWidth: 2.0, borderDash: [4, 4], pointRadius: 0, fill: false }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                scales: {
                    x: {
                        grid: { color: '#f1f5f9' },
                        ticks: { color: '#475569', font: { size: 10, family: 'sans-serif' } },
                        title: { display: true, text: 'Time (s)', color: '#334155', font: { size: 11, weight: 'bold' } }
                    },
                    y: {
                        min: -1.2,
                        max: 1.2,
                        grid: { color: '#e2e8f0' },
                        ticks: { color: '#475569', font: { size: 10 } },
                        title: { display: true, text: 'Acceleration (g)', color: '#334155', font: { size: 11, weight: 'bold' } }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: { boxWidth: 12, font: { size: 11, weight: '600' }, color: '#0f172a' }
                    }
                }
            }
        });

        // 2. FDM Fluid Velocity Profile Canvas
        const fdmCtx = document.getElementById('fdm-canvas').getContext('2d');
        this.fdmChart = new Chart(fdmCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    { label: 'u_θ (mm/s)', data: [], borderColor: '#1e3a8a', backgroundColor: 'rgba(30, 58, 138, 0.08)', fill: true, borderWidth: 1.8, pointRadius: 0 }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                scales: {
                    x: {
                        grid: { color: '#f1f5f9' },
                        ticks: { color: '#475569', font: { size: 10 } },
                        title: { display: true, text: 'Radius r (cm)', color: '#334155', font: { size: 11, weight: 'bold' } }
                    },
                    y: {
                        min: 0,
                        grid: { color: '#e2e8f0' },
                        ticks: { color: '#475569', font: { size: 10 } },
                        title: { display: true, text: 'Velocity (mm/s)', color: '#334155', font: { size: 11, weight: 'bold' } }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }

    bindEvents() {
        document.getElementById('mode-select').addEventListener('change', (e) => {
            this.setMode(e.target.value);
        });

        document.getElementById('inner-rpm-slider').addEventListener('input', (e) => {
            const val = parseFloat(e.target.value);
            document.getElementById('inner-rpm-val').textContent = val.toFixed(1) + ' RPM';
            this.base_inner_rpm = val;
            this.updateTargetSpeeds();
        });

        document.getElementById('outer-rpm-slider').addEventListener('input', (e) => {
            const val = parseFloat(e.target.value);
            document.getElementById('outer-rpm-val').textContent = val.toFixed(1) + ' RPM';
            this.base_outer_rpm = val;
            this.updateTargetSpeeds();
        });

        document.getElementById('chamber-radius-slider').addEventListener('input', (e) => {
            const val = parseFloat(e.target.value);
            document.getElementById('chamber-radius-val').textContent = val.toFixed(1) + ' cm';
            this.chamber_radius_m = val / 100.0;
            this.fluid_u.fill(0);
        });

        document.getElementById('btn-start').addEventListener('click', () => this.isRunning = true);
        document.getElementById('btn-stop').addEventListener('click', () => this.isRunning = false);
        document.getElementById('btn-reset').addEventListener('click', () => this.reset());

        document.getElementById('btn-export-csv').addEventListener('click', () => this.exportCSV());
        document.getElementById('btn-export-plot').addEventListener('click', () => this.exportPlot());
    }

    setMode(mode) {
        this.operation_mode = mode;
        this.updateTargetSpeeds();
        this.updateModeUI();
    }

    updateTargetSpeeds() {
        if (this.operation_mode === 'clinostat_optimal') {
            this.target_omega_phi = this.base_inner_rpm;
            this.target_omega_psi = this.base_inner_rpm * 1.146; // Kim et al. 2026
        } else if (this.operation_mode === 'clinostat_3d') {
            this.target_omega_phi = this.base_inner_rpm;
            this.target_omega_psi = this.base_outer_rpm;
        } else if (this.operation_mode === 'rpm_stochastic') {
            this.stochastic_timer = 0.0;
            this.next_stochastic_switch = 20.0 + Math.random() * 25.0;
            this.triggerStochasticStep();
        }
    }

    triggerStochasticStep() {
        const factorPhi = (0.80 + Math.random() * 0.20) * (Math.random() > 0.5 ? 1.0 : -1.0);
        const factorPsi = (0.80 + Math.random() * 0.20) * (Math.random() > 0.5 ? 1.0 : -1.0);
        this.target_omega_phi = this.base_inner_rpm * factorPhi;
        this.target_omega_psi = this.base_outer_rpm * factorPsi;
        this.direction_changes_count++;
    }

    updateModeUI() {
        const descEl = document.getElementById('mode-description');
        if (!descEl) return;
        if (this.operation_mode === 'clinostat_optimal') {
            descEl.innerHTML = '<strong>Kim et al. (npj Microgravity 2026):</strong> Non-harmonic velocity ratio γ = 1.146 (e.g. 2.0 / 2.292 RPM) achieving uniform S² ergodicity and pole-avoidance.';
        } else if (this.operation_mode === 'clinostat_3d') {
            descEl.innerHTML = '<strong>Standard 3D Clinostat:</strong> Constant rotation speeds producing predictable periodic Lissajous loops on S².';
        } else if (this.operation_mode === 'rpm_stochastic') {
            descEl.innerHTML = '<strong>Pica et al. (PLOS ONE 2026) Mode A:</strong> Stochastic zero-crossing reversals every 20-45 s canceling angular momentum bias.';
        }
    }

    reset() {
        this.phi_deg = 0.0;
        this.psi_deg = 0.0;
        this.elapsed_time = 0.0;
        this.samples = 0;
        this.sum_gx = 0.0;
        this.sum_gy = 0.0;
        this.sum_gz = 0.0;
        this.min_g = 1.0;
        this.max_g = 1.0;
        this.direction_changes_count = 0;
        this.fluid_u.fill(0);
        this.telemetry_history = [];
        this.plot_time = [];
        this.plot_gx = [];
        this.plot_gy = [];
        this.plot_gz = [];
        this.plot_tasmg = [];
    }

    step(dt) {
        if (!this.isRunning) return;

        this.elapsed_time += dt;

        // Mode logic
        if (this.operation_mode === 'rpm_stochastic') {
            this.stochastic_timer += dt;
            if (this.stochastic_timer >= this.next_stochastic_switch) {
                this.stochastic_timer = 0.0;
                this.next_stochastic_switch = 20.0 + Math.random() * 25.0;
                this.triggerStochasticStep();
            }
        }

        // Motor torque acceleration ramping (max alpha = 95.5 RPM/s)
        const maxStep = this.max_alpha_rpm_s * dt;
        const dPhi = this.target_omega_phi - this.omega_phi_rpm;
        if (Math.abs(dPhi) <= maxStep) this.omega_phi_rpm = this.target_omega_phi;
        else this.omega_phi_rpm += Math.sign(dPhi) * maxStep;

        const dPsi = this.target_omega_psi - this.omega_psi_rpm;
        if (Math.abs(dPsi) <= maxStep) this.omega_psi_rpm = this.target_omega_psi;
        else this.omega_psi_rpm += Math.sign(dPsi) * maxStep;

        // Gimbal angles integration (1 RPM = 6 deg/sec)
        this.phi_deg = (this.phi_deg + this.omega_phi_rpm * 6.0 * dt) % 360.0;
        if (this.phi_deg < 0) this.phi_deg += 360.0;
        this.psi_deg = (this.psi_deg + this.omega_psi_rpm * 6.0 * dt) % 360.0;
        if (this.psi_deg < 0) this.psi_deg += 360.0;

        // Yotov et al. (2022) Equations (1)-(2)
        const phi_rad = this.phi_deg * Math.PI / 180.0;
        const psi_rad = this.psi_deg * Math.PI / 180.0;
        const gx = -Math.sin(phi_rad) * Math.cos(psi_rad);
        const gy =  Math.sin(phi_rad) * Math.sin(psi_rad);
        const gz =  Math.cos(phi_rad);
        const inst_g = Math.sqrt(gx * gx + gy * gy + gz * gz);

        // Cumulative taSMG
        this.samples++;
        this.sum_gx += gx;
        this.sum_gy += gy;
        this.sum_gz += gz;
        const avg_gx = this.sum_gx / this.samples;
        const avg_gy = this.sum_gy / this.samples;
        const avg_gz = this.sum_gz / this.samples;
        const tasmg = Math.sqrt(avg_gx * avg_gx + avg_gy * avg_gy + avg_gz * avg_gz);

        // Wadhwa et al. (2026) Volumetric Accelerations
        const omega_phi_rad_s = (this.omega_phi_rpm * 2.0 * Math.PI) / 60.0;
        const omega_psi_rad_s = (this.omega_psi_rpm * 2.0 * Math.PI) / 60.0;
        const omega_norm = Math.sqrt(omega_phi_rad_s**2 + omega_psi_rad_s**2);
        const g0 = 9.80665;

        // Safe radius threshold r_safe = (10^-3 * g0) / ||omega||^2
        const r_safe_cm = (0.001 * g0) / (omega_norm**2 + 1e-12) * 100.0;

        // Centrifugal acceleration at boundary
        const a_cent_edge_g = (omega_norm**2 * this.chamber_radius_m) / g0;

        // Hasenstein & van Loon (2015) 1D Navier-Stokes FDM
        const dr = this.chamber_radius_m / (this.fluid_N - 1);
        const u_wall = omega_norm * this.chamber_radius_m;
        const u_new = new Float64Array(this.fluid_N);

        for (let i = 1; i < this.fluid_N - 1; i++) {
            const r_i = i * dr;
            const d2u = (this.fluid_u[i + 1] - 2.0 * this.fluid_u[i] + this.fluid_u[i - 1]) / (dr * dr);
            const du = (this.fluid_u[i + 1] - this.fluid_u[i - 1]) / (2.0 * dr);
            u_new[i] = this.fluid_u[i] + dt * this.fluid_nu * (d2u + (1.0 / r_i) * du - (this.fluid_u[i] / (r_i * r_i)));
        }
        u_new[0] = 0.0;
        u_new[this.fluid_N - 1] = u_wall;
        this.fluid_u.set(u_new);

        // Wall shear stress
        const du_dr_wall = (this.fluid_u[this.fluid_N - 1] - this.fluid_u[this.fluid_N - 2]) / dr;
        this.last_shear_stress = this.fluid_mu * Math.abs(du_dr_wall - (this.fluid_u[this.fluid_N - 1] / this.chamber_radius_m)) * 1000.0;

        // Stokes boundary layer
        this.stokes_delta_mm = omega_norm > 1e-4 ? Math.sqrt(2.0 * this.fluid_nu / omega_norm) * 1000.0 : (this.chamber_radius_m * 1000.0);

        // Update CAD Model
        if (this.cadAssembly) {
            this.cadAssembly.updateRotations(this.phi_deg, this.psi_deg);
        }

        // Log record for CSV
        if (this.telemetry_history.length < this.max_history_records) {
            this.telemetry_history.push({
                time: this.elapsed_time,
                phi: this.phi_deg,
                psi: this.psi_deg,
                omega_phi: this.omega_phi_rpm,
                omega_psi: this.omega_psi_rpm,
                gx: gx,
                gy: gy,
                gz: gz,
                inst_g: inst_g,
                tasmg: tasmg,
                cent_edge: a_cent_edge_g,
                shear_mPa: this.last_shear_stress
            });
        }

        // Plot buffers
        this.plot_time.push(this.elapsed_time.toFixed(1));
        this.plot_gx.push(gx);
        this.plot_gy.push(gy);
        this.plot_gz.push(gz);
        this.plot_tasmg.push(tasmg);

        if (this.plot_time.length > this.max_plot_points) {
            this.plot_time.shift();
            this.plot_gx.shift();
            this.plot_gy.shift();
            this.plot_gz.shift();
            this.plot_tasmg.shift();
        }

        // Update UI every 5 steps (10 Hz refresh)
        if (this.samples % 5 === 0) {
            this.updateTelemetryDOM(tasmg, inst_g, a_cent_edge_g, r_safe_cm, this.last_shear_stress);
            this.updateCharts();
        }
    }

    updateTelemetryDOM(tasmg, inst_g, a_cent, r_safe, shear_mPa) {
        document.getElementById('metric-tasmg').textContent = tasmg.toFixed(4) + ' g';
        document.getElementById('metric-inst-g').textContent = inst_g.toFixed(3) + ' g';
        document.getElementById('metric-centrifugal').textContent = a_cent.toFixed(5) + ' g';
        document.getElementById('metric-safe-radius').textContent = r_safe.toFixed(1) + ' cm';
        document.getElementById('metric-shear').textContent = shear_mPa.toFixed(2) + ' mPa';
        document.getElementById('metric-samples').textContent = this.samples.toLocaleString();

        document.getElementById('display-phi').textContent = this.phi_deg.toFixed(1) + '°';
        document.getElementById('display-psi').textContent = this.psi_deg.toFixed(1) + '°';
        document.getElementById('display-omega-phi').textContent = this.omega_phi_rpm.toFixed(2) + ' RPM';
        document.getElementById('display-omega-psi').textContent = this.omega_psi_rpm.toFixed(2) + ' RPM';
    }

    updateCharts() {
        if (!this.tsChart || !this.fdmChart) return;

        // Update Time-Series
        this.tsChart.data.labels = this.plot_time;
        this.tsChart.data.datasets[0].data = this.plot_gx;
        this.tsChart.data.datasets[1].data = this.plot_gy;
        this.tsChart.data.datasets[2].data = this.plot_gz;
        this.tsChart.data.datasets[3].data = this.plot_tasmg;
        this.tsChart.update('none');

        // Update FDM
        const rLabels = [];
        const uVals = [];
        const dr = (this.chamber_radius_m * 100.0) / (this.fluid_N - 1);
        for (let i = 0; i < this.fluid_N; i++) {
            rLabels.push((i * dr).toFixed(1));
            uVals.push((this.fluid_u[i] * 1000.0).toFixed(2));
        }
        this.fdmChart.data.labels = rLabels;
        this.fdmChart.data.datasets[0].data = uVals;
        this.fdmChart.update('none');
    }

    exportCSV() {
        if (this.telemetry_history.length === 0) {
            alert('No simulation records logged yet.');
            return;
        }

        const lines = [];
        lines.push('# =====================================================================');
        lines.push('# INDIAN INSTITUTE OF SPACE SCIENCE AND TECHNOLOGY (IIST)');
        lines.push('# Department of Aerospace Engineering - Microgravity Simulation Laboratory');
        lines.push('# Project: Random Positioning Machine (RPM) Digital Twin v2.0');
        lines.push(`# Date: ${new Date().toISOString()}`);
        lines.push(`# Operation Mode: ${this.operation_mode}`);
        lines.push('# CAD Model: Final_Drawing.pdf (Outer 500mm, Inner 350mm, Payload 200mm)');
        lines.push(`# Chamber Radius: ${(this.chamber_radius_m * 100.0).toFixed(1)} cm`);
        lines.push('# =====================================================================');
        lines.push('timestamp_s,phi_deg,psi_deg,omega_phi_rpm,omega_psi_rpm,gx_g,gy_g,gz_g,inst_g,taSMG_g,centrifugal_edge_g,wall_shear_stress_mPa');

        for (const r of this.telemetry_history) {
            lines.push([
                r.time.toFixed(3),
                r.phi.toFixed(2),
                r.psi.toFixed(2),
                r.omega_phi.toFixed(3),
                r.omega_psi.toFixed(3),
                r.gx.toFixed(4),
                r.gy.toFixed(4),
                r.gz.toFixed(4),
                r.inst_g.toFixed(4),
                r.tasmg.toFixed(5),
                r.cent_edge.toFixed(5),
                r.shear_mPa.toFixed(2)
            ].join(','));
        }

        const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `iist_rpm_telemetry_${Date.now()}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }

    exportPlot() {
        const canvas = document.getElementById('timeseries-canvas');
        if (!canvas) return;

        // Render to temporary canvas with solid white background
        const exportCanvas = document.createElement('canvas');
        exportCanvas.width = canvas.width;
        exportCanvas.height = canvas.height;
        const ctx = exportCanvas.getContext('2d');
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, exportCanvas.width, exportCanvas.height);
        ctx.drawImage(canvas, 0, 0);

        const imgURL = exportCanvas.toDataURL('image/png');
        const link = document.createElement('a');
        link.href = imgURL;
        link.setAttribute('download', `iist_rpm_plot_${Date.now()}.png`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

// Modal controls
function toggleCitationsModal(show) {
    const el = document.getElementById('citations-modal');
    if (el) el.classList.toggle('active', show);
}

window.addEventListener('load', () => {
    window.app = new RPMScientificApp();
});
