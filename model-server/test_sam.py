import torch
from ultralytics import SAM
import numpy as np
from PIL import Image

img = Image.new("RGB", (256, 256), color="black")
model = SAM('mobile_sam.pt')
res = model(img, bboxes=[50, 50, 100, 100])
print(res)
