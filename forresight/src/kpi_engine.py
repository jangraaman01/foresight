import numpy as np
import pandas as pd


# ============================================================
# SAFE HELPERS
# ============================================================

def _safe_numeric(value, default=0.0):
    try:
        value = float(value)

        if np.isnan(value) or np.isinf(value):
            return default

        return value

    except (TypeError, ValueError):
        return default


def _safe_divide(numerator, denominator, default=0.0):
    numerator = _safe_numeric(numerator)
    denominator = _safe_numeric(denominator)

    if denominator == 0:
        return default

    return numerator / denominator


# ============================================================
# SALES KPIs
# ============================================================

def calculate_sales_kpis(sales):

    if sales is None or sales.empty:
        return {
            "total_units_sold": 0,
            "total_revenue": 0.0,
            "average_daily_units": 0.0,
            "average_daily_revenue": 0.0,
            "active_skus": 0,
            "sales_days": 0,
        }

    df = sales.copy()

    total_units = _safe_numeric(
        df["units_sold"].sum()
        if "units_sold" in df.columns
        else 0
    )

    total_revenue = _safe_numeric(
        df["revenue"].sum()
        if "revenue" in df.columns
        else 0
    )

    active_skus = (
        df["sku_id"].nunique()
        if "sku_id" in df.columns
        else 0
    )

    sales_days = (
        df["date"].nunique()
        if "date" in df.columns
        else 0
    )

    return {
        "total_units_sold": total_units,
        "total_revenue": total_revenue,
        "average_daily_units": _safe_divide(
            total_units,
            sales_days,
        ),
        "average_daily_revenue": _safe_divide(
            total_revenue,
            sales_days,
        ),
        "active_skus": active_skus,
        "sales_days": sales_days,
    }


# ============================================================
# INVENTORY KPIs
# ============================================================

def calculate_inventory_kpis(inventory):

    if inventory is None or inventory.empty:
        return {
            "total_on_hand": 0.0,
            "total_on_order": 0.0,
            "inventory_skus": 0,
            "average_lead_time_days": 0.0,
        }

    df = inventory.copy()

    if "date" in df.columns:

        latest_date = df["date"].max()

        latest = df[
            df["date"] == latest_date
        ].copy()

    else:
        latest = df.copy()

    total_on_hand = _safe_numeric(
        latest["on_hand_units"].sum()
        if "on_hand_units" in latest.columns
        else 0
    )

    total_on_order = _safe_numeric(
        latest["on_order_units"].sum()
        if "on_order_units" in latest.columns
        else 0
    )

    inventory_skus = (
        latest["sku_id"].nunique()
        if "sku_id" in latest.columns
        else 0
    )

    average_lead_time_days = _safe_numeric(
        latest["lead_time_days"].mean()
        if "lead_time_days" in latest.columns
        else 0
    )

    return {
        "total_on_hand": total_on_hand,
        "total_on_order": total_on_order,
        "inventory_skus": inventory_skus,
        "average_lead_time_days": average_lead_time_days,
    }


# ============================================================
# FORECAST KPIs
# ============================================================

def calculate_forecast_kpis(forecast_summary):

    if (
        forecast_summary is None
        or forecast_summary.empty
    ):
        return {
            "forecast_skus": 0,
            "total_forecast_demand": 0.0,
            "average_weekly_demand": 0.0,
            "increasing_demand_skus": 0,
            "declining_demand_skus": 0,
            "stable_demand_skus": 0,
        }

    df = forecast_summary.copy()

    forecast_skus = (
        df["sku_id"].nunique()
        if "sku_id" in df.columns
        else len(df)
    )

    total_forecast_demand = _safe_numeric(
        df["total_forecast_demand"].sum()
        if "total_forecast_demand" in df.columns
        else 0
    )

    average_weekly_demand = _safe_numeric(
        df["avg_weekly_demand"].mean()
        if "avg_weekly_demand" in df.columns
        else 0
    )

    increasing = 0
    declining = 0
    stable = 0

    if "demand_trend" in df.columns:

        trend = (
            df["demand_trend"]
            .astype(str)
            .str.strip()
            .str.lower()
        )

        increasing = int(
            trend.str.contains("increas").sum()
        )

        declining = int(
            trend.str.contains("declin").sum()
        )

        stable = int(
            trend.str.contains("stable").sum()
        )

    return {
        "forecast_skus": forecast_skus,
        "total_forecast_demand": total_forecast_demand,
        "average_weekly_demand": average_weekly_demand,
        "increasing_demand_skus": increasing,
        "declining_demand_skus": declining,
        "stable_demand_skus": stable,
    }


# ============================================================
# RISK KPIs
# ============================================================

def calculate_risk_kpis(intelligence_df):

    if (
        intelligence_df is None
        or intelligence_df.empty
    ):
        return {
            "critical_risk_skus": 0,
            "high_risk_skus": 0,
            "medium_risk_skus": 0,
            "low_risk_skus": 0,
            "stockout_risk_skus": 0,
            "overstock_risk_skus": 0,
        }

    df = intelligence_df.copy()

    if "risk_severity" in df.columns:

        severity = (
            df["risk_severity"]
            .astype(str)
            .str.strip()
            .str.lower()
        )

    else:

        severity = pd.Series(
            "",
            index=df.index,
        )

    critical = int(
        severity.eq("critical").sum()
    )

    high = int(
        severity.eq("high").sum()
    )

    medium = int(
        severity.eq("medium").sum()
    )

    low = int(
        severity.eq("low").sum()
    )

    stockout_risk = 0

    if "stockout_risk_percent" in df.columns:

        values = pd.to_numeric(
            df["stockout_risk_percent"],
            errors="coerce",
        ).fillna(0)

        stockout_risk = int(
            (values >= 25).sum()
        )

    overstock_risk = 0

    if "overstock_risk_percent" in df.columns:

        values = pd.to_numeric(
            df["overstock_risk_percent"],
            errors="coerce",
        ).fillna(0)

        overstock_risk = int(
            (values >= 25).sum()
        )

    return {
        "critical_risk_skus": critical,
        "high_risk_skus": high,
        "medium_risk_skus": medium,
        "low_risk_skus": low,
        "stockout_risk_skus": stockout_risk,
        "overstock_risk_skus": overstock_risk,
    }


# ============================================================
# FINANCIAL KPIs
# ============================================================

def calculate_financial_kpis(intelligence_df):

    if (
        intelligence_df is None
        or intelligence_df.empty
    ):
        return {
            "sales_at_risk": 0.0,
            "capital_locked": 0.0,
            "total_financial_exposure": 0.0,
            "exposure_skus": 0,
        }

    df = intelligence_df.copy()

    sales_at_risk = _safe_numeric(
        df["sales_at_risk"].sum()
        if "sales_at_risk" in df.columns
        else 0
    )

    capital_locked = _safe_numeric(
        df["capital_locked"].sum()
        if "capital_locked" in df.columns
        else 0
    )

    if "total_financial_exposure" in df.columns:

        total_exposure = _safe_numeric(
            df["total_financial_exposure"].sum()
        )

    else:

        total_exposure = (
            sales_at_risk
            + capital_locked
        )

    exposure_skus = 0

    if "total_financial_exposure" in df.columns:

        exposure_values = pd.to_numeric(
            df["total_financial_exposure"],
            errors="coerce",
        ).fillna(0)

        exposure_skus = int(
            (exposure_values > 0).sum()
        )

    return {
        "sales_at_risk": sales_at_risk,
        "capital_locked": capital_locked,
        "total_financial_exposure": total_exposure,
        "exposure_skus": exposure_skus,
    }


# ============================================================
# BUSINESS PRIORITY KPIs
# ============================================================

def calculate_priority_kpis(intelligence_df):

    if (
        intelligence_df is None
        or intelligence_df.empty
        or "business_priority" not in intelligence_df.columns
    ):
        return {
            "protect_sales": 0,
            "reduce_overstock": 0,
            "healthy": 0,
        }

    priority = (
        intelligence_df["business_priority"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    return {
        "protect_sales": int(
            priority.str.contains(
                "protect sales"
            ).sum()
        ),
        "reduce_overstock": int(
            priority.str.contains(
                "reduce overstock"
            ).sum()
        ),
        "healthy": int(
            priority.str.contains(
                "healthy"
            ).sum()
        ),
    }


# ============================================================
# COMPLETE KPI ENGINE
# ============================================================

def calculate_all_kpis(
    sales,
    inventory,
    forecast_summary,
    intelligence_df,
):
    """
    Centralized FORESIGHT KPI engine.
    """

    return {
        "sales": calculate_sales_kpis(
            sales
        ),

        "inventory": calculate_inventory_kpis(
            inventory
        ),

        "forecast": calculate_forecast_kpis(
            forecast_summary
        ),

        "risk": calculate_risk_kpis(
            intelligence_df
        ),

        "financial": calculate_financial_kpis(
            intelligence_df
        ),

        "priority": calculate_priority_kpis(
            intelligence_df
        ),
    }


# ============================================================
# FORMATTING
# ============================================================

def format_currency(
    value,
    decimals=0,
):

    value = _safe_numeric(value)

    return f"₹{value:,.{decimals}f}"


def format_number(
    value,
    decimals=0,
):

    value = _safe_numeric(value)

    return f"{value:,.{decimals}f}"


def format_percentage(
    value,
    decimals=1,
):

    value = _safe_numeric(value)

    return f"{value:.{decimals}f}%"