/**
 * 3D Interactive Pearl-White & Neon-Blue Robot Widget (Three.js)
 * High-detail Spline-inspired model for Hero Banner Analytics Overview
 */
function initRobotWidget() {
  const container =
    document.getElementById('hero-robot-container') ||
    document.getElementById('sidebar-robot-container');
  if (!container || !window.THREE) return;

  // --- Scene Setup ---
  const scene = new THREE.Scene();

  const getWidth = () => container.clientWidth || 240;
  const getHeight = () => container.clientHeight || 196;

  // Camera calibrated so the entire 3-tier pedestal + neck + head fit with generous margin
  const camera = new THREE.PerspectiveCamera(32, getWidth() / getHeight(), 0.1, 100);
  camera.position.set(0, -0.02, 7.15);

  // Renderer (100% Transparent + ACES Filmic Tone Mapping to prevent blown-out white)
  const renderer = new THREE.WebGLRenderer({
    alpha: true,
    antialias: true,
    powerPreference: 'high-performance'
  });
  renderer.setClearColor(0x000000, 0);
  renderer.setSize(getWidth(), getHeight());
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.02;
  if (THREE.sRGBEncoding) {
    renderer.outputEncoding = THREE.sRGBEncoding;
  }

  container.innerHTML = '';
  container.appendChild(renderer.domElement);

  // --- Procedural Studio Environment Map (Gives realistic 3D shading & bevel highlights) ---
  try {
    const envCanvas = document.createElement('canvas');
    envCanvas.width = 256;
    envCanvas.height = 128;
    const envCtx = envCanvas.getContext('2d');

    // Studio gradient: soft white top-left, cool slate midtone, deep navy bottom
    const bgGrad = envCtx.createLinearGradient(0, 0, 0, 128);
    bgGrad.addColorStop(0.0, '#ffffff');
    bgGrad.addColorStop(0.28, '#cbd5e1');
    bgGrad.addColorStop(0.55, '#475569');
    bgGrad.addColorStop(0.82, '#1e293b');
    bgGrad.addColorStop(1.0, '#0f172a');
    envCtx.fillStyle = bgGrad;
    envCtx.fillRect(0, 0, 256, 128);

    // Studio softbox highlights
    const spot1 = envCtx.createRadialGradient(75, 28, 4, 75, 28, 52);
    spot1.addColorStop(0, 'rgba(255, 255, 255, 0.95)');
    spot1.addColorStop(1, 'rgba(255, 255, 255, 0)');
    envCtx.fillStyle = spot1;
    envCtx.fillRect(0, 0, 256, 128);

    // Cyan rim accent in environment
    const spot2 = envCtx.createRadialGradient(200, 56, 4, 200, 56, 48);
    spot2.addColorStop(0, 'rgba(0, 240, 255, 0.65)');
    spot2.addColorStop(1, 'rgba(0, 240, 255, 0)');
    envCtx.fillStyle = spot2;
    envCtx.fillRect(0, 0, 256, 128);

    const envTex = new THREE.CanvasTexture(envCanvas);
    envTex.mapping = THREE.EquirectangularReflectionMapping;

    const pmremGenerator = new THREE.PMREMGenerator(renderer);
    pmremGenerator.compileEquirectangularShader();
    const envMap = pmremGenerator.fromEquirectangular(envTex).texture;
    scene.environment = envMap;
    envTex.dispose();
    pmremGenerator.dispose();
  } catch (e) {
    // Fallback if PMREM unavailable
  }

  // --- Helper: High-Precision Rounded Box Geometry ---
  function createRoundedBox(width, height, depth, radius, smoothness) {
    const shape = new THREE.Shape();
    const eps = 0.00001;
    const r = Math.min(radius, width / 2 - 0.001, height / 2 - 0.001, depth / 2 - 0.001);
    const radiusMinusEps = Math.max(0.001, r - eps);

    shape.absarc(-width / 2 + r, -height / 2 + r, radiusMinusEps, Math.PI, (3 * Math.PI) / 2, false);
    shape.absarc(width / 2 - r, -height / 2 + r, radiusMinusEps, (3 * Math.PI) / 2, 2 * Math.PI, false);
    shape.absarc(width / 2 - r, height / 2 - r, radiusMinusEps, 0, Math.PI / 2, false);
    shape.absarc(-width / 2 + r, height / 2 - r, radiusMinusEps, Math.PI / 2, Math.PI, false);

    const extrudeSettings = {
      depth: Math.max(0.001, depth - r * 2),
      bevelEnabled: true,
      bevelSegments: smoothness * 2,
      steps: 1,
      bevelSize: radiusMinusEps,
      bevelThickness: r,
      curveSegments: smoothness * 2
    };

    const geom = new THREE.ExtrudeGeometry(shape, extrudeSettings);
    geom.center();
    geom.computeVertexNormals();
    return geom;
  }

  // --- Carefully Balanced Multi-Tone Materials ---
  // 1. Satin Pearl White (Main helmet & pedestal plates - rich 3D shading, not flat white)
  const pearlWhiteMat = new THREE.MeshStandardMaterial({
    color: 0xe4ecf5,
    roughness: 0.24,
    metalness: 0.12
  });

  // 2. Brushed Silver-Slate Trim (Recessed visor bezel & collar rings)
  const silverTrimMat = new THREE.MeshStandardMaterial({
    color: 0x94a3b8,
    roughness: 0.26,
    metalness: 0.72
  });

  // 3. Anodized Dark Titanium (Mechanical joints, ear dials, middle pedestal step)
  const darkTitaniumMat = new THREE.MeshStandardMaterial({
    color: 0x1e293b,
    roughness: 0.30,
    metalness: 0.85
  });

  // 4. Deep Obsidian Glass Visor
  const visorGlassMat = new THREE.MeshStandardMaterial({
    color: 0x050811,
    roughness: 0.06,
    metalness: 0.92
  });

  // 5. Electric Neon Cyan (Eyes & LED Accents)
  const neonCyanMat = new THREE.MeshBasicMaterial({
    color: 0x00e5ff
  });

  // 6. Bright Cyan-White Core (Inner eye intensity)
  const eyeCoreMat = new THREE.MeshBasicMaterial({
    color: 0xd8ffff
  });

  // 7. Pure White Catchlight (Cute eye sparkle dot)
  const catchlightMat = new THREE.MeshBasicMaterial({
    color: 0xffffff
  });

  // 8. Subtle Glass Sheen Material
  const glassSheenMat = new THREE.MeshBasicMaterial({
    color: 0x38bdf8,
    transparent: true,
    opacity: 0.09
  });

  // --- Studio 3-Point Lighting (Tuned for 3D Depth & Contour Separation) ---
  // Hemisphere light provides natural top-to-bottom shading gradient
  const hemiLight = new THREE.HemisphereLight(0xf1f5f9, 0x0f172a, 0.55);
  scene.add(hemiLight);

  // Main key light (Front-Top-Left)
  const keyLight = new THREE.DirectionalLight(0xffffff, 0.95);
  keyLight.position.set(-2.8, 4.5, 5.0);
  scene.add(keyLight);

  // Neon Cyan Rim Light (Back-Left - highlights the left edge of head & pedestal)
  const cyanRimLight = new THREE.DirectionalLight(0x00f0ff, 1.35);
  cyanRimLight.position.set(-5.0, 2.2, -2.5);
  scene.add(cyanRimLight);

  // Cool Indigo-Blue Rim Light (Back-Right - gives 3D volume to the right side)
  const rightRimLight = new THREE.DirectionalLight(0x60a5fa, 0.95);
  rightRimLight.position.set(5.0, 1.8, -2.0);
  scene.add(rightRimLight);

  // Subtle Teal Bottom Bounce Light
  const bottomBounce = new THREE.DirectionalLight(0x2dd4bf, 0.35);
  bottomBounce.position.set(0, -4.0, 2.0);
  scene.add(bottomBounce);

  // =========================================================================
  // CHARACTER HIERARCHY (Spline-Style Stepped Base + Mechanical Neck + Head)
  // =========================================================================
  const robotRoot = new THREE.Group();
  robotRoot.position.y = -0.05;
  scene.add(robotRoot);

  // --- 1. 3-TIER STEPPED PEDESTAL BASE (Spline Reference Style) ---
  const pedestalGroup = new THREE.Group();
  robotRoot.add(pedestalGroup);

  // Lower Shadow Foot (grounds the pedestal)
  const subFoot = new THREE.Mesh(
    createRoundedBox(1.75, 0.12, 1.45, 0.04, 3),
    darkTitaniumMat
  );
  subFoot.position.y = -1.24;
  pedestalGroup.add(subFoot);

  // Tier 1: Bottom Wide Chamfered Platform (Pearl White)
  const baseTier1 = new THREE.Mesh(
    createRoundedBox(2.32, 0.34, 1.92, 0.09, 5),
    pearlWhiteMat
  );
  baseTier1.position.y = -1.03;
  pedestalGroup.add(baseTier1);

  // Glowing Neon Cyan LED Seam between Tier 1 & Tier 2
  const baseLedSeam = new THREE.Mesh(
    createRoundedBox(1.74, 0.035, 1.44, 0.015, 3),
    neonCyanMat
  );
  baseLedSeam.position.y = -0.84;
  pedestalGroup.add(baseLedSeam);

  // Tier 2: Middle Stepped Platform (Anodized Dark Titanium for contrast)
  const baseTier2 = new THREE.Mesh(
    createRoundedBox(1.66, 0.18, 1.36, 0.06, 4),
    darkTitaniumMat
  );
  baseTier2.position.y = -0.74;
  pedestalGroup.add(baseTier2);

  // Tier 3: Top Pedestal Deck (Pearl White)
  const baseTier3 = new THREE.Mesh(
    createRoundedBox(1.12, 0.14, 0.96, 0.045, 4),
    pearlWhiteMat
  );
  baseTier3.position.y = -0.59;
  pedestalGroup.add(baseTier3);

  // --- 2. ARTICULATED MECHANICAL NECK (Inverted Cup + Hydraulic Struts) ---
  const neckGroup = new THREE.Group();
  neckGroup.position.y = -0.52;
  robotRoot.add(neckGroup);

  // Base Mounting Collar
  const neckBaseCollar = new THREE.Mesh(
    new THREE.CylinderGeometry(0.36, 0.42, 0.10, 32),
    silverTrimMat
  );
  neckBaseCollar.position.y = 0.04;
  neckGroup.add(neckBaseCollar);

  // Glowing Cyan Power Core Ring
  const neckPowerRing = new THREE.Mesh(
    new THREE.TorusGeometry(0.28, 0.025, 16, 32),
    neonCyanMat
  );
  neckPowerRing.rotation.x = Math.PI / 2;
  neckPowerRing.position.y = 0.10;
  neckGroup.add(neckPowerRing);

  // 3 Vertical Hydraulic Micro-Struts (Matches the Spline neck detail!)
  const strutGeom = new THREE.CylinderGeometry(0.032, 0.032, 0.22, 12);
  for (let i = 0; i < 3; i++) {
    const angle = (i * Math.PI * 2) / 3 + Math.PI / 6;
    const strut = new THREE.Mesh(strutGeom, silverTrimMat);
    strut.position.set(Math.cos(angle) * 0.14, 0.18, Math.sin(angle) * 0.14);
    neckGroup.add(strut);
  }

  // Central Dark Titanium Core Rod
  const centerRod = new THREE.Mesh(
    new THREE.CylinderGeometry(0.09, 0.11, 0.24, 24),
    darkTitaniumMat
  );
  centerRod.position.y = 0.18;
  neckGroup.add(centerRod);

  // Tapered Upper Neck Cup (Inverted Cone in Pearl White)
  const neckCup = new THREE.Mesh(
    new THREE.CylinderGeometry(0.20, 0.30, 0.26, 32),
    pearlWhiteMat
  );
  neckCup.position.y = 0.36;
  neckGroup.add(neckCup);

  // Upper Neck Joint Ring
  const neckTopRing = new THREE.Mesh(
    new THREE.TorusGeometry(0.21, 0.04, 16, 32),
    darkTitaniumMat
  );
  neckTopRing.rotation.x = Math.PI / 2;
  neckTopRing.position.y = 0.49;
  neckGroup.add(neckTopRing);

  // --- 3. DETAILED ROUNDED MONITOR HEAD ---
  const headPivot = new THREE.Group();
  headPivot.position.set(0, -0.02, 0);
  robotRoot.add(headPivot);

  const headGroup = new THREE.Group();
  headGroup.position.set(0, 0.56, 0);
  headPivot.add(headGroup);

  // Main Rounded Rectangular Helmet (Pearl White)
  const headShell = new THREE.Mesh(
    createRoundedBox(2.02, 1.34, 1.44, 0.29, 6),
    pearlWhiteMat
  );
  headGroup.add(headShell);

  // Top Sculpted Sensor Cap (Forehead / Crown Detail)
  const topSensorCap = new THREE.Mesh(
    createRoundedBox(0.68, 0.08, 0.48, 0.03, 3),
    silverTrimMat
  );
  topSensorCap.position.set(0, 0.69, 0.05);
  headGroup.add(topSensorCap);

  // Tiny Glowing Cyan Status Pill on Top Cap
  const topLedPill = new THREE.Mesh(
    createRoundedBox(0.22, 0.028, 0.04, 0.01, 2),
    neonCyanMat
  );
  topLedPill.position.set(0, 0.70, 0.28);
  headGroup.add(topLedPill);

  // Recessed Brushed Silver-Slate Visor Bezel Frame (Creates 3D depth lip)
  const visorBezel = new THREE.Mesh(
    createRoundedBox(1.78, 1.10, 0.12, 0.22, 5),
    silverTrimMat
  );
  visorBezel.position.z = 0.68;
  headGroup.add(visorBezel);

  // Deep Obsidian Glossy Glass Visor Screen
  const visorScreen = new THREE.Mesh(
    createRoundedBox(1.66, 0.98, 0.10, 0.19, 5),
    visorGlassMat
  );
  visorScreen.position.z = 0.71;
  headGroup.add(visorScreen);

  // Subtle Curved Glass Reflection Highlight (Upper-Left of Visor)
  const visorReflection = new THREE.Mesh(
    createRoundedBox(0.52, 0.06, 0.01, 0.025, 2),
    glassSheenMat
  );
  visorReflection.position.set(-0.42, 0.34, 0.765);
  visorReflection.rotation.z = 0.08;
  headGroup.add(visorReflection);

  // --- Side Mechanical Ear Modules (Left & Right) ---
  function createEarModule(side) {
    const earModule = new THREE.Group();
    earModule.position.set(side * 1.02, 0, 0);

    // Outer Pearl White Cuff
    const cuffGeom = new THREE.CylinderGeometry(0.27, 0.29, 0.08, 32);
    cuffGeom.rotateZ(Math.PI / 2);
    const cuff = new THREE.Mesh(cuffGeom, silverTrimMat);
    earModule.add(cuff);

    // Inner Anodized Dark Titanium Dial
    const dialGeom = new THREE.CylinderGeometry(0.19, 0.19, 0.15, 32);
    dialGeom.rotateZ(Math.PI / 2);
    const dial = new THREE.Mesh(dialGeom, darkTitaniumMat);
    earModule.add(dial);

    // Glowing Neon Cyan Ear Ring
    const ringGeom = new THREE.TorusGeometry(0.20, 0.018, 16, 32);
    ringGeom.rotateY(Math.PI / 2);
    const cyanRing = new THREE.Mesh(ringGeom, neonCyanMat);
    cyanRing.position.x = side * 0.055;
    earModule.add(cyanRing);

    return earModule;
  }

  headGroup.add(createEarModule(-1));
  headGroup.add(createEarModule(1));

  // --- 4. EXPRESSIVE NEON BLUE EYES (Multi-Layer + Catchlight + Glow) ---
  const eyesGroup = new THREE.Group();
  eyesGroup.position.set(0, 0.02, 0.77);
  headGroup.add(eyesGroup);

  function createExpressiveEye(offsetX) {
    const singleEyeGroup = new THREE.Group();
    singleEyeGroup.position.x = offsetX;

    // 1. Main Neon Cyan Capsule
    const outerGeom = new THREE.SphereGeometry(0.155, 32, 24);
    outerGeom.scale(1.0, 1.22, 0.38);
    const outerMesh = new THREE.Mesh(outerGeom, neonCyanMat);
    singleEyeGroup.add(outerMesh);

    // 2. Bright Inner Core (Gives LED depth)
    const coreGeom = new THREE.SphereGeometry(0.105, 24, 20);
    coreGeom.scale(0.95, 1.15, 0.42);
    const coreMesh = new THREE.Mesh(coreGeom, eyeCoreMat);
    coreMesh.position.z = 0.012;
    singleEyeGroup.add(coreMesh);

    // 3. Cute Specular Catchlight Dot (Top-Right of eye)
    const dotGeom = new THREE.SphereGeometry(0.036, 16, 16);
    dotGeom.scale(1.0, 1.0, 0.4);
    const dotMesh = new THREE.Mesh(dotGeom, catchlightMat);
    dotMesh.position.set(0.048, 0.068, 0.058);
    singleEyeGroup.add(dotMesh);

    return singleEyeGroup;
  }

  const leftEye = createExpressiveEye(-0.36);
  const rightEye = createExpressiveEye(0.36);
  eyesGroup.add(leftEye, rightEye);

  // Soft Neon Cyan Halo Sprite behind each eye
  function createGlowHalo() {
    const haloCanvas = document.createElement('canvas');
    haloCanvas.width = 128;
    haloCanvas.height = 128;
    const ctx = haloCanvas.getContext('2d');
    const grad = ctx.createRadialGradient(64, 64, 6, 64, 64, 62);
    grad.addColorStop(0.0, 'rgba(0, 240, 255, 0.85)');
    grad.addColorStop(0.35, 'rgba(0, 210, 255, 0.32)');
    grad.addColorStop(1.0, 'rgba(0, 180, 255, 0)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 128, 128);

    const tex = new THREE.CanvasTexture(haloCanvas);
    const mat = new THREE.SpriteMaterial({
      map: tex,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });
    const sprite = new THREE.Sprite(mat);
    sprite.scale.set(0.76, 0.82, 1);
    return sprite;
  }

  const leftGlow = createGlowHalo();
  leftGlow.position.set(-0.36, 0, 0.02);
  eyesGroup.add(leftGlow);

  const rightGlow = createGlowHalo();
  rightGlow.position.set(0.36, 0, 0.02);
  eyesGroup.add(rightGlow);

  // Soft Eye Point Light to illuminate the inner visor bezel
  const eyeLight = new THREE.PointLight(0x00e5ff, 1.1, 2.2);
  eyeLight.position.set(0, 0, 0.22);
  eyesGroup.add(eyeLight);

  // =========================================================================
  // INTERACTIVITY: SMOOTH CURSOR TRACKING, BLINKING, & CLICK REACTION
  // =========================================================================
  const mouse = { x: 0, y: 0, targetX: 0, targetY: 0 };
  const targetLookPos = new THREE.Vector3(0, 0.45, 4.5);
  const currentLookPos = new THREE.Vector3(0, 0.45, 4.5);

  function onMouseMove(event) {
    if (!container.offsetParent) return;
    const rect = container.getBoundingClientRect();
    const clientX =
      event.clientX !== undefined
        ? event.clientX
        : event.touches && event.touches[0]
        ? event.touches[0].clientX
        : window.innerWidth / 2;
    const clientY =
      event.clientY !== undefined
        ? event.clientY
        : event.touches && event.touches[0]
        ? event.touches[0].clientY
        : window.innerHeight / 2;

    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;

    const normX = (clientX - centerX) / (window.innerWidth * 0.45);
    const normY = (clientY - centerY) / (window.innerHeight * 0.45);

    mouse.targetX = Math.max(-1.25, Math.min(1.25, normX));
    mouse.targetY = -Math.max(-1.25, Math.min(1.25, normY));
  }

  window.addEventListener('mousemove', onMouseMove);
  window.addEventListener('touchmove', onMouseMove, { passive: true });

  // Automatic Blinking & Click Happy Reaction
  let eyeScaleY = 1.0;
  let targetEyeScaleY = 1.0;
  let nextBlink = performance.now() + 2400;
  let isBlinking = false;
  let bounceVelocity = 0;
  let bounceOffset = 0;
  let headTiltZ = 0;
  let targetHeadTiltZ = 0;

  function blink() {
    if (isBlinking) return;
    isBlinking = true;
    targetEyeScaleY = 0.07;
    setTimeout(() => {
      targetEyeScaleY = 1.0;
      setTimeout(() => {
        isBlinking = false;
        nextBlink = performance.now() + 2600 + Math.random() * 3200;
      }, 110);
    }, 85);
  }

  // --- AI Security Tips Rotator ---
  const robotTips = [
    "Pastikan <b>cek 2 kali</b> &amp; <b>cek rekening</b> sebelum validasi! 🛡️",
    "Cocokkan <b>mutasi di m-Banking</b> ya, jangan cuma percaya bukti foto! 🔍",
    "Periksa <b>nama pengirim</b> &amp; <b>nominal</b> sampai digit terakhir! 💳",
    "Status lunas? Pastikan dana riil <b>sudah masuk ke rekening</b>! ✨"
  ];
  let tipIndex = 0;

  window.cycleRobotTip = function(e) {
    if (e) e.stopPropagation();
    tipIndex = (tipIndex + 1) % robotTips.length;
    const textEl = document.getElementById('robot-speech-text');
    if (textEl) {
      textEl.style.opacity = '0';
      textEl.style.transform = 'translateY(3px)';
      setTimeout(() => {
        textEl.innerHTML = robotTips[tipIndex];
        textEl.style.opacity = '1';
        textEl.style.transform = 'translateY(0)';
      }, 140);
    }
    blink();
    bounceVelocity = -0.28;
    targetHeadTiltZ = (Math.random() > 0.5 ? 1 : -1) * 0.14;
    setTimeout(() => {
      targetHeadTiltZ = 0;
    }, 420);
  };

  container.addEventListener('click', () => {
    window.cycleRobotTip();
  });

  // Resize Handler
  function onResize() {
    if (!container.offsetParent) return;
    const w = getWidth();
    const h = getHeight();
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  }
  window.addEventListener('resize', onResize);

  // --- Animation Loop ---
  const clock = new THREE.Clock();

  function animate() {
    requestAnimationFrame(animate);

    if (!container.offsetParent) return;

    const time = clock.getElapsedTime();
    const now = performance.now();

    // 1. Smooth mouse damping
    mouse.x += (mouse.targetX - mouse.x) * 0.085;
    mouse.y += (mouse.targetY - mouse.y) * 0.085;

    // 2. Eye blinking interpolation
    if (now > nextBlink) blink();
    eyeScaleY += (targetEyeScaleY - eyeScaleY) * 0.38;
    leftEye.scale.y = eyeScaleY;
    rightEye.scale.y = eyeScaleY;
    leftGlow.scale.y = 0.82 * eyeScaleY;
    rightGlow.scale.y = 0.82 * eyeScaleY;

    // 3. Spring physics for click nod & playful head tilt
    bounceOffset += bounceVelocity;
    bounceVelocity += (0 - bounceOffset) * 0.18;
    bounceVelocity *= 0.80;
    headTiltZ += (targetHeadTiltZ - headTiltZ) * 0.12;

    // 4. Direct Cursor Look-At (Robot looks straight toward cursor position)
    targetLookPos.set(
      mouse.x * 3.2,
      0.45 + mouse.y * 2.1 + bounceOffset,
      4.5
    );
    currentLookPos.lerp(targetLookPos, 0.11);
    headPivot.lookAt(currentLookPos);

    // Subtle natural roll when looking left/right + click tilt
    headGroup.rotation.z = -mouse.x * 0.06 + headTiltZ;

    // 5. Secondary Articulation on Neck & Pedestal Base
    neckGroup.rotation.y = headPivot.rotation.y * 0.42;
    neckGroup.rotation.x = headPivot.rotation.x * 0.28;

    pedestalGroup.rotation.y = headPivot.rotation.y * 0.14;
    pedestalGroup.rotation.x = headPivot.rotation.x * 0.08;

    // 6. Independent Eye Pupil Tracking inside Visor
    eyesGroup.position.x = mouse.x * 0.11;
    eyesGroup.position.y = 0.02 + mouse.y * 0.075;

    // 7. Gentle Floating Bob (Head & Neck hover smoothly above pedestal)
    const floatBob = Math.sin(time * 2.4) * 0.045;
    headGroup.position.y = 0.56 + floatBob;
    neckGroup.position.y = -0.52 + floatBob * 0.45;
    pedestalGroup.position.y = Math.sin(time * 2.4 - 0.6) * 0.018;

    renderer.render(scene, camera);
  }

  animate();
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initRobotWidget);
} else {
  initRobotWidget();
}
