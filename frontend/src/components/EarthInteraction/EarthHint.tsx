// EarthHint — Subtle "Click Earth to Enter" hint, bottom-left
// Fades in after entry ready, hides on hover (user is already over Earth)

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { AnimationPhase } from '../../types/animation';

interface EarthHintProps {
  phase: AnimationPhase;
  isHovering: boolean;
}

const EarthHint: React.FC<EarthHintProps> = ({ phase, isHovering }) => {
  const show = phase === 'ENTRY_READY' || phase === 'EARTH_HOVER';

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          key="earth-hint"
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: isHovering ? 0 : 0.6, y: 0 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.8, delay: 0.6, ease: 'easeOut' }}
          style={{
            position: 'fixed',
            bottom: 'clamp(20px, 3.5vh, 40px)',
            left: 'clamp(28px, 5vw, 80px)',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            zIndex: 10,
            pointerEvents: 'none',
          }}
        >
          {/* Pulsing orbit indicator */}
          <div style={{ position: 'relative', width: '12px', height: '12px', flexShrink: 0 }}>
            <motion.div
              animate={{ scale: [1, 1.8, 1], opacity: [0.9, 0, 0.9] }}
              transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
              style={{
                position: 'absolute',
                inset: 0,
                borderRadius: '50%',
                border: '1px solid rgba(0,255,136,0.7)',
              }}
            />
            <div
              style={{
                position: 'absolute',
                inset: '3px',
                borderRadius: '50%',
                background: '#00ff88',
                boxShadow: '0 0 6px rgba(0,255,136,0.9)',
              }}
            />
          </div>

          <span
            style={{
              fontFamily: "'Space Grotesk', sans-serif",
              fontWeight: 400,
              fontSize: 'clamp(9px, 0.85vw, 11px)',
              color: '#6b7fa3',
              letterSpacing: '0.22em',
              textTransform: 'uppercase',
            }}
          >
            Click anywhere on Earth to enter
          </span>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default EarthHint;
