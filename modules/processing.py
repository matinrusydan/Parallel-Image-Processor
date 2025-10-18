# modules/processing.py
# CPU-bound image processing functions
from typing import Dict, Tuple
from PIL import Image
import numpy as np
import math
import time
import os

def process_image_file(filepath: str, heavy: bool = False) -> Tuple[str, float, float, float, float]:
    # Proses gambar dari file path: load, resize, hitung rata-rata RGB, return elapsed time.
    # Jika heavy=True, tambah kerja CPU ekstra (GaussianBlur dan histogram).
    start = time.perf_counter()
    try:
        with Image.open(filepath) as img:
            img = img.convert("RGB")
            img = img.resize((128, 128), resample=Image.Resampling.LANCZOS)
            if heavy:
                # Tambah kerja CPU: multiple GaussianBlur
                from PIL import ImageFilter
                img = img.filter(ImageFilter.GaussianBlur(radius=2))
                img = img.filter(ImageFilter.GaussianBlur(radius=1))
                # Hitung histogram (extra computation)
                hist = img.histogram()
                # Lakukan operasi dummy pada histogram
                _ = sum(hist) / len(hist)
            arr = np.array(img, dtype=np.float32)
            avg = arr.mean(axis=(0,1))
        end = time.perf_counter()
        elapsed = end - start
        filename = os.path.basename(filepath)
        return (filename, float(avg[0]), float(avg[1]), float(avg[2]), elapsed)
    except Exception as e:
        end = time.perf_counter()
        elapsed = end - start
        filename = os.path.basename(filepath) if filepath else "<unknown>"
        return (filename, math.nan, math.nan, math.nan, elapsed)
