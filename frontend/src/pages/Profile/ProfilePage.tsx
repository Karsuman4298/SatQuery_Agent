import React, { useState } from 'react';
import { UserIcon, Key, Settings, CreditCard, ChevronRight } from 'lucide-react';
import TopBar from '../../components/dashboard/TopBar';
import { useAuth } from '../../context/AuthContext';
import './Profile.css';

type Tab = 'profile' | 'api-keys' | 'preferences' | 'billing';

const ProfilePage: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<Tab>('profile');

  return (
    <div className="satquery-dashboard-layout">
      {/* Shared Top Navbar */}
      <TopBar />

      <main className="profile-main-container">
        <div className="profile-content-wrapper">
          
          <aside className="profile-sidebar">
            <h2 className="profile-sidebar-title">Settings</h2>
            <nav className="profile-nav-menu">
              <button 
                className={`profile-nav-item ${activeTab === 'profile' ? 'active' : ''}`}
                onClick={() => setActiveTab('profile')}
              >
                <UserIcon size={16} />
                <span>Profile & Team</span>
              </button>
              <button 
                className={`profile-nav-item ${activeTab === 'api-keys' ? 'active' : ''}`}
                onClick={() => setActiveTab('api-keys')}
              >
                <Key size={16} />
                <span>API Keys & Webhooks</span>
              </button>
              <button 
                className={`profile-nav-item ${activeTab === 'preferences' ? 'active' : ''}`}
                onClick={() => setActiveTab('preferences')}
              >
                <Settings size={16} />
                <span>Preferences</span>
              </button>
              <button 
                className={`profile-nav-item ${activeTab === 'billing' ? 'active' : ''}`}
                onClick={() => setActiveTab('billing')}
              >
                <CreditCard size={16} />
                <span>Billing</span>
              </button>
            </nav>
          </aside>

          <section className="profile-tab-content">
            {activeTab === 'profile' && (
              <div className="profile-tab-section fade-in">
                <div className="profile-section-header">
                  <h3>Personal Information</h3>
                  <p>Manage your public profile and email address.</p>
                </div>
                
                <div className="profile-card">
                  <div className="profile-avatar-row">
                    <div className="profile-avatar-large">
                      <UserIcon size={32} color="#94a3b8" />
                    </div>
                    <div className="profile-avatar-actions">
                      <button className="btn-secondary">Change Avatar</button>
                      <button className="btn-text-danger">Remove</button>
                    </div>
                  </div>

                  <div className="profile-form-group">
                    <label>Full Name</label>
                    <input type="text" defaultValue={user?.name || ''} className="profile-input" />
                  </div>

                  <div className="profile-form-group">
                    <label>Email Address</label>
                    <input type="email" defaultValue={user?.email || ''} className="profile-input" readOnly disabled />
                    <span className="input-hint">Email address cannot be changed for Demo users.</span>
                  </div>

                  <button className="btn-primary mt-4">Save Changes</button>
                </div>
              </div>
            )}

            {activeTab === 'api-keys' && (
              <div className="profile-tab-section fade-in">
                <div className="profile-section-header">
                  <h3>API Keys & Webhooks</h3>
                  <p>Manage keys for programmatic access to the SatQuery model server.</p>
                </div>
                
                <div className="profile-card empty-state-card">
                  <Key size={32} className="empty-state-icon" />
                  <h4>No API Keys Generated</h4>
                  <p>Create a secret key to access the model endpoints directly.</p>
                  <button className="btn-primary">Generate New Key</button>
                </div>
              </div>
            )}

            {activeTab === 'preferences' && (
              <div className="profile-tab-section fade-in">
                <div className="profile-section-header">
                  <h3>Preferences</h3>
                  <p>Customize your workspace layout and AI settings.</p>
                </div>
                
                <div className="profile-card">
                  <div className="pref-row">
                    <div>
                      <span className="pref-title">Default Workspace Modality</span>
                      <span className="pref-desc">The modality to auto-select if multiple exist.</span>
                    </div>
                    <select className="profile-select" defaultValue="optical">
                      <option value="optical">Optical (Default)</option>
                      <option value="sar">SAR</option>
                      <option value="msi">Multispectral</option>
                    </select>
                  </div>
                  
                  <div className="pref-row mt-4">
                    <div>
                      <span className="pref-title">Streaming AI Text</span>
                      <span className="pref-desc">Enable live token streaming in GeoChat.</span>
                    </div>
                    <div className="toggle-switch active">
                      <div className="toggle-knob"></div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'billing' && (
              <div className="profile-tab-section fade-in">
                <div className="profile-section-header">
                  <h3>Billing & Quotas</h3>
                  <p>You are currently on the Free Research Tier.</p>
                </div>
                
                <div className="profile-card">
                  <div className="billing-quota-bar">
                    <div className="quota-fill" style={{ width: '45%' }}></div>
                  </div>
                  <div className="quota-labels">
                    <span>45 / 100 queries used this month</span>
                    <span>Resets in 12 days</span>
                  </div>
                  
                  <button className="btn-upgrade mt-5">
                    Upgrade to Pro <ChevronRight size={14} />
                  </button>
                </div>
              </div>
            )}
          </section>

        </div>
      </main>
    </div>
  );
};

export default ProfilePage;
