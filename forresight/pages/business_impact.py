import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from src.data_loader import (
    load_sales,
    load_inventory,
    load_sku_master,
)

from src.forecast_engine import (
    generate_all_forecasts,
    generate_forecast_summary,
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
    page_title="Business Impact | FORESIGHT",
    page_icon="💰",
    layout="wide",
)

apply_foresight_style()
show_sidebar_brand()

page_header(
    "💰 Business Impact",
    "Translate demand and inventory risk into financial exposure and management actions.",
)


# ============================================================
# LOAD DATA
# ============================================================
@st.cache_data
def load_business_data():
    sales_df = load_sales()
    inventory_df = load_inventory()
    sku_df = load_sku_master()

    return sales_df, inventory_df, sku_df


sales, inventory, sku_master = load_business_data()


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
# DATA CLEANING
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
    if column in inventory.columns:
        inventory[column] = pd.to_numeric(
            inventory[column],
            errors="coerce",
        ).fillna(0)

for column in ["unit_cost", "list_price"]:
    if column in sku_master.columns:
        sku_master[column] = pd.to_numeric(
            sku_master[column],
            errors="coerce",
        ).fillna(0)


# ============================================================
# SIDEBAR CONTROLS
# ============================================================
st.sidebar.markdown("---")
st.sidebar.subheader("Business Impact Settings")

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

price_history_weeks = st.sidebar.slider(
    "Price History (Weeks)",
    min_value=1,
    max_value=24,
    value=8,
)

top_n = st.sidebar.slider(
    "Top Products to Display",
    min_value=5,
    max_value=30,
    value=15,
)


# ============================================================
# FORECAST ENGINE
# ============================================================
with st.spinner("Calculating forecasts and business exposure..."):

    forecasts = generate_all_forecasts(
        sales,
        horizon=forecast_horizon,
    )

    forecast_summary = generate_forecast_summary(
        sales,
        horizon=forecast_horizon,
    )


if forecast_summary.empty:
    st.warning("No forecast results are available.")
    st.stop()


# ============================================================
# LATEST INVENTORY
# ============================================================
latest_inventory_date = inventory["date"].max()

latest_inventory = inventory[
    inventory["date"] == latest_inventory_date
].copy()

# prevent duplicate SKU rows
latest_inventory = (
    latest_inventory
    .sort_values("date")
    .drop_duplicates(
        subset=["sku_id"],
        keep="last",
    )
)


# ============================================================
# PRODUCT INFORMATION
# ============================================================
product_columns = [
    col
    for col in [
        "sku_id",
        "product_name",
        "category",
        "subcategory",
        "unit_cost",
        "list_price",
    ]
    if col in sku_master.columns
]

products = sku_master[
    product_columns
].drop_duplicates(
    subset=["sku_id"]
)


# ============================================================
# BUILD BUSINESS IMPACT DATASET
# ============================================================
impact = forecast_summary.merge(
    latest_inventory,
    on="sku_id",
    how="left",
)

impact = impact.merge(
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
    "reorder_point",
    "unit_cost",
    "list_price",
]:
    if column not in impact.columns:
        impact[column] = 0

    impact[column] = pd.to_numeric(
        impact[column],
        errors="coerce",
    ).fillna(0)


if "product_name" not in impact.columns:
    impact["product_name"] = impact["sku_id"].astype(str)

impact["product_name"] = impact["product_name"].fillna(
    impact["sku_id"].astype(str)
)


if "category" not in impact.columns:
    impact["category"] = "Unknown"

impact["category"] = impact["category"].fillna("Unknown")


# ============================================================
# INVENTORY POSITION
# ============================================================
impact["inventory_position"] = (
    impact["on_hand_units"]
    + impact["on_order_units"]
)


# ============================================================
# LEAD TIME DEMAND
# ============================================================
impact["lead_time_weeks"] = (
    impact["lead_time_days"] / 7
)

impact["lead_time_demand"] = (
    impact["avg_weekly_demand"]
    * impact["lead_time_weeks"]
)


# ============================================================
# WEEKS OF SUPPLY
# ============================================================
impact["weeks_of_supply"] = np.where(
    impact["avg_weekly_demand"] > 0,
    impact["inventory_position"]
    / impact["avg_weekly_demand"],
    np.inf,
)


# ============================================================
# STOCKOUT RISK
# ============================================================
impact["stockout_risk_percent"] = np.where(
    impact["lead_time_demand"] > 0,
    (
        impact["lead_time_demand"]
        - impact["inventory_position"]
    )
    / impact["lead_time_demand"]
    * 100,
    0,
)

impact["stockout_risk_percent"] = (
    impact["stockout_risk_percent"]
    .clip(lower=0, upper=100)
)


# ============================================================
# OVERSTOCK RISK %
# ============================================================
impact["overstock_risk_percent"] = np.where(
    impact["weeks_of_supply"] > target_weeks,
    (
        impact["weeks_of_supply"] - target_weeks
    )
    / target_weeks
    * 100,
    0,
)

impact["overstock_risk_percent"] = (
    impact["overstock_risk_percent"]
    .replace([np.inf, -np.inf], 0)
    .clip(lower=0, upper=100)
)


# ============================================================
# ESTIMATED SELLING PRICE
# ============================================================
latest_sales_date = sales["date"].max()

price_start_date = (
    latest_sales_date
    - pd.Timedelta(
        weeks=price_history_weeks
    )
)

recent_sales = sales[
    sales["date"] >= price_start_date
].copy()


if "revenue" in recent_sales.columns:

    recent_price = (
        recent_sales
        .groupby("sku_id")
        .agg(
            recent_units=("units_sold", "sum"),
            recent_revenue=("revenue", "sum"),
        )
        .reset_index()
    )

    recent_price["estimated_selling_price"] = np.where(
        recent_price["recent_units"] > 0,
        recent_price["recent_revenue"]
        / recent_price["recent_units"],
        np.nan,
    )

    impact = impact.merge(
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

    impact["estimated_selling_price"] = np.nan


impact["estimated_selling_price"] = (
    impact["estimated_selling_price"]
    .fillna(impact["list_price"])
)


# ============================================================
# STOCKOUT FINANCIAL EXPOSURE
# ============================================================
impact["stockout_units_at_risk"] = (
    impact["lead_time_demand"]
    - impact["inventory_position"]
).clip(lower=0)


impact["sales_at_risk"] = (
    impact["stockout_units_at_risk"]
    * impact["estimated_selling_price"]
)


# ============================================================
# TARGET INVENTORY
# ============================================================
impact["target_inventory"] = (
    impact["avg_weekly_demand"]
    * target_weeks
)


# ============================================================
# EXCESS INVENTORY
# ============================================================
impact["excess_units"] = (
    impact["inventory_position"]
    - impact["target_inventory"]
).clip(lower=0)


impact["capital_locked"] = (
    impact["excess_units"]
    * impact["unit_cost"]
)


# ============================================================
# TOTAL FINANCIAL EXPOSURE
# ============================================================
impact["total_financial_exposure"] = (
    impact["sales_at_risk"]
    + impact["capital_locked"]
)


# ============================================================
# BUSINESS PRIORITY
# ============================================================
conditions = [
    (
        impact["sales_at_risk"] <= 0
    )
    & (
        impact["capital_locked"] <= 0
    ),
    impact["sales_at_risk"]
    >= impact["capital_locked"],
]

choices = [
    "Healthy",
    "Protect Sales",
]

impact["business_priority"] = np.select(
    conditions,
    choices,
    default="Reduce Overstock",
)


# ============================================================
# RECOMMENDED ACTION
# ============================================================
def determine_action(row):

    if row["stockout_risk_percent"] >= 50:
        return "Reorder Now"

    if row["stockout_risk_percent"] >= 25:
        return "Monitor & Replenish"

    if row["weeks_of_supply"] >= 12:
        return "Markdown / Clear"

    if row["weeks_of_supply"] >= 8:
        return "Reduce Future Orders"

    return "Healthy"


impact["recommended_action"] = impact.apply(
    determine_action,
    axis=1,
)


# ============================================================
# RISK SEVERITY
# ============================================================
def calculate_risk_severity(row):

    if (
        row["stockout_risk_percent"] >= 80
        or row["sales_at_risk"] >= 100000
        or row["capital_locked"] >= 100000
    ):
        return "Critical"

    elif (
        row["stockout_risk_percent"] >= 50
        or row["weeks_of_supply"] >= 12
        or row["sales_at_risk"] >= 50000
        or row["capital_locked"] >= 50000
    ):
        return "High"

    elif (
        row["stockout_risk_percent"] >= 25
        or row["weeks_of_supply"] >= 8
        or row["sales_at_risk"] >= 10000
        or row["capital_locked"] >= 10000
    ):
        return "Medium"

    return "Low"


impact["risk_severity"] = impact.apply(
    calculate_risk_severity,
    axis=1,
)


severity_order = pd.CategoricalDtype(
    categories=[
        "Critical",
        "High",
        "Medium",
        "Low",
    ],
    ordered=True,
)

impact["risk_severity"] = impact[
    "risk_severity"
].astype(severity_order)


# ============================================================
# PRIORITY SCORE
# ============================================================
impact["priority_score"] = (
    impact["stockout_risk_percent"] * 0.35
    + impact["overstock_risk_percent"] * 0.20
    + np.minimum(
        impact["sales_at_risk"] / 1000,
        100,
    ) * 0.25
    + np.minimum(
        impact["capital_locked"] / 1000,
        100,
    ) * 0.20
)

impact["priority_score"] = impact[
    "priority_score"
].round(2)


# ============================================================
# FILTERS
# ============================================================
st.sidebar.markdown("---")
st.sidebar.subheader("Filters")


category_options = sorted(
    impact["category"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)

selected_categories = st.sidebar.multiselect(
    "category",
    options=category_options,
    default=category_options,
)


priority_options = [
    "Healthy",
    "Protect Sales",
    "Reduce Overstock",
]

selected_priorities = st.sidebar.multiselect(
    "Business Priority",
    options=priority_options,
    default=priority_options,
)


severity_options = [
    "Critical",
    "High",
    "Medium",
    "Low",
]

selected_severity = st.sidebar.multiselect(
    "Risk Severity",
    options=severity_options,
    default=severity_options,
)


sku_options = (
    impact["sku_id"]
    .dropna()
    .unique()
    .tolist()
)

selected_skus = st.sidebar.multiselect(
    "SKU",
    options=sku_options,
)


filtered_impact = impact.copy()


if selected_categories:

    filtered_impact = filtered_impact[
        filtered_impact["category"]
        .astype(str)
        .isin(selected_categories)
    ]


if selected_priorities:

    filtered_impact = filtered_impact[
        filtered_impact["business_priority"]
        .isin(selected_priorities)
    ]


if selected_severity:

    filtered_impact = filtered_impact[
        filtered_impact["risk_severity"]
        .astype(str)
        .isin(selected_severity)
    ]


if selected_skus:

    filtered_impact = filtered_impact[
        filtered_impact["sku_id"]
        .isin(selected_skus)
    ]


# ============================================================
# EMPTY FILTER CHECK
# ============================================================
if filtered_impact.empty:

    st.warning(
        "No products match the selected filters."
    )

    show_footer()
    st.stop()


# ============================================================
# KPI SUMMARY
# ============================================================
section_header(
    "Executive Financial Exposure",
    "Financial value currently exposed through stock shortages and excess inventory.",
)


total_sales_risk = (
    filtered_impact["sales_at_risk"].sum()
)

total_capital_locked = (
    filtered_impact["capital_locked"].sum()
)

total_exposure = (
    filtered_impact[
        "total_financial_exposure"
    ].sum()
)

stockout_units = (
    filtered_impact[
        "stockout_units_at_risk"
    ].sum()
)

excess_units = (
    filtered_impact["excess_units"].sum()
)


col1, col2, col3, col4, col5 = st.columns(5)

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
    "Units at Stockout Risk",
    f"{stockout_units:,.0f}",
)

col5.metric(
    "Excess Units",
    f"{excess_units:,.0f}",
)


# ============================================================
# MANAGEMENT STATUS
# ============================================================
critical_count = (
    filtered_impact["risk_severity"]
    .astype(str)
    .eq("Critical")
    .sum()
)

high_count = (
    filtered_impact["risk_severity"]
    .astype(str)
    .eq("High")
    .sum()
)

protect_count = (
    filtered_impact[
        "business_priority"
    ]
    .eq("Protect Sales")
    .sum()
)

reduce_count = (
    filtered_impact[
        "business_priority"
    ]
    .eq("Reduce Overstock")
    .sum()
)


col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Critical SKUs",
    f"{critical_count:,}",
)

col2.metric(
    "High-Risk SKUs",
    f"{high_count:,}",
)

col3.metric(
    "Protect Sales",
    f"{protect_count:,}",
)

col4.metric(
    "Reduce Overstock",
    f"{reduce_count:,}",
)


# ============================================================
# FINANCIAL EXPOSURE CHART
# ============================================================
section_header(
    "Financial Exposure",
    "Compare potential lost sales against working capital tied up in excess inventory.",
)


financial_summary = pd.DataFrame(
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
    financial_summary,
    x="Exposure Type",
    y="Amount",
    text_auto=".2s",
    title="Business Financial Exposure",
)

fig.update_layout(
    yaxis_title="Financial Value",
    xaxis_title="",
)

st.plotly_chart(
    fig,
    use_container_width=True,
)


# ============================================================
# BUSINESS PRIORITY DISTRIBUTION
# ============================================================
section_header(
    "Business Priority Distribution",
    "Products classified according to the dominant financial issue.",
)


priority_distribution = (
    filtered_impact[
        "business_priority"
    ]
    .value_counts()
    .reset_index()
)

priority_distribution.columns = [
    "Business Priority",
    "Products",
]

fig = px.bar(
    priority_distribution,
    x="Business Priority",
    y="Products",
    text_auto=True,
    title="Business Priority by SKU Count",
)

st.plotly_chart(
    fig,
    use_container_width=True,
)


# ============================================================
# RISK SEVERITY DISTRIBUTION
# ============================================================
section_header(
    "Risk Severity",
    "Number of products requiring management attention.",
)


severity_distribution = (
    filtered_impact[
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

severity_distribution.columns = [
    "Risk Severity",
    "Products",
]

fig = px.bar(
    severity_distribution,
    x="Risk Severity",
    y="Products",
    text_auto=True,
    title="Risk Severity Distribution",
)

st.plotly_chart(
    fig,
    use_container_width=True,
)


# ============================================================
# CATEGORY FINANCIAL EXPOSURE
# ============================================================
section_header(
    "Category Financial Exposure",
    "Identify categories driving the greatest financial impact.",
)


category_impact = (
    filtered_impact
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
)


category_impact = category_impact.sort_values(
    "total_exposure",
    ascending=False,
)


category_long = category_impact.melt(
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

fig.update_layout(
    xaxis_title="category",
    yaxis_title="Financial Value",
)

st.plotly_chart(
    fig,
    use_container_width=True,
)


# ============================================================
# TOP BUSINESS RISKS
# ============================================================
section_header(
    "Top Business Risks",
    "Products with the highest combined financial exposure.",
)


top_exposure = (
    filtered_impact
    .sort_values(
        "total_financial_exposure",
        ascending=False,
    )
    .head(top_n)
)


fig = px.bar(
    top_exposure,
    x="product_name",
    y="total_financial_exposure",
    color="business_priority",
    hover_data=[
        "sku_id",
        "category",
        "sales_at_risk",
        "capital_locked",
        "risk_severity",
    ],
    title=f"Top {top_n} Products by Financial Exposure",
)

fig.update_layout(
    xaxis_title="Product",
    yaxis_title="Total Financial Exposure",
)

st.plotly_chart(
    fig,
    use_container_width=True,
)


# ============================================================
# PROTECT SALES PRIORITIES
# ============================================================
section_header(
    "Protect Sales Priorities",
    "Products where inventory shortages could result in lost revenue.",
)


protect_sales = filtered_impact[
    filtered_impact[
        "business_priority"
    ] == "Protect Sales"
].copy()


protect_sales = protect_sales.sort_values(
    "sales_at_risk",
    ascending=False,
).head(top_n)


if protect_sales.empty:

    st.success(
        "No significant sales-protection priorities under the current filters."
    )

else:

    display_protect = protect_sales[
        [
            "sku_id",
            "product_name",
            "category",
            "avg_weekly_demand",
            "inventory_position",
            "weeks_of_supply",
            "stockout_risk_percent",
            "stockout_units_at_risk",
            "sales_at_risk",
            "demand_trend",
            "forecast_confidence",
            "risk_severity",
            "recommended_action",
        ]
    ].copy()

    display_protect[
        "avg_weekly_demand"
    ] = display_protect[
        "avg_weekly_demand"
    ].round(2)

    display_protect[
        "weeks_of_supply"
    ] = display_protect[
        "weeks_of_supply"
    ].replace(
        np.inf,
        np.nan,
    ).round(2)

    display_protect[
        "stockout_risk_percent"
    ] = display_protect[
        "stockout_risk_percent"
    ].round(2)

    display_protect[
        "stockout_units_at_risk"
    ] = display_protect[
        "stockout_units_at_risk"
    ].round(0)

    display_protect[
        "sales_at_risk"
    ] = display_protect[
        "sales_at_risk"
    ].round(2)

    st.dataframe(
        display_protect,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# REDUCE OVERSTOCK PRIORITIES
# ============================================================
section_header(
    "Reduce Overstock Priorities",
    "Products where excess stock is tying up working capital.",
)


reduce_overstock = filtered_impact[
    filtered_impact[
        "business_priority"
    ] == "Reduce Overstock"
].copy()


reduce_overstock = reduce_overstock.sort_values(
    "capital_locked",
    ascending=False,
).head(top_n)


if reduce_overstock.empty:

    st.success(
        "No significant overstock reduction priorities under the current filters."
    )

else:

    display_overstock = reduce_overstock[
        [
            "sku_id",
            "product_name",
            "category",
            "avg_weekly_demand",
            "inventory_position",
            "weeks_of_supply",
            "excess_units",
            "unit_cost",
            "capital_locked",
            "demand_trend",
            "forecast_confidence",
            "risk_severity",
            "recommended_action",
        ]
    ].copy()

    display_overstock[
        "avg_weekly_demand"
    ] = display_overstock[
        "avg_weekly_demand"
    ].round(2)

    display_overstock[
        "weeks_of_supply"
    ] = display_overstock[
        "weeks_of_supply"
    ].replace(
        np.inf,
        np.nan,
    ).round(2)

    display_overstock[
        "excess_units"
    ] = display_overstock[
        "excess_units"
    ].round(0)

    display_overstock[
        "capital_locked"
    ] = display_overstock[
        "capital_locked"
    ].round(2)

    st.dataframe(
        display_overstock,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# MANAGEMENT RECOMMENDATIONS
# ============================================================
section_header(
    "Management Recommendations",
    "Automatically generated recommendations from the current risk profile.",
)


if total_sales_risk > total_capital_locked:

    recommendation_card(
        "Protect Revenue",
        (
            "Potential lost sales exceed excess inventory exposure. "
            "Prioritize replenishment of high-demand and high-stockout-risk products."
        ),
    )

else:

    recommendation_card(
        "Release Working Capital",
        (
            "Capital locked in excess inventory exceeds potential lost sales. "
            "Prioritize markdowns, order reductions, and inventory transfers."
        ),
    )


if critical_count > 0:

    recommendation_card(
        "Critical Risk Escalation",
        (
            f"{critical_count} SKU(s) currently have Critical business risk. "
            "These products should receive immediate management review."
        ),
    )


if protect_count > 0:

    recommendation_card(
        "Sales Protection",
        (
            f"{protect_count} SKU(s) are classified as Protect Sales priorities. "
            "Review reorder quantities, supplier lead times, and available inventory."
        ),
    )


if reduce_count > 0:

    recommendation_card(
        "Inventory Optimization",
        (
            f"{reduce_count} SKU(s) are classified as Reduce Overstock priorities. "
            "Consider reducing future purchase orders or using targeted promotions."
        ),
    )


# ============================================================
# SKU LEVEL DRILLDOWN
# ============================================================
section_header(
    "SKU Business Impact Drill-Down",
    "Inspect the financial and forecast position of an individual product.",
)


filtered_sku_ids = (
    filtered_impact["sku_id"]
    .dropna()
    .tolist()
)
selected_sku = st.selectbox(
    "Select SKU",
    options=filtered_sku_ids,
    format_func=lambda sku: (
        f"{sku} - "
        f"{filtered_impact.loc[filtered_impact['sku_id'] == sku, 'product_name'].iloc[0]}"
    ),
)

selected_row = filtered_impact[
    filtered_impact["sku_id"] == selected_sku
].iloc[0]
# ============================================================
# PRODUCT KPI DRILLDOWN
# ============================================================
col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Sales at Risk",
    f"₹{selected_row['sales_at_risk']:,.0f}",
)

col2.metric(
    "Capital Locked",
    f"₹{selected_row['capital_locked']:,.0f}",
)

col3.metric(
    "Weeks of Supply",
    (
        f"{selected_row['weeks_of_supply']:.1f}"
        if np.isfinite(
            selected_row["weeks_of_supply"]
        )
        else "N/A"
    ),
)

col4.metric(
    "Priority Score",
    f"{selected_row['priority_score']:.1f}",
)


col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Stockout Risk",
    f"{selected_row['stockout_risk_percent']:.1f}%",
)

col2.metric(
    "Overstock Risk",
    f"{selected_row['overstock_risk_percent']:.1f}%",
)

col3.metric(
    "Demand Trend",
    str(
        selected_row[
            "demand_trend"
        ]
    ),
)

col4.metric(
    "Forecast Confidence",
    str(
        selected_row[
            "forecast_confidence"
        ]
    ),
)


st.info(
    f"""
**Product:** {selected_row['product_name']}

**Category:** {selected_row['category']}

**Business Priority:** {selected_row['business_priority']}

**Risk Severity:** {selected_row['risk_severity']}

**Recommended Action:** {selected_row['recommended_action']}
"""
)


# ============================================================
# SKU FORECAST TRAJECTORY
# ============================================================
selected_forecast = forecasts[
    forecasts["sku_id"] == selected_sku
].copy()


if not selected_forecast.empty:

    section_header(
        "Forecast Trajectory",
        "Expected weekly demand and approximate uncertainty range.",
    )

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=selected_forecast["date"],
            y=selected_forecast[
                "upper_bound"
            ],
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=selected_forecast["date"],
            y=selected_forecast[
                "lower_bound"
            ],
            mode="lines",
            fill="tonexty",
            name="Forecast Range",
            line=dict(width=0),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=selected_forecast["date"],
            y=selected_forecast[
                "predicted_demand"
            ],
            mode="lines+markers",
            name="Predicted Demand",
        )
    )

    fig.update_layout(
        title=(
            f"Demand Forecast — "
            f"{selected_row['product_name']}"
        ),
        xaxis_title="Week",
        yaxis_title="Predicted Units",
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )


    forecast_detail = selected_forecast[
        [
            "date",
            "predicted_demand",
            "lower_bound",
            "upper_bound",
            "demand_trend",
            "forecast_confidence",
        ]
    ].copy()

    forecast_detail[
        "predicted_demand"
    ] = forecast_detail[
        "predicted_demand"
    ].round(2)

    forecast_detail[
        "lower_bound"
    ] = forecast_detail[
        "lower_bound"
    ].round(2)

    forecast_detail[
        "upper_bound"
    ] = forecast_detail[
        "upper_bound"
    ].round(2)

    st.dataframe(
        forecast_detail,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# COMPLETE BUSINESS IMPACT TABLE
# ============================================================
section_header(
    "Complete Business Impact Summary",
    "Detailed operational and financial impact for all filtered products.",
)


final_columns = [
    "sku_id",
    "product_name",
    "category",
    "avg_weekly_demand",
    "total_forecast_demand",
    "demand_trend",
    "forecast_confidence",
    "inventory_position",
    "weeks_of_supply",
    "stockout_risk_percent",
    "overstock_risk_percent",
    "stockout_units_at_risk",
    "sales_at_risk",
    "excess_units",
    "capital_locked",
    "total_financial_exposure",
    "business_priority",
    "risk_severity",
    "priority_score",
    "recommended_action",
]


final_table = filtered_impact[
    final_columns
].copy()


numeric_round_columns = [
    "avg_weekly_demand",
    "total_forecast_demand",
    "inventory_position",
    "weeks_of_supply",
    "stockout_risk_percent",
    "overstock_risk_percent",
    "stockout_units_at_risk",
    "sales_at_risk",
    "excess_units",
    "capital_locked",
    "total_financial_exposure",
    "priority_score",
]


for column in numeric_round_columns:

    final_table[column] = (
        pd.to_numeric(
            final_table[column],
            errors="coerce",
        )
        .replace(
            [np.inf, -np.inf],
            np.nan,
        )
        .round(2)
    )


final_table = final_table.sort_values(
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
    final_table,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# METHODOLOGY
# ============================================================
with st.expander(
    "ℹ️ Business Impact Methodology"
):

    st.markdown(
        f"""
### Sales at Risk

Potential sales exposure is estimated as:

**Stockout Units × Estimated Selling Price**

Stockout units are calculated by comparing projected demand
during supplier lead time with currently available and incoming inventory.

---

### Capital Locked

Capital tied up in excess inventory is estimated as:

**Excess Units × Unit Cost**

Target inventory is currently configured at:

**{target_weeks} weeks of forecast demand**

---

### Business Priority

Each product is assigned to one of three groups:

- **Protect Sales** — potential lost sales are greater than excess inventory cost.
- **Reduce Overstock** — excess inventory capital exceeds potential lost sales.
- **Healthy** — no material exposure is identified.

---

### Risk Severity

Financial exposure, stockout probability and weeks of supply
are combined to classify products into:

**Critical → High → Medium → Low**

---

### Forecast Confidence

Forecast confidence is based on historical demand variability.
The displayed lower and upper forecast bands represent an
approximate uncertainty range and should not be interpreted
as formally calibrated statistical prediction intervals.
"""
    )


# ============================================================
# FOOTER
# ============================================================
show_footer()