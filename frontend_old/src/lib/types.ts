export type GeoJsonPolygon = {
  type: "Polygon";
  coordinates: number[][][];
};

export type ImageMetadata = {
  id: string;
  filename: string;
  file_path: string;
  crs?: string;
  bounds?: GeoJsonPolygon;
  resolution_m?: number;
  sensor?: string;
  band_count?: number;
  width_px?: number;
  height_px?: number;
  metadata_json?: Record<string, any>;
  upload_time: string;
};
