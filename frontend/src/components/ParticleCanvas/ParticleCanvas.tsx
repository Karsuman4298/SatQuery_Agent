// ParticleCanvas — Orchestrates the complete pixel formation and dissolve sequence.
// Canvas handles ONLY visual elements: stars, space, Earth pixels, atmosphere, satellite.
// Text (SATQUERY AI, headline, sub-text) is handled entirely by Framer Motion overlays.

import {
  useRef,
  useEffect,
  useCallback,
  forwardRef,
  useImperativeHandle,

} from 'react';
import { ParticleEngine, getAdaptiveCount } from '../../animations/ParticleEngine';
import {
  buildStarParticles,
  buildSpaceParticles,
  buildEarthParticles,
  buildAtmosphereParticles,
} from '../../animations/SceneBuilder';
import type { AnimationPhase } from '../../types/animation';

interface ParticleCanvasProps {
  phase: AnimationPhase;
  prefersReducedMotion: boolean;
  onPhaseAdvance: (phase: AnimationPhase) => void;
}

export interface ParticleCanvasHandle {
  triggerDissolve: () => void;
}

const ParticleCanvas = forwardRef<ParticleCanvasHandle, ParticleCanvasProps>(
  ({ phase, prefersReducedMotion, onPhaseAdvance }, ref) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const engineRef = useRef<ParticleEngine | null>(null);

    const triggerDissolve = useCallback(() => {
      engineRef.current?.startDissolve();
    }, []);

    useImperativeHandle(ref, () => ({ triggerDissolve }));

    useEffect(() => {
      const canvas = canvasRef.current;
      if (!canvas) return;

      const dpr = window.devicePixelRatio || 1;
      const w = window.innerWidth;
      const h = window.innerHeight;

      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;

      const engine = new ParticleEngine({ canvas, width: w, height: h, pixelRatio: dpr });
      engineRef.current = engine;
      engine.start();

      const totalParticles = getAdaptiveCount();
      const sceneConfig = { width: w, height: h, totalParticles };

      if (prefersReducedMotion) {
        // Instant reveal for reduced motion
        const all = [
          ...buildSpaceParticles(sceneConfig),
          ...buildStarParticles(sceneConfig),
          ...buildEarthParticles(sceneConfig),
          ...buildAtmosphereParticles(sceneConfig),
        ];
        all.forEach((p) => { p.x = p.targetX; p.y = p.targetY; p.progress = 1; p.alpha = p.targetAlpha; });
        engine.addParticles(all);
        onPhaseAdvance('ENTRY_READY');
        return;
      }

      onPhaseAdvance('FORMING_PAGE');

      // STEP 1: First pixels appear (0.2s) — deep space + initial stars
      setTimeout(() => {
        engine.addParticles(buildSpaceParticles(sceneConfig));
        const firstStars = buildStarParticles(sceneConfig);
        engine.addParticles(firstStars.slice(0, Math.floor(firstStars.length * 0.35)));
      }, 200);

      // STEP 2: More stars form (1.2s)
      setTimeout(() => {
        const moreStars = buildStarParticles(sceneConfig);
        engine.addParticles(moreStars.slice(Math.floor(moreStars.length * 0.35)));
      }, 1200);

      // STEP 3: Earth begins assembling (2.6s) — chunked for visual drama
      setTimeout(() => {
        onPhaseAdvance('EARTH_FORMING');
        const earthParticles = buildEarthParticles(sceneConfig);
        const quarter = Math.floor(earthParticles.length / 4);
        engine.addParticles(earthParticles.slice(0, quarter));              // silhouette
        setTimeout(() => engine.addParticles(earthParticles.slice(quarter, quarter * 2)), 300);   // continents
        setTimeout(() => engine.addParticles(earthParticles.slice(quarter * 2, quarter * 3)), 600); // city lights
        setTimeout(() => engine.addParticles(earthParticles.slice(quarter * 3)), 900);            // final detail
      }, 3000);

      // STEP 5: Atmosphere rim (4.0s)
      setTimeout(() => {
        engine.addParticles(buildAtmosphereParticles(sceneConfig));
      }, 4000);

      // STEP 6: Advance to BRANDING_FORMING (4.5s) — Framer Motion reveals brand + text
      setTimeout(() => {
        onPhaseAdvance('BRANDING_FORMING');
      }, 4500);

      // STEP 7: Entry ready (6.0s) — all Framer Motion text fully formed
      setTimeout(() => {
        onPhaseAdvance('ENTRY_READY');
      }, 6000);

      // ── Resize handler
      const handleResize = () => {
        const nw = window.innerWidth;
        const nh = window.innerHeight;
        canvas.width = nw * dpr;
        canvas.height = nh * dpr;
        canvas.style.width = `${nw}px`;
        canvas.style.height = `${nh}px`;
        engine.resize(nw, nh);
      };
      window.addEventListener('resize', handleResize);

      return () => {
        window.removeEventListener('resize', handleResize);
        engine.destroy();
      };
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // Trigger dissolve when phase demands it
    useEffect(() => {
      if (
        (phase === 'EARTH_ENTERING' || phase === 'PAGE_DISSOLVING') &&
        engineRef.current &&
        !engineRef.current.isDissolving
      ) {
        triggerDissolve();
      }
    }, [phase, triggerDissolve]);

    return (
      <div
        style={{
          position: 'fixed',
          inset: 0,
          pointerEvents: 'none',
          zIndex: 1,
        }}
      >
        <canvas
          ref={canvasRef}
          aria-hidden="true"
          style={{ display: 'block', width: '100%', height: '100%' }}
        />
      </div>
    );
  }
);

ParticleCanvas.displayName = 'ParticleCanvas';
export default ParticleCanvas;
