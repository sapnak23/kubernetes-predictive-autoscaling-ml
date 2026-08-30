from pathlib import Path

import pandas as pd
import numpy as np


# ============================================================
# Configuration
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = BASE_DIR / "data" / "raw" / "experiment3_final_mixed.csv"
OUTPUT_FILE = BASE_DIR / "data" / "processed" / "experiment3_ml_dataset.csv"

TARGET_HORIZON_SECONDS = 30

# Future CPU must be within ±5 seconds of the requested
# 30-second prediction horizon.
HORIZON_TOLERANCE_SECONDS = 5

# Normal recorder interval was approximately 10 seconds.
# Anything greater than 15 seconds is treated as a break
# in the continuous time series.
MAX_CONTINUOUS_GAP_SECONDS = 15

LAG_TIMES = [15, 30, 45, 60]


# ============================================================
# Add a time-based historical lag
# ============================================================

def add_time_lag(
    df,
    seconds,
    source_col,
    output_col
):

    output = pd.Series(
        np.nan,
        index=df.index,
        dtype=float
    )

    # Process each continuous segment separately.
    # This prevents values before the 22-minute recorder
    # interruption being connected with values after it.
    for segment_id, segment in df.groupby(
        "segment_id",
        sort=False
    ):

        segment = segment.sort_values(
            "timestamp"
        )

        left = segment[
            ["timestamp"]
        ].copy()

        left["lookup_time"] = (
            left["timestamp"]
            - pd.to_timedelta(
                seconds,
                unit="s"
            )
        )

        right = segment[
            ["timestamp", source_col]
        ].copy()

        right = right.rename(
            columns={
                "timestamp":
                    "source_timestamp",

                source_col:
                    output_col
            }
        )

        result = pd.merge_asof(
            left.sort_values(
                "lookup_time"
            ),

            right.sort_values(
                "source_timestamp"
            ),

            left_on="lookup_time",
            right_on="source_timestamp",

            direction="nearest",

            tolerance=pd.Timedelta(
                seconds=6
            )
        )

        output.loc[
            segment.index
        ] = result[
            output_col
        ].to_numpy()

    return output


# ============================================================
# Create CPU target approximately 30 seconds ahead
# ============================================================

def add_future_target(df):

    future_cpu = pd.Series(
        np.nan,
        index=df.index,
        dtype=float
    )

    future_timestamp = pd.Series(
        pd.NaT,
        index=df.index,
        dtype="datetime64[ns, UTC]"
    )

    # Again process each continuous segment independently.
    for segment_id, segment in df.groupby(
        "segment_id",
        sort=False
    ):

        segment = segment.sort_values(
            "timestamp"
        )

        left = segment[
            ["timestamp"]
        ].copy()

        left["target_time"] = (
            left["timestamp"]
            + pd.to_timedelta(
                TARGET_HORIZON_SECONDS,
                unit="s"
            )
        )

        right = segment[
            [
                "timestamp",
                "current_cpu_percentage"
            ]
        ].copy()

        right = right.rename(
            columns={
                "timestamp":
                    "future_timestamp",

                "current_cpu_percentage":
                    "future_cpu_30s"
            }
        )

        result = pd.merge_asof(
            left.sort_values(
                "target_time"
            ),

            right.sort_values(
                "future_timestamp"
            ),

            left_on="target_time",
            right_on="future_timestamp",

            direction="nearest",

            tolerance=pd.Timedelta(
                seconds=
                HORIZON_TOLERANCE_SECONDS
            )
        )

        future_cpu.loc[
            segment.index
        ] = result[
            "future_cpu_30s"
        ].to_numpy()

        future_timestamp.loc[
            segment.index
        ] = pd.to_datetime(
            result[
                "future_timestamp"
            ].to_numpy(),
            utc=True
        )

    return (
        future_cpu,
        future_timestamp
    )


# ============================================================
# Main feature-engineering pipeline
# ============================================================

def main():

    # --------------------------------------------------------
    # Load dataset
    # --------------------------------------------------------

    df = pd.read_csv(
        INPUT_FILE
    )

    print(
        "Source rows:",
        len(df)
    )

    # --------------------------------------------------------
    # Timestamp preparation
    # --------------------------------------------------------

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        utc=True
    )

    df = (
        df
        .sort_values("timestamp")
        .reset_index(drop=True)
    )


    # --------------------------------------------------------
    # Detect recorder gaps
    # --------------------------------------------------------

    df["sampling_interval_seconds"] = (
        df["timestamp"]
        .diff()
        .dt.total_seconds()
    )

    # Any gap greater than 15 seconds begins
    # a new continuous segment.
    df["segment_id"] = (
        df[
            "sampling_interval_seconds"
        ]
        .gt(
            MAX_CONTINUOUS_GAP_SECONDS
        )
        .cumsum()
    )


    print(
        "\nDetected continuous segments:"
    )

    segment_summary = (
        df.groupby("segment_id")
        .agg(
            rows=(
                "timestamp",
                "size"
            ),
            start=(
                "timestamp",
                "min"
            ),
            end=(
                "timestamp",
                "max"
            )
        )
    )

    print(
        segment_summary.to_string()
    )


    # Display actual large gaps

    gaps = df[
        df[
            "sampling_interval_seconds"
        ]
        > MAX_CONTINUOUS_GAP_SECONDS
    ][
        [
            "timestamp",
            "sampling_interval_seconds"
        ]
    ]

    print(
        "\nDetected recording gaps:"
    )

    if len(gaps) == 0:

        print(
            "No gaps detected."
        )

    else:

        print(
            gaps.to_string(
                index=False
            )
        )


    # --------------------------------------------------------
    # Historical CPU lag features
    # --------------------------------------------------------

    for seconds in LAG_TIMES:

        column_name = (
            f"cpu_lag_{seconds}s"
        )

        df[column_name] = (
            add_time_lag(
                df=df,
                seconds=seconds,
                source_col=
                    "current_cpu_percentage",
                output_col=
                    column_name
            )
        )


    # --------------------------------------------------------
    # Replica historical feature
    # --------------------------------------------------------

    df[
        "replicas_lag_15s"
    ] = add_time_lag(
        df=df,
        seconds=15,
        source_col=
            "current_replicas",
        output_col=
            "replicas_lag_15s"
    )


    # --------------------------------------------------------
    # CPU change features
    # --------------------------------------------------------

    df[
        "cpu_change_15s"
    ] = (
        df[
            "current_cpu_percentage"
        ]
        - df[
            "cpu_lag_15s"
        ]
    )


    df[
        "cpu_change_30s"
    ] = (
        df[
            "current_cpu_percentage"
        ]
        - df[
            "cpu_lag_30s"
        ]
    )


    # Average rate of CPU movement per second
    # during the previous 30 seconds.
    df[
        "cpu_slope_30s"
    ] = (
        df[
            "cpu_change_30s"
        ]
        / 30.0
    )


    # --------------------------------------------------------
    # Recent CPU statistics
    # --------------------------------------------------------

    recent_cpu_columns = [

        "current_cpu_percentage",

        "cpu_lag_15s",
        "cpu_lag_30s",
        "cpu_lag_45s",
        "cpu_lag_60s"
    ]


    df[
        "cpu_recent_mean"
    ] = (
        df[
            recent_cpu_columns
        ]
        .mean(axis=1)
    )


    df[
        "cpu_recent_max"
    ] = (
        df[
            recent_cpu_columns
        ]
        .max(axis=1)
    )


    df[
        "cpu_recent_min"
    ] = (
        df[
            recent_cpu_columns
        ]
        .min(axis=1)
    )


    df[
        "cpu_recent_std"
    ] = (
        df[
            recent_cpu_columns
        ]
        .std(axis=1)
    )


    # --------------------------------------------------------
    # Replica behaviour
    # --------------------------------------------------------

    df[
        "replica_change_15s"
    ] = (
        df[
            "current_replicas"
        ]
        - df[
            "replicas_lag_15s"
        ]
    )


    # Difference between current CPU and
    # Kubernetes HPA target CPU.
    #
    # Example:
    #
    # current CPU = 70
    # target CPU  = 50
    #
    # cpu_above_target = +20
    #
    df[
        "cpu_above_target"
    ] = (
        df[
            "current_cpu_percentage"
        ]
        - df[
            "target_cpu_percentage"
        ]
    )


    # --------------------------------------------------------
    # Create prediction target
    # --------------------------------------------------------

    (
        future_cpu,
        future_timestamp
    ) = add_future_target(
        df
    )


    df[
        "future_cpu_30s"
    ] = future_cpu


    df[
        "future_timestamp"
    ] = future_timestamp


    # Exact prediction horizon
    df[
        "actual_horizon_seconds"
    ] = (
        df[
            "future_timestamp"
        ]
        - df[
            "timestamp"
        ]
    ).dt.total_seconds()


    # --------------------------------------------------------
    # ML feature list
    # --------------------------------------------------------

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

        "cpu_above_target"
    ]


    required_columns = (

        feature_columns

        + [

            "future_cpu_30s",

            "future_timestamp",

            "actual_horizon_seconds"
        ]
    )


    # --------------------------------------------------------
    # Remove rows that do not have sufficient
    # historical/future information
    # --------------------------------------------------------

    ml_df = df.dropna(
        subset=required_columns
    ).copy()


    # --------------------------------------------------------
    # Final safety check for target horizon
    # --------------------------------------------------------

    ml_df = ml_df[
        ml_df[
            "actual_horizon_seconds"
        ].between(

            TARGET_HORIZON_SECONDS
            - HORIZON_TOLERANCE_SECONDS,

            TARGET_HORIZON_SECONDS
            + HORIZON_TOLERANCE_SECONDS
        )
    ].copy()


    # --------------------------------------------------------
    # Save dataset
    # --------------------------------------------------------

    ml_df.to_csv(
        OUTPUT_FILE,
        index=False
    )


    # ========================================================
    # Results / validation
    # ========================================================

    print(
        "\n======================================"
    )

    print(
        "FEATURE ENGINEERING COMPLETE"
    )

    print(
        "======================================"
    )

    print(
        "Raw rows:",
        len(df)
    )

    print(
        "ML-ready rows:",
        len(ml_df)
    )

    print(
        "Rows removed:",
        len(df) - len(ml_df)
    )

    print(
        "Output:",
        OUTPUT_FILE
    )


    # --------------------------------------------------------
    # Sampling intervals
    # --------------------------------------------------------

    print(
        "\nSampling interval summary:"
    )

    print(
        df[
            "sampling_interval_seconds"
        ]
        .describe()
        .round(2)
    )


    # --------------------------------------------------------
    # Prediction horizon
    # --------------------------------------------------------

    print(
        "\nActual prediction horizon:"
    )

    print(
        ml_df[
            "actual_horizon_seconds"
        ]
        .describe()
        .round(2)
    )


    # --------------------------------------------------------
    # Rows per continuous segment
    # --------------------------------------------------------

    print(
        "\nML-ready rows by segment:"
    )

    print(
        ml_df[
            "segment_id"
        ]
        .value_counts()
        .sort_index()
    )


    # --------------------------------------------------------
    # CPU transition distribution
    # --------------------------------------------------------

    change = (

        ml_df[
            "future_cpu_30s"
        ]

        - ml_df[
            "current_cpu_percentage"
        ]

    ).abs()


    print(
        "\n30-second CPU transition distribution:"
    )


    print(
        "Exact same:",
        (change == 0).sum(),
        f"({(change == 0).mean()*100:.1f}%)"
    )


    print(
        "Within 5:",
        (change <= 5).sum(),
        f"({(change <= 5).mean()*100:.1f}%)"
    )


    print(
        "Within 10:",
        (change <= 10).sum(),
        f"({(change <= 10).mean()*100:.1f}%)"
    )


    print(
        "Change >10:",
        (change > 10).sum(),
        f"({(change > 10).mean()*100:.1f}%)"
    )


    print(
        "Change >20:",
        (change > 20).sum(),
        f"({(change > 20).mean()*100:.1f}%)"
    )


    print(
        "Change >30:",
        (change > 30).sum(),
        f"({(change > 30).mean()*100:.1f}%)"
    )


    print(
        "Maximum change:",
        change.max()
    )


    # --------------------------------------------------------
    # Display feature names
    # --------------------------------------------------------

    print(
        "\nFeature columns:"
    )

    for column in feature_columns:

        print(
            "-",
            column
        )


    print(
        "\nPrediction target:"
    )

    print(
        "- future_cpu_30s"
    )


# ============================================================
# Run
# ============================================================

if __name__ == "__main__":

    main()