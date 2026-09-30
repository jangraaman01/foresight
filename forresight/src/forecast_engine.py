import pandas as pd
import numpy as np
import streamlit as st

from src.ml_forecast import (
    train_ml_model,
    recursive_ml_forecast
)


# =========================================================
# PREPARE SALES DATA
# =========================================================

def prepare_weekly_sales(sales):

    sales_clean = sales.copy()

    # -----------------------------
    # Required columns
    # -----------------------------

    required_columns = [
        "date",
        "sku_id",
        "units_sold"
    ]

    missing_columns = [
        col
        for col in required_columns
        if col not in sales_clean.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Sales dataset is missing required columns: "
            f"{missing_columns}"
        )

    # -----------------------------
    # Clean date
    # -----------------------------

    sales_clean["date"] = pd.to_datetime(
        sales_clean["date"],
        errors="coerce"
    )

    # -----------------------------
    # Clean SKU
    # -----------------------------

    sales_clean["sku_id"] = (
        sales_clean["sku_id"]
        .astype(str)
        .str.strip()
    )

    # -----------------------------
    # Clean demand
    # -----------------------------

    sales_clean["units_sold"] = pd.to_numeric(
        sales_clean["units_sold"],
        errors="coerce"
    ).fillna(0)

    # Prevent negative demand
    sales_clean["units_sold"] = (
        sales_clean["units_sold"]
        .clip(lower=0)
    )

    # -----------------------------
    # Remove invalid rows
    # -----------------------------

    sales_clean = sales_clean.dropna(
        subset=[
            "date",
            "sku_id"
        ]
    )

    sales_clean = sales_clean[
        sales_clean["sku_id"] != ""
    ]

    return sales_clean


# =========================================================
# CALCULATE FORECAST CONFIDENCE INTERVAL
# =========================================================

def calculate_forecast_confidence(
    historical_values,
    forecast_values
):
    """
    Estimate forecast uncertainty using
    historical demand variability.

    Uses approximately 95% uncertainty
    based on 1.96 standard deviations.
    """

    historical_values = pd.to_numeric(
        pd.Series(historical_values),
        errors="coerce"
    ).dropna()

    forecast_values = pd.to_numeric(
        pd.Series(forecast_values),
        errors="coerce"
    ).fillna(0)

    forecast_values = forecast_values.clip(
        lower=0
    )

    # -----------------------------
    # Historical standard deviation
    # -----------------------------

    if len(historical_values) <= 1:

        std = 0.0

    else:

        std = float(
            historical_values.std()
        )

        if np.isnan(std):
            std = 0.0

    # -----------------------------
    # Approx. 95% uncertainty
    # -----------------------------

    uncertainty = 1.96 * std

    # -----------------------------
    # Lower / upper bounds
    # -----------------------------

    lower = (
        forecast_values - uncertainty
    ).clip(lower=0)

    upper = (
        forecast_values + uncertainty
    ).clip(lower=0)

    return (
        lower.to_numpy(),
        upper.to_numpy()
    )


# =========================================================
# CALCULATE DEMAND TREND
# =========================================================

def calculate_demand_trend(
    historical_values,
    forecast_values
):

    historical_values = pd.to_numeric(
        pd.Series(historical_values),
        errors="coerce"
    ).dropna()

    forecast_values = pd.to_numeric(
        pd.Series(forecast_values),
        errors="coerce"
    ).dropna()

    if historical_values.empty:
        return "Stable"

    if forecast_values.empty:
        return "Stable"

    # -----------------------------
    # Recent historical demand
    # -----------------------------

    historical_avg = float(
        historical_values
        .tail(4)
        .mean()
    )

    # -----------------------------
    # Forecast demand
    # -----------------------------

    forecast_avg = float(
        forecast_values.mean()
    )

    # -----------------------------
    # Handle zero historical demand
    # -----------------------------

    if historical_avg <= 0:

        if forecast_avg > 0:
            return "Increasing"

        return "Stable"

    # -----------------------------
    # Percentage change
    # -----------------------------

    change_pct = (
        (forecast_avg - historical_avg)
        / historical_avg
    ) * 100

    # -----------------------------
    # Classification
    # -----------------------------

    if change_pct >= 10:
        return "Increasing"

    if change_pct <= -10:
        return "Declining"

    return "Stable"


# =========================================================
# CALCULATE FORECAST CONFIDENCE LEVEL
# =========================================================

def calculate_confidence_level(
    historical_values,
    forecast_values
):

    historical_values = pd.to_numeric(
        pd.Series(historical_values),
        errors="coerce"
    ).dropna()

    forecast_values = pd.to_numeric(
        pd.Series(forecast_values),
        errors="coerce"
    ).dropna()

    if historical_values.empty:
        return "Low"

    historical_mean = float(
        historical_values.mean()
    )

    if len(historical_values) <= 1:

        historical_std = 0.0

    else:

        historical_std = float(
            historical_values.std()
        )

    if np.isnan(historical_std):
        historical_std = 0.0

    # -----------------------------
    # No meaningful demand
    # -----------------------------

    if historical_mean <= 0:
        return "Low"

    # -----------------------------
    # Coefficient of variation
    # -----------------------------

    coefficient_variation = (
        historical_std
        / historical_mean
    )

    # -----------------------------
    # Confidence classification
    # -----------------------------

    if coefficient_variation <= 0.25:
        return "High"

    if coefficient_variation <= 0.50:
        return "Medium"

    return "Low"


# =========================================================
# FORECAST ONE SKU
# =========================================================

def forecast_single_sku(
    sku_sales,
    horizon=8
):

    # -----------------------------
    # Validate horizon
    # -----------------------------

    try:
        horizon = int(horizon)
    except Exception:
        horizon = 8

    horizon = max(
        1,
        horizon
    )

    # -----------------------------
    # Create weekly demand
    # -----------------------------

    weekly = (
        sku_sales
        .set_index("date")
        .resample("W")["units_sold"]
        .sum()
        .reset_index()
    )

    weekly = (
        weekly
        .sort_values("date")
        .reset_index(drop=True)
    )

    # -----------------------------
    # Empty data
    # -----------------------------

    if weekly.empty:

        return pd.DataFrame(
            columns=[
                "date",
                "predicted_demand",
                "lower_bound",
                "upper_bound",
                "demand_trend",
                "forecast_confidence"
            ]
        )

    # =====================================================
    # TRAIN ML MODEL
    # =====================================================

    try:

        model_result = train_ml_model(
            weekly
        )

    except Exception:

        model_result = {
            "model": None
        }

    # -----------------------------
    # Safely extract model
    # -----------------------------

    if isinstance(
        model_result,
        dict
    ):

        model = model_result.get(
            "model"
        )

    else:

        model = model_result

    # =====================================================
    # ML FORECAST
    # =====================================================

    if model is not None:

        try:

            forecast = recursive_ml_forecast(
                weekly,
                model,
                horizon=horizon
            )

        except Exception:

            forecast = pd.DataFrame()

        if (
            isinstance(forecast, pd.DataFrame)
            and not forecast.empty
        ):

            forecast = forecast.copy()

            # -----------------------------
            # Required forecast column
            # -----------------------------

            if "predicted_demand" not in forecast.columns:

                forecast = pd.DataFrame()

            else:

                # -----------------------------
                # Clean prediction
                # -----------------------------

                forecast["predicted_demand"] = (
                    pd.to_numeric(
                        forecast[
                            "predicted_demand"
                        ],
                        errors="coerce"
                    )
                    .fillna(0)
                    .clip(lower=0)
                )

                # -----------------------------
                # Ensure forecast dates
                # -----------------------------

                if "date" not in forecast.columns:

                    forecast_dates = pd.date_range(
                        start=(
                            weekly["date"].max()
                            + pd.Timedelta(days=7)
                        ),
                        periods=horizon,
                        freq="7D"
                    )

                    forecast["date"] = (
                        forecast_dates
                    )

                else:

                    forecast["date"] = (
                        pd.to_datetime(
                            forecast["date"],
                            errors="coerce"
                        )
                    )

                # =================================================
                # CONFIDENCE INTERVAL
                # =================================================

                lower, upper = (
                    calculate_forecast_confidence(
                        weekly["units_sold"],
                        forecast[
                            "predicted_demand"
                        ]
                    )
                )

                forecast["lower_bound"] = lower

                forecast["upper_bound"] = upper

                # =================================================
                # DEMAND TREND
                # =================================================

                trend = calculate_demand_trend(
                    weekly["units_sold"],
                    forecast[
                        "predicted_demand"
                    ]
                )

                forecast["demand_trend"] = (
                    trend
                )

                # =================================================
                # CONFIDENCE LEVEL
                # =================================================

                confidence = (
                    calculate_confidence_level(
                        weekly["units_sold"],
                        forecast[
                            "predicted_demand"
                        ]
                    )
                )

                forecast[
                    "forecast_confidence"
                ] = confidence

                return forecast[
                    [
                        "date",
                        "predicted_demand",
                        "lower_bound",
                        "upper_bound",
                        "demand_trend",
                        "forecast_confidence"
                    ]
                ].reset_index(
                    drop=True
                )

    # =====================================================
    # FALLBACK FORECAST
    # =====================================================

    # Use last 8 weeks average demand
    recent_demand = (
        weekly["units_sold"]
        .tail(8)
        .mean()
    )

    if pd.isna(recent_demand):
        recent_demand = 0

    recent_demand = max(
        float(recent_demand),
        0
    )

    # -----------------------------
    # Future dates
    # -----------------------------

    future_dates = pd.date_range(
        start=(
            weekly["date"].max()
            + pd.Timedelta(days=7)
        ),
        periods=horizon,
        freq="7D"
    )

    # -----------------------------
    # Constant baseline forecast
    # -----------------------------

    predicted_values = np.repeat(
        recent_demand,
        horizon
    )

    # -----------------------------
    # Confidence interval
    # -----------------------------

    lower, upper = (
        calculate_forecast_confidence(
            weekly["units_sold"],
            predicted_values
        )
    )

    # -----------------------------
    # Trend
    # -----------------------------

    trend = calculate_demand_trend(
        weekly["units_sold"],
        predicted_values
    )

    # -----------------------------
    # Confidence
    # -----------------------------

    confidence = calculate_confidence_level(
        weekly["units_sold"],
        predicted_values
    )

    return pd.DataFrame({

        "date": future_dates,

        "predicted_demand": predicted_values,

        "lower_bound": lower,

        "upper_bound": upper,

        "demand_trend": trend,

        "forecast_confidence": confidence

    })


# =========================================================
# FORECAST ALL SKUs
# =========================================================

@st.cache_data
def generate_all_forecasts(
    sales,
    horizon=8
):

    # -----------------------------
    # Prepare sales
    # -----------------------------

    sales_clean = prepare_weekly_sales(
        sales
    )

    # -----------------------------
    # Empty result structure
    # -----------------------------

    output_columns = [
        "sku_id",
        "date",
        "predicted_demand",
        "lower_bound",
        "upper_bound",
        "demand_trend",
        "forecast_confidence"
    ]

    if sales_clean.empty:

        return pd.DataFrame(
            columns=output_columns
        )

    forecast_results = []

    # =====================================================
    # FORECAST SKU BY SKU
    # =====================================================

    unique_skus = (
        sales_clean["sku_id"]
        .dropna()
        .unique()
    )

    for sku in sorted(
        unique_skus,
        key=lambda x: str(x)
    ):

        sku_sales = sales_clean[
            sales_clean["sku_id"] == sku
        ].copy()

        try:

            forecast = forecast_single_sku(
                sku_sales,
                horizon=horizon
            )

        except Exception:

            forecast = pd.DataFrame()

        if forecast.empty:
            continue

        forecast = forecast.copy()

        forecast["sku_id"] = sku

        forecast_results.append(
            forecast
        )

    # =====================================================
    # NO FORECAST RESULTS
    # =====================================================

    if not forecast_results:

        return pd.DataFrame(
            columns=output_columns
        )

    # =====================================================
    # COMBINE FORECASTS
    # =====================================================

    result = pd.concat(
        forecast_results,
        ignore_index=True
    )

    # =====================================================
    # CLEAN NUMERIC VALUES
    # =====================================================

    numeric_columns = [
        "predicted_demand",
        "lower_bound",
        "upper_bound"
    ]

    for column in numeric_columns:

        result[column] = (
            pd.to_numeric(
                result[column],
                errors="coerce"
            )
            .fillna(0)
            .clip(lower=0)
        )

    # =====================================================
    # CLEAN DATES
    # =====================================================

    result["date"] = pd.to_datetime(
        result["date"],
        errors="coerce"
    )

    # Remove invalid dates
    result = result.dropna(
        subset=["date"]
    )

    # =====================================================
    # CLEAN TEXT FIELDS
    # =====================================================

    result["demand_trend"] = (
        result["demand_trend"]
        .fillna("Stable")
        .astype(str)
    )

    result["forecast_confidence"] = (
        result["forecast_confidence"]
        .fillna("Low")
        .astype(str)
    )

    # =====================================================
    # SORT
    # =====================================================

    result = (
        result
        .sort_values(
            [
                "sku_id",
                "date"
            ]
        )
        .reset_index(
            drop=True
        )
    )

    # =====================================================
    # FINAL COLUMN ORDER
    # =====================================================

    return result[
        output_columns
    ]


# =========================================================
# SKU LEVEL FORECAST SUMMARY
# =========================================================

@st.cache_data
def generate_forecast_summary(
    sales,
    horizon=8
):

    forecasts = generate_all_forecasts(
        sales,
        horizon=horizon
    )

    # =====================================================
    # EMPTY RESULT
    # =====================================================

    output_columns = [
        "sku_id",
        "avg_weekly_demand",
        "total_forecast_demand",
        "min_forecast_demand",
        "max_forecast_demand",
        "avg_lower_bound",
        "avg_upper_bound",
        "demand_trend",
        "forecast_confidence"
    ]

    if forecasts.empty:

        return pd.DataFrame(
            columns=output_columns
        )

    # =====================================================
    # SKU AGGREGATION
    # =====================================================

    summary = (
        forecasts
        .groupby(
            "sku_id",
            as_index=False
        )
        .agg(

            avg_weekly_demand=(
                "predicted_demand",
                "mean"
            ),

            total_forecast_demand=(
                "predicted_demand",
                "sum"
            ),

            min_forecast_demand=(
                "predicted_demand",
                "min"
            ),

            max_forecast_demand=(
                "predicted_demand",
                "max"
            ),

            avg_lower_bound=(
                "lower_bound",
                "mean"
            ),

            avg_upper_bound=(
                "upper_bound",
                "mean"
            )

        )
    )

    # =====================================================
    # DEMAND TREND
    # =====================================================

    trend_map = (
        forecasts
        .groupby("sku_id")[
            "demand_trend"
        ]
        .first()
    )

    summary["demand_trend"] = (
        summary["sku_id"]
        .map(trend_map)
        .fillna("Stable")
    )

    # =====================================================
    # FORECAST CONFIDENCE
    # =====================================================

    confidence_map = (
        forecasts
        .groupby("sku_id")[
            "forecast_confidence"
        ]
        .first()
    )

    summary["forecast_confidence"] = (
        summary["sku_id"]
        .map(confidence_map)
        .fillna("Low")
    )

    # =====================================================
    # CLEAN NUMERIC VALUES
    # =====================================================

    numeric_columns = [
        "avg_weekly_demand",
        "total_forecast_demand",
        "min_forecast_demand",
        "max_forecast_demand",
        "avg_lower_bound",
        "avg_upper_bound"
    ]

    for column in numeric_columns:

        summary[column] = (
            pd.to_numeric(
                summary[column],
                errors="coerce"
            )
            .fillna(0)
            .clip(lower=0)
        )

    # =====================================================
    # FINAL COLUMN ORDER
    # =====================================================

    return summary[
        output_columns
    ]
print("FORESIGHT FORECAST ENGINE LOADED")
print("generate_all_forecasts:", "generate_all_forecasts" in globals())