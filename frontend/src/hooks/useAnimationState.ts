// useAnimationState — Central state machine for SatQuery AI Phase 1
import { useState, useCallback, useRef } from 'react';
import type { AnimationPhase } from '../types/animation';

interface AnimationStateReturn {
  phase: AnimationPhase;
  setPhase: (phase: AnimationPhase) => void;
  onEarthEnter: () => void;
  isEarthInteractive: boolean;
  prefersReducedMotion: boolean;
}

export function useAnimationState(): AnimationStateReturn {
  const [phase, setPhaseState] = useState<AnimationPhase>('INTRO');
  const phaseRef = useRef<AnimationPhase>('INTRO');

  const prefersReducedMotion =
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const setPhase = useCallback((newPhase: AnimationPhase) => {
    phaseRef.current = newPhase;
    setPhaseState(newPhase);
  }, []);

  const onEarthEnter = useCallback(() => {
    const current = phaseRef.current;
    if (current !== 'ENTRY_READY' && current !== 'EARTH_HOVER') return;
    setPhase('EARTH_ENTERING');
    setTimeout(() => setPhase('PAGE_DISSOLVING'), 200);
    setTimeout(() => setPhase('AUTH_TRANSITION_READY'), 3200);
  }, [setPhase]);

  const isEarthInteractive =
    phase === 'ENTRY_READY' || phase === 'EARTH_HOVER';

  return {
    phase,
    setPhase,
    onEarthEnter,
    isEarthInteractive,
    prefersReducedMotion,
  };
}
