/**
 * IIST RPM CAD 3D Scene Builder.
 * Accurately models the exact mechanical assembly from Final_Drawing.pdf (MTECH2025)
 * and Microgravity_Simulation.pptx (Dr. V S Sooraj, Dept of Aerospace Engineering).
 * Supports live dynamic enclosure bounding boxes, sample probe points, and axis tilts.
 */

class RPMCadAssembly {
    constructor(scene) {
        this.scene = scene;
        
        // Materials (Engineering grade)
        this.steelMat = new THREE.MeshStandardMaterial({
            color: 0x475569,       // IS2062 E250 Structural Steel
            metalness: 0.7,
            roughness: 0.35
        });

        this.aluminumMat = new THREE.MeshStandardMaterial({
            color: 0xe2e8f0,       // Al6061-T6 Brushed Aluminum
            metalness: 0.85,
            roughness: 0.25
        });

        this.shaftMat = new THREE.MeshStandardMaterial({
            color: 0x94a3b8,       // Precision Ground Steel Shaft
            metalness: 0.9,
            roughness: 0.15
        });

        this.brassMat = new THREE.MeshStandardMaterial({
            color: 0xd97706,       // Slip Ring Brass
            metalness: 0.8,
            roughness: 0.3
        });

        this.motorMat = new THREE.MeshStandardMaterial({
            color: 0x1e293b,       // NEMA Stepper Motor Black Anodized Body
            metalness: 0.4,
            roughness: 0.5
        });

        this.polycarbMat = new THREE.MeshPhysicalMaterial({
            color: 0xffffff,       // Optical Polycarbonate Chamber
            transparent: true,
            opacity: 0.5,
            roughness: 0.1,
            metalness: 0.05,
            transmission: 0.85,
            ior: 1.586
        });

        this.specimenMat = new THREE.MeshStandardMaterial({
            color: 0x059669,       // Biological Culture Specimen / Petri Dish
            roughness: 0.4
        });

        this.probeMat = new THREE.MeshStandardMaterial({
            color: 0xe11d48,       // Probe point marker (crimson red)
            roughness: 0.2,
            metalness: 0.1
        });

        // Assemblies
        this.outerGimbalBaseGroup = new THREE.Group();
        this.outerFrameGroup = new THREE.Group();
        this.innerGimbalBaseGroup = new THREE.Group();
        this.innerFrameGroup = new THREE.Group();
        this.payloadGroup = new THREE.Group();
        this.probePointsGroup = new THREE.Group();
        this.enclosureMesh = null;

        this.innerTilt = 0;
        this.outerTilt = 0;

        this.buildAssembly();
    }

    buildAssembly() {
        // =====================================================================
        // PART 1: BASE PLATE (1200 x 900 x 45 mm)
        // =====================================================================
        // Scale: 1 unit = 1 meter
        const baseGeom = new THREE.BoxGeometry(1.20, 0.045, 0.90);
        const baseMesh = new THREE.Mesh(baseGeom, this.steelMat);
        baseMesh.position.y = 0.045 / 2.0;
        baseMesh.castShadow = true;
        baseMesh.receiveShadow = true;
        this.scene.add(baseMesh);

        // Mounting holes / slots on baseplate
        const baseLineGeom = new THREE.EdgesGeometry(baseGeom);
        const baseLine = new THREE.LineSegments(baseLineGeom, new THREE.LineBasicMaterial({ color: 0x334155 }));
        baseMesh.add(baseLine);

        // =====================================================================
        // PART 2: A-FRAME SIDE SUPPORTS (2 Stands, Height 490.9 mm, Thick 25.4 mm)
        // =====================================================================
        const aFrameHeight = 0.491;
        const standXOffset = 0.38;  // Half-span distance between side supports (~760 mm span)

        const leftStand = this.createAFrameStand();
        leftStand.position.set(-standXOffset, 0.045, 0.0);
        this.scene.add(leftStand);

        const rightStand = this.createAFrameStand();
        rightStand.position.set(standXOffset, 0.045, 0.0);
        this.scene.add(rightStand);

        // NEMA 34 Stepper Motor on Left Stand (Slide 11 & 13)
        const nema34 = this.createNemaMotor(0.086, 0.086, 0.115); // NEMA 34 (86x86x115 mm)
        nema34.position.set(-standXOffset - 0.08, 0.045 + aFrameHeight, 0.0);
        nema34.rotation.z = Math.PI / 2.0;
        this.scene.add(nema34);

        // Outer Gimbals Center of Rotation
        const centerPivotY = 0.045 + aFrameHeight;
        this.outerGimbalBaseGroup.position.set(0.0, centerPivotY, 0.0);
        this.scene.add(this.outerGimbalBaseGroup);

        this.outerGimbalBaseGroup.add(this.outerFrameGroup);

        // =====================================================================
        // PART 4 & 5: OUTER DRIVE SHAFT (Ø20 mm) & OUTER FRAME (500 x 500 x 50.8 mm)
        // =====================================================================
        // Outer drive shaft spanning from stands to outer frame
        const outerShaftGeom = new THREE.CylinderGeometry(0.010, 0.010, standXOffset * 2.0, 24);
        outerShaftGeom.rotateZ(Math.PI / 2.0);
        const outerShaft = new THREE.Mesh(outerShaftGeom, this.shaftMat);
        this.outerFrameGroup.add(outerShaft);

        // Slip rings on outer shaft
        const slipRing1 = new THREE.Mesh(new THREE.CylinderGeometry(0.018, 0.018, 0.035, 20), this.brassMat);
        slipRing1.rotation.z = Math.PI / 2.0;
        slipRing1.position.x = -standXOffset + 0.06;
        this.outerFrameGroup.add(slipRing1);

        // Outer gimbal frame: 500 x 500 mm, thickness 50.8 mm, profile face 50 mm
        const outerFrameMesh = this.createHollowSquareFrame(0.50, 0.0508, 0.050);
        this.outerFrameGroup.add(outerFrameMesh);

        // NEMA 23 Stepper Motor on Outer Frame to drive Inner Frame (Slide 11 & 13)
        const nema23 = this.createNemaMotor(0.057, 0.057, 0.076); // NEMA 23 (57x57x76 mm)
        nema23.position.set(0.0, 0.50 / 2.0 + 0.045, 0.0);
        this.outerFrameGroup.add(nema23);

        // Bearings on outer frame
        this.addBearingHousing(this.outerFrameGroup, 0.0, 0.50 / 2.0, 0.0);
        this.addBearingHousing(this.outerFrameGroup, 0.0, -0.50 / 2.0, 0.0);

        // =====================================================================
        // PART 6: INNER FRAME (350 x 350 x 50.8 mm, Al6061)
        // =====================================================================
        this.outerFrameGroup.add(this.innerGimbalBaseGroup);
        this.innerGimbalBaseGroup.add(this.innerFrameGroup);

        // Inner drive shaft spanning vertically (Y-axis)
        const innerShaftGeom = new THREE.CylinderGeometry(0.010, 0.010, 0.44, 24);
        const innerShaft = new THREE.Mesh(innerShaftGeom, this.shaftMat);
        this.innerFrameGroup.add(innerShaft);

        // Inner gimbal frame: 350 x 350 mm, thickness 50.8 mm, profile face 45 mm
        const innerFrameMesh = this.createHollowSquareFrame(0.35, 0.0508, 0.045);
        this.innerFrameGroup.add(innerFrameMesh);

        // =====================================================================
        // PART 9: PAYLOAD SUPPORT RODS (2x Ø10 mm x 350 mm SS rods spanning frame)
        // =====================================================================
        const rodGeom = new THREE.CylinderGeometry(0.005, 0.005, 0.35, 16);
        const rod1 = new THREE.Mesh(rodGeom, this.shaftMat);
        rod1.position.set(-0.06, 0.0, 0.0);
        this.innerFrameGroup.add(rod1);

        const rod2 = new THREE.Mesh(rodGeom, this.shaftMat);
        rod2.position.set(0.06, 0.0, 0.0);
        this.innerFrameGroup.add(rod2);

        // =====================================================================
        // PART 3: PAYLOAD HOLDER CUBE (200 x 200 mm Optical Polycarbonate)
        // =====================================================================
        this.innerFrameGroup.add(this.payloadGroup);
        this.payloadGroup.add(this.probePointsGroup);

        this.buildPayloadCube(0.20, 0.20, 0.20);
    }

    buildPayloadCube(w, h, d) {
        if (this.payloadMesh) {
            this.payloadGroup.remove(this.payloadMesh);
        }
        const cubeGeom = new THREE.BoxGeometry(w, h, d);
        this.payloadMesh = new THREE.Mesh(cubeGeom, this.polycarbMat);
        
        // Chamfer edge lines
        const cubeEdges = new THREE.EdgesGeometry(cubeGeom);
        const cubeLines = new THREE.LineSegments(cubeEdges, new THREE.LineBasicMaterial({ color: 0x60a5fa, transparent: true, opacity: 0.6 }));
        this.payloadMesh.add(cubeLines);

        // Internal specimen cavity
        const cavityGeom = new THREE.BoxGeometry(w * 0.6, h * 0.6, d * 0.6);
        const cavityEdges = new THREE.EdgesGeometry(cavityGeom);
        const cavityWire = new THREE.LineSegments(cavityEdges, new THREE.LineBasicMaterial({ color: 0x2563eb, linewidth: 1.5 }));
        this.payloadMesh.add(cavityWire);

        // Biological Specimen / Culture Plate in Center of Chamber
        const specimenGeom = new THREE.CylinderGeometry(w * 0.22, w * 0.22, 0.012, 24);
        const specimenMesh = new THREE.Mesh(specimenGeom, this.specimenMat);
        specimenMesh.position.set(0.0, -h * 0.1, 0.0);
        this.payloadMesh.add(specimenMesh);

        this.payloadGroup.add(this.payloadMesh);
    }

    createAFrameStand() {
        const standGroup = new THREE.Group();
        const thickness = 0.0254; // 1 inch steel sheet (Slide 12)
        const height = 0.491;     // 490.9 mm
        const baseWidth = 0.50;   // Footprint span

        // Two diagonal structural legs forming 90-degree A-frame
        const legGeom = new THREE.BoxGeometry(thickness, height, 0.06);
        
        const leftLeg = new THREE.Mesh(legGeom, this.steelMat);
        leftLeg.position.set(0.0, height / 2.0, -baseWidth / 4.0);
        leftLeg.rotation.x = 0.35;
        standGroup.add(leftLeg);

        const rightLeg = new THREE.Mesh(legGeom, this.steelMat);
        rightLeg.position.set(0.0, height / 2.0, baseWidth / 4.0);
        rightLeg.rotation.x = -0.35;
        standGroup.add(rightLeg);

        // Top bearing mounting plate
        const headGeom = new THREE.BoxGeometry(thickness * 1.5, 0.09, 0.12);
        const headMesh = new THREE.Mesh(headGeom, this.steelMat);
        headMesh.position.set(0.0, height, 0.0);
        standGroup.add(headMesh);

        return standGroup;
    }

    createHollowSquareFrame(outerSize, thickness, profileWidth) {
        const frameGroup = new THREE.Group();
        const halfSize = outerSize / 2.0;
        const halfProfile = profileWidth / 2.0;
        const innerLen = outerSize - 2.0 * profileWidth;

        // Top bar
        const hBarGeom = new THREE.BoxGeometry(outerSize, profileWidth, thickness);
        const topBar = new THREE.Mesh(hBarGeom, this.aluminumMat);
        topBar.position.set(0.0, halfSize - halfProfile, 0.0);
        frameGroup.add(topBar);

        // Bottom bar
        const botBar = new THREE.Mesh(hBarGeom, this.aluminumMat);
        botBar.position.set(0.0, -halfSize + halfProfile, 0.0);
        frameGroup.add(botBar);

        // Left bar
        const vBarGeom = new THREE.BoxGeometry(profileWidth, innerLen, thickness);
        const leftBar = new THREE.Mesh(vBarGeom, this.aluminumMat);
        leftBar.position.set(-halfSize + halfProfile, 0.0, 0.0);
        frameGroup.add(leftBar);

        // Right bar
        const rightBar = new THREE.Mesh(vBarGeom, this.aluminumMat);
        rightBar.position.set(halfSize - halfProfile, 0.0, 0.0);
        frameGroup.add(rightBar);

        // Edge line highlights
        const edgesGeom = new THREE.EdgesGeometry(new THREE.BoxGeometry(outerSize, outerSize, thickness));
        const edges = new THREE.LineSegments(edgesGeom, new THREE.LineBasicMaterial({ color: 0x94a3b8 }));
        frameGroup.add(edges);

        return frameGroup;
    }

    createNemaMotor(width, height, length) {
        const motorGroup = new THREE.Group();
        const bodyGeom = new THREE.BoxGeometry(width, height, length);
        const bodyMesh = new THREE.Mesh(bodyGeom, this.motorMat);
        motorGroup.add(bodyMesh);

        const faceGeom = new THREE.BoxGeometry(width * 1.02, height * 1.02, 0.006);
        const faceMesh = new THREE.Mesh(faceGeom, this.aluminumMat);
        faceMesh.position.set(0.0, 0.0, length / 2.0);
        motorGroup.add(faceMesh);

        const shaftGeom = new THREE.CylinderGeometry(0.005, 0.005, 0.025, 16);
        shaftGeom.rotateX(Math.PI / 2.0);
        const shaftMesh = new THREE.Mesh(shaftGeom, this.shaftMat);
        shaftMesh.position.set(0.0, 0.0, length / 2.0 + 0.0125);
        motorGroup.add(shaftMesh);

        return motorGroup;
    }

    addBearingHousing(parentGroup, x, y, z) {
        const housingGeom = new THREE.BoxGeometry(0.045, 0.065, 0.065);
        const housingMesh = new THREE.Mesh(housingGeom, this.steelMat);
        housingMesh.position.set(x, y, z);
        parentGroup.add(housingMesh);

        const boreGeom = new THREE.CylinderGeometry(0.012, 0.012, 0.046, 20);
        boreGeom.rotateZ(Math.PI / 2.0);
        const boreMesh = new THREE.Mesh(boreGeom, this.shaftMat);
        boreMesh.position.set(x, y, z);
        parentGroup.add(boreMesh);
    }

    updateRotations(phi_deg, psi_deg) {
        // Outer gimbal rotates about the horizontal shaft (X-axis)
        this.outerFrameGroup.rotation.x = THREE.MathUtils.degToRad(psi_deg);

        // Inner gimbal rotates about vertical axis (Y-axis of inner frame)
        this.innerFrameGroup.rotation.y = THREE.MathUtils.degToRad(phi_deg);
    }

    updateAxisTilts(innerTilt_deg, outerTilt_deg) {
        this.innerTilt = innerTilt_deg;
        this.outerTilt = outerTilt_deg;

        // Apply tilt to outer gimbal base
        this.outerGimbalBaseGroup.rotation.z = THREE.MathUtils.degToRad(outerTilt_deg);

        // Apply tilt to inner gimbal base relative to outer frame
        this.innerGimbalBaseGroup.rotation.z = THREE.MathUtils.degToRad(innerTilt_deg);
    }

    updateEnclosureBox(w_cm, h_cm, d_cm, show) {
        if (this.enclosureMesh) {
            this.payloadGroup.remove(this.enclosureMesh);
            this.enclosureMesh = null;
        }

        if (show) {
            const w = w_cm / 100.0;
            const h = h_cm / 100.0;
            const d = d_cm / 100.0;

            const boxGeom = new THREE.BoxGeometry(w, h, d);
            const boxEdges = new THREE.EdgesGeometry(boxGeom);
            this.enclosureMesh = new THREE.LineSegments(
                boxEdges,
                new THREE.LineBasicMaterial({ color: 0xd97706, linewidth: 2 })
            );
            this.payloadGroup.add(this.enclosureMesh);
        }
    }

    updatePayloadDimensions(w_cm, h_cm, d_cm, show) {
        if (!show) {
            if (this.payloadMesh) this.payloadMesh.visible = false;
        } else {
            if (this.payloadMesh) this.payloadMesh.visible = true;
            this.buildPayloadCube(w_cm / 100.0, h_cm / 100.0, d_cm / 100.0);
        }
    }

    updateSamplePoints(pointsArray) {
        // Clear old probe meshes
        while (this.probePointsGroup.children.length > 0) {
            this.probePointsGroup.remove(this.probePointsGroup.children[0]);
        }

        // Add probe sphere markers
        const sphereGeom = new THREE.SphereGeometry(0.008, 16, 16);
        for (const pt of pointsArray) {
            const mesh = new THREE.Mesh(sphereGeom, this.probeMat);
            // Coordinates in cm converted to meters
            mesh.position.set(pt.x / 100.0, pt.y / 100.0, pt.z / 100.0);
            this.probePointsGroup.add(mesh);
        }
    }
}
