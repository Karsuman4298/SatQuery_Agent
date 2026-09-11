// HeadlineReveal — Cinematic headline with correct composition
// Positioned LEFT side to avoid overlapping the Earth hero on the right

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { AnimationPhase } from '../../types/animation';

interface HeadlineRevealProps {
  phase: AnimationPhase;
  prefersReducedMotion: boolean;
}

const showPhases: AnimationPhase[] = [
  'BRANDING_FORMING', 'ENTRY_READY', 'EARTH_HOVER', 'EARTH_ENTERING', 'PAGE_DISSOLVING',
];

const HeadlineReveal: React.FC<HeadlineRevealProps> = ({ phase, prefersReducedMotion }) => {
  const show = showPhases.includes(phase);
  const dissolving = phase === 'PAGE_DISSOLVING' || phase === 'EARTH_ENTERING';

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          key="headline"
          initial={{ opacity: 0 }}
          animate={{ opacity: dissolving ? 0 : 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: prefersReducedMotion ? 0.1 : 0.8, ease: 'easeOut' }}
          style={{
            position: 'fixed',
            // Left-aligned: gives Earth (positioned right-center) breathing room
            left: 'clamp(28px, 5vw, 80px)',
            top: '50%',
            transform: 'translateY(-50%)',
            zIndex: 10,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'flex-start',
            gap: '0',
            pointerEvents: 'none',
            maxWidth: 'clamp(260px, 38vw, 560px)',
          }}
        >
          {/* Subtle top rule */}
          <motion.div
            initial={{ scaleX: 0, opacity: 0 }}
            animate={{ scaleX: dissolving ? 0 : 1, opacity: dissolving ? 0 : 0.4 }}
            transition={{ duration: prefersReducedMotion ? 0.1 : 0.7, ease: 'easeOut', delay: 0.1 }}
            style={{
              width: '32px',
              height: '1px',
              background: '#00ff88',
              marginBottom: '1.2rem',
              transformOrigin: 'left',
            }}
          />

          {/* ASK THE EARTH. */}
          <motion.div
            initial={{ opacity: 0, x: -16 }}
            animate={{ opacity: dissolving ? 0 : 1, x: 0 }}
            transition={{ duration: prefersReducedMotion ? 0.1 : 0.9, ease: [0.16, 1, 0.3, 1], delay: 0.05 }}
            style={{
              fontFamily: "'Space Grotesk', sans-serif",
              fontWeight: 700,
              fontSize: 'clamp(24px, 3.6vw, 58px)',
              lineHeight: 1.05,
              color: '#eef2f7',
              letterSpacing: '-0.025em',
              display: 'block',
              textShadow: '0 2px 40px rgba(0,0,0,0.8)',
            }}
          >
            ASK THE EARTH.
          </motion.div>

          {/* GET EVIDENCE. */}
          <motion.div
            initial={{ opacity: 0, x: -16 }}
            animate={{ opacity: dissolving ? 0 : 1, x: 0 }}
            transition={{ duration: prefersReducedMotion ? 0.1 : 0.9, ease: [0.16, 1, 0.3, 1], delay: 0.18 }}
            style={{
              fontFamily: "'Space Grotesk', sans-serif",
              fontWeight: 700,
              fontSize: 'clamp(24px, 3.6vw, 58px)',
              lineHeight: 1.05,
              letterSpacing: '-0.025em',
              display: 'block',
              textShadow: '0 0 30px rgba(0,212,255,0.3)',
            }}
          >
            <span style={{ color: '#eef2f7' }}>GET </span>
            <span
              style={{
                color: '#00d4ff',
                textShadow: '0 0 25px rgba(0,212,255,0.55)',
              }}
            >
              EVIDENCE.
            </span>
          </motion.div>

          {/* Supporting text */}
          <motion.p
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: dissolving ? 0 : 0.72, y: 0 }}
            transition={{
              duration: prefersReducedMotion ? 0.1 : 1.0,
              delay: prefersReducedMotion ? 0 : 0.4,
              ease: 'easeOut',
            }}
            style={{
              fontFamily: "'Inter', sans-serif",
              fontWeight: 300,
              fontSize: 'clamp(10px, 1.05vw, 14px)',
              color: '#8a9ab8',
              letterSpacing: '0.025em',
              lineHeight: 1.65,
              marginTop: '1.4rem',
            }}
          >
            An Interactive Vision-Language Assistant<br />
            for Multimodal Remote Sensing Image Analysis.
          </motion.p>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default HeadlineReveal;
