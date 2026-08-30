import pandas as pd
from pathlib import Path

# Base folder containing Experiment 1 files
BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"

# Experiment names and corresponding CSV paths
experiments = {
    "baseline": RAW_DIR / "baseline_hpa_metrics.csv",
    "gradual_ramp": RAW_DIR / "gradual_ramp_hpa_metrics.csv",
    "sudden_spike": RAW_DIR / "sudden_spike_hpa_metrics.csv",
    "oscillating_load": RAW_DIR / "oscillating_load_hpa_metrics.csv",
    "long_mixed_workload": RAW_DIR / "long_mixed_workload_hpa_metrics.csv",
    "random_bursty_workload": RAW_DIR / "random_bursty_workload_hpa_metrics.csv",
}

all_data = []

for experiment_name, csv_path in experiments.items():

    print(f"Loading {experiment_name}...")

    df = pd.read_csv(csv_path)

    # Add experiment label
    df["experiment"] = experiment_name

    all_data.append(df)

# Merge everything
master_df = pd.concat(all_data, ignore_index=True)

# Save merged dataset
output_file = BASE_DIR / "data" / "processed" / "master_dataset.csv"
master_df.to_csv(output_file, index=False)

print("\nMerge completed successfully!")
print(f"Total rows: {len(master_df)}")
print(f"Columns: {list(master_df.columns)}")
print(f"Saved as: {output_file}")