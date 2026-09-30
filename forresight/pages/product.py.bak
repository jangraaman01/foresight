import streamlit as st
import pandas as pd
import numpy as np
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
    recommendation_card,
    show_footer
)


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="FORESIGHT | Product Details",
    page_icon="📦",
    layout="wide"
)

apply_foresight_style()
show_sidebar_brand()


# =========================================================
# PAGE HEADER
# =========================================================

page_header(
    "📦 Product Details",
    "360° SKU-level intelligence combining demand, forecast, inventory, risk and financial exposure."
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

inventory = inventory.dropna(
    subset=["date", "sku_id"]
)


# =========================================================
# SIDEBAR SETTINGS
# =========================================================

st.sidebar.markdown(
    "### ⚙️ Product Settings"
)

forecast_horizon = st.sidebar.slider(
    "Forecast Horizon (Weeks)",
    min_value=1,
    max_value=16,
    value=8
)


# =========================================================
# SKU MASTER
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
        "sku_id": sales["sku_id"].unique()
    })

    product_info["product_name"] = (
        product_info["sku_id"]
        .astype(str)
    )

    product_info["category"] = "Unknown"

    product_info["subcategory"] = "Unknown"


# =========================================================
# SKU SELECTOR
# =========================================================

sku_options = (
    product_info["sku_id"]
    .dropna()
    .unique()
    .tolist()
)


if not sku_options:

    st.warning("No SKUs are available.")
    st.stop()


def sku_label(sku):

    row = product_info[
        product_info["sku_id"] == sku
    ]

    if row.empty:
        return str(sku)

    product_name = row.iloc[0].get(
        "product_name",
        ""
    )

    return (
        f"{sku} — {product_name}"
        if pd.notna(product_name)
        else str(sku)
    )


selected_sku = st.selectbox(
    "Select Product / SKU",
    sku_options,
    format_func=sku_label
)


# =========================================================
# GENERATE CENTRALIZED FORECAST
# =========================================================

with st.spinner(
    "Loading product intelligence..."
):

    all_forecasts = generate_all_forecasts(
        sales,
        horizon=forecast_horizon
    )

    forecast_summary = generate_forecast_summary(
        sales,
        horizon=forecast_horizon
    )


selected_forecast = all_forecasts[
    all_forecasts["sku_id"] == selected_sku
].copy()


selected_summary = forecast_summary[
    forecast_summary["sku_id"] == selected_sku
].copy()


if selected_forecast.empty:

    st.warning(
        "No forecast is available for this SKU."
    )


# =========================================================
# PRODUCT INFORMATION
# =========================================================

product_row = product_info[
    product_info["sku_id"] == selected_sku
]

if product_row.empty:

    product_name = str(selected_sku)
    category = "Unknown"
    subcategory = "Unknown"

else:

    product_row = product_row.iloc[0]

    product_name = product_row.get(
        "product_name",
        selected_sku
    )

    category = product_row.get(
        "category",
        "Unknown"
    )

    subcategory = product_row.get(
        "subcategory",
        "Unknown"
    )


# =========================================================
# LATEST INVENTORY
# =========================================================

sku_inventory = inventory[
    inventory["sku_id"] == selected_sku
].copy()


if sku_inventory.empty:

    st.warning(
        "No inventory information is available for this SKU."
    )

    latest_inventory = pd.Series(dtype=float)

else:

    latest_inventory = (
        sku_inventory
        .sort_values("date")
        .iloc[-1]
    )


on_hand = float(
    latest_inventory.get(
        "on_hand_units",
        0
    )
)

on_order = float(
    latest_inventory.get(
        "on_order_units",
        0
    )
)

lead_time_days = float(
    latest_inventory.get(
        "lead_time_days",
        0
    )
)

reorder_point = float(
    latest_inventory.get(
        "reorder_point",
        0
    )
)

inventory_position = (
    on_hand + on_order
)


# =========================================================
# FORECAST METRICS
# =========================================================

if selected_summary.empty:

    avg_weekly_demand = 0
    total_forecast_demand = 0
    forecast_confidence = "Low"
    demand_trend = "Stable"
    min_forecast = 0
    max_forecast = 0
    avg_lower = 0
    avg_upper = 0

else:

    selected_summary = selected_summary.iloc[0]

    avg_weekly_demand = float(
        selected_summary.get(
            "avg_weekly_demand",
            0
        )
    )

    total_forecast_demand = float(
        selected_summary.get(
            "total_forecast_demand",
            0
        )
    )

    forecast_confidence = (
        selected_summary.get(
            "forecast_confidence",
            "Low"
        )
    )

    demand_trend = (
        selected_summary.get(
            "demand_trend",
            "Stable"
        )
    )

    min_forecast = float(
        selected_summary.get(
            "min_forecast_demand",
            0
        )
    )

    max_forecast = float(
        selected_summary.get(
            "max_forecast_demand",
            0
        )
    )

    avg_lower = float(
        selected_summary.get(
            "avg_lower_bound",
            0
        )
    )

    avg_upper = float(
        selected_summary.get(
            "avg_upper_bound",
            0
        )
    )


# =========================================================
# INVENTORY RISK
# =========================================================

if avg_weekly_demand > 0:

    lead_time_demand = (
        avg_weekly_demand
        * lead_time_days
        / 7
    )

    weeks_of_supply = (
        inventory_position
        / avg_weekly_demand
    )

else:

    lead_time_demand = 0
    weeks_of_supply = 0


if lead_time_demand > 0:

    stockout_risk_percent = (
        max(
            0,
            (
                1
                -
                inventory_position
                / lead_time_demand
            )
        )
        * 100
    )

else:

    stockout_risk_percent = 0


stockout_risk = classify_stockout_risk(
    stockout_risk_percent
)

overstock_risk = classify_overstock_risk(
    weeks_of_supply
)

recommended_action = calculate_action(
    stockout_risk_percent,
    weeks_of_supply
)

priority_score = calculate_priority_score(
    stockout_risk_percent,
    weeks_of_supply
)


# =========================================================
# RISK SEVERITY
# =========================================================

if (
    stockout_risk_percent >= 90
    and weeks_of_supply >= 12
):

    risk_severity = "Critical"

elif (
    stockout_risk_percent >= 90
    or weeks_of_supply >= 12
):

    risk_severity = "High"

elif (
    stockout_risk_percent >= 70
    or weeks_of_supply >= 8
):

    risk_severity = "Medium"

else:

    risk_severity = "Low"


# =========================================================
# FINANCIAL METRICS
# =========================================================

unit_cost = 0
list_price = 0

if not product_row.empty:

    if "unit_cost" in product_row.index:

        unit_cost = pd.to_numeric(
            product_row.get(
                "unit_cost",
                0
            ),
            errors="coerce"
        )

        if pd.isna(unit_cost):
            unit_cost = 0

    if "list_price" in product_row.index:

        list_price = pd.to_numeric(
            product_row.get(
                "list_price",
                0
            ),
            errors="coerce"
        )

        if pd.isna(list_price):
            list_price = 0


# Recent selling price
recent_cutoff = (
    sales["date"].max()
    - pd.Timedelta(days=56)
)

recent_sales = sales[
    (
        sales["sku_id"] == selected_sku
    )
    &
    (
        sales["date"] >= recent_cutoff
    )
].copy()


selling_price = 0

if "revenue" in recent_sales.columns:

    recent_sales["revenue"] = pd.to_numeric(
        recent_sales["revenue"],
        errors="coerce"
    ).fillna(0)

    total_units = (
        recent_sales["units_sold"].sum()
    )

    total_revenue = (
        recent_sales["revenue"].sum()
    )

    if total_units > 0:

        selling_price = (
            total_revenue
            / total_units
        )

if selling_price <= 0:

    selling_price = list_price


# =========================================================
# BUSINESS IMPACT
# =========================================================

stockout_units_at_risk = max(
    lead_time_demand
    - inventory_position,
    0
)

sales_at_risk = (
    stockout_units_at_risk
    * selling_price
)

target_weeks = 8

target_inventory = (
    avg_weekly_demand
    * target_weeks
)

excess_units = max(
    inventory_position
    - target_inventory,
    0
)

capital_locked = (
    excess_units
    * unit_cost
)


# =========================================================
# PRODUCT HEADER
# =========================================================

section_header(
    "📌 Product Overview",
    "Current commercial and operational status of the selected SKU."
)


header_col1, header_col2 = st.columns(
    [3, 1]
)

with header_col1:

    st.markdown(
        f"""
        ## {product_name}

        **SKU:** `{selected_sku}`

        **Category:** {category}  
        **Subcategory:** {subcategory}
        """
    )

with header_col2:

    st.metric(
        "Risk Severity",
        risk_severity
    )


# =========================================================
# ACTION BANNER
# =========================================================

if risk_severity == "Critical":

    st.error(
        f"🚨 **Critical Risk:** {recommended_action}"
    )

elif risk_severity == "High":

    st.warning(
        f"⚠️ **High Risk:** {recommended_action}"
    )

elif risk_severity == "Medium":

    st.info(
        f"🔎 **Medium Risk:** {recommended_action}"
    )

else:

    st.success(
        f"✅ **Healthy:** {recommended_action}"
    )


# =========================================================
# CORE KPIs
# =========================================================

section_header(
    "📊 Product Intelligence",
    "Key demand, inventory and risk indicators."
)


kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)


with kpi1:

    st.metric(
        "Avg Weekly Demand",
        f"{avg_weekly_demand:,.0f}"
    )


with kpi2:

    st.metric(
        "Forecast Demand",
        f"{total_forecast_demand:,.0f}"
    )


with kpi3:

    st.metric(
        "Inventory Position",
        f"{inventory_position:,.0f}"
    )


with kpi4:

    st.metric(
        "Weeks of Supply",
        f"{weeks_of_supply:.1f}"
    )


with kpi5:

    st.metric(
        "Priority Score",
        f"{priority_score:.1f}"
    )


# =========================================================
# FORECAST KPIs
# =========================================================

section_header(
    "🔮 Forecast Intelligence",
    "AI forecast characteristics for the selected SKU."
)


f1, f2, f3, f4 = st.columns(4)


with f1:

    st.metric(
        "Demand Trend",
        demand_trend
    )


with f2:

    st.metric(
        "Forecast Confidence",
        forecast_confidence
    )


with f3:

    st.metric(
        "Forecast Min",
        f"{min_forecast:,.0f}"
    )


with f4:

    st.metric(
        "Forecast Max",
        f"{max_forecast:,.0f}"
    )


# =========================================================
# HISTORICAL SALES
# =========================================================

section_header(
    "📈 Historical Demand",
    "Weekly sales performance for the selected SKU."
)


sku_sales = sales[
    sales["sku_id"] == selected_sku
].copy()


weekly_sales = (
    sku_sales
    .set_index("date")
    .resample("W")["units_sold"]
    .sum()
    .reset_index()
)


fig_history = go.Figure()

fig_history.add_trace(
    go.Scatter(
        x=weekly_sales["date"],
        y=weekly_sales["units_sold"],
        mode="lines+markers",
        name="Weekly Sales"
    )
)


fig_history.update_layout(
    title="Historical Weekly Demand",
    xaxis_title="Week",
    yaxis_title="Units Sold",
    height=420,
    hovermode="x unified"
)

st.plotly_chart(
    fig_history,
    use_container_width=True
)


# =========================================================
# WEEK-BY-WEEK FORECAST
# =========================================================

section_header(
    "🔮 Week-by-Week Demand Forecast",
    "Future demand trajectory generated by the centralized FORESIGHT forecast engine."
)


if not selected_forecast.empty:

    fig_forecast = go.Figure()

    # Upper confidence boundary
    fig_forecast.add_trace(
        go.Scatter(
            x=selected_forecast["date"],
            y=selected_forecast["upper_bound"],
            mode="lines",
            line=dict(width=0),
            name="Upper Bound"
        )
    )

    # Lower boundary + filled confidence region
    fig_forecast.add_trace(
        go.Scatter(
            x=selected_forecast["date"],
            y=selected_forecast["lower_bound"],
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            name="Confidence Range"
        )
    )

    # Forecast
    fig_forecast.add_trace(
        go.Scatter(
            x=selected_forecast["date"],
            y=selected_forecast["predicted_demand"],
            mode="lines+markers",
            name="Forecast"
        )
    )

    fig_forecast.update_layout(
        title=f"Future Demand — {selected_sku}",
        xaxis_title="Forecast Week",
        yaxis_title="Units",
        height=500,
        hovermode="x unified"
    )

    st.plotly_chart(
        fig_forecast,
        use_container_width=True
    )

else:

    st.info(
        "No future forecast is available for this product."
    )


# =========================================================
# FORECAST TABLE
# =========================================================

if not selected_forecast.empty:

    section_header(
        "📅 Forecast Schedule",
        "Detailed weekly demand prediction and uncertainty range."
    )

    forecast_table = selected_forecast[
        [
            "date",
            "predicted_demand",
            "lower_bound",
            "upper_bound"
        ]
    ].copy()

    forecast_table.columns = [
        "Forecast Week",
        "Predicted Demand",
        "Lower Bound",
        "Upper Bound"
    ]

    forecast_table["Forecast Week"] = (
        pd.to_datetime(
            forecast_table["Forecast Week"]
        )
        .dt.strftime("%d %b %Y")
    )

    for column in [
        "Predicted Demand",
        "Lower Bound",
        "Upper Bound"
    ]:

        forecast_table[column] = (
            forecast_table[column]
            .round(0)
            .astype(int)
        )

    st.dataframe(
        forecast_table,
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# INVENTORY HISTORY
# =========================================================

section_header(
    "📦 Inventory History",
    "Historical on-hand and on-order inventory position."
)


inventory_history = sku_inventory.sort_values(
    "date"
).copy()


if not inventory_history.empty:

    fig_inventory = go.Figure()

    fig_inventory.add_trace(
        go.Scatter(
            x=inventory_history["date"],
            y=inventory_history["on_hand_units"],
            mode="lines+markers",
            name="On Hand"
        )
    )

    if "on_order_units" in inventory_history.columns:

        fig_inventory.add_trace(
            go.Scatter(
                x=inventory_history["date"],
                y=inventory_history["on_order_units"],
                mode="lines+markers",
                name="On Order"
            )
        )

    fig_inventory.update_layout(
        title="Inventory Position Over Time",
        xaxis_title="Date",
        yaxis_title="Units",
        height=420,
        hovermode="x unified"
    )

    st.plotly_chart(
        fig_inventory,
        use_container_width=True
    )

else:

    st.info(
        "No inventory history is available."
    )


# =========================================================
# SUPPLY VS DEMAND
# =========================================================

section_header(
    "⚖️ Supply vs Demand",
    "Comparison between available inventory and expected demand."
)


supply_demand = pd.DataFrame({
    "Metric": [
        "Inventory Position",
        "Lead-Time Demand",
        "Forecast Horizon Demand"
    ],
    "Units": [
        inventory_position,
        lead_time_demand,
        total_forecast_demand
    ]
})


fig_supply = go.Figure()

fig_supply.add_trace(
    go.Bar(
        x=supply_demand["Metric"],
        y=supply_demand["Units"],
        text=supply_demand["Units"].round(0),
        textposition="auto"
    )
)

fig_supply.update_layout(
    title="Supply vs Expected Demand",
    yaxis_title="Units",
    height=420
)

st.plotly_chart(
    fig_supply,
    use_container_width=True
)


# =========================================================
# RISK & FINANCIAL EXPOSURE
# =========================================================

section_header(
    "⚠️ Risk & Financial Exposure",
    "Operational and financial consequences associated with the selected SKU."
)


r1, r2, r3, r4 = st.columns(4)


with r1:

    st.metric(
        "Stockout Risk",
        f"{stockout_risk_percent:.1f}%"
    )


with r2:

    st.metric(
        "Sales at Risk",
        f"₹{sales_at_risk:,.0f}"
    )


with r3:

    st.metric(
        "Excess Units",
        f"{excess_units:,.0f}"
    )


with r4:

    st.metric(
        "Capital Locked",
        f"₹{capital_locked:,.0f}"
    )


# =========================================================
# PRODUCT INFORMATION
# =========================================================

section_header(
    "🏷️ Product Information",
    "Master-data information for the selected SKU."
)


info_col1, info_col2 = st.columns(2)


with info_col1:

    st.markdown(
        f"""
        **SKU:** {selected_sku}

        **Product:** {product_name}

        **Category:** {category}

        **Subcategory:** {subcategory}
        """
    )


with info_col2:

    st.markdown(
        f"""
        **Unit Cost:** ₹{unit_cost:,.2f}

        **List Price:** ₹{list_price:,.2f}

        **Estimated Selling Price:** ₹{selling_price:,.2f}

        **Reorder Point:** {reorder_point:,.0f} units
        """
    )


# =========================================================
# INVENTORY DETAILS
# =========================================================

section_header(
    "📦 Inventory Details",
    "Current inventory and replenishment parameters."
)


i1, i2, i3, i4 = st.columns(4)


with i1:

    st.metric(
        "On Hand",
        f"{on_hand:,.0f}"
    )


with i2:

    st.metric(
        "On Order",
        f"{on_order:,.0f}"
    )


with i3:

    st.metric(
        "Lead Time",
        f"{lead_time_days:.0f} days"
    )


with i4:

    st.metric(
        "Reorder Point",
        f"{reorder_point:,.0f}"
    )


# =========================================================
# MANAGEMENT RECOMMENDATION
# =========================================================

section_header(
    "🧠 Management Recommendation",
    "Recommended action based on demand, inventory and financial exposure."
)


if recommended_action == "Reorder Now":

    recommendation_text = (
        f"Inventory may not adequately cover expected lead-time demand. "
        f"Current inventory position is {inventory_position:,.0f} units "
        f"against estimated lead-time demand of "
        f"{lead_time_demand:,.0f} units. "
        f"Estimated sales exposure is ₹{sales_at_risk:,.0f}."
    )

elif recommended_action == "Markdown / Clear":

    recommendation_text = (
        f"Inventory appears elevated relative to expected demand. "
        f"Current weeks of supply are {weeks_of_supply:.1f}, "
        f"with approximately {excess_units:,.0f} excess units. "
        f"Estimated capital locked is ₹{capital_locked:,.0f}."
    )

elif recommended_action == "Monitor Stock":

    recommendation_text = (
        f"Inventory should be monitored because projected demand "
        f"may place pressure on available supply. "
        f"Current stockout risk is {stockout_risk_percent:.1f}%."
    )

elif recommended_action == "Monitor Overstock":

    recommendation_text = (
        f"Inventory should be monitored for potential overstock. "
        f"Current supply is approximately {weeks_of_supply:.1f} weeks."
    )

else:

    recommendation_text = (
        "The SKU currently appears operationally healthy. "
        "Continue monitoring demand and inventory trends."
    )


recommendation_card(
    recommended_action,
    recommendation_text
)


# =========================================================
# 360° SUMMARY
# =========================================================

section_header(
    "🎯 360° Product Summary",
    "One-page decision view for the selected SKU."
)


summary_table = pd.DataFrame({
    "Indicator": [
        "Demand Trend",
        "Forecast Confidence",
        "Average Weekly Demand",
        "Forecast Horizon Demand",
        "Inventory Position",
        "Weeks of Supply",
        "Stockout Risk",
        "Overstock Risk",
        "Risk Severity",
        "Recommended Action",
        "Priority Score",
        "Sales at Risk",
        "Capital Locked"
    ],
    "Value": [
        demand_trend,
        forecast_confidence,
        f"{avg_weekly_demand:,.0f}",
        f"{total_forecast_demand:,.0f}",
        f"{inventory_position:,.0f}",
        f"{weeks_of_supply:.1f}",
        f"{stockout_risk_percent:.1f}%",
        overstock_risk,
        risk_severity,
        recommended_action,
        f"{priority_score:.1f}",
        f"₹{sales_at_risk:,.0f}",
        f"₹{capital_locked:,.0f}"
    ]
})


st.dataframe(
    summary_table,
    use_container_width=True,
    hide_index=True
)


# =========================================================
# METHODOLOGY
# =========================================================

with st.expander(
    "📘 Product Intelligence Methodology"
):

    st.markdown(
        """
        ### Demand

        Historical SKU sales are aggregated into weekly demand.

        ### Forecast

        FORESIGHT uses the centralized ML forecasting engine
        to generate future week-by-week demand.

        ### Forecast Confidence

        Confidence is estimated using historical demand
        variability.

        ### Inventory

        Inventory position is calculated as:

        **On Hand + On Order**

        ### Lead-Time Demand

        **Average Weekly Demand × Lead Time / 7**

        ### Weeks of Supply

        **Inventory Position / Average Weekly Demand**

        ### Financial Exposure

        Sales-at-risk estimates the potential sales exposure
        associated with insufficient inventory.

        Capital-locked estimates the inventory value above the
        target stock level.

        ### Decision Support

        The final recommendation combines demand, forecast,
        inventory and risk signals.
        """
    )


# =========================================================
# FOOTER
# =========================================================

show_footer()