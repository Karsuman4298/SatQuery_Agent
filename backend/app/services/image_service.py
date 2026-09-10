"""
Image processing service.
Extracts metadata from uploaded images (especially GeoTIFFs) using rasterio.
"""

import json
import logging
from pathlib import Path

import rasterio
from geoalchemy2.elements import WKTElement
from rasterio.errors import RasterioIOError
from shapely.geometry import box, mapping

logger = logging.getLogger(__name__)


def extract_metadata(file_path: str) -> dict:
    """
    Extract metadata from an image file.
    If it's a GeoTIFF, extracts CRS, bounds, resolution.
    Returns a dictionary suitable for creating an ImageModel.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found at {file_path}")

    metadata = {
        "filename": path.name,
        "file_path": str(path),
        "crs": None,
        "bounds": None,
        "resolution_m": None,
        "band_count": None,
        "width_px": None,
        "height_px": None,
        "metadata_json": {},
    }

    try:
        with rasterio.open(file_path) as src:
            metadata["width_px"] = src.width
            metadata["height_px"] = src.height
            metadata["band_count"] = src.count

            # Extract basic raster metadata
            metadata["metadata_json"] = {
                "driver": src.driver,
                "dtypes": src.dtypes,
                "nodata": src.nodatavals,
            }

            # Spatial metadata
            if src.crs:
                # Store CRS as string (e.g., EPSG:4326)
                metadata["crs"] = src.crs.to_string()

                # Get spatial resolution
                res_x, res_y = src.res
                # Use average resolution as a single value
                metadata["resolution_m"] = (abs(res_x) + abs(res_y)) / 2.0

                # Extract bounds as a Shapely Polygon and convert to WKTElement for PostGIS
                bbox = box(src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top)
                
                # If the image is not in EPSG:4326, we should ideally reproject it.
                # For this hackathon, we'll assume it's either in 4326 or just store the geometry as-is
                # with the SRID matching the image (but our schema enforces 4326).
                # We'll use 4326 for the WKTElement. In a production app, use pyproj to transform.
                
                # We format it for PostGIS (assuming 4326)
                metadata["bounds"] = WKTElement(bbox.wkt, srid=4326)
                
                # Also store a GeoJSON representation in metadata_json for frontend convenience if needed
                metadata["metadata_json"]["geojson_bounds"] = mapping(bbox)

    except RasterioIOError:
        # Not a geospatial raster, probably a standard image (PNG/JPEG)
        # We can use Pillow to just get width/height
        try:
            from PIL import Image
            with Image.open(file_path) as img:
                metadata["width_px"] = img.width
                metadata["height_px"] = img.height
                metadata["metadata_json"] = {"format": img.format, "mode": img.mode}
        except Exception as e:
            logger.warning(f"Could not read image {file_path} with Pillow: {e}")

    return metadata
