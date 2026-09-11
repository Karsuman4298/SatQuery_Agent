import React from 'react';

interface SatQueryLogoProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const SatQueryLogo: React.FC<SatQueryLogoProps> = ({ size = 'md' }) => {
  const iconSize = size === 'sm' ? 24 : size === 'lg' ? 36 : 30;
  const titleSize = size === 'sm' ? '1.1rem' : size === 'lg' ? '1.5rem' : '1.3rem';
  const subtitleSize = size === 'sm' ? '0.55rem' : size === 'lg' ? '0.7rem' : '0.62rem';

  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '12px', userSelect: 'none' }}>
      {/* Orbital Planet Icon */}
      <svg
        width={iconSize}
        height={iconSize}
        viewBox="0 0 40 40"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={{ filter: 'drop-shadow(0 0 10px rgba(0, 255, 136, 0.4))' }}
      >
        {/* Planet sphere */}
        <circle cx="20" cy="20" r="10" fill="url(#planet-grad)" />
        {/* Orbit Ring Back */}
        <ellipse
          cx="20"
          cy="20"
          rx="18"
          ry="6.5"
          transform="rotate(-28 20 20)"
          stroke="url(#ring-grad)"
          strokeWidth="1.8"
          strokeDasharray="50 30"
        />
        {/* Planet front highlights */}
        <circle cx="18" cy="18" r="9" fill="url(#planet-light)" />
        {/* Orbit Ring Front */}
        <path
          d="M 5 28 C 12 36, 28 34, 35 22"
          stroke="#00ff88"
          strokeWidth="2"
          strokeLinecap="round"
          style={{ filter: 'drop-shadow(0 0 6px #00ff88)' }}
        />
        {/* Orbit Dot */}
        <circle cx="34" cy="23" r="1.8" fill="#ffffff" style={{ filter: 'drop-shadow(0 0 4px #ffffff)' }} />

        <defs>
          <radialGradient id="planet-grad" cx="30%" cy="30%" r="70%">
            <stop offset="0%" stopColor="#00d4ff" />
            <stop offset="50%" stopColor="#0a3d62" />
            <stop offset="100%" stopColor="#020814" />
          </radialGradient>
          <linearGradient id="ring-grad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#00d4ff" stopOpacity="0.3" />
            <stop offset="50%" stopColor="#00ff88" />
            <stop offset="100%" stopColor="#00d4ff" stopOpacity="0.8" />
          </linearGradient>
          <radialGradient id="planet-light" cx="35%" cy="30%" r="60%">
            <stop offset="0%" stopColor="rgba(0, 255, 136, 0.35)" />
            <stop offset="60%" stopColor="transparent" />
          </radialGradient>
        </defs>
      </svg>

      {/* Brand Text */}
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <span
            style={{
              fontFamily: "'Space Grotesk', sans-serif",
              fontWeight: 700,
              fontSize: titleSize,
              color: '#ffffff',
              letterSpacing: '-0.02em',
              lineHeight: 1.1,
            }}
          >
            SatQuery
          </span>
          <span
            style={{
              fontFamily: "'Space Grotesk', sans-serif",
              fontWeight: 700,
              fontSize: titleSize,
              color: '#00ff88',
              letterSpacing: '-0.02em',
              lineHeight: 1.1,
              textShadow: '0 0 12px rgba(0, 255, 136, 0.4)',
            }}
          >
            AI
          </span>
        </div>
        <span
          style={{
            fontFamily: "'Space Grotesk', sans-serif",
            fontWeight: 500,
            fontSize: subtitleSize,
            color: '#6b7fa3',
            letterSpacing: '0.22em',
            textTransform: 'uppercase',
            marginTop: '3px',
          }}
        >
          INSIGHTS FROM ABOVE
        </span>
      </div>
    </div>
  );
};

export default SatQueryLogo;
