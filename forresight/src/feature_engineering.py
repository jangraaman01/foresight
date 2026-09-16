import pandas as pd
import numpy as np


def create_weekly_features(weekly_df):
    """
    Create time-series features for weekly SKU demand.

    Expected columns:
        date
        units_sold
    """

    df = weekly_df.copy()

    # ---------------------------------------------------------
    # CHECK REQUIRED COLUMNS
    # ---------------------------------------------------------

    required_columns = ["date", "units_sold"]

    missing_columns = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    # ---------------------------------------------------------
    # DATE PREPARATION
    # ---------------------------------------------------------

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce"
    )

    df["units_sold"] = pd.to_numeric(
        df["units_sold"],
        errors="coerce"
    ).fillna(0)

    df = df.dropna(
        subset=["date"]
    )

    df = df.sort_values(
        "date"
    ).reset_index(drop=True)

    # ---------------------------------------------------------
    # LAG FEATURES
    # ---------------------------------------------------------

    df["lag_1"] = df["units_sold"].shift(1)

    df["lag_2"] = df["units_sold"].shift(2)

    df["lag_4"] = df["units_sold"].shift(4)

    df["lag_8"] = df["units_sold"].shift(8)

    # ---------------------------------------------------------
    # ROLLING DEMAND FEATURES
    # ---------------------------------------------------------

    df["rolling_mean_4"] = (
        df["units_sold"]
        .shift(1)
        .rolling(window=4)
        .mean()
    )

    df["rolling_mean_8"] = (
        df["units_sold"]
        .shift(1)
        .rolling(window=8)
        .mean()
    )

    df["rolling_std_4"] = (
        df["units_sold"]
        .shift(1)
        .rolling(window=4)
        .std()
    )

    # ---------------------------------------------------------
    # TREND FEATURES
    # ---------------------------------------------------------

    df["demand_change_1w"] = (
        df["units_sold"].shift(1)
        - df["units_sold"].shift(2)
    )

    df["demand_change_4w"] = (
        df["units_sold"].shift(1)
        - df["units_sold"].shift(5)
    )

    # ---------------------------------------------------------
    # CALENDAR FEATURES
    # ---------------------------------------------------------

    df["week_of_year"] = (
        df["date"].dt.isocalendar().week.astype(int)
    )

    df["month"] = (
        df["date"].dt.month
    )

    df["quarter"] = (
        df["date"].dt.quarter
    )

    # ---------------------------------------------------------
    # YEAR TREND
    # ---------------------------------------------------------

    df["time_index"] = np.arange(
        len(df)
    )

    # ---------------------------------------------------------
    # REMOVE INFINITE VALUES
    # ---------------------------------------------------------

    df = df.replace(
        [np.inf, -np.inf],
        np.nan
    )

    return df


def get_feature_columns():
    """
    Return the features used by the ML model.
    """

    return [
        "lag_1",
        "lag_2",
        "lag_4",
        "lag_8",
        "rolling_mean_4",
        "rolling_mean_8",
        "rolling_std_4",
        "demand_change_1w",
        "demand_change_4w",
        "week_of_year",
        "month",
        "quarter",
        "time_index"
    ]