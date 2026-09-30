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
    page_title="Executive Summary | FORESIGHT",
    page_icon="🎯",
    layout="wide",
)

apply_foresight_style()
show_sidebar_brand()

page_header(
    "🎯 FORESIGHT Executive Summary",
    "Management command center for demand, inventory, financial exposure and business risk.",
)


# ============================================================
# LOAD DATA
# ============================================================
@st.cache_data
def load_data():

    sales = load_sales()
    inventory = load_inventory()
    sku_master = load_sku_master()

    return sales, inventory, sku_master


sales, inventory, sku_master = load_data()


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
    "reorder_point",
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
# SIDEBAR CONTROLS
# ============================================================
st.sidebar.markdown("---")
st.sidebar.subheader("Executive Settings")

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
with st.spinner("Building executive intelligence..."):

    forecast_summary = generate_forecast_summary(
        sales,
        horizon=forecast_horizon,
    )


if forecast_summary.empty:

    st.warning(
        "No forecast information is available."
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
# BUILD EXECUTIVE DATASET
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
# DEFAULT COLUMNS
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
        summary["sku_id"]
        .astype(str)
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
# ESTIMATED SELLING PRICE
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
# BUSINESS INTELLIGENCE ENGINE
# ============================================================
summary = calculate_business_intelligence(
    summary,
    target_weeks=target_weeks,
)


# ============================================================
# FILTERS
# ============================================================
st.sidebar.markdown("---")
st.sidebar.subheader("Executive Filters")


categories = sorted(
    summary["category"]
    .astype(str)
    .unique()
    .tolist()
)

selected_categories = st.sidebar.multiselect(
    "Category",
    categories,
    default=categories,
)


priorities = [
    "Healthy",
    "Protect Sales",
    "Reduce Overstock",
]

selected_priorities = st.sidebar.multiselect(
    "Business Priority",
    priorities,
    default=priorities,
)


severity_options = [
    "Critical",
    "High",
    "Medium",
    "Low",
]

selected_severity = st.sidebar.multiselect(
    "Risk Severity",
    severity_options,
    default=severity_options,
)


filtered = summary.copy()


if selected_categories:

    filtered = filtered[
        filtered["category"]
        .astype(str)
        .isin(selected_categories)
    ]


if selected_priorities:

    filtered = filtered[
        filtered["business_priority"]
        .isin(selected_priorities)
    ]


if selected_severity:

    filtered = filtered[
        filtered["risk_severity"]
        .astype(str)
        .isin(selected_severity)
    ]


if filtered.empty:

    st.warning(
        "No products match the selected filters."
    )

    show_footer()
    st.stop()


# ============================================================
# EXECUTIVE KPIs
# ============================================================
section_header(
    "Executive Health",
    "Current financial and operational position across the filtered product portfolio.",
)


total_sales_risk = filtered[
    "sales_at_risk"
].sum()

total_capital_locked = filtered[
    "capital_locked"
].sum()

total_exposure = filtered[
    "total_financial_exposure"
].sum()

stockout_units = filtered[
    "stockout_units_at_risk"
].sum()

excess_units = filtered[
    "excess_units"
].sum()

critical_count = (
    filtered["risk_severity"]
    .astype(str)
    .eq("Critical")
    .sum()
)

high_count = (
    filtered["risk_severity"]
    .astype(str)
    .eq("High")
    .sum()
)


col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Sales at Risk",
    f"₹{total_sales_risk:,.0f}",
)

col2.metric(
    "Capital Locked",
    f"₹{total_capital_locked:,.0f}",
)

col3.metric(
    "Total Exposure",
    f"₹{total_exposure:,.0f}",
)

col4.metric(
    "Critical / High SKUs",
    f"{critical_count + high_count:,}",
)


# ============================================================
# WHAT NEEDS ATTENTION TODAY
# ============================================================
section_header(
    "🚨 What Needs Attention Today?",
    "Highest-priority management alerts generated from current business intelligence.",
)


alerts = generate_intelligence_alerts(
    filtered
)

alert_summary = get_alert_summary(
    alerts
)


if alerts.empty:

    st.success(
        "No significant management alerts detected."
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
                "category",
                "alert_type",
                "severity",
                "message",
                "recommended_action",
            ]
        ].head(20),
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# ALERT TYPE DISTRIBUTION
# ============================================================
if not alerts.empty:

    section_header(
        "Alert Distribution",
        "Breakdown of the issues currently requiring attention.",
    )

    alert_distribution = (
        alerts["alert_type"]
        .value_counts()
        .reset_index()
    )

    alert_distribution.columns = [
        "Alert Type",
        "Count",
    ]

    fig = px.bar(
        alert_distribution,
        x="Alert Type",
        y="Count",
        text_auto=True,
        title="Management Alert Types",
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )


# ============================================================
# FINANCIAL EXPOSURE
# ============================================================
section_header(
    "Financial Exposure",
    "Where the portfolio is exposed to lost revenue or tied-up working capital.",
)


financial_df = pd.DataFrame(
    {
        "Exposure": [
            "Sales at Risk",
            "Capital Locked",
        ],
        "Value": [
            total_sales_risk,
            total_capital_locked,
        ],
    }
)


fig = px.bar(
    financial_df,
    x="Exposure",
    y="Value",
    text_auto=".2s",
    title="Portfolio Financial Exposure",
)

st.plotly_chart(
    fig,
    use_container_width=True,
)


# ============================================================
# BUSINESS PRIORITY
# ============================================================
section_header(
    "Business Priority",
    "Identify whether management should protect revenue or release working capital.",
)


priority_df = (
    filtered[
        "business_priority"
    ]
    .value_counts()
    .reset_index()
)

priority_df.columns = [
    "Business Priority",
    "SKU Count",
]


fig = px.bar(
    priority_df,
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
# RISK SEVERITY
# ============================================================
section_header(
    "Risk Severity",
    "Portfolio risk concentration from Critical to Low.",
)


severity_df = (
    filtered[
        "risk_severity"
    ]
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

severity_df.columns = [
    "Risk Severity",
    "SKU Count",
]


fig = px.bar(
    severity_df,
    x="Risk Severity",
    y="SKU Count",
    text_auto=True,
    title="Risk Severity Distribution",
)

st.plotly_chart(
    fig,
    use_container_width=True,
)


# ============================================================
# TOP RISKS
# ============================================================
section_header(
    "Top Business Risks",
    "Products with the highest combined financial and operational exposure.",
)


top_risks = (
    filtered
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
    .head(15)
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
    "Highest potential lost-sales exposure requiring replenishment attention.",
)


protect_sales = filtered[
    filtered["business_priority"]
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

    st.success(
        "No products currently require sales-protection action."
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
                "lead_time_demand",
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
    "Products tying up the greatest amount of working capital.",
)


overstock = filtered[
    filtered["business_priority"]
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

    st.success(
        "No significant excess-inventory exposure detected."
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
# CATEGORY EXPOSURE
# ============================================================
section_header(
    "Category Exposure",
    "Categories contributing most to total financial exposure.",
)


category_exposure = (
    filtered
    .groupby(
        "category",
        as_index=False,
    )
    .agg(
        sales_at_risk=(
            "sales_at_risk",
            "sum",
        ),
        capital_locked=(
            "capital_locked",
            "sum",
        ),
        total_exposure=(
            "total_financial_exposure",
            "sum",
        ),
    )
    .sort_values(
        "total_exposure",
        ascending=False,
    )
)


category_long = category_exposure.melt(
    id_vars=["category"],
    value_vars=[
        "sales_at_risk",
        "capital_locked",
    ],
    var_name="Exposure Type",
    value_name="Amount",
)


category_long[
    "Exposure Type"
] = category_long[
    "Exposure Type"
].replace(
    {
        "sales_at_risk": "Sales at Risk",
        "capital_locked": "Capital Locked",
    }
)


fig = px.bar(
    category_long,
    x="category",
    y="Amount",
    color="Exposure Type",
    barmode="group",
    title="Financial Exposure by Category",
)

st.plotly_chart(
    fig,
    use_container_width=True,
)


# ============================================================
# MANAGEMENT RECOMMENDATIONS
# ============================================================
section_header(
    "Management Recommendations",
    "Recommended actions based on the current portfolio condition.",
)


if total_sales_risk > total_capital_locked:

    recommendation_card(
        "Priority: Protect Revenue",
        (
            f"Potential sales exposure of ₹{total_sales_risk:,.0f} "
            f"exceeds capital locked of ₹{total_capital_locked:,.0f}. "
            "Prioritize replenishment for high-risk products."
        ),
    )

else:

    recommendation_card(
        "Priority: Release Working Capital",
        (
            f"Capital locked of ₹{total_capital_locked:,.0f} "
            f"exceeds sales exposure of ₹{total_sales_risk:,.0f}. "
            "Prioritize excess-stock reduction."
        ),
    )


if critical_count > 0:

    recommendation_card(
        "Immediate Escalation",
        (
            f"{critical_count} SKU(s) are classified as Critical. "
            "Management should review these products immediately."
        ),
    )


if high_count > 0:

    recommendation_card(
        "High-Risk Review",
        (
            f"{high_count} SKU(s) are classified as High risk. "
            "Review their replenishment and inventory strategy."
        ),
    )


if not alerts.empty:

    demand_alerts = alerts[
        alerts["alert_type"]
        == "Demand Increase"
    ]

    if not demand_alerts.empty:

        recommendation_card(
            "Demand Growth Watch",
            (
                f"{len(demand_alerts)} product(s) "
                "are showing increasing demand. "
                "Review forecast and replenishment levels."
            ),
        )


# ============================================================
# EXECUTIVE DECISION TABLE
# ============================================================
section_header(
    "Executive Decision Table",
    "A concise action-oriented view for management review.",
)


decision_table = filtered[
    [
        "sku_id",
        "product_name",
        "category",
        "risk_severity",
        "business_priority",
        "demand_trend",
        "forecast_confidence",
        "sales_at_risk",
        "capital_locked",
        "weeks_of_supply",
        "priority_score",
        "recommended_action",
    ]
].copy()


decision_table = decision_table.sort_values(
    [
        "risk_severity",
        "priority_score",
    ],
    ascending=[
        True,
        False,
    ],
)


st.dataframe(
    decision_table,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# PORTFOLIO SUMMARY
# ============================================================
section_header(
    "Portfolio Summary",
    "High-level statistics for the current executive view.",
)


col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Products",
    f"{len(filtered):,}",
)

col2.metric(
    "Avg Weekly Demand",
    f"{filtered['avg_weekly_demand'].sum():,.0f}",
)

col3.metric(
    "Forecast Demand",
    f"{filtered['total_forecast_demand'].sum():,.0f}",
)

col4.metric(
    "Affected SKUs",
    f"{alert_summary['affected_skus']:,}",
)


# ============================================================
# METHODOLOGY
# ============================================================
with st.expander(
    "ℹ️ Executive Intelligence Methodology"
):

    st.markdown(
        f"""
### Forecast

The executive dashboard uses the centralized FORESIGHT
forecast engine with a **{forecast_horizon}-week forecast horizon**.

### Inventory Risk

Stockout exposure compares inventory position against
expected demand during supplier lead time.

### Overstock

Target inventory is calculated using:

**Average Weekly Demand × {target_weeks} Target Weeks**

### Sales at Risk

**Stockout Units × Estimated Selling Price**

### Capital Locked

**Excess Inventory Units × Unit Cost**

### Business Priority

Products are classified as:

- **Protect Sales**
- **Reduce Overstock**
- **Healthy**

### Risk Severity

The intelligence engine combines operational and financial
risk into:

**Critical → High → Medium → Low**

### Alerts

The alert engine automatically identifies:

- Critical stockout risk
- High stockout risk
- Excess inventory
- Sales exposure
- Capital exposure
- Increasing demand
- Declining demand

The financial values are estimates intended for management
decision support rather than accounting or financial reporting.
"""
    )


# ============================================================
# FOOTER
# ============================================================
show_footer()