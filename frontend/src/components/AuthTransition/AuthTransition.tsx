// AuthTransition — Temporary Phase 1 auth placeholder
// This is a clean callback state that Phase 2 will replace with /auth/signin

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { AnimationPhase } from '../../types/animation';

interface AuthTransitionProps {
  phase: AnimationPhase;
  // Phase 2 hook: onEarthEnter → /auth/signin
  onEarthEnter?: () => void;
}

const AuthTransition: React.FC<AuthTransitionProps> = ({ phase }) => {
  const show = phase === 'AUTH_TRANSITION_READY';

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          key="auth-transition"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 1.2, ease: 'easeOut' }}
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 100,
            background: '#020408',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '1.5rem',
          }}
        >
          {/* Brand mark */}
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4, ease: 'easeOut' }}
            style={{
              fontFamily: "'Space Grotesk', sans-serif",
              fontWeight: 600,
              fontSize: '13px',
              letterSpacing: '0.4em',
              color: '#00ff88',
              textTransform: 'uppercase',
              textShadow: '0 0 20px rgba(0,255,136,0.4)',
            }}
          >
            SATQUERY AI
          </motion.div>

          {/* Separator */}
          <motion.div
            initial={{ scaleX: 0 }}
            animate={{ scaleX: 1 }}
            transition={{ duration: 0.6, delay: 0.6, ease: 'easeOut' }}
            style={{
              width: '60px',
              height: '1px',
              background: 'linear-gradient(90deg, transparent, #00ff88, transparent)',
            }}
          />

          {/* Phase label */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.8 }}
            style={{
              fontFamily: "'Inter', sans-serif",
              fontWeight: 300,
              fontSize: '11px',
              letterSpacing: '0.25em',
              color: '#3a4a62',
              textTransform: 'uppercase',
            }}
          >
            AUTHENTICATION PHASE
          </motion.div>

          {/* Pulsing indicator */}
          <motion.div
            animate={{ opacity: [0.3, 1, 0.3] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut', delay: 1 }}
            style={{
              display: 'flex',
              gap: '6px',
              marginTop: '0.5rem',
            }}
          >
            {[0, 1, 2].map((i) => (
              <motion.div
                key={i}
                animate={{ opacity: [0.2, 1, 0.2] }}
                transition={{
                  duration: 1.5,
                  repeat: Infinity,
                  ease: 'easeInOut',
                  delay: i * 0.3,
                }}
                style={{
                  width: '4px',
                  height: '4px',
                  borderRadius: '50%',
                  background: '#00ff88',
                }}
              />
            ))}
          </motion.div>

          {/* Phase 2 note */}
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.35 }}
            transition={{ duration: 1, delay: 1.2 }}
            style={{
              fontFamily: "'Inter', sans-serif",
              fontWeight: 300,
              fontSize: '10px',
              color: '#3a4a62',
              letterSpacing: '0.15em',
              textAlign: 'center',
              marginTop: '2rem',
            }}
          >
            Phase 2 → /auth/signin
          </motion.p>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default AuthTransition;
