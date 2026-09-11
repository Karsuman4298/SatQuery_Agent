import asyncio
import base64
import json
import rasterio
from rasterio.transform import from_origin
import numpy as np

from app.agent.state import GraphState
from app.agent.pipeline import normalize_metadata

def create_dummy_geotiff(filename):
    # Create a 100x100 dummy array
    Z = np.random.randint(0, 255, (3, 100, 100), dtype=np.uint8)
    
    # Define coordinate reference system and transform
    crs = rasterio.crs.CRS.from_epsg(32632) # WGS 84 / UTM zone 32N
    transform = from_origin(500000.0, 4600000.0, 10.0, 10.0) # 10m resolution
    
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
    
    with open(filename, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")
        
    state = GraphState(
        image_context={"image": f"data:image/tiff;base64,{img_b64}"}
    )
    
    # Test normalize_metadata
    state = normalize_metadata(state)
    
    primary_metadata = state.sensor_metadata.get("primary")
    
    output = {
        "file_0": {
            "sensor_metadata": primary_metadata.model_dump() if primary_metadata else None,
        }
    }
        
    with open("/Users/sumankar/.gemini/antigravity-ide/brain/1584c908-585a-4255-b72a-812c4947aa3d/geotiff_verification.json", "w") as f:
        json.dump(output, f, indent=2)

if __name__ == "__main__":
    run_test()
