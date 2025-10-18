# modules/pipeline.py
# Fungsi runner pipeline
import statistics
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import time
import os
import math
from typing import List, Dict, Any, Optional
from modules.processing import process_image_file

def run_serial(file_list: List[str], verbose: bool = False, heavy: bool = False) -> Dict[str, Any]:
    # Jalankan baseline serial untuk perbandingan
    start = time.perf_counter()
    processed = []
    task_times = []
    for idx, p in enumerate(file_list, start=1):
        try:
            result = process_image_file(p, heavy=heavy)
            processed.append(result[:4])  # exclude elapsed
            task_times.append(result[4])  # elapsed per task
        except Exception as e:
            if verbose:
                print(f"[WARN serial] {p}: {e}")
            processed.append((os.path.basename(p), math.nan, math.nan, math.nan))
            task_times.append(math.nan)
    end = time.perf_counter()
    elapsed = end - start
    count = len(processed)
    throughput = count / elapsed if elapsed > 0 else float("inf")
    # Ambil avg colors untuk audit
    avg_colors = [(r, g, b) for _, r, g, b in processed]
    return {"elapsed": elapsed, "throughput": throughput, "processed": processed, "count": count, "avg_colors": avg_colors, "task_times": task_times}

def run_experiments(experiment_configs: List[Dict[str, Any]], file_list: List[str], runs_per_config: int = 3, verbose: bool = False, heavy: bool = False) -> Dict[str, Any]:
    # Jalankan eksperimen berbagai konfigurasi
    results = []
    serial_baseline = None

    for config in experiment_configs:
        label = config["label"]
        threads = config["threads"]
        processes = config["processes"]
        data_count = config["data"]
        config_files = file_list[:data_count]

        if verbose:
            print(f"[EXPERIMENT] Running {label}: threads={threads}, processes={processes}, data={data_count}")

        times = []
        for run in range(runs_per_config):
            if verbose:
                print(f"  Run {run+1}/{runs_per_config}...")
            if threads == 1 and processes == 1:
                result = run_serial(config_files, verbose=False, heavy=heavy)
            else:
                result = run_configuration(threads, processes, config_files, verbose=False)
            times.append(result["elapsed"])

        median_time = statistics.median(times)
        throughput = data_count / median_time if median_time > 0 else float("inf")

        if serial_baseline is None and threads == 1 and processes == 1:
            serial_baseline = median_time

        speedup = serial_baseline / median_time if serial_baseline and median_time > 0 else 1.0
        efficiency = (speedup / max(1, processes)) * 100.0

        result_entry = {
            "label": label,
            "threads": threads,
            "processes": processes,
            "data_count": data_count,
            "time_s": median_time,
            "throughput": throughput,
            "speedup": speedup,
            "efficiency_percent": efficiency,
            "times": times
        }
        results.append(result_entry)

    return {"results": results, "serial_baseline": serial_baseline}

def run_configuration(num_threads: int, num_processes: int, file_list: List[str], verbose: bool = False, chunksize: Optional[int] = None, heavy: bool = False) -> Dict[str, Any]:
    # Jalankan pipeline paralel ThreadPool + ProcessPool
    io_start = time.perf_counter()
    # Step A: kumpulkan file paths
    loaded_paths = file_list
    io_end = time.perf_counter()
    io_time = io_end - io_start

    # Step B: proses dengan processes
    cpu_start = time.perf_counter()
    processed = []
    task_times = []
    chunksize = chunksize or max(1, len(loaded_paths) // (num_processes * 8))
    with ProcessPoolExecutor(max_workers=num_processes) as ppool:
        # Gunakan map dengan chunksize
        from functools import partial
        process_func = partial(process_image_file, heavy=heavy)
        results = ppool.map(process_func, loaded_paths, chunksize=chunksize)
        for i, result in enumerate(results, start=1):
            processed.append(result[:4])
            task_times.append(result[4])
            if verbose and (i % 10 == 0 or i == len(loaded_paths)):
                print(f"[INFO] Processed {i}/{len(loaded_paths)}")
    cpu_end = time.perf_counter()
    cpu_time = cpu_end - cpu_start

    total_elapsed = io_time + cpu_time
    count = len(processed)
    throughput = count / total_elapsed if total_elapsed > 0 else float("inf")
    # Ambil avg colors untuk audit
    avg_colors = [(r, g, b) for _, r, g, b in processed]
    return {"elapsed": total_elapsed, "throughput": throughput, "processed": processed, "count": count, "avg_colors": avg_colors, "io_time": io_time, "cpu_time": cpu_time, "task_times": task_times}
