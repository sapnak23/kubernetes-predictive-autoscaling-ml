from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DIR = BASE_DIR / "data" / "processed"

INPUT_FILE = PROCESSED_DIR / "master_dataset_clean.csv"
OUTPUT_FILE = PROCESSED_DIR / "ml_dataset.csv"

# All features and targets are defined by time, not row position.
FORECAST_HORIZON_SECONDS = 30

LAG_SECONDS = [15, 30, 45, 60]

# Allows for small variations in the recorder interval.
MATCH_TOLERANCE_SECONDS = 5


def attach_time_shifted_value(
    base_df: pd.DataFrame,
    source_df: pd.DataFrame,
    seconds_offset: int,
    source_column: str,
    output_column: str,
) -> pd.DataFrame:
    """
    Attach the value closest to timestamp + seconds_offset.

    Negative offsets create lag features.
    Positive offsets create future targets.
    """

    lookup = source_df[["timestamp", source_column]].copy()

    lookup["lookup_timestamp"] = (
        lookup["timestamp"]
        - pd.to_timedelta(seconds_offset, unit="s")
    )

    lookup = lookup.rename(columns={source_column: output_column})
    lookup = lookup.drop(columns=["timestamp"])
    lookup = lookup.sort_values("lookup_timestamp")

    result = pd.merge_asof(
        base_df.sort_values("timestamp"),
        lookup,
        left_on="timestamp",
        right_on="lookup_timestamp",
        direction="nearest",
        tolerance=pd.Timedelta(seconds=MATCH_TOLERANCE_SECONDS),
    )

    result = result.drop(columns=["lookup_timestamp"])

    return result


def engineer_experiment(experiment_df: pd.DataFrame) -> pd.DataFrame:
    """
    Create time-based features within a single experiment.

    Processing each experiment independently prevents information
    leaking across workload boundaries.
    """

    experiment_df = (
        experiment_df
        .copy()
        .sort_values("timestamp")
        .drop_duplicates(subset=["timestamp"], keep="last")
        .reset_index(drop=True)
    )

    engineered = experiment_df.copy()

    # Record the interval since the previous observation.
    engineered["sampling_interval_seconds"] = (
        engineered["timestamp"]
        .diff()
        .dt.total_seconds()
    )

    # Time-based CPU lag features.
    for lag_seconds in LAG_SECONDS:
        engineered = attach_time_shifted_value(
            base_df=engineered,
            source_df=experiment_df,
            seconds_offset=-lag_seconds,
            source_column="current_cpu_percentage",
            output_column=f"cpu_lag_{lag_seconds}s",
        )

    # Time-based replica lag.
    engineered = attach_time_shifted_value(
        base_df=engineered,
        source_df=experiment_df,
        seconds_offset=-15,
        source_column="current_replicas",
        output_column="replicas_lag_15s",
    )

    # Thirty-second future CPU target.
    engineered = attach_time_shifted_value(
        base_df=engineered,
        source_df=experiment_df,
        seconds_offset=FORECAST_HORIZON_SECONDS,
        source_column="current_cpu_percentage",
        output_column="future_cpu_30s",
    )

    # Future timestamp, used to validate the actual forecast horizon.
    future_timestamp_source = experiment_df[
        ["timestamp"]
    ].copy()

    future_timestamp_source["future_observation_timestamp"] = (
        future_timestamp_source["timestamp"]
    )

    future_timestamp_source["lookup_timestamp"] = (
        future_timestamp_source["timestamp"]
        - pd.to_timedelta(
            FORECAST_HORIZON_SECONDS,
            unit="s",
        )
    )

    future_timestamp_source = future_timestamp_source[
        ["lookup_timestamp", "future_observation_timestamp"]
    ].sort_values("lookup_timestamp")

    engineered = pd.merge_asof(
        engineered.sort_values("timestamp"),
        future_timestamp_source,
        left_on="timestamp",
        right_on="lookup_timestamp",
        direction="nearest",
        tolerance=pd.Timedelta(
            seconds=MATCH_TOLERANCE_SECONDS
        ),
    )

    engineered = engineered.drop(columns=["lookup_timestamp"])

    engineered["actual_horizon_seconds"] = (
        engineered["future_observation_timestamp"]
        - engineered["timestamp"]
    ).dt.total_seconds()

    # Trend features using consistent time-based lags.
    engineered["cpu_change_15s"] = (
        engineered["current_cpu_percentage"]
        - engineered["cpu_lag_15s"]
    )

    engineered["cpu_change_30s"] = (
        engineered["current_cpu_percentage"]
        - engineered["cpu_lag_30s"]
    )

    engineered["cpu_slope_30s"] = (
        engineered["cpu_change_30s"] / 30.0
    )

    # Summary of recent CPU behaviour.
    lag_columns = [
        "current_cpu_percentage",
        "cpu_lag_15s",
        "cpu_lag_30s",
        "cpu_lag_45s",
    ]

    engineered["cpu_recent_mean"] = (
        engineered[lag_columns].mean(axis=1)
    )

    engineered["cpu_recent_max"] = (
        engineered[lag_columns].max(axis=1)
    )

    engineered["cpu_recent_min"] = (
        engineered[lag_columns].min(axis=1)
    )

    engineered["cpu_recent_std"] = (
        engineered[lag_columns].std(axis=1)
    )

    # Replica behaviour.
    engineered["replica_change_15s"] = (
        engineered["current_replicas"]
        - engineered["replicas_lag_15s"]
    )

    # Distance from the configured HPA threshold.
    engineered["cpu_above_target"] = (
        engineered["current_cpu_percentage"]
        - engineered["target_cpu_percentage"]
    )

    return engineered


def main() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"{INPUT_FILE} was not found. "
        )

    df = pd.read_csv(INPUT_FILE)

    required_input_columns = [
        "timestamp",
        "current_replicas",
        "desired_replicas",
        "current_cpu_percentage",
        "target_cpu_percentage",
        "experiment",
    ]

    missing_columns = [
        column
        for column in required_input_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        utc=True,
        errors="coerce",
    )

    df = df.dropna(subset=["timestamp"]).copy()

    numeric_columns = [
        "current_replicas",
        "desired_replicas",
        "current_cpu_percentage",
        "target_cpu_percentage",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    df = df.dropna(
        subset=numeric_columns + ["experiment"]
    ).copy()

    engineered_experiments = []

    for experiment_name, experiment_df in df.groupby(
        "experiment",
        sort=False,
    ):
        print(
            f"Processing {experiment_name}: "
            f"{len(experiment_df)} source rows"
        )

        engineered = engineer_experiment(experiment_df)
        engineered_experiments.append(engineered)

    ml_df = pd.concat(
        engineered_experiments,
        ignore_index=True,
    )

    feature_columns = [
        "current_cpu_percentage",
        "current_replicas",
        "target_cpu_percentage",
        "cpu_lag_15s",
        "cpu_lag_30s",
        "cpu_lag_45s",
        "cpu_lag_60s",
        "replicas_lag_15s",
        "cpu_change_15s",
        "cpu_change_30s",
        "cpu_slope_30s",
        "cpu_recent_mean",
        "cpu_recent_max",
        "cpu_recent_min",
        "cpu_recent_std",
        "replica_change_15s",
        "cpu_above_target",
    ]

    target_column = "future_cpu_30s"

    rows_before_cleanup = len(ml_df)

    ml_df = ml_df.replace(
        [np.inf, -np.inf],
        np.nan,
    )

    ml_df = ml_df.dropna(
        subset=feature_columns
        + [
            target_column,
            "actual_horizon_seconds",
        ]
    ).copy()

    # The target should represent approximately 30 seconds.
    ml_df = ml_df[
        ml_df["actual_horizon_seconds"].between(
            FORECAST_HORIZON_SECONDS
            - MATCH_TOLERANCE_SECONDS,
            FORECAST_HORIZON_SECONDS
            + MATCH_TOLERANCE_SECONDS,
        )
    ].copy()

    ml_df = ml_df.sort_values(
        ["experiment", "timestamp"]
    ).reset_index(drop=True)

    ml_df.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print("\nFeature engineering completed successfully.")
    print(f"Rows before feature cleanup: {rows_before_cleanup}")
    print(f"ML-ready rows: {len(ml_df)}")
    print(f"Saved as: {OUTPUT_FILE}")

    print("\nSource sampling intervals by experiment:")

    sampling_summary = (
        ml_df.groupby("experiment")[
            "sampling_interval_seconds"
        ]
        .agg(["count", "median", "mean", "min", "max"])
        .round(2)
    )

    print(sampling_summary.to_string())

    print("\nML-ready rows by experiment:")
    print(
        ml_df.groupby("experiment")
        .size()
        .to_string()
    )

    print("\nActual prediction horizon:")
    print(
        ml_df["actual_horizon_seconds"]
        .describe()
        .round(2)
        .to_string()
    )

    print("\nFeature columns:")
    for feature in feature_columns:
        print(f"- {feature}")

    print(f"\nPrediction target: {target_column}")


if __name__ == "__main__":
    main()