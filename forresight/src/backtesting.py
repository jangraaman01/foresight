import pandas as pd
import numpy as np

from sklearn.ensemble import HistGradientBoostingRegressor

from src.feature_engineering import (
    create_weekly_features,
    get_feature_columns
)

from src.model_evaluation import calculate_wape


def rolling_origin_backtest(
    weekly_df,
    min_train_size=20,
    test_size=4,
    step_size=4
):
    """
    Rolling-origin time-series backtesting
    for the ML demand forecasting model.
    """

    feature_df = create_weekly_features(
        weekly_df
    )

    feature_columns = get_feature_columns()

    model_df = feature_df.dropna(
        subset=feature_columns + ["units_sold"]
    ).reset_index(drop=True)

    results = []

    if len(model_df) < (
        min_train_size + test_size
    ):
        return pd.DataFrame()

    # ---------------------------------------------------------
    # ROLLING TIME WINDOWS
    # ---------------------------------------------------------

    train_end = min_train_size

    while (
        train_end + test_size
        <= len(model_df)
    ):

        train_data = model_df.iloc[
            :train_end
        ]

        test_data = model_df.iloc[
            train_end:
            train_end + test_size
        ]

        X_train = train_data[
            feature_columns
        ]

        y_train = train_data[
            "units_sold"
        ]

        X_test = test_data[
            feature_columns
        ]

        y_test = test_data[
            "units_sold"
        ]

        # -----------------------------------------------------
        # TRAIN MODEL
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # PREDICT
        # -----------------------------------------------------

        predictions = model.predict(
            X_test
        )

        predictions = np.maximum(
            predictions,
            0
        )

        # -----------------------------------------------------
        # WAPE
        # -----------------------------------------------------

        wape = calculate_wape(
            y_test,
            predictions
        )

        results.append({
            "train_end": train_end,
            "test_start": test_data[
                "date"
            ].min(),
            "test_end": test_data[
                "date"
            ].max(),
            "wape": wape
        })

        train_end += step_size

    return pd.DataFrame(
        results
    )


def summarize_backtest(results):
    """
    Summarize rolling-origin results.
    """

    if results.empty:
        return {
            "mean_wape": np.nan,
            "median_wape": np.nan,
            "folds": 0
        }

    return {
        "mean_wape": results[
            "wape"
        ].mean(),

        "median_wape": results[
            "wape"
        ].median(),

        "folds": len(results)
    }