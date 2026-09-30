import pandas as pd
import numpy as np

from sklearn.ensemble import HistGradientBoostingRegressor

from src.feature_engineering import (
    create_weekly_features,
    get_feature_columns
)


def train_ml_model(weekly_df):
    """
    Train a HistGradientBoosting model
    using historical weekly demand.
    """

    # ---------------------------------------------------------
    # CREATE FEATURES
    # ---------------------------------------------------------

    feature_df = create_weekly_features(
        weekly_df
    )

    feature_columns = get_feature_columns()

    # ---------------------------------------------------------
    # REMOVE ROWS WITHOUT ENOUGH HISTORY
    # ---------------------------------------------------------

    model_df = feature_df.dropna(
        subset=feature_columns + ["units_sold"]
    ).copy()

    if len(model_df) < 20:
        return {
            "model": None,
            "feature_df": feature_df,
            "message": (
                "Not enough historical data "
                "to train the ML model."
            )
        }

    # ---------------------------------------------------------
    # FEATURES AND TARGET
    # ---------------------------------------------------------

    X = model_df[
        feature_columns
    ]

    y = model_df[
        "units_sold"
    ]

    # ---------------------------------------------------------
    # TIME-BASED TRAIN / TEST SPLIT
    # ---------------------------------------------------------

    split_index = int(
        len(model_df) * 0.80
    )

    X_train = X.iloc[
        :split_index
    ]

    X_test = X.iloc[
        split_index:
    ]

    y_train = y.iloc[
        :split_index
    ]

    y_test = y.iloc[
        split_index:
    ]

    # ---------------------------------------------------------
    # MODEL
    # ---------------------------------------------------------

    model = HistGradientBoostingRegressor(
        max_iter=200,
        learning_rate=0.05,
        max_leaf_nodes=15,
        l2_regularization=1.0,
        random_state=42
    )

    model.fit(
        X_train,
        y_train
    )

    # ---------------------------------------------------------
    # TEST PREDICTIONS
    # ---------------------------------------------------------

    predictions = model.predict(
        X_test
    )

    predictions = np.maximum(
        predictions,
        0
    )

    evaluation = pd.DataFrame({
        "date": model_df.iloc[
            split_index:
        ]["date"].values,

        "actual": y_test.values,

        "predicted": predictions
    })

    return {
        "model": model,
        "feature_df": feature_df,
        "evaluation": evaluation,
        "X_train": X_train,
        "X_test": X_test,
        "y_train": y_train,
        "y_test": y_test,
        "message": "ML model trained successfully."
    }


def calculate_ml_wape(evaluation):
    """
    Calculate WAPE for ML model predictions.
    """

    if evaluation.empty:
        return np.nan

    actual = evaluation["actual"].values

    predicted = evaluation["predicted"].values

    denominator = np.sum(
        np.abs(actual)
    )

    if denominator == 0:
        return np.nan

    return (
        np.sum(
            np.abs(
                actual - predicted
            )
        )
        / denominator
    ) * 100
def recursive_ml_forecast(
    weekly_df,
    model,
    horizon=8
):
    """
    Generate recursive multi-week forecasts using the trained ML model.
    """

    if model is None:
        return pd.DataFrame()

    history = weekly_df.copy()

    history["date"] = pd.to_datetime(
        history["date"],
        errors="coerce"
    )

    history["units_sold"] = pd.to_numeric(
        history["units_sold"],
        errors="coerce"
    ).fillna(0)

    history = (
        history
        .dropna(subset=["date"])
        .sort_values("date")
        .reset_index(drop=True)
    )

    predictions = []

    feature_columns = get_feature_columns()

    for _ in range(horizon):

        next_date = (
            history["date"].iloc[-1]
            + pd.Timedelta(weeks=1)
        )

        temp = history.copy()

        new_row = pd.DataFrame({
            "date": [next_date],
            "units_sold": [np.nan]
        })

        temp = pd.concat(
            [temp, new_row],
            ignore_index=True
        )

        feature_df = create_weekly_features(temp)

        future_features = feature_df.iloc[[-1]][
            feature_columns
        ]

        future_features = future_features.fillna(0)

        prediction = model.predict(
            future_features
        )[0]

        prediction = max(
            float(prediction),
            0
        )

        predictions.append({
            "date": next_date,
            "predicted_demand": prediction
        })

        history = pd.concat(
            [
                history,
                pd.DataFrame({
                    "date": [next_date],
                    "units_sold": [prediction]
                })
            ],
            ignore_index=True
        )

    return pd.DataFrame(predictions)