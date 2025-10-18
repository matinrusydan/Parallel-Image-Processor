# modules/io.py
# I/O utilities for image loading and dataset handling
import os
from typing import List, Dict, Any
from PIL import Image
import numpy as np

def gather_image_files(folder: str, max_count: int) -> List[str]:
    # Kumpulkan file gambar dari folder dan ambil hingga max_count.
    exts = {'.jpg','.jpeg','.png','.bmp'}
    if not os.path.isdir(folder):
        return []
    files = [os.path.join(folder,f) for f in os.listdir(folder) if os.path.splitext(f)[1].lower() in exts]
    files = sorted(files)
    return files[:max_count]

def load_image_to_bytes(path: str) -> Dict[str, Any]:
    # Baca gambar dan kembalikan sebagai dict dengan bytes dan metadata.
    try:
        with Image.open(path) as im:
            im = im.convert("RGB")
            size = im.size  # (w,h)
            data = im.tobytes()
            return {"filename": os.path.basename(path), "mode": "RGB", "size": size, "data": data}
    except Exception as e:
        # Lempar exception supaya caller dapat menangani (logging)
        raise RuntimeError(f"Failed to load {path}: {e}")

def get_kaggle_cars_folder(kaggle_path: str) -> str:
    # Cari folder 'cars' di dalam path Kaggle dataset.
    cars_path = os.path.join(kaggle_path, "cars")
    if os.path.isdir(cars_path):
        return cars_path
    # Cari rekursif
    for root, dirs, _ in os.walk(kaggle_path):
        if "cars" in dirs:
            return os.path.join(root, "cars")
    raise FileNotFoundError(f"Folder 'cars' tidak ditemukan di {kaggle_path}")

def generate_synthetic_images(folder: str, count: int, size=(256,256), seed: int = 0) -> None:
    # Buat gambar synthetic untuk testing.
    os.makedirs(folder, exist_ok=True)
    for i in range(count):
        rng = np.random.RandomState(seed=seed + i)
        arr = (rng.rand(size[1], size[0], 3) * 255).astype(np.uint8)
        img = Image.fromarray(arr, mode="RGB")
        img.save(os.path.join(folder, f"generated_{i:04d}.png"), format="PNG")
