/**
 * SatQuery AI — Report Generator Utility
 * Produces clean, professional HTML analysis reports from real satellite observation data.
 */

export interface ReportData {
  id: string;
  title: string;
  imageUrl?: string;
  fileName?: string;
  fileSize?: string;
  fileDimensions?: string;
  fileType?: string;
  modality?: string;
  spectralChannel?: string;
  region?: string;
  confidence?: number;
  dataset?: string;
  createdAt?: string;
  chatMessages?: Array<{
    id: string;
    sender: 'ai' | 'user';
    text: string;
    time: string;
  }>;
  detectedRegions?: Array<{
    name: string;
    type: string;
    score: string;
  }>;
}

export function generateReportHtml(data: ReportData): string {
  const now = new Date();
  const createdDate = data.createdAt ? new Date(data.createdAt) : now;
  const dateStr = createdDate.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
  const timeStr = createdDate.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
  });
  const sceneTitle = (data.title || 'Satellite Observation').replace(/\.(jpg|jpeg|png|tif|tiff|webp)/i, '');

  const userMessages = (data.chatMessages || []).filter((m) => m.sender === 'user');
  const chatTranscriptHtml = (data.chatMessages || [])
    .slice(1) // skip welcome message if desired
    .map((m) => {
      const role = m.sender === 'ai' ? '🤖 GeoChat AI' : '👤 Analyst';
      const bubbleColor =
        m.sender === 'ai'
          ? 'background:#0d1f2d;border-left:3px solid #00d4ff;'
          : 'background:#0a1f0a;border-left:3px solid #00ff88;';
      return `<div style="${bubbleColor}padding:10px 14px;border-radius:6px;margin-bottom:10px;">
        <div style="font-size:11px;color:#64748b;margin-bottom:4px;">${role} · ${m.time}</div>
        <div style="font-size:13px;color:#e2e8f0;line-height:1.6;">${m.text.replace(/\n/g, '<br/>')}</div>
      </div>`;
    })
    .join('');

  const regions = data.detectedRegions || [];
  const regionRows = regions.length > 0
    ? regions
        .map(
          (r) =>
            `<tr><td style="padding:10px 14px;color:#e2e8f0;font-weight:600;">${r.name}</td><td style="padding:10px 14px;color:#94a3b8;">${r.type}</td><td style="padding:10px 14px;color:#00ff88;font-weight:700;">${r.score}</td></tr>`
        )
        .join('')
    : `<tr><td colspan="3" style="padding:14px;color:#64748b;text-align:center;font-size:12.5px;">No detected region subsets recorded for this scene.</td></tr>`;

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>SatQuery AI — Analysis Report: ${sceneTitle}</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: #020b12;
      color: #e2e8f0;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      padding: 40px 32px;
      line-height: 1.5;
    }
    .container { max-width: 900px; margin: 0 auto; }
    .report-header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      border-bottom: 1px solid rgba(0, 212, 255, 0.2);
      padding-bottom: 24px;
      margin-bottom: 32px;
    }
    .brand-title { font-size: 24px; font-weight: 800; color: #ffffff; letter-spacing: -0.02em; }
    .brand-title span { color: #00ff88; }
    .brand-sub { font-size: 13px; color: #94a3b8; margin-top: 3px; }
    .badge-verified {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: rgba(0, 255, 136, 0.1);
      border: 1px solid rgba(0, 255, 136, 0.3);
      color: #00ff88;
      padding: 4px 12px;
      border-radius: 20px;
      font-size: 11px;
      font-weight: 700;
      margin-top: 8px;
    }
    .meta-box { text-align: right; font-size: 12.5px; color: #64748b; line-height: 1.8; }
    .meta-id { color: #00d4ff; font-family: monospace; font-size: 12px; }
    h2 {
      font-size: 13px;
      font-weight: 700;
      color: #00d4ff;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      margin-bottom: 12px;
    }
    .section { margin-bottom: 28px; }
    .card {
      background: rgba(10, 25, 41, 0.7);
      border: 1px solid rgba(0, 212, 255, 0.12);
      border-radius: 10px;
      padding: 20px;
    }
    .info-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
      margin-top: 14px;
    }
    @media (max-width: 680px) {
      .info-grid { grid-template-columns: 1fr; }
      .report-header { flex-direction: column; gap: 16px; }
      .meta-box { text-align: left; }
    }
    .info-item {
      background: rgba(2, 11, 18, 0.6);
      border: 1px solid rgba(255, 255, 255, 0.05);
      border-radius: 8px;
      padding: 12px 14px;
    }
    .info-label {
      font-size: 10.5px;
      color: #64748b;
      margin-bottom: 4px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      font-weight: 600;
    }
    .info-val { font-size: 14px; font-weight: 600; color: #ffffff; }
    .info-val.cyan { color: #00d4ff; }
    .info-val.green { color: #00ff88; }
    table { width: 100%; border-collapse: collapse; }
    th {
      text-align: left;
      padding: 10px 14px;
      font-size: 11px;
      color: #64748b;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }
    td { border-bottom: 1px solid rgba(255, 255, 255, 0.04); }
    .scene-img-wrap {
      max-width: 100%;
      border-radius: 8px;
      overflow: hidden;
      border: 1px solid rgba(0, 212, 255, 0.2);
      background: #020b12;
    }
    .scene-img { width: 100%; max-height: 420px; object-fit: contain; display: block; }
    .footer {
      text-align: center;
      color: #475569;
      font-size: 11.5px;
      padding-top: 24px;
      border-top: 1px solid rgba(255, 255, 255, 0.06);
      margin-top: 36px;
    }
  </style>
</head>
<body>
  <div class="container">
    <header class="report-header">
      <div>
        <div class="brand-title">SatQuery <span>AI</span></div>
        <div class="brand-sub">Satellite Observation &amp; Multimodal Geospatial Analysis</div>
        <div class="badge-verified">✓ Verified Satellite Analysis Report</div>
      </div>
      <div class="meta-box">
        <div><strong>Date:</strong> ${dateStr}</div>
        <div><strong>Time:</strong> ${timeStr}</div>
        <div><strong>Report ID:</strong> <span class="meta-id">${data.id}</span></div>
      </div>
    </header>

    <main>
      <!-- Analysis Overview -->
      <section class="section">
        <h2>Analysis Overview</h2>
        <div class="card">
          <div style="font-size: 19px; font-weight: 700; color: #fff;">${sceneTitle}</div>
          <div class="info-grid">
            <div class="info-item">
              <div class="info-label">Imagery Modality</div>
              <div class="info-val cyan">${data.modality || 'Optical'}</div>
            </div>
            <div class="info-item">
              <div class="info-label">Active Channel</div>
              <div class="info-val">${data.spectralChannel || 'True Color (RGB)'}</div>
            </div>
            <div class="info-item">
              <div class="info-label">Target Region</div>
              <div class="info-val green">${data.region || 'Entire Scene'}</div>
            </div>
            <div class="info-item">
              <div class="info-label">Dataset / Source</div>
              <div class="info-val">${data.dataset || 'User Imagery'}</div>
            </div>
            ${data.confidence ? `
            <div class="info-item">
              <div class="info-label">AI Confidence</div>
              <div class="info-val green">${data.confidence}%</div>
            </div>` : ''}
            ${data.fileDimensions ? `
            <div class="info-item">
              <div class="info-label">Image Dimensions</div>
              <div class="info-val">${data.fileDimensions}</div>
            </div>` : ''}
            ${data.fileSize ? `
            <div class="info-item">
              <div class="info-label">File Size</div>
              <div class="info-val">${data.fileSize}</div>
            </div>` : ''}
            ${data.fileName ? `
            <div class="info-item">
              <div class="info-label">File Name</div>
              <div class="info-val" style="font-size: 12px; word-break: break-all;">${data.fileName}</div>
            </div>` : ''}
          </div>
        </div>
      </section>

      <!-- Detected Regions -->
      <section class="section">
        <h2>Detected Regions</h2>
        <div class="card">
          <table>
            <thead>
              <tr>
                <th>Region Name</th>
                <th>Classification</th>
                <th>Confidence</th>
              </tr>
            </thead>
            <tbody>
              ${regionRows}
            </tbody>
          </table>
        </div>
      </section>

      <!-- GeoChat Insights -->
      ${data.chatMessages && data.chatMessages.length > 1 ? `
      <section class="section">
        <h2>GeoChat AI Session (${userMessages.length} quer${userMessages.length === 1 ? 'y' : 'ies'})</h2>
        <div class="card">
          ${chatTranscriptHtml || '<p style="color:#64748b;font-size:13px;">No interactive queries recorded.</p>'}
        </div>
      </section>` : ''}

      <!-- Scene Imagery Preview -->
      ${data.imageUrl ? `
      <section class="section">
        <h2>Satellite Scene Preview</h2>
        <div class="card">
          <div class="scene-img-wrap">
            <img src="${data.imageUrl}" alt="Satellite Analysis Scene" class="scene-img" />
          </div>
        </div>
      </section>` : ''}
    </main>

    <footer class="footer">
      Generated by SatQuery AI &bull; Satellite Intelligence &bull; ${dateStr} at ${timeStr}<br />
      &copy; ${now.getFullYear()} SatQuery AI Platform
    </footer>
  </div>
</body>
</html>`;
}

export function downloadReportHtmlFile(data: ReportData): void {
  const htmlContent = generateReportHtml(data);
  const blob = new Blob([htmlContent], { type: 'text/html;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  const sanitizedTitle = (data.title || 'Analysis').replace(/[^a-zA-Z0-9_-]/g, '_');
  const now = new Date();
  const dateStamp = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}`;
  a.href = url;
  a.download = `SatQuery_Report_${sanitizedTitle}_${dateStamp}.html`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
