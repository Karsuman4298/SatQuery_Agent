-- ═══════════════════════════════════════════════════════════
-- SatQuery Database Schema — Initial Setup
-- Runs automatically on first PostgreSQL container startup
-- ═══════════════════════════════════════════════════════════

-- Extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── Images ────────────────────────────────────────────────
CREATE TABLE images (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename        TEXT NOT NULL,
    file_path       TEXT NOT NULL,
    crs             TEXT,
    bounds          GEOMETRY(Polygon, 4326),
    resolution_m    DOUBLE PRECISION,
    sensor          TEXT,
    band_count      INTEGER,
    width_px        INTEGER,
    height_px       INTEGER,
    metadata_json   JSONB,
    upload_time     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_images_bounds ON images USING GIST (bounds);
CREATE INDEX idx_images_sensor ON images (sensor);
CREATE INDEX idx_images_upload_time ON images (upload_time DESC);

-- ─── Regions ───────────────────────────────────────────────
CREATE TABLE regions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    image_id        UUID NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    geometry        GEOMETRY(Polygon, 4326),
    pixel_bounds    JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_regions_image_id ON regions (image_id);
CREATE INDEX idx_regions_geom ON regions USING GIST (geometry);

-- ─── Queries ───────────────────────────────────────────────
CREATE TABLE queries (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    image_id        UUID NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    region_id       UUID REFERENCES regions(id) ON DELETE SET NULL,
    question        TEXT NOT NULL,
    answer          TEXT,
    confidence      DOUBLE PRECISION,
    evidence        JSONB,
    execution_trace JSONB,
    model_used      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_queries_image_id ON queries (image_id);
CREATE INDEX idx_queries_region_id ON queries (region_id);
CREATE INDEX idx_queries_created_at ON queries (created_at DESC);

-- ─── Change Detection Results ──────────────────────────────
CREATE TABLE change_results (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    before_image_id     UUID NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    after_image_id      UUID NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    change_mask_path    TEXT,
    change_mask_url     TEXT,
    change_pct          DOUBLE PRECISION,
    status              TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    error_message       TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMPTZ
);

CREATE INDEX idx_change_before ON change_results (before_image_id);
CREATE INDEX idx_change_after ON change_results (after_image_id);
CREATE INDEX idx_change_status ON change_results (status);
CREATE UNIQUE INDEX idx_change_pair ON change_results (before_image_id, after_image_id);

-- ─── Impact Statistics ─────────────────────────────────────
CREATE TABLE impact_stats (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    change_result_id        UUID NOT NULL REFERENCES change_results(id) ON DELETE CASCADE,
    affected_population     INTEGER,
    affected_buildings      INTEGER,
    affected_roads_km       DOUBLE PRECISION,
    affected_area_sqkm      DOUBLE PRECISION,
    data_sources            JSONB,
    computed_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_impact_change ON impact_stats (change_result_id);

-- ─── Reports ───────────────────────────────────────────────
CREATE TABLE reports (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query_id        UUID REFERENCES queries(id) ON DELETE SET NULL,
    change_id       UUID REFERENCES change_results(id) ON DELETE SET NULL,
    format          TEXT NOT NULL DEFAULT 'geojson'
                    CHECK (format IN ('geojson', 'pdf')),
    file_path       TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT reports_source_check CHECK (query_id IS NOT NULL OR change_id IS NOT NULL)
);

CREATE INDEX idx_reports_query ON reports (query_id);
CREATE INDEX idx_reports_change ON reports (change_id);
