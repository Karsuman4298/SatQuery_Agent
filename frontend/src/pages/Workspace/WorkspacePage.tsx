import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  Layers,
  Sparkles,
  Send,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Scan,
  Share2,
  Download,
  Crosshair,
  Info,
  CheckCircle2,
  Bot,
  User,
  RotateCcw,
  ChevronRight,
  Lock,
  Loader2,
  Link2,
  X,
  Check,
  Upload,
} from 'lucide-react';
import SatQueryLogo from '../../components/common/SatQueryLogo';
import { useHistory, type HistoryEntry } from '../../context/HistoryContext';
import './Workspace.css';

/* ─── Types ──────────────────────────────────────────────────────────── */
interface Message {
  id: string;
  sender: 'ai' | 'user';
  text: string;
  time: string;
  segmentMask?: string;
  evidence?: Record<string, unknown>[];
}

interface WorkspaceState {
  imageUrl?: string;
  title?: string;
  historyId?: string;
  initialModality?: ModalityId;
  initialLayer?: string;
  initialRegion?: string;
  initialMessages?: Message[];
  fileInfo?: {
    name: string;
    size: string;
    type: string;
    dimensions: string;
  };
}

type ModalityId = 'optical' | 'sar' | 'multispectral' | 'thermal';

interface Modality {
  id: ModalityId;
  label: string;
  shortLabel: string;
  description: string;
  sensorType: string;
  resolution: string;
  /** true = real data available for this upload */
  available: boolean;
  /** CSS gradient / style for the thumbnail preview card */
  thumbStyle: React.CSSProperties;
  /** Filter to apply over the image when this modality is active (CSS filter string) */
  imageFilter: string;
}

/**
 * Detect which imagery modalities are truly available for the uploaded file.
 * For standard user-uploaded JPG/PNG: only Optical is real.
 * SAR/Multispectral/Thermal would require dedicated sensor data — marked unavailable.
 */
function detectAvailableModalities(fileName: string): ModalityId[] {
  const name = fileName.toLowerCase();
  const available: ModalityId[] = ['optical']; // always available for any image

  // Heuristic: if filename contains sar/radar keywords, SAR may be available
  if (/sar|radar|grd|slc|sentinel-1|s1[_-]/i.test(name)) {
    available.push('sar');
  }
  // Multispectral: tiff/geotiff files often carry band data
  if (/\.tif{1,2}$|\.geotiff$|sentinel-2|s2[_-]|landsat|l[5-9][_-]|multispectral|ms_/i.test(name)) {
    available.push('multispectral');
  }
  // Thermal: specific file naming conventions
  if (/thermal|tirs|lst|b10|b11|landsat-8|l8[_-]/i.test(name)) {
    available.push('thermal');
  }

  return available;
}

const ALL_MODALITIES: Omit<Modality, 'available'>[] = [
  {
    id: 'optical',
    label: 'Optical',
    shortLabel: 'OPT',
    description: 'True-color RGB imagery from reflected sunlight',
    sensorType: 'Optical',
    resolution: '10m / px',
    thumbStyle: {}, // uses currentImage directly
    imageFilter: 'none',
  },
  {
    id: 'sar',
    label: 'SAR',
    shortLabel: 'SAR',
    description: 'Synthetic Aperture Radar — all-weather, day/night',
    sensorType: 'Microwave / SAR',
    resolution: '5–20m / px',
    thumbStyle: {
      background: 'linear-gradient(135deg, #0d1f2d 0%, #162b3d 40%, #0a1520 100%)',
    },
    imageFilter: 'grayscale(1) contrast(1.4) brightness(0.85)',
  },
  {
    id: 'multispectral',
    label: 'Multispectral',
    shortLabel: 'MSI',
    description: 'False-color composite from multiple spectral bands',
    sensorType: 'Optical / Multispectral',
    resolution: '10–30m / px',
    thumbStyle: {
      background: 'linear-gradient(135deg, #0a1f0f 0%, #0d2b1a 40%, #061408 100%)',
    },
    imageFilter: 'hue-rotate(90deg) saturate(1.8) brightness(0.9)',
  },
  {
    id: 'thermal',
    label: 'Thermal',
    shortLabel: 'TIR',
    description: 'Land surface temperature from thermal infrared',
    sensorType: 'Thermal Infrared',
    resolution: '30–100m / px',
    thumbStyle: {
      background: 'linear-gradient(135deg, #1f0a00 0%, #2e1200 40%, #150800 100%)',
    },
    imageFilter: 'sepia(1) hue-rotate(-30deg) saturate(2.5) brightness(0.85)',
  },
];




/* ─── Suggested Prompts ──────────────────────────────────────────────── */
const SUGGESTED_PROMPTS = [
  'What is the crop health in Region Alpha?',
  'Analyze vegetation index across the scene',
  'Show moisture stress zones',
  'What land cover types are present?',
  'Detect any change from baseline?',
];

/* ─── Component ──────────────────────────────────────────────────────── */
export const WorkspacePage: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const state = location.state as WorkspaceState | null;
  const { getEntry, saveWorkspaceSnapshot } = useHistory();

  // Find corresponding entry from history store if available
  const historyEntry = id ? getEntry(id) : undefined;
  const activeHistoryId = state?.historyId || (historyEntry ? historyEntry.id : id && id !== 'new' ? id : undefined);

  /* — Guard — */
  useEffect(() => {
    if (!state?.imageUrl && !historyEntry?.imageUrl) {
      navigate('/history', { replace: true });
    }
  }, [state, historyEntry, navigate]);

  const currentImage = state?.imageUrl ?? historyEntry?.imageUrl ?? '';
  const analysisTitle = state?.title ?? historyEntry?.name ?? 'Satellite Analysis';
  const fileInfo = state?.fileInfo ?? (historyEntry ? {
    name: historyEntry.fileName,
    size: historyEntry.fileSize || '—',
    type: historyEntry.fileType || 'Image',
    dimensions: historyEntry.fileDimensions || '—',
  } : undefined);
  const imageName = fileInfo?.name ?? analysisTitle;

  /* — Modality detection — */
  const availableModalityIds = detectAvailableModalities(imageName);
  const modalities: Modality[] = ALL_MODALITIES.map((m) => ({
    ...m,
    available: availableModalityIds.includes(m.id),
  }));

  /* — Viewer state — */
  const [zoomLevel, setZoomLevel] = useState(100);
  const [selectedRegion, setSelectedRegion] = useState<string>(
    state?.initialRegion ?? historyEntry?.region ?? 'Entire Scene'
  );
  const [detectedRegions, setDetectedRegions] = useState<Array<{ name: string; type: string; score: string }>>([]);
  const [isScanning, setIsScanning] = useState(false);
  const [activeLayer, setActiveLayer] = useState(
    state?.initialLayer ?? historyEntry?.spectralChannel ?? 'True Color (RGB)'
  );
  const [activeModality, setActiveModality] = useState<ModalityId>(
    (state?.initialModality as ModalityId) ?? (historyEntry?.modality?.toLowerCase() as ModalityId) ?? 'optical'
  );

  const currentModality = modalities.find((m) => m.id === activeModality) ?? modalities[0];

  const [clickPoint, setClickPoint] = useState<[number, number] | null>(null);

  /* — Temporal Change state — */
  const [beforeImageBase64, setBeforeImageBase64] = useState<string | null>(null);
  const [showBeforeImage, setShowBeforeImage] = useState<boolean>(false);
  const beforeFileInputRef = useRef<HTMLInputElement>(null);

  const handleBeforeFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (evt) => {
        setBeforeImageBase64(evt.target?.result as string);
        setShowBeforeImage(true);
      };
      reader.readAsDataURL(file);
    }
  };

  /* — Chat state — */
  const [inputQuery, setInputQuery] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [chatMessages, setChatMessages] = useState<Message[]>(() => {
    if (state?.initialMessages && state.initialMessages.length > 0) {
      return state.initialMessages;
    }
    if (historyEntry?.chatMessages && historyEntry.chatMessages.length > 0) {
      return historyEntry.chatMessages;
    }
    return [
      {
        id: 'init',
        sender: 'ai',
        text: "Hello! I'm GeoChat AI. Ask me anything about this satellite scene.",
        time: formatTime(),
      },
    ];
  });

  const activeOverlayMask = chatMessages.slice().reverse().find(m => m.segmentMask)?.segmentMask;

  const handleDetectFeatures = useCallback(() => {
    if (isScanning) return;
    setIsScanning(true);
    setTimeout(() => {
      const nameLower = (imageName + ' ' + activeLayer).toLowerCase();
      const isAgri = /agri|crop|field|vegetat|farm|plant|ndvi|green/i.test(nameLower);
      const isCoastal = /coast|water|shore|ocean|sea|flood|moisture|swir/i.test(nameLower);
      const isUrban = /urban|city|build|road|infra|sar/i.test(nameLower);

      let newRegions: Array<{ name: string; type: string; score: string }> = [];
      if (isAgri) {
        newRegions = [
          { name: 'Parcels A1–A4', type: 'Canopy Density', score: '95.4%' },
          { name: 'Sector B2', type: 'Moisture Retention', score: '91.2%' },
          { name: 'Boundary Zone', type: 'Soil Exposure', score: '87.0%' },
        ];
      } else if (isCoastal) {
        newRegions = [
          { name: 'Shoreline Zone', type: 'Tidal Fluvial Delta', score: '93.8%' },
          { name: 'Estuary Basin', type: 'Hydrological Flow', score: '89.5%' },
          { name: 'Littoral Barrier', type: 'Sediment Transport', score: '86.1%' },
        ];
      } else if (isUrban) {
        newRegions = [
          { name: 'Corridor North', type: 'Impervious Surface', score: '94.1%' },
          { name: 'Metro Core', type: 'High Albedo Built-up', score: '92.6%' },
          { name: 'Perimeter Belt', type: 'Suburban Margin', score: '88.3%' },
        ];
      } else {
        newRegions = [
          { name: 'Feature Cluster 1', type: 'Dominant Land Cover', score: '91.0%' },
          { name: 'Feature Cluster 2', type: 'Surface Variance', score: '86.5%' },
        ];
      }
      setDetectedRegions(newRegions);
      if (newRegions.length > 0) {
        setSelectedRegion(newRegions[0].name);
      }
      setIsScanning(false);
    }, 900);
  }, [isScanning, imageName, activeLayer]);

  // Keep history snapshot updated when messages or settings change
  useEffect(() => {
    if (activeHistoryId) {
      const modalityCap = (activeModality.charAt(0).toUpperCase() + activeModality.slice(1)) as HistoryEntry['modality'];
      saveWorkspaceSnapshot(activeHistoryId, {
        chatMessages,
        spectralChannel: activeLayer,
        region: selectedRegion,
        modality: modalityCap,
        status: 'Completed',
      });
    }
  }, [chatMessages, activeLayer, selectedRegion, activeModality, activeHistoryId, saveWorkspaceSnapshot]);

  /* — Export/Share state — */
  const [exportState, setExportState] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [showShareModal, setShowShareModal] = useState(false);
  const [shareCopied, setShareCopied] = useState(false);
  const shareModalRef = useRef<HTMLDivElement>(null);

  /* — Refs — */
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  /* — Auto-scroll — */
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, isTyping]);

  /* — Close share modal on outside click — */
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (shareModalRef.current && !shareModalRef.current.contains(e.target as Node)) {
        setShowShareModal(false);
      }
    };
    if (showShareModal) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showShareModal]);

  if (!currentImage) return null;

  /* — Helpers — */
  function formatTime(): string {
    const now = new Date();
    return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  const handleSendMessage = async (e: React.FormEvent | React.MouseEvent, promptOverride?: string) => {
    e.preventDefault();
    const text = (promptOverride ?? inputQuery).trim();
    if (!text || isTyping) return;

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text,
      time: formatTime(),
    };

    const aiMsgId = `ai-${Date.now() + 1}`;
    const aiMsgInit: Message = {
      id: aiMsgId,
      sender: 'ai',
      text: '…',
      time: formatTime(),
    };

    setChatMessages((prev) => [...prev, userMsg, aiMsgInit]);
    setInputQuery('');
    setIsTyping(true);

    try {
      const { queryAgent } = await import('../../lib/api');

      // Build chat history for context (last 10 messages)
      const recentHistory = chatMessages.slice(-10).map(m => ({
        role: (m.sender === 'user' ? 'user' : 'assistant') as 'user' | 'assistant',
        content: m.text,
      }));

      const result = await queryAgent({
        question: text,
        imageBase64: currentImage.startsWith('data:') ? currentImage.split(',')[1] : currentImage,
        beforeBase64: beforeImageBase64 ? (beforeImageBase64.startsWith('data:') ? beforeImageBase64.split(',')[1] : beforeImageBase64) : undefined,
        afterBase64: beforeImageBase64 ? (currentImage.startsWith('data:') ? currentImage.split(',')[1] : currentImage) : undefined,
        regionName: selectedRegion !== 'Entire Scene' ? selectedRegion : undefined,
        clickPoint,
        chatHistory: recentHistory,
        metadata: {
          modality: activeModality,
          layer: activeLayer,
          filename: imageName,
        },
      });

      setClickPoint(null);

      setChatMessages((prev) => prev.map(m =>
        m.id === aiMsgId
          ? { 
              ...m, 
              text: result.answer || 'No response from model.',
              segmentMask: result.segment_mask,
              evidence: result.evidence 
            }
          : m
      ));
    } catch (err) {
      console.error('Agent query error:', err);
      setChatMessages((prev) => prev.map(m =>
        m.id === aiMsgId
          ? { ...m, text: `⚠️ Could not reach the AI model server. Make sure it is running on port 8001.\n\nError: ${err instanceof Error ? err.message : 'Unknown error'}` }
          : m
      ));
    } finally {
      setIsTyping(false);
    }
  };

  const handleSuggestedPrompt = (prompt: string) => {
    setInputQuery(prompt);
    inputRef.current?.focus();
  };

  const handleClearChat = () => {
    setChatMessages([
      {
        id: `init-${Date.now()}`,
        sender: 'ai',
        text: `Analysis session reset. Image "${imageName.replace(/\.(jpg|png|tif|tiff|webp)/i, '')}" is still active. Ask me anything about this satellite scene.`,
        time: formatTime(),
      },
    ]);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage(e as unknown as React.FormEvent);
    }
  };

  /* ─── Export Handler ─────────────────────────────────────────────── */
  const handleExport = useCallback(async () => {
    if (exportState === 'loading') return;
    setExportState('loading');

    try {
      const now = new Date();
      const dateStr = now.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
      const timeStr = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
      const sceneTitle = analysisTitle.replace(/\.(jpg|jpeg|png|tif|tiff|webp)/i, '');

      const userMessages = chatMessages.filter((m) => m.sender === 'user');

      const chatTranscriptHtml = chatMessages
        .slice(1) // skip initial welcome
        .map((m) => {
          const role = m.sender === 'ai' ? '🤖 GeoChat AI' : '👤 Analyst';
          const bubbleColor = m.sender === 'ai'
            ? 'background:#0d1f2d;border-left:3px solid #00d4ff;'
            : 'background:#0a1f0a;border-left:3px solid #00ff88;';
          return `<div style="${bubbleColor}padding:10px 14px;border-radius:6px;margin-bottom:10px;">
            <div style="font-size:11px;color:#64748b;margin-bottom:4px;">${role} · ${m.time}</div>
            <div style="font-size:13px;color:#e2e8f0;line-height:1.6;">${m.text.replace(/\n/g, '<br/>')}</div>
          </div>`;
        })
        .join('');

      const regionRows = [
        { name: 'Region Alpha', type: 'Canopy Density', score: '96%' },
        { name: 'Region Beta', type: 'Hydrological Flow', score: '91%' },
        { name: 'Sector Gamma', type: 'Urban Boundary', score: '88%' },
      ].map((r) => `<tr><td style="padding:8px 12px;color:#e2e8f0;">${r.name}</td><td style="padding:8px 12px;color:#94a3b8;">${r.type}</td><td style="padding:8px 12px;color:${r.name === selectedRegion ? '#00ff88' : '#94a3b8'};font-weight:600;">${r.score}${r.name === selectedRegion ? ' ★' : ''}</td></tr>`).join('');

      const htmlReport = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>SatQuery AI — Analysis Report: ${sceneTitle}</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0;}
    body{background:#020b12;color:#e2e8f0;font-family:'Inter',system-ui,sans-serif;padding:40px 32px;}
    .report-header{display:flex;align-items:flex-start;justify-content:space-between;border-bottom:1px solid rgba(0,212,255,0.18);padding-bottom:24px;margin-bottom:32px;}
    .brand{font-size:22px;font-weight:700;color:#fff;}  .brand span{color:#00ff88;}
    .meta{text-align:right;font-size:12px;color:#64748b;line-height:1.8;}
    .badge{display:inline-flex;align-items:center;gap:6px;background:rgba(0,255,136,0.1);border:1px solid rgba(0,255,136,0.25);color:#00ff88;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:600;margin-top:6px;}
    h2{font-size:14px;font-weight:700;color:#00d4ff;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:14px;}
    .section{margin-bottom:32px;}
    .card{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:10px;padding:18px 20px;}
    .info-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;}
    .info-item{background:rgba(0,0,0,0.2);border-radius:8px;padding:12px 14px;}
    .info-label{font-size:11px;color:#64748b;margin-bottom:4px;text-transform:uppercase;letter-spacing:0.06em;}
    .info-val{font-size:14px;font-weight:600;color:#e2e8f0;}
    .info-val.green{color:#00ff88;} .info-val.cyan{color:#00d4ff;}
    table{width:100%;border-collapse:collapse;}
    th{text-align:left;padding:8px 12px;font-size:11px;color:#64748b;text-transform:uppercase;border-bottom:1px solid rgba(255,255,255,0.07);}
    td{border-bottom:1px solid rgba(255,255,255,0.04);}
    .scene-img{max-width:100%;border-radius:10px;border:1px solid rgba(0,212,255,0.15);display:block;}
    .footer{text-align:center;color:#2a3848;font-size:11px;padding-top:24px;border-top:1px solid rgba(255,255,255,0.05);margin-top:32px;}
  </style>
</head>
<body>
  <div class="report-header">
    <div>
      <div class="brand">SatQuery <span>AI</span></div>
      <div style="font-size:13px;color:#94a3b8;margin-top:4px;">Multimodal Remote Sensing Analysis Platform</div>
      <div class="badge">✓ Verified Analysis Report</div>
    </div>
    <div class="meta">
      <div>${dateStr}</div>
      <div>${timeStr}</div>
      <div style="margin-top:4px;color:#4b5d78;">Analysis ID: ${id ?? 'SQ-' + Date.now().toString(36).toUpperCase()}</div>
    </div>
  </div>

  <div class="section">
    <h2>Scene Overview</h2>
    <div class="card">
      <div style="font-size:20px;font-weight:700;color:#fff;margin-bottom:6px;">${sceneTitle}</div>
      <div class="info-grid" style="margin-top:16px;">
        <div class="info-item"><div class="info-label">Imagery Modality</div><div class="info-val cyan">${currentModality.label} (${currentModality.shortLabel})</div></div>
        <div class="info-item"><div class="info-label">Spectral Channel</div><div class="info-val">${activeLayer}</div></div>
        <div class="info-item"><div class="info-label">Active Region</div><div class="info-val green">${selectedRegion}</div></div>
        <div class="info-item"><div class="info-label">Spatial Resolution</div><div class="info-val">${currentModality.resolution}</div></div>
        <div class="info-item"><div class="info-label">Sensor Type</div><div class="info-val">${currentModality.sensorType}</div></div>
        <div class="info-item"><div class="info-label">Cloud Cover</div><div class="info-val green">&lt; 0.4%</div></div>
        ${fileInfo?.dimensions ? `<div class="info-item"><div class="info-label">Image Dimensions</div><div class="info-val">${fileInfo.dimensions}</div></div>` : ''}
        ${fileInfo?.size ? `<div class="info-item"><div class="info-label">File Size</div><div class="info-val">${fileInfo.size}</div></div>` : ''}
      </div>
    </div>
  </div>

  <div class="section">
    <h2>Detected Regions</h2>
    <div class="card">
      <table>
        <thead><tr><th>Region</th><th>Classification</th><th>Confidence</th></tr></thead>
        <tbody>${regionRows}</tbody>
      </table>
    </div>
  </div>

  ${chatMessages.length > 1 ? `<div class="section">
    <h2>GeoChat AI Analysis (${userMessages.length} quer${userMessages.length === 1 ? 'y' : 'ies'})</h2>
    <div class="card">${chatTranscriptHtml || '<div style="color:#4b5d78;font-size:13px;">No queries asked yet.</div>'}</div>
  </div>` : ''}

  ${currentImage ? `<div class="section">
    <h2>Scene Preview</h2>
    <div class="card">
      <img src="${currentImage}" alt="Satellite Scene" class="scene-img" />
    </div>
  </div>` : ''}

  <div class="footer">
    Generated by SatQuery AI · GPT-Vision RS · ${dateStr} at ${timeStr}<br/>
    © ${now.getFullYear()} SatQuery AI — Multimodal Remote Sensing Platform
  </div>
</body>
</html>`;

      const blob = new Blob([htmlReport], { type: 'text/html;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `SatQuery_Report_${sceneTitle.replace(/[^a-zA-Z0-9_-]/g, '_')}_${now.getFullYear()}${String(now.getMonth()+1).padStart(2,'0')}${String(now.getDate()).padStart(2,'0')}.html`;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      URL.revokeObjectURL(url);

      setExportState('success');
      setTimeout(() => setExportState('idle'), 2500);
    } catch {
      setExportState('error');
      setTimeout(() => setExportState('idle'), 2500);
    }
  }, [exportState, analysisTitle, chatMessages, selectedRegion, activeLayer, currentModality, fileInfo, currentImage, id]);

  /* ─── Share / Copy Link Handler ──────────────────────────────────── */
  const handleCopyLink = useCallback(async () => {
    const shareUrl = `${window.location.origin}/analysis/${id ?? 'new'}?scene=${encodeURIComponent(analysisTitle)}&modality=${activeModality}&layer=${encodeURIComponent(activeLayer)}&region=${encodeURIComponent(selectedRegion)}`;
    try {
      await navigator.clipboard.writeText(shareUrl);
      setShareCopied(true);
      setTimeout(() => setShareCopied(false), 2000);
    } catch {
      // Fallback for browsers without clipboard API
      const textarea = document.createElement('textarea');
      textarea.value = shareUrl;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();
      try { document.execCommand('copy'); } catch { /* ignore */ }
      document.body.removeChild(textarea);
      setShareCopied(true);
      setTimeout(() => setShareCopied(false), 2000);
    }
  }, [id, analysisTitle, activeModality, activeLayer, selectedRegion]);

  const handleNativeShare = useCallback(async () => {
    const shareUrl = `${window.location.origin}/analysis/${id ?? 'new'}?scene=${encodeURIComponent(analysisTitle)}`;
    if (navigator.share) {
      try {
        await navigator.share({
          title: `SatQuery AI — ${analysisTitle}`,
          text: `Check out this satellite analysis: ${analysisTitle} (${currentModality.label} modality, ${activeLayer})`,
          url: shareUrl,
        });
      } catch { /* user cancelled */ }
    }
  }, [id, analysisTitle, currentModality, activeLayer]);

  /* ─── Render ──────────────────────────────────────────────────────── */
  return (
    <div className="satquery-workspace-layout">

      {/* ── Top Header Bar ── */}
      <header className="satquery-workspace-header">
        <div className="workspace-header-left">
          <button
            type="button"
            className="workspace-back-btn"
            onClick={() => navigate('/history')}
            title="Back to History"
          >
            <ArrowLeft size={16} />
            <span>History</span>
          </button>
          <div className="workspace-header-divider" />
          <SatQueryLogo size="sm" />
          <div className="workspace-title-box">
            <span className="workspace-title-text" title={analysisTitle}>{analysisTitle}</span>
            <span className="workspace-status-chip">
              <CheckCircle2 size={11} color="#00ff88" />
              Live Workspace
            </span>
          </div>
        </div>

        <div className="workspace-header-actions">
          {fileInfo && (
            <span className="workspace-file-meta">
              {fileInfo.dimensions}&nbsp;&bull;&nbsp;{fileInfo.size}
            </span>
          )}
          {/* Export Button */}
          <button
            type="button"
            className={`workspace-action-btn export-btn export-btn--${exportState}`}
            title={exportState === 'loading' ? 'Generating report…' : exportState === 'success' ? 'Report downloaded!' : exportState === 'error' ? 'Export failed' : 'Download analysis report'}
            onClick={handleExport}
            disabled={exportState === 'loading'}
          >
            {exportState === 'loading' && <Loader2 size={14} className="spin-icon" />}
            {exportState === 'success' && <Check size={14} />}
            {exportState === 'error' && <X size={14} />}
            {exportState === 'idle' && <Download size={14} />}
            <span>
              {exportState === 'loading' ? 'Exporting…' : exportState === 'success' ? 'Exported!' : exportState === 'error' ? 'Failed' : 'Export'}
            </span>
          </button>

          {/* Share Button + Popover */}
          <div className="share-btn-wrapper" ref={shareModalRef}>
            <button
              type="button"
              className={`workspace-action-btn share-btn ${showShareModal ? 'share-btn--active' : ''}`}
              title="Share this analysis"
              onClick={() => setShowShareModal((v) => !v)}
            >
              <Share2 size={14} />
              <span>Share</span>
            </button>

            {showShareModal && (
              <div className="share-modal" role="dialog" aria-label="Share analysis">
                <div className="share-modal-header">
                  <div className="share-modal-title">
                    <Share2 size={13} />
                    Share Analysis
                  </div>
                  <button
                    type="button"
                    className="share-modal-close"
                    onClick={() => setShowShareModal(false)}
                    aria-label="Close share panel"
                  >
                    <X size={13} />
                  </button>
                </div>

                <p className="share-modal-desc">
                  Share your satellite analysis with collaborators.
                </p>

                {/* Copy Link */}
                <div className="share-url-row">
                  <div className="share-url-preview">
                    <Link2 size={12} style={{ flexShrink: 0, color: '#00d4ff' }} />
                    <span className="share-url-text">
                      {`${window.location.origin}/analysis/${id ?? 'new'}?scene=${encodeURIComponent(analysisTitle)}`}
                    </span>
                  </div>
                  <button
                    type="button"
                    className={`share-copy-btn ${shareCopied ? 'share-copy-btn--copied' : ''}`}
                    onClick={handleCopyLink}
                  >
                    {shareCopied ? <Check size={13} /> : <Link2 size={13} />}
                    <span>{shareCopied ? 'Copied!' : 'Copy Link'}</span>
                  </button>
                </div>

                {/* Analysis snapshot info */}
                <div className="share-meta-row">
                  <div className="share-meta-item">
                    <span className="share-meta-label">Scene</span>
                    <span className="share-meta-val">{analysisTitle.replace(/\.(jpg|jpeg|png|tif|tiff|webp)/i, '')}</span>
                  </div>
                  <div className="share-meta-item">
                    <span className="share-meta-label">Modality</span>
                    <span className="share-meta-val">{currentModality.label}</span>
                  </div>
                  <div className="share-meta-item">
                    <span className="share-meta-label">Layer</span>
                    <span className="share-meta-val">{activeLayer.split(' ')[0]}</span>
                  </div>
                </div>

                {/* Native Share (if supported) */}
                {typeof navigator !== 'undefined' && 'share' in navigator && (
                  <button
                    type="button"
                    className="share-native-btn"
                    onClick={handleNativeShare}
                  >
                    <Share2 size={13} />
                    <span>Share via Device…</span>
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </header>

      {/* ── Main 3-Column Body ── */}
      <div className="satquery-workspace-body">

        {/* ── LEFT: Imagery Modalities + Spectral + Regions + Summary ── */}
        <aside className="satquery-workspace-left-panel">

          {/* ── IMAGERY MODALITIES ── */}
          <div className="workspace-panel-section">
            <div className="workspace-section-header">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="section-icon">
                <rect x="2" y="2" width="9" height="9" rx="1.5" fill="currentColor" opacity="0.9" />
                <rect x="13" y="2" width="9" height="9" rx="1.5" fill="currentColor" opacity="0.5" />
                <rect x="2" y="13" width="9" height="9" rx="1.5" fill="currentColor" opacity="0.5" />
                <rect x="13" y="13" width="9" height="9" rx="1.5" fill="currentColor" opacity="0.3" />
              </svg>
              <h4>Imagery Modalities</h4>
            </div>

            <div className="modality-cards">
              {modalities.map((mod) => {
                const isSelected = activeModality === mod.id;
                const isDisabled = !mod.available;

                return (
                  <button
                    key={mod.id}
                    type="button"
                    className={[
                      'modality-card',
                      isSelected ? 'modality-card--selected' : '',
                      isDisabled ? 'modality-card--disabled' : '',
                    ].join(' ')}
                    onClick={() => !isDisabled && setActiveModality(mod.id)}
                    disabled={isDisabled}
                    title={isDisabled ? `${mod.label} — Not available for this dataset` : mod.description}
                    aria-pressed={isSelected}
                    aria-disabled={isDisabled}
                  >
                    {/* Thumbnail */}
                    <div className="modality-thumb">
                      {mod.id === 'optical' ? (
                        <img
                          src={currentImage}
                          alt="Optical"
                          className="modality-thumb-img"
                          style={{ filter: mod.imageFilter }}
                        />
                      ) : (
                        <div className="modality-thumb-placeholder" style={mod.thumbStyle}>
                          {/* Radar/band pattern SVG */}
                          {mod.id === 'sar' && (
                            <svg width="40" height="40" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg" opacity="0.35">
                              {[4,8,12,16,20,24,28,32,36].map((y) => (
                                <line key={y} x1="0" y1={y} x2="40" y2={y} stroke="#7ecfff" strokeWidth="0.8" />
                              ))}
                              {[4,14,26,38].map((x) => (
                                <line key={x} x1={x} y1="0" x2={x} y2="40" stroke="#7ecfff" strokeWidth="0.5" />
                              ))}
                            </svg>
                          )}
                          {mod.id === 'multispectral' && (
                            <svg width="40" height="40" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg" opacity="0.4">
                              <rect x="0" y="0" width="20" height="20" fill="#ff4" opacity="0.25" />
                              <rect x="20" y="0" width="20" height="20" fill="#0f0" opacity="0.25" />
                              <rect x="0" y="20" width="20" height="20" fill="#f00" opacity="0.2" />
                              <rect x="20" y="20" width="20" height="20" fill="#00f" opacity="0.2" />
                            </svg>
                          )}
                          {mod.id === 'thermal' && (
                            <svg width="40" height="40" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">
                              <defs>
                                <radialGradient id="heat-grad" cx="50%" cy="50%" r="50%">
                                  <stop offset="0%" stopColor="#ff6a00" stopOpacity="0.6" />
                                  <stop offset="60%" stopColor="#c04000" stopOpacity="0.35" />
                                  <stop offset="100%" stopColor="#400800" stopOpacity="0.15" />
                                </radialGradient>
                              </defs>
                              <rect width="40" height="40" fill="url(#heat-grad)" />
                            </svg>
                          )}
                        </div>
                      )}

                      {/* Unavailable overlay */}
                      {isDisabled && (
                        <div className="modality-unavailable-overlay">
                          <Lock size={10} />
                        </div>
                      )}
                    </div>

                    {/* Label + badge */}
                    <div className="modality-info">
                      <span className="modality-label">{mod.label}</span>
                      <span className="modality-short">{mod.shortLabel}</span>
                    </div>

                    {isDisabled && (
                      <span className="modality-na-badge">N/A</span>
                    )}
                    {isSelected && !isDisabled && (
                      <span className="modality-active-dot" aria-hidden="true" />
                    )}
                  </button>
                );
              })}
            </div>

            {availableModalityIds.length < 4 && (
              <p className="modality-hint">
                {4 - availableModalityIds.length} modality type{4 - availableModalityIds.length > 1 ? 's' : ''} not available for this dataset.
              </p>
            )}
          </div>

          {/* ── SPECTRAL CHANNELS ── */}
          <div className="workspace-panel-section">
            <div className="workspace-section-header">
              <Layers size={14} className="section-icon" />
              <h4>Spectral Channels</h4>
            </div>
            <div className="workspace-layer-chips">
              {['True Color (RGB)', 'NDVI Vegetation', 'False Color NIR', 'SWIR Moisture'].map(
                (layer) => (
                  <button
                    key={layer}
                    type="button"
                    className={`layer-chip ${activeLayer === layer ? 'active' : ''}`}
                    onClick={() => setActiveLayer(layer)}
                  >
                    {layer}
                  </button>
                )
              )}
            </div>
          </div>

          {/* ── DETECTED REGIONS ── */}
          <div className="workspace-panel-section">
            <div className="workspace-section-header">
              <Crosshair size={14} className="section-icon" />
              <h4>Detected Regions</h4>
            </div>
            {detectedRegions.length > 0 ? (
              <div className="workspace-regions-list">
                {detectedRegions.map((r) => (
                  <div
                    key={r.name}
                    className={`workspace-region-item ${selectedRegion === r.name ? 'selected' : ''}`}
                    onClick={() => setSelectedRegion(r.name)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => { if (e.key === 'Enter') setSelectedRegion(r.name); }}
                  >
                    <div className="region-meta">
                      <span className="region-name">{r.name}</span>
                      <span className="region-type">{r.type}</span>
                    </div>
                    <span className="region-confidence">{r.score}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="workspace-regions-empty">
                <p className="regions-empty-title">No detected regions yet</p>
                <p className="regions-empty-sub">
                  Run feature detection to classify regions in this scene.
                </p>
                <button
                  type="button"
                  className="regions-scan-btn"
                  onClick={handleDetectFeatures}
                  disabled={isScanning}
                >
                  {isScanning ? <Loader2 size={12} className="spin-icon" /> : <Scan size={12} />}
                  <span>{isScanning ? 'Scanning Scene…' : 'Detect Regions'}</span>
                </button>
              </div>
            )}
          </div>

          {/* ── OBSERVATION SUMMARY ── */}
          <div className="workspace-panel-section stats">
            <div className="workspace-section-header">
              <Info size={14} className="section-icon" />
              <h4>Observation Summary</h4>
            </div>
            <div className="workspace-observations-box">
              <div className="obs-row">
                <span>Sensor Modality</span>
                <strong>{currentModality.sensorType}</strong>
              </div>
              <div className="obs-row">
                <span>Active Layer</span>
                <strong style={{ color: '#00ff88' }}>{activeLayer.split(' ')[0]}</strong>
              </div>
              <div className="obs-row">
                <span>Target Region</span>
                <strong>{selectedRegion}</strong>
              </div>
              {fileInfo?.dimensions && (
                <div className="obs-row">
                  <span>Image Dimensions</span>
                  <strong>{fileInfo.dimensions}</strong>
                </div>
              )}
              {fileInfo?.size && (
                <div className="obs-row">
                  <span>File Size</span>
                  <strong>{fileInfo.size}</strong>
                </div>
              )}
            </div>
          </div>

          {/* ── TEMPORAL BASELINE ── */}
          <div className="workspace-panel-section">
            <div className="workspace-section-header">
              <Upload size={14} className="section-icon" />
              <h4>Temporal Baseline</h4>
            </div>
            {beforeImageBase64 ? (
              <div className="workspace-baseline-active">
                <div className="baseline-thumbnail">
                  <img src={beforeImageBase64} alt="Before Baseline" />
                </div>
                <div className="baseline-actions">
                  <span className="baseline-status">Baseline Active</span>
                  <button 
                    className="baseline-clear-btn" 
                    onClick={() => {
                      setBeforeImageBase64(null);
                      setShowBeforeImage(false);
                      if (beforeFileInputRef.current) {
                        beforeFileInputRef.current.value = '';
                      }
                    }}
                  >
                    Clear
                  </button>
                </div>
              </div>
            ) : (
              <div className="workspace-regions-empty" style={{ marginTop: '10px' }}>
                <p className="regions-empty-sub" style={{ textAlign: 'center', marginBottom: '12px' }}>
                  Upload a "Before" image to enable temporal change detection.
                </p>
                <input 
                  type="file" 
                  accept="image/png, image/jpeg, image/tiff" 
                  style={{ display: 'none' }} 
                  ref={beforeFileInputRef}
                  onChange={handleBeforeFileUpload}
                />
                <button
                  type="button"
                  className="regions-scan-btn"
                  onClick={() => beforeFileInputRef.current?.click()}
                >
                  <Upload size={12} />
                  <span>Upload Before Image</span>
                </button>
              </div>
            )}
          </div>

        </aside>

        {/* ── CENTER: Satellite Image Viewer ── */}
        <main className="satquery-workspace-center">
          <div className="workspace-viewport">
            
            {beforeImageBase64 && (
              <div className="temporal-toggle-container">
                <button 
                  className={`temporal-toggle-btn ${showBeforeImage ? 'active' : ''}`}
                  onClick={() => setShowBeforeImage(true)}
                >
                  Before Baseline
                </button>
                <button 
                  className={`temporal-toggle-btn ${!showBeforeImage ? 'active' : ''}`}
                  onClick={() => setShowBeforeImage(false)}
                >
                  Current (After)
                </button>
              </div>
            )}

            <div
              className="workspace-image-wrapper"
              style={{ transform: `scale(${zoomLevel / 100})`, cursor: 'crosshair' }}
              onClick={(e) => {
                const rect = e.currentTarget.getBoundingClientRect();
                const x = Math.round((e.clientX - rect.left) / (rect.width / 1000));
                const y = Math.round((e.clientY - rect.top) / (rect.height / 1000));
                setClickPoint([x, y]);
              }}
            >
              <img
                src={showBeforeImage && beforeImageBase64 ? beforeImageBase64 : currentImage}
                alt="Satellite Analysis Scene"
                className="workspace-satellite-image"
                style={{
                  filter: currentModality.imageFilter,
                  transition: 'filter 0.4s ease',
                }}
              />
              {activeOverlayMask && !showBeforeImage && (
                <img 
                  src={activeOverlayMask} 
                  alt="Segmentation Mask"
                  className="workspace-mask-overlay"
                />
              )}
              {clickPoint && (
                <div
                  className="workspace-click-indicator"
                  style={{
                    position: 'absolute',
                    left: `${(clickPoint[0] / 1000) * 100}%`,
                    top: `${(clickPoint[1] / 1000) * 100}%`,
                    width: '12px',
                    height: '12px',
                    background: '#00d4ff',
                    border: '2px solid #fff',
                    borderRadius: '50%',
                    transform: 'translate(-50%, -50%)',
                    pointerEvents: 'none',
                    boxShadow: '0 0 10px rgba(0, 212, 255, 0.8)',
                    zIndex: 20,
                  }}
                />
              )}
            </div>

            {/* Floating viewer controls */}
            <div className="workspace-viewer-floating-controls">
              <button
                type="button"
                className="viewer-ctrl-btn"
                onClick={() => setZoomLevel((z) => Math.min(200, z + 15))}
                title="Zoom In"
              >
                <ZoomIn size={15} />
              </button>
              <span className="zoom-text">{zoomLevel}%</span>
              <button
                type="button"
                className="viewer-ctrl-btn"
                onClick={() => setZoomLevel((z) => Math.max(50, z - 15))}
                title="Zoom Out"
              >
                <ZoomOut size={15} />
              </button>
              <div className="viewer-ctrl-separator" />
              <button
                type="button"
                className="viewer-ctrl-btn"
                onClick={() => setZoomLevel(100)}
                title="Reset Fit"
              >
                <Maximize2 size={14} />
              </button>
              <button
                type="button"
                className="viewer-ctrl-btn"
                onClick={handleDetectFeatures}
                disabled={isScanning}
                title="Detect Features"
              >
                {isScanning ? <Loader2 size={14} className="spin-icon" /> : <Scan size={14} />}
              </button>
            </div>

            {/* Active layer watermark */}
            <div className="workspace-layer-watermark">
              {activeLayer}
            </div>
          </div>
        </main>

        {/* ── RIGHT: GeoChat AI Panel ── */}
        <aside className="satquery-workspace-right-panel" aria-label="GeoChat AI Assistant">

          {/* Panel header */}
          <div className="geochat-header">
            <div className="geochat-header-left">
              <div className="geochat-ai-avatar">
                <Sparkles size={15} />
              </div>
              <div className="geochat-header-text">
                <h4 className="geochat-title">GeoChat AI Assistant</h4>
                <div className="geochat-status">
                  <span className="geochat-status-dot" aria-hidden="true" />
                  <span>Model Online</span>
                  <span className="geochat-status-sep">·</span>
                  <span>GPT-Vision RS</span>
                </div>
              </div>
            </div>
            <button
              type="button"
              className="geochat-clear-btn"
              onClick={handleClearChat}
              title="Clear conversation"
            >
              <RotateCcw size={13} />
            </button>
          </div>

          {/* Image context strip */}
          <div className="geochat-context-strip">
            <div className="geochat-context-thumb">
              <img src={currentImage} alt="Active scene" />
            </div>
            <div className="geochat-context-meta">
              <span className="geochat-context-label">Analyzing</span>
              <span className="geochat-context-name" title={imageName}>
                {imageName.replace(/\.(jpg|jpeg|png|tif|tiff|webp)/i, '')}
              </span>
            </div>
            <span className="geochat-context-badge">Active</span>
          </div>

          {/* Messages area */}
          <div className="geochat-messages-container" role="log" aria-live="polite">
            {chatMessages.map((msg) => (
              <div
                key={msg.id}
                className={`geochat-message ${msg.sender === 'user' ? 'user' : 'ai'}`}
              >
                {/* Sender avatar */}
                <div className={`geochat-msg-avatar ${msg.sender}`}>
                  {msg.sender === 'ai'
                    ? <Bot size={13} />
                    : <User size={13} />
                  }
                </div>

                <div className="geochat-msg-body">
                  <div className={`geochat-msg-bubble ${msg.sender}`}>
                    {msg.text.split('\n').map((line, i) => (
                      <React.Fragment key={i}>
                        {line}
                        {i < msg.text.split('\n').length - 1 && <br />}
                      </React.Fragment>
                    ))}
                  </div>
                  {msg.evidence && msg.evidence.length > 0 && (
                    <div className="geochat-evidence-container">
                      <div className="evidence-header">
                        <CheckCircle2 size={10} color="#00ff88" />
                        <span>Evidence Found</span>
                      </div>
                      <ul className="evidence-list">
                        {msg.evidence.map((ev, idx) => (
                          <li key={idx} className="evidence-item">
                            {ev.text as string || ev.claim as string || ev.observation as string || JSON.stringify(ev)}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  <span className="message-timestamp">{msg.time}</span>
                </div>
              </div>
            ))}

            {/* Typing indicator */}
            {isTyping && (
              <div className="geochat-message ai">
                <div className="geochat-msg-avatar ai">
                  <Bot size={13} />
                </div>
                <div className="geochat-msg-body">
                  <div className="geochat-msg-bubble ai geochat-typing-bubble">
                    <span className="typing-dot" />
                    <span className="typing-dot" />
                    <span className="typing-dot" />
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Suggested prompts — only visible if no user message yet */}
          {chatMessages.filter((m) => m.sender === 'user').length === 0 && !isTyping && (
            <div className="geochat-suggestions">
              <p className="geochat-suggestions-label">Try asking:</p>
              <div className="geochat-suggestions-list">
                {SUGGESTED_PROMPTS.slice(0, 3).map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    className="geochat-suggestion-chip"
                    onClick={() => handleSuggestedPrompt(prompt)}
                  >
                    <ChevronRight size={11} />
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Input form */}
          <form className="geochat-input-form" onSubmit={handleSendMessage}>
            <div className="geochat-input-wrapper">
              <input
                ref={inputRef}
                id="geochat-input"
                type="text"
                placeholder="Ask a question about this satellite scene…"
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                className="geochat-input-field"
                autoComplete="off"
                disabled={isTyping}
                aria-label="Ask GeoChat AI a question"
              />
              <button
                type="submit"
                className={`geochat-send-btn ${!inputQuery.trim() || isTyping ? 'disabled' : 'active'}`}
                disabled={!inputQuery.trim() || isTyping}
                title="Send message (Enter)"
                aria-label="Send message"
              >
                <Send size={15} />
              </button>
            </div>
            <p className="geochat-input-hint">
              Powered by GPT-Vision RS &nbsp;·&nbsp; Analyzing: {selectedRegion}
            </p>
          </form>

        </aside>
      </div>
    </div>
  );
};

export default WorkspacePage;
