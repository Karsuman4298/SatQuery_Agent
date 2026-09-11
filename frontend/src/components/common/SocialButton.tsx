import React from 'react';

interface SocialButtonProps {
  provider: 'google' | 'microsoft';
  onClick?: () => void;
  disabled?: boolean;
}

export const SocialButton: React.FC<SocialButtonProps> = ({ provider, onClick, disabled }) => {
  const isGoogle = provider === 'google';

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="satquery-social-btn"
      style={{
        width: '100%',
        height: '46px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '12px',
        background: 'rgba(15, 23, 38, 0.65)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: '8px',
        color: '#d1dced',
        fontFamily: "'Inter', sans-serif",
        fontSize: '13.5px',
        fontWeight: 500,
        cursor: disabled ? 'not-allowed' : 'pointer',
        transition: 'all 0.2s ease',
        outline: 'none',
      }}
    >
      {isGoogle ? (
        // Official Google G icon
        <svg width="18" height="18" viewBox="0 0 24 24">
          <path
            fill="#4285F4"
            d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.66-5.17 3.66-9.17z"
          />
          <path
            fill="#34A853"
            d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.33 24 12 24z"
          />
          <path
            fill="#FBBC05"
            d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.18 0 9.98 0 12s.45 3.82 1.25 5.42l4.03-3.15z"
          />
          <path
            fill="#EA4335"
            d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.33 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98z"
          />
        </svg>
      ) : (
        // Official Microsoft 4-square icon
        <svg width="18" height="18" viewBox="0 0 23 23">
          <rect x="1" y="1" width="10" height="10" fill="#F25022" />
          <rect x="12" y="1" width="10" height="10" fill="#7FBA00" />
          <rect x="1" y="12" width="10" height="10" fill="#00A4EF" />
          <rect x="12" y="12" width="10" height="10" fill="#FFB900" />
        </svg>
      )}
      <span>{isGoogle ? 'Continue with Google' : 'Continue with Microsoft'}</span>
    </button>
  );
};

export default SocialButton;
