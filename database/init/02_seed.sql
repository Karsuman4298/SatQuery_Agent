-- ═══════════════════════════════════════════════════════════
-- SatQuery Seed Data
-- Inserts sample images and regions for local development
-- ═══════════════════════════════════════════════════════════

-- Sample image 1: Urban area (simulating Sentinel-2)
INSERT INTO images (id, filename, file_path, crs, bounds, resolution_m, sensor, band_count, width_px, height_px, metadata_json)
VALUES (
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    'urban_sentinel2_sample.tif',
    '/app/uploads/urban_sentinel2_sample.tif',
    'EPSG:4326',
    ST_GeomFromText('POLYGON((77.55 12.95, 77.65 12.95, 77.65 13.05, 77.55 13.05, 77.55 12.95))', 4326),
    10.0,
    'Sentinel-2',
    4,
    1024,
    1024,
    '{"driver": "GTiff", "dtype": "uint16", "nodata": 0}'
);

-- Sample image 2: Same area, later date (for temporal pair)
INSERT INTO images (id, filename, file_path, crs, bounds, resolution_m, sensor, band_count, width_px, height_px, metadata_json)
VALUES (
    'b2c3d4e5-f6a7-8901-bcde-f12345678901',
    'urban_sentinel2_after.tif',
    '/app/uploads/urban_sentinel2_after.tif',
    'EPSG:4326',
    ST_GeomFromText('POLYGON((77.55 12.95, 77.65 12.95, 77.65 13.05, 77.55 13.05, 77.55 12.95))', 4326),
    10.0,
    'Sentinel-2',
    4,
    1024,
    1024,
    '{"driver": "GTiff", "dtype": "uint16", "nodata": 0}'
);

-- Sample image 3: SAR image (for optical-SAR fusion)
INSERT INTO images (id, filename, file_path, crs, bounds, resolution_m, sensor, band_count, width_px, height_px, metadata_json)
VALUES (
    'c3d4e5f6-a7b8-9012-cdef-123456789012',
    'urban_sar_sample.tif',
    '/app/uploads/urban_sar_sample.tif',
    'EPSG:4326',
    ST_GeomFromText('POLYGON((77.55 12.95, 77.65 12.95, 77.65 13.05, 77.55 13.05, 77.55 12.95))', 4326),
    5.0,
    'SAR',
    1,
    2048,
    2048,
    '{"driver": "GTiff", "dtype": "float32", "nodata": -9999}'
);

-- Sample regions on image 1
INSERT INTO regions (image_id, name, pixel_bounds)
VALUES
    ('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'Region A — City Center', '{"x_min": 200, "y_min": 200, "x_max": 600, "y_max": 600}'),
    ('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'Region B — Industrial Zone', '{"x_min": 600, "y_min": 100, "x_max": 900, "y_max": 400}'),
    ('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'Region C — River Area', '{"x_min": 100, "y_min": 700, "x_max": 500, "y_max": 950}');
