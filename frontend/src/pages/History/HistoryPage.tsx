import React, { useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  Filter,
  ArrowUpDown,
  Plus,
  ArrowRight,
  Trash2,
  Edit2,
  Download,
  Share2,
  Calendar,
  Layers,
  Sparkles,
  LayoutGrid,
  List,
  CheckCircle2,
  Clock,
  AlertCircle,
  FileSpreadsheet,
  X,
  Check,
  CheckCircle,
  Link2,
  Info,
} from 'lucide-react';
import Sidebar from '../../components/dashboard/Sidebar';
import TopBar from '../../components/dashboard/TopBar';
import { useHistory, type HistoryEntry, type HistoryModality, type HistoryStatus } from '../../context/HistoryContext';
import earthOrbitBg from '../../assets/auth/signin_earth_orbit.jpg';
import './History.css';

type SortOption = 'newest' | 'oldest' | 'name' | 'confidence';
type ViewMode = 'grid' | 'list';

export const HistoryPage: React.FC = () => {
  const navigate = useNavigate();
  const { entries, deleteEntry, renameEntry } = useHistory();

  // Search & Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedModality, setSelectedModality] = useState<'All' | HistoryModality>('All');
  const [selectedStatus, setSelectedStatus] = useState<'All' | HistoryStatus>('All');
  const [sortBy, setSortBy] = useState<SortOption>('newest');
  const [viewMode, setViewMode] = useState<ViewMode>('grid');

  // Modal states
  const [renamingItem, setRenamingItem] = useState<{ id: string; name: string } | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [exportSuccessId, setExportSuccessId] = useState<string | null>(null);

  // Filtered and Sorted entries
  const filteredEntries = useMemo(() => {
    return entries
      .filter((entry) => {
        const matchesSearch =
          entry.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          entry.fileName.toLowerCase().includes(searchQuery.toLowerCase()) ||
          (entry.dataset && entry.dataset.toLowerCase().includes(searchQuery.toLowerCase())) ||
          entry.spectralChannel.toLowerCase().includes(searchQuery.toLowerCase()) ||
          entry.region.toLowerCase().includes(searchQuery.toLowerCase());

        const matchesModality =
          selectedModality === 'All' || entry.modality === selectedModality;

        const matchesStatus =
          selectedStatus === 'All' || entry.status === selectedStatus;

        return matchesSearch && matchesModality && matchesStatus;
      })
      .sort((a, b) => {
        if (sortBy === 'newest') {
          return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
        }
        if (sortBy === 'oldest') {
          return new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
        }
        if (sortBy === 'name') {
          return a.name.localeCompare(b.name);
        }
        if (sortBy === 'confidence') {
          return (b.confidence || 0) - (a.confidence || 0);
        }
        return 0;
      });
  }, [entries, searchQuery, selectedModality, selectedStatus, sortBy]);

  // Statistics
  const stats = useMemo(() => {
    const total = entries.length;
    const completed = entries.filter((e) => e.status === 'Completed').length;
    const processing = entries.filter((e) => e.status === 'Processing').length;
    const avgConfidence = total > 0
      ? `${(entries.reduce((acc, curr) => acc + (curr.confidence || 0), 0) / total).toFixed(1)}%`
      : '—';
    return { total, completed, processing, avgConfidence };
  }, [entries]);

  // Open Analysis in Workspace
  const handleOpenAnalysis = (entry: HistoryEntry) => {
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
  };

  // Start Rename Modal
  const openRenameModal = (entry: HistoryEntry) => {
    setRenamingItem({ id: entry.id, name: entry.name });
    setRenameValue(entry.name);
  };

  const handleSaveRename = (e: React.FormEvent) => {
    e.preventDefault();
    if (renamingItem && renameValue.trim()) {
      renameEntry(renamingItem.id, renameValue.trim());
      setRenamingItem(null);
    }
  };

  // Confirm Delete
  const handleConfirmDelete = () => {
    if (deletingId) {
      deleteEntry(deletingId);
      setDeletingId(null);
    }
  };

  // Share link
  const handleShare = (entry: HistoryEntry) => {
    const url = `${window.location.origin}/analysis/${entry.id}?title=${encodeURIComponent(entry.name)}`;
    if (navigator.clipboard) {
      navigator.clipboard.writeText(url).then(() => {
        setCopiedId(entry.id);
        setTimeout(() => setCopiedId(null), 2000);
      });
    }
  };

  // Quick Export
  const handleExport = useCallback((entry: HistoryEntry) => {
    const now = new Date();
    const dateStr = new Date(entry.createdAt).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
    const exportTimeStr = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });

    const reportHtml = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>SatQuery AI Analysis Report: ${entry.name}</title>
  <style>
    body { background: #020b12; color: #e2e8f0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 40px; margin: 0; }
    .header { border-bottom: 1px solid rgba(0, 212, 255, 0.2); padding-bottom: 20px; margin-bottom: 28px; }
    h1 { color: #fff; font-size: 24px; margin: 0 0 8px 0; }
    h1 span { color: #00ff88; }
    .meta-box { background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 20px; margin-bottom: 24px; }
    .meta-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-top: 12px; }
    .meta-item label { color: #64748b; font-size: 11px; text-transform: uppercase; display: block; margin-bottom: 4px; }
    .meta-item span { color: #00d4ff; font-weight: 600; font-size: 15px; }
    .badge { display: inline-block; padding: 4px 10px; background: rgba(0, 255, 136, 0.15); color: #00ff88; border-radius: 12px; font-size: 12px; font-weight: bold; }
    .chat-section { margin-top: 24px; background: rgba(0,0,0,0.3); border-radius: 8px; padding: 16px; }
    .msg { margin-bottom: 12px; padding: 10px 14px; border-radius: 6px; }
    .msg.ai { background: #0c2133; border-left: 3px solid #00d4ff; }
    .msg.user { background: #0c2b18; border-left: 3px solid #00ff88; }
    .footer { margin-top: 30px; font-size: 11px; color: #64748b; text-align: center; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 16px; }
  </style>
</head>
<body>
  <div class="header">
    <h1>SatQuery <span>AI</span> — Satellite Analysis Report</h1>
    <div style="color: #94a3b8; font-size: 13px;">Created: ${dateStr} · Analysis ID: ${entry.id}</div>
  </div>
  <div class="meta-box">
    <div style="font-size: 18px; font-weight: bold; color: #fff;">${entry.name}</div>
    <div class="meta-grid">
      <div class="meta-item"><label>Modality</label><span>${entry.modality}</span></div>
      <div class="meta-item"><label>Spectral Channel</label><span>${entry.spectralChannel}</span></div>
      <div class="meta-item"><label>Active Region</label><span>${entry.region}</span></div>
      <div class="meta-item"><label>Confidence</label><span style="color: #00ff88;">${entry.confidence}%</span></div>
      <div class="meta-item"><label>Status</label><span class="badge">${entry.status}</span></div>
      <div class="meta-item"><label>File Name</label><span style="color: #fff; font-size: 13px;">${entry.fileName}</span></div>
    </div>
  </div>
  ${entry.chatMessages && entry.chatMessages.length > 0 ? `
  <div class="chat-section">
    <h3 style="color: #00d4ff; margin-top: 0; font-size: 14px;">GeoChat AI Session Transcript</h3>
    ${entry.chatMessages.map(m => `<div class="msg ${m.sender}"><div style="font-size: 11px; color: #64748b; margin-bottom: 4px;">${m.sender === 'ai' ? '🤖 GeoChat AI' : '👤 Analyst'} · ${m.time}</div><div>${m.text}</div></div>`).join('')}
  </div>` : ''}
  <div class="footer">
    Exported from SatQuery AI on ${dateStr} at ${exportTimeStr}
  </div>
</body>
</html>`;

    const blob = new Blob([reportHtml], { type: 'text/html;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `SatQuery_Report_${entry.name.replace(/[^a-zA-Z0-9_-]/g, '_')}.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    setExportSuccessId(entry.id);
    setTimeout(() => setExportSuccessId(null), 2500);
  }, []);

  const formatDate = (isoStr: string) => {
    try {
      const date = new Date(isoStr);
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return 'Recently';
    }
  };

  const getModalityClass = (mod: HistoryModality) => {
    switch (mod) {
      case 'Optical': return 'modality-tag-optical';
      case 'SAR': return 'modality-tag-sar';
      case 'Multispectral': return 'modality-tag-multi';
      case 'Thermal': return 'modality-tag-thermal';
      default: return '';
    }
  };

  const getStatusBadge = (status: HistoryStatus) => {
    switch (status) {
      case 'Completed':
        return (
          <span className="history-status-badge status-completed">
            <CheckCircle2 size={12} />
            Completed
          </span>
        );
      case 'Processing':
        return (
          <span className="history-status-badge status-processing">
            <Clock size={12} className="spin-slow" />
            Processing
          </span>
        );
      case 'Failed':
        return (
          <span className="history-status-badge status-failed">
            <AlertCircle size={12} />
            Failed
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="satquery-dashboard-layout">
      {/* Sidebar navigation */}
      <Sidebar />

      <div className="satquery-dashboard-main">
        {/* Ambient Top Orbit Earth Glow */}
        <div className="satquery-dashboard-top-earth-bg" aria-hidden="true">
          <img src={earthOrbitBg} alt="" />
          <div className="satquery-dashboard-top-earth-overlay" />
        </div>

        {/* TopBar */}
        <TopBar onSearch={(q) => setSearchQuery(q)} />

        <div className="satquery-dashboard-content history-page-content">
          {/* Header Banner */}
          <div className="history-header-wrapper">
            <div className="history-header-left">
              <div className="history-header-badge">
                <Sparkles size={13} className="green-icon" />
                <span>OBSERVATION REPOSITORY</span>
              </div>
              <h1 className="history-page-title">Analysis History</h1>
              <p className="history-page-subtitle">
                Review, inspect, manage, and reopen past satellite observation sessions.
              </p>
            </div>

            <div className="history-header-actions">
              <button
                type="button"
                className="history-new-analysis-btn"
                onClick={() => navigate('/new-analysis')}
              >
                <Plus size={16} />
                <span>Start New Analysis</span>
              </button>
            </div>
          </div>

          {/* Metric Stats Cards */}
          <div className="history-stats-row">
            <div className="history-stat-box">
              <div className="history-stat-icon-wrap cyan">
                <Layers size={18} />
              </div>
              <div className="history-stat-info">
                <span className="history-stat-label">Total Analyses</span>
                <span className="history-stat-val">{stats.total}</span>
              </div>
            </div>

            <div className="history-stat-box">
              <div className="history-stat-icon-wrap green">
                <CheckCircle size={18} />
              </div>
              <div className="history-stat-info">
                <span className="history-stat-label">Completed Sessions</span>
                <span className="history-stat-val">{stats.completed}</span>
              </div>
            </div>

            <div className="history-stat-box">
              <div className="history-stat-icon-wrap amber">
                <Clock size={18} />
              </div>
              <div className="history-stat-info">
                <span className="history-stat-label">In Processing</span>
                <span className="history-stat-val">{stats.processing}</span>
              </div>
            </div>

            <div className="history-stat-box">
              <div className="history-stat-icon-wrap teal">
                <Sparkles size={18} />
              </div>
              <div className="history-stat-info">
                <span className="history-stat-label">Avg. Confidence</span>
                <span className="history-stat-val">{stats.avgConfidence}</span>
              </div>
            </div>
          </div>

          {/* Filter & Toolbar Area */}
          <div className="history-toolbar-panel">
            {/* Search Input */}
            <div className="history-search-wrap">
              <Search size={15} className="history-search-icon" />
              <input
                type="text"
                placeholder="Search by analysis name, file, channel, or region..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="history-search-input"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery('')}
                  className="history-search-clear"
                >
                  <X size={14} />
                </button>
              )}
            </div>

            {/* Modality Filter Chips */}
            <div className="history-modality-filters">
              {(['All', 'Optical', 'SAR', 'Multispectral', 'Thermal'] as const).map((mod) => (
                <button
                  key={mod}
                  type="button"
                  className={`history-filter-chip ${selectedModality === mod ? 'active' : ''}`}
                  onClick={() => setSelectedModality(mod)}
                >
                  {mod}
                </button>
              ))}
            </div>

            <div className="history-toolbar-right">
              {/* Status Filter */}
              <div className="history-select-group">
                <Filter size={13} className="select-icon" />
                <select
                  value={selectedStatus}
                  onChange={(e) => setSelectedStatus(e.target.value as 'All' | HistoryStatus)}
                  className="history-select"
                >
                  <option value="All">All Statuses</option>
                  <option value="Completed">Completed</option>
                  <option value="Processing">Processing</option>
                  <option value="Failed">Failed</option>
                </select>
              </div>

              {/* Sort Dropdown */}
              <div className="history-select-group">
                <ArrowUpDown size={13} className="select-icon" />
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as SortOption)}
                  className="history-select"
                >
                  <option value="newest">Newest First</option>
                  <option value="oldest">Oldest First</option>
                  <option value="name">Name (A-Z)</option>
                  <option value="confidence">Highest Confidence</option>
                </select>
              </div>

              {/* View Mode Toggle */}
              <div className="history-view-toggle">
                <button
                  type="button"
                  className={`view-toggle-btn ${viewMode === 'grid' ? 'active' : ''}`}
                  onClick={() => setViewMode('grid')}
                  title="Grid View"
                >
                  <LayoutGrid size={15} />
                </button>
                <button
                  type="button"
                  className={`view-toggle-btn ${viewMode === 'list' ? 'active' : ''}`}
                  onClick={() => setViewMode('list')}
                  title="List View"
                >
                  <List size={15} />
                </button>
              </div>
            </div>
          </div>

          {/* Main Content: Grid or List */}
          {filteredEntries.length === 0 ? (
            <div className="history-empty-state">
              <div className="empty-state-icon-circle">
                <FileSpreadsheet size={32} />
              </div>
              <h3 className="empty-state-title">
                {searchQuery || selectedModality !== 'All' || selectedStatus !== 'All'
                  ? 'No matching analyses found'
                  : 'No satellite analyses in your repository yet'}
              </h3>
              <p className="empty-state-desc">
                {searchQuery || selectedModality !== 'All' || selectedStatus !== 'All'
                  ? 'Try clearing your search query or loosening your filter criteria.'
                  : 'Upload your first satellite image to initiate AI-powered spectral classification and GeoChat.'}
              </p>
              {searchQuery || selectedModality !== 'All' || selectedStatus !== 'All' ? (
                <button
                  type="button"
                  className="history-empty-reset-btn"
                  onClick={() => {
                    setSearchQuery('');
                    setSelectedModality('All');
                    setSelectedStatus('All');
                  }}
                >
                  Reset All Filters
                </button>
              ) : (
                <button
                  type="button"
                  className="history-new-analysis-btn"
                  onClick={() => navigate('/new-analysis')}
                >
                  <Plus size={16} />
                  <span>Start a New Analysis</span>
                </button>
              )}
            </div>
          ) : viewMode === 'grid' ? (
            /* ── GRID VIEW ── */
            <div className="history-cards-grid">
              <AnimatePresence>
                {filteredEntries.map((entry) => (
                  <motion.div
                    key={entry.id}
                    className="history-card"
                    layout
                    initial={{ opacity: 0, y: 15 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    transition={{ duration: 0.3 }}
                  >
                    {/* Card Thumbnail */}
                    <div
                      className="history-card-thumb-wrap"
                      onClick={() => handleOpenAnalysis(entry)}
                      role="button"
                      tabIndex={0}
                      title="Click to open analysis in workspace"
                    >
                      <img
                        src={entry.imageUrl}
                        alt={entry.name}
                        className="history-card-thumb-img"
                      />
                      <div className="history-card-thumb-overlay">
                        <span className="open-hover-chip">
                          Open Analysis <ArrowRight size={13} />
                        </span>
                      </div>

                      {/* Floating Modality Pill */}
                      <span className={`history-modality-badge ${getModalityClass(entry.modality)}`}>
                        {entry.modality}
                      </span>

                      {/* Confidence Tag */}
                      <span className="history-confidence-badge">
                        {entry.confidence}% Conf.
                      </span>
                    </div>

                    {/* Card Body */}
                    <div className="history-card-body">
                      <div className="history-card-top-row">
                        <h3
                          className="history-card-title"
                          onClick={() => handleOpenAnalysis(entry)}
                          title={entry.name}
                        >
                          {entry.name}
                        </h3>
                        {getStatusBadge(entry.status)}
                      </div>

                      <p className="history-card-filename" title={entry.fileName}>
                        {entry.fileName}
                      </p>

                      {/* Metadata Chips */}
                      <div className="history-card-meta-chips">
                        <div className="meta-chip">
                          <Layers size={11} />
                          <span>{entry.spectralChannel}</span>
                        </div>
                        <div className="meta-chip">
                          <Info size={11} />
                          <span>{entry.region}</span>
                        </div>
                        {entry.dataset && (
                          <div className="meta-chip dataset-chip">
                            <span>{entry.dataset}</span>
                          </div>
                        )}
                      </div>

                      <div className="history-card-date-row">
                        <Calendar size={12} className="calendar-icon" />
                        <span>{formatDate(entry.createdAt)}</span>
                      </div>

                      {/* Card Action Footer */}
                      <div className="history-card-footer">
                        <button
                          type="button"
                          className="history-open-btn"
                          onClick={() => handleOpenAnalysis(entry)}
                        >
                          <span>Open Workspace</span>
                          <ArrowRight size={14} />
                        </button>

                        <div className="history-card-icon-actions">
                          <button
                            type="button"
                            className="card-mini-btn"
                            title="Rename analysis"
                            onClick={() => openRenameModal(entry)}
                          >
                            <Edit2 size={13} />
                          </button>
                          <button
                            type="button"
                            className={`card-mini-btn ${copiedId === entry.id ? 'active-success' : ''}`}
                            title={copiedId === entry.id ? 'Link copied!' : 'Share analysis link'}
                            onClick={() => handleShare(entry)}
                          >
                            {copiedId === entry.id ? <Check size={13} /> : <Share2 size={13} />}
                          </button>
                          <button
                            type="button"
                            className={`card-mini-btn ${exportSuccessId === entry.id ? 'active-success' : ''}`}
                            title={exportSuccessId === entry.id ? 'Downloaded!' : 'Export report HTML'}
                            onClick={() => handleExport(entry)}
                          >
                            {exportSuccessId === entry.id ? <Check size={13} /> : <Download size={13} />}
                          </button>
                          <button
                            type="button"
                            className="card-mini-btn delete-btn"
                            title="Delete from history"
                            onClick={() => setDeletingId(entry.id)}
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          ) : (
            /* ── LIST / TABLE VIEW ── */
            <div className="history-table-container">
              <table className="history-table">
                <thead>
                  <tr>
                    <th>Scene / Name</th>
                    <th>Modality</th>
                    <th>Channel &amp; Region</th>
                    <th>Status</th>
                    <th>Confidence</th>
                    <th>Date Created</th>
                    <th style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredEntries.map((entry) => (
                    <tr key={entry.id} className="history-table-row">
                      <td className="table-scene-cell">
                        <div
                          className="table-thumb-wrap"
                          onClick={() => handleOpenAnalysis(entry)}
                        >
                          <img src={entry.imageUrl} alt={entry.name} />
                        </div>
                        <div className="table-name-info">
                          <span
                            className="table-analysis-name"
                            onClick={() => handleOpenAnalysis(entry)}
                          >
                            {entry.name}
                          </span>
                          <span className="table-file-name">{entry.fileName}</span>
                        </div>
                      </td>
                      <td>
                        <span className={`history-modality-badge ${getModalityClass(entry.modality)}`}>
                          {entry.modality}
                        </span>
                      </td>
                      <td>
                        <div className="table-channel-info">
                          <span className="channel-primary">{entry.spectralChannel}</span>
                          <span className="channel-region">{entry.region}</span>
                        </div>
                      </td>
                      <td>{getStatusBadge(entry.status)}</td>
                      <td>
                        <span className="table-conf-val">{entry.confidence}%</span>
                      </td>
                      <td>
                        <span className="table-date-val">{formatDate(entry.createdAt)}</span>
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <div className="table-actions-cell">
                          <button
                            type="button"
                            className="table-open-btn"
                            onClick={() => handleOpenAnalysis(entry)}
                          >
                            Open
                          </button>
                          <button
                            type="button"
                            className="table-icon-btn"
                            title="Rename"
                            onClick={() => openRenameModal(entry)}
                          >
                            <Edit2 size={13} />
                          </button>
                          <button
                            type="button"
                            className="table-icon-btn"
                            title="Share link"
                            onClick={() => handleShare(entry)}
                          >
                            {copiedId === entry.id ? <Check size={13} color="#00ff88" /> : <Link2 size={13} />}
                          </button>
                          <button
                            type="button"
                            className="table-icon-btn"
                            title="Export HTML report"
                            onClick={() => handleExport(entry)}
                          >
                            {exportSuccessId === entry.id ? <Check size={13} color="#00ff88" /> : <Download size={13} />}
                          </button>
                          <button
                            type="button"
                            className="table-icon-btn delete-btn"
                            title="Delete"
                            onClick={() => setDeletingId(entry.id)}
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* ── RENAME MODAL ── */}
      {renamingItem && (
        <div className="history-modal-backdrop" onClick={() => setRenamingItem(null)}>
          <div
            className="history-modal-box"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-label="Rename Analysis"
          >
            <div className="history-modal-header">
              <div className="history-modal-title">
                <Edit2 size={16} className="cyan-icon" />
                Rename Analysis
              </div>
              <button
                type="button"
                className="history-modal-close"
                onClick={() => setRenamingItem(null)}
              >
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handleSaveRename}>
              <div className="history-modal-body">
                <label className="history-modal-label">Analysis Display Title</label>
                <input
                  type="text"
                  value={renameValue}
                  onChange={(e) => setRenameValue(e.target.value)}
                  className="history-modal-input"
                  autoFocus
                  placeholder="Enter a descriptive title..."
                />
              </div>

              <div className="history-modal-footer">
                <button
                  type="button"
                  className="history-modal-cancel-btn"
                  onClick={() => setRenamingItem(null)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="history-modal-save-btn"
                  disabled={!renameValue.trim()}
                >
                  Save Title
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── DELETE CONFIRMATION MODAL ── */}
      {deletingId && (
        <div className="history-modal-backdrop" onClick={() => setDeletingId(null)}>
          <div
            className="history-modal-box"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-label="Confirm Delete"
          >
            <div className="history-modal-header">
              <div className="history-modal-title delete-title">
                <Trash2 size={16} color="#ff4d4f" />
                Delete Analysis Session
              </div>
              <button
                type="button"
                className="history-modal-close"
                onClick={() => setDeletingId(null)}
              >
                <X size={16} />
              </button>
            </div>

            <div className="history-modal-body">
              <p className="delete-confirm-text">
                Are you sure you want to remove this analysis from your history? This action cannot be undone.
              </p>
            </div>

            <div className="history-modal-footer">
              <button
                type="button"
                className="history-modal-cancel-btn"
                onClick={() => setDeletingId(null)}
              >
                Keep Session
              </button>
              <button
                type="button"
                className="history-modal-delete-btn"
                onClick={handleConfirmDelete}
              >
                Delete Analysis
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default HistoryPage;
