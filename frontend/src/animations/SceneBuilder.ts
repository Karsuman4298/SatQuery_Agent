// SceneBuilder — Generates pixel targets for every visual layer
// All particles have INTENTIONAL destinations: stars, space dust, Earth silhouette,
// city lights halo, atmosphere ring, satellite shape, and text glyphs.

import { createParticle, scatterOrigin } from './ParticleEngine';
import type { Particle, ParticleLayer } from '../types/animation';

interface SceneConfig {
  width: number;
  height: number;
  totalParticles: number;
}

// ─── Seeded random (deterministic per build) ──────────────────────────────────
function seededRand(seed: number) {
  let s = seed;
  return () => {
    s = (s * 1664525 + 1013904223) & 0xffffffff;
    return (s >>> 0) / 0xffffffff;
  };
}

// ─── Colour helpers ───────────────────────────────────────────────────────────
function rnd(base: number, spread: number): number {
  return Math.max(0, Math.min(255, base + (Math.random() - 0.5) * spread));
}

// ─── Earth geometry helpers ───────────────────────────────────────────────────
// Returns the screen-space position of the Earth center and radius,
// mirroring exactly what EarthScene.tsx uses (Three.js camera pos z=3.0, fov 42°,
// earth sphere at position (0.12, -0.22, 0), radius 1 unit).
export function getEarthScreenGeometry(width: number, height: number): { cx: number; cy: number; r: number } {
  // Project the Earth center from 3D to screen
  const fovRad = (42 * Math.PI) / 180;
  const aspect = width / height;
  // Three.js ortho-ish projection at z=3.0, earth at world (0.12, -0.22, 0)
  // NDC: ndc_x = earthWorldX / (tan(fov/2) * aspect * cameraZ) * cameraZ
  const tanHalfFov = Math.tan(fovRad / 2);
  const ndcX = 0.12 / (tanHalfFov * aspect * 3.0) * 3.0; // ≈ 0.12 / (tanHalfFov * aspect)
  const ndcY = -(-0.22) / (tanHalfFov * 3.0) * 3.0;      // flip Y
  const cx = (ndcX + 1) * 0.5 * width;
  const cy = (1 - (ndcY + 1) * 0.5) * height;
  // Radius: how many pixels does radius=1 unit project to at z=3?
  const r = height / (2 * tanHalfFov) / 3.0;
  return { cx, cy, r };
}

// ─── Stars ────────────────────────────────────────────────────────────────────
export function buildStarParticles(config: SceneConfig): Particle[] {
  const { width, height } = config;
  const count = Math.floor(config.totalParticles * 0.10);
  const rand = seededRand(42);
  const particles: Particle[] = [];

  // Star distribution weighted to upper half and edges (avoiding logo area)
  for (let i = 0; i < count; i++) {
    const tx = rand() * width;
    const ty = rand() * height;
    // Keep top-left logo area clean & minimal
    if (tx < 360 && ty < 130) continue;

    const [sx, sy] = scatterOrigin(width, height);
    const brightness = 160 + Math.floor(rand() * 95);
    const alpha = 0.2 + rand() * 0.75;
    const size = rand() < 0.08 ? 2 : 1;
    const p = createParticle(sx, sy, tx, ty, brightness, brightness, brightness + Math.floor(rand() * 20), 'stars', size);
    p.targetAlpha = alpha;
    p.speed = 0.0015 + rand() * 0.003;
    particles.push(p);
  }
  return particles;
}

// ─── Space ambient pixels (very sparse, very dim) ─────────────────────────────
export function buildSpaceParticles(config: SceneConfig): Particle[] {
  const { width, height } = config;
  const count = Math.floor(config.totalParticles * 0.03);
  const particles: Particle[] = [];
  for (let i = 0; i < count; i++) {
    const tx = Math.random() * width;
    const ty = Math.random() * height;
    // Keep top-left logo area clean
    if (tx < 360 && ty < 130) continue;

    const [sx, sy] = scatterOrigin(width, height);
    const p = createParticle(
      sx, sy, tx, ty,
      Math.floor(Math.random() * 15),
      Math.floor(20 + Math.random() * 35),
      Math.floor(50 + Math.random() * 70),
      'space', 2
    );
    p.targetAlpha = 0.05 + Math.random() * 0.12;
    p.speed = 0.001 + Math.random() * 0.002;
    particles.push(p);
  }
  return particles;
}

// ─── Earth Silhouette pixels ──────────────────────────────────────────────────
// Fills the Earth sphere area with data-like pixels that will be covered
// by the Three.js render but give the "assembling" feel
export function buildEarthParticles(config: SceneConfig): Particle[] {
  const { width, height } = config;
  const { cx, cy, r } = getEarthScreenGeometry(width, height);
  const count = Math.floor(config.totalParticles * 0.35);
  const particles: Particle[] = [];

  for (let i = 0; i < count; i++) {
    // Uniform sampling within the disk
    const angle = Math.random() * Math.PI * 2;
    const dist = Math.sqrt(Math.random()) * r * 0.96;
    const tx = cx + Math.cos(angle) * dist;
    const ty = cy + Math.sin(angle) * dist;
    const [sx, sy] = scatterOrigin(width, height);

    // Normalised position on disk
    const nx = Math.cos(angle) * (dist / r);
    const ny = Math.sin(angle) * (dist / r);

    // Night side left (~35%), day side right
    const isNight = nx < -0.10;
    const isPolar = Math.abs(ny) > 0.80;

    let pr: number, pg: number, pb: number, size: number, layer: ParticleLayer;
    size = 2;

    if (isPolar) {
      // Ice/snow
      const v = rnd(195, 30);
      pr = v; pg = v + 8; pb = v + 15; layer = 'earth';
    } else if (isNight && isLand(nx, ny) && Math.random() < 0.14) {
      // City lights — dense golden pixels on night side
      pr = rnd(252, 8); pg = rnd(200, 35); pb = rnd(70, 40);
      size = Math.random() < 0.35 ? 3 : 2;
      layer = 'citylights';
    } else if (isNight) {
      // Night ocean / dark land
      pr = rnd(4, 6); pg = rnd(12, 10); pb = rnd(30, 18);
      layer = 'earth';
    } else if (isLand(nx, ny)) {
      // Sunlit land — dark olive green tones
      pr = rnd(35, 20); pg = rnd(58, 22); pb = rnd(28, 18);
      layer = 'earth';
    } else {
      // Sunlit ocean — deep navy blue
      pr = rnd(8, 10); pg = rnd(32, 18); pb = rnd(88, 28);
      layer = 'earth';
    }

    const p = createParticle(sx, sy, tx, ty, pr, pg, pb, layer, size);
    p.targetAlpha = 0.7 + Math.random() * 0.3;
    p.speed = 0.002 + Math.random() * 0.005;
    particles.push(p);
  }

  return particles;
}

// Continent heuristic on unit disk (matches EarthScene texture mapping)
function isLand(nx: number, ny: number): boolean {
  // Europe/Africa (right-center of texture → NX +0.0 to +0.25)
  const isEuroAfrica = nx > 0.0 && nx < 0.28 && ny > -0.55 && ny < 0.60 && Math.random() < 0.55;
  // Asia (further right → NX +0.2 to +0.7)
  const isAsia = nx > 0.2 && nx < 0.72 && ny > -0.42 && ny < 0.50 && Math.random() < 0.45;
  // Americas (left → NX -0.6 to -0.05)
  const isAmericas = nx > -0.65 && nx < -0.05 && ny > -0.50 && ny < 0.55 && Math.random() < 0.38;
  // Australia (bottom-right)
  const isAustralia = nx > 0.38 && nx < 0.72 && ny > 0.20 && ny < 0.58 && Math.random() < 0.45;
  return isEuroAfrica || isAsia || isAmericas || isAustralia;
}

// ─── Atmosphere ring pixels ───────────────────────────────────────────────────
export function buildAtmosphereParticles(config: SceneConfig): Particle[] {
  const { width, height } = config;
  const { cx, cy, r } = getEarthScreenGeometry(width, height);
  const count = Math.floor(config.totalParticles * 0.06);
  const particles: Particle[] = [];
  const rimR = r * 1.035;
  const rimW = r * 0.06;

  for (let i = 0; i < count; i++) {
    const angle = Math.random() * Math.PI * 2;
    const distOffset = (Math.random() - 0.5) * rimW;
    const tx = cx + Math.cos(angle) * (rimR + distOffset);
    const ty = cy + Math.sin(angle) * (rimR + distOffset);
    const [sx, sy] = scatterOrigin(width, height);

    // Sun-side (right) is bright, night-side is dim
    const sunFactor = (Math.cos(angle) + 1) / 2; // 0 (night) → 1 (day)
    const pr = Math.floor(30 + sunFactor * 40);
    const pg = Math.floor(130 + sunFactor * 90);
    const pb = Math.floor(210 + sunFactor * 45);

    const p = createParticle(sx, sy, tx, ty, pr, pg, pb, 'atmosphere', 2);
    p.targetAlpha = 0.15 + sunFactor * 0.55;
    p.speed = 0.003 + Math.random() * 0.004;
    particles.push(p);
  }
  return particles;
}

// ─── Satellite pixels ─────────────────────────────────────────────────────────
// Positions match Three.js satellite world position projected to screen
export function buildSatelliteParticles(config: SceneConfig): Particle[] {
  const { width, height } = config;
  const particles: Particle[] = [];

  // Project satellite world pos (-0.70, 0.72, 0.35) with camera z=3.05 fov40
  const fovRad = (40 * Math.PI) / 180;
  const aspect = width / height;
  const tanHalfFov = Math.tan(fovRad / 2);
  const satNdcX = -0.70 / (tanHalfFov * aspect * (3.05 - 0.35));
  const satNdcY = 0.72 / (tanHalfFov * (3.05 - 0.35));
  const satCx = (satNdcX + 1) * 0.5 * width;
  const satCy = (1 - (satNdcY + 1) * 0.5) * height;

  const scale = Math.min(width, height) * 0.022;

  // Spacecraft bus pixels (gold foil & metallic)
  for (let i = 0; i < 45; i++) {
    const tx = satCx + (Math.random() - 0.5) * scale * 1.8;
    const ty = satCy + (Math.random() - 0.5) * scale * 1.2;
    const [sx, sy] = scatterOrigin(width, height);
    const p = createParticle(sx, sy, tx, ty, 220, 180, 80, 'satellite', 2);
    p.targetAlpha = 0.7 + Math.random() * 0.25;
    p.speed = 0.003 + Math.random() * 0.005;
    particles.push(p);
  }

  // Left solar panel (deep blue)
  for (let i = 0; i < 35; i++) {
    const tx = satCx - scale * (1.2 + Math.random() * 1.6);
    const ty = satCy + (Math.random() - 0.5) * scale * 0.7;
    const [sx, sy] = scatterOrigin(width, height);
    const p = createParticle(sx, sy, tx, ty, 15, 60, 160, 'satellite', 2);
    p.targetAlpha = 0.6 + Math.random() * 0.25;
    p.speed = 0.003 + Math.random() * 0.005;
    particles.push(p);
  }

  // Right solar panel (deep blue)
  for (let i = 0; i < 35; i++) {
    const tx = satCx + scale * (1.2 + Math.random() * 1.6);
    const ty = satCy + (Math.random() - 0.5) * scale * 0.7;
    const [sx, sy] = scatterOrigin(width, height);
    const p = createParticle(sx, sy, tx, ty, 15, 60, 160, 'satellite', 2);
    p.targetAlpha = 0.6 + Math.random() * 0.25;
    p.speed = 0.003 + Math.random() * 0.005;
    particles.push(p);
  }

  return particles;
}

// ─── Text pixel targets ───────────────────────────────────────────────────────
// Renders text to offscreen canvas, samples pixel positions intentionally
export function buildTextParticles(
  text: string,
  targetCenterX: number,
  targetCenterY: number,
  fontSize: number,
  fontFamily: string,
  color: [number, number, number],
  layer: ParticleLayer,
  config: SceneConfig,
  letterSpacing = 0,
  weight = '700'
): Particle[] {
  const offCanvas = document.createElement('canvas');
  const canvasW = Math.min(config.width, 1400);
  const canvasH = fontSize * 3;
  offCanvas.width = canvasW;
  offCanvas.height = canvasH;
  const offCtx = offCanvas.getContext('2d')!;

  offCtx.fillStyle = 'white';
  offCtx.font = `${weight} ${fontSize}px ${fontFamily}`;
  offCtx.textAlign = 'center';
  offCtx.textBaseline = 'middle';

  if (letterSpacing > 0) {
    const chars = text.split('');
    let totalW = 0;
    chars.forEach(ch => { totalW += offCtx.measureText(ch).width + letterSpacing; });
    totalW -= letterSpacing;
    let xPos = canvasW / 2 - totalW / 2;
    chars.forEach(ch => {
      const cw = offCtx.measureText(ch).width;
      offCtx.fillText(ch, xPos + cw / 2, canvasH / 2);
      xPos += cw + letterSpacing;
    });
  } else {
    offCtx.fillText(text, canvasW / 2, canvasH / 2);
  }

  const imageData = offCtx.getImageData(0, 0, canvasW, canvasH);
  const pixels = imageData.data;
  const step = Math.max(2, Math.floor(fontSize / 20));
  const targets: [number, number][] = [];

  for (let y = 0; y < canvasH; y += step) {
    for (let x = 0; x < canvasW; x += step) {
      const idx = (y * canvasW + x) * 4;
      if (pixels[idx + 3] > 128) {
        const screenX = targetCenterX - canvasW / 2 + x;
        const screenY = targetCenterY - canvasH / 2 + y;
        // Only keep pixels that are on screen
        if (screenX > 0 && screenX < config.width && screenY > 0 && screenY < config.height) {
          targets.push([screenX, screenY]);
        }
      }
    }
  }

  // Shuffle for organic assembly
  for (let i = targets.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [targets[i], targets[j]] = [targets[j], targets[i]];
  }

  const [r, g, b] = color;
  return targets.map(([tx, ty]) => {
    const [sx, sy] = scatterOrigin(config.width, config.height);
    const p = createParticle(sx, sy, tx, ty, rnd(r, 18), rnd(g, 18), rnd(b, 18), layer, 2);
    p.targetAlpha = 0.88 + Math.random() * 0.12;
    p.speed = 0.006 + Math.random() * 0.009;
    return p;
  });
}
