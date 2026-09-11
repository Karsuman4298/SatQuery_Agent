import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  UploadCloud,
  ArrowUp,
  Image as ImageIcon,
  Cpu,
  Target,
  ArrowRight,
} from 'lucide-react';
import Sidebar from '../../components/dashboard/Sidebar';
import TopBar from '../../components/dashboard/TopBar';
import { useAuth } from '../../context/AuthContext';
import { useHistory, type HistoryEntry } from '../../context/HistoryContext';
import satelliteHeroImg from '../../assets/auth/satellite_model.jpg';
import deltaTerrainBg from '../../assets/auth/signup_satellite_delta.jpg';
import earthOrbitBg from '../../assets/auth/signin_earth_orbit.jpg';
import './Dashboard.css';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { entries } = useHistory();
  const [searchQuery, setSearchQuery] = useState('');

  const handleStartAnalysis = (entry?: HistoryEntry) => {
    if (entry) {
      // Opening a specific recent analysis — go directly to workspace
      navigate(`/analysis/${entry.id}`, {
        state: {
          imageUrl: entry.imageUrl,
          title: entry.name,
          historyId: entry.id,
          initialModality: entry.modality.toLowerCase(),
          initialLayer: entry.spectralChannel,
          initialRegion: entry.region,
          initialMessages: entry.chatMessages,
          fileInfo: {
            name: entry.fileName,
            size: entry.fileSize || '—',
            type: entry.fileType || 'Image',
            dimensions: entry.fileDimensions || '—',
          },
        },
      });
    } else {
      // No image selected — go to upload page
      navigate('/new-analysis');
    }
  };

  const filteredEntries = entries.filter(
    (item) =>
      item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.fileName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.spectralChannel.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.modality.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const imagesAnalyzed = entries.length;
  const totalAIQueries = entries.reduce(
    (acc, e) => acc + (e.chatMessages ? e.chatMessages.filter((m) => m.sender === 'user').length : 0),
    0
  );
  const avgConfidence =
    entries.length > 0
      ? `${(entries.reduce((acc, e) => acc + (e.confidence || 0), 0) / entries.length).toFixed(1)}%`
      : '—';

  return (
    <div className="satquery-dashboard-layout">
      {/* Left Navigation Sidebar */}
      <Sidebar />

      {/* Main Dashboard Area */}
      <div className="satquery-dashboard-main">
        {/* Subtle Top-Right Earth Orbit Glow Background */}
        <div className="satquery-dashboard-top-earth-bg" aria-hidden="true">
          <img src={earthOrbitBg} alt="" />
          <div className="satquery-dashboard-top-earth-overlay" />
        </div>

        <TopBar onSearch={(q) => setSearchQuery(q)} />

        <div className="satquery-dashboard-content">
          {/* Welcome Section */}
          <section className="satquery-welcome-section">
            <div className="satquery-welcome-left">
              <h1 className="satquery-welcome-title">
                Good morning, <span className="green">{user?.name ? user.name.split(' ')[0] : 'Explorer'}.</span>
              </h1>
              <p className="satquery-welcome-sub">
                Turn satellite imagery into actionable insights.
              </p>
            </div>

            <div className="satquery-welcome-tagline">
              <span>EXPLORE</span>
              <span>ANALYZE</span>
              <span>SOLVE</span>
              <span className="satquery-tagline-dash" />
            </div>
          </section>

          {/* Start a New Analysis Hero Card */}
          <motion.section
            className="satquery-analysis-card"
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <div className="satquery-card-header">
              <div className="satquery-card-icon-badge">
                <ArrowUp size={18} />
              </div>
              <div className="satquery-card-header-text">
                <h2 className="satquery-analysis-card-title">Start a New Analysis</h2>
                <p className="satquery-analysis-card-sub">
                  Upload satellite imagery and ask questions using AI.
                </p>
              </div>
            </div>

            <div className="satquery-analysis-card-body">
              {/* Upload Zone — routes to /new-analysis for full upload flow */}
              <div
                className="satquery-upload-zone"
                onClick={() => navigate('/new-analysis')}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') navigate('/new-analysis'); }}
                aria-label="Start a new analysis"
              >
                <UploadCloud size={36} className="satquery-upload-icon" />
                <span className="satquery-upload-main-text">
                  Drag &amp; drop your satellite image here
                </span>
                <span className="satquery-upload-or">or</span>
                <button
                  type="button"
                  className="satquery-browse-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate('/new-analysis');
                  }}
                >
                  Browse Files
                </button>
                <span className="satquery-upload-formats">
                  Supported formats: JPG &bull; PNG &bull; TIFF &bull; GeoTIFF
                </span>
              </div>

              {/* Right Side Spacecraft Visual */}
              <div className="satquery-card-visual-right">
                <img
                  src={deltaTerrainBg}
                  alt="Satellite Topography"
                  className="satquery-card-visual-bg"
                />
                <img
                  src={satelliteHeroImg}
                  alt="Earth Observation Satellite"
                  style={{
                    position: 'absolute',
                    top: '10%',
                    right: '12%',
                    width: '180px',
                    height: '180px',
                    objectFit: 'contain',
                    mixBlendMode: 'screen',
                    filter: 'drop-shadow(0 0 15px rgba(0,212,255,0.3))',
                    transform: 'rotate(-8deg)',
                  }}
                />
                <div className="satquery-card-visual-overlay" />
                <div className="satquery-card-script-text">
                  From Space<br />to Solutions
                </div>
                <div className="satquery-card-script-dash" />
              </div>
            </div>
          </motion.section>

          {/* Three Metric Statistics Grid — Dynamic from user history */}
          <section className="satquery-stats-grid">
            {/* Stat 1 */}
            <div className="satquery-stat-card">
              <div className="satquery-stat-left">
                <div className="satquery-stat-icon-wrapper green">
                  <ImageIcon size={20} />
                </div>
                <div className="satquery-stat-data">
                  <span className="satquery-stat-label">Images Analyzed</span>
                  <span className="satquery-stat-value">{imagesAnalyzed}</span>
                  <span className="satquery-stat-trend">
                    {imagesAnalyzed > 0 ? `${imagesAnalyzed} active session${imagesAnalyzed === 1 ? '' : 's'}` : '0 recorded'}
                  </span>
                </div>
              </div>
            </div>

            {/* Stat 2 */}
            <div className="satquery-stat-card">
              <div className="satquery-stat-left">
                <div className="satquery-stat-icon-wrapper blue">
                  <Cpu size={20} />
                </div>
                <div className="satquery-stat-data">
                  <span className="satquery-stat-label">AI Queries</span>
                  <span className="satquery-stat-value">{totalAIQueries}</span>
                  <span className="satquery-stat-trend">
                    {totalAIQueries > 0 ? `${totalAIQueries} prompt${totalAIQueries === 1 ? '' : 's'} asked` : '0 prompts'}
                  </span>
                </div>
              </div>
            </div>

            {/* Stat 3 */}
            <div className="satquery-stat-card">
              <div className="satquery-stat-left">
                <div className="satquery-stat-icon-wrapper teal">
                  <Target size={20} />
                </div>
                <div className="satquery-stat-data">
                  <span className="satquery-stat-label">Avg. Confidence</span>
                  <span className="satquery-stat-value">{avgConfidence}</span>
                  <span className="satquery-stat-trend">
                    {entries.length > 0 ? 'Calculated from analyses' : 'Pending analyses'}
                  </span>
                </div>
              </div>
            </div>
          </section>

          {/* Recent Analyses Section */}
          <section className="satquery-recent-section">
            <div className="satquery-recent-header">
              <h3 className="satquery-recent-title">Recent Analyses</h3>
              <button
                type="button"
                className="satquery-recent-view-all"
                onClick={() => navigate('/history')}
              >
                <span>View All History</span>
                <ArrowRight size={14} />
              </button>
            </div>

            <div className="satquery-recent-list">
              {filteredEntries.length > 0 ? (
                filteredEntries.slice(0, 5).map((item) => (
                  <div key={item.id} className="satquery-recent-row">
                    <div className="satquery-recent-left">
                      <div className="satquery-recent-thumb" onClick={() => handleStartAnalysis(item)} style={{ cursor: 'pointer' }}>
                        <img src={item.imageUrl} alt={item.name} />
                      </div>
                      <div className="satquery-recent-info">
                        <span className="satquery-recent-item-title" onClick={() => handleStartAnalysis(item)} style={{ cursor: 'pointer' }}>
                          {item.name}
                        </span>
                        <span className="satquery-recent-item-meta">
                          {item.modality} • {item.spectralChannel} • {item.region}
                        </span>
                      </div>
                    </div>
                    <div className="satquery-recent-right">
                      <span className={`satquery-status-badge ${item.status.toLowerCase()}`}>
                        {item.status}
                      </span>
                      <button
                        type="button"
                        className="satquery-view-analysis-btn"
                        onClick={() => handleStartAnalysis(item)}
                      >
                        <span>View Analysis</span>
                        <ArrowRight size={13} />
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <div className="dashboard-empty-analyses">
                  <div className="dashboard-empty-icon">
                    <UploadCloud size={24} />
                  </div>
                  <h4 className="dashboard-empty-title">
                    {searchQuery ? `No analyses matching "${searchQuery}"` : 'No analyses yet'}
                  </h4>
                  <p className="dashboard-empty-sub">
                    {searchQuery
                      ? 'Try clearing your search query to see other sessions.'
                      : 'Upload a satellite image to start your first analysis.'}
                  </p>
                  <button
                    type="button"
                    className="dashboard-empty-cta"
                    onClick={() => navigate('/new-analysis')}
                  >
                    <span>Start New Analysis</span>
                    <ArrowRight size={14} />
                  </button>
                </div>
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
