import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from src.data_loader import (
    load_sales,
    load_inventory,
    load_sku_master
)

from src.forecast_engine import (
    generate_all_forecasts,
    generate_forecast_summary
)

from src.risk_scoring import (
    classify_stockout_risk,
    classify_overstock_risk,
    calculate_action,
    calculate_priority_score
)

from src.ui import (
    apply_foresight_style,
    show_sidebar_brand,
    page_header,
    section_header,
    show_footer
)


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="FORESIGHT | Risk Dashboard",
    page_icon="⚠️",
    layout="wide"
)

apply_foresight_style()
show_sidebar_brand()


# =========================================================
# PAGE HEADER
# =========================================================

page_header(
    "⚠️ Risk Dashboard",
    "AI-powered inventory risk monitoring using forecast demand, supply coverage and financial exposure."
)


# =========================================================
# LOAD DATA
# =========================================================

sales = load_sales()
inventory = load_inventory()
sku_master = load_sku_master()


if sales is None or sales.empty:

    st.error("Sales data could not be loaded.")
    st.stop()


if inventory is None or inventory.empty:

    st.error("Inventory data could not be loaded.")
    st.stop()


# =========================================================
# CLEAN SALES
# =========================================================

sales = sales.copy()

sales["date"] = pd.to_datetime(
    sales["date"],
    errors="coerce"
)

sales["units_sold"] = pd.to_numeric(
    sales["units_sold"],
    errors="coerce"
).fillna(0)

sales = sales.dropna(
    subset=["date", "sku_id"]
)

sales["units_sold"] = (
    sales["units_sold"]
    .clip(lower=0)
)


# =========================================================
# CLEAN INVENTORY
# =========================================================

inventory = inventory.copy()

# ---------------------------------------------------------
# INVENTORY COLUMN COMPATIBILITY
# ---------------------------------------------------------
# Your FORESIGHT inventory dataset uses:
#
# sku_id
# date
# on_hand
# on_order
# lead_time_days
#
# This block also supports the alternative names:
# on_hand_units
# on_order_units
#
# so the dashboard does not break.
# ---------------------------------------------------------

inventory_column_mapping = {}

if "on_hand" in inventory.columns:

    inventory_column_mapping["on_hand"] = "on_hand_units"

elif "on_hand_units" in inventory.columns:

    inventory_column_mapping["on_hand_units"] = "on_hand_units"

else:

    inventory["on_hand_units"] = 0


if "on_order" in inventory.columns:

    inventory_column_mapping["on_order"] = "on_order_units"

elif "on_order_units" in inventory.columns:

    inventory_column_mapping["on_order_units"] = "on_order_units"

else:

    inventory["on_order_units"] = 0


# Rename only if required

if inventory_column_mapping:

    inventory = inventory.rename(
        columns=inventory_column_mapping
    )


# ---------------------------------------------------------
# REQUIRED BASIC INVENTORY COLUMNS
# ---------------------------------------------------------

if "sku_id" not in inventory.columns:

    st.error(
        "Inventory dataset is missing required column: sku_id"
    )

    st.write(
        "Available inventory columns:",
        inventory.columns.tolist()
    )

    st.stop()


if "date" not in inventory.columns:

    st.error(
        "Inventory dataset is missing required column: date"
    )

    st.write(
        "Available inventory columns:",
        inventory.columns.tolist()
    )

    st.stop()


# ---------------------------------------------------------
# DATE CLEANING
# ---------------------------------------------------------

inventory["date"] = pd.to_datetime(
    inventory["date"],
    errors="coerce"
)


# ---------------------------------------------------------
# NUMERIC INVENTORY FIELDS
# ---------------------------------------------------------

for column in [
    "on_hand_units",
    "on_order_units",
    "lead_time_days",
    "reorder_point"
]:

    if column not in inventory.columns:

        # reorder_point is optional
        if column == "reorder_point":

            inventory[column] = np.nan

        else:

            inventory[column] = 0

    inventory[column] = pd.to_numeric(
        inventory[column],
        errors="coerce"
    ).fillna(0)


inventory = inventory.dropna(
    subset=["date", "sku_id"]
)


# =========================================================
# SIDEBAR SETTINGS
# =========================================================

st.sidebar.markdown(
    "### ⚙️ Risk Settings"
)

forecast_horizon = st.sidebar.slider(
    "Forecast Horizon (Weeks)",
    min_value=1,
    max_value=16,
    value=8
)

top_n = st.sidebar.slider(
    "Top Products",
    min_value=5,
    max_value=30,
    value=15
)


# =========================================================
# GENERATE CENTRALIZED FORECAST
# =========================================================

with st.spinner(
    "Calculating demand and inventory risk..."
):

    forecasts = generate_all_forecasts(
        sales,
        horizon=forecast_horizon
    )

    forecast_summary = generate_forecast_summary(
        sales,
        horizon=forecast_horizon
    )


if forecast_summary is None or forecast_summary.empty:

    st.warning(
        "No forecast data is available."
    )

    st.stop()


# =========================================================
# LATEST INVENTORY SNAPSHOT
# =========================================================

latest_inventory_date = inventory["date"].max()

latest_inventory = (
    inventory[
        inventory["date"]
        == latest_inventory_date
    ]
    .copy()
)


# =========================================================
# PRODUCT INFORMATION
# =========================================================

if sku_master is not None and not sku_master.empty:

    sku_master = sku_master.copy()

    product_columns = [
        col for col in [
            "sku_id",
            "product_name",
            "category",
            "subcategory",
            "unit_cost",
            "list_price"
        ]
        if col in sku_master.columns
    ]

    product_info = (
        sku_master[
            product_columns
        ]
        .drop_duplicates(
            subset=["sku_id"]
        )
    )

else:

    product_info = pd.DataFrame({
        "sku_id": forecast_summary["sku_id"]
    })

    product_info["product_name"] = (
        product_info["sku_id"]
        .astype(str)
    )

    product_info["category"] = "Unknown"

    product_info["subcategory"] = "Unknown"

    product_info["unit_cost"] = 0

    product_info["list_price"] = 0


# ---------------------------------------------------------
# MAKE SURE PRODUCT COLUMNS EXIST
# ---------------------------------------------------------

for column, default_value in {
    "product_name": "Unknown",
    "category": "Unknown",
    "subcategory": "Unknown",
    "unit_cost": 0,
    "list_price": 0
}.items():

    if column not in product_info.columns:

        product_info[column] = default_value


# =========================================================
# BUILD RISK DATASET
# =========================================================

risk = forecast_summary.merge(
    latest_inventory,
    on="sku_id",
    how="left",
    suffixes=("", "_inventory")
)


risk = risk.merge(
    product_info,
    on="sku_id",
    how="left",
    suffixes=("", "_product")
)


# =========================================================
# CLEAN INVENTORY / PRODUCT FIELDS
# =========================================================

for column in [
    "on_hand_units",
    "on_order_units",
    "lead_time_days",
    "reorder_point",
    "unit_cost",
    "list_price"
]:

    if column not in risk.columns:

        risk[column] = 0

    risk[column] = pd.to_numeric(
        risk[column],
        errors="coerce"
    ).fillna(0)


for column, default_value in {
    "product_name": "Unknown",
    "category": "Unknown",
    "subcategory": "Unknown"
}.items():

    if column not in risk.columns:

        risk[column] = default_value

    risk[column] = (
        risk[column]
        .fillna(default_value)
        .astype(str)
    )


# =========================================================
# INVENTORY POSITION
# =========================================================

risk["inventory_position"] = (
    risk["on_hand_units"]
    + risk["on_order_units"]
)


# =========================================================
# LEAD-TIME DEMAND
# =========================================================

if "avg_weekly_demand" not in risk.columns:

    risk["avg_weekly_demand"] = 0


risk["avg_weekly_demand"] = pd.to_numeric(
    risk["avg_weekly_demand"],
    errors="coerce"
).fillna(0)


risk["lead_time_demand"] = (
    risk["avg_weekly_demand"]
    * risk["lead_time_days"]
    / 7
)


# =========================================================
# WEEKS OF SUPPLY
# =========================================================

risk["weeks_of_supply"] = np.where(
    risk["avg_weekly_demand"] > 0,

    risk["inventory_position"]
    / risk["avg_weekly_demand"],

    0
)


risk["weeks_of_supply"] = (
    risk["weeks_of_supply"]
    .replace(
        [np.inf, -np.inf],
        0
    )
    .fillna(0)
)


# =========================================================
# STOCKOUT RISK
# =========================================================

risk["stockout_risk_percent"] = np.where(
    risk["lead_time_demand"] > 0,

    np.maximum(
        0,
        (
            1
            -
            risk["inventory_position"]
            /
            risk["lead_time_demand"]
        )
        * 100
    ),

    0
)


risk["stockout_risk_percent"] = (
    risk["stockout_risk_percent"]
    .clip(0, 100)
)


# =========================================================
# STOCKOUT RISK CATEGORY
# =========================================================

risk["stockout_risk"] = (
    risk["stockout_risk_percent"]
    .apply(
        classify_stockout_risk
    )
)


# =========================================================
# OVERSTOCK RISK
# =========================================================

risk["overstock_risk"] = (
    risk["weeks_of_supply"]
    .apply(
        classify_overstock_risk
    )
)


# =========================================================
# RECOMMENDED ACTION
# =========================================================

risk["recommended_action"] = (
    risk.apply(
        lambda row: calculate_action(
            row["stockout_risk_percent"],
            row["weeks_of_supply"]
        ),
        axis=1
    )
)


# =========================================================
# PRIORITY SCORE
# =========================================================

risk["priority_score"] = (
    risk.apply(
        lambda row: calculate_priority_score(
            row["stockout_risk_percent"],
            row["weeks_of_supply"]
        ),
        axis=1
    )
)


# =========================================================
# FINANCIAL EXPOSURE
# =========================================================

recent_cutoff = (
    sales["date"].max()
    - pd.Timedelta(days=56)
)


recent_sales = sales[
    sales["date"] >= recent_cutoff
].copy()


if "revenue" in recent_sales.columns:

    recent_sales["revenue"] = pd.to_numeric(
        recent_sales["revenue"],
        errors="coerce"
    ).fillna(0)

    price_by_sku = (
        recent_sales
        .groupby("sku_id")
        .agg(
            recent_units=(
                "units_sold",
                "sum"
            ),
            recent_revenue=(
                "revenue",
                "sum"
            )
        )
        .reset_index()
    )

    price_by_sku["estimated_selling_price"] = (
        np.where(
            price_by_sku["recent_units"] > 0,

            price_by_sku["recent_revenue"]
            /
            price_by_sku["recent_units"],

            0
        )
    )

    risk = risk.merge(
        price_by_sku[
            [
                "sku_id",
                "estimated_selling_price"
            ]
        ],
        on="sku_id",
        how="left"
    )

else:

    risk["estimated_selling_price"] = 0


risk["estimated_selling_price"] = (
    pd.to_numeric(
        risk["estimated_selling_price"],
        errors="coerce"
    )
    .fillna(0)
)


# Use list price where selling price is unavailable

risk["estimated_selling_price"] = np.where(
    risk["estimated_selling_price"] > 0,

    risk["estimated_selling_price"],

    risk["list_price"]
)


# =========================================================
# SALES AT RISK
# =========================================================

risk["stockout_units_at_risk"] = np.maximum(
    risk["lead_time_demand"]
    -
    risk["inventory_position"],
    0
)


risk["sales_at_risk"] = (
    risk["stockout_units_at_risk"]
    *
    risk["estimated_selling_price"]
)


# =========================================================
# TARGET INVENTORY
# =========================================================

target_weeks = st.sidebar.slider(
    "Target Weeks of Supply",
    min_value=1,
    max_value=16,
    value=8
)


risk["target_inventory"] = (
    risk["avg_weekly_demand"]
    * target_weeks
)


risk["excess_units"] = np.maximum(
    risk["inventory_position"]
    -
    risk["target_inventory"],
    0
)


# =========================================================
# CAPITAL LOCKED
# =========================================================

risk["capital_locked"] = (
    risk["excess_units"]
    *
    risk["unit_cost"]
)


# =========================================================
# RISK SEVERITY
# =========================================================

def calculate_risk_severity(row):

    stockout = row["stockout_risk_percent"]

    weeks = row["weeks_of_supply"]

    sales_risk = row.get(
        "sales_at_risk",
        0
    )

    capital_locked = row.get(
        "capital_locked",
        0
    )

    if (
        stockout >= 80
        or sales_risk >= 100000
        or capital_locked >= 100000
    ):

        return "Critical"

    if (
        stockout >= 50
        or weeks >= 12
        or sales_risk >= 50000
        or capital_locked >= 50000
    ):

        return "High"

    if (
        stockout >= 25
        or weeks >= 8
        or sales_risk >= 10000
        or capital_locked >= 10000
    ):

        return "Medium"

    return "Low"


risk["risk_severity"] = (
    risk.apply(
        calculate_risk_severity,
        axis=1
    )
)


# =========================================================
# PRIORITY ORDER
# =========================================================

severity_order = pd.CategoricalDtype(
    categories=[
        "Critical",
        "High",
        "Medium",
        "Low"
    ],
    ordered=True
)

risk["risk_severity"] = (
    risk["risk_severity"]
    .astype(severity_order)
)


# =========================================================
# FILTERS
# =========================================================

section_header(
    "🔎 Risk Filters",
    "Focus on specific categories, risk levels, actions or SKUs."
)


filter1, filter2, filter3, filter4 = st.columns(
    [1, 1, 1, 2]
)


with filter1:

    categories = sorted(
        risk["category"]
        .fillna("Unknown")
        .astype(str)
        .unique()
        .tolist()
    )

    selected_categories = st.multiselect(
        "Category",
        categories,
        default=categories
    )


with filter2:

    severity_options = [
        "Critical",
        "High",
        "Medium",
        "Low"
    ]

    selected_severity = st.multiselect(
        "Risk Severity",
        severity_options,
        default=severity_options
    )


with filter3:

    action_options = sorted(
        risk["recommended_action"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    selected_actions = st.multiselect(
        "Recommended Action",
        action_options,
        default=action_options
    )


with filter4:

    sku_options = (
        risk["sku_id"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    selected_skus = st.multiselect(
        "SKU",
        sku_options
    )


# =========================================================
# APPLY FILTERS
# =========================================================

filtered_risk = risk.copy()


if selected_categories:

    filtered_risk = filtered_risk[
        filtered_risk["category"]
        .astype(str)
        .isin(selected_categories)
    ]


if selected_severity:

    filtered_risk = filtered_risk[
        filtered_risk["risk_severity"]
        .astype(str)
        .isin(selected_severity)
    ]


if selected_actions:

    filtered_risk = filtered_risk[
        filtered_risk["recommended_action"]
        .astype(str)
        .isin(selected_actions)
    ]


if selected_skus:

    filtered_risk = filtered_risk[
        filtered_risk["sku_id"]
        .astype(str)
        .isin(selected_skus)
    ]


if filtered_risk.empty:

    st.warning(
        "No products match the selected filters."
    )

    st.stop()


# =========================================================
# EXECUTIVE RISK KPIs
# =========================================================

section_header(
    "📊 Risk Overview",
    "Portfolio-level inventory and demand risk indicators."
)


k1, k2, k3, k4, k5, k6 = st.columns(6)


with k1:

    st.metric(
        "SKUs",
        f"{len(filtered_risk):,}"
    )


with k2:

    critical_count = (
        filtered_risk["risk_severity"]
        .astype(str)
        .eq("Critical")
        .sum()
    )

    st.metric(
        "Critical",
        f"{critical_count:,}"
    )


with k3:

    high_count = (
        filtered_risk["risk_severity"]
        .astype(str)
        .eq("High")
        .sum()
    )

    st.metric(
        "High Risk",
        f"{high_count:,}"
    )


with k4:

    stockout_count = (
        filtered_risk["stockout_risk"]
        .astype(str)
        .eq("High")
        .sum()
    )

    st.metric(
        "High Stockout",
        f"{stockout_count:,}"
    )


with k5:

    st.metric(
        "Sales at Risk",
        f"₹{filtered_risk['sales_at_risk'].sum():,.0f}"
    )


with k6:

    st.metric(
        "Capital Locked",
        f"₹{filtered_risk['capital_locked'].sum():,.0f}"
    )


# =========================================================
# RISK SEVERITY DISTRIBUTION
# =========================================================

section_header(
    "🚨 Risk Severity Distribution",
    "Prioritized classification of operational and financial risk."
)


severity_counts = (
    filtered_risk[
        "risk_severity"
    ]
    .astype(str)
    .value_counts()
    .reindex(
        [
            "Critical",
            "High",
            "Medium",
            "Low"
        ],
        fill_value=0
    )
    .reset_index()
)

severity_counts.columns = [
    "Severity",
    "SKU Count"
]


fig_severity = px.bar(
    severity_counts,
    x="Severity",
    y="SKU Count",
    text="SKU Count",
    title="Risk Severity by SKU"
)

fig_severity.update_layout(
    height=400,
    showlegend=False
)

st.plotly_chart(
    fig_severity,
    use_container_width=True
)


# =========================================================
# ACTION DISTRIBUTION
# =========================================================

section_header(
    "🛠️ Recommended Actions",
    "Recommended operational response for each risk condition."
)


action_counts = (
    filtered_risk["recommended_action"]
    .value_counts()
    .reset_index()
)

action_counts.columns = [
    "Recommended Action",
    "SKU Count"
]


fig_action = px.bar(
    action_counts,
    x="Recommended Action",
    y="SKU Count",
    text="SKU Count",
    title="Recommended Action Distribution"
)

fig_action.update_layout(
    height=420,
    showlegend=False
)

st.plotly_chart(
    fig_action,
    use_container_width=True
)


# =========================================================
# STOCKOUT VS OVERSTOCK MATRIX
# =========================================================

section_header(
    "⚖️ Stockout vs Overstock Risk",
    "Identify products exposed to either insufficient or excessive inventory."
)


fig_matrix = px.scatter(
    filtered_risk,
    x="stockout_risk_percent",
    y="weeks_of_supply",
    size="priority_score",
    hover_name="product_name",
    hover_data=[
        "sku_id",
        "risk_severity",
        "recommended_action",
        "forecast_confidence"
    ],
    title="Stockout Risk vs Weeks of Supply"
)

fig_matrix.add_vline(
    x=50,
    line_dash="dash"
)

fig_matrix.add_vline(
    x=80,
    line_dash="dash"
)

fig_matrix.add_hline(
    y=8,
    line_dash="dash"
)

fig_matrix.add_hline(
    y=12,
    line_dash="dash"
)

fig_matrix.update_layout(
    height=520,
    xaxis_title="Stockout Risk (%)",
    yaxis_title="Weeks of Supply"
)

st.plotly_chart(
    fig_matrix,
    use_container_width=True
)


# =========================================================
# DEMAND VS INVENTORY
# =========================================================

section_header(
    "📦 Forecast Demand vs Inventory",
    "Compare expected weekly demand against current inventory position."
)


fig_demand_inventory = px.scatter(
    filtered_risk,
    x="avg_weekly_demand",
    y="inventory_position",
    size="priority_score",
    hover_name="product_name",
    hover_data=[
        "sku_id",
        "weeks_of_supply",
        "risk_severity",
        "forecast_confidence"
    ],
    title="Forecast Demand vs Inventory Position"
)

fig_demand_inventory.update_layout(
    height=500,
    xaxis_title="Average Weekly Forecast Demand",
    yaxis_title="Inventory Position"
)

st.plotly_chart(
    fig_demand_inventory,
    use_container_width=True
)


# =========================================================
# FORECAST CONFIDENCE VS RISK
# =========================================================

section_header(
    "🎯 Forecast Confidence vs Risk",
    "Identify high-risk products where forecast reliability may influence decisions."
)


if "forecast_confidence" not in filtered_risk.columns:

    filtered_risk["forecast_confidence"] = "Unknown"


confidence_order = [
    "High",
    "Medium",
    "Low",
    "Unknown"
]


confidence_counts = (
    filtered_risk[
        "forecast_confidence"
    ]
    .fillna("Unknown")
    .astype(str)
    .value_counts()
    .reindex(
        confidence_order,
        fill_value=0
    )
    .reset_index()
)

confidence_counts.columns = [
    "Forecast Confidence",
    "SKU Count"
]


fig_confidence = px.bar(
    confidence_counts,
    x="Forecast Confidence",
    y="SKU Count",
    text="SKU Count",
    title="Forecast Confidence Distribution"
)

fig_confidence.update_layout(
    height=400,
    showlegend=False
)

st.plotly_chart(
    fig_confidence,
    use_container_width=True
)


# =========================================================
# TOP PRIORITY PRODUCTS
# =========================================================

section_header(
    "🔥 Top Priority Products",
    "Products requiring the most immediate management attention."
)


top_priority = (
    filtered_risk
    .sort_values(
        [
            "risk_severity",
            "priority_score"
        ],
        ascending=[
            True,
            False
        ]
    )
    .head(top_n)
    .copy()
)


priority_columns = [
    col for col in [
        "sku_id",
        "product_name",
        "category",
        "risk_severity",
        "forecast_confidence",
        "avg_weekly_demand",
        "inventory_position",
        "weeks_of_supply",
        "stockout_risk_percent",
        "recommended_action",
        "priority_score",
        "sales_at_risk",
        "capital_locked"
    ]
    if col in top_priority.columns
]


priority_table = top_priority[
    priority_columns
].copy()


if "stockout_risk_percent" in priority_table.columns:

    priority_table[
        "stockout_risk_percent"
    ] = priority_table[
        "stockout_risk_percent"
    ].round(1)


if "sales_at_risk" in priority_table.columns:

    priority_table[
        "sales_at_risk"
    ] = priority_table[
        "sales_at_risk"
    ].round(0)


if "capital_locked" in priority_table.columns:

    priority_table[
        "capital_locked"
    ] = priority_table[
        "capital_locked"
    ].round(0)


st.dataframe(
    priority_table,
    use_container_width=True,
    hide_index=True
)


# =========================================================
# STOCKOUT PRIORITIES
# =========================================================

section_header(
    "🚨 Immediate Reorder Priorities",
    "Products where forecast demand may exceed available supply."
)


# Support multiple possible action names

reorder_actions = [
    "Reorder Now",
    "REORDER NOW",
    "URGENTLY REPLENISH",
    "URGENT REORDER",
    "CRITICAL REORDER"
]


reorder = (
    filtered_risk[
        filtered_risk["recommended_action"]
        .astype(str)
        .str.upper()
        .isin(
            [x.upper() for x in reorder_actions]
        )
    ]
    .sort_values(
        "sales_at_risk",
        ascending=False
    )
    .head(top_n)
)


if reorder.empty:

    st.success(
        "No products currently require immediate reorder."
    )

else:

    reorder_columns = [
        col for col in [
            "sku_id",
            "product_name",
            "category",
            "forecast_confidence",
            "avg_weekly_demand",
            "inventory_position",
            "lead_time_demand",
            "stockout_risk_percent",
            "sales_at_risk",
            "priority_score"
        ]
        if col in reorder.columns
    ]

    st.dataframe(
        reorder[
            reorder_columns
        ],
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# OVERSTOCK PRIORITIES
# =========================================================

section_header(
    "📦 Overstock Priorities",
    "Products with inventory materially above expected demand."
)


overstock_actions = [
    "Markdown / Clear",
    "MARKDOWN / CLEAR",
    "STOP PURCHASES / REVIEW SKU",
    "REDUCE PURCHASES / PROMOTE STOCK"
]


overstock = (
    filtered_risk[
        filtered_risk["recommended_action"]
        .astype(str)
        .str.upper()
        .isin(
            [x.upper() for x in overstock_actions]
        )
    ]
    .sort_values(
        "capital_locked",
        ascending=False
    )
    .head(top_n)
)


if overstock.empty:

    st.success(
        "No major overstock priorities detected."
    )

else:

    overstock_columns = [
        col for col in [
            "sku_id",
            "product_name",
            "category",
            "forecast_confidence",
            "avg_weekly_demand",
            "inventory_position",
            "weeks_of_supply",
            "excess_units",
            "capital_locked",
            "priority_score"
        ]
        if col in overstock.columns
    ]

    st.dataframe(
        overstock[
            overstock_columns
        ],
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# CATEGORY RISK
# =========================================================

section_header(
    "🏷️ Category Risk Exposure",
    "Compare operational and financial risk across product categories."
)


category_risk = (
    filtered_risk
    .groupby(
        "category",
        as_index=False
    )
    .agg(
        SKUs=(
            "sku_id",
            "nunique"
        ),
        Sales_at_Risk=(
            "sales_at_risk",
            "sum"
        ),
        Capital_Locked=(
            "capital_locked",
            "sum"
        ),
        Stockout_Risk=(
            "stockout_risk_percent",
            "mean"
        )
    )
    .sort_values(
        "Sales_at_Risk",
        ascending=False
    )
)


st.dataframe(
    category_risk,
    use_container_width=True,
    hide_index=True
)


# =========================================================
# MANAGEMENT RECOMMENDATIONS
# =========================================================

section_header(
    "🧠 Management Recommendations",
    "Automated decision guidance based on the current risk portfolio."
)


total_sales_risk = (
    filtered_risk["sales_at_risk"]
    .sum()
)

total_capital_locked = (
    filtered_risk["capital_locked"]
    .sum()
)

critical_total = (
    filtered_risk["risk_severity"]
    .astype(str)
    .eq("Critical")
    .sum()
)

high_total = (
    filtered_risk["risk_severity"]
    .astype(str)
    .eq("High")
    .sum()
)


if critical_total > 0:

    st.error(
        f"🚨 **{critical_total} critical-risk SKU(s)** "
        "require immediate management review."
    )


if high_total > 0:

    st.warning(
        f"⚠️ **{high_total} high-risk SKU(s)** "
        "should be prioritized for operational action."
    )


if total_sales_risk > 0:

    st.info(
        f"💰 Estimated sales exposure is "
        f"**₹{total_sales_risk:,.0f}**. "
        "Review immediate replenishment priorities."
    )


if total_capital_locked > 0:

    st.info(
        f"📦 Approximately **₹{total_capital_locked:,.0f}** "
        "is estimated to be locked in excess inventory."
    )


if (
    critical_total == 0
    and high_total == 0
):

    st.success(
        "✅ No critical or high-risk products detected "
        "under the current filters."
    )


# =========================================================
# SKU DRILL-DOWN
# =========================================================

section_header(
    "🔍 SKU Risk Drill-Down",
    "Detailed risk profile for an individual product."
)


risk_sku_options = (
    filtered_risk["sku_id"]
    .dropna()
    .tolist()
)


def _format_sku_label(sku):
    """Build the selectbox label for a given SKU without breaking
    the f-string across multiple lines inside braces."""

    matches = filtered_risk.loc[
        filtered_risk["sku_id"] == sku,
        "product_name"
    ]

    product_name = matches.iloc[0] if not matches.empty else "Unknown"

    return f"{sku} — {product_name}"


selected_risk_sku = st.selectbox(
    "Select SKU",
    risk_sku_options,
    format_func=_format_sku_label
)


selected_row = filtered_risk[
    filtered_risk["sku_id"]
    == selected_risk_sku
].iloc[0]


d1, d2, d3, d4 = st.columns(4)


with d1:

    st.metric(
        "Risk Severity",
        str(
            selected_row["risk_severity"]
        )
    )


with d2:

    st.metric(
        "Forecast Confidence",
        selected_row.get(
            "forecast_confidence",
            "Unknown"
        )
    )


with d3:

    st.metric(
        "Stockout Risk",
        f"{selected_row['stockout_risk_percent']:.1f}%"
    )


with d4:

    st.metric(
        "Weeks of Supply",
        f"{selected_row['weeks_of_supply']:.1f}"
    )


# =========================================================
# SKU RISK PROFILE
# =========================================================

risk_profile = pd.DataFrame({

    "Metric": [

        "Average Weekly Demand",

        "Total Forecast Demand",

        "Inventory Position",

        "Lead-Time Demand",

        "Weeks of Supply",

        "Stockout Risk",

        "Sales at Risk",

        "Excess Units",

        "Capital Locked",

        "Priority Score",

        "Recommended Action"
    ],

    "Value": [

        f"{selected_row['avg_weekly_demand']:,.0f}",

        f"{selected_row.get('total_forecast_demand', 0):,.0f}",

        f"{selected_row['inventory_position']:,.0f}",

        f"{selected_row['lead_time_demand']:,.0f}",

        f"{selected_row['weeks_of_supply']:.1f}",

        f"{selected_row['stockout_risk_percent']:.1f}%",

        f"₹{selected_row['sales_at_risk']:,.0f}",

        f"{selected_row['excess_units']:,.0f}",

        f"₹{selected_row['capital_locked']:,.0f}",

        f"{selected_row['priority_score']:.1f}",

        selected_row["recommended_action"]
    ]
})


st.dataframe(
    risk_profile,
    use_container_width=True,
    hide_index=True
)


# =========================================================
# FORECAST TRAJECTORY FOR SELECTED SKU
# =========================================================

section_header(
    "🔮 Selected SKU Forecast",
    "Future demand trajectory used by the risk engine."
)


selected_sku_forecast = forecasts[
    forecasts["sku_id"]
    == selected_risk_sku
].copy()


if not selected_sku_forecast.empty:

    fig_selected_forecast = go.Figure()

    if "upper_bound" in selected_sku_forecast.columns:

        fig_selected_forecast.add_trace(
            go.Scatter(
                x=selected_sku_forecast["date"],
                y=selected_sku_forecast["upper_bound"],
                mode="lines",
                line=dict(width=0),
                name="Upper Bound"
            )
        )


    if "lower_bound" in selected_sku_forecast.columns:

        fig_selected_forecast.add_trace(
            go.Scatter(
                x=selected_sku_forecast["date"],
                y=selected_sku_forecast["lower_bound"],
                mode="lines",
                line=dict(width=0),
                fill="tonexty",
                name="Confidence Range"
            )
        )


    if "predicted_demand" in selected_sku_forecast.columns:

        fig_selected_forecast.add_trace(
            go.Scatter(
                x=selected_sku_forecast["date"],
                y=selected_sku_forecast["predicted_demand"],
                mode="lines+markers",
                name="Forecast Demand"
            )
        )


    fig_selected_forecast.update_layout(
        title=f"Forecast Trajectory — {selected_risk_sku}",
        xaxis_title="Week",
        yaxis_title="Units",
        height=450,
        hovermode="x unified"
    )

    st.plotly_chart(
        fig_selected_forecast,
        use_container_width=True
    )

else:

    st.info(
        "No forecast trajectory is available for the selected SKU."
    )


# =========================================================
# COMPLETE RISK SUMMARY
# =========================================================

section_header(
    "📑 Complete Risk Summary",
    "Management-ready SKU-level risk dataset."
)


risk_columns = [
    col for col in [
        "sku_id",
        "product_name",
        "category",
        "avg_weekly_demand",
        "total_forecast_demand",
        "forecast_confidence",
        "inventory_position",
        "lead_time_demand",
        "weeks_of_supply",
        "stockout_risk_percent",
        "overstock_risk",
        "risk_severity",
        "recommended_action",
        "priority_score",
        "sales_at_risk",
        "excess_units",
        "capital_locked"
    ]
    if col in filtered_risk.columns
]


complete_risk = filtered_risk[
    risk_columns
].copy()


complete_risk = complete_risk.sort_values(
    [
        "risk_severity",
        "priority_score"
    ],
    ascending=[
        True,
        False
    ]
)


st.dataframe(
    complete_risk.head(100),
    use_container_width=True,
    hide_index=True
)


# =========================================================
# METHODOLOGY
# =========================================================

with st.expander(
    "📘 Risk Methodology"
):

    st.markdown(
        """
        ### Forecast Demand

        Demand is generated using the centralized FORESIGHT
        forecasting engine.

        ### Inventory Position

        **On Hand + On Order**

        ### Lead-Time Demand

        **Average Weekly Demand × Lead Time / 7**

        ### Weeks of Supply

        **Inventory Position / Average Weekly Demand**

        ### Stockout Risk

        Estimates the percentage of lead-time demand that may
        not be covered by the current inventory position.

        ### Overstock Risk

        Evaluates whether inventory coverage is materially
        above expected demand.

        ### Risk Severity

        Products are classified as:

        - 🔴 Critical
        - 🟠 High
        - 🟡 Medium
        - 🟢 Low

        based on stockout exposure, inventory coverage and
        financial exposure.

        ### Financial Exposure

        **Sales at Risk** estimates potential sales exposure
        from insufficient inventory.

        **Capital Locked** estimates inventory value above the
        target stock level.

        ### Forecast Confidence

        Forecast confidence is used as an additional decision
        signal when available.
        """
    )


# =========================================================
# FOOTER
# =========================================================

show_footer()