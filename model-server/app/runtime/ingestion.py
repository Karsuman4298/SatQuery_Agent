"""Deterministic raster ingestion; no language model infers metadata."""
from __future__ import annotations
import hashlib
import io
import json
import math
from pathlib import Path
from uuid import UUID
import numpy as np
import rasterio
from rasterio.io import MemoryFile
from rasterio.enums import Resampling
from rasterio.warp import transform_bounds
from rasterio.windows import Window
from PIL import Image
from app.runtime.contracts import Asset

BENCHMARKS = {'VRSBench', 'RSVQA', 'CDVQA', 'BigEarthNet.txt'}


def encode_preview(src, window=None, max_side=1024):
    width = int(window.width) if window else src.width
    height = int(window.height) if window else src.height
    scale = min(1., max_side / max(width, height))
    indexes = list(range(1, min(3, src.count) + 1))
    pixels = src.read(indexes, window=window, masked=True,
        out_shape=(len(indexes), max(1, round(height * scale)), max(1, round(width * scale))), resampling=Resampling.bilinear)
    channels = []
    for band in pixels:
        raw = band.astype('float32').filled(np.nan)
        valid = np.isfinite(raw)
        out = np.zeros(raw.shape, dtype='uint8')
        if valid.any():
            low, high = np.percentile(raw[valid], [2, 98])
            if src.dtypes[0] == 'uint8': out[valid] = np.clip(raw[valid], 0, 255)
            elif high > low: out[valid] = np.clip((raw[valid] - low) / (high - low) * 255, 0, 255)
            else: out[valid] = 127
        channels.append(out)
    while len(channels) < 3: channels.append(channels[-1])
    buffer = io.BytesIO()
    Image.fromarray(np.stack(channels, axis=-1)).save(buffer, format='PNG')
    return buffer.getvalue()


def ingest(data: bytes, filename: str, owner: str, metadata: dict, objects, records) -> Asset:
    suffix = Path(filename).suffix.lower()
    formats = {'.tif': 'GTiff', '.tiff': 'GTiff', '.png': 'PNG', '.jpg': 'JPEG', '.jpeg': 'JPEG'}
    if suffix not in formats: raise ValueError('Use TIFF/GeoTIFF, or prescribed benchmark PNG/JPEG.')
    if not data or len(data) > 50 * 1024 * 1024: raise ValueError('Image must contain between 1 byte and 50 MB.')
    if suffix not in {'.tif', '.tiff'} and metadata.get('benchmark') not in BENCHMARKS:
        raise ValueError('PNG/JPEG requires a prescribed benchmark source.')
    checksum = hashlib.sha256(data).hexdigest()
    identity = hashlib.sha256((owner + checksum + json.dumps(metadata, sort_keys=True, default=str)).encode()).hexdigest()
    asset_id = UUID(identity[:32])
    try: return Asset.model_validate(records.get(owner, 'asset', str(asset_id)))
    except KeyError: pass
    prefix = hashlib.sha256(owner.encode()).hexdigest()[:24]
    with MemoryFile(data) as memory:
        with memory.open() as src:
            if src.driver != formats[suffix]: raise ValueError('File contents do not match the extension.')
            if not src.count or src.width * src.height > 100_000_000: raise ValueError('Raster exceeds the 100-million-pixel limit or has no bands.')
            if any(not math.isfinite(v) for v in src.transform): raise ValueError('Invalid geotransform.')
            bbox = list(transform_bounds(src.crs, 'EPSG:4326', *src.bounds, densify_pts=21)) if src.crs else None
            asset = Asset(asset_id=asset_id, owner=owner, filename=Path(filename).name, checksum=checksum,
                storage_uri=objects.put(data, f'raw/{prefix}/{asset_id}', suffix.lstrip('.')),
                preview_uri=objects.put(encode_preview(src), f'thumbnails/{prefix}/{asset_id}', 'png'),
                modality=metadata['modality'], sensor=metadata.get('sensor'),
                acquisition_time=metadata.get('acquisition_time'), benchmark=metadata.get('benchmark'),
                processing_level=metadata.get('processing_level'),
                crs=src.crs.to_string() if src.crs else None, transform=list(src.transform)[:6], bbox_geo=bbox,
                width=src.width, height=src.height, dtype=src.dtypes[0], resolution=list(src.res),
                bands=[name or f'band_{i + 1}' for i, name in enumerate(src.descriptions)])
            for y in range(0, src.height, 1024):
                for x in range(0, src.width, 1024):
                    window = Window(x, y, min(1024, src.width - x), min(1024, src.height - y))
                    uri = objects.put(encode_preview(src, window), f'tiles/{prefix}/{asset_id}/{x}/{y}', 'png')
                    asset.tiles.append({'tile_id': f'{asset_id}:{x}:{y}', 'storage_uri': uri,
                                        'bbox_pixel': [x, y, x + int(window.width), y + int(window.height)]})
    records.put(owner, 'asset', str(asset_id), asset.model_dump(mode='json'))
    return asset
