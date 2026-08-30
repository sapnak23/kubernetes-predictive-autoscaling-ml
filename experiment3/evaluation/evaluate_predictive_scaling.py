from pathlib import Path

import pandas as pd
import numpy as np

# ============================================================
# Configuration
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]
EVALUATION_DIR = BASE_DIR / "evaluation"

INPUT_FILE = EVALUATION_DIR / "experiment3_predictions.csv"
OUTPUT_FILE = EVALUATION_DIR / "experiment3_predictive_scaling.csv"
MIN_REPLICAS = 1
MAX_REPLICAS = 20

# ============================================================
# Load predictions
# ============================================================

df = pd.read_csv(INPUT_FILE)

print("Rows loaded:", len(df))

# ============================================================
# Predictive replica recommendation
# ============================================================

# Gradient Boosting prediction used for the
# prediction-informed replica evaluation.

predicted_cpu = df[
    "gradient_boosting_prediction"
].clip(lower=0)

current_replicas = df[
    "current_replicas"
]

# HPA target is stored in the original experiment as 50%.
# Experiment 3 used a constant target of 50%.
target_cpu = 50.0

df["predicted_cpu_30s"] = predicted_cpu

df["predictive_replicas"] = np.ceil(
    current_replicas
    * predicted_cpu
    / target_cpu
)

df["predictive_replicas"] = (
    df["predictive_replicas"]
    .clip(
        lower=MIN_REPLICAS,
        upper=MAX_REPLICAS
    )
    .astype(int)
)

# ============================================================
# Reactive recommendation using CURRENT CPU
# ============================================================

df["reactive_replicas_now"] = np.ceil(
    current_replicas
    * df["current_cpu_percentage"]
    / target_cpu
)

df["reactive_replicas_now"] = (
    df["reactive_replicas_now"]
    .clip(
        lower=MIN_REPLICAS,
        upper=MAX_REPLICAS
    )
    .astype(int)
)

# ============================================================
# Reference future replica requirement
#
# This uses the CPU actually observed approximately 30 seconds later.
# It is unavailable during live operation and is used only as an
# evaluation reference.
# ============================================================

df["oracle_replicas_30s"] = np.ceil(
    current_replicas
    * df["future_cpu_30s"]
    / target_cpu
)

df["oracle_replicas_30s"] = (
    df["oracle_replicas_30s"]
    .clip(
        lower=MIN_REPLICAS,
        upper=MAX_REPLICAS
    )
    .astype(int)
)

# ============================================================
# Replica recommendation errors
# ============================================================

df["predictive_replica_error"] = (
    df["predictive_replicas"]
    - df["oracle_replicas_30s"]
).abs()

df["reactive_replica_error"] = (
    df["reactive_replicas_now"]
    - df["oracle_replicas_30s"]
).abs()

# ============================================================
# Does predictive scaling act earlier?
# ============================================================

df["predictive_scale_up"] = (
    df["predictive_replicas"]
    > df["current_replicas"]
)

df["reactive_scale_up"] = (
    df["reactive_replicas_now"]
    > df["current_replicas"]
)

df["predictive_earlier_than_reactive"] = (
    df["predictive_scale_up"]
    & ~df["reactive_scale_up"]
)

# ============================================================
# Exact / near-exact replica recommendation
# ============================================================

predictive_exact = (
    df["predictive_replica_error"] == 0
).mean() * 100

reactive_exact = (
    df["reactive_replica_error"] == 0
).mean() * 100

predictive_within_one = (
    df["predictive_replica_error"] <= 1
).mean() * 100

reactive_within_one = (
    df["reactive_replica_error"] <= 1
).mean() * 100

# ============================================================
# Save
# ============================================================

df.to_csv(
    OUTPUT_FILE,
    index=False
)

# ============================================================
# Results
# ============================================================

print()
print("=" * 65)
print("PREDICTION-INFORMED REPLICA EVALUATION")
print("=" * 65)

print("\nTest observations:", len(df))

print("\nMean absolute replica error:")

print(
    "Predictive:",
    round(
        df["predictive_replica_error"].mean(),
        3
    )
)

print(
    "Reactive:",
    round(
        df["reactive_replica_error"].mean(),
        3
    )
)

print("\nExact replica recommendation:")

print(
    f"Predictive: {predictive_exact:.1f}%"
)

print(
    f"Reactive:   {reactive_exact:.1f}%"
)

print("\nWithin ±1 replica:")

print(
    f"Predictive: {predictive_within_one:.1f}%"
)

print(
    f"Reactive:   {reactive_within_one:.1f}%"
)

print("\nScale-up behaviour:")

print(
    "Predictive scale-up recommendations:",
    df["predictive_scale_up"].sum()
)

print(
    "Reactive scale-up recommendations:",
    df["reactive_scale_up"].sum()
)

print(
    "Predictive earlier than reactive:",
    df[
        "predictive_earlier_than_reactive"
    ].sum()
)

# ============================================================
# Transition-specific comparison
# ============================================================

df["cpu_change_30s_abs"] = (
    df["future_cpu_30s"]
    - df["current_cpu_percentage"]
).abs()

for threshold in [10, 20]:

    subset = df[
        df["cpu_change_30s_abs"] > threshold
    ]

    print()
    print(
        f"CPU change > {threshold} points"
    )

    print(
        "Rows:",
        len(subset)
    )

    if len(subset) > 0:

        print(
            "Predictive replica MAE:",
            round(
                subset[
                    "predictive_replica_error"
                ].mean(),
                3
            )
        )

        print(
            "Reactive replica MAE:",
            round(
                subset[
                    "reactive_replica_error"
                ].mean(),
                3
            )
        )

print()
print("Saved:", OUTPUT_FILE)