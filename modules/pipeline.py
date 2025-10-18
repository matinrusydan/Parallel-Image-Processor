# modules/pipeline.py
# Pipeline runner functions
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import time
from typing import List, Dict, Any
from modules.io import load_image_to_bytes
from modules.processing import process_image_bytes

def run_serial(file_list: List[str], verbose: bool = False) -> Dict[str, Any]:
    # Jalankan baseline serial processing untuk perbandingan waktu.
    start = time.perf_counter()
    processed = []
    for idx, p in enumerate(file_list, start=1):
        try:
            item = load_image_to_bytes(p)
            processed.append(process_image_bytes(item))
        except Exception as e:
            if verbose:
                print(f"[WARN serial] {p}: {e}")
    end = time.perf_counter()
    elapsed = end - start
    count = len(processed)
    throughput = count / elapsed if elapsed > 0 else float("inf")
    # Extract avg colors for audit
    avg_colors = [(r, g, b) for _, r, g, b in processed]
    return {"elapsed": elapsed, "throughput": throughput, "processed": processed, "count": count, "avg_colors": avg_colors}

def run_configuration(num_threads: int, num_processes: int, file_list: List[str], verbose: bool = False) -> Dict[str, Any]:
    # Jalankan pipeline paralel dengan ThreadPool untuk I/O dan ProcessPool untuk CPU.
    start = time.perf_counter()
    loaded = []
    # Step A: load dengan threads
    with ThreadPoolExecutor(max_workers=num_threads) as tpool:
        futures = { tpool.submit(load_image_to_bytes, p): p for p in file_list }
        for i, fut in enumerate(as_completed(futures), start=1):
            p = futures[fut]
            try:
                res = fut.result()
                loaded.append(res)
            except Exception as e:
                if verbose:
                    print(f"[WARN] gagal load {p}: {e}")
            if verbose and (i % 10 == 0 or i == len(futures)):
                print(f"[INFO] Loaded {i}/{len(futures)}")
    # Step B: process with processes
    processed = []
    with ProcessPoolExecutor(max_workers=num_processes) as ppool:
        futures = { ppool.submit(process_image_bytes, item): item["filename"] for item in loaded }
        for i, fut in enumerate(as_completed(futures), start=1):
            try:
                processed.append(fut.result())
            except Exception as e:
                if verbose:
                    print(f"[WARN] proses gagal: {e}")
            if verbose and (i % 10 == 0 or i == len(futures)):
                print(f"[INFO] Processed {i}/{len(futures)}")
    end = time.perf_counter()
    elapsed = end - start
    count = len(processed)
    throughput = count / elapsed if elapsed > 0 else float("inf")
    # Extract avg colors for audit
    avg_colors = [(r, g, b) for _, r, g, b in processed]
    return {"elapsed": elapsed, "throughput": throughput, "processed": processed, "count": count, "avg_colors": avg_colors}
