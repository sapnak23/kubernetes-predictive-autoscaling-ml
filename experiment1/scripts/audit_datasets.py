from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"

EXPERIMENTS = {
    "baseline": RAW_DIR / "baseline_hpa_metrics.csv",
    "gradual_ramp": RAW_DIR / "gradual_ramp_hpa_metrics.csv",
    "sudden_spike": RAW_DIR / "sudden_spike_hpa_metrics.csv",
    "oscillating_load": RAW_DIR / "oscillating_load_hpa_metrics.csv",
    "long_mixed_workload": RAW_DIR / "long_mixed_workload_hpa_metrics.csv",
    "random_bursty_workload": RAW_DIR / "random_bursty_workload_hpa_metrics.csv",
}


def main() -> None:
    summaries = []

    for experiment, path in EXPERIMENTS.items():
        if not path.exists():
            print(f"Missing file: {path}")
            continue

        df = pd.read_csv(path)

        print("\n" + "=" * 70)
        print(f"Experiment: {experiment}")
        print(f"File: {path}")
        print(f"Rows: {len(df)}")
        print(f"Columns: {list(df.columns)}")
        print("\nFirst three rows:")
        print(df.head(3).to_string(index=False))

        summary = {
            "experiment": experiment,
            "rows": len(df),
            "columns": len(df.columns),
            "duplicate_rows": int(df.duplicated().sum()),
            "missing_cells": int(df.isna().sum().sum()),
        }

        for column in [
            "current_cpu_percentage",
            "current_replicas",
            "desired_replicas",
        ]:
            if column in df.columns:
                numeric = pd.to_numeric(df[column], errors="coerce")

                summary[f"{column}_valid"] = int(numeric.notna().sum())
                summary[f"{column}_min"] = numeric.min()
                summary[f"{column}_max"] = numeric.max()
                summary[f"{column}_mean"] = numeric.mean()

        summaries.append(summary)

    summary_df = pd.DataFrame(summaries)

    print("\n" + "=" * 70)
    print("ALL DATASETS SUMMARY")
    print(summary_df.to_string(index=False))

    output_path = BASE_DIR / "data" / "processed" / "dataset_audit_summary.csv"
    summary_df.to_csv(output_path, index=False)

    print(f"\nSaved audit summary to: {output_path}")


if __name__ == "__main__":
    main()