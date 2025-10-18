# main.py
# Titik masuk utama untuk pemrosesan gambar paralel
import argparse
import os
import random
from modules.utils import parse_nim, save_csv, save_json, plot_results, compute_global_avg, audit_color_variation, plot_experiments, save_experiments_csv, save_experiments_json, print_experiments_table
from modules.io import gather_image_files
from modules.pipeline import run_serial, run_configuration, run_experiments
import json
import numpy as np


NAME = "Matin Rusydan"
NIM = "237006030"  # string

def print_boxed_summary(name: str, nim: str, threads: int, processes: int, data: int, total_time: float, speedup: float, efficiency: float) -> None:
    # Mencetak ringkasan dalam kotak seperti contoh.
    line1 = f"Hybrid Project by: {name} ({nim})"
    line2 = f"Threads: {threads} | Processes: {processes} | Data: {data}"
    line3 = f"Total Time: {total_time:.2f}s | Speedup: {speedup:.2f} | Efficiency: {efficiency:.1f}%"
    width = max(len(line1), len(line2), len(line3)) + 4
    try:
        print("┌" + "─" * (width - 2) + "┐")
        print(f"│ {line1:<{width-4}} │")
        print(f"│ {line2:<{width-4}} │")
        print(f"│ {line3:<{width-4}} │")
        print("└" + "─" * (width - 2) + "┘")
    except UnicodeEncodeError:
        # Fallback untuk console Windows
        print("+" + "-" * (width - 2) + "+")
        print(f"| {line1:<{width-4}} |")
        print(f"| {line2:<{width-4}} |")
        print(f"| {line3:<{width-4}} |")
        print("+" + "-" * (width - 2) + "+")

def main_cli():
    import argparse
    parser = argparse.ArgumentParser(
        description="Parallel Image Processor — Thread + ProcessPool (UTS Project)"
    )

    # Mengaktifkan beban kerja CPU yang lebih berat per gambar (contoh: blur atau histogram)
    parser.add_argument("--heavy", action="store_true",
                        help="Menjalankan mode CPU berat (opsional)")

    # Menjalankan beberapa konfigurasi eksperimen
    parser.add_argument("--exp", action="store_true",
                        help="Menjalankan mode eksperimen (beberapa konfigurasi threads/process/data)")

    # Melewati pembuatan grafik
    parser.add_argument("--no-plot", action="store_true",
                        help="Melewati pembuatan grafik hasil")

    # Lokasi output CSV custom (default: results/results.csv)
    parser.add_argument("--out", type=str, default="results/results.csv",
                        help="Lokasi file CSV output (default: results/results.csv)")

    # Mode verbose untuk logging detail
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Menampilkan log proses (I/O dan CPU progress)")

    args = parser.parse_args()

    # Parse NIM -> parameters
    num_threads, num_processes, num_data, _, _, _ = parse_nim(NIM)
    # Mengatur seed reproducibility berdasarkan NIM
    random.seed(int(NIM))
    np.random.seed(int(NIM))

    out_csv = args.out
    out_json = os.path.splitext(out_csv)[0] + ".json"
    out_png = os.path.splitext(out_csv)[0] + "_plot.png"

    print("===========================================")
    print(f"Nama : {NAME}")
    print(f"NIM  : {NIM}")
    print("Project: Parallel Image Processor (Thread + ProcessPool)")
    print("===========================================")
    print(f"Computed params -> threads: {num_threads}, processes: {num_processes}, data: {num_data}")
    print()

    # Pastikan folder data ada
    files = []
    image_folder = "data"  # Folder tetap
    if not files:
        files = gather_image_files(image_folder, num_data)

    if len(files) == 0:
        print(f"[ERROR] Folder 'data' kosong. Harap isi dengan dataset gambar sebelum menjalankan program.")
        return

    files = files[:num_data]
    data_count = len(files)
    print(f"[INFO] Using {data_count} images from '{image_folder}'")

    if args.exp:
        # Jalankan mode eksperimen
        experiment_configs = [
            {"label": "serial_baseline", "threads": 1, "processes": 1, "data": num_data},
            {"label": "nim_config", "threads": num_threads, "processes": num_processes, "data": num_data},
            {"label": "more_threads", "threads": min(max(num_threads * 2, num_threads + 1), 16), "processes": num_processes, "data": num_data},
            {"label": "more_processes", "threads": num_threads, "processes": min(num_processes + 1, 16), "data": num_data},
            {"label": "less_data", "threads": num_threads, "processes": num_processes, "data": max(num_data // 2, 1)}
        ]

        exp_result = run_experiments(experiment_configs, files, 3, args.verbose, args.heavy)
        exp_results = exp_result["results"]

        # Simpan output eksperimen
        exp_csv = "results/experiments.csv"
        exp_json = "results/experiments.json"
        exp_dir = "results"
        save_experiments_csv(exp_results, exp_csv)
        save_experiments_json(exp_results, exp_json)
        plot_experiments(exp_results, exp_dir)

        # Cetak tabel dan laporan
        table = print_experiments_table(exp_results)
        print("\nExperiments Results:")
        print(table)

        # Simpan laporan
        with open("results/experiments_report.txt", "w") as f:
            f.write("Experiments Report\n")
            f.write("=" * 50 + "\n")
            f.write(f"Name: {NAME}\n")
            f.write(f"NIM: {NIM}\n")
            f.write(f"Serial Baseline Time: {exp_result['serial_baseline']:.6f}s\n\n")
            f.write(table + "\n\n")
            best_time = min(r["time_s"] for r in exp_results)
            best_config = next(r for r in exp_results if r["time_s"] == best_time)
            f.write(f"Best Time Config: {best_config['label']} ({best_time:.6f}s)\n")
            best_speedup = max(r["speedup"] for r in exp_results)
            best_speedup_config = next(r for r in exp_results if r["speedup"] == best_speedup)
            f.write(f"Best Speedup Config: {best_speedup_config['label']} ({best_speedup:.3f}x)\n")

        print(f"[OK] Experiments saved to {exp_csv}, {exp_json}, and plots in {exp_dir}")

        # Verifikasi
        with open("results/experiments_verification.txt", "w") as f:
            f.write("Experiments Verification\n")
            f.write("=" * 30 + "\n")
            f.write(f"Total configs: {len(exp_results)}\n")
            f.write(f"Files created: {exp_csv}, {exp_json}, time_vs_threads.png, time_vs_processes.png, speedup_vs_config.png\n")
            f.write(f"Table printed: YES\n")
            f.write(f"Median times used: YES\n")
            f.write("Status: SUCCESS\n")

        return

    results_rows = []

    # 1) Serial baseline
    print("[RUN] Serial baseline (no concurrency)...")
    serial_res = run_serial(files, verbose=args.verbose, heavy=args.heavy)
    T_serial = serial_res["elapsed"]
    print(f"  Serial time: {T_serial:.6f} s, throughput: {serial_res['throughput']:.6f} img/s")
    results_rows.append({
        "mode":"serial",
        "num_threads":1,
        "num_processes":1,
        "data_count":data_count,
        "time_s": f"{T_serial:.6f}",
        "throughput": f"{serial_res['throughput']:.6f}",
        "speedup": 1.0,
        "efficiency_percent": 100.0
    })
    # Gunakan serial avg_colors untuk audit
    all_avg_colors = serial_res["avg_colors"]

    # 2) NIM config
    print(f"[RUN] Config NIM: threads={num_threads}, processes={num_processes}")
    nim_res = run_configuration(num_threads, num_processes, files, verbose=args.verbose, heavy=args.heavy)
    T_nim = nim_res["elapsed"]
    speedup_nim = T_serial / T_nim if T_nim > 0 else float("inf")
    efficiency_nim = (speedup_nim / max(1, num_processes)) * 100.0
    results_rows.append({
        "mode":"nim_config",
        "num_threads": num_threads,
        "num_processes": num_processes,
        "data_count": data_count,
        "time_s": f"{T_nim:.6f}",
        "throughput": f"{nim_res['throughput']:.6f}",
        "speedup": f"{speedup_nim:.6f}",
        "efficiency_percent": f"{efficiency_nim:.2f}"
    })
    print(f"  Time: {T_nim:.6f} s, throughput: {nim_res['throughput']:.6f} img/s, speedup: {speedup_nim:.3f}, efficiency: {efficiency_nim:.2f}%")

    # 3) Alternative config
    alt_threads = max(2, num_threads * 2)
    alt_procs = max(1, num_processes + 1)
    print(f"[RUN] Alternative config: threads={alt_threads}, processes={alt_procs}")
    alt_res = run_configuration(alt_threads, alt_procs, files, verbose=args.verbose, heavy=args.heavy)
    T_alt = alt_res["elapsed"]
    speedup_alt = T_serial / T_alt if T_alt > 0 else float("inf")
    efficiency_alt = (speedup_alt / max(1, alt_procs)) * 100.0
    results_rows.append({
        "mode":"alt_config",
        "num_threads": alt_threads,
        "num_processes": alt_procs,
        "data_count": data_count,
        "time_s": f"{T_alt:.6f}",
        "throughput": f"{alt_res['throughput']:.6f}",
        "speedup": f"{speedup_alt:.6f}",
        "efficiency_percent": f"{efficiency_alt:.2f}"
    })
    print(f"  Time: {T_alt:.6f} s, throughput: {alt_res['throughput']:.6f} img/s, speedup: {speedup_alt:.3f}, efficiency: {efficiency_alt:.2f}%")

    # Simpan CSV & JSON
    save_csv(results_rows, out_csv)
    summary = {
        "name": NAME,
        "nim": NIM,
        "params": {"threads": num_threads, "processes": num_processes, "data": num_data},
        "results": results_rows
    }
    save_json(summary, out_json)
    print(f"[OK] Results saved to {out_csv} and {out_json}")

    # Buat plot kecuali dilewati
    if not args.no_plot:
        plot_results(results_rows, out_png)
        print(f"[OK] Plot saved to {out_png}")
    else:
        print("[INFO] Plot generation skipped (--no-plot).")

    # Audit warna dan ringkasan
    global_avg, stds = compute_global_avg(all_avg_colors)
    variation = audit_color_variation(all_avg_colors)
    variation_str = "YES" if variation else "NO"

    # Cetak ringkasan dalam kotak untuk nim_config
    nim_row = next(r for r in results_rows if r["mode"] == "nim_config")
    print_boxed_summary(NAME, NIM, num_threads, num_processes, data_count,
                        float(nim_row["time_s"]), float(nim_row["speedup"]), float(nim_row["efficiency_percent"]))

    # Cetak contoh rata-rata warna
    print("Sample avg colors (first 5):")
    for filename, (r, g, b) in zip([os.path.basename(f) for f in files[:5]], all_avg_colors[:5]):
        print(f" - {filename}: ({r:.1f}, {g:.1f}, {b:.1f})")

    # Cetak rata-rata global dan variasi
    print(f"Global avg color: ({global_avg[0]:.1f}, {global_avg[1]:.1f}, {global_avg[2]:.1f})")
    print(f"Color variation: {variation_str} (stddev R: {stds[0]:.2f}, G: {stds[1]:.2f}, B: {stds[2]:.2f})")

if __name__ == "__main__":
    main_cli()
