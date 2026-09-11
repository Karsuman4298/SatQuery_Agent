// BrandReveal — SATQUERY AI brand mark, top-left anchored
// Consistent with left-side composition where headline lives

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { AnimationPhase } from '../../types/animation';

interface BrandRevealProps {
  phase: AnimationPhase;
  prefersReducedMotion: boolean;
}

const showPhases: AnimationPhase[] = [
  'BRANDING_FORMING', 'ENTRY_READY', 'EARTH_HOVER', 'EARTH_ENTERING', 'PAGE_DISSOLVING',
];

const BrandReveal: React.FC<BrandRevealProps> = ({ phase, prefersReducedMotion }) => {
  const show = showPhases.includes(phase);
  const dissolving = phase === 'PAGE_DISSOLVING' || phase === 'EARTH_ENTERING';

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          key="brand"
          initial={{ opacity: 0 }}
          animate={{ opacity: dissolving ? 0 : 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: prefersReducedMotion ? 0.1 : 0.8, ease: 'easeOut' }}
          style={{
            position: 'fixed',
            top: 'clamp(20px, 3vh, 36px)',
            left: 'clamp(28px, 5vw, 80px)',
            zIndex: 10,
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            pointerEvents: 'none',
          }}
        >
          {/* Small icon dot — satellite data indicator */}
          <motion.div
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: dissolving ? 0 : 1, opacity: dissolving ? 0 : 1 }}
            transition={{ duration: prefersReducedMotion ? 0.1 : 0.5, ease: 'backOut' }}
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              background: '#00ff88',
              boxShadow: '0 0 8px rgba(0,255,136,0.9), 0 0 20px rgba(0,255,136,0.3)',
              flexShrink: 0,
            }}
          />

          {/* SATQUERY AI wordmark */}
          <motion.span
            initial={{ opacity: 0, letterSpacing: '0.5em', x: -8 }}
            animate={{
              opacity: dissolving ? 0 : 1,
              letterSpacing: '0.32em',
              x: 0,
            }}
            transition={{ duration: prefersReducedMotion ? 0.1 : 1.1, ease: 'easeOut', delay: 0.08 }}
            style={{
              fontFamily: "'Space Grotesk', sans-serif",
              fontWeight: 600,
              fontSize: 'clamp(10px, 1.05vw, 14px)',
              color: '#00ff88',
              textTransform: 'uppercase',
              textShadow: '0 0 16px rgba(0,255,136,0.5)',
              display: 'inline-block',
            }}
          >
            SATQUERY AI
          </motion.span>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default BrandReveal;
