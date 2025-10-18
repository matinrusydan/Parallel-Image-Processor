# main.py
# Main entry point for parallel image processing
import argparse
import os
import random
from modules.utils import parse_nim, save_csv, save_json, plot_results, compute_global_avg, audit_color_variation
from modules.io import gather_image_files, generate_synthetic_images, get_kaggle_cars_folder
from modules.pipeline import run_serial, run_configuration
import json
import numpy as np


NAME = "Matin Rusydan"
NIM = "237006030"  # string

def print_boxed_summary(name: str, nim: str, threads: int, processes: int, data: int, total_time: float, speedup: float, efficiency: float) -> None:
    # Print boxed summary seperti contoh.
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
        # Fallback for Windows console
        print("+" + "-" * (width - 2) + "+")
        print(f"| {line1:<{width-4}} |")
        print(f"| {line2:<{width-4}} |")
        print(f"| {line3:<{width-4}} |")
        print("+" + "-" * (width - 2) + "+")

def main_cli():
    parser = argparse.ArgumentParser(description="Parallel Image Processor (Thread + ProcessPool) modular")
    parser.add_argument("--folder", type=str, default="data", help="Folder dataset gambar (default: data)")
    parser.add_argument("--generate", action="store_true", help="Generate synthetic images jika folder kosong")
    parser.add_argument("--kaggle", action="store_true", help="Download dan gunakan dataset Kaggle 'pavansanagapati/images-dataset' subfolder 'cars'")
    parser.add_argument("--out", type=str, default="results/results.csv", help="Output CSV file")
    parser.add_argument("--no-plot", action="store_true", help="Skip generate plot")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    # Parse NIM -> parameters
    num_threads, num_processes, num_data, _, _, _ = parse_nim(NIM)
    # Set reproducibility seeds based on NIM
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

    # Ensure data folder exists or generate/download
    files = []
    image_folder = args.folder
    if args.kaggle:
        try:
            import kagglehub
            path = kagglehub.dataset_download('pavansanagapati/images-dataset')
            print(f"Path to dataset files: {path}")
            image_folder = get_kaggle_cars_folder(path)
            files = gather_image_files(image_folder, num_data)
            if len(files) < num_data:
                print(f"[WARN] Folder 'cars' hanya memiliki {len(files)} gambar, kurang dari {num_data}. Fallback ke --generate.")
                raise ValueError("Insufficient images in Kaggle dataset")
        except (ImportError, Exception) as e:
            print(f"[WARN] Kaggle download gagal ({e}). Fallback ke --generate synthetic images.")
            args.generate = True
            args.kaggle = False
            image_folder = args.folder
            files = []

    if not files:
        files = gather_image_files(image_folder, num_data)
        if (len(files) < 1) and args.generate:
            print(f"[INFO] folder '{image_folder}' kosong/tidak ada. Generating {num_data} synthetic images...")
            generate_synthetic_images(image_folder, num_data, size=(256,256), seed=int(NIM))
            files = gather_image_files(image_folder, num_data)

    if len(files) == 0:
        print(f"[ERROR] Tidak ada gambar di folder '{args.folder}'. Jalankan dengan --generate untuk membuat data uji.")
        return

    files = files[:num_data]
    data_count = len(files)
    folder_display = image_folder if args.kaggle else args.folder
    print(f"[INFO] Using {data_count} images from '{folder_display}'")

    results_rows = []

    # 1) Serial baseline
    print("[RUN] Serial baseline (no concurrency)...")
    serial_res = run_serial(files, verbose=args.verbose)
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
    # Use serial avg_colors for audit
    all_avg_colors = serial_res["avg_colors"]

    # 2) NIM config
    print(f"[RUN] Config NIM: threads={num_threads}, processes={num_processes}")
    nim_res = run_configuration(num_threads, num_processes, files, verbose=args.verbose)
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
    alt_res = run_configuration(alt_threads, alt_procs, files, verbose=args.verbose)
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

    # Save CSV & JSON
    save_csv(results_rows, out_csv)
    summary = {
        "name": NAME,
        "nim": NIM,
        "params": {"threads": num_threads, "processes": num_processes, "data": num_data},
        "results": results_rows
    }
    save_json(summary, out_json)
    print(f"[OK] Results saved to {out_csv} and {out_json}")

    # Plot unless skipped
    if not args.no_plot:
        plot_results(results_rows, out_png)
        print(f"[OK] Plot saved to {out_png}")
    else:
        print("[INFO] Plot generation skipped (--no-plot).")

    # Color audit and summary
    global_avg, stds = compute_global_avg(all_avg_colors)
    variation = audit_color_variation(all_avg_colors)
    variation_str = "YES" if variation else "NO"

    # Print boxed summary for nim_config
    nim_row = next(r for r in results_rows if r["mode"] == "nim_config")
    print_boxed_summary(NAME, NIM, num_threads, num_processes, data_count,
                        float(nim_row["time_s"]), float(nim_row["speedup"]), float(nim_row["efficiency_percent"]))

    # Print sample avg colors
    print("Sample avg colors (first 5):")
    for filename, (r, g, b) in zip([os.path.basename(f) for f in files[:5]], all_avg_colors[:5]):
        print(f" - {filename}: ({r:.1f}, {g:.1f}, {b:.1f})")

    # Print global avg and variation
    print(f"Global avg color: ({global_avg[0]:.1f}, {global_avg[1]:.1f}, {global_avg[2]:.1f})")
    print(f"Color variation: {variation_str} (stddev R: {stds[0]:.2f}, G: {stds[1]:.2f}, B: {stds[2]:.2f})")

if __name__ == "__main__":
    main_cli()
