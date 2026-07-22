# Data Analysis Pipeline

An ETL pipeline that converts CSVs to Parquet, joins them, and computes a derived column.

## Setup

```bash
mkdir -p /tmp/pyantz_data/output
python setup_data.py
```

## Run it

```bash
pyantz pipeline.json
```

## Pipeline graph

```
setup_dirs
├── convert_sales   ──┐
└── convert_products ──┤
                       └── join_tables
                               └── compute_revenue
```

Note that `convert_sales` and `convert_products` can run **in parallel** because they both only depend on `setup_dirs`. With `number_processes: 4` two workers will pick them up simultaneously.

## What it demonstrates

- **Global `variables`** — `data_dir` is defined once at the top level and interpolated as `%{data_dir}` throughout all job parameters
- **Fan-out / fan-in** — two parallel jobs converge into one downstream job via `depends_on`
- **`csv_to_parquet`** — low-memory streaming conversion using Polars
- **`join_parquets`** — Polars join with configurable strategy (`inner`, `left`, `full`, etc.)
- **`columnar_operation`** — apply arithmetic between two columns and save the result
