// Backend (FastAPI gateway) on port 8000, Model-server on port 8001
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";
const MODEL_SERVER_URL = import.meta.env.VITE_MODEL_SERVER_URL || "http://localhost:8001";

/* ─── Image Upload (to backend gateway) ─────────────────────────────── */
export async function uploadImage(file: File, sensor?: string, description?: string) {
  const formData = new FormData();
  formData.append("file", file);
  if (sensor) formData.append("sensor", sensor);
  if (description) formData.append("description", description);

  const response = await fetch(`${BACKEND_URL}/images/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || `Upload failed with status ${response.status}`);
  }

  return response.json();
}

/* ─── Region CRUD (to backend gateway) ──────────────────────────────── */
export async function createRegion(imageId: string, name: string, pixelBounds: unknown) {
  const response = await fetch(`${BACKEND_URL}/regions/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image_id: imageId, name, pixel_bounds: pixelBounds }),
  });
  if (!response.ok) throw new Error("Failed to create region");
  return response.json();
}

export async function listRegions(imageId: string) {
  const response = await fetch(`${BACKEND_URL}/regions/${imageId}`);
  if (!response.ok) throw new Error("Failed to list regions");
  return response.json();
}

/* ─── Agent Query (to model-server directly) ─────────────────────────
 *  Sends image as base64, receives full JSON response (not SSE).
 *  WorkspacePage converts it into the streaming-like chat format.
 * ────────────────────────────────────────────────────────────────── */
export interface AgentQueryOptions {
  question: string;
  imageBase64?: string;       // primary image
  beforeBase64?: string;      // change-detection: before
  afterBase64?: string;       // change-detection: after
  opticalBase64?: string;     // fusion: optical
  sarBase64?: string;         // fusion: SAR
  regionName?: string;
  clickPoint?: [number, number] | null;
  chatHistory?: { role: "user" | "assistant"; content: string }[];
  metadata?: Record<string, unknown>;
}

export async function queryAgent(opts: AgentQueryOptions): Promise<{
  answer: string;
  tool_used: string;
  confidence: number;
  segment_mask?: string;
  execution_summary?: Record<string, unknown>;
  evidence?: Record<string, unknown>[];
  errors?: unknown[];
}> {
  const body = {
    question: opts.question,
    mode: "vqa",                          // classifier re-routes internally
    image: opts.imageBase64 || "",
    before: opts.beforeBase64 || "",
    after: opts.afterBase64 || "",
    optical: opts.opticalBase64 || "",
    sar: opts.sarBase64 || "",
    region_name: opts.regionName || "",
    click_point: opts.clickPoint || null,
    chat_history: opts.chatHistory || [],
    metadata: opts.metadata || {},
  };

  const response = await fetch(`${MODEL_SERVER_URL}/agent`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => null);
    let errMsg = err?.detail;
    if (Array.isArray(errMsg)) {
      errMsg = errMsg.map((e: any) => e.msg).join(', ');
    }
    throw new Error(errMsg || `Agent query failed: ${response.status}`);
  }

  return response.json();
}

/* ─── Legacy streamQuery shim (kept for compatibility) ──────────────── */
export function streamQuery(imageId: string, question: string, _regionId?: string) {
  // Old SSE path — hits backend gateway
  const url = `${BACKEND_URL}/agent/`;
  return fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({ image_id: imageId, question }),
  });
}

/* ─── Report helpers ─────────────────────────────────────────────────── */
export function getReportUrl(queryId: string, format: "geojson" | "pdf" = "geojson") {
  return `${BACKEND_URL}/reports/${queryId}?format=${format}`;
}

export async function fetchQueries(imageId: string) {
  const response = await fetch(`${BACKEND_URL}/agent/${imageId}`);
  if (!response.ok) throw new Error("Failed to fetch queries");
  return response.json();
}
