import base64
import json
import os

images = ["vqa_screenshot.png", "change_detection_screenshot.png", "fusion_screenshot.png"]
md = "## Screenshots\n\n"
for img in images:
    if os.path.exists(img):
        # copy to artifacts
        os.system(f"cp {img} /Users/sumankar/.gemini/antigravity-ide/brain/1584c908-585a-4255-b72a-812c4947aa3d/{img}")
        md += f"![{img}](/Users/sumankar/.gemini/antigravity-ide/brain/1584c908-585a-4255-b72a-812c4947aa3d/{img})\n\n"

with open("/Users/sumankar/.gemini/antigravity-ide/brain/1584c908-585a-4255-b72a-812c4947aa3d/screens.md", "w") as f:
    f.write(md)
