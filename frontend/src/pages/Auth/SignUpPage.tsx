import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { User, Mail, Lock, Eye, EyeOff, ArrowRight, ArrowLeft } from 'lucide-react';
import SatQueryLogo from '../../components/common/SatQueryLogo';
import SocialButton from '../../components/common/SocialButton';
import { useAuth } from '../../context/AuthContext';
import signupDeltaBg from '../../assets/auth/signup_satellite_delta.jpg';
import opticalThumb from '../../assets/auth/modality_optical.jpg';
import sarThumb from '../../assets/auth/modality_sar.jpg';
import multispectralThumb from '../../assets/auth/modality_multispectral.jpg';
import thermalThumb from '../../assets/auth/modality_thermal.jpg';
import './Auth.css';

export const SignUpPage: React.FC = () => {
  const navigate = useNavigate();
  const { signup } = useAuth();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [agreeTerms, setAgreeTerms] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState<{
    fullName?: string;
    email?: string;
    password?: string;
    confirmPassword?: string;
    agreeTerms?: string;
    general?: string;
  }>({});
  const [successMessage, setSuccessMessage] = useState('');
  const [socialNotice, setSocialNotice] = useState('');

  const validateForm = () => {
    const newErrors: typeof errors = {};
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!fullName.trim()) {
      newErrors.fullName = 'Full Name is required';
    }

    if (!email.trim()) {
      newErrors.email = 'Email address is required';
    } else if (!emailRegex.test(email.trim())) {
      newErrors.email = 'Please enter a valid email address';
    }

    if (!password) {
      newErrors.password = 'Password is required';
    } else if (password.length < 6) {
      newErrors.password = 'Password must be at least 6 characters';
    }

    if (!confirmPassword) {
      newErrors.confirmPassword = 'Confirm Password is required';
    } else if (password !== confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }

    if (!agreeTerms) {
      newErrors.agreeTerms = 'You must agree to the Terms of Service & Privacy Policy';
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
      const res = await signup(fullName, email, password);
      setIsLoading(false);
      if (res.success) {
        if ((res as any).needsConfirmation) {
          setSuccessMessage(
            `✅ Account created! A confirmation email has been sent to ${email}. Please verify it, then sign in.`
          );
          setTimeout(() => navigate('/login'), 4000);
        } else {
          setSuccessMessage('Account created successfully! Redirecting to Dashboard...');
          setTimeout(() => navigate('/dashboard'), 400);
        }
      } else {
        setErrors({ general: res.error || 'Failed to create account.' });
      }
    } catch (err) {
      setIsLoading(false);
      setErrors({ general: 'An unexpected error occurred. Please try again.' });
    }
  };

  return (
    <div className="satquery-auth-page">
      <div className="satquery-auth-container">
        {/* Left Column — Hero Remote Sensing & Earth Science Visual */}
        <motion.div
          className="satquery-auth-left"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8 }}
        >
          {/* Satellite Delta Imagery */}
          <img
            src={signupDeltaBg}
            alt="High resolution satellite remote sensing delta"
            className="satquery-auth-left-bg"
          />
          <div className="satquery-auth-left-overlay" />

          {/* Target Reticle Overlay */}
          <div className="satquery-target-reticle" />

          <div className="satquery-auth-left-content">
            {/* Top Logo */}
            <div className="satquery-auth-header">
              <SatQueryLogo size="md" />
            </div>

            {/* Headline & Modality Badges */}
            <div className="satquery-auth-headline-block">
              <h1 className="satquery-auth-headline">
                Explore.<br />
                Analyze.<br />
                Understand.<br />
                For a Better<br />
                <span className="satquery-auth-headline-green">Tomorrow.</span>
              </h1>

              <p className="satquery-auth-description">
                Transforming satellite<br />
                data into real-world impact<br />
                through AI.
              </p>

              {/* 4 Modality Cards: Optical, SAR, Multispectral, Thermal */}
              <div className="satquery-auth-modalities">
                <div className="satquery-modality-card">
                  <div className="satquery-modality-thumb">
                    <img src={opticalThumb} alt="Optical Satellite Modality" />
                  </div>
                  <span className="satquery-modality-lbl">Optical</span>
                </div>

                <div className="satquery-modality-card">
                  <div className="satquery-modality-thumb">
                    <img src={sarThumb} alt="SAR Radar Modality" />
                  </div>
                  <span className="satquery-modality-lbl">SAR</span>
                </div>

                <div className="satquery-modality-card">
                  <div className="satquery-modality-thumb">
                    <img src={multispectralThumb} alt="Multispectral Modality" />
                  </div>
                  <span className="satquery-modality-lbl">Multispectral</span>
                </div>

                <div className="satquery-modality-card">
                  <div className="satquery-modality-thumb">
                    <img src={thermalThumb} alt="Thermal Modality" />
                  </div>
                  <span className="satquery-modality-lbl">Thermal</span>
                </div>
              </div>
            </div>

            {/* Left Hero Bottom Banner */}
            <div className="satquery-auth-left-footer">
              <span className="satquery-auth-left-footer-dash" />
              <span>ONE PLANET, LIMITLESS INSIGHTS.</span>
            </div>
          </div>
        </motion.div>

        {/* Right Column — Sign Up Form */}
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

          {/* Sign Up Card */}
          <div className="satquery-auth-card">
            <div className="satquery-card-tag">Create Your Account</div>
            <h2 className="satquery-card-title">Join SatQuery AI</h2>
            <p className="satquery-card-subtitle">
              Be a part of the next generation of geospatial intelligence.
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
              {/* Full Name */}
              <div>
                <div className="satquery-input-group">
                  <span className="satquery-input-icon">
                    <User size={17} />
                  </span>
                  <input
                    type="text"
                    placeholder="Full Name"
                    value={fullName}
                    onChange={(e) => {
                      setFullName(e.target.value);
                      if (errors.fullName) setErrors((prev) => ({ ...prev, fullName: undefined }));
                    }}
                    className={`satquery-input ${errors.fullName ? 'satquery-input-error-border' : ''}`}
                    autoComplete="name"
                    required
                  />
                </div>
                {errors.fullName && (
                  <span className="satquery-field-error">{errors.fullName}</span>
                )}
              </div>

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
                    autoComplete="new-password"
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

              {/* Confirm Password */}
              <div>
                <div className="satquery-input-group">
                  <span className="satquery-input-icon">
                    <Lock size={17} />
                  </span>
                  <input
                    type={showConfirmPassword ? 'text' : 'password'}
                    placeholder="Confirm Password"
                    value={confirmPassword}
                    onChange={(e) => {
                      setConfirmPassword(e.target.value);
                      if (errors.confirmPassword) setErrors((prev) => ({ ...prev, confirmPassword: undefined }));
                    }}
                    className={`satquery-input ${errors.confirmPassword ? 'satquery-input-error-border' : ''}`}
                    autoComplete="new-password"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="satquery-input-toggle"
                    aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                  >
                    {showConfirmPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
                {errors.confirmPassword && (
                  <span className="satquery-field-error">{errors.confirmPassword}</span>
                )}
              </div>

              {/* Agree Terms Checkbox */}
              <div>
                <label className="satquery-checkbox-label" style={{ fontSize: '12px', lineHeight: 1.4 }}>
                  <input
                    type="checkbox"
                    checked={agreeTerms}
                    onChange={(e) => {
                      setAgreeTerms(e.target.checked);
                      if (errors.agreeTerms) setErrors((prev) => ({ ...prev, agreeTerms: undefined }));
                    }}
                    className="satquery-checkbox"
                    style={{ flexShrink: 0 }}
                  />
                  <span>
                    I agree to the{' '}
                    <span className="satquery-link" style={{ cursor: 'pointer' }}>Terms of Service</span>
                    {' '}and{' '}
                    <span className="satquery-link" style={{ cursor: 'pointer' }}>Privacy Policy</span>
                  </span>
                </label>
                {errors.agreeTerms && (
                  <span className="satquery-field-error" style={{ marginTop: '4px' }}>
                    {errors.agreeTerms}
                  </span>
                )}
              </div>

              {/* Create Account Button */}
              <button
                type="submit"
                disabled={isLoading}
                className="satquery-submit-btn"
              >
                {isLoading ? (
                  <span>Creating Account...</span>
                ) : (
                  <>
                    <span>Create Account</span>
                    <ArrowRight size={17} />
                  </>
                )}
              </button>
            </form>

            {/* Social Auth Divider */}
            <div className="satquery-divider">
              <span className="satquery-divider-line" />
              <span className="satquery-divider-text">OR SIGN UP WITH</span>
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

            {/* Switch to Sign In */}
            <div className="satquery-card-switch">
              Already have an account?{' '}
              <button
                type="button"
                onClick={() => navigate('/login')}
                className="satquery-link"
              >
                Sign in
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default SignUpPage;
