import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DIR = BASE_DIR / "data" / "processed"

df = pd.read_csv(PROCESSED_DIR / "model_predictions.csv")

df["cpu_change_future"] = abs(
    df["future_cpu_30s"] - df["current_cpu_percentage"]
)

models = {
    "Persistence": "persistence_prediction",
    "Linear Regression": "linear_regression_prediction",
    "Random Forest": "random_forest_prediction",
    "Gradient Boosting": "gradient_boosting_prediction"
}

groups = {
    "All observations": df,
    "Change > 10": df[df["cpu_change_future"] > 10],
    "Change > 20": df[df["cpu_change_future"] > 20],
    "Change > 50": df[df["cpu_change_future"] > 50]
}

results = []

for group_name, group in groups.items():

    print("\n======================================")
    print(group_name)
    print("Rows:", len(group))
    print("======================================")

    for model_name, column in models.items():

        if len(group) == 0:
            continue

        actual = group["future_cpu_30s"]
        predicted = group[column]

        mae = mean_absolute_error(actual, predicted)
        rmse = np.sqrt(mean_squared_error(actual, predicted))

        # R² is not reliable/defined for fewer than 2 observations
        if len(group) >= 2:
            r2 = r2_score(actual, predicted)
        else:
            r2 = np.nan

        results.append({
            "group": group_name,
            "rows": len(group),
            "model": model_name,
            "MAE": mae,
            "RMSE": rmse,
            "R2": r2
        })

        print(
            f"{model_name:20s} "
            f"MAE={mae:8.2f} "
            f"RMSE={rmse:8.2f} "
            f"R2={r2:8.3f}"
        )


results_df = pd.DataFrame(results)

results_df.to_csv(
    PROCESSED_DIR / "transition_results.csv",
    index=False
)

print("\nSaved: transition_results.csv")