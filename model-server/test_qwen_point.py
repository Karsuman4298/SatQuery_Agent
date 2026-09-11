import asyncio
import base64
import os
import sys

# We need to run localize_region
sys.path.append(os.path.join(os.path.dirname(__file__), "app"))

from app.agent.tools import localize_region

async def main():
    # Read the user's uploaded image (the one with the river)
    # The image path is in the brain directory, but let's just find the original tile if we can.
    # Actually, the user uploaded a screenshot to the chat. Let's use the first uploaded media.
    image_path = "/Users/sumankar/.gemini/antigravity-ide/brain/1584c908-585a-4255-b72a-812c4947aa3d/.user_uploaded/uploaded_media_1789070196617.img"
    
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()
        
    print("Calling Qwen...")
    result = await localize_region(f"data:image/jpeg;base64,{img_b64}", "the river")
    print("Result:", result)

if __name__ == "__main__":
    asyncio.run(main())
