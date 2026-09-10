"""
SQLAlchemy ORM models matching contracts/schema.sql.
Uses GeoAlchemy2 for PostGIS geometry columns.
"""

import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Double,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class ImageModel(Base):
    __tablename__ = "images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(Text, nullable=False)
    file_path = Column(Text, nullable=False)
    crs = Column(Text)
    bounds = Column(Geometry("POLYGON", srid=4326))
    resolution_m = Column(Double)
    sensor = Column(Text)
    band_count = Column(Integer)
    width_px = Column(Integer)
    height_px = Column(Integer)
    metadata_json = Column(JSONB)
    upload_time = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationships
    regions = relationship("RegionModel", back_populates="image", cascade="all, delete-orphan")
    queries = relationship("QueryModel", back_populates="image", cascade="all, delete-orphan")


class RegionModel(Base):
    __tablename__ = "regions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    image_id = Column(UUID(as_uuid=True), ForeignKey("images.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    geometry = Column(Geometry("POLYGON", srid=4326))
    pixel_bounds = Column(JSONB)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationships
    image = relationship("ImageModel", back_populates="regions")


class QueryModel(Base):
    __tablename__ = "queries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    image_id = Column(UUID(as_uuid=True), ForeignKey("images.id", ondelete="CASCADE"), nullable=False)
    region_id = Column(UUID(as_uuid=True), ForeignKey("regions.id", ondelete="SET NULL"))
    question = Column(Text, nullable=False)
    answer = Column(Text)
    confidence = Column(Double)
    evidence = Column(JSONB)
    execution_trace = Column(JSONB)
    model_used = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationships
    image = relationship("ImageModel", back_populates="queries")
    region = relationship("RegionModel")


class ChangeResultModel(Base):
    __tablename__ = "change_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    before_image_id = Column(UUID(as_uuid=True), ForeignKey("images.id", ondelete="CASCADE"), nullable=False)
    after_image_id = Column(UUID(as_uuid=True), ForeignKey("images.id", ondelete="CASCADE"), nullable=False)
    change_mask_path = Column(Text)
    change_mask_url = Column(Text)
    change_pct = Column(Double)
    status = Column(Text, nullable=False, default="pending")
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime(timezone=True))

    # Relationships
    before_image = relationship("ImageModel", foreign_keys=[before_image_id])
    after_image = relationship("ImageModel", foreign_keys=[after_image_id])
    impact_stats = relationship("ImpactStatsModel", back_populates="change_result", uselist=False)

    __table_args__ = (
        UniqueConstraint("before_image_id", "after_image_id", name="idx_change_pair"),
        CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed')", name="ck_change_status"),
    )


class ImpactStatsModel(Base):
    __tablename__ = "impact_stats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    change_result_id = Column(
        UUID(as_uuid=True),
        ForeignKey("change_results.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    affected_population = Column(Integer)
    affected_buildings = Column(Integer)
    affected_roads_km = Column(Double)
    affected_area_sqkm = Column(Double)
    data_sources = Column(JSONB)
    computed_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationships
    change_result = relationship("ChangeResultModel", back_populates="impact_stats")


class ReportModel(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_id = Column(UUID(as_uuid=True), ForeignKey("queries.id", ondelete="SET NULL"))
    change_id = Column(UUID(as_uuid=True), ForeignKey("change_results.id", ondelete="SET NULL"))
    format = Column(Text, nullable=False, default="geojson")
    file_path = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("query_id IS NOT NULL OR change_id IS NOT NULL", name="reports_source_check"),
        CheckConstraint("format IN ('geojson', 'pdf')", name="ck_report_format"),
    )
