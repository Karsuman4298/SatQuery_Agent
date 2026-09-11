import React, { useState, useMemo, useCallback, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FileText,
  Search,
  Filter,
  Calendar,
  Download,
  Share2,
  Trash2,
  Eye,
  Plus,
  ArrowRight,
  X,
  Check,
  Clock,
  CheckCircle2,
  Sparkles,
  Link2,
  LayoutGrid,
  List,
  Layers,
  Info,
  Loader2,
  FileCheck,
  AlertCircle,
  FolderOpen,
} from 'lucide-react';
import Sidebar from '../../components/dashboard/Sidebar';
import TopBar from '../../components/dashboard/TopBar';
import { useReports, type ReportEntry, type ReportStatus, type ReportType } from '../../context/ReportsContext';
import { useHistory, type HistoryEntry } from '../../context/HistoryContext';
import { downloadReportHtmlFile } from '../../utils/reportGenerator';
import earthOrbitBg from '../../assets/auth/signin_earth_orbit.jpg';
import './Reports.css';

type DateFilterOption = 'all' | 'today' | 'week' | 'month';
type ViewMode = 'list' | 'grid';

export const ReportsPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { reports, generateReportFromAnalysis, deleteReport, markAsShared } = useReports();
  const { entries: historyEntries } = useHistory();

  // Search & Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'All' | ReportStatus>('All');
  const [typeFilter, setTypeFilter] = useState<'All' | ReportType>('All');
  const [dateFilter, setDateFilter] = useState<DateFilterOption>('all');
  const [viewMode, setViewMode] = useState<ViewMode>('list');

  // Modals & Active items
  const [selectedReport, setSelectedReport] = useState<ReportEntry | null>(null);
  const [showGenerateModal, setShowGenerateModal] = useState(false);
  const [selectedAnalysisToGenerate, setSelectedAnalysisToGenerate] = useState<HistoryEntry | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [deletingReport, setDeletingReport] = useState<ReportEntry | null>(null);
  const [shareReportItem, setShareReportItem] = useState<ReportEntry | null>(null);
  const [shareCopied, setShareCopied] = useState(false);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  // Auto-open report if ?view=<id> is in URL
  useEffect(() => {
    const viewId = searchParams.get('view');
    if (viewId && reports.length > 0) {
      const matched = reports.find((r) => r.id === viewId);
      if (matched) {
        setSelectedReport(matched);
      }
    }
  }, [searchParams, reports]);

  // Statistics calculation from real user data
  const stats = useMemo(() => {
    const total = reports.length;
    const now = new Date();
    const currentYear = now.getFullYear();
    const currentMonth = now.getMonth();

    const thisMonthCount = reports.filter((r) => {
      try {
        const d = new Date(r.createdAt);
        return d.getFullYear() === currentYear && d.getMonth() === currentMonth;
      } catch {
        return false;
      }
    }).length;

    const sharedCount = reports.filter((r) => r.isShared).length;

    let latestStr = '—';
    if (total > 0) {
      const sorted = [...reports].sort(
        (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
      );
      try {
        const latestDate = new Date(sorted[0].createdAt);
        latestStr = latestDate.toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric',
        });
      } catch {
        latestStr = 'Recently';
      }
    }

    return {
      total,
      thisMonthCount,
      sharedCount,
      latestStr,
    };
  }, [reports]);

  // Filtered reports
  const filteredReports = useMemo(() => {
    const now = Date.now();
    return reports.filter((report) => {
      // Text search
      const q = searchQuery.toLowerCase();
      const matchesSearch =
        report.title.toLowerCase().includes(q) ||
        report.analysisName.toLowerCase().includes(q) ||
        report.fileName.toLowerCase().includes(q) ||
        (report.dataset && report.dataset.toLowerCase().includes(q)) ||
        report.modality.toLowerCase().includes(q) ||
        report.region.toLowerCase().includes(q);

      // Status
      const matchesStatus = statusFilter === 'All' || report.status === statusFilter;

      // Type
      const matchesType = typeFilter === 'All' || report.reportType === typeFilter;

      // Date filter
      let matchesDate = true;
      if (dateFilter !== 'all') {
        const reportTime = new Date(report.createdAt).getTime();
        const diffMs = now - reportTime;
        if (dateFilter === 'today') {
          matchesDate = diffMs <= 24 * 3600 * 1000;
        } else if (dateFilter === 'week') {
          matchesDate = diffMs <= 7 * 24 * 3600 * 1000;
        } else if (dateFilter === 'month') {
          matchesDate = diffMs <= 30 * 24 * 3600 * 1000;
        }
      }

      return matchesSearch && matchesStatus && matchesType && matchesDate;
    });
  }, [reports, searchQuery, statusFilter, typeFilter, dateFilter]);

  // Handle generating a report from an analysis
  const handleConfirmGenerate = () => {
    if (!selectedAnalysisToGenerate) return;
    setIsGenerating(true);
    setTimeout(() => {
      const newReportId = generateReportFromAnalysis(
        selectedAnalysisToGenerate,
        'Analysis Report'
      );
      setIsGenerating(false);
      setShowGenerateModal(false);
      setSelectedAnalysisToGenerate(null);

      // Open the newly generated report in viewer
      const created = reports.find((r) => r.id === newReportId);
      if (created) {
        setSelectedReport(created);
      }
    }, 600);
  };

  // Handle Download HTML
  const handleDownloadReport = useCallback((report: ReportEntry) => {
    setDownloadingId(report.id);
    try {
      downloadReportHtmlFile(report);
      setTimeout(() => setDownloadingId(null), 1500);
    } catch {
      setDownloadingId(null);
    }
  }, []);

  // Handle Share link copy
  const handleCopyShareLink = useCallback((report: ReportEntry) => {
    markAsShared(report.id);
    const shareUrl = `${window.location.origin}/reports?view=${report.id}`;
    if (navigator.clipboard) {
      navigator.clipboard.writeText(shareUrl).then(() => {
        setShareCopied(true);
        setTimeout(() => setShareCopied(false), 2000);
      });
    }
  }, [markAsShared]);

  // Native device share if supported
  const handleNativeShare = useCallback((report: ReportEntry) => {
    markAsShared(report.id);
    const shareUrl = `${window.location.origin}/reports?view=${report.id}`;
    if (navigator.share) {
      navigator
        .share({
          title: `SatQuery AI Report — ${report.title}`,
          text: `Satellite observation report for ${report.analysisName} (${report.modality})`,
          url: shareUrl,
        })
        .catch(() => {});
    }
  }, [markAsShared]);

  // Handle Delete confirmation
  const handleConfirmDelete = () => {
    if (deletingReport) {
      deleteReport(deletingReport.id);
      if (selectedReport?.id === deletingReport.id) {
        setSelectedReport(null);
      }
      setDeletingReport(null);
    }
  };

  const formatDate = (isoStr: string) => {
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString('en-US', {
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

  return (
    <div className="satquery-dashboard-layout">
      {/* Navigation Sidebar */}
      <Sidebar />

      <div className="satquery-dashboard-main">
        {/* Subtle Ambient Earth Orbit Glow */}
        <div className="satquery-dashboard-top-earth-bg" aria-hidden="true">
          <img src={earthOrbitBg} alt="" />
          <div className="satquery-dashboard-top-earth-overlay" />
        </div>

        <TopBar onSearch={(q) => setSearchQuery(q)} />

        <div className="satquery-dashboard-content reports-page-content">
          {/* Header Banner */}
          <div className="reports-header-wrapper">
            <div className="reports-header-left">
              <div className="reports-header-badge">
                <FileCheck size={13} className="green-icon" />
                <span>VERIFIED INTELLIGENCE</span>
              </div>
              <h1 className="reports-page-title">Reports</h1>
              <p className="reports-page-subtitle">
                View, manage, and export your satellite analysis reports.
              </p>
            </div>

            <div className="reports-header-actions">
              <button
                type="button"
                className="reports-generate-btn"
                onClick={() => setShowGenerateModal(true)}
              >
                <Plus size={16} />
                <span>Generate Report</span>
              </button>
            </div>
          </div>

          {/* Compact Statistics Grid */}
          <div className="reports-stats-row">
            <div className="reports-stat-box">
              <div className="reports-stat-icon cyan">
                <FileText size={18} />
              </div>
              <div className="reports-stat-info">
                <span className="reports-stat-label">Total Reports</span>
                <span className="reports-stat-val">{stats.total}</span>
              </div>
            </div>

            <div className="reports-stat-box">
              <div className="reports-stat-icon green">
                <Calendar size={18} />
              </div>
              <div className="reports-stat-info">
                <span className="reports-stat-label">Generated This Month</span>
                <span className="reports-stat-val">{stats.thisMonthCount}</span>
              </div>
            </div>

            <div className="reports-stat-box">
              <div className="reports-stat-icon blue">
                <Share2 size={18} />
              </div>
              <div className="reports-stat-info">
                <span className="reports-stat-label">Shared Reports</span>
                <span className="reports-stat-val">{stats.sharedCount}</span>
              </div>
            </div>

            <div className="reports-stat-box">
              <div className="reports-stat-icon teal">
                <Sparkles size={18} />
              </div>
              <div className="reports-stat-info">
                <span className="reports-stat-label">Latest Report</span>
                <span className="reports-stat-val">{stats.latestStr}</span>
              </div>
            </div>
          </div>

          {/* Search and Filters Toolbar */}
          <div className="reports-toolbar-panel">
            <div className="reports-search-wrap">
              <Search size={15} className="reports-search-icon" />
              <input
                type="text"
                placeholder="Search reports by name, file, dataset, or region..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="reports-search-input"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery('')}
                  className="reports-search-clear"
                >
                  <X size={14} />
                </button>
              )}
            </div>

            <div className="reports-filters-group">
              {/* Status Filter */}
              <div className="reports-select-wrap">
                <Filter size={13} className="select-icon" />
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value as 'All' | ReportStatus)}
                  className="reports-select"
                >
                  <option value="All">All Statuses</option>
                  <option value="Ready">Ready</option>
                  <option value="Generating">Generating</option>
                  <option value="Failed">Failed</option>
                </select>
              </div>

              {/* Type Filter */}
              <div className="reports-select-wrap">
                <FileText size={13} className="select-icon" />
                <select
                  value={typeFilter}
                  onChange={(e) => setTypeFilter(e.target.value as 'All' | ReportType)}
                  className="reports-select"
                >
                  <option value="All">All Types</option>
                  <option value="Analysis Report">Analysis Report</option>
                  <option value="Exported Report">Exported Report</option>
                </select>
              </div>

              {/* Date Filter */}
              <div className="reports-select-wrap">
                <Calendar size={13} className="select-icon" />
                <select
                  value={dateFilter}
                  onChange={(e) => setDateFilter(e.target.value as DateFilterOption)}
                  className="reports-select"
                >
                  <option value="all">All Time</option>
                  <option value="today">Today</option>
                  <option value="week">This Week</option>
                  <option value="month">This Month</option>
                </select>
              </div>

              {/* View Mode Toggle */}
              <div className="reports-view-toggle">
                <button
                  type="button"
                  className={`view-toggle-btn ${viewMode === 'list' ? 'active' : ''}`}
                  onClick={() => setViewMode('list')}
                  title="List View"
                >
                  <List size={15} />
                </button>
                <button
                  type="button"
                  className={`view-toggle-btn ${viewMode === 'grid' ? 'active' : ''}`}
                  onClick={() => setViewMode('grid')}
                  title="Grid View"
                >
                  <LayoutGrid size={15} />
                </button>
              </div>

              {(searchQuery || statusFilter !== 'All' || typeFilter !== 'All' || dateFilter !== 'all') && (
                <button
                  type="button"
                  className="reports-clear-filters-btn"
                  onClick={() => {
                    setSearchQuery('');
                    setStatusFilter('All');
                    setTypeFilter('All');
                    setDateFilter('all');
                  }}
                >
                  Clear Filters
                </button>
              )}
            </div>
          </div>

          {/* Report List Content */}
          {filteredReports.length === 0 ? (
            /* Empty State */
            <div className="reports-empty-state">
              <div className="reports-empty-icon-circle">
                <FileText size={32} />
              </div>
              <h3 className="reports-empty-title">
                {searchQuery || statusFilter !== 'All' || typeFilter !== 'All' || dateFilter !== 'all'
                  ? 'No matching reports found'
                  : 'No reports yet'}
              </h3>
              <p className="reports-empty-desc">
                {searchQuery || statusFilter !== 'All' || typeFilter !== 'All' || dateFilter !== 'all'
                  ? 'Try clearing your search query or filter criteria to see other reports.'
                  : 'Generate a report from your completed satellite analyses.'}
              </p>
              {searchQuery || statusFilter !== 'All' || typeFilter !== 'All' || dateFilter !== 'all' ? (
                <button
                  type="button"
                  className="reports-empty-btn-secondary"
                  onClick={() => {
                    setSearchQuery('');
                    setStatusFilter('All');
                    setTypeFilter('All');
                    setDateFilter('all');
                  }}
                >
                  Reset Filters
                </button>
              ) : historyEntries.length > 0 ? (
                <button
                  type="button"
                  className="reports-generate-btn"
                  onClick={() => setShowGenerateModal(true)}
                >
                  <Plus size={16} />
                  <span>Generate Your First Report &rarr;</span>
                </button>
              ) : (
                <button
                  type="button"
                  className="reports-generate-btn"
                  onClick={() => navigate('/new-analysis')}
                >
                  <Plus size={16} />
                  <span>Start New Analysis &rarr;</span>
                </button>
              )}
            </div>
          ) : viewMode === 'list' ? (
            /* ── Table / List View ── */
            <div className="reports-table-container">
              <table className="reports-table">
                <thead>
                  <tr>
                    <th>Report &amp; Analysis</th>
                    <th>Modality</th>
                    <th>Generated Date</th>
                    <th>Status</th>
                    <th>Confidence</th>
                    <th style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredReports.map((report) => (
                    <tr key={report.id} className="reports-table-row">
                      <td className="reports-scene-cell">
                        <div
                          className="reports-thumb-wrap"
                          onClick={() => setSelectedReport(report)}
                          title="Open report preview"
                        >
                          <img src={report.imageUrl} alt={report.title} />
                        </div>
                        <div className="reports-name-info">
                          <span
                            className="reports-title-text"
                            onClick={() => setSelectedReport(report)}
                          >
                            {report.title}
                          </span>
                          <span className="reports-analysis-sub">
                            Analysis: {report.analysisName}
                          </span>
                        </div>
                      </td>
                      <td>
                        <div className="reports-modality-pill">
                          <span className="mod-name">{report.modality}</span>
                          <span className="mod-channel">{report.spectralChannel.split(' ')[0]}</span>
                        </div>
                      </td>
                      <td>
                        <span className="reports-date-text">{formatDate(report.createdAt)}</span>
                      </td>
                      <td>
                        <span className={`reports-status-badge status-${report.status.toLowerCase()}`}>
                          {report.status === 'Ready' && <CheckCircle2 size={11} />}
                          {report.status === 'Generating' && <Loader2 size={11} className="spin-icon" />}
                          {report.status === 'Failed' && <AlertCircle size={11} />}
                          {report.status}
                        </span>
                      </td>
                      <td>
                        <span className="reports-confidence-val">
                          {report.confidence ? `${report.confidence}%` : '—'}
                        </span>
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <div className="reports-actions-cell">
                          <button
                            type="button"
                            className="reports-action-open-btn"
                            onClick={() => setSelectedReport(report)}
                            title="Open report"
                          >
                            <Eye size={13} />
                            <span>Open</span>
                          </button>
                          <button
                            type="button"
                            className={`reports-icon-btn ${downloadingId === report.id ? 'active-success' : ''}`}
                            onClick={() => handleDownloadReport(report)}
                            title="Download HTML Report"
                          >
                            {downloadingId === report.id ? <Check size={13} /> : <Download size={13} />}
                          </button>
                          <button
                            type="button"
                            className={`reports-icon-btn ${report.isShared ? 'shared-active' : ''}`}
                            onClick={() => setShareReportItem(report)}
                            title="Share Report"
                          >
                            <Share2 size={13} />
                          </button>
                          <button
                            type="button"
                            className="reports-icon-btn delete-btn"
                            onClick={() => setDeletingReport(report)}
                            title="Delete Report"
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
          ) : (
            /* ── Grid Cards View ── */
            <div className="reports-grid">
              <AnimatePresence>
                {filteredReports.map((report) => (
                  <motion.div
                    key={report.id}
                    className="reports-card"
                    layout
                    initial={{ opacity: 0, y: 15 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    transition={{ duration: 0.25 }}
                  >
                    <div
                      className="reports-card-thumb-wrap"
                      onClick={() => setSelectedReport(report)}
                    >
                      <img src={report.imageUrl} alt={report.title} />
                      <div className="reports-card-overlay">
                        <span className="open-report-chip">
                          <Eye size={12} /> View Report
                        </span>
                      </div>
                      <span className="reports-card-modality-badge">{report.modality}</span>
                      <span className={`reports-status-badge status-${report.status.toLowerCase()}`}>
                        {report.status}
                      </span>
                    </div>

                    <div className="reports-card-body">
                      <h3
                        className="reports-card-title"
                        onClick={() => setSelectedReport(report)}
                        title={report.title}
                      >
                        {report.title}
                      </h3>
                      <p className="reports-card-analysis-sub">
                        Analysis: {report.analysisName}
                      </p>

                      <div className="reports-card-meta-chips">
                        <span className="meta-chip">
                          <Layers size={10} /> {report.spectralChannel.split(' ')[0]}
                        </span>
                        <span className="meta-chip">
                          <Info size={10} /> {report.region}
                        </span>
                        {report.confidence && (
                          <span className="meta-chip green">
                            {report.confidence}% Conf.
                          </span>
                        )}
                      </div>

                      <div className="reports-card-date">
                        <Clock size={11} />
                        <span>{formatDate(report.createdAt)}</span>
                      </div>

                      <div className="reports-card-footer">
                        <button
                          type="button"
                          className="reports-card-open-btn"
                          onClick={() => setSelectedReport(report)}
                        >
                          <span>Open</span>
                          <ArrowRight size={13} />
                        </button>

                        <div className="reports-card-icon-actions">
                          <button
                            type="button"
                            className="card-mini-btn"
                            onClick={() => handleDownloadReport(report)}
                            title="Download HTML Report"
                          >
                            <Download size={13} />
                          </button>
                          <button
                            type="button"
                            className={`card-mini-btn ${report.isShared ? 'shared-active' : ''}`}
                            onClick={() => setShareReportItem(report)}
                            title="Share Report"
                          >
                            <Share2 size={13} />
                          </button>
                          <button
                            type="button"
                            className="card-mini-btn delete-btn"
                            onClick={() => setDeletingReport(report)}
                            title="Delete Report"
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
          )}
        </div>
      </div>

      {/* ── GENERATE REPORT MODAL ── */}
      {showGenerateModal && (
        <div className="reports-modal-backdrop" onClick={() => setShowGenerateModal(false)}>
          <div
            className="reports-modal-box generate-modal-box"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-label="Generate Report"
          >
            <div className="reports-modal-header">
              <div className="reports-modal-title">
                <Plus size={16} className="cyan-icon" />
                Generate New Report
              </div>
              <button
                type="button"
                className="reports-modal-close"
                onClick={() => setShowGenerateModal(false)}
              >
                <X size={16} />
              </button>
            </div>

            <div className="reports-modal-body">
              <p className="modal-description-text">
                Select a completed satellite analysis from your repository to compile a formal report.
              </p>

              {historyEntries.length === 0 ? (
                <div className="modal-no-analyses-box">
                  <FolderOpen size={28} className="cyan-icon" />
                  <p>No completed analyses found.</p>
                  <span>You must analyze a satellite image before generating a report.</span>
                  <button
                    type="button"
                    className="reports-modal-cta-btn"
                    onClick={() => {
                      setShowGenerateModal(false);
                      navigate('/new-analysis');
                    }}
                  >
                    Start an Analysis &rarr;
                  </button>
                </div>
              ) : (
                <div className="modal-analyses-list">
                  {historyEntries.map((analysis) => {
                    const isSelected = selectedAnalysisToGenerate?.id === analysis.id;
                    return (
                      <div
                        key={analysis.id}
                        className={`modal-analysis-item ${isSelected ? 'selected' : ''}`}
                        onClick={() => setSelectedAnalysisToGenerate(analysis)}
                      >
                        <div className="modal-analysis-thumb">
                          <img src={analysis.imageUrl} alt={analysis.name} />
                        </div>
                        <div className="modal-analysis-info">
                          <span className="modal-analysis-name">{analysis.name}</span>
                          <span className="modal-analysis-meta">
                            {analysis.modality} &bull; {analysis.spectralChannel} &bull; {analysis.region}
                          </span>
                        </div>
                        <div className="modal-analysis-radio">
                          {isSelected && <Check size={13} color="#00ff88" />}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {historyEntries.length > 0 && (
              <div className="reports-modal-footer">
                <button
                  type="button"
                  className="reports-modal-cancel-btn"
                  onClick={() => setShowGenerateModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="reports-modal-save-btn"
                  disabled={!selectedAnalysisToGenerate || isGenerating}
                  onClick={handleConfirmGenerate}
                >
                  {isGenerating ? (
                    <>
                      <Loader2 size={14} className="spin-icon" />
                      <span>Compiling Report…</span>
                    </>
                  ) : (
                    <span>Generate Report</span>
                  )}
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── REPORT PREVIEW VIEWER MODAL ── */}
      {selectedReport && (
        <div className="reports-modal-backdrop" onClick={() => setSelectedReport(null)}>
          <div
            className="reports-viewer-modal-box"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-label="Report Preview"
          >
            {/* Viewer Header */}
            <div className="reports-viewer-header">
              <div className="viewer-header-left">
                <div className="viewer-badge">
                  <CheckCircle2 size={12} />
                  <span>Verified Report</span>
                </div>
                <h2 className="viewer-title">{selectedReport.title}</h2>
                <div className="viewer-meta-row">
                  <span>Report ID: <strong className="cyan-text">{selectedReport.id}</strong></span>
                  <span>&bull;</span>
                  <span>Generated: {formatDate(selectedReport.createdAt)}</span>
                </div>
              </div>

              <div className="viewer-header-actions">
                <button
                  type="button"
                  className="viewer-action-btn"
                  onClick={() => handleDownloadReport(selectedReport)}
                  title="Download HTML report file"
                >
                  <Download size={14} />
                  <span>Download HTML</span>
                </button>
                <button
                  type="button"
                  className="viewer-action-btn"
                  onClick={() => setShareReportItem(selectedReport)}
                  title="Share report"
                >
                  <Share2 size={14} />
                  <span>Share</span>
                </button>
                <button
                  type="button"
                  className="reports-modal-close"
                  onClick={() => setSelectedReport(null)}
                  title="Close preview"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            {/* Viewer Content Body */}
            <div className="reports-viewer-body">
              {/* Analysis Overview Card */}
              <div className="viewer-card">
                <h4 className="viewer-card-title">Analysis Overview</h4>
                <div className="viewer-info-grid">
                  <div className="viewer-info-item">
                    <span className="info-label">Analysis Name</span>
                    <span className="info-val">{selectedReport.analysisName}</span>
                  </div>
                  <div className="viewer-info-item">
                    <span className="info-label">Imagery Modality</span>
                    <span className="info-val cyan">{selectedReport.modality}</span>
                  </div>
                  <div className="viewer-info-item">
                    <span className="info-label">Active Channel</span>
                    <span className="info-val">{selectedReport.spectralChannel}</span>
                  </div>
                  <div className="viewer-info-item">
                    <span className="info-label">Target Region</span>
                    <span className="info-val green">{selectedReport.region}</span>
                  </div>
                  <div className="viewer-info-item">
                    <span className="info-label">Dataset / Source</span>
                    <span className="info-val">{selectedReport.dataset || 'Satellite Imagery'}</span>
                  </div>
                  <div className="viewer-info-item">
                    <span className="info-label">Confidence Score</span>
                    <span className="info-val green">{selectedReport.confidence}%</span>
                  </div>
                  {selectedReport.fileDimensions && (
                    <div className="viewer-info-item">
                      <span className="info-label">Image Dimensions</span>
                      <span className="info-val">{selectedReport.fileDimensions}</span>
                    </div>
                  )}
                  {selectedReport.fileSize && (
                    <div className="viewer-info-item">
                      <span className="info-label">File Size</span>
                      <span className="info-val">{selectedReport.fileSize}</span>
                    </div>
                  )}
                  {selectedReport.fileName && (
                    <div className="viewer-info-item">
                      <span className="info-label">File Name</span>
                      <span className="info-val" style={{ wordBreak: 'break-all' }}>{selectedReport.fileName}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Detected Regions Section */}
              <div className="viewer-card">
                <h4 className="viewer-card-title">Detected Regions</h4>
                {selectedReport.detectedRegions && selectedReport.detectedRegions.length > 0 ? (
                  <table className="viewer-regions-table">
                    <thead>
                      <tr>
                        <th>Region Name</th>
                        <th>Classification</th>
                        <th>Confidence</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedReport.detectedRegions.map((r, i) => (
                        <tr key={i}>
                          <td><strong>{r.name}</strong></td>
                          <td style={{ color: '#94a3b8' }}>{r.type}</td>
                          <td style={{ color: '#00ff88', fontWeight: 700 }}>{r.score}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <p className="viewer-empty-subtext">No detected regions recorded.</p>
                )}
              </div>

              {/* AI Insights & GeoChat Transcript */}
              {selectedReport.chatMessages && selectedReport.chatMessages.length > 1 ? (
                <div className="viewer-card">
                  <h4 className="viewer-card-title">
                    GeoChat AI Session (
                    {selectedReport.chatMessages.filter((m) => m.sender === 'user').length} queries)
                  </h4>
                  <div className="viewer-chat-list">
                    {selectedReport.chatMessages.slice(1).map((msg) => (
                      <div key={msg.id} className={`viewer-chat-item ${msg.sender}`}>
                        <div className="viewer-chat-header">
                          <span>{msg.sender === 'ai' ? '🤖 GeoChat AI' : '👤 Analyst'}</span>
                          <span>{msg.time}</span>
                        </div>
                        <p className="viewer-chat-text">{msg.text}</p>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="viewer-card">
                  <h4 className="viewer-card-title">AI Insights</h4>
                  <p className="viewer-empty-subtext">
                    No GeoChat interactions recorded for this analysis.
                  </p>
                </div>
              )}

              {/* Satellite Image Preview */}
              {selectedReport.imageUrl && (
                <div className="viewer-card">
                  <h4 className="viewer-card-title">Satellite Scene Preview</h4>
                  <div className="viewer-image-wrap">
                    <img src={selectedReport.imageUrl} alt="Analysis Satellite Scene" />
                  </div>
                </div>
              )}
            </div>

            {/* Viewer Footer */}
            <div className="reports-viewer-footer">
              <span className="footer-brand-text">
                Generated by SatQuery AI &bull; Verified Geospatial Report
              </span>
              <button
                type="button"
                className="reports-modal-cancel-btn"
                onClick={() => setSelectedReport(null)}
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── SHARE MODAL ── */}
      {shareReportItem && (
        <div className="reports-modal-backdrop" onClick={() => setShareReportItem(null)}>
          <div
            className="reports-modal-box"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-label="Share Report"
          >
            <div className="reports-modal-header">
              <div className="reports-modal-title">
                <Share2 size={16} className="cyan-icon" />
                Share Report
              </div>
              <button
                type="button"
                className="reports-modal-close"
                onClick={() => setShareReportItem(null)}
              >
                <X size={16} />
              </button>
            </div>

            <div className="reports-modal-body">
              <p className="modal-description-text">
                Share this verified satellite observation report with team members and collaborators.
              </p>

              <div className="share-url-box">
                <div className="share-url-input-preview">
                  <Link2 size={13} style={{ color: '#00d4ff', flexShrink: 0 }} />
                  <span className="share-url-text">
                    {`${window.location.origin}/reports?view=${shareReportItem.id}`}
                  </span>
                </div>
                <button
                  type="button"
                  className={`share-copy-btn ${shareCopied ? 'copied' : ''}`}
                  onClick={() => handleCopyShareLink(shareReportItem)}
                >
                  {shareCopied ? <Check size={13} /> : <Link2 size={13} />}
                  <span>{shareCopied ? 'Report link copied!' : 'Copy Link'}</span>
                </button>
              </div>

              {typeof navigator !== 'undefined' && 'share' in navigator && (
                <button
                  type="button"
                  className="share-native-device-btn"
                  onClick={() => handleNativeShare(shareReportItem)}
                >
                  <Share2 size={13} />
                  <span>Share via Device Menu…</span>
                </button>
              )}
            </div>

            <div className="reports-modal-footer">
              <button
                type="button"
                className="reports-modal-cancel-btn"
                onClick={() => setShareReportItem(null)}
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── DELETE CONFIRMATION MODAL ── */}
      {deletingReport && (
        <div className="reports-modal-backdrop" onClick={() => setDeletingReport(null)}>
          <div
            className="reports-modal-box"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-label="Confirm Delete Report"
          >
            <div className="reports-modal-header">
              <div className="reports-modal-title delete-title">
                <Trash2 size={16} color="#ff4d4f" />
                Delete Report
              </div>
              <button
                type="button"
                className="reports-modal-close"
                onClick={() => setDeletingReport(null)}
              >
                <X size={16} />
              </button>
            </div>

            <div className="reports-modal-body">
              <p className="delete-confirm-text">
                Delete this report?
              </p>
              <p className="delete-confirm-subtext">
                Are you sure you want to remove this report? The underlying analysis in your History will remain preserved.
              </p>
            </div>

            <div className="reports-modal-footer">
              <button
                type="button"
                className="reports-modal-cancel-btn"
                onClick={() => setDeletingReport(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="reports-modal-delete-btn"
                onClick={handleConfirmDelete}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ReportsPage;
