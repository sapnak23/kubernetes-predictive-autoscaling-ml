from pathlib import Path

import time
import joblib
import numpy as np
import pandas as pd

from sklearn.linear_model import LinearRegression
from sklearn.ensemble import (
    RandomForestRegressor,
    GradientBoostingRegressor
)
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)


# ============================================================
# Configuration
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DIR = BASE_DIR / "data" / "processed"
EVALUATION_DIR = BASE_DIR / "evaluation"
MODELS_DIR = BASE_DIR / "models"

INPUT_FILE = PROCESSED_DIR / "experiment3_ml_dataset.csv"

RESULTS_FILE = EVALUATION_DIR / "experiment3_model_results.csv"
PREDICTIONS_FILE = EVALUATION_DIR / "experiment3_predictions.csv"

TARGET = "future_cpu_30s"


FEATURES = [
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


# ============================================================
# Metrics
# ============================================================

def calculate_metrics(actual, predicted):

    mae = mean_absolute_error(
        actual,
        predicted
    )

    rmse = np.sqrt(
        mean_squared_error(
            actual,
            predicted
        )
    )

    r2 = r2_score(
        actual,
        predicted
    )

    return mae, rmse, r2


# ============================================================
# Load data
# ============================================================

df = pd.read_csv(INPUT_FILE)

df["timestamp"] = pd.to_datetime(
    df["timestamp"],
    utc=True
)

df = (
    df
    .sort_values("timestamp")
    .reset_index(drop=True)
)

print("Dataset loaded.")
print("Total ML-ready rows:", len(df))


# ============================================================
# Chronological 70 / 15 / 15 split
# ============================================================

total_rows = len(df)

train_end = int(
    total_rows * 0.70
)

validation_end = int(
    total_rows * 0.85
)


train_df = df.iloc[
    :train_end
].copy()

validation_df = df.iloc[
    train_end:validation_end
].copy()

test_df = df.iloc[
    validation_end:
].copy()


print("\nChronological split:")

print(
    "Training:",
    len(train_df),
    f"({len(train_df)/total_rows*100:.1f}%)"
)

print(
    "Validation:",
    len(validation_df),
    f"({len(validation_df)/total_rows*100:.1f}%)"
)

print(
    "Testing:",
    len(test_df),
    f"({len(test_df)/total_rows*100:.1f}%)"
)


print("\nTime ranges:")

print(
    "TRAIN:",
    train_df["timestamp"].min(),
    "→",
    train_df["timestamp"].max()
)

print(
    "VALIDATION:",
    validation_df["timestamp"].min(),
    "→",
    validation_df["timestamp"].max()
)

print(
    "TEST:",
    test_df["timestamp"].min(),
    "→",
    test_df["timestamp"].max()
)


# ============================================================
# Prepare ML arrays
# ============================================================

X_train = train_df[FEATURES]
y_train = train_df[TARGET]

X_validation = validation_df[FEATURES]
y_validation = validation_df[TARGET]

X_test = test_df[FEATURES]
y_test = test_df[TARGET]


# ============================================================
# Models
# ============================================================

models = {

    "Linear Regression":
        LinearRegression(),

    "Random Forest":
        RandomForestRegressor(
            n_estimators=300,
            random_state=42,
            n_jobs=-1,
            min_samples_leaf=2
        ),

    "Gradient Boosting":
        GradientBoostingRegressor(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=3,
            random_state=42
        )
}


# ============================================================
# Results containers
# ============================================================

results = []


predictions = test_df[
    [
        "timestamp",
        "segment_id",
        "current_cpu_percentage",
        "current_replicas",
        "future_cpu_30s",
        "actual_horizon_seconds"
    ]
].copy()


# Persistence forecast:
#
# CPU after 30 sec = CPU now
#
predictions[
    "persistence_prediction"
] = test_df[
    "current_cpu_percentage"
].to_numpy()


# ============================================================
# Persistence evaluation
# ============================================================

for split_name, split_df in [

    ("training", train_df),

    ("validation", validation_df),

    ("testing", test_df)

]:

    actual = split_df[TARGET]

    predicted = split_df[
        "current_cpu_percentage"
    ]

    mae, rmse, r2 = calculate_metrics(
        actual,
        predicted
    )

    results.append({

        "model": "Persistence Baseline",

        "split": split_name,

        "rows": len(split_df),

        "MAE": mae,

        "RMSE": rmse,

        "R2": r2,

        "training_time_seconds": 0.0,

        "test_inference_time_seconds": 0.0
    })


# ============================================================
# Train ML models
# ============================================================

EVALUATION_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)

for model_name, model in models.items():

    print("\n--------------------------------------")
    print("Training:", model_name)
    print("--------------------------------------")

    training_start = time.perf_counter()

    model.fit(
        X_train,
        y_train
    )

    training_time = (
        time.perf_counter()
        - training_start
    )


    # --------------------------------------------------------
    # Predictions
    # --------------------------------------------------------

    train_prediction = model.predict(
        X_train
    )

    validation_prediction = model.predict(
        X_validation
    )


    inference_start = time.perf_counter()

    test_prediction = model.predict(
        X_test
    )

    inference_time = (
        time.perf_counter()
        - inference_start
    )


    # --------------------------------------------------------
    # Evaluate all splits
    # --------------------------------------------------------

    evaluations = [

        (
            "training",
            y_train,
            train_prediction
        ),

        (
            "validation",
            y_validation,
            validation_prediction
        ),

        (
            "testing",
            y_test,
            test_prediction
        )
    ]


    for (
        split_name,
        actual,
        predicted
    ) in evaluations:

        mae, rmse, r2 = calculate_metrics(
            actual,
            predicted
        )

        results.append({

            "model": model_name,

            "split": split_name,

            "rows": len(actual),

            "MAE": mae,

            "RMSE": rmse,

            "R2": r2,

            "training_time_seconds":
                training_time,

            "test_inference_time_seconds":
                inference_time
        })


    # --------------------------------------------------------
    # Store test predictions
    # --------------------------------------------------------

    safe_name = (
        model_name
        .lower()
        .replace(" ", "_")
    )

    predictions[
        f"{safe_name}_prediction"
    ] = test_prediction


    # --------------------------------------------------------
    # Save model
    # --------------------------------------------------------

    joblib.dump(
    model,
    MODELS_DIR / f"experiment3_{safe_name}.joblib"
)


# ============================================================
# Save result files
# ============================================================

results_df = pd.DataFrame(
    results
)

results_df.to_csv(
    RESULTS_FILE,
    index=False
)

predictions.to_csv(
    PREDICTIONS_FILE,
    index=False
)


# ============================================================
# Display complete comparison
# ============================================================

print("\n")
print("=" * 70)
print("EXPERIMENT 3 MODEL COMPARISON")
print("=" * 70)

print(

    results_df[
        [
            "model",
            "split",
            "rows",
            "MAE",
            "RMSE",
            "R2"
        ]
    ]
    .round(4)
    .to_string(index=False)

)


# ============================================================
# Final test comparison
# ============================================================

print("\n")
print("=" * 70)
print("FINAL TEST COMPARISON")
print("=" * 70)


test_results = (

    results_df[
        results_df["split"]
        == "testing"
    ]

    [
        [
            "model",
            "rows",
            "MAE",
            "RMSE",
            "R2"
        ]
    ]

    .sort_values("MAE")
)


print(
    test_results
    .round(4)
    .to_string(index=False)
)


# ============================================================
# Transition-specific test evaluation
# ============================================================

print("\n")
print("=" * 70)
print("TEST PERFORMANCE DURING CPU TRANSITIONS")
print("=" * 70)


predictions[
    "absolute_cpu_change"
] = (

    predictions[
        "future_cpu_30s"
    ]

    - predictions[
        "current_cpu_percentage"
    ]

).abs()


prediction_columns = {

    "Persistence Baseline":
        "persistence_prediction",

    "Linear Regression":
        "linear_regression_prediction",

    "Random Forest":
        "random_forest_prediction",

    "Gradient Boosting":
        "gradient_boosting_prediction"
}


transition_results = []


for threshold in [10, 20]:

    transition_df = predictions[
        predictions[
            "absolute_cpu_change"
        ] > threshold
    ]

    print(
        f"\nCPU change > {threshold} percentage points"
    )

    print(
        "Rows:",
        len(transition_df)
    )


    for model_name, column in (
        prediction_columns.items()
    ):

        if len(transition_df) == 0:
            continue

        actual = transition_df[
            "future_cpu_30s"
        ]

        predicted = transition_df[
            column
        ]

        mae, rmse, r2 = calculate_metrics(
            actual,
            predicted
        )

        transition_results.append({

            "threshold":
                f">{threshold}",

            "rows":
                len(transition_df),

            "model":
                model_name,

            "MAE":
                mae,

            "RMSE":
                rmse,

            "R2":
                r2
        })


        print(
            f"{model_name:22s} "
            f"MAE={mae:8.3f} "
            f"RMSE={rmse:8.3f} "
            f"R2={r2:8.3f}"
        )


pd.DataFrame(
    transition_results
).to_csv(
    EVALUATION_DIR / "experiment3_transition_results.csv",
    index=False
)


print("\n")
print("=" * 70)
print("FILES SAVED")
print("=" * 70)

print("-", RESULTS_FILE)
print("-", PREDICTIONS_FILE)
print("- experiment3_transition_results.csv")
print("- experiment3_linear_regression.joblib")
print("- experiment3_random_forest.joblib")
print("- experiment3_gradient_boosting.joblib")