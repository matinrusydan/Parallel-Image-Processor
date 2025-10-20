# modules/utils.py
# Fungsi utilitas untuk parsing NIM, simpan output, dan plotting
import statistics
import json
import csv
from typing import List, Dict, Any, Tuple
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os

def parse_nim(nim_str: str):
    # Parse NIM untuk dapatkan parameter paralel
    s = str(nim_str).zfill(9)
    dua_terakhir = int(s[-2:])
    dua_tengah = int(s[3:5])
    tiga_terakhir = int(s[-3:])
    num_threads = (dua_terakhir % 4) + 2
    num_processes = (dua_tengah % 3) + 2
    num_data = tiga_terakhir * 10
    return num_threads, num_processes, num_data, dua_terakhir, dua_tengah, tiga_terakhir

def save_csv(rows: List[Dict[str,Any]], out_csv: str) -> None:
    # Simpan hasil ke CSV
    header = ["mode","num_threads","num_processes","data_count","time_s","throughput","speedup","efficiency_percent"]
    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
    with open(out_csv, "w", newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for r in rows:
            w.writerow(r)

def save_json(summary: Dict[str,Any], out_json: str) -> None:
    # Simpan summary ke JSON
    os.makedirs(os.path.dirname(out_json) or ".", exist_ok=True)
    with open(out_json, "w", encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

def compute_global_avg(per_image_avgs: List[Tuple[float, float, float]]) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    # Hitung rata-rata global dan stddev per channel
    if not per_image_avgs:
        return ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    import numpy as np
    avgs = np.array(per_image_avgs)
    means = avgs.mean(axis=0)
    stds = avgs.std(axis=0)
    return ((means[0], means[1], means[2]), (stds[0], stds[1], stds[2]))

def audit_color_variation(per_image_avgs: List[Tuple[float, float, float]], threshold: float = 1.0) -> bool:
    # Audit variasi warna dataset
    _, stds = compute_global_avg(per_image_avgs)
    return all(s > threshold for s in stds)

def plot_results(csv_rows: List[Dict[str,Any]], out_png: str) -> None:
    # Buat plot hasil eksekusi
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

def plot_experiments(results: List[Dict[str, Any]], out_dir: str) -> None:
    # Buat plot untuk eksperimen
    import os
    os.makedirs(out_dir, exist_ok=True)

    # Plot 1: Time vs Threads
    thread_data = {}
    for r in results:
        t = r["threads"]
        if t not in thread_data:
            thread_data[t] = []
        thread_data[t].append(r["time_s"])
    threads = sorted(thread_data.keys())
    times = [statistics.mean(thread_data[t]) for t in threads]

    plt.figure()
    plt.plot(threads, times, marker='o')
    plt.xlabel("Jumlah Thread")
    plt.ylabel("Waktu (s)")
    plt.title("Time vs Jumlah Thread")
    plt.grid(True)
    plt.savefig(os.path.join(out_dir, "time_vs_threads.png"))
    plt.close()

    # Plot 2: Time vs Processes
    process_data = {}
    for r in results:
        p = r["processes"]
        if p not in process_data:
            process_data[p] = []
        process_data[p].append(r["time_s"])
    processes = sorted(process_data.keys())
    times_p = [statistics.mean(process_data[p]) for p in processes]

    plt.figure()
    plt.plot(processes, times_p, marker='o')
    plt.xlabel("Jumlah Process")
    plt.ylabel("Waktu (s)")
    plt.title("Time vs Jumlah Process")
    plt.grid(True)
    plt.savefig(os.path.join(out_dir, "time_vs_processes.png"))
    plt.close()

    # Plot 3: Speedup vs Config
    labels = [r["label"] for r in results]
    speedups = [r["speedup"] for r in results]
    best_idx = speedups.index(max(speedups))

    plt.figure()
    plt.bar(labels, speedups)
    plt.xlabel("Konfigurasi")
    plt.ylabel("Speedup")
    plt.title("Speedup vs Konfigurasi")
    plt.xticks(rotation=45)
    plt.annotate(f"Best: {labels[best_idx]}", xy=(best_idx, speedups[best_idx]), xytext=(best_idx-0.5, speedups[best_idx]+0.1))
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "speedup_vs_config.png"))
    plt.close()

def save_experiments_csv(results: List[Dict[str, Any]], out_csv: str) -> None:
    # Simpan hasil eksperimen ke CSV
    header = ["No", "Jumlah Thread", "Jumlah Process", "Data/Task", "Waktu (s)", "Speedup", "Efisiensi (%)", "Avg RGB", "Warna"]
    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
    with open(out_csv, "w", newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(header)
        for i, r in enumerate(results, 1):
            avg_rgb_str = f"rgb({r['avg_rgb'][0]:.1f},{r['avg_rgb'][1]:.1f},{r['avg_rgb'][2]:.1f})"
            w.writerow([i, r["threads"], r["processes"], r["data_count"], f"{r['time_s']:.6f}", f"{r['speedup']:.6f}", f"{r['efficiency_percent']:.2f}", avg_rgb_str, r["color_name"]])

def save_experiments_json(results: List[Dict[str, Any]], out_json: str) -> None:
    # Simpan hasil eksperimen ke JSON
    os.makedirs(os.path.dirname(out_json) or ".", exist_ok=True)
    with open(out_json, "w", encoding='utf-8') as f:
        json.dump({"experiments": results}, f, indent=2)

# Color palette for nearest color lookup
COLOR_PALETTE = {
    "Hitam": (0, 0, 0),
    "Putih": (255, 255, 255),
    "Merah": (255, 0, 0),
    "Hijau": (0, 128, 0),
    "Biru": (0, 0, 255),
    "Kuning": (255, 255, 0),
    "Oranye": (255, 165, 0),
    "Magenta": (255, 0, 255),
    "Cyan": (0, 255, 255),
    "Abu-abu": (128, 128, 128),
    "Coklat": (150, 75, 0),
    "Ungu": (128, 0, 128),
    "Pink": (255, 192, 203),
    "Krem": (240, 234, 214)
}

def color_name_from_rgb(rgb: Tuple[float, float, float]) -> Tuple[str, Tuple[int, int, int]]:
    # Compute nearest color by Euclidean distance
    r_i, g_i, b_i = int(round(rgb[0])), int(round(rgb[1])), int(round(rgb[2]))
    best_name = "Hitam"  # Default to avoid None
    best_dist = float('inf')
    for name, (pr, pg, pb) in COLOR_PALETTE.items():
        dist = (r_i - pr) ** 2 + (g_i - pg) ** 2 + (b_i - pb) ** 2
        if dist < best_dist:
            best_dist = dist
            best_name = name
    return best_name, (r_i, g_i, b_i)

def print_experiments_table(results: List[Dict[str, Any]]) -> str:
    # Cetak tabel ASCII untuk eksperimen
    table = []
    table.append("No | Jumlah Thread | Jumlah Process | Data/Task | Waktu (s) | Speedup | Efisiensi (%) | Avg RGB              | Warna")
    table.append("-" * 120)
    for i, r in enumerate(results, 1):
        avg_rgb_str = f"rgb({r['avg_rgb'][0]:.1f},{r['avg_rgb'][1]:.1f},{r['avg_rgb'][2]:.1f})"
        table.append(f"{i:2} | {r['threads']:13} | {r['processes']:14} | {r['data_count']:9} | {r['time_s']:9.6f} | {r['speedup']:6.6f} | {r['efficiency_percent']:11.2f} | {avg_rgb_str:20} | {r['color_name']}")
    return "\n".join(table)
