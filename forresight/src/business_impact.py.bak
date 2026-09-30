import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

from src.data_loader import (
    load_sales,
    load_inventory,
    load_sku_master
)

from src.business_impact import calculate_business_impact
from src.forecast_engine import generate_forecast_summary


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Business Impact Dashboard",
    page_icon="💰",
    layout="wide"
)


# ============================================================
# PAGE TITLE
# ============================================================

st.title("💰 Business Impact Dashboard")

st.markdown(
    """
    Analyze the financial impact of inventory decisions, identify potential
    lost sales, detect excess inventory, and prioritize SKUs requiring
    management attention.
    """
)


# ============================================================
# LOAD DATA
# ============================================================

sales = load_sales()
inventory = load_inventory()
sku_master = load_sku_master()


# ============================================================
# DATA VALIDATION
# ============================================================

if sales.empty or inventory.empty:
    st.error("Sales or inventory data could not be loaded.")
    st.stop()


# ============================================================
# BUSINESS ASSUMPTIONS
# ============================================================

st.subheader("⚙️ Business Assumptions")

col1, col2, col3 = st.columns(3)

with col1:
    forecast_horizon = st.slider(
        "Forecast Horizon (Weeks)",
        min_value=1,
        max_value=16,
        value=8
    )

with col2:
    target_weeks = st.slider(
        "Target Weeks of Supply",
        min_value=1,
        max_value=16,
        value=8
    )

with col3:
    price_history_weeks = st.slider(
        "Price History (Weeks)",
        min_value=1,
        max_value=24,
        value=8
    )


st.caption(
    f"Forecast: {forecast_horizon} weeks | "
    f"Target inventory: {target_weeks} weeks | "
    f"Price history: {price_history_weeks} weeks"
)


# ============================================================
# CLEAN DATA
# ============================================================

sales = sales.copy()
inventory = inventory.copy()

sales["date"] = pd.to_datetime(
    sales["date"],
    errors="coerce"
)

inventory["date"] = pd.to_datetime(
    inventory["date"],
    errors="coerce"
)

sales["units_sold"] = pd.to_numeric(
    sales["units_sold"],
    errors="coerce"
).fillna(0)


if "revenue" in sales.columns:
    sales["revenue"] = pd.to_numeric(
        sales["revenue"],
        errors="coerce"
    ).fillna(0)


for column in [
    "on_hand_units",
    "on_order_units",
    "lead_time_days",
    "reorder_point"
]:
    if column in inventory.columns:
        inventory[column] = pd.to_numeric(
            inventory[column],
            errors="coerce"
        ).fillna(0)


# ============================================================
# LATEST INVENTORY SNAPSHOT
# ============================================================

latest_date = inventory["date"].max()

latest_inventory = inventory[
    inventory["date"] == latest_date
].copy()


# ============================================================
# DEMAND FORECAST
# ============================================================

weekly_demand = generate_forecast_summary(
    sales,
    horizon=forecast_horizon
)


if "avg_weekly_demand" not in weekly_demand.columns:
    weekly_demand["avg_weekly_demand"] = 0


weekly_demand["avg_weekly_demand"] = (
    pd.to_numeric(
        weekly_demand["avg_weekly_demand"],
        errors="coerce"
    )
    .fillna(0)
)


# ============================================================
# MERGE INVENTORY + FORECAST
# ============================================================

impact = latest_inventory.merge(
    weekly_demand,
    on="sku_id",
    how="left"
)


impact["avg_weekly_demand"] = (
    impact["avg_weekly_demand"]
    .fillna(0)
)


# ============================================================
# INVENTORY POSITION
# ============================================================

impact["inventory_position"] = (
    impact["on_hand_units"]
    + impact["on_order_units"]
)


# ============================================================
# LEAD-TIME DEMAND
# ============================================================

impact["lead_time_demand"] = (
    impact["avg_weekly_demand"]
    * impact["lead_time_days"]
    / 7
)


# ============================================================
# STOCKOUT UNITS AT RISK
# ============================================================

impact["stockout_units_at_risk"] = (
    impact["lead_time_demand"]
    - impact["inventory_position"]
).clip(lower=0)


# ============================================================
# ESTIMATE RECENT AVERAGE SELLING PRICE
# ============================================================

valid_sales_dates = sales["date"].dropna()

if not valid_sales_dates.empty:

    recent_cutoff = (
        valid_sales_dates.max()
        - pd.Timedelta(
            days=price_history_weeks * 7
        )
    )

    recent_sales = sales[
        sales["date"] >= recent_cutoff
    ].copy()

else:
    recent_sales = sales.copy()


if (
    "revenue" in recent_sales.columns
    and not recent_sales.empty
):

    price_summary = (
        recent_sales
        .groupby("sku_id", as_index=False)
        .agg(
            revenue=("revenue", "sum"),
            units_sold=("units_sold", "sum")
        )
    )

    price_summary["average_price"] = np.where(
        price_summary["units_sold"] > 0,
        price_summary["revenue"]
        / price_summary["units_sold"],
        np.nan
    )

    price_summary["average_price"] = (
        price_summary["average_price"]
        .replace(
            [np.inf, -np.inf],
            np.nan
        )
    )

    price_map = price_summary.set_index(
        "sku_id"
    )["average_price"]

    impact["average_price"] = (
        impact["sku_id"]
        .map(price_map)
        .fillna(0)
    )

else:
    impact["average_price"] = 0


# ============================================================
# UNIT COST
# ============================================================

if (
    not sku_master.empty
    and "sku_id" in sku_master.columns
    and "unit_cost" in sku_master.columns
):

    sku_master = sku_master.copy()

    sku_master["unit_cost"] = pd.to_numeric(
        sku_master["unit_cost"],
        errors="coerce"
    ).fillna(0)

    cost_map = (
        sku_master
        .drop_duplicates("sku_id")
        .set_index("sku_id")["unit_cost"]
    )

    impact["unit_cost"] = (
        impact["sku_id"]
        .map(cost_map)
        .fillna(0)
    )

else:
    impact["unit_cost"] = 0


# ============================================================
# PRODUCT INFORMATION
# ============================================================

if not sku_master.empty and "sku_id" in sku_master.columns:

    product_columns = ["sku_id"]

    possible_columns = [
        "product_name",
        "sku_name",
        "category",
        "brand"
    ]

    for column in possible_columns:
        if (
            column in sku_master.columns
            and column not in impact.columns
        ):
            product_columns.append(column)

    if len(product_columns) > 1:

        product_info = (
            sku_master[product_columns]
            .drop_duplicates("sku_id")
        )

        impact = impact.merge(
            product_info,
            on="sku_id",
            how="left"
        )


# ============================================================
# BUSINESS IMPACT ENGINE
# ============================================================

impact["stockout_units"] = (
    impact["stockout_units_at_risk"]
)

impact["average_selling_price"] = (
    impact["average_price"]
)


impact = calculate_business_impact(
    impact,
    target_weeks=target_weeks
)


# ============================================================
# GUARANTEE REQUIRED FINANCIAL COLUMNS
# ============================================================

required_numeric_columns = [
    "sales_at_risk",
    "capital_locked",
    "excess_units",
    "stockout_units",
    "stockout_units_at_risk",
    "avg_weekly_demand",
    "inventory_position",
    "average_price",
    "unit_cost"
]


for column in required_numeric_columns:

    if column not in impact.columns:
        impact[column] = 0

    impact[column] = pd.to_numeric(
        impact[column],
        errors="coerce"
    ).fillna(0)


# ============================================================
# BUSINESS PRIORITY
# ============================================================

impact["business_priority"] = np.where(
    impact["sales_at_risk"]
    >= impact["capital_locked"],
    "Protect Sales",
    "Reduce Overstock"
)


# ============================================================
# RISK SEVERITY CLASSIFICATION
# ============================================================

financial_exposure = (
    impact["sales_at_risk"]
    + impact["capital_locked"]
)

impact["financial_exposure"] = financial_exposure


positive_exposure = impact.loc[
    impact["financial_exposure"] > 0,
    "financial_exposure"
]


if len(positive_exposure) >= 4:

    q25 = positive_exposure.quantile(0.25)
    q50 = positive_exposure.quantile(0.50)
    q75 = positive_exposure.quantile(0.75)

    def classify_risk(value):

        if value <= 0:
            return "Low"

        elif value <= q25:
            return "Low"

        elif value <= q50:
            return "Medium"

        elif value <= q75:
            return "High"

        else:
            return "Critical"

    impact["risk_severity"] = (
        impact["financial_exposure"]
        .apply(classify_risk)
    )

else:

    impact["risk_severity"] = np.where(
        impact["financial_exposure"] > 0,
        "High",
        "Low"
    )


# ============================================================
# FILTERS
# ============================================================

st.divider()

st.subheader("🔎 Business Impact Filters")


filter_col1, filter_col2, filter_col3, filter_col4 = (
    st.columns(4)
)


# ------------------------------------------------------------
# CATEGORY FILTER
# ------------------------------------------------------------

with filter_col1:

    if "category" in impact.columns:

        categories = sorted(
            impact["category"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        selected_categories = st.multiselect(
            "Category",
            options=categories,
            default=[]
        )

    else:
        selected_categories = []


# ------------------------------------------------------------
# BUSINESS PRIORITY FILTER
# ------------------------------------------------------------

with filter_col2:

    selected_priority = st.selectbox(
        "Business Priority",
        options=[
            "All",
            "Protect Sales",
            "Reduce Overstock"
        ]
    )


# ------------------------------------------------------------
# RISK SEVERITY FILTER
# ------------------------------------------------------------

with filter_col3:

    selected_risk = st.multiselect(
        "Risk Severity",
        options=[
            "Critical",
            "High",
            "Medium",
            "Low"
        ],
        default=[]
    )


# ------------------------------------------------------------
# SKU FILTER
# ------------------------------------------------------------

with filter_col4:

    sku_options = sorted(
        impact["sku_id"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    selected_skus = st.multiselect(
        "SKU",
        options=sku_options,
        default=[]
    )


# ============================================================
# APPLY FILTERS
# ============================================================

filtered_impact = impact.copy()


if (
    selected_categories
    and "category" in filtered_impact.columns
):

    filtered_impact = filtered_impact[
        filtered_impact["category"]
        .astype(str)
        .isin(selected_categories)
    ]


if selected_priority != "All":

    filtered_impact = filtered_impact[
        filtered_impact["business_priority"]
        == selected_priority
    ]


if selected_risk:

    filtered_impact = filtered_impact[
        filtered_impact["risk_severity"]
        .isin(selected_risk)
    ]


if selected_skus:

    filtered_impact = filtered_impact[
        filtered_impact["sku_id"]
        .astype(str)
        .isin(selected_skus)
    ]


st.caption(
    f"Showing {len(filtered_impact):,} SKUs "
    f"out of {len(impact):,} total SKUs."
)


# ============================================================
# EMPTY FILTER CHECK
# ============================================================

if filtered_impact.empty:

    st.warning(
        "No SKUs match the selected filters. "
        "Change the filters to display results."
    )

    st.stop()


# ============================================================
# KPI CALCULATIONS
# ============================================================

total_sales_risk = (
    filtered_impact["sales_at_risk"].sum()
)

total_capital_locked = (
    filtered_impact["capital_locked"].sum()
)

total_stockout_units = (
    filtered_impact[
        "stockout_units_at_risk"
    ].sum()
)

total_excess_units = (
    filtered_impact["excess_units"].sum()
)


# ============================================================
# KPI CARDS
# ============================================================

st.divider()

st.subheader("📊 Financial Impact Overview")


kpi1, kpi2, kpi3, kpi4 = st.columns(4)


with kpi1:

    st.metric(
        "💸 Sales at Risk",
        f"₹{total_sales_risk:,.0f}"
    )


with kpi2:

    st.metric(
        "🔒 Capital Locked",
        f"₹{total_capital_locked:,.0f}"
    )


with kpi3:

    st.metric(
        "⚠️ Stockout Units",
        f"{total_stockout_units:,.0f}"
    )


with kpi4:

    st.metric(
        "📦 Excess Units",
        f"{total_excess_units:,.0f}"
    )


# ============================================================
# TOTAL FINANCIAL EXPOSURE
# ============================================================

total_financial_exposure = (
    total_sales_risk
    + total_capital_locked
)

st.metric(
    "💰 Total Financial Exposure",
    f"₹{total_financial_exposure:,.0f}"
)


# ============================================================
# SALES RISK CHART
# ============================================================

st.divider()

chart_col1, chart_col2 = st.columns(2)


with chart_col1:

    st.subheader("🚨 Top SKUs by Sales at Risk")

    top_sales_risk = (
        filtered_impact
        .nlargest(
            10,
            "sales_at_risk"
        )
    )

    fig_sales = px.bar(
        top_sales_risk,
        x="sku_id",
        y="sales_at_risk",
        title="Potential Revenue Loss by SKU",
        labels={
            "sku_id": "SKU",
            "sales_at_risk": "Sales at Risk (₹)"
        },
        template="plotly_dark"
    )

    st.plotly_chart(
        fig_sales,
        use_container_width=True
    )


# ============================================================
# CAPITAL LOCKED CHART
# ============================================================

with chart_col2:

    st.subheader("📦 Top SKUs by Capital Locked")

    top_capital = (
        filtered_impact
        .nlargest(
            10,
            "capital_locked"
        )
    )

    fig_capital = px.bar(
        top_capital,
        x="sku_id",
        y="capital_locked",
        title="Capital Locked in Excess Inventory",
        labels={
            "sku_id": "SKU",
            "capital_locked": "Capital Locked (₹)"
        },
        template="plotly_dark"
    )

    st.plotly_chart(
        fig_capital,
        use_container_width=True
    )


# ============================================================
# FINANCIAL EXPOSURE CHART
# ============================================================

st.subheader("💵 Overall Financial Exposure by SKU")


top_financial_exposure = (
    filtered_impact
    .nlargest(
        15,
        "financial_exposure"
    )
)


fig_exposure = px.bar(
    top_financial_exposure,
    x="sku_id",
    y="financial_exposure",
    color="risk_severity",
    title="Top SKUs by Total Financial Exposure",
    labels={
        "sku_id": "SKU",
        "financial_exposure":
            "Financial Exposure (₹)",
        "risk_severity":
            "Risk Severity"
    },
    template="plotly_dark"
)


st.plotly_chart(
    fig_exposure,
    use_container_width=True
)


# ============================================================
# FINANCIAL PRIORITY LIST
# ============================================================

st.divider()

st.subheader("🎯 Financial Priority List")


priority_columns = [
    "sku_id"
]


for optional_column in [
    "product_name",
    "sku_name",
    "category"
]:

    if optional_column in filtered_impact.columns:
        priority_columns.append(
            optional_column
        )


priority_columns += [
    "risk_severity",
    "business_priority",
    "avg_weekly_demand",
    "inventory_position",
    "stockout_units_at_risk",
    "excess_units",
    "sales_at_risk",
    "capital_locked",
    "financial_exposure"
]


priority_columns = [
    column
    for column in priority_columns
    if column in filtered_impact.columns
]


priority_table = (
    filtered_impact[
        priority_columns
    ]
    .sort_values(
        "financial_exposure",
        ascending=False
    )
)


st.dataframe(
    priority_table,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# STEP 26.5 — EXECUTIVE BUSINESS IMPACT SUMMARY
# ============================================================

st.divider()

st.header("🧠 Executive Business Impact Summary")


# ============================================================
# RISK COUNTS
# ============================================================

high_sales_risk_count = (
    filtered_impact["sales_at_risk"] > 0
).sum()


capital_locked_count = (
    filtered_impact["capital_locked"] > 0
).sum()


stockout_risk_count = (
    filtered_impact[
        "stockout_units_at_risk"
    ] > 0
).sum()


excess_stock_count = (
    filtered_impact["excess_units"] > 0
).sum()


# ============================================================
# RISK SUMMARY KPI CARDS
# ============================================================

summary1, summary2, summary3, summary4 = (
    st.columns(4)
)


with summary1:

    st.metric(
        "SKUs with Sales Risk",
        f"{high_sales_risk_count:,}"
    )


with summary2:

    st.metric(
        "SKUs with Stockout Risk",
        f"{stockout_risk_count:,}"
    )


with summary3:

    st.metric(
        "SKUs with Excess Stock",
        f"{excess_stock_count:,}"
    )


with summary4:

    st.metric(
        "SKUs with Capital Locked",
        f"{capital_locked_count:,}"
    )


# ============================================================
# RISK DISTRIBUTION
# ============================================================

st.subheader("📊 Inventory Risk Distribution")


risk_distribution = pd.DataFrame(
    {
        "Risk Type": [
            "Sales Risk",
            "Stockout Risk",
            "Excess Stock",
            "Capital Locked"
        ],
        "SKU Count": [
            high_sales_risk_count,
            stockout_risk_count,
            excess_stock_count,
            capital_locked_count
        ]
    }
)


fig_risk_distribution = px.bar(
    risk_distribution,
    x="Risk Type",
    y="SKU Count",
    title="Number of SKUs by Business Risk",
    text="SKU Count",
    template="plotly_dark"
)


fig_risk_distribution.update_traces(
    textposition="outside"
)


st.plotly_chart(
    fig_risk_distribution,
    use_container_width=True
)


# ============================================================
# RISK SEVERITY DISTRIBUTION
# ============================================================

st.subheader("🚦 Financial Risk Severity")


severity_order = [
    "Critical",
    "High",
    "Medium",
    "Low"
]


severity_distribution = (
    filtered_impact[
        "risk_severity"
    ]
    .value_counts()
    .reindex(
        severity_order,
        fill_value=0
    )
    .reset_index()
)


severity_distribution.columns = [
    "Risk Severity",
    "SKU Count"
]


fig_severity = px.bar(
    severity_distribution,
    x="Risk Severity",
    y="SKU Count",
    text="SKU Count",
    title="SKU Distribution by Financial Risk Severity",
    template="plotly_dark"
)


fig_severity.update_traces(
    textposition="outside"
)


st.plotly_chart(
    fig_severity,
    use_container_width=True
)


# ============================================================
# MANAGEMENT RECOMMENDATIONS
# ============================================================

st.subheader("💡 Management Recommendations")


recommendations = []


if total_sales_risk > 0:

    recommendations.append(
        f"🚨 Potential sales worth "
        f"₹{total_sales_risk:,.0f} are currently at risk. "
        f"Prioritize replenishment for SKUs with the "
        f"highest expected lost sales."
    )


if total_stockout_units > 0:

    recommendations.append(
        f"📉 Approximately "
        f"{total_stockout_units:,.0f} units are exposed "
        f"to stockout risk during supplier lead time. "
        f"Review reorder points and replenishment timing."
    )


if total_capital_locked > 0:

    recommendations.append(
        f"💰 Around ₹{total_capital_locked:,.0f} of "
        f"capital is tied up in excess inventory. "
        f"Consider reducing future purchase quantities "
        f"for slow-moving SKUs."
    )


if total_excess_units > 0:

    recommendations.append(
        f"📦 Approximately "
        f"{total_excess_units:,.0f} excess units "
        f"are currently held above the target inventory "
        f"level of {target_weeks} weeks."
    )


critical_count = (
    filtered_impact[
        "risk_severity"
    ] == "Critical"
).sum()


if critical_count > 0:

    recommendations.append(
        f"🔴 {critical_count:,} SKU(s) are classified "
        f"as Critical financial risks and should receive "
        f"immediate management attention."
    )


if not recommendations:

    st.success(
        "✅ No major financial inventory risks were "
        "identified for the currently selected filters."
    )

else:

    for recommendation in recommendations:

        st.info(recommendation)


# ============================================================
# BUSINESS PRIORITY BREAKDOWN
# ============================================================

st.subheader("🏢 Management Priority Breakdown")


priority_breakdown = (
    filtered_impact
    .groupby(
        "business_priority",
        as_index=False
    )
    .agg(
        SKU_Count=("sku_id", "count"),
        Sales_at_Risk=(
            "sales_at_risk",
            "sum"
        ),
        Capital_Locked=(
            "capital_locked",
            "sum"
        ),
        Financial_Exposure=(
            "financial_exposure",
            "sum"
        )
    )
)


st.dataframe(
    priority_breakdown,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# MANAGEMENT PRIORITY CHART
# ============================================================

fig_priority = px.bar(
    priority_breakdown,
    x="business_priority",
    y="Financial_Exposure",
    text="Financial_Exposure",
    title="Financial Exposure by Management Priority",
    labels={
        "business_priority":
            "Management Priority",
        "Financial_Exposure":
            "Financial Exposure (₹)"
    },
    template="plotly_dark"
)


st.plotly_chart(
    fig_priority,
    use_container_width=True
)


# ============================================================
# SKU FINANCIAL DRILL-DOWN
# ============================================================

st.divider()

st.header("🔍 SKU Financial Drill-Down")


drilldown_skus = sorted(
    filtered_impact["sku_id"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)


if drilldown_skus:

    selected_sku_detail = st.selectbox(
        "Select SKU for Detailed Analysis",
        options=drilldown_skus,
        key="business_impact_sku_drilldown"
    )


    sku_detail = filtered_impact[
        filtered_impact["sku_id"]
        .astype(str)
        == selected_sku_detail
    ].iloc[0]


    detail1, detail2, detail3, detail4 = (
        st.columns(4)
    )


    with detail1:

        st.metric(
            "Weekly Demand",
            f"{sku_detail['avg_weekly_demand']:,.1f}"
        )


    with detail2:

        st.metric(
            "Inventory Position",
            f"{sku_detail['inventory_position']:,.0f}"
        )


    with detail3:

        st.metric(
            "Sales at Risk",
            f"₹{sku_detail['sales_at_risk']:,.0f}"
        )


    with detail4:

        st.metric(
            "Capital Locked",
            f"₹{sku_detail['capital_locked']:,.0f}"
        )


    detail5, detail6, detail7, detail8 = (
        st.columns(4)
    )


    with detail5:

        st.metric(
            "Stockout Units",
            f"{sku_detail['stockout_units_at_risk']:,.0f}"
        )


    with detail6:

        st.metric(
            "Excess Units",
            f"{sku_detail['excess_units']:,.0f}"
        )


    with detail7:

        st.metric(
            "Financial Exposure",
            f"₹{sku_detail['financial_exposure']:,.0f}"
        )


    with detail8:

        st.metric(
            "Risk Severity",
            sku_detail["risk_severity"]
        )


    # --------------------------------------------------------
    # SKU DETAILS TABLE
    # --------------------------------------------------------

    st.subheader(
        f"📋 Detailed Information — {selected_sku_detail}"
    )


    detail_columns = [
        "sku_id"
    ]


    for optional_column in [
        "product_name",
        "sku_name",
        "category",
        "brand"
    ]:

        if optional_column in filtered_impact.columns:
            detail_columns.append(
                optional_column
            )


    detail_columns += [
        "avg_weekly_demand",
        "on_hand_units",
        "on_order_units",
        "inventory_position",
        "lead_time_days",
        "lead_time_demand",
        "reorder_point",
        "stockout_units_at_risk",
        "excess_units",
        "average_price",
        "unit_cost",
        "sales_at_risk",
        "capital_locked",
        "financial_exposure",
        "business_priority",
        "risk_severity"
    ]


    detail_columns = [
        column
        for column in detail_columns
        if column in filtered_impact.columns
    ]


    detail_table = filtered_impact[
        filtered_impact["sku_id"]
        .astype(str)
        == selected_sku_detail
    ][detail_columns]


    st.dataframe(
        detail_table,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# METHODOLOGY
# ============================================================

st.divider()

with st.expander(
    "📘 How Business Impact Is Calculated"
):

    st.markdown(
        f"""
### 1. Demand Forecast

The system estimates SKU-level weekly demand using
the centralized forecasting engine.

Current forecast horizon:

**{forecast_horizon} weeks**

---

### 2. Inventory Position

Inventory position is calculated as:

**On-Hand Inventory + On-Order Inventory**

This represents the quantity expected to be available
for satisfying future demand.

---

### 3. Lead-Time Demand

Expected demand during supplier lead time is calculated as:

**Average Weekly Demand × Lead Time Days ÷ 7**

---

### 4. Stockout Units at Risk

When expected lead-time demand is greater than the available
inventory position, the difference is treated as stockout risk.

**Stockout Units = Lead-Time Demand − Inventory Position**

Negative values are converted to zero.

---

### 5. Sales at Risk

Potential lost revenue is estimated from stockout units
and the SKU's average selling price.

Recent selling price is calculated using approximately:

**{price_history_weeks} weeks of sales history**

---

### 6. Excess Inventory

The dashboard compares available inventory with the target
inventory requirement.

Current target:

**{target_weeks} weeks of supply**

Inventory above this level can be classified as excess stock.

---

### 7. Capital Locked

Capital locked represents money tied up in excess inventory.

It is estimated using:

**Excess Units × Unit Cost**

---

### 8. Financial Exposure

Total SKU financial exposure is calculated as:

**Sales at Risk + Capital Locked**

This allows SKUs to be ranked according to their overall
financial impact.

---

### 9. Business Priority

SKUs are classified into two broad management priorities:

- **Protect Sales** — lost-sales exposure is greater than or
  equal to excess-inventory exposure.
- **Reduce Overstock** — excess inventory has the larger
  financial impact.

---

### 10. Risk Severity

Financial exposure is classified into:

- 🔴 Critical
- 🟠 High
- 🟡 Medium
- 🟢 Low

The classification is based on the relative financial exposure
of SKUs in the current dataset.

This makes it easier for managers to identify which products
require attention first.
"""
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "FORESIGHT • AI-Driven Demand Forecasting, "
    "Inventory Risk & Business Impact Analytics"
)