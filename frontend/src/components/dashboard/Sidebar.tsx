import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Compass,
  History,
  FileText,
  Settings,
  HelpCircle,
} from 'lucide-react';
import './DashboardComponents.css';

export const Sidebar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const navItems = [
    { label: 'Dashboard', icon: LayoutDashboard, path: '/dashboard', active: location.pathname === '/dashboard' },
    {
      label: 'New Analysis',
      icon: Compass,
      path: '/new-analysis',
      active: location.pathname === '/new-analysis' || location.pathname.startsWith('/analysis/'),
    },
    {
      label: 'History',
      icon: History,
      path: '/history',
      active: location.pathname === '/history',
    },
    {
      label: 'Reports',
      icon: FileText,
      path: '/reports',
      active: location.pathname === '/reports',
    },
  ];


  const secondaryNavItems = [
    { label: 'Settings', icon: Settings, path: '/dashboard', active: false },
    { label: 'Help', icon: HelpCircle, path: '/dashboard', active: false },
  ];

  return (
    <aside className="satquery-sidebar">
      {/* Brand Header */}
      <div className="satquery-sidebar-brand" onClick={() => navigate('/dashboard')}>
        <div className="satquery-sidebar-logo-icon">
          {/* Diamond Quad Logo */}
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <rect x="11" y="2" width="6" height="6" rx="1.5" transform="rotate(45 11 2)" fill="#00ff88" />
            <rect x="4" y="9" width="6" height="6" rx="1.5" transform="rotate(45 4 9)" fill="#00d4ff" />
            <rect x="18" y="9" width="6" height="6" rx="1.5" transform="rotate(45 18 9)" fill="#00e575" />
            <rect x="11" y="16" width="6" height="6" rx="1.5" transform="rotate(45 11 16)" fill="#00b4d8" />
          </svg>
        </div>
        <div className="satquery-sidebar-brand-text">
          <div className="satquery-brand-title">
            <span>SatQuery</span> <span className="green">AI</span>
          </div>
          <div className="satquery-brand-sub">See Earth. Ask More.</div>
        </div>
      </div>

      {/* Main Navigation */}
      <nav className="satquery-sidebar-nav">
        <div className="satquery-nav-group">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.label}
                type="button"
                onClick={() => navigate(item.path)}
                className={`satquery-nav-item ${item.active ? 'active' : ''}`}
              >
                <Icon size={18} className="satquery-nav-icon" />
                <span className="satquery-nav-label">{item.label}</span>
              </button>
            );
          })}
        </div>

        <div className="satquery-nav-divider" />

        <div className="satquery-nav-group">
          {secondaryNavItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.label}
                type="button"
                onClick={() => navigate(item.path)}
                className={`satquery-nav-item ${item.active ? 'active' : ''}`}
              >
                <Icon size={18} className="satquery-nav-icon" />
                <span className="satquery-nav-label">{item.label}</span>
              </button>
            );
          })}
        </div>
      </nav>

      {/* Bottom Footer Widget */}
      <div className="satquery-sidebar-footer">
        <div className="satquery-sidebar-earth-glow" />
        <p className="satquery-sidebar-tagline">
          Satellite data<br />for a better<br />tomorrow.
        </p>
        <div className="satquery-sidebar-dash" />
      </div>
    </aside>
  );
};

export default Sidebar;
