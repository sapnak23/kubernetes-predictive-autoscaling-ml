from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


BASE_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DIR = BASE_DIR / "data" / "processed"

INPUT_FILE = PROCESSED_DIR / "ml_dataset.csv"
OUTPUT_FILE = PROCESSED_DIR / "baseline_results.csv"


TRAIN_EXPERIMENTS = [
    "baseline",
    "gradual_ramp",
    "sudden_spike",
    "oscillating_load",
]

VALIDATION_EXPERIMENTS = [
    "long_mixed_workload",
]

TEST_EXPERIMENTS = [
    "random_bursty_workload",
]


def calculate_metrics(actual, predicted):
    mae = mean_absolute_error(actual, predicted)
    rmse = np.sqrt(mean_squared_error(actual, predicted))
    r2 = r2_score(actual, predicted)

    return {
        "MAE": mae,
        "RMSE": rmse,
        "R2": r2,
    }


def evaluate_split(name, df):
    actual = df["future_cpu_30s"]

    # Persistence baseline:
    # assume CPU after ~30 seconds will equal CPU now
    predicted = df["current_cpu_percentage"]

    metrics = calculate_metrics(actual, predicted)

    return {
        "split": name,
        "rows": len(df),
        "MAE": metrics["MAE"],
        "RMSE": metrics["RMSE"],
        "R2": metrics["R2"],
    }


def main():

    df = pd.read_csv(INPUT_FILE)

    train_df = df[
        df["experiment"].isin(TRAIN_EXPERIMENTS)
    ].copy()

    validation_df = df[
        df["experiment"].isin(VALIDATION_EXPERIMENTS)
    ].copy()

    test_df = df[
        df["experiment"].isin(TEST_EXPERIMENTS)
    ].copy()

    results = [
        evaluate_split("training", train_df),
        evaluate_split("validation", validation_df),
        evaluate_split("testing", test_df),
    ]

    results_df = pd.DataFrame(results)

    results_df.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print("Persistence baseline completed.")

    print("\nDataset split:")
    print(f"Training rows:   {len(train_df)}")
    print(f"Validation rows: {len(validation_df)}")
    print(f"Testing rows:    {len(test_df)}")

    print("\nResults:")
    print(
        results_df.round(4).to_string(index=False)
    )

    print(f"\nSaved as: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()