import asyncio
import app.agent.tools

# Mock localize_region to return null (None bbox)
async def mock_localize(image, description):
    return {"bbox": None, "internal_reasoning": "Could not confidently locate the region"}

app.agent.tools.localize_region = mock_localize

async def run_test():
    result = await app.agent.tools.segmentation_tool.ainvoke({
        "image": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=",
        "point": None,
        "region_description": "the building on the left"
    })
    
    print("Segmentation Tool Result:", result)
    assert result.get("error") == "please click the region", f"Expected error message, got {result}"
    print("Test passed: missing click + null bbox -> 'please click the region'")

if __name__ == "__main__":
    asyncio.run(run_test())
