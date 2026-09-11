// ParticleEngine — Core Canvas 2D pixel system
// Handles all pixel formation (ease-to-target) and dissolve (physics scatter)

import type { Particle, ParticleLayer } from '../types/animation';

export interface ParticleEngineConfig {
  canvas: HTMLCanvasElement;
  width: number;
  height: number;
  pixelRatio: number;
}

// Easing
const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3);

let _id = 0;

export function createParticle(
  x: number, y: number,
  targetX: number, targetY: number,
  r: number, g: number, b: number,
  layer: ParticleLayer,
  size = 2
): Particle {
  return {
    id: _id++,
    x, y,
    targetX, targetY,
    startX: x, startY: y,
    r, g, b,
    alpha: 0,
    targetAlpha: 1,
    size,
    targetSize: size,
    progress: 0,
    speed: 0.004 + Math.random() * 0.008,
    layer,
    active: true,
    dissolving: false,
    dissolveVx: 0,
    dissolveVy: 0,
  };
}

export class ParticleEngine {
  canvas: HTMLCanvasElement;
  ctx: CanvasRenderingContext2D;
  width: number;
  height: number;
  pixelRatio: number;
  particles: Particle[] = [];
  animationId: number | null = null;
  isDissolving = false;

  constructor(config: ParticleEngineConfig) {
    this.canvas = config.canvas;
    this.ctx = config.canvas.getContext('2d')!;
    this.width = config.width;
    this.height = config.height;
    this.pixelRatio = config.pixelRatio;
  }

  resize(width: number, height: number) {
    this.width = width;
    this.height = height;
  }

  addParticles(particles: Particle[]) {
    this.particles.push(...particles);
  }

  startDissolve() {
    this.isDissolving = true;
    this.particles.forEach((p) => {
      p.dissolving = true;
      // Scatter angle: away from Earth center + some randomness
      const earthCx = this.width * 0.52;
      const earthCy = this.height * 0.55;
      const awayAngle = Math.atan2(p.targetY - earthCy, p.targetX - earthCx);
      const spreadAngle = awayAngle + (Math.random() - 0.5) * Math.PI * 1.4;
      const speed = 0.3 + Math.random() * 3.5;
      p.dissolveVx = Math.cos(spreadAngle) * speed;
      p.dissolveVy = Math.sin(spreadAngle) * speed - 0.2;
    });
  }

  render() {
    const ctx = this.ctx;
    const dpr = this.pixelRatio;
    ctx.clearRect(0, 0, this.width * dpr, this.height * dpr);

    const toRemove: number[] = [];

    for (let i = 0; i < this.particles.length; i++) {
      const p = this.particles[i];
      if (!p.active) continue;

      if (p.dissolving) {
        p.x += p.dissolveVx;
        p.y += p.dissolveVy;
        p.dissolveVy += 0.015;      // gravity
        p.dissolveVx *= 0.985;      // air resistance
        p.alpha -= 0.018;
        p.size *= 0.975;
        if (p.alpha <= 0 || p.size < 0.25) {
          toRemove.push(i);
          continue;
        }
      } else {
        if (p.progress < 1) {
          p.progress = Math.min(1, p.progress + p.speed);
        }
        const t = easeOutCubic(p.progress);
        p.x = p.startX + (p.targetX - p.startX) * t;
        p.y = p.startY + (p.targetY - p.startY) * t;
        p.alpha = Math.min(p.targetAlpha, p.progress * 2.2);
      }

      const s = Math.max(0.25, p.size);
      const sx = p.x * dpr;
      const sy = p.y * dpr;
      const ss = s * dpr;

      ctx.globalAlpha = Math.max(0, Math.min(1, p.alpha));
      ctx.fillStyle = `rgb(${Math.round(p.r)},${Math.round(p.g)},${Math.round(p.b)})`;
      ctx.fillRect(sx - ss / 2, sy - ss / 2, ss, ss);
    }

    // Prune dead particles (reverse to preserve indices)
    for (let i = toRemove.length - 1; i >= 0; i--) {
      this.particles.splice(toRemove[i], 1);
    }
    ctx.globalAlpha = 1;
  }

  start() {
    const loop = () => {
      this.render();
      this.animationId = requestAnimationFrame(loop);
    };
    this.animationId = requestAnimationFrame(loop);
  }

  stop() {
    if (this.animationId !== null) {
      cancelAnimationFrame(this.animationId);
      this.animationId = null;
    }
  }

  destroy() {
    this.stop();
    this.particles = [];
  }
}

// ─── Adaptive particle count ──────────────────────────────────────────────────
export function getAdaptiveCount(): number {
  const w = window.innerWidth;
  const cores = (navigator as { hardwareConcurrency?: number }).hardwareConcurrency ?? 2;
  if (w >= 1440 && cores >= 4) return 7000;
  if (w >= 1024) return 4500;
  if (w >= 768) return 2800;
  return 1600;
}

// ─── Random scatter origin (off-screen edge) ──────────────────────────────────
export function scatterOrigin(width: number, height: number): [number, number] {
  const edge = Math.floor(Math.random() * 4);
  const padding = 30;
  switch (edge) {
    case 0: return [Math.random() * width, -padding];
    case 1: return [Math.random() * width, height + padding];
    case 2: return [-padding, Math.random() * height];
    default: return [width + padding, Math.random() * height];
  }
}
