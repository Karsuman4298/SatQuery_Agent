const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

/**
 * Upload an image to the backend and extract metadata.
 */
export async function uploadImage(file: File, sensor?: string, description?: string) {
  const formData = new FormData();
  formData.append("file", file);
  if (sensor) formData.append("sensor", sensor);
  if (description) formData.append("description", description);

  const response = await fetch(`${API_BASE_URL}/images/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || `Upload failed with status ${response.status}`);
  }

  return response.json();
}

/**
 * Create a named region for an image.
 */
export async function createRegion(imageId: string, name: string, pixelBounds: any) {
  const response = await fetch(`${API_BASE_URL}/regions/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      image_id: imageId,
      name,
      pixel_bounds: pixelBounds,
    }),
  });
  if (!response.ok) throw new Error("Failed to create region");
  return response.json();
}

/**
 * List all regions for an image.
 */
export async function listRegions(imageId: string) {
  const response = await fetch(`${API_BASE_URL}/regions/${imageId}`);
  if (!response.ok) throw new Error("Failed to list regions");
  return response.json();
}

/**
 * Returns a configured EventSource for streaming the VQA query.
 */
export function streamQuery(imageId: string, question: string, regionId?: string) {
  const url = new URL(`${API_BASE_URL}/query/`);
  return fetch(url.toString(), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "text/event-stream",
    },
    body: JSON.stringify({
      image_id: imageId,
      region_id: regionId,
      question,
    }),
  });
}



/**
 * Download report url
 */
export function getReportUrl(queryId: string, format: "geojson" | "pdf" = "geojson") {
  return `${API_BASE_URL}/reports/${queryId}?format=${format}`;
}

/**
 * Fetch previous queries for a specific image to restore chat history.
 */
export async function fetchQueries(imageId: string) {
  const response = await fetch(`${API_BASE_URL}/agent/${imageId}`);
  if (!response.ok) throw new Error("Failed to fetch queries");
  return response.json();
}
