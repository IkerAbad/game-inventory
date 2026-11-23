# Benchmarks

Measured on 2026-11-23 on the development machine:

- AMD Ryzen 9 5900X, 12 cores / 24 threads.
- 31.9 GiB RAM (32 GB DDR4-3600 CL16).
- Windows 11 Pro 10.0.26300.
- Python 3.14.5.
- Local C: drive. Network disabled with `--offline`.

## Method

- Synthetic libraries under `%TEMP%`: one folder per game and one 1 KB file per folder.
- Three runs per size, median reported.
- `Scan` is `inventory.scan.scan_games`.
- `Build` is `inventory.excel.build_workbook` with the six sheets and charts.
- `Save` is `openpyxl` writing the `.xlsx` file.
- `Build + save` is the workbook publication time.
- `Full CLI` is `python -m inventory --offline --keep --output`, including scan, analysis, workbook and history.

## Synthetic libraries

| Games | Scan (s) | Build (s) | Save (s) | Build + save (s) | Full CLI (s) |
|---:|---:|---:|---:|---:|---:|
| 100 | 0.018 | 0.426 | 0.108 | 0.534 | 1.125 |
| 500 | 0.085 | 1.956 | 0.180 | 2.136 | 1.450 |
| 1000 | 0.105 | 1.881 | 0.219 | 2.100 | 2.639 |

The synthetic scan is a lower bound: each game has one file, while a real game folder contains hundreds or thousands. The scan only reads file metadata, not file contents.

## Real library

136 installed games, 1,323.49 GB, all configured libraries on C:, D:, E: and F:.

| Measurement | Time |
|---|---:|
| Scan and analysis (`--dry-run`, warm) | 6.278 s |
| Full CLI (`--offline --keep`, warm) | 8.457 s |
| Workbook publication (full minus dry run) | about 2.18 s |
| First cold `--dry-run` | 23.167 s |

The first run paid for cold file metadata and antivirus scanning. Warm runs are the numbers to compare with the synthetic table.

## Limits

- File count, disk speed, antivirus and the file system change the scan time.
- The workbook time depends on the number of rows and the charts, and on the Excel library version.
- These are local save times. Printing, uploading or opening the workbook are not measured.
- Figures are medians of real executions, not a guarantee for another machine.
