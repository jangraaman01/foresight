import numpy as np
import pandas as pd


# ============================================================
# RISK SEVERITY
# ============================================================
def calculate_risk_severity(row):
    """
    Calculate business risk severity using operational
    and financial exposure.
    """

    stockout_risk = float(
        row.get("stockout_risk_percent", 0) or 0
    )

    overstock_risk = float(
        row.get("overstock_risk_percent", 0) or 0
    )

    sales_at_risk = float(
        row.get("sales_at_risk", 0) or 0
    )

    capital_locked = float(
        row.get("capital_locked", 0) or 0
    )

    weeks_of_supply = float(
        row.get("weeks_of_supply", 0) or 0
    )

    if (
        stockout_risk >= 80
        or sales_at_risk >= 100000
        or capital_locked >= 100000
    ):
        return "Critical"

    if (
        stockout_risk >= 50
        or overstock_risk >= 50
        or weeks_of_supply >= 12
        or sales_at_risk >= 50000
        or capital_locked >= 50000
    ):
        return "High"

    if (
        stockout_risk >= 25
        or overstock_risk >= 25
        or weeks_of_supply >= 8
        or sales_at_risk >= 10000
        or capital_locked >= 10000
    ):
        return "Medium"

    return "Low"


# ============================================================
# BUSINESS PRIORITY
# ============================================================
def calculate_business_priority(row):
    """
    Determine whether management should primarily protect
    sales or reduce excess inventory.
    """

    sales_at_risk = float(
        row.get("sales_at_risk", 0) or 0
    )

    capital_locked = float(
        row.get("capital_locked", 0) or 0
    )

    if sales_at_risk <= 0 and capital_locked <= 0:
        return "Healthy"

    if sales_at_risk >= capital_locked:
        return "Protect Sales"

    return "Reduce Overstock"


# ============================================================
# RECOMMENDED ACTION
# ============================================================
def calculate_recommended_action(row):
    """
    Convert risk measurements into an operational action.
    """

    stockout_risk = float(
        row.get("stockout_risk_percent", 0) or 0
    )

    weeks_of_supply = float(
        row.get("weeks_of_supply", 0) or 0
    )

    if stockout_risk >= 50:
        return "Reorder Now"

    if stockout_risk >= 25:
        return "Monitor & Replenish"

    if weeks_of_supply >= 12:
        return "Markdown / Clear"

    if weeks_of_supply >= 8:
        return "Reduce Future Orders"

    return "Healthy"


# ============================================================
# COMPLETE BUSINESS INTELLIGENCE
# ============================================================
def calculate_business_intelligence(df, target_weeks=8):
    """
    Calculate common business-risk metrics for all SKUs.

    Expected columns:
        avg_weekly_demand
        inventory_position
        lead_time_days
        estimated_selling_price
        unit_cost

    Optional columns:
        stockout_risk_percent
        overstock_risk_percent
        sales_at_risk
        capital_locked
    """

    result = df.copy()

    # --------------------------------------------------------
    # Required numeric columns
    # --------------------------------------------------------
    numeric_columns = [
        "avg_weekly_demand",
        "inventory_position",
        "lead_time_days",
        "estimated_selling_price",
        "unit_cost",
    ]

    for column in numeric_columns:

        if column not in result.columns:
            result[column] = 0

        result[column] = pd.to_numeric(
            result[column],
            errors="coerce",
        ).fillna(0)

    # --------------------------------------------------------
    # Lead-time demand
    # --------------------------------------------------------
    result["lead_time_weeks"] = (
        result["lead_time_days"] / 7
    )

    result["lead_time_demand"] = (
        result["avg_weekly_demand"]
        * result["lead_time_weeks"]
    )

    # --------------------------------------------------------
    # Weeks of supply
    # --------------------------------------------------------
    result["weeks_of_supply"] = np.where(
        result["avg_weekly_demand"] > 0,
        result["inventory_position"]
        / result["avg_weekly_demand"],
        np.inf,
    )

    # --------------------------------------------------------
    # Stockout risk
    # --------------------------------------------------------
    result["stockout_risk_percent"] = np.where(
        result["lead_time_demand"] > 0,
        (
            (
                result["lead_time_demand"]
                - result["inventory_position"]
            )
            / result["lead_time_demand"]
        )
        * 100,
        0,
    )

    result["stockout_risk_percent"] = (
        result["stockout_risk_percent"]
        .clip(0, 100)
    )

    # --------------------------------------------------------
    # Overstock risk
    # --------------------------------------------------------
    result["overstock_risk_percent"] = np.where(
        result["weeks_of_supply"] > target_weeks,
        (
            (
                result["weeks_of_supply"]
                - target_weeks
            )
            / target_weeks
        )
        * 100,
        0,
    )

    result["overstock_risk_percent"] = (
        result["overstock_risk_percent"]
        .replace(
            [np.inf, -np.inf],
            0,
        )
        .clip(0, 100)
    )

    # --------------------------------------------------------
    # Stockout units
    # --------------------------------------------------------
    result["stockout_units_at_risk"] = (
        result["lead_time_demand"]
        - result["inventory_position"]
    ).clip(lower=0)

    # --------------------------------------------------------
    # Sales at risk
    # --------------------------------------------------------
    result["sales_at_risk"] = (
        result["stockout_units_at_risk"]
        * result["estimated_selling_price"]
    )

    # --------------------------------------------------------
    # Target inventory
    # --------------------------------------------------------
    result["target_inventory"] = (
        result["avg_weekly_demand"]
        * target_weeks
    )

    # --------------------------------------------------------
    # Excess inventory
    # --------------------------------------------------------
    result["excess_units"] = (
        result["inventory_position"]
        - result["target_inventory"]
    ).clip(lower=0)

    # --------------------------------------------------------
    # Capital locked
    # --------------------------------------------------------
    result["capital_locked"] = (
        result["excess_units"]
        * result["unit_cost"]
    )

    # --------------------------------------------------------
    # Total exposure
    # --------------------------------------------------------
    result["total_financial_exposure"] = (
        result["sales_at_risk"]
        + result["capital_locked"]
    )

    # --------------------------------------------------------
    # Business priority
    # --------------------------------------------------------
    result["business_priority"] = result.apply(
        calculate_business_priority,
        axis=1,
    )

    # --------------------------------------------------------
    # Risk severity
    # --------------------------------------------------------
    result["risk_severity"] = result.apply(
        calculate_risk_severity,
        axis=1,
    )

    # --------------------------------------------------------
    # Recommended action
    # --------------------------------------------------------
    result["recommended_action"] = result.apply(
        calculate_recommended_action,
        axis=1,
    )

    # --------------------------------------------------------
    # Priority score
    # --------------------------------------------------------
    result["priority_score"] = (
        result["stockout_risk_percent"] * 0.35
        + result["overstock_risk_percent"] * 0.20
        + np.minimum(
            result["sales_at_risk"] / 1000,
            100,
        ) * 0.25
        + np.minimum(
            result["capital_locked"] / 1000,
            100,
        ) * 0.20
    )

    result["priority_score"] = (
        result["priority_score"]
        .round(2)
    )

    # --------------------------------------------------------
    # Risk ordering
    # --------------------------------------------------------
    severity_order = pd.CategoricalDtype(
        categories=[
            "Critical",
            "High",
            "Medium",
            "Low",
        ],
        ordered=True,
    )

    result["risk_severity"] = (
        result["risk_severity"]
        .astype(severity_order)
    )

    return result


# ============================================================
# INTELLIGENCE ALERTS
# ============================================================
def generate_intelligence_alerts(df):
    """
    Generate management alerts from the business
    intelligence dataset.
    """

    if df is None or df.empty:
        return pd.DataFrame(
            columns=[
                "sku_id",
                "product_name",
                "category",
                "alert_type",
                "severity",
                "message",
                "recommended_action",
                "priority_score",
            ]
        )

    data = df.copy()

    # --------------------------------------------------------
    # Safe defaults
    # --------------------------------------------------------
    defaults = {
        "product_name": "",
        "category": "Unknown",
        "stockout_risk_percent": 0,
        "overstock_risk_percent": 0,
        "weeks_of_supply": 0,
        "sales_at_risk": 0,
        "capital_locked": 0,
        "avg_weekly_demand": 0,
        "demand_trend": "Stable",
        "recommended_action": "Healthy",
        "priority_score": 0,
    }

    for column, default in defaults.items():

        if column not in data.columns:
            data[column] = default

    alerts = []

    # --------------------------------------------------------
    # Generate alerts
    # --------------------------------------------------------
    for _, row in data.iterrows():

        sku = row.get(
            "sku_id",
            "Unknown",
        )

        product = row.get(
            "product_name",
            sku,
        )

        category = row.get(
            "category",
            "Unknown",
        )

        stockout = float(
            row.get(
                "stockout_risk_percent",
                0,
            )
            or 0
        )

        overstock = float(
            row.get(
                "overstock_risk_percent",
                0,
            )
            or 0
        )

        weeks = float(
            row.get(
                "weeks_of_supply",
                0,
            )
            or 0
        )

        sales_risk = float(
            row.get(
                "sales_at_risk",
                0,
            )
            or 0
        )

        capital = float(
            row.get(
                "capital_locked",
                0,
            )
            or 0
        )

        trend = str(
            row.get(
                "demand_trend",
                "Stable",
            )
        )

        severity = str(
            row.get(
                "risk_severity",
                "Low",
            )
        )

        action = row.get(
            "recommended_action",
            "Healthy",
        )

        priority = float(
            row.get(
                "priority_score",
                0,
            )
            or 0
        )

        # ----------------------------------------------------
        # Stockout alert
        # ----------------------------------------------------
        if stockout >= 80:

            alerts.append(
                {
                    "sku_id": sku,
                    "product_name": product,
                    "category": category,
                    "alert_type": "Critical Stockout",
                    "severity": "Critical",
                    "message": (
                        f"{product} has "
                        f"{stockout:.1f}% stockout risk."
                    ),
                    "recommended_action": "Reorder Now",
                    "priority_score": priority,
                }
            )

        elif stockout >= 50:

            alerts.append(
                {
                    "sku_id": sku,
                    "product_name": product,
                    "category": category,
                    "alert_type": "High Stockout Risk",
                    "severity": "High",
                    "message": (
                        f"{product} has "
                        f"{stockout:.1f}% stockout risk."
                    ),
                    "recommended_action": "Reorder Now",
                    "priority_score": priority,
                }
            )

        elif stockout >= 25:

            alerts.append(
                {
                    "sku_id": sku,
                    "product_name": product,
                    "category": category,
                    "alert_type": "Stockout Warning",
                    "severity": "Medium",
                    "message": (
                        f"{product} may face inventory "
                        f"shortage with {stockout:.1f}% risk."
                    ),
                    "recommended_action": action,
                    "priority_score": priority,
                }
            )

        # ----------------------------------------------------
        # Overstock alert
        # ----------------------------------------------------
        if overstock >= 50 or weeks >= 12:

            alerts.append(
                {
                    "sku_id": sku,
                    "product_name": product,
                    "category": category,
                    "alert_type": "Excess Inventory",
                    "severity": "High",
                    "message": (
                        f"{product} has "
                        f"{weeks:.1f} weeks of supply."
                    ),
                    "recommended_action": (
                        "Markdown / Clear"
                    ),
                    "priority_score": priority,
                }
            )

        elif overstock >= 25 or weeks >= 8:

            alerts.append(
                {
                    "sku_id": sku,
                    "product_name": product,
                    "category": category,
                    "alert_type": "Overstock Warning",
                    "severity": "Medium",
                    "message": (
                        f"{product} has "
                        f"{weeks:.1f} weeks of supply."
                    ),
                    "recommended_action": (
                        "Reduce Future Orders"
                    ),
                    "priority_score": priority,
                }
            )

        # ----------------------------------------------------
        # Sales exposure
        # ----------------------------------------------------
        if sales_risk >= 100000:

            alerts.append(
                {
                    "sku_id": sku,
                    "product_name": product,
                    "category": category,
                    "alert_type": "Critical Sales Exposure",
                    "severity": "Critical",
                    "message": (
                        f"{product} has approximately "
                        f"₹{sales_risk:,.0f} in sales at risk."
                    ),
                    "recommended_action": "Protect Sales",
                    "priority_score": priority,
                }
            )

        elif sales_risk >= 50000:

            alerts.append(
                {
                    "sku_id": sku,
                    "product_name": product,
                    "category": category,
                    "alert_type": "High Sales Exposure",
                    "severity": "High",
                    "message": (
                        f"{product} has approximately "
                        f"₹{sales_risk:,.0f} in sales at risk."
                    ),
                    "recommended_action": "Protect Sales",
                    "priority_score": priority,
                }
            )

        # ----------------------------------------------------
        # Capital exposure
        # ----------------------------------------------------
        if capital >= 100000:

            alerts.append(
                {
                    "sku_id": sku,
                    "product_name": product,
                    "category": category,
                    "alert_type": "Critical Capital Exposure",
                    "severity": "Critical",
                    "message": (
                        f"{product} has approximately "
                        f"₹{capital:,.0f} locked in excess stock."
                    ),
                    "recommended_action": (
                        "Reduce Overstock"
                    ),
                    "priority_score": priority,
                }
            )

        elif capital >= 50000:

            alerts.append(
                {
                    "sku_id": sku,
                    "product_name": product,
                    "category": category,
                    "alert_type": "High Capital Exposure",
                    "severity": "High",
                    "message": (
                        f"{product} has approximately "
                        f"₹{capital:,.0f} locked in excess stock."
                    ),
                    "recommended_action": (
                        "Reduce Overstock"
                    ),
                    "priority_score": priority,
                }
            )

        # ----------------------------------------------------
        # Demand trend
        # ----------------------------------------------------
        if trend == "Increasing":

            alerts.append(
                {
                    "sku_id": sku,
                    "product_name": product,
                    "category": category,
                    "alert_type": "Demand Increase",
                    "severity": "Medium",
                    "message": (
                        f"{product} is showing increasing "
                        "demand and may require additional inventory."
                    ),
                    "recommended_action": (
                        "Review Replenishment"
                    ),
                    "priority_score": priority,
                }
            )

        elif trend == "Declining":

            alerts.append(
                {
                    "sku_id": sku,
                    "product_name": product,
                    "category": category,
                    "alert_type": "Demand Decline",
                    "severity": "Low",
                    "message": (
                        f"{product} is showing declining demand."
                    ),
                    "recommended_action": (
                        "Reduce Future Orders"
                    ),
                    "priority_score": priority,
                }
            )

    # --------------------------------------------------------
    # Output
    # --------------------------------------------------------
    alerts_df = pd.DataFrame(alerts)

    if alerts_df.empty:
        return pd.DataFrame(
            columns=[
                "sku_id",
                "product_name",
                "category",
                "alert_type",
                "severity",
                "message",
                "recommended_action",
                "priority_score",
            ]
        )

    severity_rank = {
        "Critical": 4,
        "High": 3,
        "Medium": 2,
        "Low": 1,
    }

    alerts_df["severity_rank"] = (
        alerts_df["severity"]
        .map(severity_rank)
        .fillna(0)
    )

    alerts_df = alerts_df.sort_values(
        [
            "severity_rank",
            "priority_score",
        ],
        ascending=[
            False,
            False,
        ],
    )

    alerts_df = alerts_df.drop(
        columns=["severity_rank"]
    )

    return alerts_df.reset_index(
        drop=True
    )


# ============================================================
# ALERT SUMMARY
# ============================================================
def get_alert_summary(alerts_df):
    """
    Return high-level alert statistics.
    """

    if alerts_df is None or alerts_df.empty:

        return {
            "total_alerts": 0,
            "critical_alerts": 0,
            "high_alerts": 0,
            "medium_alerts": 0,
            "low_alerts": 0,
            "affected_skus": 0,
        }

    severity = alerts_df[
        "severity"
    ].astype(str)

    return {
        "total_alerts": len(alerts_df),

        "critical_alerts": int(
            (severity == "Critical").sum()
        ),

        "high_alerts": int(
            (severity == "High").sum()
        ),

        "medium_alerts": int(
            (severity == "Medium").sum()
        ),

        "low_alerts": int(
            (severity == "Low").sum()
        ),

        "affected_skus": int(
            alerts_df["sku_id"]
            .nunique()
        ),
    }