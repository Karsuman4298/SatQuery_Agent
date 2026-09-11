import json
import asyncio
from app.services.image_service import extract_metadata
import rasterio
from rasterio.transform import from_origin
import numpy as np

def create_dummy_geotiff(filename):
    Z = np.random.randint(0, 255, (3, 100, 100), dtype=np.uint8)
    crs = rasterio.crs.CRS.from_epsg(32632) 
    transform = from_origin(500000.0, 4600000.0, 10.0, 10.0) 
    with rasterio.open(
        filename,
        'w',
        driver='GTiff',
        height=Z.shape[1],
        width=Z.shape[2],
        count=3,
        dtype=Z.dtype,
        crs=crs,
        transform=transform,
    ) as dst:
        dst.write(Z)

def run_test():
    filename = "dummy_geotiff.tif"
    create_dummy_geotiff(filename)
    
    metadata = extract_metadata(filename)
    
    # Remove geoalchemy WKTElement because it's not JSON serializable easily
    if "bounds" in metadata:
        metadata["bounds"] = str(metadata["bounds"])
        
    with open("/app/geotiff_verification.json", "w") as f:
        json.dump({"dummy_geotiff": metadata}, f, indent=2)

if __name__ == "__main__":
    run_test()
