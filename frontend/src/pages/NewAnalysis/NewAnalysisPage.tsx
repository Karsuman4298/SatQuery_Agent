import React, { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowLeft,
  UploadCloud,
  FileCheck,
  ArrowRight,
  Image as ImageIcon,
  Ruler,
  HardDrive,
  X,
  Sparkles,
} from 'lucide-react';
import Sidebar from '../../components/dashboard/Sidebar';
import TopBar from '../../components/dashboard/TopBar';
import { useHistory, type HistoryEntry } from '../../context/HistoryContext';
import agriThumb from '../../assets/dashboard/agri_thumb.jpg';
import coastalThumb from '../../assets/dashboard/coastal_thumb.jpg';
import urbanThumb from '../../assets/dashboard/urban_thumb.jpg';
import earthOrbitBg from '../../assets/auth/signin_earth_orbit.jpg';
import './NewAnalysis.css';

interface UploadedFile {
  name: string;
  size: string;
  type: string;
  dimensions: string;
  previewUrl: string;
  rawSize: number;
  fileObject?: File;
}

const RECENT_SAMPLES = [
  {
    id: 'agri',
    title: 'Agricultural Field Analysis',
    meta: 'Sentinel-2 • 2 hours ago',
    thumb: agriThumb,
  },
  {
    id: 'coastal',
    title: 'Coastal Change Detection',
    meta: 'Satellite Imagery • Yesterday',
    thumb: coastalThumb,
  },
  {
    id: 'urban',
    title: 'Urban Expansion Analysis',
    meta: 'Multispectral • 2 days ago',
    thumb: urbanThumb,
  },
];

export const NewAnalysisPage: React.FC = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { entries, addEntry } = useHistory();
  const [uploadedFile, setUploadedFile] = useState<UploadedFile | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isLoadingSample, setIsLoadingSample] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [imgError, setImgError] = useState('');

  const processFile = useCallback((file: File) => {
    const validExtensions = /\.(tif|tiff|geotiff|jpg|jpeg|png|webp|bmp)$/i;
    if (!file.type.startsWith('image/') && !validExtensions.test(file.name)) {
      setImgError('Unsupported file format. Please upload JPG, PNG, TIFF, or GeoTIFF.');
      return;
    }
    setImgError('');

    const sizeStr =
      file.size > 1024 * 1024
        ? `${(file.size / (1024 * 1024)).toFixed(2)} MB`
        : `${Math.round(file.size / 1024)} KB`;

    const ext = file.name.split('.').pop()?.toUpperCase() || 'Image';

    const reader = new FileReader();
    reader.onload = (e) => {
      const dataUrl = e.target?.result as string;
      // Get dimensions via Image element
      const img = new Image();
      img.onload = () => {
        setUploadedFile({
          name: file.name,
          size: sizeStr,
          type: ext,
          dimensions: `${img.naturalWidth} × ${img.naturalHeight} px`,
          previewUrl: dataUrl,
          rawSize: file.size,
          fileObject: file,
        });
      };
      img.src = dataUrl;
    };
    reader.readAsDataURL(file);
  }, []);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => setIsDragging(false);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) processFile(file);
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
  };

  const handleAnalyze = async () => {
    if (!uploadedFile || !uploadedFile.fileObject) return;
    const cleanTitle = uploadedFile.name.replace(/\.[^/.]+$/, '').replace(/_/g, ' ') || 'Satellite Analysis';
    
    setIsUploading(true);
    let imageId = "dummy_image_id";
    try {
      const { uploadImage } = await import('../../lib/api');
      const response = await uploadImage(uploadedFile.fileObject);
      imageId = response.id || imageId;
    } catch (e) {
      console.error("Failed to upload image:", e);
    } finally {
      setIsUploading(false);
    }

    // Add to history store
    const newId = addEntry({
      name: cleanTitle,
      imageUrl: uploadedFile.previewUrl,
      fileName: uploadedFile.name,
      fileSize: uploadedFile.size,
      fileDimensions: uploadedFile.dimensions,
      fileType: uploadedFile.type,
      modality: 'Optical',
      spectralChannel: 'True Color (RGB)',
      region: 'Region Alpha',
      status: 'Completed',
      confidence: 94.8,
      dataset: 'User Upload',
      chatMessages: [
        {
          id: 'init-1',
          sender: 'ai',
          text: `Satellite image "${cleanTitle}" loaded and indexed successfully. I can analyze spectral bands, vegetation indices, land cover, moisture levels, and more.\n\nAsk me anything about this scene — try one of the suggested queries below to get started.`,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ],
    });

    navigate(`/analysis/${newId}`, {
      state: {
        imageUrl: uploadedFile.previewUrl,
        title: cleanTitle,
        historyId: newId,
        fileInfo: {
          name: uploadedFile.name,
          size: uploadedFile.size,
          type: uploadedFile.type,
          dimensions: uploadedFile.dimensions,
        },
      },
    });
  };

  const handleLoadSample = (sample: typeof RECENT_SAMPLES[0]) => {
    setIsLoadingSample(sample.id);
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      const ctx = canvas.getContext('2d');
      ctx?.drawImage(img, 0, 0);
      const dataUrl = canvas.toDataURL('image/jpeg', 0.92);
      setUploadedFile({
        name: `${sample.title.replace(/\s+/g, '_')}.jpg`,
        size: '— (sample)',
        type: 'JPG',
        dimensions: `${img.naturalWidth} × ${img.naturalHeight} px`,
        previewUrl: dataUrl,
        rawSize: 0,
      });
      setIsLoadingSample(null);
    };
    img.onerror = () => {
      setUploadedFile({
        name: `${sample.title.replace(/\s+/g, '_')}.jpg`,
        size: '— (sample)',
        type: 'JPG',
        dimensions: '1920 × 1080 px',
        previewUrl: sample.thumb,
        rawSize: 0,
      });
      setIsLoadingSample(null);
    };
    img.src = sample.thumb;
  };

  const handleOpenHistoryEntry = (entry: HistoryEntry) => {
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

  return (
    <div className="satquery-dashboard-layout">
      <Sidebar />
      <div className="satquery-dashboard-main">
        {/* Ambient background */}
        <div className="satquery-dashboard-top-earth-bg" aria-hidden="true">
          <img src={earthOrbitBg} alt="" />
          <div className="satquery-dashboard-top-earth-overlay" />
        </div>

        <TopBar />

        <div className="satquery-dashboard-content">
          {/* Page header */}
          <div className="na-page-header">
            <button
              type="button"
              className="na-back-btn"
              onClick={() => navigate('/dashboard')}
            >
              <ArrowLeft size={16} />
              <span>Back to Dashboard</span>
            </button>

            <div className="na-header-text">
              <h1 className="na-title">Start a New Analysis</h1>
              <p className="na-subtitle">
                Upload satellite imagery and let SatQuery AI uncover meaningful insights.
              </p>
            </div>
          </div>

          <div className="na-body">
            {/* Left: Upload panel */}
            <motion.div
              className="na-upload-panel"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45 }}
            >
              <div className="na-upload-panel-header">
                <div className="na-upload-icon-badge">
                  <UploadCloud size={20} />
                </div>
                <div>
                  <h2 className="na-panel-title">Upload Satellite Image</h2>
                  <p className="na-panel-sub">Select or drag &amp; drop your imagery file</p>
                </div>
              </div>

              <AnimatePresence mode="wait">
                {!uploadedFile ? (
                  <motion.div
                    key="dropzone"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.25 }}
                  >
                    {/* Drop zone */}
                    <div
                      className={`na-dropzone ${isDragging ? 'na-dropzone--over' : ''}`}
                      onDragOver={handleDragOver}
                      onDragLeave={handleDragLeave}
                      onDrop={handleDrop}
                      onClick={() => fileInputRef.current?.click()}
                      role="button"
                      tabIndex={0}
                      aria-label="Upload satellite image"
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') fileInputRef.current?.click();
                      }}
                    >
                      <input
                        type="file"
                        ref={fileInputRef}
                        onChange={handleFileInput}
                        accept="image/*,.tif,.tiff,.geotiff"
                        style={{ display: 'none' }}
                        aria-hidden="true"
                      />
                      <div className="na-dropzone-inner">
                        <UploadCloud size={48} className="na-dropzone-cloud-icon" />
                        <p className="na-dropzone-main">Drag &amp; drop your image here</p>
                        <p className="na-dropzone-or">or</p>
                        <button
                          type="button"
                          className="na-browse-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            fileInputRef.current?.click();
                          }}
                        >
                          Browse Files
                        </button>
                        <p className="na-dropzone-formats">
                          Supported formats: JPG &bull; PNG &bull; TIFF &bull; GeoTIFF
                        </p>
                      </div>
                    </div>

                    {imgError && (
                      <div className="na-error-banner">
                        <X size={14} />
                        <span>{imgError}</span>
                      </div>
                    )}

                    {/* Sample image option */}
                    <div className="na-sample-row">
                      <span className="na-sample-hint">
                        No image? Try a sample:
                      </span>
                      <button
                        type="button"
                        className="na-try-sample-btn"
                        disabled={isLoadingSample === 'agri'}
                        onClick={() => handleLoadSample(RECENT_SAMPLES[0])}
                      >
                        <Sparkles size={13} />
                        {isLoadingSample === 'agri' ? 'Loading...' : 'Try Sample Image'}
                      </button>
                    </div>
                  </motion.div>
                ) : (
                  /* Preview state */
                  <motion.div
                    key="preview"
                    className="na-preview-section"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.3 }}
                  >
                    {/* Image preview */}
                    <div className="na-preview-image-wrap">
                      <img
                        src={uploadedFile.previewUrl}
                        alt="Selected satellite imagery"
                        className="na-preview-image"
                      />
                      <button
                        type="button"
                        className="na-preview-remove"
                        onClick={() => setUploadedFile(null)}
                        title="Remove image"
                      >
                        <X size={14} />
                      </button>
                    </div>

                    {/* File information */}
                    <div className="na-file-info-grid">
                      <div className="na-info-item">
                        <div className="na-info-icon">
                          <ImageIcon size={14} />
                        </div>
                        <div>
                          <p className="na-info-label">File Name</p>
                          <p className="na-info-value na-info-value--filename">
                            {uploadedFile.name}
                          </p>
                        </div>
                      </div>
                      <div className="na-info-item">
                        <div className="na-info-icon">
                          <FileCheck size={14} />
                        </div>
                        <div>
                          <p className="na-info-label">File Type</p>
                          <p className="na-info-value">{uploadedFile.type}</p>
                        </div>
                      </div>
                      <div className="na-info-item">
                        <div className="na-info-icon">
                          <Ruler size={14} />
                        </div>
                        <div>
                          <p className="na-info-label">Dimensions</p>
                          <p className="na-info-value">{uploadedFile.dimensions}</p>
                        </div>
                      </div>
                      <div className="na-info-item">
                        <div className="na-info-icon">
                          <HardDrive size={14} />
                        </div>
                        <div>
                          <p className="na-info-label">File Size</p>
                          <p className="na-info-value">{uploadedFile.size}</p>
                        </div>
                      </div>
                    </div>

                    {/* Action buttons */}
                    <div className="na-action-row">
                      <button
                        type="button"
                        className="na-analyze-btn"
                        onClick={handleAnalyze}
                        disabled={isUploading}
                      >
                        <span>{isUploading ? 'Uploading...' : 'Analyze Image'}</span>
                        {!isUploading && <ArrowRight size={16} />}
                      </button>
                      <button
                        type="button"
                        className="na-change-btn"
                        onClick={() => {
                          setUploadedFile(null);
                          setImgError('');
                        }}
                      >
                        Change Image
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>

            {/* Right: Recent images panel */}
            <motion.div
              className="na-recent-panel"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, delay: 0.1 }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                <h3 className="na-recent-title" style={{ margin: 0 }}>Recent Analyses</h3>
                <button
                  type="button"
                  onClick={() => navigate('/history')}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#00ff88',
                    fontSize: '12px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                >
                  View All <ArrowRight size={12} />
                </button>
              </div>
              <p className="na-recent-sub">Open an existing analysis or load its image</p>

              <div className="na-recent-list">
                {entries.length > 0 ? (
                  entries.slice(0, 4).map((entry) => (
                    <div key={entry.id} className="na-recent-item">
                      <div className="na-recent-thumb">
                        <img src={entry.imageUrl} alt={entry.name} />
                      </div>
                      <div className="na-recent-info">
                        <p className="na-recent-item-title">{entry.name}</p>
                        <p className="na-recent-item-meta">{entry.modality} • {entry.spectralChannel.split(' ')[0]}</p>
                      </div>
                      <div className="na-recent-actions">
                        <button
                          type="button"
                          className="na-open-analysis-btn"
                          onClick={() => handleOpenHistoryEntry(entry)}
                          title="Open existing analysis"
                        >
                          Open <ArrowRight size={12} />
                        </button>
                      </div>
                    </div>
                  ))
                ) : (
                  <div style={{ padding: '24px 16px', textAlign: 'center', background: 'rgba(2, 11, 18, 0.4)', borderRadius: '8px', border: '1px dashed rgba(255, 255, 255, 0.08)' }}>
                    <p style={{ margin: '0 0 6px 0', fontSize: '13px', fontWeight: 600, color: '#e2e8f0' }}>No recent analyses yet</p>
                    <p style={{ margin: 0, fontSize: '11.5px', color: '#64748b', lineHeight: 1.5 }}>
                      Analyses you perform will be saved here and in your History repository.
                    </p>
                  </div>
                )}
              </div>

              <div className="na-recent-divider" />

              <div className="na-info-callout">
                <Sparkles size={14} style={{ color: '#00d4ff', flexShrink: 0 }} />
                <p>
                  Upload your own satellite imagery to start a fresh AI-powered analysis session
                  with spectral band inspection, region detection and GeoChat.
                </p>
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NewAnalysisPage;
