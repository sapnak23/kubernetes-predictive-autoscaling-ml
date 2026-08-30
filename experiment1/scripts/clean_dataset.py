from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DIR = BASE_DIR / "data" / "processed"

INPUT_FILE = PROCESSED_DIR / "master_dataset.csv"
OUTPUT_FILE = PROCESSED_DIR / "master_dataset_clean.csv"
SUMMARY_FILE = PROCESSED_DIR / "cleaning_summary.csv"

REQUIRED_COLUMNS = [
    "timestamp",
    "current_replicas",
    "desired_replicas",
    "current_cpu_percentage",
    "target_cpu_percentage",
    "experiment",
]


def main() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"{INPUT_FILE} was not found."
        )

    df = pd.read_csv(INPUT_FILE)

    missing_columns = [
        column for column in REQUIRED_COLUMNS if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    print(f"Original rows: {len(df)}")

    # Convert timestamp to a valid datetime.
    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce",
        utc=True,
    )

    numeric_columns = [
        "current_replicas",
        "desired_replicas",
        "current_cpu_percentage",
        "target_cpu_percentage",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    # Show missing values before cleaning.
    print("\nMissing values before cleaning:")
    print(df[REQUIRED_COLUMNS].isna().sum())

    rows_before = len(df)

    # Remove exact duplicate rows.
    duplicate_count = int(df.duplicated().sum())
    df = df.drop_duplicates()

    # Remove rows where essential HPA information is unavailable.
    df = df.dropna(
        subset=[
            "timestamp",
            "current_replicas",
            "desired_replicas",
            "current_cpu_percentage",
            "target_cpu_percentage",
            "experiment",
        ]
    )

    # Remove impossible values.
    df = df[
        (df["current_replicas"] >= 1)
        & (df["desired_replicas"] >= 1)
        & (df["current_cpu_percentage"] >= 0)
        & (df["target_cpu_percentage"] > 0)
    ].copy()

    # Replica values should be integers.
    df["current_replicas"] = df["current_replicas"].astype(int)
    df["desired_replicas"] = df["desired_replicas"].astype(int)

    # Sort within each experiment.
    df = df.sort_values(
        by=["experiment", "timestamp"]
    ).reset_index(drop=True)

    rows_after = len(df)
    removed_rows = rows_before - rows_after

    df.to_csv(OUTPUT_FILE, index=False)

    summary = (
        df.groupby("experiment")
        .agg(
            rows=("timestamp", "size"),
            start_time=("timestamp", "min"),
            end_time=("timestamp", "max"),
            cpu_min=("current_cpu_percentage", "min"),
            cpu_max=("current_cpu_percentage", "max"),
            cpu_mean=("current_cpu_percentage", "mean"),
            min_current_replicas=("current_replicas", "min"),
            max_current_replicas=("current_replicas", "max"),
            min_desired_replicas=("desired_replicas", "min"),
            max_desired_replicas=("desired_replicas", "max"),
        )
        .reset_index()
    )

    summary.to_csv(SUMMARY_FILE, index=False)

    print("\nCleaning completed successfully.")
    print(f"Duplicate rows removed: {duplicate_count}")
    print(f"Total rows removed: {removed_rows}")
    print(f"Clean rows remaining: {rows_after}")
    print(f"Saved clean dataset: {OUTPUT_FILE}")
    print(f"Saved experiment summary: {SUMMARY_FILE}")

    print("\nRows by experiment:")
    print(df["experiment"].value_counts().to_string())


if __name__ == "__main__":
    main()