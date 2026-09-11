import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Bell, ChevronDown, CheckCircle2, User as UserIcon, Key, Settings, LogOut } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import './DashboardComponents.css';

interface TopBarProps {
  onSearch?: (query: string) => void;
}

export const TopBar: React.FC<TopBarProps> = ({ onSearch }) => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const [showNotifications, setShowNotifications] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const notifRef = useRef<HTMLDivElement>(null);
  const userMenuRef = useRef<HTMLDivElement>(null);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
    onSearch?.(e.target.value);
  };

  // Close menus when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(event.target as Node)) {
        setShowNotifications(false);
      }
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setShowUserMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <header className="satquery-topbar">
      {/* Search Field */}
      <div className="satquery-topbar-search">
        <Search size={16} className="satquery-search-icon" />
        <input
          type="text"
          placeholder="Search analyses..."
          value={searchQuery}
          onChange={handleSearchChange}
          className="satquery-search-input"
        />
      </div>

      {/* Right User Navigation */}
      <div className="satquery-topbar-right">
        {/* Notification Bell */}
        <div className="satquery-notif-wrapper" ref={notifRef}>
          <button
            type="button"
            className={`satquery-notification-btn ${showNotifications ? 'active' : ''}`}
            aria-label="Notifications"
            onClick={() => {
              setShowNotifications(!showNotifications);
              setShowUserMenu(false);
            }}
          >
            <Bell size={17} />
            <span className="satquery-notification-dot" />
          </button>

          {/* Notifications Dropdown */}
          {showNotifications && (
            <div className="satquery-popover notif-popover">
              <div className="popover-header">
                <span className="popover-title">Notifications</span>
                <span className="popover-badge">3 New</span>
              </div>
              <div className="popover-list">
                <div className="popover-item unread">
                  <CheckCircle2 size={16} color="#00ff88" className="popover-icon" />
                  <div className="popover-item-content">
                    <p className="popover-item-text">Agricultural Field Analysis completed</p>
                    <span className="popover-item-time">2 hours ago</span>
                  </div>
                </div>
                <div className="popover-item unread">
                  <CheckCircle2 size={16} color="#00d4ff" className="popover-icon" />
                  <div className="popover-item-content">
                    <p className="popover-item-text">Coastal Change Detection tile ready</p>
                    <span className="popover-item-time">Yesterday</span>
                  </div>
                </div>
                <div className="popover-item">
                  <CheckCircle2 size={16} color="#94a3b8" className="popover-icon" />
                  <div className="popover-item-content">
                    <p className="popover-item-text">System spectral calibration verified</p>
                    <span className="popover-item-time">2 days ago</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* User Profile Pill */}
        <div className="satquery-user-wrapper" ref={userMenuRef}>
          <div
            className={`satquery-user-profile ${showUserMenu ? 'active' : ''}`}
            onClick={() => {
              setShowUserMenu(!showUserMenu);
              setShowNotifications(false);
            }}
          >
            <div className="satquery-user-avatar">
              <svg width="34" height="34" viewBox="0 0 34 34" fill="none">
                <circle cx="17" cy="17" r="17" fill="#1e293b" />
                <circle cx="17" cy="13" r="6" fill="#94a3b8" />
                <path
                  d="M6 29C6 24 11 21 17 21C23 21 28 24 28 29"
                  fill="#64748b"
                />
              </svg>
            </div>
            <span className="satquery-user-name">{user?.name || 'Explorer'}</span>
            <ChevronDown size={14} className={`satquery-user-chevron ${showUserMenu ? 'open' : ''}`} />
          </div>

          {/* User Profile Dropdown */}
          {showUserMenu && (
            <div className="satquery-popover user-popover">
              <div className="user-popover-header">
                <div className="user-popover-name">{user?.name || 'Explorer'}</div>
                <div className="user-popover-email">{user?.email || 'demo@satquery.ai'}</div>
              </div>
              <div className="popover-divider" />
              <button
                type="button"
                className="user-menu-item"
                onClick={() => {
                  setShowUserMenu(false);
                  navigate('/profile');
                }}
              >
                <UserIcon size={15} />
                <span>Profile & Team</span>
              </button>
              <button
                type="button"
                className="user-menu-item"
                onClick={() => {
                  setShowUserMenu(false);
                  navigate('/profile');
                }}
              >
                <Key size={15} />
                <span>API Keys & Webhooks</span>
              </button>
              <button
                type="button"
                className="user-menu-item"
                onClick={() => {
                  setShowUserMenu(false);
                  navigate('/profile');
                }}
              >
                <Settings size={15} />
                <span>Preferences</span>
              </button>
              <div className="popover-divider" />
              <button
                type="button"
                className="user-menu-item logout"
                onClick={() => {
                  setShowUserMenu(false);
                  logout();
                  navigate('/login');
                }}
              >
                <LogOut size={15} />
                <span>Sign Out</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

export default TopBar;
