import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Mail, Lock, Eye, EyeOff, ArrowRight, ArrowLeft } from 'lucide-react';
import SatQueryLogo from '../../components/common/SatQueryLogo';
import SocialButton from '../../components/common/SocialButton';
import { useAuth } from '../../context/AuthContext';
import signinEarthBg from '../../assets/auth/signin_earth_orbit.jpg';
import satelliteModelImg from '../../assets/auth/satellite_model.jpg';
import './Auth.css';

export const SignInPage: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState<{ email?: string; password?: string; general?: string }>({});
  const [successMessage, setSuccessMessage] = useState('');
  const [socialNotice, setSocialNotice] = useState('');

  const validateForm = () => {
    const newErrors: { email?: string; password?: string } = {};
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!emailRegex.test(email.trim())) {
      newErrors.email = 'Please enter a valid email address';
    }

    if (!password) {
      newErrors.password = 'Password is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSuccessMessage('');
    setSocialNotice('');
    setErrors({});

    if (!validateForm()) return;

    setIsLoading(true);
    try {
      const result = await login(email, password);
      setIsLoading(false);
      if (result.success) {
        navigate('/dashboard');
      } else {
        setErrors({ general: result.error || 'Invalid email or password.' });
      }
    } catch (err) {
      setIsLoading(false);
      setErrors({ general: 'An unexpected error occurred. Please try again.' });
    }
  };

  return (
    <div className="satquery-auth-page">
      <div className="satquery-auth-container">
        {/* Left Column — Hero Orbit & Satellite Visual */}
        <motion.div
          className="satquery-auth-left"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8 }}
        >
          {/* Background Earth from orbit with satellite */}
          <img
            src={signinEarthBg}
            alt="Earth from orbit with satellite"
            className="satquery-auth-left-bg"
          />
          <div className="satquery-auth-left-overlay" />

          {/* Floating Satellite Hardware in Upper Orbit */}
          <motion.div
            initial={{ opacity: 0, y: -10, rotate: -6 }}
            animate={{ opacity: 0.95, y: [0, -5, 0], rotate: [-6, -3, -6] }}
            transition={{
              opacity: { duration: 1 },
              y: { duration: 6, repeat: Infinity, ease: 'easeInOut' },
              rotate: { duration: 8, repeat: Infinity, ease: 'easeInOut' },
            }}
            style={{
              position: 'absolute',
              top: '7%',
              left: '4%',
              width: '190px',
              height: '190px',
              pointerEvents: 'none',
              zIndex: 3,
              mixBlendMode: 'screen',
              WebkitMaskImage: 'radial-gradient(circle at center, rgba(0,0,0,1) 50%, rgba(0,0,0,0) 90%)',
              maskImage: 'radial-gradient(circle at center, rgba(0,0,0,1) 50%, rgba(0,0,0,0) 90%)',
              filter: 'drop-shadow(0 0 20px rgba(0, 212, 255, 0.25))',
            }}
          >
            <img
              src={satelliteModelImg}
              alt="Orbital Satellite"
              style={{ width: '100%', height: '100%', objectFit: 'contain' }}
            />
          </motion.div>

          <div className="satquery-auth-left-content">
            {/* Top Logo */}
            <div className="satquery-auth-header">
              <SatQueryLogo size="md" />
            </div>

            {/* Headline & Description */}
            <div className="satquery-auth-headline-block">
              <h1 className="satquery-auth-headline">
                Ask<br />
                the Earth.<br />
                Get<br />
                Evidence.
              </h1>
              <div className="satquery-auth-headline-line" />
              <p className="satquery-auth-description">
                An interactive<br />
                Vision-Language Assistant<br />
                for Multimodal Remote Sensing<br />
                Image Analysis.
              </p>

              {/* Stats Bar */}
              <div className="satquery-auth-stats">
                <div className="satquery-auth-stat-item">
                  <span className="satquery-auth-stat-val">50+</span>
                  <span className="satquery-auth-stat-lbl">Satellite Datasets</span>
                </div>
                <div className="satquery-auth-stat-divider" />
                <div className="satquery-auth-stat-item">
                  <span className="satquery-auth-stat-val">10K+</span>
                  <span className="satquery-auth-stat-lbl">Queries Analyzed</span>
                </div>
                <div className="satquery-auth-stat-divider" />
                <div className="satquery-auth-stat-item">
                  <span className="satquery-auth-stat-val">95%</span>
                  <span className="satquery-auth-stat-lbl">Accuracy Rate</span>
                </div>
              </div>
            </div>

            {/* Left Hero Bottom Banner */}
            <div className="satquery-auth-left-footer">
              <span className="satquery-auth-left-footer-dash" />
              <span>A GREENER, SAFER, SMARTER TOMORROW.</span>
            </div>
          </div>
        </motion.div>

        {/* Right Column — Sign In Form */}
        <motion.div
          className="satquery-auth-right"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8, delay: 0.1 }}
        >
          {/* Back to Home Link */}
          <div className="satquery-auth-top-nav">
            <button
              onClick={() => navigate('/')}
              className="satquery-back-home-link"
              type="button"
              aria-label="Back to Home"
            >
              <ArrowLeft size={15} />
              <span>Back to Home</span>
            </button>
          </div>

          {/* Sign In Card */}
          <div className="satquery-auth-card">
            <div className="satquery-card-tag">Welcome Back</div>
            <h2 className="satquery-card-title">Sign in to SatQuery AI</h2>
            <p className="satquery-card-subtitle">
              Continue your journey to explore the Earth with AI.
            </p>

            {successMessage && (
              <div className="satquery-form-alert success">
                {successMessage}
              </div>
            )}
            {errors.general && (
              <div className="satquery-form-alert error">
                {errors.general}
              </div>
            )}
            {socialNotice && (
              <div className="satquery-form-alert error" style={{ background: 'rgba(0, 212, 255, 0.1)', borderColor: 'rgba(0, 212, 255, 0.3)', color: '#67e8f9' }}>
                {socialNotice}
              </div>
            )}

            <form onSubmit={handleSubmit} className="satquery-form" noValidate>
              {/* Email Address */}
              <div>
                <div className="satquery-input-group">
                  <span className="satquery-input-icon">
                    <Mail size={17} />
                  </span>
                  <input
                    type="email"
                    placeholder="Email address"
                    value={email}
                    onChange={(e) => {
                      setEmail(e.target.value);
                      if (errors.email) setErrors((prev) => ({ ...prev, email: undefined }));
                    }}
                    className={`satquery-input ${errors.email ? 'satquery-input-error-border' : ''}`}
                    autoComplete="email"
                    required
                  />
                </div>
                {errors.email && (
                  <span className="satquery-field-error">{errors.email}</span>
                )}
              </div>

              {/* Password */}
              <div>
                <div className="satquery-input-group">
                  <span className="satquery-input-icon">
                    <Lock size={17} />
                  </span>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Password"
                    value={password}
                    onChange={(e) => {
                      setPassword(e.target.value);
                      if (errors.password) setErrors((prev) => ({ ...prev, password: undefined }));
                    }}
                    className={`satquery-input ${errors.password ? 'satquery-input-error-border' : ''}`}
                    autoComplete="current-password"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="satquery-input-toggle"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
                {errors.password && (
                  <span className="satquery-field-error">{errors.password}</span>
                )}
              </div>

              {/* Remember me & Forgot password */}
              <div className="satquery-form-options">
                <label className="satquery-checkbox-label">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="satquery-checkbox"
                  />
                  <span>Remember me</span>
                </label>
                <button
                  type="button"
                  onClick={() => setSuccessMessage('Password reset instructions sent to your registered email.')}
                  className="satquery-link"
                >
                  Forgot password?
                </button>
              </div>

              {/* Sign in Button */}
              <button
                type="submit"
                disabled={isLoading}
                className="satquery-submit-btn"
              >
                {isLoading ? (
                  <span>Signing in...</span>
                ) : (
                  <>
                    <span>Sign in</span>
                    <ArrowRight size={17} />
                  </>
                )}
              </button>
            </form>

            {/* Helper text below the login form */}
            <div
              style={{
                marginTop: '12px',
                padding: '7px 10px',
                background: 'rgba(0, 212, 255, 0.06)',
                border: '1px solid rgba(0, 212, 255, 0.18)',
                borderRadius: '6px',
                fontSize: '11.5px',
                color: '#7dd3fc',
                textAlign: 'center',
                fontFamily: "'Space Grotesk', 'Inter', monospace",
                letterSpacing: '0.02em',
                userSelect: 'all',
              }}
            >
              Demo: demo@satquery.ai / SatQuery@123
            </div>

            {/* Social Auth Divider */}
            <div className="satquery-divider">
              <span className="satquery-divider-line" />
              <span className="satquery-divider-text">OR CONTINUE WITH</span>
              <span className="satquery-divider-line" />
            </div>

            {/* Social Logins */}
            <div className="satquery-social-stack">
              <SocialButton
                provider="google"
                onClick={() => setSocialNotice('Google OAuth coming soon. Please use demo credentials.')}
              />
              <SocialButton
                provider="microsoft"
                onClick={() => setSocialNotice('Microsoft OAuth coming soon. Please use demo credentials.')}
              />
            </div>

            {/* Switch to Sign Up */}
            <div className="satquery-card-switch">
              Don't have an account?{' '}
              <button
                type="button"
                onClick={() => navigate('/signup')}
                className="satquery-link"
              >
                Sign up
              </button>
            </div>
          </div>

          {/* Bottom Footer Credits */}
          <div className="satquery-auth-page-footer">
            ISRO &nbsp;|&nbsp; NASA &nbsp;|&nbsp; Copernicus &nbsp;|&nbsp; Making Earth Data Accessible
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default SignInPage;
