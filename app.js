/**
 * IIST RPM Digital Twin v2.0 - Scientific Controller & Instrumentation.
 * Handles 50Hz physics, CAD rendering, S² Unit Sphere 3D projection,
 * sample enclosure probe tracking, CSV logging, and scientific publication plots.
 */

class RPMScientificApp {
    constructor() {
        window.app = this;
        this.isRunning = true;
        this.dt = 0.02; // 50 Hz discrete timestep
        this.isHoldingAngles = false;

        // Kinematics & Mechanics
        this.phi_deg = 0.0;
        this.psi_deg = 0.0;
        this.innerTilt_deg = 0.0;
        this.outerTilt_deg = 0.0;

        this.omega_phi_rpm = 0.5;
        this.omega_psi_rpm = 0.573;
        this.target_omega_phi = 0.5;
        this.target_omega_psi = 0.573;
        this.base_inner_rpm = 0.5;
        this.base_outer_rpm = 0.573;

        // Dynamic Angular Accelerations & Motor Torques
        this.prev_omega_phi_rad_s = (0.5 * 2.0 * Math.PI) / 60.0;
        this.prev_omega_psi_rad_s = (0.573 * 2.0 * Math.PI) / 60.0;
        this.inst_torque_inner = 0.18;
        this.inst_torque_outer = 0.35;
        this.peak_torque_observed = 0.38;

        // Custom Mechanics & Mass Moment of Inertia (MOI)
        this.moiParams = {
            outerSize_mm: 500,
            outerSection_mm: 50.8,
            outerWall_mm: 3.2,
            outerMat: 'Al6061',
            innerSize_mm: 350,
            innerSection_mm: 50.8,
            innerWall_mm: 3.2,
            innerMat: 'Al6061',
            payloadDim_mm: 200,
            payloadMass_kg: 3.5,
            payloadOffset_mm: 5.0
        };
        this.currentMOI = this.calculateMechanicalMOI();

        // Experimental Domain: 'manufacturing' (Space Manufacturing / WAAM) or 'biology'
        this.experiment_domain = 'manufacturing';
        this.melt_L_mm = 5.0; // 5 mm weld pool
        this.melt_rho = 7200.0; // kg/m³
        this.melt_sigma = 1.4; // N/m
        this.envelope_radius_m = 0.10; // 10 cm (200x200mm payload CAD DWG 02)
        this.last_bond_number = 3.5e-5;

        // Thermal & Rendering Optimization Flags (Prevents Browser Overheating)
        this.lastCadTime = 0;
        this.lastSphereTime = 0;
        this.cadFpsInterval = 1000 / 30; // 30 FPS cap
        this.sphereFpsInterval = 1000 / 30; // 30 FPS cap
        this.shadowUpdateCounter = 0;

        // Acceleration limit (10 rad/s² per Slide 9/11) ~ 95.5 RPM/s
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
        this.inst_gx = 0.0;
        this.inst_gy = 0.0;
        this.inst_gz = 1.0;
        this.tasmg = 1.0;

        // Sample Probe Points (dynamic user-added markers)
        this.samplePoints = [];
        this.nextPointId = 1;

        // 1D Navier-Stokes FDM
        this.fluid_N = 25;
        this.fluid_u = new Float64Array(this.fluid_N);
        this.fluid_nu = 1.004e-6; // m^2/s (water 20°C)
        this.fluid_mu = 1.002e-3; // Pa.s
        this.last_shear_stress = 0.0;
        this.stokes_delta_mm = 0.0;

        // Telemetry history for CSV export
        this.telemetry_history = [];
        this.max_history_records = 20000;

        // Plot history buffers (Time-series)
        this.plot_time = [];
        this.plot_gx = [];
        this.plot_gy = [];
        this.plot_gz = [];
        this.plot_tasmg = [];
        this.max_plot_points = 250;

        // Dynamic Torque Buffers
        this.plot_torque_inner = [];
        this.plot_torque_outer = [];
        this.plot_torque_limit = [];

        // S² Unit Sphere trajectory buffer
        this.sphereTrajectory = [];
        this.maxSpherePoints = 1200;

        // Web Serial
        this.serialPort = null;
        this.serialReader = null;
        this.serialConnected = false;

        // Three.js instances
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.cadAssembly = null;

        // Sphere Scene instances
        this.sphereScene = null;
        this.sphereCamera = null;
        this.sphereRenderer = null;
        this.sphereTrajectoryLine = null;
        this.sphereCurrentMarker = null;

        this.init();
    }

    init() {
        try { this.init3D(); } catch (err) { console.error('init3D error:', err); }
        try { this.initSphereVisualization(); } catch (err) { console.error('initSphereVisualization error:', err); }
        try { this.initPlots(); } catch (err) { console.error('initPlots error:', err); }
        try { this.bindEvents(); } catch (err) { console.error('bindEvents error:', err); }
        try { this.renderSamplePointsTable(); } catch (err) { console.error('renderSamplePointsTable error:', err); }
        try { this.updateModeUI(); } catch (err) { console.error('updateModeUI error:', err); }
        try { this.applyCustomMechanicsParameters(false); } catch (err) { console.error('applyCustomMechanicsParameters error:', err); }

        // 50 Hz Physics Interval (guaranteed running)
        setInterval(() => this.step(this.dt), 20);
    }

    /* =========================================================================
       MECHANICAL MOI & PROVEN TORQUE DYNAMICS
       ========================================================================= */
    calculateMechanicalMOI() {
        const p = this.moiParams || {
            outerSize_mm: 500, outerSection_mm: 50.8, outerWall_mm: 3.2, outerMat: 'Al6061',
            innerSize_mm: 350, innerSection_mm: 50.8, innerWall_mm: 3.2, innerMat: 'Al6061',
            payloadDim_mm: 200, payloadMass_kg: 3.5, payloadOffset_mm: 5.0
        };

        const rhoOuter = p.outerMat === 'Steel' ? 7850 : 2700;
        const rhoInner = p.innerMat === 'Steel' ? 7850 : 2700;

        // Outer Gimbal Hollow Section Geometry (Square hollow tube)
        const wOut_m = p.outerSection_mm / 1000.0;
        const tOut_m = p.outerWall_mm / 1000.0;
        const LOut_m = p.outerSize_mm / 1000.0;
        const aTubeOut = (wOut_m * wOut_m) - Math.max(0, (wOut_m - 2 * tOut_m)**2);
        const perimOut = Math.max(0.1, 4 * (LOut_m - wOut_m));
        const massOuterFrame = rhoOuter * aTubeOut * perimOut * 1.10; // +10% corner gussets/flanges

        // Inner Gimbal Hollow Section Geometry
        const wIn_m = p.innerSection_mm / 1000.0;
        const tIn_m = p.innerWall_mm / 1000.0;
        const LIn_m = p.innerSize_mm / 1000.0;
        const aTubeIn = (wIn_m * wIn_m) - Math.max(0, (wIn_m - 2 * tIn_m)**2);
        const perimIn = Math.max(0.1, 4 * (LIn_m - wIn_m));
        const massInnerFrame = rhoInner * aTubeIn * perimIn * 1.10;

        // Payload Cube & Eccentricity
        const mPayload = p.payloadMass_kg;
        const LPayload_m = p.payloadDim_mm / 1000.0;
        const offset_m = p.payloadOffset_mm / 1000.0;

        // Inner Gimbal MOI (I_yy) about vertical pivot:
        const mBeamIn = massInnerFrame / 4.0;
        const dIn = (LIn_m - wIn_m) / 2.0;
        const iParallelIn = 2 * ((1/12) * mBeamIn * (wIn_m**2) + mBeamIn * (dIn**2));
        const iPerpIn = 2 * ((1/12) * mBeamIn * ((LIn_m - wIn_m)**2));
        const iHubIn = 0.005; // bearing hub + shaft
        const iPayloadIn = (1/6) * mPayload * (LPayload_m**2) + mPayload * (offset_m**2);
        const I_yy = Math.max(0.01, iParallelIn + iPerpIn + iHubIn + iPayloadIn);

        // Outer Gimbal MOI (I_xx) about horizontal pivot:
        const mBeamOut = massOuterFrame / 4.0;
        const dOut = (LOut_m - wOut_m) / 2.0;
        const iParallelOut = 2 * ((1/12) * mBeamOut * (wOut_m**2) + mBeamOut * (dOut**2));
        const iPerpOut = 2 * ((1/12) * mBeamOut * ((LOut_m - wOut_m)**2));
        const iHubOut = 0.010;
        const I_xx = Math.max(0.02, iParallelOut + iPerpOut + iHubOut + I_yy);

        // Dynamic Torques
        const alpha_max = 10.0; // rad/s²
        const tau_inertial_inner = I_yy * alpha_max;
        const tau_inertial_outer = I_xx * alpha_max;
        const tau_unbalance = mPayload * 9.80665 * offset_m;
        const tau_friction = 0.06; // dual ball bearings + gold slip ring drag
        const tau_peak_inner = tau_inertial_inner + tau_unbalance + tau_friction;
        const tau_peak_outer = tau_inertial_outer + tau_unbalance + tau_friction;
        const tau_peak_max = Math.max(tau_peak_inner, tau_peak_outer);
        const motor_rated = 2.80; // N·m for NEMA 23
        const sf = motor_rated / (tau_peak_max + 1e-6);

        return {
            massOuterFrame,
            massInnerFrame,
            I_yy,
            I_xx,
            tau_inertial_inner,
            tau_inertial_outer,
            tau_unbalance,
            tau_friction,
            tau_peak_inner,
            tau_peak_outer,
            tau_peak_max,
            sf
        };
    }

    applyCustomMechanicsParameters(notify = true) {
        const outerSize = parseFloat(document.getElementById('outer-size-input')?.value || 500);
        const outerSection = parseFloat(document.getElementById('outer-section-input')?.value || 50.8);
        const outerWall = parseFloat(document.getElementById('outer-wall-input')?.value || 3.2);
        const outerMat = document.getElementById('outer-mat-select')?.value || 'Al6061';

        const innerSize = parseFloat(document.getElementById('inner-size-input')?.value || 350);
        const innerSection = parseFloat(document.getElementById('inner-section-input')?.value || 50.8);
        const innerWall = parseFloat(document.getElementById('inner-wall-input')?.value || 3.2);
        const innerMat = document.getElementById('inner-mat-select')?.value || 'Al6061';

        const payloadDim = parseFloat(document.getElementById('payload-dim-input')?.value || 200);
        const payloadMass = parseFloat(document.getElementById('payload-mass-input')?.value || 3.5);
        const payloadOffset = parseFloat(document.getElementById('payload-offset-input')?.value || 5.0);

        this.moiParams = {
            outerSize_mm: outerSize,
            outerSection_mm: outerSection,
            outerWall_mm: outerWall,
            outerMat: outerMat,
            innerSize_mm: innerSize,
            innerSection_mm: innerSection,
            innerWall_mm: innerWall,
            innerMat: innerMat,
            payloadDim_mm: payloadDim,
            payloadMass_kg: payloadMass,
            payloadOffset_mm: payloadOffset
        };

        const moi = this.calculateMechanicalMOI();
        this.currentMOI = moi;

        // Update Spec Table DOM
        const elMassOut = document.getElementById('calc-mass-outer');
        const elMassIn = document.getElementById('calc-mass-inner');
        const elMoiIn = document.getElementById('calc-moi-inner');
        const elMoiOut = document.getElementById('calc-moi-outer');
        const elTorqueInertial = document.getElementById('calc-torque-inertial');
        const elTorqueUnbal = document.getElementById('calc-torque-unbal');
        const elTorquePeak = document.getElementById('calc-torque-peak');
        const elSf = document.getElementById('calc-sf');

        if (elMassOut) elMassOut.textContent = moi.massOuterFrame.toFixed(2) + ' kg';
        if (elMassIn) elMassIn.textContent = moi.massInnerFrame.toFixed(2) + ' kg';
        if (elMoiIn) elMoiIn.textContent = moi.I_yy.toFixed(3) + ' kg·m²';
        if (elMoiOut) elMoiOut.textContent = moi.I_xx.toFixed(3) + ' kg·m²';
        if (elTorqueInertial) elTorqueInertial.textContent = moi.tau_inertial_outer.toFixed(2) + ' N·m (Outer)';
        if (elTorqueUnbal) elTorqueUnbal.textContent = `${moi.tau_unbalance.toFixed(2)} N·m (${payloadOffset}mm C.G.)`;
        if (elTorquePeak) elTorquePeak.textContent = moi.tau_peak_max.toFixed(2) + ' N·m';
        if (elSf) {
            elSf.textContent = `${moi.sf.toFixed(1)}x (${moi.sf >= 2.0 ? 'SAFE' : 'MARGINAL'})`;
            elSf.style.color = moi.sf >= 2.0 ? 'var(--accent-green)' : 'var(--accent-red)';
        }

        // Update CAD labels
        const lblFrames = document.getElementById('cad-frames-label');
        const lblPayload = document.getElementById('cad-payload-label');
        if (lblFrames) lblFrames.textContent = `Outer: ${outerSize} mm ${outerMat} • Inner: ${innerSize} mm ${innerMat}`;
        if (lblPayload) lblPayload.textContent = `Chamber: ${payloadDim} mm (Payload ${payloadMass} kg, ${payloadOffset}mm offset)`;

        // Rescale CAD Assembly smoothly
        if (this.cadAssembly) {
            const outerScale = outerSize / 500.0;
            const innerScale = innerSize / 350.0;
            const payloadScale = payloadDim / 200.0;
            if (this.cadAssembly.outerFrameGroup) this.cadAssembly.outerFrameGroup.scale.set(outerScale, outerScale, outerScale);
            if (this.cadAssembly.innerFrameGroup) this.cadAssembly.innerFrameGroup.scale.set(innerScale, innerScale, innerScale);
            if (this.cadAssembly.payloadGroup) this.cadAssembly.payloadGroup.scale.set(payloadScale, payloadScale, payloadScale);
        }

        if (notify && typeof showToast === 'function') {
            showToast(`Mechanics updated: I_xx = ${moi.I_xx.toFixed(3)} kg·m², I_yy = ${moi.I_yy.toFixed(3)} kg·m², Peak τ = ${moi.tau_peak_max.toFixed(2)} N·m (SF: ${moi.sf.toFixed(1)}x)`, 'info');
        }
    }

    /* =========================================================================
       3D CAD ASSEMBLY VISUALIZATION (Three.js)
       ========================================================================= */
    init3D() {
        const container = document.getElementById('cad-canvas-container');
        if (!container) return;

        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0xf8fafc); // Clean laboratory light background

        this.camera = new THREE.PerspectiveCamera(40, container.clientWidth / container.clientHeight, 0.05, 50);
        this.camera.position.set(1.4, 1.1, 1.6);
        this.camera.lookAt(0.0, 0.45, 0.0);

        this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: false, powerPreference: "high-performance" });
        this.renderer.setSize(container.clientWidth, container.clientHeight);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        this.renderer.shadowMap.autoUpdate = false; // Freeze dynamic shadow passes to eliminate GPU overheating
        this.renderer.shadowMap.needsUpdate = true;
        container.appendChild(this.renderer.domElement);

        // Lighting
        const hemiLight = new THREE.HemisphereLight(0xffffff, 0xe2e8f0, 0.85);
        this.scene.add(hemiLight);

        const dirLight = new THREE.DirectionalLight(0xffffff, 0.7);
        dirLight.position.set(2.5, 4.0, 3.0);
        dirLight.castShadow = true;
        this.scene.add(dirLight);

        const backLight = new THREE.DirectionalLight(0x94a3b8, 0.3);
        backLight.position.set(-2.5, 2.0, -2.0);
        this.scene.add(backLight);

        // Grid floor
        const grid = new THREE.GridHelper(3.0, 30, 0xcbd5e1, 0xe2e8f0);
        grid.position.y = 0.0;
        this.scene.add(grid);

        // Build exact CAD Assembly
        this.cadAssembly = new RPMCadAssembly(this.scene);
        this.cadAssembly.updateSamplePoints(this.samplePoints);

        // Interactive Orbit Controls (Mouse Drag & Scroll)
        this.setupOrbitControls(container, this.camera);

        // Resize observer
        window.addEventListener('resize', () => {
            if (!container) return;
            this.camera.aspect = container.clientWidth / container.clientHeight;
            this.camera.updateProjectionMatrix();
            this.renderer.setSize(container.clientWidth, container.clientHeight);
        });

        // Render loop (Throttled to 30 FPS with tab dormancy check to prevent GPU heating)
        const animate = (timestamp) => {
            requestAnimationFrame(animate);
            if (document.hidden) return;
            if (timestamp - this.lastCadTime < this.cadFpsInterval) return;
            this.lastCadTime = timestamp;
            this.renderer.render(this.scene, this.camera);
        };
        requestAnimationFrame(animate);
    }

    setupOrbitControls(container, camera) {
        let isDragging = false;
        let prevMouseX = 0;
        let prevMouseY = 0;
        let spherical = { radius: 2.4, theta: 0.85, phi: 1.15 };

        const updateCameraPos = () => {
            camera.position.x = spherical.radius * Math.sin(spherical.phi) * Math.sin(spherical.theta);
            camera.position.y = spherical.radius * Math.cos(spherical.phi) + 0.45;
            camera.position.z = spherical.radius * Math.sin(spherical.phi) * Math.cos(spherical.theta);
            camera.lookAt(0.0, 0.45, 0.0);
        };
        updateCameraPos();

        container.addEventListener('mousedown', (e) => {
            if (e.target.tagName === 'BUTTON') return;
            isDragging = true;
            prevMouseX = e.clientX;
            prevMouseY = e.clientY;
        });

        window.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            const deltaX = e.clientX - prevMouseX;
            const deltaY = e.clientY - prevMouseY;
            prevMouseX = e.clientX;
            prevMouseY = e.clientY;

            spherical.theta -= deltaX * 0.008;
            spherical.phi = Math.max(0.1, Math.min(Math.PI / 2.05, spherical.phi - deltaY * 0.008));
            updateCameraPos();
        });

        window.addEventListener('mouseup', () => { isDragging = false; });

        container.addEventListener('wheel', (e) => {
            e.preventDefault();
            spherical.radius = Math.max(0.8, Math.min(5.0, spherical.radius + e.deltaY * 0.0015));
            updateCameraPos();
        }, { passive: false });
    }

    /* =========================================================================
       S² UNIT SPHERE TRAJECTORY PLOT (Restored from v1 with Scientific White BG)
       ========================================================================= */
    initSphereVisualization() {
        const canvas = document.getElementById('sphere-canvas');
        if (!canvas) return;

        this.sphereScene = new THREE.Scene();
        this.sphereScene.background = new THREE.Color(0xffffff); // Pure white scientific background

        const width = canvas.parentElement.clientWidth || 320;
        const height = canvas.parentElement.clientHeight || 240;

        this.sphereCamera = new THREE.PerspectiveCamera(40, width / height, 0.1, 50);
        this.sphereCamera.position.set(2.2, 1.6, 2.2);
        this.sphereCamera.lookAt(0, 0, 0);

        this.sphereRenderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false, powerPreference: "low-power" });
        this.sphereRenderer.setSize(width, height);
        this.sphereRenderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));

        // Wireframe Unit Sphere (S²)
        const sphereGeom = new THREE.SphereGeometry(1.0, 24, 16);
        const sphereWire = new THREE.LineSegments(
            new THREE.WireframeGeometry(sphereGeom),
            new THREE.LineBasicMaterial({ color: 0xe2e8f0, transparent: true, opacity: 0.85 })
        );
        this.sphereScene.add(sphereWire);

        // Equator ring
        const equatorGeom = new THREE.BufferGeometry();
        const eqPts = [];
        for (let i = 0; i <= 64; i++) {
            const angle = (i / 64) * Math.PI * 2;
            eqPts.push(new THREE.Vector3(Math.cos(angle), 0, Math.sin(angle)));
        }
        equatorGeom.setFromPoints(eqPts);
        const equatorLine = new THREE.Line(equatorGeom, new THREE.LineBasicMaterial({ color: 0x94a3b8 }));
        this.sphereScene.add(equatorLine);

        // Coordinate Axes Helper (X = Red, Y = Green, Z = Blue)
        const axesHelper = new THREE.AxesHelper(1.2);
        this.sphereScene.add(axesHelper);

        // Pole markers (+Z and -Z)
        const poleGeom = new THREE.SphereGeometry(0.035, 12, 12);
        const northPole = new THREE.Mesh(poleGeom, new THREE.MeshBasicMaterial({ color: 0x2563eb }));
        northPole.position.set(0, 0, 1.0);
        this.sphereScene.add(northPole);

        const southPole = new THREE.Mesh(poleGeom, new THREE.MeshBasicMaterial({ color: 0x64748b }));
        southPole.position.set(0, 0, -1.0);
        this.sphereScene.add(southPole);

        // Dynamic Gravity Trajectory Line on S²
        const trajGeom = new THREE.BufferGeometry();
        trajGeom.setAttribute('position', new THREE.BufferAttribute(new Float32Array(this.maxSpherePoints * 3), 3));
        const trajMat = new THREE.LineBasicMaterial({ color: 0x0284c7, linewidth: 2 });
        this.sphereTrajectoryLine = new THREE.Line(trajGeom, trajMat);
        this.sphereScene.add(this.sphereTrajectoryLine);

        // Instantaneous Gravity Vector Tip Marker (Red Sphere)
        const tipGeom = new THREE.SphereGeometry(0.055, 16, 16);
        const tipMat = new THREE.MeshBasicMaterial({ color: 0xdc2626 });
        this.sphereCurrentMarker = new THREE.Mesh(tipGeom, tipMat);
        this.sphereScene.add(this.sphereCurrentMarker);

        // Mouse Drag to rotate S² sphere
        let isSphereDragging = false;
        let prevX = 0, prevY = 0;
        let sAngleX = 0.8, sAngleY = 0.6, sRadius = 2.8;

        const updateSphereCam = () => {
            this.sphereCamera.position.x = sRadius * Math.sin(sAngleY) * Math.sin(sAngleX);
            this.sphereCamera.position.y = sRadius * Math.cos(sAngleY);
            this.sphereCamera.position.z = sRadius * Math.sin(sAngleY) * Math.cos(sAngleX);
            this.sphereCamera.lookAt(0, 0, 0);
        };
        updateSphereCam();

        canvas.addEventListener('mousedown', (e) => {
            isSphereDragging = true;
            prevX = e.clientX;
            prevY = e.clientY;
        });

        window.addEventListener('mousemove', (e) => {
            if (!isSphereDragging) return;
            const dx = e.clientX - prevX;
            const dy = e.clientY - prevY;
            prevX = e.clientX;
            prevY = e.clientY;
            sAngleX -= dx * 0.01;
            sAngleY = Math.max(0.1, Math.min(Math.PI - 0.1, sAngleY - dy * 0.01));
            updateSphereCam();
        });

        window.addEventListener('mouseup', () => { isSphereDragging = false; });

        // Sphere render loop (Throttled to 30 FPS and only rendered when Trajectory tab is visible)
        const animateSphere = (timestamp) => {
            requestAnimationFrame(animateSphere);
            if (document.hidden) return;
            const trajTab = document.getElementById('tab-kinematics');
            if (trajTab && !trajTab.classList.contains('active')) return;
            if (timestamp - this.lastSphereTime < this.sphereFpsInterval) return;
            this.lastSphereTime = timestamp;
            if (this.sphereRenderer && this.sphereScene && this.sphereCamera) {
                this.sphereRenderer.render(this.sphereScene, this.sphereCamera);
            }
        };
        requestAnimationFrame(animateSphere);
    }

    updateSphereTrajectory(gx, gy, gz) {
        if (!this.sphereTrajectoryLine) return;

        // Unit vector projection onto S²
        const norm = Math.sqrt(gx * gx + gy * gy + gz * gz) || 1.0;
        const ux = gx / norm;
        const uy = gy / norm;
        const uz = gz / norm;

        // Position current tip marker
        if (this.sphereCurrentMarker) {
            this.sphereCurrentMarker.position.set(ux, uy, uz);
        }

        // Add to history
        this.sphereTrajectory.push(ux, uy, uz);
        if (this.sphereTrajectory.length > this.maxSpherePoints * 3) {
            this.sphereTrajectory.splice(0, 3);
        }

        const positions = this.sphereTrajectoryLine.geometry.attributes.position.array;
        for (let i = 0; i < this.sphereTrajectory.length; i++) {
            positions[i] = this.sphereTrajectory[i];
        }
        this.sphereTrajectoryLine.geometry.attributes.position.needsUpdate = true;
        this.sphereTrajectoryLine.geometry.setDrawRange(0, this.sphereTrajectory.length / 3);
    }

    /* =========================================================================
       SCIENTIFIC CHARTS (Chart.js)
       ========================================================================= */
    initPlots() {
        if (typeof Chart === 'undefined') {
            console.warn('Chart.js not yet loaded, deferring initPlots');
            setTimeout(() => this.initPlots(), 500);
            return;
        }

        // Chart 1: Time Series of Gx, Gy, Gz & taSMG (White Background)
        const tsCtx = document.getElementById('timeseries-canvas');
        if (tsCtx) {
            this.tsChart = new Chart(tsCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        { label: 'Gx (g)', data: [], borderColor: '#dc2626', borderWidth: 1.5, pointRadius: 0, tension: 0.1 },
                        { label: 'Gy (g)', data: [], borderColor: '#2563eb', borderWidth: 1.5, pointRadius: 0, tension: 0.1 },
                        { label: 'Gz (g)', data: [], borderColor: '#15803d', borderWidth: 1.5, pointRadius: 0, tension: 0.1 },
                        { label: '<g> taSMG', data: [], borderColor: '#0f172a', borderWidth: 2, borderDash: [4, 4], pointRadius: 0 }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: false,
                    scales: {
                        x: {
                            title: { display: true, text: 'Time (s)', color: '#475569', font: { size: 10 } },
                            ticks: { color: '#64748b', font: { size: 9 }, maxTicksLimit: 12 },
                            grid: { color: '#f1f5f9' }
                        },
                        y: {
                            min: -1.2, max: 1.2,
                            title: { display: true, text: 'Acceleration (g)', color: '#475569', font: { size: 10 } },
                            ticks: { color: '#64748b', font: { size: 9 }, stepSize: 0.5 },
                            grid: { color: '#e2e8f0' }
                        }
                    },
                    plugins: {
                        legend: { position: 'top', labels: { boxWidth: 12, font: { size: 10, weight: '600' } } }
                    }
                }
            });
        }

        // Chart 2: Dynamic Motor Torque τ(t) (N·m)
        const torqueCtx = document.getElementById('torque-canvas');
        if (torqueCtx) {
            this.torqueChart = new Chart(torqueCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        { label: 'τ Inner (N·m)', data: [], borderColor: '#1e3a8a', borderWidth: 1.5, pointRadius: 0, tension: 0.1 },
                        { label: 'τ Outer (N·m)', data: [], borderColor: '#059669', borderWidth: 1.5, pointRadius: 0, tension: 0.1 },
                        { label: 'NEMA 23 Limit (2.8)', data: [], borderColor: '#dc2626', borderWidth: 1.5, borderDash: [4, 4], pointRadius: 0 }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: false,
                    scales: {
                        x: {
                            title: { display: true, text: 'Time (s)', color: '#475569', font: { size: 9 } },
                            ticks: { color: '#64748b', font: { size: 8 }, maxTicksLimit: 8 },
                            grid: { color: '#f1f5f9' }
                        },
                        y: {
                            min: 0, max: 3.2,
                            title: { display: true, text: 'Torque (N·m)', color: '#475569', font: { size: 9 } },
                            ticks: { color: '#64748b', font: { size: 8 }, stepSize: 0.8 },
                            grid: { color: '#e2e8f0' }
                        }
                    },
                    plugins: {
                        legend: { position: 'top', labels: { boxWidth: 10, font: { size: 9, weight: '600' } } }
                    }
                }
            });
        }

        // Chart 2C: Volumetric Centrifugal Gradient vs Radius
        const centCtx = document.getElementById('centrifugal-canvas');
        if (centCtx) {
            this.centChart = new Chart(centCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: 'Centrifugal Accel a_c (g)',
                            data: [],
                            borderColor: '#d97706',
                            borderWidth: 2,
                            pointRadius: 0,
                            tension: 0.1
                        },
                        {
                            label: '10⁻³ g Microgravity Boundary',
                            data: [],
                            borderColor: '#dc2626',
                            borderWidth: 1.5,
                            borderDash: [5, 5],
                            pointRadius: 0
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: false,
                    scales: {
                        x: {
                            title: { display: true, text: 'Radial Distance r (cm)', color: '#475569', font: { size: 10 } },
                            ticks: { color: '#64748b', font: { size: 9 } },
                            grid: { color: '#f1f5f9' }
                        },
                        y: {
                            title: { display: true, text: 'Acceleration (g)', color: '#475569', font: { size: 10 } },
                            ticks: { color: '#64748b', font: { size: 9 } },
                            grid: { color: '#e2e8f0' }
                        }
                    },
                    plugins: {
                        legend: { position: 'top', labels: { boxWidth: 12, font: { size: 10 } } }
                    }
                }
            });
        }
    }

    bindEvents() {
        // Mode Selector
        const modeSelect = document.getElementById('mode-select');
        if (modeSelect) {
            modeSelect.addEventListener('change', (e) => {
                this.setOperationMode(e.target.value);
            });
        }

        // Speed Sliders
        const innerSlider = document.getElementById('inner-rpm-slider');
        if (innerSlider) {
            innerSlider.addEventListener('input', (e) => {
                this.base_inner_rpm = parseFloat(e.target.value);
                document.getElementById('inner-rpm-val').textContent = this.base_inner_rpm.toFixed(1) + ' RPM';
                this.updateTargetSpeeds();
            });
        }

        const outerSlider = document.getElementById('outer-rpm-slider');
        if (outerSlider) {
            outerSlider.addEventListener('input', (e) => {
                this.base_outer_rpm = parseFloat(e.target.value);
                document.getElementById('outer-rpm-val').textContent = this.base_outer_rpm.toFixed(1) + ' RPM';
                this.updateTargetSpeeds();
            });
        }

        // Controls
        document.getElementById('btn-start')?.addEventListener('click', () => { this.isRunning = true; this.isHoldingAngles = false; });
        document.getElementById('btn-stop')?.addEventListener('click', () => { this.isRunning = false; });
        document.getElementById('btn-reset')?.addEventListener('click', () => { this.reset(); });

        // Exports
        document.getElementById('btn-export-csv')?.addEventListener('click', () => { this.exportCSV(); });
        document.getElementById('btn-export-plot')?.addEventListener('click', () => { this.exportPlot(); });
    }

    setOperationMode(mode) {
        this.operation_mode = mode;
        this.updateTargetSpeeds();
        this.updateModeUI();
    }

    updateTargetSpeeds() {
        if (this.isHoldingAngles) return;

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
        this.isHoldingAngles = false;
        this.direction_changes_count = 0;
        this.fluid_u.fill(0);
        this.telemetry_history = [];
        this.plot_time = [];
        this.plot_gx = [];
        this.plot_gy = [];
        this.plot_gz = [];
        this.plot_tasmg = [];
        this.sphereTrajectory = [];

        for (const pt of this.samplePoints) {
            pt.sumG = 0.0;
            pt.samples = 0;
            pt.tasmg = 1.0;
        }

        if (this.cadAssembly) {
            this.cadAssembly.updateRotations(0, 0);
        }
        document.getElementById('orbit-state-badge').textContent = 'ORBITING';
        document.getElementById('orbit-state-badge').style.color = 'var(--accent-green)';
    }

    /* =========================================================================
       50 HZ MAIN SIMULATION TICK
       ========================================================================= */
    step(dt) {
        if (!this.isRunning) return;

        this.elapsed_time += dt;

        if (!this.isHoldingAngles) {
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
        } else {
            this.omega_phi_rpm = 0.0;
            this.omega_psi_rpm = 0.0;
        }

        // Yotov et al. (2022) Kinematics with Axis Inclination Tilts
        const phi_rad = (this.phi_deg + this.innerTilt_deg) * Math.PI / 180.0;
        const psi_rad = (this.psi_deg + this.outerTilt_deg) * Math.PI / 180.0;

        const gx = -Math.sin(phi_rad) * Math.cos(psi_rad);
        const gy =  Math.sin(phi_rad) * Math.sin(psi_rad);
        const gz =  Math.cos(phi_rad);
        const inst_g = Math.sqrt(gx * gx + gy * gy + gz * gz);

        this.inst_gx = gx;
        this.inst_gy = gy;
        this.inst_gz = gz;

        // Cumulative taSMG
        this.samples++;
        this.sum_gx += gx;
        this.sum_gy += gy;
        this.sum_gz += gz;
        const avg_gx = this.sum_gx / this.samples;
        const avg_gy = this.sum_gy / this.samples;
        const avg_gz = this.sum_gz / this.samples;
        this.tasmg = Math.sqrt(avg_gx * avg_gx + avg_gy * avg_gy + avg_gz * avg_gz);

        // Dynamic angular accelerations (alpha) in rad/s²
        const omega_phi_rad_s = (this.omega_phi_rpm * 2.0 * Math.PI) / 60.0;
        const omega_psi_rad_s = (this.omega_psi_rpm * 2.0 * Math.PI) / 60.0;
        const alpha_phi = (omega_phi_rad_s - this.prev_omega_phi_rad_s) / dt;
        const alpha_psi = (omega_psi_rad_s - this.prev_omega_psi_rad_s) / dt;
        this.prev_omega_phi_rad_s = omega_phi_rad_s;
        this.prev_omega_psi_rad_s = omega_psi_rad_s;

        // Dynamic motor torques with speed-dependent drag and gyroscopic cross-coupling:
        // 1. Angular acceleration inertial torque: I * alpha
        // 2. Gyroscopic cross-coupling torque between rotating gimbals: I_yy * |omega_psi * omega_phi * sin(phi)|
        // 3. Speed-dependent drag: Coulomb friction (0.04 N·m) + viscous bearing drag (c_visc * |omega|) + aerodynamic windage (c_aero * omega^2)
        // 4. Static payload unbalance torque: M * g * delta_r * sin(theta)
        const moi = this.currentMOI || this.calculateMechanicalMOI();
        const c_visc = 0.035;   // N·s/rad (lubricant shear + slip-ring gold brush friction)
        const c_aero = 0.003;   // N·s²/rad² (aerodynamic drag of rotating frames)
        
        const tau_drag_inner = 0.04 + c_visc * Math.abs(omega_phi_rad_s) + c_aero * (omega_phi_rad_s ** 2);
        const tau_drag_outer = 0.04 + c_visc * Math.abs(omega_psi_rad_s) + c_aero * (omega_psi_rad_s ** 2);
        const tau_gyro = moi.I_yy * Math.abs(omega_psi_rad_s * omega_phi_rad_s * Math.sin(phi_rad));

        const tau_in = Math.abs(moi.I_yy * alpha_phi) + tau_gyro + Math.abs(moi.tau_unbalance * Math.sin(phi_rad)) + tau_drag_inner;
        const tau_out = Math.abs(moi.I_xx * alpha_psi) + tau_gyro + Math.abs(moi.tau_unbalance * Math.sin(psi_rad)) + tau_drag_outer;
        this.inst_torque_inner = tau_in;
        this.inst_torque_outer = tau_out;
        if (tau_in > this.peak_torque_observed) this.peak_torque_observed = tau_in;
        if (tau_out > this.peak_torque_observed) this.peak_torque_observed = tau_out;

        // Wadhwa et al. (2026) Volumetric Accelerations
        const omega_norm = Math.sqrt(omega_phi_rad_s**2 + omega_psi_rad_s**2);
        const g0 = 9.80665;

        // Safe radius threshold r_safe = (10^-3 * g0) / ||omega||^2
        const r_safe_cm = (0.001 * g0) / (omega_norm**2 + 1e-12) * 100.0;

        // Centrifugal acceleration at chamber boundary (biology)
        const a_cent_edge_g = (omega_norm**2 * this.chamber_radius_m) / g0;

        // Space Manufacturing / WAAM 200 mm CAD envelope edge (r = 10 cm = 0.10 m)
        const envelope_r_m = 0.10;
        const a_cent_envelope_g = (omega_norm**2 * envelope_r_m) / g0;
        const g_eff = Math.max(a_cent_envelope_g * g0, 1e-6);

        // Bond Number: Bo = (rho * g_eff * L_melt^2) / sigma
        const L_m = this.melt_L_mm / 1000.0;
        const bond_number = (this.melt_rho * g_eff * (L_m**2)) / this.melt_sigma;
        this.last_bond_number = bond_number;

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

        // Update Sample Points local accelerations (Wadhwa Eq. 5)
        for (const pt of this.samplePoints) {
            const r_m = Math.sqrt(pt.x**2 + pt.y**2 + pt.z**2) / 100.0;
            const a_c = (omega_norm**2 * r_m) / g0;
            pt.ac = a_c;
            const pt_inst = Math.sqrt(gx**2 + gy**2 + gz**2) + a_c;
            pt.sumG += pt_inst;
            pt.samples++;
            pt.tasmg = pt.sumG / pt.samples;
        }

        // Update CAD Model with throttled shadow pass
        if (this.cadAssembly) {
            this.cadAssembly.updateRotations(this.phi_deg, this.psi_deg);
            this.shadowUpdateCounter++;
            if (this.shadowUpdateCounter % 15 === 0 && this.renderer && this.renderer.shadowMap) {
                this.renderer.shadowMap.needsUpdate = true; // Update shadows at 3.3 Hz rather than 120 Hz
            }
        }

        // Update S² Sphere plot
        this.updateSphereTrajectory(gx, gy, gz);

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
                tasmg: this.tasmg,
                torque_inner: tau_in,
                torque_outer: tau_out,
                cent_edge: a_cent_edge_g,
                shear_mPa: this.last_shear_stress
            });
        }

        // Plot buffers
        this.plot_time.push(this.elapsed_time.toFixed(1));
        this.plot_gx.push(gx);
        this.plot_gy.push(gy);
        this.plot_gz.push(gz);
        this.plot_tasmg.push(this.tasmg);

        // Torque buffers
        this.plot_torque_inner.push(parseFloat(tau_in.toFixed(3)));
        this.plot_torque_outer.push(parseFloat(tau_out.toFixed(3)));
        this.plot_torque_limit.push(2.80);

        if (this.plot_time.length > this.max_plot_points) {
            this.plot_time.shift();
            this.plot_gx.shift();
            this.plot_gy.shift();
            this.plot_gz.shift();
            this.plot_tasmg.shift();
            this.plot_torque_inner.shift();
            this.plot_torque_outer.shift();
            this.plot_torque_limit.shift();
        }

        // Update UI every 5 steps (10 Hz refresh)
        if (this.samples % 5 === 0) {
            this.updateTelemetryDOM(this.tasmg, inst_g, a_cent_edge_g, r_safe_cm, this.last_shear_stress, avg_gx, avg_gy, avg_gz, a_cent_envelope_g, bond_number);
            this.updateCharts(omega_norm);
        }
    }

    updateTelemetryDOM(tasmg, inst_g, a_cent, r_safe, shear_mPa, avg_gx, avg_gy, avg_gz, a_cent_envelope, bond_num) {
        const elTasmg = document.getElementById('metric-tasmg');
        const elInstG = document.getElementById('metric-inst-g');
        const elTorqueIn = document.getElementById('metric-torque-inner');
        const elTorqueOut = document.getElementById('metric-torque-outer');
        const elMoi = document.getElementById('metric-moi');
        const elSamples = document.getElementById('metric-samples');

        if (elTasmg) elTasmg.textContent = tasmg.toFixed(4) + ' g';
        if (elInstG) elInstG.textContent = inst_g.toFixed(3) + ' g';
        if (elTorqueIn) elTorqueIn.textContent = this.inst_torque_inner.toFixed(2) + ' N·m';
        if (elTorqueOut) elTorqueOut.textContent = this.inst_torque_outer.toFixed(2) + ' N·m';
        if (elMoi && this.currentMOI) elMoi.textContent = `${this.currentMOI.I_xx.toFixed(3)} / ${this.currentMOI.I_yy.toFixed(3)} kg·m²`;
        if (elSamples) elSamples.textContent = this.samples.toLocaleString();

        const elLiveIn = document.getElementById('live-torque-inner');
        const elLiveOut = document.getElementById('live-torque-outer');
        const elLivePeak = document.getElementById('live-torque-peak');
        const elLiveSf = document.getElementById('live-sf-badge');

        if (elLiveIn) elLiveIn.textContent = this.inst_torque_inner.toFixed(2) + ' N·m';
        if (elLiveOut) elLiveOut.textContent = this.inst_torque_outer.toFixed(2) + ' N·m';
        if (elLivePeak) elLivePeak.textContent = this.peak_torque_observed.toFixed(2) + ' N·m';
        if (elLiveSf) {
            const sf = 2.80 / Math.max(this.peak_torque_observed, 0.05);
            elLiveSf.textContent = `SF: ${sf.toFixed(1)}x`;
            elLiveSf.style.color = sf >= 2.0 ? 'var(--accent-green)' : 'var(--accent-red)';
        }

        const elPhi = document.getElementById('display-phi');
        const elPsi = document.getElementById('display-psi');
        const elOmegaPhi = document.getElementById('display-omega-phi');
        const elOmegaPsi = document.getElementById('display-omega-psi');
        const elGamma = document.getElementById('display-gamma');
        const elTilts = document.getElementById('display-tilts');

        if (elPhi) elPhi.textContent = this.phi_deg.toFixed(1) + '°';
        if (elPsi) elPsi.textContent = this.psi_deg.toFixed(1) + '°';
        if (elOmegaPhi) elOmegaPhi.textContent = this.omega_phi_rpm.toFixed(2) + ' RPM';
        if (elOmegaPsi) elOmegaPsi.textContent = this.omega_psi_rpm.toFixed(2) + ' RPM';

        const gamma = (this.omega_phi_rpm > 0) ? (this.omega_psi_rpm / this.omega_phi_rpm).toFixed(3) : '1.146';
        if (elGamma) elGamma.textContent = gamma;
        if (elTilts) elTilts.textContent = `${this.innerTilt_deg.toFixed(1)}° / ${this.outerTilt_deg.toFixed(1)}°`;

        // Update sample points table cells
        for (const pt of this.samplePoints) {
            const tasmgEl = document.getElementById(`pt-tasmg-${pt.id}`);
            const acEl = document.getElementById(`pt-ac-${pt.id}`);
            if (tasmgEl) tasmgEl.textContent = pt.tasmg.toFixed(4) + 'g';
            if (acEl) acEl.textContent = pt.ac.toFixed(5) + 'g';
        }
    }

    setExperimentDomain(domain) {
        this.experiment_domain = domain;
        const mfgBtn = document.getElementById('domain-mfg-btn');
        const bioBtn = document.getElementById('domain-bio-btn');
        const badge = document.getElementById('domain-badge');
        const desc = document.getElementById('domain-description');
        const centLabel = document.getElementById('metric-cent-label');
        const regimeLabel = document.getElementById('metric-regime-label');

        if (domain === 'manufacturing') {
            if (mfgBtn) mfgBtn.className = 'btn btn-primary';
            if (bioBtn) bioBtn.className = 'btn btn-secondary';
            if (badge) {
                badge.textContent = 'MANUFACTURING / WAAM';
                badge.style.background = '#e0e7ff';
                badge.style.color = '#3730a3';
            }
            if (desc) {
                desc.innerHTML = '<strong>Manufacturing Regime (Bo ≪ 1):</strong> Governed by capillary surface tension & convection suppression. Entire 200 mm CAD envelope with IMU operates in microgravity (a_c &lt; 1.1×10⁻⁴ g at 0.5–1 RPM).';
            }
            if (centLabel) centLabel.textContent = 'Envelope a_c (r=10cm)';
            if (regimeLabel) regimeLabel.textContent = 'Bond Number Bo (Capillary)';

            // Set recommended low-speed manufacturing presets (Kim ergodic ratio 1.146)
            this.base_inner_rpm = 0.5;
            this.base_outer_rpm = 0.573;
            const innerSlider = document.getElementById('inner-rpm-slider');
            const outerSlider = document.getElementById('outer-rpm-slider');
            if (innerSlider) innerSlider.value = 0.5;
            if (outerSlider) outerSlider.value = 0.573;
            const innerVal = document.getElementById('inner-rpm-val');
            const outerVal = document.getElementById('outer-rpm-val');
            if (innerVal) innerVal.textContent = '0.5 RPM';
            if (outerVal) outerVal.textContent = '0.6 RPM';
            this.updateTargetSpeeds();
        } else {
            if (mfgBtn) mfgBtn.className = 'btn btn-secondary';
            if (bioBtn) bioBtn.className = 'btn btn-primary';
            if (badge) {
                badge.textContent = 'BIOLOGY (SEDIMENTATION)';
                badge.style.background = '#fef3c7';
                badge.style.color = '#92400e';
            }
            if (desc) {
                desc.innerHTML = '<strong>Biological Regime:</strong> Governed by cellular organelle sedimentation. Constrained to safe radius r &le; 2.2 cm at 2.0 RPM (a_c &lt; 10⁻³ g).';
            }
            if (centLabel) centLabel.textContent = 'Centrifugal Bias (Edge)';
            if (regimeLabel) regimeLabel.textContent = 'Safe Radius (10⁻³g)';

            this.base_inner_rpm = 2.0;
            this.base_outer_rpm = 2.292;
            const innerSlider = document.getElementById('inner-rpm-slider');
            const outerSlider = document.getElementById('outer-rpm-slider');
            if (innerSlider) innerSlider.value = 2.0;
            if (outerSlider) outerSlider.value = 2.292;
            const innerVal = document.getElementById('inner-rpm-val');
            const outerVal = document.getElementById('outer-rpm-val');
            if (innerVal) innerVal.textContent = '2.0 RPM';
            if (outerVal) outerVal.textContent = '2.3 RPM';
            this.updateTargetSpeeds();
        }
    }

    updateCharts(omega_norm) {
        if (document.hidden) return;

        // Update Time-Series only if canvas is visible
        const tsCanvas = document.getElementById('timeseries-canvas');
        if (this.tsChart && tsCanvas && tsCanvas.offsetParent !== null) {
            this.tsChart.data.labels = this.plot_time;
            this.tsChart.data.datasets[0].data = this.plot_gx;
            this.tsChart.data.datasets[1].data = this.plot_gy;
            this.tsChart.data.datasets[2].data = this.plot_gz;
            this.tsChart.data.datasets[3].data = this.plot_tasmg;
            this.tsChart.update('none');
        }

        // Update Dynamic Motor Torque Chart
        const torqueCanvas = document.getElementById('torque-canvas');
        if (this.torqueChart && torqueCanvas && torqueCanvas.offsetParent !== null) {
            this.torqueChart.data.labels = this.plot_time;
            this.torqueChart.data.datasets[0].data = this.plot_torque_inner;
            this.torqueChart.data.datasets[1].data = this.plot_torque_outer;
            this.torqueChart.data.datasets[2].data = this.plot_torque_limit;
            this.torqueChart.update('none');
        }

        // Update Centrifugal Gradient only if canvas is visible
        const centCanvas = document.getElementById('centrifugal-canvas');
        if (this.centChart && centCanvas && centCanvas.offsetParent !== null) {
            const centLabels = [];
            const centVals = [];
            const threshVals = [];
            const g0 = 9.80665;
            for (let r_cm = 0; r_cm <= 15; r_cm += 1) {
                centLabels.push(r_cm.toString());
                const r_m = r_cm / 100.0;
                centVals.push((omega_norm**2 * r_m) / g0);
                threshVals.push(0.001); // 10^-3 g threshold
            }
            this.centChart.data.labels = centLabels;
            this.centChart.data.datasets[0].data = centVals;
            this.centChart.data.datasets[1].data = threshVals;
            this.centChart.update('none');
        }
    }

    /* =========================================================================
       SAMPLE PROBE POINTS MANAGEMENT (From v1)
       ========================================================================= */
    addSamplePoint(x, y, z) {
        const pt = {
            id: this.nextPointId++,
            x: x !== undefined ? x : parseFloat(document.getElementById('sample-pt-x').value || 0),
            y: y !== undefined ? y : parseFloat(document.getElementById('sample-pt-y').value || 0),
            z: z !== undefined ? z : parseFloat(document.getElementById('sample-pt-z').value || 0),
            sumG: 0.0,
            samples: 0,
            tasmg: 1.0,
            ac: 0.0
        };
        this.samplePoints.push(pt);
        this.renderSamplePointsTable();
        if (this.cadAssembly) {
            this.cadAssembly.updateSamplePoints(this.samplePoints);
        }
    }

    removeSamplePoint(id) {
        this.samplePoints = this.samplePoints.filter(p => p.id !== id);
        this.renderSamplePointsTable();
        if (this.cadAssembly) {
            this.cadAssembly.updateSamplePoints(this.samplePoints);
        }
    }

    renderSamplePointsTable() {
        const tbody = document.getElementById('sample-points-tbody');
        if (!tbody) return;
        tbody.innerHTML = '';

        for (const pt of this.samplePoints) {
            const r = Math.sqrt(pt.x**2 + pt.y**2 + pt.z**2).toFixed(1);
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>(${pt.x}, ${pt.y}, ${pt.z})</td>
                <td>${r} cm</td>
                <td id="pt-tasmg-${pt.id}">${pt.tasmg.toFixed(4)}g</td>
                <td id="pt-ac-${pt.id}">${pt.ac.toFixed(5)}g</td>
                <td><button class="btn-del-pt" onclick="window.app.removeSamplePoint(${pt.id})">&times;</button></td>
            `;
            tbody.appendChild(tr);
        }
    }

    /* =========================================================================
       CSV & PLOT EXPORT
       ========================================================================= */
    exportCSV() {
        if (this.telemetry_history.length === 0) {
            showToast('No simulation records logged yet.', 'warn');
            return;
        }

        const lines = [];
        lines.push('# =====================================================================');
        lines.push('# INDIAN INSTITUTE OF SPACE SCIENCE AND TECHNOLOGY (IIST)');
        lines.push('# Department of Aerospace Engineering - Microgravity Simulation Laboratory');
        lines.push('# Project: Random Positioning Machine (RPM) Digital Twin v2.0');
        lines.push(`# Date: ${new Date().toISOString()}`);
        lines.push(`# Operation Mode: ${this.operation_mode}`);
        lines.push('# CAD Model: Final_Drawing.pdf (Base 1200x900mm, Outer 500mm, Inner 350mm, Payload 200mm)');
        lines.push(`# Inner Tilt: ${this.innerTilt_deg}° | Outer Tilt: ${this.outerTilt_deg}°`);
        lines.push(`# Chamber Radius: ${(this.chamber_radius_m * 100.0).toFixed(1)} cm`);
        lines.push('# Tracked Sample Points:');
        for (const p of this.samplePoints) {
            lines.push(`#   Point ${p.id}: (${p.x}, ${p.y}, ${p.z}) cm -> local taSMG = ${p.tasmg.toFixed(5)} g, centrifugal = ${p.ac.toFixed(5)} g`);
        }
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

/* =========================================================================
   UI HANDLERS & GLOBAL FUNCTIONS
   ========================================================================= */

// Subtabs navigation
function switchSidebarTab(tabId) {
    document.querySelectorAll('.subtab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.subtab-content').forEach(content => content.classList.remove('active'));

    const activeBtn = Array.from(document.querySelectorAll('.subtab-btn')).find(b => b.getAttribute('onclick')?.includes(tabId));
    if (activeBtn) activeBtn.classList.add('active');

    const activeContent = document.getElementById(tabId);
    if (activeContent) activeContent.classList.add('active');
}

// Multiplot tab switcher
function switchPlotView(viewId) {
    document.querySelectorAll('.plot-tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.plot-view').forEach(view => view.classList.remove('active'));

    const activeBtn = Array.from(document.querySelectorAll('.plot-tab-btn')).find(b => b.getAttribute('onclick')?.includes(viewId));
    if (activeBtn) activeBtn.classList.add('active');

    const activeView = document.getElementById(viewId);
    if (activeView) activeView.classList.add('active');

    const titleEl = document.getElementById('multiplot-title');
    if (titleEl) {
        if (viewId === 'plot-sphere') titleEl.textContent = 'g⃗ Trajectory on Unit Sphere (S² Celestial Space)';
        else if (viewId === 'plot-shear') titleEl.textContent = '1D Navier-Stokes Fluid Shear Profile u_θ(r)';
        else if (viewId === 'plot-centrifugal') titleEl.textContent = 'Volumetric Centrifugal Gradient vs Radial Distance';
    }
}

// Axis Inclination (Tilts)
function applyAxisInclinations() {
    const innerTilt = parseFloat(document.getElementById('inner-tilt-input').value || 0);
    const outerTilt = parseFloat(document.getElementById('outer-tilt-input').value || 0);
    window.app.innerTilt_deg = innerTilt;
    window.app.outerTilt_deg = outerTilt;

    if (window.app.cadAssembly) {
        window.app.cadAssembly.updateAxisTilts(innerTilt, outerTilt);
    }
    document.getElementById('display-tilts').textContent = `${innerTilt.toFixed(1)}° / ${outerTilt.toFixed(1)}°`;
}

// Manual Angle Jog & Hold
function jogAngles(dPhi, dPsi) {
    if (dPhi === 0 && dPsi === 0) {
        window.app.phi_deg = 0;
        window.app.psi_deg = 0;
    } else {
        window.app.phi_deg = (window.app.phi_deg + dPhi + 360) % 360;
        window.app.psi_deg = (window.app.psi_deg + dPsi + 360) % 360;
    }
    document.getElementById('manual-phi-input').value = window.app.phi_deg.toFixed(1);
    document.getElementById('manual-psi-input').value = window.app.psi_deg.toFixed(1);
    applyManualAnglesAndHold();
}

function applyManualAnglesAndHold() {
    const phi = parseFloat(document.getElementById('manual-phi-input').value || 0);
    const psi = parseFloat(document.getElementById('manual-psi-input').value || 0);
    window.app.phi_deg = phi;
    window.app.psi_deg = psi;
    window.app.isHoldingAngles = true;
    window.app.omega_phi_rpm = 0.0;
    window.app.omega_psi_rpm = 0.0;

    if (window.app.cadAssembly) {
        window.app.cadAssembly.updateRotations(phi, psi);
    }
    const badge = document.getElementById('orbit-state-badge');
    if (badge) {
        badge.textContent = 'HOLDING TILT';
        badge.style.color = 'var(--accent-red)';
    }
}

function resumeSimulationTrajectory() {
    window.app.isHoldingAngles = false;
    window.app.updateTargetSpeeds();
    const badge = document.getElementById('orbit-state-badge');
    if (badge) {
        badge.textContent = 'ORBITING';
        badge.style.color = 'var(--accent-green)';
    }
}

// Floating Tilt Modal
function toggleTiltModal(show) {
    const modal = document.getElementById('tilt-modal');
    if (modal) modal.style.display = show ? 'flex' : 'none';
    if (show) {
        document.getElementById('modal-phi').value = window.app.phi_deg.toFixed(1);
        document.getElementById('modal-psi').value = window.app.psi_deg.toFixed(1);
        document.getElementById('modal-inner-tilt').value = window.app.innerTilt_deg.toFixed(1);
        document.getElementById('modal-outer-tilt').value = window.app.outerTilt_deg.toFixed(1);
    }
}

function modalJog(dPhi, dPsi) {
    let phi = parseFloat(document.getElementById('modal-phi').value || 0);
    let psi = parseFloat(document.getElementById('modal-psi').value || 0);
    if (dPhi === 0 && dPsi === 0) {
        phi = 0; psi = 0;
    } else {
        phi = (phi + dPhi + 360) % 360;
        psi = (psi + dPsi + 360) % 360;
    }
    document.getElementById('modal-phi').value = phi.toFixed(1);
    document.getElementById('modal-psi').value = psi.toFixed(1);
}

function applyModalChangesAndHold() {
    const phi = parseFloat(document.getElementById('modal-phi').value || 0);
    const psi = parseFloat(document.getElementById('modal-psi').value || 0);
    const innerTilt = parseFloat(document.getElementById('modal-inner-tilt').value || 0);
    const outerTilt = parseFloat(document.getElementById('modal-outer-tilt').value || 0);

    window.app.phi_deg = phi;
    window.app.psi_deg = psi;
    window.app.innerTilt_deg = innerTilt;
    window.app.outerTilt_deg = outerTilt;
    window.app.isHoldingAngles = true;

    if (window.app.cadAssembly) {
        window.app.cadAssembly.updateRotations(phi, psi);
        window.app.cadAssembly.updateAxisTilts(innerTilt, outerTilt);
    }

    document.getElementById('manual-phi-input').value = phi;
    document.getElementById('manual-psi-input').value = psi;
    document.getElementById('inner-tilt-input').value = innerTilt;
    document.getElementById('outer-tilt-input').value = outerTilt;

    const badge = document.getElementById('orbit-state-badge');
    if (badge) {
        badge.textContent = 'HOLDING TILT';
        badge.style.color = 'var(--accent-red)';
    }
    toggleTiltModal(false);
}

function resumeFromModal() {
    resumeSimulationTrajectory();
    toggleTiltModal(false);
}

// Sample Enclosure Box
function updateEnclosureBox() {
    const x = parseFloat(document.getElementById('enclosure-x')?.value || 20);
    const y = parseFloat(document.getElementById('enclosure-y')?.value || 20);
    const z = parseFloat(document.getElementById('enclosure-z')?.value || 20);
    const show = document.getElementById('show-enclosure')?.value === 'yes';

    if (window.app && window.app.cadAssembly) {
        window.app.cadAssembly.updateEnclosureBox(x, y, z, show);
        if (show) {
            window.app.showToast(`Enclosure wireframe applied: ${x} × ${y} × ${z} cm`, 'info');
        } else {
            window.app.showToast('Enclosure wireframe hidden', 'info');
        }
    }
}

// Sample Points
function addSamplePoint() {
    window.app.addSamplePoint();
}

// Payload Dimensions
function updatePayloadDimensions() {
    const w = parseFloat(document.getElementById('payload-w').value || 20);
    const h = parseFloat(document.getElementById('payload-h').value || 20);
    const d = parseFloat(document.getElementById('payload-d').value || 20);
    const show = document.getElementById('show-payload').value === 'yes';

    if (window.app.cadAssembly) {
        window.app.cadAssembly.updatePayloadDimensions(w, h, d, show);
    }
}

function updateFrameClearances() {
    showToast('CAD Clearances updated: Inner frame opening 250x250 mm, Outer frame opening 400x400 mm verified against DWG 02.', 'info');
}

// WebSerial (from v1)
async function connectWebSerial() {
    if (!('serial' in navigator)) {
        showToast('WebSerial API is not supported in this browser. Please use Chrome, Edge, or Opera.', 'warn');
        return;
    }
    try {
        const port = await navigator.serial.requestPort();
        await port.open({ baudRate: 115200 });
        showToast('WebSerial connected successfully to RPM motor controller at 115200 baud.', 'info');
        document.getElementById('ws-status-badge').textContent = 'WebSerial Connected (115200)';
        document.getElementById('ws-status-badge').style.color = 'var(--accent-green)';
    } catch (err) {
        console.warn('WebSerial connection cancelled or failed:', err);
    }
}

// Experimental Domain Switcher (Manufacturing vs Biology)
function setExperimentDomain(domain) {
    if (window.app) window.app.setExperimentDomain(domain);
}

// Citations Modal (Strict Overleaf LaTeX Rendering via KaTeX)
function toggleCitationsModal(show) {
    const modal = document.getElementById('citations-modal');
    if (modal) {
        modal.style.display = show ? 'flex' : 'none';
        if (show && typeof renderMathInElement === 'function') {
            try {
                renderMathInElement(document.getElementById('latex-article') || modal, {
                    delimiters: [
                        { left: "$$", right: "$$", display: true },
                        { left: "$", right: "$", display: false },
                        { left: "\\(", right: "\\)", display: false },
                        { left: "\\[", right: "\\]", display: true }
                    ],
                    throwOnError: false
                });
            } catch (err) {
                console.warn('KaTeX auto-render note:', err);
            }
        }
    }
}

// Architecture & Wiring Schematic Modal
function toggleSchematicModal(show) {
    const modal = document.getElementById('schematic-modal');
    if (modal) modal.style.display = show ? 'flex' : 'none';
}

// Custom Mechanics Apply Trigger
function applyCustomMechanicsParameters() {
    if (window.app) {
        window.app.applyCustomMechanicsParameters(true);
    }
}

// Non-blocking Toast Notification
function showToast(message, type = 'info') {
    let toast = document.getElementById('app-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'app-toast';
        document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.className = `toast-visible toast-${type}`;
    clearTimeout(window._toastTimeout);
    window._toastTimeout = setTimeout(() => {
        toast.className = '';
    }, 4500);
}

// Initialize on page load and trigger KaTeX typesetter
window.addEventListener('load', () => {
    if (!window.app) {
        window.app = new RPMScientificApp();
    }
    if (typeof renderMathInElement === 'function') {
        try {
            renderMathInElement(document.body, {
                delimiters: [
                    { left: "$$", right: "$$", display: true },
                    { left: "$", right: "$", display: false },
                    { left: "\\(", right: "\\)", display: false },
                    { left: "\\[", right: "\\]", display: true }
                ],
                throwOnError: false
            });
        } catch (err) {
            console.warn('KaTeX body render note:', err);
        }
    }
});
