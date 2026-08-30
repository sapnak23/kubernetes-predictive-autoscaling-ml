import time
import joblib
import numpy as np
import pandas as pd

from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from pathlib import Path

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DIR = BASE_DIR / "data" / "processed"
MODELS_DIR = BASE_DIR / "models"

INPUT_FILE = PROCESSED_DIR / "ml_dataset.csv"
RESULTS_FILE = PROCESSED_DIR / "model_results.csv"
PREDICTIONS_FILE = PROCESSED_DIR / "model_predictions.csv"

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

TARGET = "future_cpu_30s"


# ---------------------------------------------------------
# Metrics
# ---------------------------------------------------------

def calculate_metrics(actual, predicted):

    mae = mean_absolute_error(actual, predicted)

    rmse = np.sqrt(
        mean_squared_error(actual, predicted)
    )

    r2 = r2_score(actual, predicted)

    return mae, rmse, r2


# ---------------------------------------------------------
# Load dataset
# ---------------------------------------------------------

df = pd.read_csv(INPUT_FILE)

print("Dataset loaded successfully.")
print("Total rows:", len(df))


# ---------------------------------------------------------
# Create workload-based split
# ---------------------------------------------------------

train_df = df[
    df["experiment"].isin(TRAIN_EXPERIMENTS)
].copy()

validation_df = df[
    df["experiment"].isin(VALIDATION_EXPERIMENTS)
].copy()

test_df = df[
    df["experiment"].isin(TEST_EXPERIMENTS)
].copy()


print("\nDataset split:")
print("Training rows:", len(train_df))
print("Validation rows:", len(validation_df))
print("Testing rows:", len(test_df))


X_train = train_df[FEATURES]
y_train = train_df[TARGET]

X_validation = validation_df[FEATURES]
y_validation = validation_df[TARGET]

X_test = test_df[FEATURES]
y_test = test_df[TARGET]


# ---------------------------------------------------------
# Models
# ---------------------------------------------------------

models = {

    "Linear Regression":
        LinearRegression(),

    "Random Forest":
        RandomForestRegressor(
            n_estimators=300,
            random_state=42,
            n_jobs=-1
        ),

    "Gradient Boosting":
        GradientBoostingRegressor(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=3,
            random_state=42
        )
}


results = []

predictions = test_df[
    [
        "timestamp",
        "experiment",
        "current_cpu_percentage",
        "future_cpu_30s"
    ]
].copy()

MODELS_DIR.mkdir(exist_ok=True)
# ---------------------------------------------------------
# Train and evaluate models
# ---------------------------------------------------------

for model_name, model in models.items():

    print("\n------------------------------------")
    print("Training:", model_name)
    print("------------------------------------")

    start_training = time.perf_counter()

    model.fit(
        X_train,
        y_train
    )

    training_time = (
        time.perf_counter()
        - start_training
    )


    # Predictions

    train_pred = model.predict(X_train)

    validation_pred = model.predict(
        X_validation
    )


    start_inference = time.perf_counter()

    test_pred = model.predict(X_test)

    inference_time = (
        time.perf_counter()
        - start_inference
    )


    # Metrics

    for split_name, actual, predicted in [

        (
            "training",
            y_train,
            train_pred
        ),

        (
            "validation",
            y_validation,
            validation_pred
        ),

        (
            "testing",
            y_test,
            test_pred
        )
    ]:

        mae, rmse, r2 = calculate_metrics(
            actual,
            predicted
        )

        results.append({

            "model": model_name,
            "split": split_name,

            "MAE": mae,
            "RMSE": rmse,
            "R2": r2,

            "training_time_seconds":
                training_time,

            "test_inference_time_seconds":
                inference_time,

            "test_rows":
                len(test_df)
        })


    # Save test predictions

    safe_name = (
        model_name
        .lower()
        .replace(" ", "_")
    )

    predictions[
        safe_name + "_prediction"
    ] = test_pred


    # Save trained model

    joblib.dump(
    model,
    MODELS_DIR / (safe_name + "_model.joblib")
)


# ---------------------------------------------------------
# Add persistence baseline
# ---------------------------------------------------------

persistence_prediction = (
    test_df["current_cpu_percentage"]
)

predictions[
    "persistence_prediction"
] = persistence_prediction


# ---------------------------------------------------------
# Save outputs
# ---------------------------------------------------------

results_df = pd.DataFrame(results)

results_df.to_csv(
    RESULTS_FILE,
    index=False
)

predictions.to_csv(
    PREDICTIONS_FILE,
    index=False
)


# ---------------------------------------------------------
# Display results
# ---------------------------------------------------------

print("\n\n====================================")
print("MODEL COMPARISON")
print("====================================")

print(
    results_df[
        [
            "model",
            "split",
            "MAE",
            "RMSE",
            "R2"
        ]
    ]
    .round(4)
    .to_string(index=False)
)


print("\n====================================")
print("FINAL TEST COMPARISON")
print("====================================")

test_results = results_df[
    results_df["split"] == "testing"
].copy()


# Persistence metrics

p_mae, p_rmse, p_r2 = calculate_metrics(
    y_test,
    persistence_prediction
)


persistence_row = pd.DataFrame(
    [{
        "model":
            "Persistence Baseline",

        "MAE":
            p_mae,

        "RMSE":
            p_rmse,

        "R2":
            p_r2
    }]
)


comparison = pd.concat(
    [
        persistence_row,

        test_results[
            [
                "model",
                "MAE",
                "RMSE",
                "R2"
            ]
        ]
    ],
    ignore_index=True
)


print(
    comparison
    .round(4)
    .to_string(index=False)
)


print("\nSaved:")
print("-", RESULTS_FILE)
print("-", PREDICTIONS_FILE)

print(
    "- linear_regression_model.joblib"
)

print(
    "- random_forest_model.joblib"
)

print(
    "- gradient_boosting_model.joblib"
)