# modules/processing.py
# CPU-bound image processing functions
from typing import Dict, Tuple
from PIL import Image
import numpy as np
import math

def process_image_bytes(item: Dict) -> Tuple[str, float, float, float]:
    # Proses gambar dari bytes: resize ke 128x128 dan hitung rata-rata warna RGB.
    try:
        filename = item.get("filename", "<unknown>")
        mode = item.get("mode", "RGB")
        size = item.get("size", None)
        data = item.get("data", None)
        if size is None or data is None:
            return (filename, math.nan, math.nan, math.nan)
        img = Image.frombytes(mode, size, data)
        img = img.resize((128, 128), resample=Image.Resampling.LANCZOS)
        arr = np.array(img, dtype=np.float32)
        avg = arr.mean(axis=(0,1))
        return (filename, float(avg[0]), float(avg[1]), float(avg[2]))
    except Exception:
        return (item.get("filename","<unknown>"), math.nan, math.nan, math.nan)
