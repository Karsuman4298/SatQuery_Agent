// EntryPage — Main Phase 1 entry page orchestrator for SatQuery AI
// Composes: ParticleCanvas + EarthScene + BrandReveal + HeadlineReveal + EarthHint + AuthTransition

import React, { useRef, useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import ParticleCanvas, { type ParticleCanvasHandle } from '../../components/ParticleCanvas/ParticleCanvas';
import EarthScene from '../../components/EarthScene/EarthScene';
import BrandReveal from '../../components/BrandReveal/BrandReveal';
import HeadlineReveal from '../../components/BrandReveal/HeadlineReveal';
import EarthHint from '../../components/EarthInteraction/EarthHint';
import AuthTransition from '../../components/AuthTransition/AuthTransition';
import { useAnimationState } from '../../hooks/useAnimationState';
import type { AnimationPhase } from '../../types/animation';

const EntryPage: React.FC = () => {
  const navigate = useNavigate();
  const { phase, setPhase, onEarthEnter, isEarthInteractive, prefersReducedMotion } =
    useAnimationState();
  const particleCanvasRef = useRef<ParticleCanvasHandle>(null);
  const [isEarthHovering, setIsEarthHovering] = useState(false);

  const handlePhaseAdvance = useCallback(
    (newPhase: AnimationPhase) => {
      setPhase(newPhase);
    },
    [setPhase]
  );

  const handleEarthEnter = useCallback(() => {
    // Trigger particle dissolve simultaneously
    particleCanvasRef.current?.triggerDissolve();
    onEarthEnter();
  }, [onEarthEnter]);

  const handleHoverChange = useCallback(
    (hovering: boolean) => {
      setIsEarthHovering(hovering);
      if (phase === 'ENTRY_READY' && hovering) {
        setPhase('EARTH_HOVER');
      } else if (phase === 'EARTH_HOVER' && !hovering) {
        setPhase('ENTRY_READY');
      }
    },
    [phase, setPhase]
  );

  // Transition into Phase 2 /login when dissolve finishes
  useEffect(() => {
    if (phase === 'AUTH_TRANSITION_READY') {
      const timer = setTimeout(() => {
        navigate('/login');
      }, 600);
      return () => clearTimeout(timer);
    }
  }, [phase, navigate]);

  return (
    <main
      style={{
        width: '100vw',
        height: '100vh',
        background: '#020408',
        position: 'relative',
        overflow: 'hidden',
      }}
      aria-label="SatQuery AI — Entry Experience"
    >
      {/* Layer 1: Pixel Canvas (z-index: 1) — particle system */}
      <ParticleCanvas
        ref={particleCanvasRef}
        phase={phase}
        prefersReducedMotion={prefersReducedMotion}
        onPhaseAdvance={handlePhaseAdvance}
      />

      {/* Layer 2: Earth (z-index: 2) — Three.js WebGL Earth */}
      <EarthScene
        phase={phase}
        onEarthEnter={handleEarthEnter}
        onHoverChange={handleHoverChange}
      />

      {/* Layer 3: UI Overlays (z-index: 10+) */}
      <BrandReveal phase={phase} prefersReducedMotion={prefersReducedMotion} />
      <HeadlineReveal phase={phase} prefersReducedMotion={prefersReducedMotion} />
      <EarthHint phase={phase} isHovering={isEarthHovering} />

      {/* Auth Transition (z-index: 100) */}
      <AuthTransition phase={phase} />

      {/* Keyboard accessibility: Enter key fires Earth entry */}
      {isEarthInteractive && (
        <button
          aria-label="Enter SatQuery AI — Press Enter to proceed"
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') handleEarthEnter();
          }}
          style={{
            position: 'fixed',
            opacity: 0,
            pointerEvents: 'none',
            width: 1,
            height: 1,
          }}
        />
      )}
    </main>
  );
};

export default EntryPage;
