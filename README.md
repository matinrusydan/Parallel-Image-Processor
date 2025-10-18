# Parallel Image Processor (Thread + ProcessPool)

Proyek UTS untuk pemrosesan gambar paralel menggunakan ThreadPoolExecutor dan ProcessPoolExecutor di Python.

## Deskripsi

Aplikasi ini mengimplementasikan pipeline paralel untuk memproses gambar:
- **Threading Layer**: Membaca gambar dari disk menggunakan ThreadPoolExecutor (I/O-bound).
- **Process Pool Layer**: Memproses gambar (resize, compute average color) menggunakan ProcessPoolExecutor (CPU-bound).
- **Aggregation**: Mengumpulkan hasil, menghitung metrik (throughput, speedup, efficiency), menyimpan CSV/JSON/PNG.

Parameter dihitung otomatis dari NIM: `num_threads = (dua_terakhir % 4) + 2`, `num_processes = (dua_tengah % 3) + 2`, `num_data = tiga_terakhir * 10`.

## Fitur

- Parsing NIM otomatis untuk konfigurasi paralel.
- Reproducibility dengan seed NIM.
- CLI arguments lengkap: `--folder`, `--generate`, `--kaggle`, `--out`, `--no-plot`, `--verbose`.
- Output: CSV (header: mode,num_threads,num_processes,data_count,time_s,throughput,speedup,efficiency_percent), JSON summary, PNG plot.
- Audit warna: Hitung rata-rata global dan variasi warna per dataset.
- Tabel CLI boxed summary dengan Nama+NIM, parameter, dan metrik.
- Error handling dan fallback (synthetic images jika dataset kosong).

## Instalasi

1. Clone repository ini.
2. Install dependencies:
   ```
   pip install pillow numpy matplotlib
   ```
   (Opsional: `pip install kagglehub` untuk dataset Kaggle)

3. Jalankan:
   ```
   python main.py --generate --verbose
   ```

## Penggunaan

### Generate Synthetic Dataset
```
python main.py --generate --out results/results.csv --verbose
```

### Gunakan Folder Existing
```
python main.py --folder data --out results/results.csv --no-plot
```

### Download Dataset Kaggle (jika kagglehub terinstall)
```
python main.py --kaggle --out results/kaggle_results.csv --verbose
```

### CLI Arguments
- `--folder`: Folder dataset (default: "data")
- `--generate`: Generate synthetic images jika folder kosong
- `--kaggle`: Download dan gunakan dataset Kaggle 'pavansanagapati/images-dataset' subfolder 'cars'
- `--out`: Output CSV file (default: "results/results.csv")
- `--no-plot`: Skip generate plot PNG
- `--verbose`: Enable detailed logging/progress

## Output

- **Console**: Header Nama+NIM, parameter, ringkasan tiap konfigurasi, tabel boxed summary, sample avg colors, global avg & variation.
- **CSV**: Tabel hasil dengan header lengkap.
- **JSON**: Summary dengan name, nim, params, results.
- **PNG**: Plot bar (time) dan line (speedup/efficiency).

## Struktur Proyek

```
Parallel-Image-Processor/
├── main.py                    # Entry point utama
├── modules/
│   ├── io.py                  # I/O utilities (load, generate, gather files)
│   ├── utils.py               # Parsing NIM, save CSV/JSON, compute avg/variation
│   ├── pipeline.py            # run_serial dan run_configuration
│   └── processing.py          # process_image_bytes (CPU-bound)
├── data/                      # Folder untuk dataset (generated atau real)
├── results/                   # Output CSV, JSON, PNG
└── README.md                  # Dokumentasi ini
```

## NIM dan Parameter

NIM: 237006030
- dua_terakhir: 30 → num_threads = (30 % 4) + 2 = 4
- dua_tengah: 70 → num_processes = (70 % 3) + 2 = 2
- tiga_terakhir: 30 → num_data = 30 * 10 = 300

## Catatan

- Kode menggunakan `time.perf_counter()` untuk timing akurat.
- Semua fungsi ProcessPool picklable (top-level).
- Kompatibel Windows dengan fallback Unicode untuk box drawing.
- Jika dataset Kaggle tidak tersedia, fallback ke synthetic images.

## Dataset Source

Dataset Source: Kaggle (pavansanagapati/images-dataset, cars subset)

## Lisensi

Proyek ini untuk keperluan akademik UTS.

Version: Final Submission — Cleaned & Verified (2025-10-18)