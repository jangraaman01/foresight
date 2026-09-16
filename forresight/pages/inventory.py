from src.ui import (
    apply_foresight_style,
    show_sidebar_brand,
    page_header,
    section_header,
    show_footer
)
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

from src.forecast_engine import generate_forecast_summary


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Inventory Dashboard",
    page_icon="📦",
    layout="wide"
)
apply_foresight_style()
show_sidebar_brand()

# ============================================================
# PAGE TITLE
# ============================================================

page_header(
    "📦 Inventory Dashboard",
    "Monitor inventory position, supply coverage and replenishment requirements."
)

st.markdown(
    """
    Monitor inventory availability, stock coverage, reorder
    requirements, excess stock, and SKU-level inventory risk.
    """
)


# ============================================================
# LOAD DATA
# ============================================================

sales = load_sales()
inventory = load_inventory()
sku_master = load_sku_master()


# ============================================================
# VALIDATION
# ============================================================

if sales.empty:
    st.error("Sales data could not be loaded.")
    st.stop()

if inventory.empty:
    st.error("Inventory data could not be loaded.")
    st.stop()


# ============================================================
# COPY DATA
# ============================================================

sales = sales.copy()
inventory = inventory.copy()
sku_master = sku_master.copy()


# ============================================================
# CLEAN SALES DATA
# ============================================================

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


# ============================================================
# CLEAN INVENTORY DATA
# ============================================================

inventory["date"] = pd.to_datetime(
    inventory["date"],
    errors="coerce"
)

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
# INVENTORY SETTINGS
# ============================================================

st.subheader("⚙️ Inventory Analysis Settings")

setting_col1, setting_col2, setting_col3 = st.columns(3)


with setting_col1:

    forecast_horizon = st.slider(
        "Forecast Horizon (Weeks)",
        min_value=1,
        max_value=16,
        value=8
    )


with setting_col2:

    target_weeks = st.slider(
        "Target Weeks of Supply",
        min_value=1,
        max_value=16,
        value=8
    )


with setting_col3:

    risk_threshold = st.slider(
        "Low Stock Threshold (Weeks)",
        min_value=1,
        max_value=12,
        value=4
    )


# ============================================================
# LATEST INVENTORY SNAPSHOT
# ============================================================

latest_date = inventory["date"].max()

latest_inventory = inventory[
    inventory["date"] == latest_date
].copy()


# ============================================================
# FORECAST SUMMARY
# ============================================================

forecast_summary = generate_forecast_summary(
    sales,
    horizon=forecast_horizon
)


if forecast_summary.empty:

    st.warning(
        "Forecast information could not be generated."
    )

    forecast_summary = pd.DataFrame(
        columns=[
            "sku_id",
            "avg_weekly_demand"
        ]
    )


if "avg_weekly_demand" not in forecast_summary.columns:

    forecast_summary["avg_weekly_demand"] = 0


forecast_summary["avg_weekly_demand"] = (
    pd.to_numeric(
        forecast_summary["avg_weekly_demand"],
        errors="coerce"
    )
    .fillna(0)
)


# ============================================================
# MERGE INVENTORY + FORECAST
# ============================================================

inventory_data = latest_inventory.merge(
    forecast_summary,
    on="sku_id",
    how="left"
)


inventory_data["avg_weekly_demand"] = (
    inventory_data["avg_weekly_demand"]
    .fillna(0)
)


# ============================================================
# PRODUCT INFORMATION
# ============================================================

if (
    not sku_master.empty
    and "sku_id" in sku_master.columns
):

    product_columns = ["sku_id"]

    for column in [
        "product_name",
        "sku_name",
        "category",
        "brand"
    ]:

        if column in sku_master.columns:

            product_columns.append(column)


    product_information = (
        sku_master[
            list(dict.fromkeys(product_columns))
        ]
        .drop_duplicates("sku_id")
    )


    inventory_data = inventory_data.merge(
        product_information,
        on="sku_id",
        how="left"
    )


# ============================================================
# INVENTORY POSITION
# ============================================================

inventory_data["inventory_position"] = (
    inventory_data["on_hand_units"]
    + inventory_data["on_order_units"]
)


# ============================================================
# WEEKS OF SUPPLY
# ============================================================

inventory_data["weeks_of_supply"] = np.where(
    inventory_data["avg_weekly_demand"] > 0,
    inventory_data["inventory_position"]
    / inventory_data["avg_weekly_demand"],
    np.inf
)


# ============================================================
# LEAD-TIME DEMAND
# ============================================================

inventory_data["lead_time_demand"] = (
    inventory_data["avg_weekly_demand"]
    * inventory_data["lead_time_days"]
    / 7
)


# ============================================================
# STOCKOUT UNITS
# ============================================================

inventory_data["stockout_units"] = (
    inventory_data["lead_time_demand"]
    - inventory_data["inventory_position"]
).clip(lower=0)


# ============================================================
# TARGET INVENTORY
# ============================================================

inventory_data["target_inventory"] = (
    inventory_data["avg_weekly_demand"]
    * target_weeks
)


# ============================================================
# EXCESS INVENTORY
# ============================================================

inventory_data["excess_units"] = (
    inventory_data["inventory_position"]
    - inventory_data["target_inventory"]
).clip(lower=0)


# ============================================================
# INVENTORY STATUS
# ============================================================

inventory_data["inventory_status"] = np.select(
    [
        inventory_data["stockout_units"] > 0,

        (
            inventory_data["weeks_of_supply"]
            < risk_threshold
        ),

        (
            inventory_data["weeks_of_supply"]
            > target_weeks * 1.5
        )
    ],
    [
        "Critical Stockout Risk",
        "Low Stock",
        "Excess Inventory"
    ],
    default="Healthy"
)


# ============================================================
# REORDER REQUIREMENT
# ============================================================

inventory_data["reorder_requirement"] = (
    inventory_data["target_inventory"]
    - inventory_data["inventory_position"]
).clip(lower=0)


# ============================================================
# FILTERS
# ============================================================

st.divider()

st.subheader("🔎 Inventory Filters")

filter_col1, filter_col2, filter_col3 = st.columns(3)


# ============================================================
# CATEGORY FILTER
# ============================================================

with filter_col1:

    if "category" in inventory_data.columns:

        category_options = sorted(
            inventory_data["category"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        selected_categories = st.multiselect(
            "Category",
            options=category_options,
            default=[]
        )

    else:

        selected_categories = []


# ============================================================
# STATUS FILTER
# ============================================================

with filter_col2:

    status_options = [
        "All",
        "Critical Stockout Risk",
        "Low Stock",
        "Excess Inventory",
        "Healthy"
    ]

    selected_status = st.selectbox(
        "Inventory Status",
        options=status_options
    )


# ============================================================
# SKU FILTER
# ============================================================

with filter_col3:

    sku_options = sorted(
        inventory_data["sku_id"]
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

filtered_inventory = inventory_data.copy()


if selected_categories:

    filtered_inventory = filtered_inventory[
        filtered_inventory["category"]
        .astype(str)
        .isin(selected_categories)
    ]


if selected_status != "All":

    filtered_inventory = filtered_inventory[
        filtered_inventory["inventory_status"]
        == selected_status
    ]


if selected_skus:

    filtered_inventory = filtered_inventory[
        filtered_inventory["sku_id"]
        .astype(str)
        .isin(selected_skus)
    ]


# ============================================================
# EMPTY DATA CHECK
# ============================================================

if filtered_inventory.empty:

    st.warning(
        "No inventory data matches the selected filters."
    )

    st.stop()


st.caption(
    f"Showing {len(filtered_inventory):,} SKUs "
    f"out of {len(inventory_data):,} total SKUs."
)


# ============================================================
# KPI CALCULATIONS
# ============================================================

total_on_hand = (
    filtered_inventory["on_hand_units"].sum()
)

total_on_order = (
    filtered_inventory["on_order_units"].sum()
)

total_inventory_position = (
    filtered_inventory["inventory_position"].sum()
)

total_excess = (
    filtered_inventory["excess_units"].sum()
)

total_reorder = (
    filtered_inventory["reorder_requirement"].sum()
)

stockout_skus = (
    filtered_inventory["stockout_units"] > 0
).sum()

low_stock_skus = (
    filtered_inventory["inventory_status"]
    == "Low Stock"
).sum()

excess_skus = (
    filtered_inventory["inventory_status"]
    == "Excess Inventory"
).sum()


# ============================================================
# KPI DASHBOARD
# ============================================================

st.divider()

st.subheader("📊 Inventory Overview")


kpi1, kpi2, kpi3, kpi4 = st.columns(4)


with kpi1:

    st.metric(
        "On-Hand Units",
        f"{total_on_hand:,.0f}"
    )


with kpi2:

    st.metric(
        "On-Order Units",
        f"{total_on_order:,.0f}"
    )


with kpi3:

    st.metric(
        "Inventory Position",
        f"{total_inventory_position:,.0f}"
    )


with kpi4:

    st.metric(
        "SKUs at Stockout Risk",
        f"{stockout_skus:,}"
    )


# ============================================================
# SECONDARY KPIs
# ============================================================

kpi5, kpi6, kpi7, kpi8 = st.columns(4)


with kpi5:

    st.metric(
        "Low Stock SKUs",
        f"{low_stock_skus:,}"
    )


with kpi6:

    st.metric(
        "Excess Stock SKUs",
        f"{excess_skus:,}"
    )


with kpi7:

    st.metric(
        "Excess Units",
        f"{total_excess:,.0f}"
    )


with kpi8:

    st.metric(
        "Reorder Requirement",
        f"{total_reorder:,.0f}"
    )


# ============================================================
# INVENTORY STATUS DISTRIBUTION
# ============================================================

st.divider()

st.subheader("🚦 Inventory Health")


status_distribution = (
    filtered_inventory[
        "inventory_status"
    ]
    .value_counts()
    .reset_index()
)

status_distribution.columns = [
    "Status",
    "SKU_Count"
]


fig_status = px.bar(
    status_distribution,
    x="Status",
    y="SKU_Count",
    text="SKU_Count",
    title="Inventory Status Distribution",
    template="plotly_dark"
)


fig_status.update_traces(
    textposition="outside"
)


st.plotly_chart(
    fig_status,
    use_container_width=True
)


# ============================================================
# INVENTORY POSITION BREAKDOWN
# ============================================================

st.subheader("📦 Inventory Position Breakdown")


position_data = pd.DataFrame(
    {
        "Inventory Component": [
            "On-Hand",
            "On-Order"
        ],
        "Units": [
            total_on_hand,
            total_on_order
        ]
    }
)


fig_position = px.bar(
    position_data,
    x="Inventory Component",
    y="Units",
    text="Units",
    title="Current Inventory Position",
    template="plotly_dark"
)


fig_position.update_traces(
    textposition="outside"
)


st.plotly_chart(
    fig_position,
    use_container_width=True
)


# ============================================================
# WEEKS OF SUPPLY DISTRIBUTION
# ============================================================

st.divider()

st.subheader("📅 Weeks of Supply")


weeks_data = filtered_inventory.copy()

weeks_data["weeks_of_supply_plot"] = (
    weeks_data["weeks_of_supply"]
    .replace(
        [np.inf, -np.inf],
        np.nan
    )
    .dropna()
)


if not weeks_data["weeks_of_supply_plot"].dropna().empty:

    fig_wos = px.histogram(
        weeks_data,
        x="weeks_of_supply_plot",
        nbins=20,
        title="Distribution of Weeks of Supply",
        labels={
            "weeks_of_supply_plot":
            "Weeks of Supply"
        },
        template="plotly_dark"
    )


    st.plotly_chart(
        fig_wos,
        use_container_width=True
    )

else:

    st.info(
        "Weeks of supply cannot be calculated for the "
        "selected inventory records."
    )


# ============================================================
# STOCKOUT RISK TABLE
# ============================================================

st.divider()

st.subheader("🚨 Stockout Risk")


stockout_table = (
    filtered_inventory[
        filtered_inventory["stockout_units"] > 0
    ]
    .sort_values(
        "stockout_units",
        ascending=False
    )
)


if stockout_table.empty:

    st.success(
        "✅ No stockout risk detected for the "
        "selected inventory."
    )

else:

    stockout_columns = [
        "sku_id",
        "on_hand_units",
        "on_order_units",
        "inventory_position",
        "avg_weekly_demand",
        "lead_time_days",
        "lead_time_demand",
        "stockout_units",
        "weeks_of_supply"
    ]


    if "category" in stockout_table.columns:

        stockout_columns.insert(
            1,
            "category"
        )


    stockout_columns = [
        column
        for column in stockout_columns
        if column in stockout_table.columns
    ]


    st.dataframe(
        stockout_table[
            stockout_columns
        ],
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# EXCESS INVENTORY TABLE
# ============================================================

st.subheader("📦 Excess Inventory")


excess_table = (
    filtered_inventory[
        filtered_inventory["excess_units"] > 0
    ]
    .sort_values(
        "excess_units",
        ascending=False
    )
)


if excess_table.empty:

    st.success(
        "✅ No excess inventory detected."
    )

else:

    excess_columns = [
        "sku_id",
        "on_hand_units",
        "on_order_units",
        "inventory_position",
        "avg_weekly_demand",
        "target_inventory",
        "excess_units",
        "weeks_of_supply"
    ]


    if "category" in excess_table.columns:

        excess_columns.insert(
            1,
            "category"
        )


    excess_columns = [
        column
        for column in excess_columns
        if column in excess_table.columns
    ]


    st.dataframe(
        excess_table[
            excess_columns
        ],
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# REORDER REQUIREMENT
# ============================================================

st.divider()

st.subheader("🔄 Reorder Requirements")


reorder_table = (
    filtered_inventory[
        filtered_inventory["reorder_requirement"] > 0
    ]
    .sort_values(
        "reorder_requirement",
        ascending=False
    )
)


if reorder_table.empty:

    st.success(
        "✅ No additional reorder requirement "
        "is currently identified."
    )

else:

    reorder_columns = [
        "sku_id",
        "inventory_position",
        "avg_weekly_demand",
        "target_inventory",
        "reorder_requirement",
        "weeks_of_supply"
    ]


    if "category" in reorder_table.columns:

        reorder_columns.insert(
            1,
            "category"
        )


    reorder_columns = [
        column
        for column in reorder_columns
        if column in reorder_table.columns
    ]


    st.dataframe(
        reorder_table[
            reorder_columns
        ],
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# INVENTORY VS DEMAND
# ============================================================

st.divider()

st.subheader("⚖️ Inventory vs Demand")


scatter_data = filtered_inventory.copy()


fig_scatter = px.scatter(
    scatter_data,
    x="avg_weekly_demand",
    y="inventory_position",
    size="inventory_position",
    hover_name="sku_id",
    color="inventory_status",
    title="Inventory Position vs Weekly Demand",
    labels={
        "avg_weekly_demand": "Average Weekly Demand",
        "inventory_position": "Inventory Position",
        "inventory_status": "Status"
    },
    template="plotly_dark"
)


st.plotly_chart(
    fig_scatter,
    use_container_width=True
)


# ============================================================
# TOP INVENTORY HOLDING SKUs
# ============================================================

st.subheader("🏦 Highest Inventory Holding SKUs")


top_inventory = (
    filtered_inventory[
        [
            "sku_id",
            "inventory_position"
        ]
    ]
    .sort_values(
        "inventory_position",
        ascending=False
    )
    .head(15)
)


fig_top_inventory = px.bar(
    top_inventory,
    x="sku_id",
    y="inventory_position",
    text="inventory_position",
    title="Top SKUs by Inventory Position",
    labels={
        "sku_id": "SKU",
        "inventory_position": "Inventory Units"
    },
    template="plotly_dark"
)


fig_top_inventory.update_traces(
    textposition="outside"
)


st.plotly_chart(
    fig_top_inventory,
    use_container_width=True
)


# ============================================================
# SKU INVENTORY DRILL-DOWN
# ============================================================

st.divider()

st.header("🔍 SKU Inventory Drill-Down")


drilldown_skus = sorted(
    filtered_inventory["sku_id"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)


selected_sku = st.selectbox(
    "Select SKU",
    options=drilldown_skus,
    key="inventory_dashboard_sku"
)


selected_rows = filtered_inventory[
    filtered_inventory["sku_id"]
    .astype(str)
    == selected_sku
]


if not selected_rows.empty:

    selected = selected_rows.iloc[0]


    # --------------------------------------------------------
    # SKU INFORMATION
    # --------------------------------------------------------

    product_name = selected_sku

    if "product_name" in selected.index:

        if pd.notna(selected["product_name"]):

            product_name = str(
                selected["product_name"]
            )

    elif "sku_name" in selected.index:

        if pd.notna(selected["sku_name"]):

            product_name = str(
                selected["sku_name"]
            )


    st.subheader(
        f"📦 {product_name}"
    )


    # --------------------------------------------------------
    # SKU KPIs
    # --------------------------------------------------------

    sku_col1, sku_col2, sku_col3, sku_col4 = (
        st.columns(4)
    )


    with sku_col1:

        st.metric(
            "On-Hand",
            f"{selected['on_hand_units']:,.0f}"
        )


    with sku_col2:

        st.metric(
            "On-Order",
            f"{selected['on_order_units']:,.0f}"
        )


    with sku_col3:

        st.metric(
            "Weekly Demand",
            f"{selected['avg_weekly_demand']:,.1f}"
        )


    with sku_col4:

        if np.isfinite(
            selected["weeks_of_supply"]
        ):

            wos_display = (
                f"{selected['weeks_of_supply']:.1f} weeks"
            )

        else:

            wos_display = "N/A"


        st.metric(
            "Weeks of Supply",
            wos_display
        )


    # --------------------------------------------------------
    # SKU STATUS
    # --------------------------------------------------------

    if (
        selected["inventory_status"]
        == "Critical Stockout Risk"
    ):

        st.error(
            "🚨 Critical Stockout Risk"
        )

    elif (
        selected["inventory_status"]
        == "Low Stock"
    ):

        st.warning(
            "⚠️ Low Stock"
        )

    elif (
        selected["inventory_status"]
        == "Excess Inventory"
    ):

        st.warning(
            "📦 Excess Inventory"
        )

    else:

        st.success(
            "✅ Healthy Inventory"
        )


    # --------------------------------------------------------
    # SKU DETAIL TABLE
    # --------------------------------------------------------

    sku_detail_columns = [
        "sku_id",
        "on_hand_units",
        "on_order_units",
        "inventory_position",
        "avg_weekly_demand",
        "lead_time_days",
        "lead_time_demand",
        "target_inventory",
        "weeks_of_supply",
        "stockout_units",
        "excess_units",
        "reorder_requirement",
        "inventory_status"
    ]


    if "category" in selected.index:

        sku_detail_columns.insert(
            1,
            "category"
        )


    sku_detail_columns = [
        column
        for column in sku_detail_columns
        if column in selected.index
    ]


    sku_detail = pd.DataFrame(
        [selected[sku_detail_columns]]
    )


    st.dataframe(
        sku_detail,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# MANAGEMENT INSIGHTS
# ============================================================

st.divider()

st.header("🧠 Inventory Management Insights")


if stockout_skus > 0:

    st.error(
        f"""
        🚨 **Immediate Attention Required**

        {stockout_skus:,} SKU(s) currently show
        potential stockout risk based on forecast demand
        and supplier lead time.

        Review purchase orders, supplier lead times,
        and inventory allocation.
        """
    )


if low_stock_skus > 0:

    st.warning(
        f"""
        ⚠️ **Low Stock Alert**

        {low_stock_skus:,} SKU(s) have inventory coverage
        below the configured threshold of
        {risk_threshold} weeks.
        """
    )


if excess_skus > 0:

    st.warning(
        f"""
        📦 **Excess Inventory Alert**

        {excess_skus:,} SKU(s) are carrying inventory
        above the target level.

        Total estimated excess units:
        **{total_excess:,.0f}**
        """
    )


if (
    stockout_skus == 0
    and low_stock_skus == 0
    and excess_skus == 0
):

    st.success(
        """
        ✅ **Inventory Portfolio Appears Healthy**

        No significant stockout, low-stock, or excess
        inventory issues were detected under the current
        assumptions.
        """
    )


# ============================================================
# INVENTORY SUMMARY TABLE
# ============================================================

st.divider()

st.subheader("📋 Complete Inventory Summary")


summary_columns = [
    "sku_id",
    "on_hand_units",
    "on_order_units",
    "inventory_position",
    "avg_weekly_demand",
    "lead_time_days",
    "lead_time_demand",
    "target_inventory",
    "weeks_of_supply",
    "stockout_units",
    "excess_units",
    "reorder_requirement",
    "inventory_status"
]


if "category" in filtered_inventory.columns:

    summary_columns.insert(
        1,
        "category"
    )


summary_columns = [
    column
    for column in summary_columns
    if column in filtered_inventory.columns
]


st.dataframe(
    filtered_inventory[
        summary_columns
    ].sort_values(
        "inventory_position",
        ascending=False
    ),
    use_container_width=True,
    hide_index=True
)


# ============================================================
# METHODOLOGY
# ============================================================

st.divider()

with st.expander(
    "📘 Inventory Dashboard Methodology"
):

    st.markdown(
        f"""
### Inventory Position

Inventory Position is calculated as:

**On-Hand Units + On-Order Units**

### Weeks of Supply

Weeks of Supply is calculated as:

**Inventory Position ÷ Average Weekly Demand**

### Lead-Time Demand

Lead-Time Demand is:

**Average Weekly Demand × Lead Time Days ÷ 7**

### Stockout Risk

A potential stockout is identified when:

**Lead-Time Demand > Inventory Position**

### Target Inventory

Target inventory is calculated using:

**Average Weekly Demand × {target_weeks} weeks**

### Excess Inventory

Inventory above the target level is classified as excess.

### Reorder Requirement

The dashboard estimates additional inventory required
to reach the configured target inventory level.

### Forecast

The centralized FORESIGHT forecasting engine uses a
forecast horizon of **{forecast_horizon} weeks**.

### Low Stock Threshold

SKUs with less than **{risk_threshold} weeks**
of inventory coverage are classified as low stock.

These indicators support inventory planning,
replenishment decisions, and working-capital management.
"""
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "FORESIGHT • AI-Driven Demand Forecasting, "
    "Inventory Risk & Supply Chain Intelligence"
)
# ============================================================
# FOOTER
# ============================================================

show_footer()