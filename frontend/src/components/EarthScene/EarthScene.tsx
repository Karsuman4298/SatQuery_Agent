// EarthScene — Photorealistic Satellite Remote Sensing Earth with High-Resolution Textures,
// Night-Side City Lights, Realistic Ocean Specular Reflections, and Multi-Layered Atmospheric Scattering.

import React, { useRef, useEffect, useCallback } from 'react';
import * as THREE from 'three';
import type { AnimationPhase } from '../../types/animation';
import earthDayMapUrl from '../../assets/earth/earth_day_map.jpg';
import earthNightMapUrl from '../../assets/earth/earth_night_map.jpg';

interface EarthSceneProps {
  phase: AnimationPhase;
  onEarthEnter: () => void;
  onHoverChange: (hovering: boolean) => void;
}

export const EarthScene: React.FC<EarthSceneProps> = ({
  phase,
  onEarthEnter,
  onHoverChange,
}) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const earthMeshRef = useRef<THREE.Mesh | null>(null);
  const atmosphereRef = useRef<THREE.Mesh | null>(null);
  const satGroupRef = useRef<THREE.Group | null>(null);
  const animFrameRef = useRef<number | null>(null);

  const isHoveringRef = useRef(false);
  const targetOpacityRef = useRef(0);
  const currentOpacityRef = useRef(0);
  const satOpacityRef = useRef(0);
  const satTargetOpacityRef = useRef(0);
  const dissolveRef = useRef(false);

  // Phase updates
  useEffect(() => {
    if (['EARTH_FORMING', 'BRANDING_FORMING', 'ENTRY_READY', 'EARTH_HOVER'].includes(phase)) {
      targetOpacityRef.current = 1;
    }
    if (phase === 'BRANDING_FORMING' || phase === 'ENTRY_READY' || phase === 'EARTH_HOVER') {
      satTargetOpacityRef.current = 0.85;
    }
    if (phase === 'EARTH_ENTERING' || phase === 'PAGE_DISSOLVING') {
      dissolveRef.current = true;
      targetOpacityRef.current = 0;
      satTargetOpacityRef.current = 0;
    }
  }, [phase]);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    const w = window.innerWidth;
    const h = window.innerHeight;

    // ── WebGL Renderer
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance',
    });
    renderer.setSize(w, h);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 0);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;
    mount.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // ── Scene + Camera
    const scene = new THREE.Scene();
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(40, w / h, 0.1, 1000);
    camera.position.z = 3.05;
    cameraRef.current = camera;

    // ── Texture Loader with Anisotropy
    const textureLoader = new THREE.TextureLoader();
    const maxAnisotropy = renderer.capabilities.getMaxAnisotropy();

    const dayTexture = textureLoader.load(earthDayMapUrl);
    dayTexture.colorSpace = THREE.SRGBColorSpace;
    dayTexture.anisotropy = maxAnisotropy;

    const nightTexture = textureLoader.load(earthNightMapUrl);
    nightTexture.colorSpace = THREE.SRGBColorSpace;
    nightTexture.anisotropy = maxAnisotropy;

    // ── Earth Sphere
    const earthGeo = new THREE.SphereGeometry(1.0, 128, 128);
    const earthMat = new THREE.MeshPhongMaterial({
      map: dayTexture,
      emissiveMap: nightTexture,
      emissive: new THREE.Color(0xffe082),
      emissiveIntensity: 1.6,
      specular: new THREE.Color(0x2266aa),
      shininess: 28,
      transparent: true,
      opacity: 0,
    });

    const earthMesh = new THREE.Mesh(earthGeo, earthMat);
    // Position: centered-right in viewport
    earthMesh.position.set(0.28, -0.12, 0);
    // Rotation: Orient Europe & Africa towards viewer
    earthMesh.rotation.y = -Math.PI * 0.48;
    earthMesh.rotation.x = 0.12; // Slight orbital axial tilt
    scene.add(earthMesh);
    earthMeshRef.current = earthMesh;

    // ── Atmospheric Glow (Photorealistic Rayleigh scattering on Earth's surface)
    const atmosGeo = new THREE.SphereGeometry(1.003, 128, 128);
    const atmosMat = new THREE.ShaderMaterial({
      uniforms: {
        glowColor: { value: new THREE.Color(0x38bdf8) },
        hoverBoost: { value: 0.0 },
        opacity: { value: 0.0 },
      },
      vertexShader: `
        varying vec3 vNormal;
        varying vec3 vViewPosition;
        void main() {
          vNormal = normalize(normalMatrix * normal);
          vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
          vViewPosition = -mvPosition.xyz;
          gl_Position = projectionMatrix * mvPosition;
        }
      `,
      fragmentShader: `
        uniform vec3 glowColor;
        uniform float hoverBoost;
        uniform float opacity;
        varying vec3 vNormal;
        varying vec3 vViewPosition;
        void main() {
          vec3 viewDir = normalize(vViewPosition);
          float NdotV = dot(vNormal, viewDir);
          float rim = 1.0 - clamp(NdotV, 0.0, 1.0);
          rim = pow(rim, 3.2);
          float boost = 1.0 + hoverBoost * 0.45;
          gl_FragColor = vec4(glowColor * boost, rim * opacity * 0.95);
        }
      `,
      side: THREE.FrontSide,
      blending: THREE.AdditiveBlending,
      transparent: true,
      depthWrite: false,
    });
    const atmosMesh = new THREE.Mesh(atmosGeo, atmosMat);
    atmosMesh.position.copy(earthMesh.position);
    scene.add(atmosMesh);
    atmosphereRef.current = atmosMesh;

    // ── 3D Earth-Observation Satellite Spacecraft (Sentinel / Landsat Class)
    const satGroup = new THREE.Group();

    // 1. Main Spacecraft Bus (Hexagonal / Rectangular chassis with Gold MLI insulation)
    const busGeo = new THREE.BoxGeometry(0.095, 0.062, 0.058);
    const busMat = new THREE.MeshStandardMaterial({
      color: 0xe5b850,
      emissive: new THREE.Color(0x332200),
      emissiveIntensity: 0.2,
      metalness: 0.9,
      roughness: 0.25,
      transparent: true,
      opacity: 0,
    });
    const busMesh = new THREE.Mesh(busGeo, busMat);
    satGroup.add(busMesh);

    // 2. Silver Radiator Equipment Bay
    const radiatorGeo = new THREE.BoxGeometry(0.055, 0.048, 0.018);
    const radiatorMat = new THREE.MeshStandardMaterial({
      color: 0xecf2f8,
      metalness: 0.92,
      roughness: 0.18,
      transparent: true,
      opacity: 0,
    });
    const radiatorMesh = new THREE.Mesh(radiatorGeo, radiatorMat);
    radiatorMesh.position.set(0, 0, 0.034);
    satGroup.add(radiatorMesh);

    // 3. Earth Observation Optical Payload / Sensor Aperture (Nadir sensor facing Earth)
    const sensorBarrelGeo = new THREE.CylinderGeometry(0.022, 0.026, 0.042, 24);
    const sensorBarrelMat = new THREE.MeshStandardMaterial({
      color: 0x1e293b,
      metalness: 0.85,
      roughness: 0.25,
      transparent: true,
      opacity: 0,
    });
    const sensorBarrel = new THREE.Mesh(sensorBarrelGeo, sensorBarrelMat);
    sensorBarrel.rotation.x = Math.PI * 0.5; // Points forward along local Z (nadir)
    sensorBarrel.position.set(0, -0.018, 0.048);
    satGroup.add(sensorBarrel);

    // Optical Lens Glass (deep reflective glass with subtle sensor glow)
    const lensGeo = new THREE.CircleGeometry(0.019, 24);
    const lensMat = new THREE.MeshStandardMaterial({
      color: 0x00d4ff,
      emissive: new THREE.Color(0x00ff88),
      emissiveIntensity: 0.6,
      metalness: 0.95,
      roughness: 0.05,
      transparent: true,
      opacity: 0,
    });
    const lensMesh = new THREE.Mesh(lensGeo, lensMat);
    lensMesh.position.set(0, -0.018, 0.07);
    satGroup.add(lensMesh);

    // 4. Solar Array Wings (Left and Right Photovoltaic panels)
    const solarWingGeo = new THREE.BoxGeometry(0.18, 0.062, 0.004);
    const solarWingMat = new THREE.MeshStandardMaterial({
      color: 0x0a2668,
      emissive: new THREE.Color(0x021844),
      emissiveIntensity: 0.35,
      metalness: 0.8,
      roughness: 0.25,
      transparent: true,
      opacity: 0,
    });

    // Left Solar Wing & Structural Truss
    const leftWing = new THREE.Mesh(solarWingGeo, solarWingMat);
    leftWing.position.set(-0.155, 0, 0);
    satGroup.add(leftWing);

    const leftTrussGeo = new THREE.CylinderGeometry(0.003, 0.003, 0.06, 8);
    const trussMat = new THREE.MeshStandardMaterial({ color: 0xa0b4c8, metalness: 0.9, roughness: 0.2, transparent: true, opacity: 0 });
    const leftTruss = new THREE.Mesh(leftTrussGeo, trussMat);
    leftTruss.rotation.z = Math.PI * 0.5;
    leftTruss.position.set(-0.058, 0, 0);
    satGroup.add(leftTruss);

    // Right Solar Wing & Structural Truss
    const rightWing = new THREE.Mesh(solarWingGeo, solarWingMat.clone());
    rightWing.position.set(0.155, 0, 0);
    satGroup.add(rightWing);

    const rightTruss = new THREE.Mesh(leftTrussGeo, trussMat.clone());
    rightTruss.rotation.z = Math.PI * 0.5;
    rightTruss.position.set(0.058, 0, 0);
    satGroup.add(rightTruss);

    // 5. Parabolic Communication Antenna Dish
    const dishGeo = new THREE.SphereGeometry(0.02, 16, 16, 0, Math.PI * 2, 0, Math.PI * 0.5);
    const dishMat = new THREE.MeshStandardMaterial({
      color: 0xdde6ed,
      metalness: 0.85,
      roughness: 0.2,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0,
    });
    const dishMesh = new THREE.Mesh(dishGeo, dishMat);
    dishMesh.rotation.x = Math.PI * 0.35;
    dishMesh.rotation.y = Math.PI * 0.2;
    dishMesh.position.set(0.032, 0.042, -0.018);
    satGroup.add(dishMesh);

    // Position Satellite in Upper Space Quadrant above & observing Earth
    satGroup.position.set(-0.58, 0.76, 0.28);
    satGroup.lookAt(earthMesh.position.x + 0.1, earthMesh.position.y + 0.2, earthMesh.position.z);
    satGroup.rotateZ(0.15); // Natural orbital inclination angle
    scene.add(satGroup);
    satGroupRef.current = satGroup;

    // ── Lighting
    // Ambient light (deep space subtle bounce)
    const ambientLight = new THREE.AmbientLight(0x0a1424, 0.7);
    scene.add(ambientLight);

    // Sun Key Light (Directional, bright crisp daylight on Earth)
    const sunLight = new THREE.DirectionalLight(0xfff8ed, 3.8);
    sunLight.position.set(4.5, 1.8, 3.0);
    scene.add(sunLight);

    // Dedicated Satellite Key & Fill Lights (crisp spacecraft illumination)
    const satKeyLight = new THREE.DirectionalLight(0xfffaec, 2.8);
    satKeyLight.position.set(-1.5, 2.0, 1.8);
    scene.add(satKeyLight);

    const satFillLight = new THREE.DirectionalLight(0x38bdf8, 1.2);
    satFillLight.position.set(0.8, 0.6, 1.2);
    scene.add(satFillLight);

    // Earth Ocean Fill Light
    const fillLight = new THREE.DirectionalLight(0x0088cc, 0.35);
    fillLight.position.set(1.5, -2, 2);
    scene.add(fillLight);

    // Deep Space Rim Fill
    const spaceRim = new THREE.DirectionalLight(0x1e3a68, 0.2);
    spaceRim.position.set(-3.5, 1.0, 1.0);
    scene.add(spaceRim);

    // ── Animation Loop
    let lastTime = performance.now();
    let satTime = 0;

    const animate = (now: number) => {
      animFrameRef.current = requestAnimationFrame(animate);
      const dt = Math.min((now - lastTime) / 1000, 0.05);
      lastTime = now;
      satTime += dt;

      // Opacity interpolation
      const opTarget = dissolveRef.current ? 0 : targetOpacityRef.current;
      const opSpeed = dissolveRef.current ? 1.6 : 0.6;
      currentOpacityRef.current = THREE.MathUtils.lerp(
        currentOpacityRef.current,
        opTarget,
        dt * opSpeed
      );
      earthMat.opacity = currentOpacityRef.current;

      // Atmosphere opacity
      atmosMat.uniforms.opacity.value = currentOpacityRef.current;

      // Hover glow boost
      const hoverTarget = isHoveringRef.current && !dissolveRef.current ? 1.0 : 0.0;
      const currentBoost = atmosMat.uniforms.hoverBoost.value;
      const newBoost = THREE.MathUtils.lerp(currentBoost, hoverTarget, dt * 6);
      atmosMat.uniforms.hoverBoost.value = newBoost;

      // Subtle slow planetary rotation
      if (!dissolveRef.current) {
        earthMesh.rotation.y += dt * 0.018;
      }

      // Hover scale feedback
      if (!dissolveRef.current) {
        const hoverScale = isHoveringRef.current ? 1.015 : 1.0;
        const s = THREE.MathUtils.lerp(earthMesh.scale.x, hoverScale, dt * 5);
        earthMesh.scale.setScalar(s);
        atmosMesh.scale.setScalar(s);
      }

      // Dissolve scaling
      if (dissolveRef.current) {
        const ds = THREE.MathUtils.lerp(earthMesh.scale.x, 1.08, dt * 0.9);
        earthMesh.scale.setScalar(ds);
        atmosMesh.scale.setScalar(ds);
      }

      // Satellite subtle orbital drift & slow breathing motion
      satGroup.position.y = 0.76 + Math.sin(satTime * 0.12) * 0.012;
      satGroup.position.x = -0.58 + Math.cos(satTime * 0.08) * 0.008;

      const sOpTarget = dissolveRef.current ? 0 : satTargetOpacityRef.current;
      const sOpSpeed = dissolveRef.current ? 2.0 : 0.5;
      satOpacityRef.current = THREE.MathUtils.lerp(
        satOpacityRef.current,
        sOpTarget,
        dt * sOpSpeed
      );
      satGroup.traverse((child) => {
        if ((child as THREE.Mesh).isMesh) {
          const mat = (child as THREE.Mesh).material as THREE.Material;
          if (mat && mat.transparent !== undefined) mat.opacity = satOpacityRef.current;
        }
      });

      renderer.render(scene, camera);
    };

    animate(performance.now());

    // Window Resize Handler
    const handleResize = () => {
      const nw = window.innerWidth;
      const nh = window.innerHeight;
      camera.aspect = nw / nh;
      camera.updateProjectionMatrix();
      renderer.setSize(nw, nh);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      earthGeo.dispose();
      earthMat.dispose();
      dayTexture.dispose();
      nightTexture.dispose();
      atmosGeo.dispose();
      atmosMat.dispose();
      renderer.dispose();
      if (mount.contains(renderer.domElement)) {
        mount.removeChild(renderer.domElement);
      }
    };
  }, []);

  // Raycasting for interactive click & hover
  const getEarthHit = useCallback((clientX: number, clientY: number) => {
    if (!cameraRef.current || !earthMeshRef.current || !mountRef.current) return false;
    const rect = mountRef.current.getBoundingClientRect();
    const x = ((clientX - rect.left) / rect.width) * 2 - 1;
    const y = -((clientY - rect.top) / rect.height) * 2 + 1;
    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(new THREE.Vector2(x, y), cameraRef.current);
    return raycaster.intersectObject(earthMeshRef.current).length > 0;
  }, []);

  const isInteractive = ['ENTRY_READY', 'EARTH_HOVER'].includes(phase);

  const handlePointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!isInteractive) return;
      const hit = getEarthHit(e.clientX, e.clientY);
      if (hit !== isHoveringRef.current) {
        isHoveringRef.current = hit;
        onHoverChange(hit);
      }
    },
    [isInteractive, getEarthHit, onHoverChange]
  );

  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      if (!isInteractive) return;
      if (getEarthHit(e.clientX, e.clientY)) {
        onEarthEnter();
      }
    },
    [isInteractive, getEarthHit, onEarthEnter]
  );

  const handlePointerLeave = useCallback(() => {
    isHoveringRef.current = false;
    onHoverChange(false);
  }, [onHoverChange]);

  return (
    <div
      ref={mountRef}
      onPointerMove={handlePointerMove}
      onClick={handleClick}
      onPointerLeave={handlePointerLeave}
      role="button"
      aria-label="Interactive Photorealistic Earth — Click to enter SatQuery AI"
      tabIndex={isInteractive ? 0 : -1}
      onKeyDown={(e) => {
        if (isInteractive && (e.key === 'Enter' || e.key === ' ')) onEarthEnter();
      }}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 2,
        cursor: isInteractive && isHoveringRef.current ? 'pointer' : 'default',
        outline: 'none',
      }}
    />
  );
};

export default EarthScene;
