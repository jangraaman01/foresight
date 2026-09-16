import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

from src.data_loader import (
    load_sales,
    load_inventory,
    load_sku_master,
)

from src.forecast_engine import (
    generate_forecast_summary,
)

from src.intelligence import (
    calculate_business_intelligence,
    generate_intelligence_alerts,
    get_alert_summary,
)

from src.ui import (
    apply_foresight_style,
    show_sidebar_brand,
    page_header,
    section_header,
    recommendation_card,
    show_footer,
)


# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="FORESIGHT | Home",
    page_icon="📊",
    layout="wide",
)

apply_foresight_style()
show_sidebar_brand()


# ============================================================
# HEADER
# ============================================================
page_header(
    "📊 FORESIGHT Command Center",
    "Executive overview of sales, demand, inventory and business risk.",
)


# ============================================================
# LOAD DATA
# ============================================================
@st.cache_data
def load_home_data():

    sales = load_sales()
    inventory = load_inventory()
    sku_master = load_sku_master()

    return sales, inventory, sku_master


sales, inventory, sku_master = load_home_data()


# ============================================================
# VALIDATION
# ============================================================
if sales.empty:
    st.error("Sales data is empty.")
    st.stop()

if inventory.empty:
    st.error("Inventory data is empty.")
    st.stop()

if sku_master.empty:
    st.error("SKU master data is empty.")
    st.stop()


# ============================================================
# CLEAN DATA
# ============================================================
sales = sales.copy()
inventory = inventory.copy()
sku_master = sku_master.copy()

sales["date"] = pd.to_datetime(
    sales["date"],
    errors="coerce",
)

inventory["date"] = pd.to_datetime(
    inventory["date"],
    errors="coerce",
)

sales["units_sold"] = pd.to_numeric(
    sales["units_sold"],
    errors="coerce",
).fillna(0)

if "revenue" in sales.columns:

    sales["revenue"] = pd.to_numeric(
        sales["revenue"],
        errors="coerce",
    ).fillna(0)

for column in [
    "on_hand_units",
    "on_order_units",
    "lead_time_days",
]:

    if column not in inventory.columns:
        inventory[column] = 0

    inventory[column] = pd.to_numeric(
        inventory[column],
        errors="coerce",
    ).fillna(0)

for column in [
    "unit_cost",
    "list_price",
]:

    if column not in sku_master.columns:
        sku_master[column] = 0

    sku_master[column] = pd.to_numeric(
        sku_master[column],
        errors="coerce",
    ).fillna(0)


# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.markdown("---")
st.sidebar.subheader("Command Center Settings")

forecast_horizon = st.sidebar.slider(
    "Forecast Horizon (Weeks)",
    min_value=1,
    max_value=16,
    value=8,
)

target_weeks = st.sidebar.slider(
    "Target Weeks of Supply",
    min_value=1,
    max_value=16,
    value=8,
)


# ============================================================
# FORECAST
# ============================================================
with st.spinner(
    "Preparing FORESIGHT command center..."
):

    forecast_summary = generate_forecast_summary(
        sales,
        horizon=forecast_horizon,
    )


if forecast_summary.empty:

    st.warning(
        "No forecast data is available."
    )

    show_footer()
    st.stop()


# ============================================================
# LATEST INVENTORY
# ============================================================
latest_inventory_date = inventory["date"].max()

latest_inventory = inventory[
    inventory["date"] == latest_inventory_date
].copy()

latest_inventory = (
    latest_inventory
    .drop_duplicates(
        subset=["sku_id"],
        keep="last",
    )
)


# ============================================================
# PRODUCT MASTER
# ============================================================
product_columns = [
    "sku_id",
    "product_name",
    "category",
    "subcategory",
    "unit_cost",
    "list_price",
]

product_columns = [
    column
    for column in product_columns
    if column in sku_master.columns
]

products = (
    sku_master[
        product_columns
    ]
    .drop_duplicates(
        subset=["sku_id"]
    )
)


# ============================================================
# BUILD DATASET
# ============================================================
summary = forecast_summary.merge(
    latest_inventory,
    on="sku_id",
    how="left",
)

summary = summary.merge(
    products,
    on="sku_id",
    how="left",
)


# ============================================================
# DEFAULT VALUES
# ============================================================
for column in [
    "on_hand_units",
    "on_order_units",
    "lead_time_days",
    "unit_cost",
    "list_price",
]:

    if column not in summary.columns:
        summary[column] = 0

    summary[column] = pd.to_numeric(
        summary[column],
        errors="coerce",
    ).fillna(0)


if "product_name" not in summary.columns:

    summary["product_name"] = (
        summary["sku_id"].astype(str)
    )

summary["product_name"] = (
    summary["product_name"]
    .fillna(
        summary["sku_id"].astype(str)
    )
)


if "category" not in summary.columns:
    summary["category"] = "Unknown"

summary["category"] = (
    summary["category"]
    .fillna("Unknown")
)


# ============================================================
# INVENTORY POSITION
# ============================================================
summary["inventory_position"] = (
    summary["on_hand_units"]
    + summary["on_order_units"]
)


# ============================================================
# SELLING PRICE
# ============================================================
latest_sales_date = sales["date"].max()

price_start_date = (
    latest_sales_date
    - pd.Timedelta(weeks=8)
)

recent_sales = sales[
    sales["date"] >= price_start_date
].copy()


if "revenue" in recent_sales.columns:

    recent_price = (
        recent_sales
        .groupby("sku_id")
        .agg(
            recent_units=(
                "units_sold",
                "sum",
            ),
            recent_revenue=(
                "revenue",
                "sum",
            ),
        )
        .reset_index()
    )

    recent_price[
        "estimated_selling_price"
    ] = np.where(
        recent_price["recent_units"] > 0,
        recent_price["recent_revenue"]
        / recent_price["recent_units"],
        np.nan,
    )

    summary = summary.merge(
        recent_price[
            [
                "sku_id",
                "estimated_selling_price",
            ]
        ],
        on="sku_id",
        how="left",
    )

else:

    summary[
        "estimated_selling_price"
    ] = np.nan


summary[
    "estimated_selling_price"
] = (
    summary[
        "estimated_selling_price"
    ]
    .fillna(
        summary["list_price"]
    )
)


# ============================================================
# BUSINESS INTELLIGENCE
# ============================================================
summary = calculate_business_intelligence(
    summary,
    target_weeks=target_weeks,
)


# ============================================================
# ALERTS
# ============================================================
alerts = generate_intelligence_alerts(
    summary
)

alert_summary = get_alert_summary(
    alerts
)


# ============================================================
# EXECUTIVE KPI ROW
# ============================================================
section_header(
    "Portfolio Health",
    "Current high-level status of the FORESIGHT portfolio.",
)


total_skus = len(summary)

total_forecast_demand = (
    summary["total_forecast_demand"].sum()
)

total_sales_risk = (
    summary["sales_at_risk"].sum()
)

total_capital_locked = (
    summary["capital_locked"].sum()
)

critical_count = (
    summary["risk_severity"]
    .astype(str)
    .eq("Critical")
    .sum()
)

high_count = (
    summary["risk_severity"]
    .astype(str)
    .eq("High")
    .sum()
)


col1, col2, col3, col4, col5 = st.columns(5)

col1.metric(
    "Total SKUs",
    f"{total_skus:,}",
)

col2.metric(
    "Forecast Demand",
    f"{total_forecast_demand:,.0f}",
)

col3.metric(
    "Sales at Risk",
    f"₹{total_sales_risk:,.0f}",
)

col4.metric(
    "Capital Locked",
    f"₹{total_capital_locked:,.0f}",
)

col5.metric(
    "Critical / High",
    f"{critical_count + high_count:,}",
)


# ============================================================
# PORTFOLIO STATUS
# ============================================================
if critical_count > 0:

    st.error(
        f"🚨 Portfolio Alert: {critical_count} SKU(s) "
        "are currently classified as Critical."
    )

elif high_count > 0:

    st.warning(
        f"⚠️ Portfolio Watch: {high_count} SKU(s) "
        "are currently classified as High risk."
    )

else:

    st.success(
        "✅ Portfolio Status: No Critical or High-risk "
        "SKU concentration detected."
    )


# ============================================================
# ATTENTION CENTER
# ============================================================
section_header(
    "🚨 What Needs Attention?",
    "The most important issues detected by the FORESIGHT intelligence engine.",
)


if alerts.empty:

    st.success(
        "No significant alerts detected."
    )

else:

    alert_col1, alert_col2, alert_col3, alert_col4 = st.columns(4)

    alert_col1.metric(
        "Total Alerts",
        alert_summary["total_alerts"],
    )

    alert_col2.metric(
        "Critical",
        alert_summary["critical_alerts"],
    )

    alert_col3.metric(
        "High",
        alert_summary["high_alerts"],
    )

    alert_col4.metric(
        "Affected SKUs",
        alert_summary["affected_skus"],
    )

    st.dataframe(
        alerts[
            [
                "sku_id",
                "product_name",
                "alert_type",
                "severity",
                "message",
                "recommended_action",
            ]
        ].head(10),
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# FINANCIAL EXPOSURE
# ============================================================
section_header(
    "Financial Exposure",
    "Comparison between potential lost sales and excess inventory capital.",
)


financial_data = pd.DataFrame(
    {
        "Exposure Type": [
            "Sales at Risk",
            "Capital Locked",
        ],
        "Amount": [
            total_sales_risk,
            total_capital_locked,
        ],
    }
)


fig = px.bar(
    financial_data,
    x="Exposure Type",
    y="Amount",
    text_auto=".2s",
    title="Current Financial Exposure",
)

st.plotly_chart(
    fig,
    use_container_width=True,
)


# ============================================================
# RISK DISTRIBUTION
# ============================================================
section_header(
    "Risk Distribution",
    "Current distribution of products by business risk severity.",
)


risk_distribution = (
    summary["risk_severity"]
    .astype(str)
    .value_counts()
    .reindex(
        [
            "Critical",
            "High",
            "Medium",
            "Low",
        ],
        fill_value=0,
    )
    .reset_index()
)

risk_distribution.columns = [
    "Risk Severity",
    "SKU Count",
]


fig = px.bar(
    risk_distribution,
    x="Risk Severity",
    y="SKU Count",
    text_auto=True,
    title="Portfolio Risk Distribution",
)

st.plotly_chart(
    fig,
    use_container_width=True,
)


# ============================================================
# BUSINESS PRIORITY
# ============================================================
section_header(
    "Business Priorities",
    "Where management attention should be concentrated.",
)


priority_distribution = (
    summary["business_priority"]
    .value_counts()
    .reset_index()
)

priority_distribution.columns = [
    "Business Priority",
    "SKU Count",
]


fig = px.bar(
    priority_distribution,
    x="Business Priority",
    y="SKU Count",
    text_auto=True,
    title="Business Priority Distribution",
)

st.plotly_chart(
    fig,
    use_container_width=True,
)


# ============================================================
# TOP RISKS
# ============================================================
section_header(
    "Top Risks",
    "Highest-priority products based on operational and financial exposure.",
)


top_risks = (
    summary
    .sort_values(
        [
            "risk_severity",
            "priority_score",
        ],
        ascending=[
            True,
            False,
        ],
    )
    .head(10)
)


st.dataframe(
    top_risks[
        [
            "sku_id",
            "product_name",
            "category",
            "risk_severity",
            "business_priority",
            "stockout_risk_percent",
            "weeks_of_supply",
            "sales_at_risk",
            "capital_locked",
            "priority_score",
            "recommended_action",
        ]
    ],
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# PROTECT SALES
# ============================================================
section_header(
    "🛡️ Protect Sales",
    "Products where inventory shortages may create the greatest lost-sales exposure.",
)


protect_sales = summary[
    summary["business_priority"]
    == "Protect Sales"
].copy()


protect_sales = (
    protect_sales
    .sort_values(
        "sales_at_risk",
        ascending=False,
    )
    .head(10)
)


if protect_sales.empty:

    st.info(
        "No significant Protect Sales priorities."
    )

else:

    st.dataframe(
        protect_sales[
            [
                "sku_id",
                "product_name",
                "category",
                "avg_weekly_demand",
                "inventory_position",
                "stockout_units_at_risk",
                "sales_at_risk",
                "demand_trend",
                "forecast_confidence",
                "recommended_action",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# REDUCE OVERSTOCK
# ============================================================
section_header(
    "📦 Reduce Overstock",
    "Products with excess inventory and significant working capital exposure.",
)


overstock = summary[
    summary["business_priority"]
    == "Reduce Overstock"
].copy()


overstock = (
    overstock
    .sort_values(
        "capital_locked",
        ascending=False,
    )
    .head(10)
)


if overstock.empty:

    st.info(
        "No significant Reduce Overstock priorities."
    )

else:

    st.dataframe(
        overstock[
            [
                "sku_id",
                "product_name",
                "category",
                "inventory_position",
                "avg_weekly_demand",
                "weeks_of_supply",
                "excess_units",
                "capital_locked",
                "demand_trend",
                "recommended_action",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# MANAGEMENT RECOMMENDATIONS
# ============================================================
section_header(
    "Management Recommendations",
    "Actions suggested from the current portfolio condition.",
)


if total_sales_risk > total_capital_locked:

    recommendation_card(
        "Protect Revenue",
        (
            f"Potential sales exposure is ₹{total_sales_risk:,.0f}, "
            f"greater than ₹{total_capital_locked:,.0f} of capital locked. "
            "Prioritize replenishment of high-risk products."
        ),
    )

else:

    recommendation_card(
        "Release Working Capital",
        (
            f"Capital locked is ₹{total_capital_locked:,.0f}, "
            f"greater than ₹{total_sales_risk:,.0f} of potential sales exposure. "
            "Prioritize excess inventory reduction."
        ),
    )


if critical_count > 0:

    recommendation_card(
        "Immediate Management Escalation",
        (
            f"{critical_count} SKU(s) are Critical. "
            "Review inventory, supplier lead times and replenishment decisions immediately."
        ),
    )


increasing_demand = summary[
    summary["demand_trend"]
    .astype(str)
    == "Increasing"
]


if not increasing_demand.empty:

    recommendation_card(
        "Demand Growth",
        (
            f"{len(increasing_demand)} SKU(s) show increasing demand. "
            "Review future inventory requirements before shortages occur."
        ),
    )


# ============================================================
# QUICK NAVIGATION
# ============================================================
section_header(
    "Explore FORESIGHT",
    "Open the detailed analysis modules.",
)


nav1, nav2, nav3, nav4 = st.columns(4)

with nav1:

    st.page_link(
    "pages/executive.py",
    label="🎯 Executive Summary",
)
    st.caption(
        "Management command center and alerts."
    )


with nav2:

    st.page_link(
        "pages/forecast.py",
        label="📈 Demand Forecast",
    )

    st.caption(
        "ML demand forecasting and trends."
    )


with nav3:

    st.page_link(
        "pages/risk.py",
        label="⚠️ Risk Dashboard",
    )

    st.caption(
        "Stockout and overstock risk."
    )


with nav4:

    st.page_link(
        "pages/business_impact.py",
        label="💰 Business Impact",
    )

    st.caption(
        "Financial exposure and priorities."
    )


# ============================================================
# ADDITIONAL NAVIGATION
# ============================================================
nav1, nav2, nav3, nav4 = st.columns(4)

with nav1:

    st.page_link(
        "pages/product.py",
        label="🔎 Product Details",
    )


with nav2:

    st.page_link(
        "pages/sales.py",
        label="📊 Sales Analytics",
    )


with nav3:

    st.page_link(
        "pages/inventory.py",
        label="📦 Inventory Dashboard",
    )


with nav4:

    st.page_link(
        "pages/data_quality.py",
        label="🧹 Data Quality",
    )


# ============================================================
# SYSTEM INFORMATION
# ============================================================
with st.expander(
    "ℹ️ FORESIGHT System Information"
):

    st.markdown(
        f"""
### Current Data

- **Latest Sales Date:** {sales["date"].max().date()}
- **Latest Inventory Date:** {latest_inventory_date.date()}
- **Products Analyzed:** {total_skus:,}
- **Forecast Horizon:** {forecast_horizon} weeks
- **Target Inventory:** {target_weeks} weeks of supply

### Intelligence Layers

FORESIGHT combines:

1. Historical sales analysis
2. Machine-learning demand forecasting
3. Inventory position analysis
4. Stockout risk detection
5. Overstock detection
6. Financial exposure analysis
7. Business priority classification
8. Automated management alerts

### Purpose

FORESIGHT is designed as a decision-support system for
proactive demand and inventory management.
"""
    )


# ============================================================
# FOOTER
# ============================================================
show_footer()