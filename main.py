from __future__ import annotations
import argparse
import os
import time
import random
import json
import csv
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from typing import List, Tuple, Dict, Any
from PIL import Image
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---------------------------
# KONFIGURASI AWAL (NIM)
# ---------------------------
NIM = "237006030"  # pastikan string (bila integer, convert ke str)
NAME = "Nama Lengkap Anda"  # Ganti sebelum submit

def parse_nim(nim_str: str) -> Tuple[int,int,int]:
    """
    Ambil dua digit terakhir, dua digit tengah, tiga digit terakhir (robust).
    Jika NIM lebih pendek, pad sebelah kiri dengan nol.
    """
    s = str(nim_str).zfill(9)  # pad ke minimal 9 digit (aman)
    dua_terakhir = int(s[-2:])
    dua_tengah = int(s[3:5])  # "dua digit tengah" interpretasi ambil posisi 4-5 (0-based)
    tiga_terakhir = int(s[-3:])
    num_threads = (dua_terakhir % 4) + 2
    num_processes = (dua_tengah % 3) + 2
    num_data = tiga_terakhir * 10
    return num_threads, num_processes, num_data

NUM_THREADS, NUM_PROCESSES, NUM_DATA = parse_nim(NIM)

# reproducibility
random.seed(int(NIM))
np.random.seed(int(NIM))

# ---------------------------
# UTIL: gambar synthetic
# ---------------------------
def generate_synthetic_images(folder: str, count: int, size=(256,256)) -> None:
    os.makedirs(folder, exist_ok=True)
    for i in range(count):
        # deterministic content per index + seed
        rng = np.random.RandomState(seed=int(NIM) + i)
        arr = (rng.rand(size[1], size[0], 3) * 255).astype(np.uint8)
        img = Image.fromarray(arr, mode="RGB")
        img.save(os.path.join(folder, f"generated_{i:04d}.png"), format="PNG")

# ---------------------------
# I/O (Thread) : baca file => bytes + metadata
# ---------------------------
def load_image_to_bytes(path: str) -> Dict[str, Any]:
    """
    Membaca file gambar ke bytes. Mengembalikan dict:
    { 'filename': ..., 'mode': 'RGB', 'size': (w,h), 'data': bytes }
    Tangani file corrupt dengan melempar Exception ke caller.
    """
    try:
        with Image.open(path) as im:
            im = im.convert("RGB")
            size = im.size  # (w,h)
            # gunakan tobytes untuk serialisasi
            data = im.tobytes()
            return {"filename": os.path.basename(path), "mode": "RGB", "size": size, "data": data}
    except Exception as e:
        raise RuntimeError(f"Failed to load {path}: {e}")

# ---------------------------
# CPU (Process) : reconstruct -> process -> avg color
# ---------------------------
def process_image_bytes(item: Dict[str, Any]) -> Tuple[str, float, float, float]:
    """
    Rekonstruksi image dari bytes, resize ke (128,128), hitung rata-rata R,G,B
    Kembalikan (filename, avg_r, avg_g, avg_b)
    """
    try:
        filename = item["filename"]
        mode = item["mode"]
        size = item["size"]  # (w,h)
        data = item["data"]  # bytes
        # reconstruct
        img = Image.frombytes(mode, size, data)
        img = img.resize((128,128), resample=Image.Resampling.LANCZOS)
        arr = np.array(img, dtype=np.float32)  # shape (h,w,3)
        avg = arr.mean(axis=(0,1))  # [R,G,B]
        return (filename, float(avg[0]), float(avg[1]), float(avg[2]))
    except Exception as e:
        # proses gagal -> return sentinel with NaN
        return (item.get("filename","<unknown>"), float("nan"), float("nan"), float("nan"))

# ---------------------------
# Pipeline Runner
# ---------------------------
def run_configuration(num_threads:int, num_processes:int, file_list:List[str]) -> Dict[str, Any]:
    """
    Menjalankan pipeline: load via threads -> process via process pool
    Mengembalikan dict berisi elapsed_time, throughput, results(list)
    """
    start = time.time()
    loaded = []
    # Step A: load with threads
    with ThreadPoolExecutor(max_workers=num_threads) as tpool:
        futures = { tpool.submit(load_image_to_bytes, p): p for p in file_list }
        for fut in as_completed(futures):
            p = futures[fut]
            try:
                res = fut.result()
                loaded.append(res)
            except Exception as e:
                print(f"[WARN] gagal load {p}: {e}")
    # Step B: process with processes
    processed = []
    with ProcessPoolExecutor(max_workers=num_processes) as ppool:
        futures = { ppool.submit(process_image_bytes, item): item["filename"] for item in loaded }
        for fut in as_completed(futures):
            try:
                processed.append(fut.result())
            except Exception as e:
                print(f"[WARN] proses gagal: {e}")
    end = time.time()
    elapsed = end - start
    count = len(processed)
    throughput = count / elapsed if elapsed>0 else float("inf")
    return {"elapsed": elapsed, "throughput": throughput, "processed": processed, "count": count}

# Serial baseline (no concurrency)
def run_serial(file_list:List[str]) -> Dict[str, Any]:
    start = time.time()
    processed = []
    for p in file_list:
        try:
            item = load_image_to_bytes(p)
            processed.append(process_image_bytes(item))
        except Exception as e:
            print(f"[WARN serial] {p}: {e}")
    end = time.time()
    elapsed = end - start
    count = len(processed)
    throughput = count / elapsed if elapsed>0 else float("inf")
    return {"elapsed": elapsed, "throughput": throughput, "processed": processed, "count": count}

# ---------------------------
# Helper: select files
# ---------------------------
def gather_image_files(folder: str, max_count: int) -> List[str]:
    exts = {'.jpg','.jpeg','.png','.bmp'}
    if not os.path.isdir(folder):
        return []
    files = [os.path.join(folder,f) for f in os.listdir(folder) if os.path.splitext(f)[1].lower() in exts]
    files = sorted(files)
    return files[:max_count]

# ---------------------------
# Save CSV / JSON
# ---------------------------
def save_csv(rows: List[Dict[str,Any]], out_csv: str) -> None:
    header = ["mode","num_threads","num_processes","data_count","time_s","throughput","speedup","efficiency_percent"]
    with open(out_csv, "w", newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for r in rows:
            w.writerow(r)

def save_json(summary: Dict[str,Any], out_json: str) -> None:
    with open(out_json, "w", encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

# ---------------------------
# Plotting
# ---------------------------
def plot_results(csv_rows: List[Dict[str,Any]], out_png: str) -> None:
    modes = [r["mode"] for r in csv_rows]
    times = [float(r["time_s"]) for r in csv_rows]
    speedups = [float(r["speedup"]) for r in csv_rows]
    effs = [float(r["efficiency_percent"]) for r in csv_rows]

    x = range(len(modes))

    plt.figure(figsize=(10,5))
    plt.subplot(1,2,1)
    plt.bar(x, times)
    plt.xticks(x, modes, rotation=30)
    plt.ylabel("Time (s)")
    plt.title("Execution Time per Configuration")

    plt.subplot(1,2,2)
    plt.plot(x, speedups, marker='o', label='Speedup')
    plt.plot(x, effs, marker='x', label='Efficiency (%)')
    plt.xticks(x, modes, rotation=30)
    plt.ylabel("Value")
    plt.title("Speedup & Efficiency")
    plt.legend()

    plt.tight_layout()
    plt.savefig(out_png)
    plt.close()

# ---------------------------
# Main: CLI and orchestrasi
# ---------------------------
def main_cli():
    parser = argparse.ArgumentParser(description="Parallel Image Processor (Thread + ProcessPool)")
    parser.add_argument("--folder", type=str, default="dataset", help="Folder dataset gambar")
    parser.add_argument("--generate", action="store_true", help="Generate synthetic images if folder empty")
    parser.add_argument("--out", type=str, default="results.csv", help="Output CSV file for results")
    args = parser.parse_args()

    folder = args.folder
    out_csv = args.out
    out_json = os.path.splitext(out_csv)[0] + ".json"
    out_plot = os.path.splitext(out_csv)[0] + "_plot.png"

    # Print header (Nama + NIM)
    print("===========================================")
    print(f"Nama : {NAME}")
    print(f"NIM  : {NIM}")
    print("Project: Parallel Image Processor (Thread + ProcessPool)")
    print("===========================================")
    print(f"Computed params -> threads: {NUM_THREADS}, processes: {NUM_PROCESSES}, data: {NUM_DATA}")
    print()

    # ensure dataset exists or generate
    files = gather_image_files(folder, NUM_DATA)
    if len(files) < 1 and args.generate:
        print(f"[INFO] folder '{folder}' kosong/tidak ada. Generating {NUM_DATA} synthetic images...")
        generate_synthetic_images(folder, NUM_DATA, size=(256,256))
        files = gather_image_files(folder, NUM_DATA)

    if len(files) == 0:
        print(f"[ERROR] Tidak ada gambar di folder '{folder}'. Jalankan dengan --generate untuk membuat data uji.")
        return

    # truncate/choose deterministic subset
    files = files[:NUM_DATA]
    data_count = len(files)
    print(f"[INFO] Using {data_count} images from '{folder}'")

    results_rows = []

    # 1) Serial baseline
    print("[RUN] Serial baseline (no concurrency)...")
    t_serial = run_serial(files)
    T_serial = t_serial["elapsed"]
    print(f"  Serial time: {T_serial:.4f} s, throughput: {t_serial['throughput']:.2f} img/s")
    results_rows.append({
        "mode":"serial",
        "num_threads":1,
        "num_processes":1,
        "data_count":data_count,
        "time_s": f"{T_serial:.6f}",
        "throughput": f"{t_serial['throughput']:.6f}",
        "speedup": 1.0,
        "efficiency_percent": 100.0
    })

    # 2) Config from NIM
    print(f"[RUN] Config NIM: threads={NUM_THREADS}, processes={NUM_PROCESSES}")
    cfg_nim = run_configuration(NUM_THREADS, NUM_PROCESSES, files)
    T_nim = cfg_nim["elapsed"]
    speedup_nim = T_serial / T_nim if T_nim>0 else float("inf")
    efficiency_nim = (speedup_nim / max(1, NUM_PROCESSES)) * 100.0
    results_rows.append({
        "mode":"nim_config",
        "num_threads": NUM_THREADS,
        "num_processes": NUM_PROCESSES,
        "data_count": data_count,
        "time_s": f"{T_nim:.6f}",
        "throughput": f"{cfg_nim['throughput']:.6f}",
        "speedup": f"{speedup_nim:.6f}",
        "efficiency_percent": f"{efficiency_nim:.2f}"
    })
    print(f"  Time: {T_nim:.4f} s, throughput: {cfg_nim['throughput']:.2f} img/s, speedup: {speedup_nim:.3f}, efficiency: {efficiency_nim:.2f}%")

    # 3) Alternative config (example)
    alt_threads = max(2, NUM_THREADS*2)
    alt_procs = max(1, NUM_PROCESSES + 1)
    print(f"[RUN] Alternative config: threads={alt_threads}, processes={alt_procs}")
    cfg_alt = run_configuration(alt_threads, alt_procs, files)
    T_alt = cfg_alt["elapsed"]
    speedup_alt = T_serial / T_alt if T_alt>0 else float("inf")
    efficiency_alt = (speedup_alt / max(1, alt_procs)) * 100.0
    results_rows.append({
        "mode":"alt_config",
        "num_threads": alt_threads,
        "num_processes": alt_procs,
        "data_count": data_count,
        "time_s": f"{T_alt:.6f}",
        "throughput": f"{cfg_alt['throughput']:.6f}",
        "speedup": f"{speedup_alt:.6f}",
        "efficiency_percent": f"{efficiency_alt:.2f}"
    })
    print(f"  Time: {T_alt:.4f} s, throughput: {cfg_alt['throughput']:.2f} img/s, speedup: {speedup_alt:.3f}, efficiency: {efficiency_alt:.2f}%")

    # Save CSV and JSON
    save_csv(results_rows, out_csv)
    summary = {
        "name": NAME,
        "nim": NIM,
        "params": {"threads": NUM_THREADS, "processes": NUM_PROCESSES, "data": NUM_DATA},
        "results": results_rows
    }
    save_json(summary, out_json)
    print(f"[OK] Results saved to {out_csv} and {out_json}")

    # Plot
    plot_results(results_rows, out_plot)
    print(f"[OK] Plot saved to {out_plot}")

if __name__ == "__main__":
    main_cli()
