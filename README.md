# Parallel Image Processor (Thread + ProcessPool)

Proyek UTS untuk pemrosesan gambar paralel menggunakan ThreadPoolExecutor dan ProcessPoolExecutor.
## Clone Repository

```bash
git clone https://github.com/matinrusydan/Parallel-Image-Processor.git
cd Parallel-Image-Processor
```


## Instalasi

```bash
pip install pillow numpy matplotlib
```

## Penggunaan

### Generate dataset sintetis dan proses
```bash
python main.py --generate -v
```

### Jalankan eksperimen dengan mode CPU berat
```bash
python main.py --heavy --exp
```

### Jalankan eksperimen tanpa plot
```bash
python main.py --exp --no-plot
```

## Argumen CLI

- `--generate`: Generate gambar sintetis jika dataset kosong
- `--heavy`: Aktifkan mode pemrosesan CPU berat
- `--exp`: Jalankan mode eksperimen dengan konfigurasi thread/proses berbeda
- `--no-plot`: Lewati pembuatan file plot
- `--out`: Path file output CSV (default: results/results.csv)
- `-v, --verbose`: Aktifkan output verbose

## Output

- `results/results.csv`: Hasil CSV dengan metrik waktu, throughput, speedup, efisiensi
- `results/results.json`: Data JSON lengkap
- `results/results_plot.png`: Plot visualisasi (jika tidak --no-plot)
- Tabel eksperimen dan ringkasan di console