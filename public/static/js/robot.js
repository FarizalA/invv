/**
 * 3D Interactive White Robot Widget (Three.js)
 * Rendered inside Hero Banner Analytics Overview
 */
function initRobotWidget() {
  const container = document.getElementById('hero-robot-container') || document.getElementById('sidebar-robot-container');
  if (!container || !window.THREE) return;

  // Scene
  const scene = new THREE.Scene();

  const getWidth = () => container.clientWidth || 210;
  const getHeight = () => container.clientHeight || 180;

  // Camera
  const camera = new THREE.PerspectiveCamera(34, getWidth() / getHeight(), 0.1, 100);
  camera.position.set(0, 0.22, 6.4);

  // Renderer transparan
  const renderer = new THREE.WebGLRenderer({
    alpha: true,
    antialias: true,
    powerPreference: 'high-performance'
  });
  renderer.setClearColor(0x000000, 0);
  renderer.setSize(getWidth(), getHeight());
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  container.innerHTML = '';
  container.appendChild(renderer.domElement);

  // Helper Rounded Box
  function createRoundedBox(width, height, depth, radius, smoothness) {
    const shape = new THREE.Shape();
    const eps = 0.00001;
    const radiusMinusEps = radius - eps;

    shape.absarc(-width / 2 + radius, -height / 2 + radius, radiusMinusEps, Math.PI, (3 * Math.PI) / 2, false);
    shape.absarc(width / 2 - radius, -height / 2 + radius, radiusMinusEps, (3 * Math.PI) / 2, 2 * Math.PI, false);
    shape.absarc(width / 2 - radius, height / 2 - radius, radiusMinusEps, 0, Math.PI / 2, false);
    shape.absarc(-width / 2 + radius, height / 2 - radius, radiusMinusEps, Math.PI / 2, Math.PI, false);

    const extrudeSettings = {
      depth: depth - radius * 2,
      bevelEnabled: true,
      bevelSegments: smoothness * 2,
      steps: 1,
      bevelSize: radiusMinusEps,
      bevelThickness: radius,
      curveSegments: smoothness * 2
    };

    const geom = new THREE.ExtrudeGeometry(shape, extrudeSettings);
    geom.center();
    return geom;
  }

  // Materials (White glossy ceramic body)
  const whiteBodyMat = new THREE.MeshStandardMaterial({
    color: 0xf5f8fc,
    roughness: 0.18,
    metalness: 0.15
  });

  const darkVisorMat = new THREE.MeshStandardMaterial({
    color: 0x090a10,
    roughness: 0.08,
    metalness: 0.95
  });

  const titaniumMat = new THREE.MeshStandardMaterial({
    color: 0x242a38,
    roughness: 0.35,
    metalness: 0.85
  });

  const eyeMat = new THREE.MeshBasicMaterial({
    color: new THREE.Color(0x00f0ff)
  });

  // Lighting (Kontras tinggi studio di atas dark navy background)
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.9);
  scene.add(ambientLight);

  const keyLight = new THREE.DirectionalLight(0xffffff, 1.6);
  keyLight.position.set(3, 5, 5);
  scene.add(keyLight);

  const rimLightBlue = new THREE.DirectionalLight(0x00f0ff, 2.0);
  rimLightBlue.position.set(-5, 3, -2);
  scene.add(rimLightBlue);

  const rimLightRight = new THREE.DirectionalLight(0x93c5fd, 1.4);
  rimLightRight.position.set(5, 2, -2);
  scene.add(rimLightRight);

  const fillLightBottom = new THREE.DirectionalLight(0x38bdf8, 0.8);
  fillLightBottom.position.set(0, -4, 3);
  scene.add(fillLightBottom);

  // Character Hierarchy
  const robotRoot = new THREE.Group();
  scene.add(robotRoot);

  // 1. Torso
  const torsoGroup = new THREE.Group();
  torsoGroup.position.y = -1.2;
  robotRoot.add(torsoGroup);

  const torsoMesh = new THREE.Mesh(createRoundedBox(2.2, 0.45, 1.8, 0.16, 4), whiteBodyMat);
  torsoGroup.add(torsoMesh);

  const lowerBase = new THREE.Mesh(createRoundedBox(1.5, 0.22, 1.3, 0.08, 4), titaniumMat);
  lowerBase.position.y = -0.32;
  torsoGroup.add(lowerBase);

  // 2. Neck
  const neckGroup = new THREE.Group();
  neckGroup.position.y = -0.85;
  robotRoot.add(neckGroup);

  const collar = new THREE.Mesh(new THREE.CylinderGeometry(0.48, 0.55, 0.16, 32), titaniumMat);
  neckGroup.add(collar);

  const neckPillar = new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.22, 0.45, 32), whiteBodyMat);
  neckPillar.position.y = 0.25;
  neckGroup.add(neckPillar);

  const neckRing = new THREE.Mesh(new THREE.TorusGeometry(0.3, 0.06, 16, 32), titaniumMat);
  neckRing.rotation.x = Math.PI / 2;
  neckRing.position.y = 0.45;
  neckGroup.add(neckRing);

  // 3. Head & Pivot
  const headPivot = new THREE.Group();
  headPivot.position.set(0, -0.2, 0);
  robotRoot.add(headPivot);

  const headGroup = new THREE.Group();
  headGroup.position.set(0, 0.7, 0);
  headPivot.add(headGroup);

  const headMesh = new THREE.Mesh(createRoundedBox(2.4, 1.6, 1.7, 0.35, 6), whiteBodyMat);
  headGroup.add(headMesh);

  const visorMesh = new THREE.Mesh(createRoundedBox(2.05, 1.28, 0.1, 0.24, 4), darkVisorMat);
  visorMesh.position.z = 0.82;
  headGroup.add(visorMesh);

  const earGeom = new THREE.CylinderGeometry(0.28, 0.28, 0.16, 32);
  earGeom.rotateZ(Math.PI / 2);

  const leftEar = new THREE.Mesh(earGeom, titaniumMat);
  leftEar.position.set(-1.22, 0, 0);
  headGroup.add(leftEar);

  const rightEar = new THREE.Mesh(earGeom, titaniumMat);
  rightEar.position.set(1.22, 0, 0);
  headGroup.add(rightEar);

  // 4. Eyes
  const eyesGroup = new THREE.Group();
  eyesGroup.position.set(0, 0.04, 0.89);
  headGroup.add(eyesGroup);

  const eyeGeom = new THREE.SphereGeometry(0.18, 32, 24);
  eyeGeom.scale(1.0, 1.18, 0.4);

  const leftEye = new THREE.Mesh(eyeGeom, eyeMat);
  leftEye.position.x = -0.42;
  eyesGroup.add(leftEye);

  const rightEye = new THREE.Mesh(eyeGeom, eyeMat);
  rightEye.position.x = 0.42;
  eyesGroup.add(rightEye);

  // Glow Halo Texture
  const createGlowHalo = () => {
    const haloCanvas = document.createElement('canvas');
    haloCanvas.width = 128;
    haloCanvas.height = 128;
    const ctx = haloCanvas.getContext('2d');
    const grad = ctx.createRadialGradient(64, 64, 10, 64, 64, 64);
    grad.addColorStop(0, 'rgba(0, 240, 255, 0.9)');
    grad.addColorStop(0.3, 'rgba(0, 240, 255, 0.4)');
    grad.addColorStop(1, 'rgba(0, 240, 255, 0)');
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
    sprite.scale.set(0.9, 0.9, 1);
    return sprite;
  };

  const leftGlow = createGlowHalo();
  leftGlow.position.set(-0.42, 0, 0.05);
  eyesGroup.add(leftGlow);

  const rightGlow = createGlowHalo();
  rightGlow.position.set(0.42, 0, 0.05);
  eyesGroup.add(rightGlow);

  // Cursor Tracking
  const mouse = { x: 0, y: 0, targetX: 0, targetY: 0 };
  const targetLookPos = new THREE.Vector3(0, 0.5, 4);
  const currentLookPos = new THREE.Vector3(0, 0.5, 4);

  function onMouseMove(event) {
    if (!container.offsetParent) return;
    const rect = container.getBoundingClientRect();
    const clientX = event.clientX || (event.touches && event.touches[0] ? event.touches[0].clientX : window.innerWidth / 2);
    const clientY = event.clientY || (event.touches && event.touches[0] ? event.touches[0].clientY : window.innerHeight / 2);

    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;

    const normX = (clientX - centerX) / (window.innerWidth / 2);
    const normY = (clientY - centerY) / (window.innerHeight / 2);

    mouse.targetX = Math.max(-1.4, Math.min(1.4, normX));
    mouse.targetY = -Math.max(-1.4, Math.min(1.4, normY));
  }

  window.addEventListener('mousemove', onMouseMove);
  window.addEventListener('touchmove', onMouseMove, { passive: true });

  // Blinking & Nodding
  let eyeScaleY = 1.0;
  let targetEyeScaleY = 1.0;
  let nextBlink = performance.now() + 2500;
  let isBlinking = false;
  let bounceVelocity = 0;
  let bounceOffset = 0;

  function blink() {
    if (isBlinking) return;
    isBlinking = true;
    targetEyeScaleY = 0.08;
    setTimeout(() => {
      targetEyeScaleY = 1.0;
      setTimeout(() => {
        isBlinking = false;
        nextBlink = performance.now() + 2500 + Math.random() * 3000;
      }, 120);
    }, 90);
  }

  container.addEventListener('click', () => {
    blink();
    bounceVelocity = -0.32;
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

  // Animation Loop
  const clock = new THREE.Clock();

  function animate() {
    requestAnimationFrame(animate);

    // Skip render jika container sedang disembunyikan (misal di mobile)
    if (!container.offsetParent) return;

    const time = clock.getElapsedTime();
    const now = performance.now();

    // Lerp mouse
    mouse.x += (mouse.targetX - mouse.x) * 0.08;
    mouse.y += (mouse.targetY - mouse.y) * 0.08;

    // Blinking
    if (now > nextBlink) blink();
    eyeScaleY += (targetEyeScaleY - eyeScaleY) * 0.4;
    leftEye.scale.y = 1.18 * eyeScaleY;
    rightEye.scale.y = 1.18 * eyeScaleY;
    leftGlow.scale.y = 0.9 * eyeScaleY;
    rightGlow.scale.y = 0.9 * eyeScaleY;

    // Nod / Bounce
    bounceOffset += bounceVelocity;
    bounceVelocity += (0 - bounceOffset) * 0.18;
    bounceVelocity *= 0.8;

    // Target look position
    targetLookPos.set(
      mouse.x * 3.8,
      0.5 + mouse.y * 2.5 + bounceOffset,
      4.2
    );

    currentLookPos.lerp(targetLookPos, 0.1);
    headPivot.lookAt(currentLookPos);

    neckGroup.rotation.y = headPivot.rotation.y * 0.4;
    neckGroup.rotation.x = headPivot.rotation.x * 0.3;
    torsoGroup.rotation.y = headPivot.rotation.y * 0.15;

    eyesGroup.position.x = mouse.x * 0.12;
    eyesGroup.position.y = 0.04 + mouse.y * 0.08;

    // Floating bob
    robotRoot.position.y = Math.sin(time * 2.2) * 0.06;

    renderer.render(scene, camera);
  }

  animate();
}

// Inisialisasi otomatis setelah DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initRobotWidget);
} else {
  initRobotWidget();
}
