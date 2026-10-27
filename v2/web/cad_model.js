/**
 * IIST RPM CAD 3D Scene Builder.
 * Accurately models the exact mechanical assembly from Final_Drawing.pdf (MTECH2025)
 * and Microgravity_Simulation.pptx (Dr. V S Sooraj, Dept of Aerospace Engineering).
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

        // Assemblies
        this.outerFrameGroup = new THREE.Group();
        this.innerFrameGroup = new THREE.Group();
        this.payloadGroup = new THREE.Group();

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
        const aFrameThick = 0.0254; // 1-inch plate
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

        // =====================================================================
        // PART 4: OUTER SHAFTS (Ø20 mm x 151 mm) & BEARINGS (PART 8)
        // =====================================================================
        const shaftRadius = 0.010; // Ø20 mm
        const outerShaftGeom = new THREE.CylinderGeometry(shaftRadius, shaftRadius, 0.151, 24);
        outerShaftGeom.rotateZ(Math.PI / 2.0);

        const leftShaft = new THREE.Mesh(outerShaftGeom, this.shaftMat);
        leftShaft.position.set(-standXOffset + 0.06, 0.045 + aFrameHeight, 0.0);
        this.scene.add(leftShaft);

        const rightShaft = new THREE.Mesh(outerShaftGeom, this.shaftMat);
        rightShaft.position.set(standXOffset - 0.06, 0.045 + aFrameHeight, 0.0);
        this.scene.add(rightShaft);

        // Pillow block bearing housings (Part 8)
        this.addBearingHousing(leftStand, 0, aFrameHeight, 0);
        this.addBearingHousing(rightStand, 0, aFrameHeight, 0);

        // =====================================================================
        // PART 5: OUTER FRAME (500 x 500 x 50.8 mm Al6061)
        // =====================================================================
        // Center of rotation at (0, 0.045 + aFrameHeight, 0)
        this.outerFrameGroup.position.set(0.0, 0.045 + aFrameHeight, 0.0);
        this.scene.add(this.outerFrameGroup);

        const outerFrameMesh = this.createHollowSquareFrame(0.50, 0.0508, 0.050); // 500mm outer, 50.8mm thick, 50mm profile
        this.outerFrameGroup.add(outerFrameMesh);

        // NEMA 23 Stepper Motor on Outer Frame for Inner Gimbal Drive (Slide 11)
        const nema23 = this.createNemaMotor(0.057, 0.057, 0.076); // NEMA 23 (57x57x76 mm)
        nema23.position.set(0.0, 0.25 + 0.045, 0.0);
        this.outerFrameGroup.add(nema23);

        // Slip Ring Cylinder on Outer Shaft
        const slipRingGeom = new THREE.CylinderGeometry(0.018, 0.018, 0.045, 20);
        slipRingGeom.rotateZ(Math.PI / 2.0);
        const slipRingMesh = new THREE.Mesh(slipRingGeom, this.brassMat);
        slipRingMesh.position.set(standXOffset - 0.09, 0, 0);
        this.outerFrameGroup.add(slipRingMesh);

        // =====================================================================
        // PART 6: INNER FRAME (350 x 350 x 50.8 mm Al6061) & INNER SHAFTS (PART 7)
        // =====================================================================
        this.innerFrameGroup.position.set(0.0, 0.0, 0.0);
        this.outerFrameGroup.add(this.innerFrameGroup);

        const innerFrameMesh = this.createHollowSquareFrame(0.35, 0.0508, 0.045); // 350mm outer, 50.8mm thick, 45mm profile
        this.innerFrameGroup.add(innerFrameMesh);

        // Inner frame shafts (Ø20 mm x 160 mm) along Y-axis
        const innerShaftGeom = new THREE.CylinderGeometry(shaftRadius, shaftRadius, 0.160, 24);
        const topInnerShaft = new THREE.Mesh(innerShaftGeom, this.shaftMat);
        topInnerShaft.position.set(0.0, 0.20, 0.0);
        this.innerFrameGroup.add(topInnerShaft);

        const botInnerShaft = new THREE.Mesh(innerShaftGeom, this.shaftMat);
        botInnerShaft.position.set(0.0, -0.20, 0.0);
        this.innerFrameGroup.add(botInnerShaft);

        // =====================================================================
        // PART 9: PAYLOAD SUPPORT RODS (Ø10 mm x 350 mm)
        // =====================================================================
        const rodRadius = 0.005; // Ø10 mm
        const rodGeom = new THREE.CylinderGeometry(rodRadius, rodRadius, 0.35, 16);
        rodGeom.rotateZ(Math.PI / 2.0);

        const frontRod = new THREE.Mesh(rodGeom, this.shaftMat);
        frontRod.position.set(0.0, 0.0375, 0.0);
        this.innerFrameGroup.add(frontRod);

        const backRod = new THREE.Mesh(rodGeom, this.shaftMat);
        backRod.position.set(0.0, -0.0375, 0.0);
        this.innerFrameGroup.add(backRod);

        // =====================================================================
        // PART 3: PAYLOAD HOLDER (200 x 200 mm Polycarbonate with 120 mm Chamber)
        // =====================================================================
        this.payloadGroup.position.set(0.0, 0.0, 0.0);
        this.innerFrameGroup.add(this.payloadGroup);

        // Outer transparent cube (200 mm)
        const payloadOuterGeom = new THREE.BoxGeometry(0.20, 0.20, 0.20);
        const payloadOuterMesh = new THREE.Mesh(payloadOuterGeom, this.polycarbMat);
        this.payloadGroup.add(payloadOuterMesh);

        // Inner hollow chamber cavity (120 mm)
        const cavityGeom = new THREE.BoxGeometry(0.12, 0.12, 0.12);
        const cavityEdges = new THREE.EdgesGeometry(cavityGeom);
        const cavityWire = new THREE.LineSegments(cavityEdges, new THREE.LineBasicMaterial({ color: 0x2563eb, linewidth: 1.5 }));
        this.payloadGroup.add(cavityWire);

        // Biological Specimen / Culture Plate in Center of Chamber
        const specimenGeom = new THREE.CylinderGeometry(0.045, 0.045, 0.012, 24);
        const specimenMesh = new THREE.Mesh(specimenGeom, this.specimenMat);
        specimenMesh.position.set(0.0, -0.02, 0.0);
        this.payloadGroup.add(specimenMesh);
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

        // Top bearing mounting plate (Detail A from drawing)
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
        // Anodized body
        const bodyGeom = new THREE.BoxGeometry(width, height, length);
        const bodyMesh = new THREE.Mesh(bodyGeom, this.motorMat);
        motorGroup.add(bodyMesh);

        // Aluminum faceplate
        const faceGeom = new THREE.BoxGeometry(width * 1.02, height * 1.02, 0.006);
        const faceMesh = new THREE.Mesh(faceGeom, this.aluminumMat);
        faceMesh.position.set(0.0, 0.0, length / 2.0);
        motorGroup.add(faceMesh);

        // Shaft output
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
        // Outer gimbal rotates about the horizontal shaft (X-axis in this scene orientation)
        this.outerFrameGroup.rotation.x = THREE.MathUtils.degToRad(psi_deg);

        // Inner gimbal rotates about its own orthogonal axis (Y-axis of inner frame)
        this.innerFrameGroup.rotation.y = THREE.MathUtils.degToRad(phi_deg);
    }
}
