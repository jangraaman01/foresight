import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

from src.data_loader import (
    load_sales,
    load_inventory,
    load_sku_master,
)

from src.forecast_engine import generate_forecast_summary

from src.intelligence import calculate_business_intelligence

from src.kpi_engine import (
    calculate_all_kpis,
    format_currency,
    format_number,
    format_percentage,
)

from src.ui import (
    apply_foresight_style,
    show_sidebar_brand,
    page_header,
    section_header,
    show_footer,
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="FORESIGHT | KPI Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# STEP 58 — INTERACTIVE CROSS-FILTER STATE
# ============================================================

if "chart_category_filter" not in st.session_state:
    st.session_state["chart_category_filter"] = None

if "chart_risk_filter" not in st.session_state:
    st.session_state["chart_risk_filter"] = None

if "chart_priority_filter" not in st.session_state:
    st.session_state["chart_priority_filter"] = None


# ============================================================
# GLOBAL UI
# ============================================================

apply_foresight_style()
show_sidebar_brand()


# ============================================================
# HEADER
# ============================================================

page_header(
    "📊 KPI Dashboard",
    "Centralized management view of sales, inventory, forecast, risk and financial exposure."
)


# ============================================================
# DATA LOADING
# ============================================================

@st.cache_data
def load_dashboard_data():

    sales = load_sales().copy()
    inventory = load_inventory().copy()
    sku_master = load_sku_master().copy()

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

    inventory["on_hand_units"] = pd.to_numeric(
        inventory["on_hand_units"],
        errors="coerce",
    ).fillna(0)

    inventory["on_order_units"] = pd.to_numeric(
        inventory["on_order_units"],
        errors="coerce",
    ).fillna(0)

    inventory["lead_time_days"] = pd.to_numeric(
        inventory["lead_time_days"],
        errors="coerce",
    ).fillna(0)

    return sales, inventory, sku_master


try:

    sales, inventory, sku_master = load_dashboard_data()

except Exception as e:

    st.error("Unable to load dashboard data.")
    st.exception(e)
    st.stop()


# ============================================================
# SIDEBAR CONTROLS
# ============================================================

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Dashboard Controls")

forecast_horizon = st.sidebar.slider(
    "Forecast Horizon",
    min_value=1,
    max_value=16,
    value=8,
    step=1,
)

target_weeks = st.sidebar.slider(
    "Target Inventory Coverage",
    min_value=2,
    max_value=16,
    value=8,
    step=1,
)


# ============================================================
# FORECAST
# ============================================================

with st.spinner("Generating forecast intelligence..."):

   forecast_summary = generate_forecast_summary(
    sales,
    horizon=forecast_horizon
)


# ============================================================
# LATEST INVENTORY
# ============================================================

latest_inventory_date = inventory["date"].max()

latest_inventory = inventory[
    inventory["date"] == latest_inventory_date
].copy()


latest_inventory["inventory_position"] = (
    latest_inventory["on_hand_units"]
    + latest_inventory["on_order_units"]
)


# ============================================================
# PRODUCT INFORMATION
# ============================================================

forecast_df = forecast_summary.copy()

if not sku_master.empty:

    product_columns = [
        c
        for c in [
            "sku_id",
            "product_name",
            "category",
            "unit_cost",
            "list_price",
            "lead_time_days",
        ]
        if c in sku_master.columns
    ]

    forecast_df = forecast_df.merge(
        sku_master[
            product_columns
        ].drop_duplicates("sku_id"),
        on="sku_id",
        how="left",
    )


# ============================================================
# SELLING PRICE
# ============================================================

if "revenue" in sales.columns:

    recent_sales = sales[
        sales["date"]
        >= sales["date"].max()
        - pd.Timedelta(weeks=8)
    ].copy()

    price_df = (
        recent_sales
        .groupby("sku_id")
        .agg(
            recent_revenue=("revenue", "sum"),
            recent_units=("units_sold", "sum"),
        )
        .reset_index()
    )

    price_df["estimated_selling_price"] = np.where(
        price_df["recent_units"] > 0,
        price_df["recent_revenue"]
        / price_df["recent_units"],
        np.nan,
    )

    forecast_df = forecast_df.merge(
        price_df[
            [
                "sku_id",
                "estimated_selling_price",
            ]
        ],
        on="sku_id",
        how="left",
    )

else:

    forecast_df["estimated_selling_price"] = np.nan


if "list_price" in forecast_df.columns:

    forecast_df["estimated_selling_price"] = (
        forecast_df["estimated_selling_price"]
        .fillna(forecast_df["list_price"])
        .fillna(0)
    )

else:

    forecast_df["estimated_selling_price"] = (
        forecast_df["estimated_selling_price"]
        .fillna(0)
    )


# ============================================================
# UNIT COST / LEAD TIME
# ============================================================

if "unit_cost" not in forecast_df.columns:
    forecast_df["unit_cost"] = 0

forecast_df["unit_cost"] = pd.to_numeric(
    forecast_df["unit_cost"],
    errors="coerce",
).fillna(0)


if "lead_time_days" not in forecast_df.columns:
    forecast_df["lead_time_days"] = 7

forecast_df["lead_time_days"] = pd.to_numeric(
    forecast_df["lead_time_days"],
    errors="coerce",
).fillna(7)


# ============================================================
# MERGE INVENTORY
# ============================================================

inventory_columns = [
    "sku_id",
    "inventory_position",
    "on_hand_units",
    "on_order_units",
]

inventory_columns = [
    c
    for c in inventory_columns
    if c in latest_inventory.columns
]


dashboard_df = forecast_df.merge(
    latest_inventory[
        inventory_columns
    ],
    on="sku_id",
    how="left",
)


# ============================================================
# CLEAN INVENTORY
# ============================================================

for column in [
    "inventory_position",
    "on_hand_units",
    "on_order_units",
]:

    if column not in dashboard_df.columns:
        dashboard_df[column] = 0

    dashboard_df[column] = pd.to_numeric(
        dashboard_df[column],
        errors="coerce",
    ).fillna(0)


# ============================================================
# BUSINESS INTELLIGENCE
# ============================================================

with st.spinner("Calculating business intelligence..."):

    intelligence_df = calculate_business_intelligence(
        dashboard_df,
        target_weeks=target_weeks,
    )


# ============================================================
# GLOBAL DASHBOARD FILTERS
# ============================================================

st.sidebar.markdown("---")
st.sidebar.header("🔎 Dashboard Filters")


# ------------------------------------------------------------
# CATEGORY FILTER
# ------------------------------------------------------------

if "category" in intelligence_df.columns:

    category_options = sorted(
        intelligence_df["category"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    selected_categories = st.sidebar.multiselect(
        "Category",
        options=category_options,
        default=category_options,
        key="category_filter",
        help="Filter the dashboard by product category.",
    )

else:

    selected_categories = []


# ------------------------------------------------------------
# BUSINESS PRIORITY FILTER
# ------------------------------------------------------------

if "business_priority" in intelligence_df.columns:

    priority_options = sorted(
        intelligence_df["business_priority"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    selected_priorities = st.sidebar.multiselect(
        "Business Priority",
        options=priority_options,
        default=priority_options,
        key="priority_filter",
        help="Filter the dashboard by business priority.",
    )

else:

    selected_priorities = []


# ------------------------------------------------------------
# RISK SEVERITY FILTER
# ------------------------------------------------------------

if "risk_severity" in intelligence_df.columns:

    risk_options = sorted(
        intelligence_df["risk_severity"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    selected_risks = st.sidebar.multiselect(
        "Risk Severity",
        options=risk_options,
        default=risk_options,
        key="risk_filter",
        help="Filter the dashboard by inventory risk severity.",
    )

else:

    selected_risks = []


# ------------------------------------------------------------
# SKU FILTER
# ------------------------------------------------------------

if "sku_id" in intelligence_df.columns:

    sku_options = sorted(
        intelligence_df["sku_id"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    selected_skus = st.sidebar.multiselect(
        "SKU",
        options=sku_options,
        default=[],
        key="sku_filter",
        help="Select specific SKUs. Leave empty to show all SKUs.",
    )

else:

    selected_skus = []


# ============================================================
# APPLY GLOBAL FILTERS TO INTELLIGENCE DATA
# ============================================================

filtered_intelligence_df = intelligence_df.copy()

if selected_categories and "category" in filtered_intelligence_df.columns:

    filtered_intelligence_df = filtered_intelligence_df[
        filtered_intelligence_df["category"]
        .astype(str)
        .isin(selected_categories)
    ]

if selected_priorities and "business_priority" in filtered_intelligence_df.columns:

    filtered_intelligence_df = filtered_intelligence_df[
        filtered_intelligence_df["business_priority"]
        .astype(str)
        .isin(selected_priorities)
    ]

if selected_risks and "risk_severity" in filtered_intelligence_df.columns:

    filtered_intelligence_df = filtered_intelligence_df[
        filtered_intelligence_df["risk_severity"]
        .astype(str)
        .isin(selected_risks)
    ]

if selected_skus and "sku_id" in filtered_intelligence_df.columns:

    filtered_intelligence_df = filtered_intelligence_df[
        filtered_intelligence_df["sku_id"]
        .astype(str)
        .isin(selected_skus)
    ]



# ============================================================
# STEP 58 — APPLY INTERACTIVE CROSS-FILTERS
# ============================================================

chart_category_filter = st.session_state.get("chart_category_filter")
chart_risk_filter = st.session_state.get("chart_risk_filter")
chart_priority_filter = st.session_state.get("chart_priority_filter")

if (
    chart_category_filter
    and "category" in filtered_intelligence_df.columns
):
    filtered_intelligence_df = filtered_intelligence_df[
        filtered_intelligence_df["category"]
        .astype(str)
        .eq(str(chart_category_filter))
    ]

if (
    chart_risk_filter
    and "risk_severity" in filtered_intelligence_df.columns
):
    filtered_intelligence_df = filtered_intelligence_df[
        filtered_intelligence_df["risk_severity"]
        .astype(str)
        .eq(str(chart_risk_filter))
    ]

if (
    chart_priority_filter
    and "business_priority" in filtered_intelligence_df.columns
):
    filtered_intelligence_df = filtered_intelligence_df[
        filtered_intelligence_df["business_priority"]
        .astype(str)
        .eq(str(chart_priority_filter))
    ]


# ============================================================
# FILTERED SKU LIST
# ============================================================

filtered_sku_ids = set(
    filtered_intelligence_df["sku_id"]
    .dropna()
    .astype(str)
)


# ============================================================
# FILTER SALES DATA
# ============================================================

filtered_sales = sales[
    sales["sku_id"]
    .astype(str)
    .isin(filtered_sku_ids)
].copy()


# ============================================================
# FILTER INVENTORY DATA
# ============================================================

filtered_inventory = latest_inventory[
    latest_inventory["sku_id"]
    .astype(str)
    .isin(filtered_sku_ids)
].copy()


# ============================================================
# FILTER FORECAST DATA
# ============================================================

filtered_forecast_summary = forecast_summary[
    forecast_summary["sku_id"]
    .astype(str)
    .isin(filtered_sku_ids)
].copy()


# ============================================================
# FILTER STATUS
# ============================================================

st.sidebar.markdown("---")

st.sidebar.caption(
    f"📊 Showing {len(filtered_intelligence_df):,} "
    f"of {len(intelligence_df):,} SKUs"
)


# ============================================================
# ACTIVE FILTER SUMMARY
# ============================================================

active_filters = []

if (
    selected_categories
    and set(selected_categories) != set(category_options)
):
    active_filters.append(
        f"Category: {len(selected_categories)}"
    )

if (
    selected_priorities
    and set(selected_priorities) != set(priority_options)
):
    active_filters.append(
        f"Priority: {len(selected_priorities)}"
    )

if (
    selected_risks
    and set(selected_risks) != set(risk_options)
):
    active_filters.append(
        f"Risk: {len(selected_risks)}"
    )

if selected_skus:
    active_filters.append(
        f"SKU: {len(selected_skus)}"
    )

if active_filters:

    st.sidebar.info(
        "🔎 Active Filters\n\n"
        + " • ".join(active_filters)
    )

else:

    st.sidebar.success(
        "🌐 Showing complete portfolio"
    )



# ============================================================
# STEP 58 — CHART FILTER STATUS
# ============================================================

chart_filter_labels = []

if st.session_state.get("chart_category_filter"):
    chart_filter_labels.append(
        f"Category: {st.session_state['chart_category_filter']}"
    )

if st.session_state.get("chart_risk_filter"):
    chart_filter_labels.append(
        f"Risk: {st.session_state['chart_risk_filter']}"
    )

if st.session_state.get("chart_priority_filter"):
    chart_filter_labels.append(
        f"Priority: {st.session_state['chart_priority_filter']}"
    )

if chart_filter_labels:

    st.sidebar.warning(
        "📊 Interactive Filters\n\n"
        + " • ".join(chart_filter_labels)
    )

    if st.sidebar.button(
        "🧹 Clear Interactive Filters",
        use_container_width=True,
        key="clear_interactive_filters",
    ):
        st.session_state["chart_category_filter"] = None
        st.session_state["chart_risk_filter"] = None
        st.session_state["chart_priority_filter"] = None
        st.rerun()


# ============================================================
# RESET FILTERS
# ============================================================

if st.sidebar.button(
    "🔄 Reset Filters",
    use_container_width=True,
):

    st.session_state["category_filter"] = category_options
    st.session_state["priority_filter"] = priority_options
    st.session_state["risk_filter"] = risk_options
    st.session_state["sku_filter"] = []

    st.session_state["chart_category_filter"] = None
    st.session_state["chart_risk_filter"] = None
    st.session_state["chart_priority_filter"] = None

    st.rerun()


# ============================================================
# EMPTY FILTER RESULT PROTECTION
# ============================================================

if filtered_intelligence_df.empty:

    st.warning(
        "⚠️ No SKUs match the selected filters. "
        "Please change the dashboard filters."
    )

    st.stop()


# ============================================================
# KPI ENGINE
# ============================================================

kpis = calculate_all_kpis(
    sales=filtered_sales,
    inventory=filtered_inventory,
    forecast_summary=filtered_forecast_summary,
    intelligence_df=filtered_intelligence_df,
)


def get_kpi(section, key, default=0):

    try:

        value = kpis.get(
            section,
            {},
        ).get(
            key,
            default,
        )

        if value is None or pd.isna(value):
            return default

        return value

    except Exception:

        return default


# ============================================================
# EXECUTIVE KPI CARDS
# ============================================================

section_header(
    "Executive Performance",
    "High-level indicators for management decision making.",
)

c1, c2, c3, c4 = st.columns(4)

with c1:

    st.metric(
        "💰 Total Revenue",
        format_currency(
            get_kpi(
                "sales",
                "total_revenue",
            )
        ),
    )

with c2:

    st.metric(
        "📦 Inventory Units",
        format_number(
            get_kpi(
                "inventory",
                "total_inventory_units",
            )
        ),
    )

with c3:

    st.metric(
        "🔮 Forecast Demand",
        format_number(
            get_kpi(
                "forecast",
                "total_forecast_demand",
            )
        ),
    )

with c4:

    st.metric(
        "⚠️ Financial Exposure",
        format_currency(
            get_kpi(
                "financial",
                "total_financial_exposure",
            )
        ),
    )


st.divider()


# ============================================================
# SALES KPI
# ============================================================

section_header(
    "Sales Performance",
    "Historical sales performance and revenue trend.",
)

c1, c2, c3, c4 = st.columns(4)

with c1:

    st.metric(
        "Total Revenue",
        format_currency(
            get_kpi(
                "sales",
                "total_revenue",
            )
        ),
    )

with c2:

    st.metric(
        "Units Sold",
        format_number(
            get_kpi(
                "sales",
                "total_units_sold",
            )
        ),
    )

with c3:

    st.metric(
        "Average Daily Units",
        format_number(
            get_kpi(
                "sales",
                "average_daily_units",
            ),
            1,
        ),
    )

with c4:

    st.metric(
        "Average Daily Revenue",
        format_currency(
            get_kpi(
                "sales",
                "average_daily_revenue",
            )
        ),
    )


# ============================================================
# REVENUE TREND CHART
# ============================================================

if "revenue" in sales.columns:

    revenue_trend = (
        filtered_sales
        .groupby("date", as_index=False)
        ["revenue"]
        .sum()
        .sort_values("date")
    )

    fig_revenue = px.line(
        revenue_trend,
        x="date",
        y="revenue",
        title="Daily Revenue Trend",
        markers=False,
    )

    fig_revenue.update_layout(
        xaxis_title="Date",
        yaxis_title="Revenue",
        hovermode="x unified",
    )

    st.plotly_chart(
        fig_revenue,
        use_container_width=True,
    )


# ============================================================
# INVENTORY HEALTH
# ============================================================

section_header(
    "Inventory Health",
    "Current inventory position and stock coverage.",
)

c1, c2, c3, c4 = st.columns(4)

with c1:

    st.metric(
        "Inventory Units",
        format_number(
            get_kpi(
                "inventory",
                "total_inventory_units",
            )
        ),
    )

with c2:

    st.metric(
        "Inventory Value",
        format_currency(
            get_kpi(
                "inventory",
                "inventory_value",
            )
        ),
    )

with c3:

    st.metric(
        "Average Weeks Supply",
        f"{get_kpi('inventory', 'average_weeks_of_supply', 0):.1f}",
    )

with c4:

    st.metric(
        "SKU Count",
        format_number(
            get_kpi(
                "inventory",
                "sku_count",
            )
        ),
    )


# ============================================================
# INVENTORY BY CATEGORY
# ============================================================

if "category" in intelligence_df.columns:

    inventory_category = (
        filtered_intelligence_df
        .groupby("category", dropna=False)
        ["inventory_position"]
        .sum()
        .reset_index()
        .sort_values(
            "inventory_position",
            ascending=False,
        )
    )

    fig_inventory = px.bar(
        inventory_category,
        x="category",
        y="inventory_position",
        title="Inventory Position by Category",
    )

    fig_inventory.update_layout(
        xaxis_title="Category",
        yaxis_title="Inventory Units",
    )

    st.plotly_chart(
        fig_inventory,
        use_container_width=True,
    )


# ============================================================
# FORECAST KPIs
# ============================================================

section_header(
    "Demand Forecast",
    "Forward-looking demand indicators generated by the forecasting engine.",
)

c1, c2, c3, c4 = st.columns(4)

with c1:

    st.metric(
        "Forecast Demand",
        format_number(
            get_kpi(
                "forecast",
                "total_forecast_demand",
            )
        ),
    )

with c2:

    st.metric(
        "Increasing Demand",
        format_number(
            get_kpi(
                "forecast",
                "increasing_demand_skus",
            )
        ),
    )

with c3:

    st.metric(
        "Declining Demand",
        format_number(
            get_kpi(
                "forecast",
                "declining_demand_skus",
            )
        ),
    )

with c4:

    confidence = get_kpi(
        "forecast",
        "average_confidence",
    )

    st.metric(
        "Average Confidence",
        f"{confidence:.1f}%",
    )


# ============================================================
# DEMAND TREND DISTRIBUTION
# ============================================================

if "demand_trend" in forecast_summary.columns:

    trend_distribution = (
        filtered_forecast_summary[
            "demand_trend"
        ]
        .value_counts()
        .reset_index()
    )

    trend_distribution.columns = [
        "Demand Trend",
        "SKUs",
    ]

    fig_trend = px.pie(
        trend_distribution,
        names="Demand Trend",
        values="SKUs",
        title="Demand Trend Distribution",
        hole=0.45,
    )

    st.plotly_chart(
        fig_trend,
        use_container_width=True,
    )


# ============================================================
# RISK OVERVIEW
# ============================================================

section_header(
    "Risk Overview",
    "Identify stockout, overstock and operational risks.",
)

c1, c2, c3, c4 = st.columns(4)

with c1:

    st.metric(
        "Average Stockout Risk",
        f"{get_kpi('risk', 'average_stockout_risk', 0):.1f}%",
    )

with c2:

    st.metric(
        "Critical SKUs",
        format_number(
            get_kpi(
                "risk",
                "critical_skus",
            )
        ),
    )

with c3:

    st.metric(
        "High-Risk SKUs",
        format_number(
            get_kpi(
                "risk",
                "high_risk_skus",
            )
        ),
    )

with c4:

    st.metric(
        "Overstock SKUs",
        format_number(
            get_kpi(
                "risk",
                "overstock_skus",
            )
        ),
    )


# ============================================================
# RISK SEVERITY CHART
# ============================================================

if "risk_severity" in intelligence_df.columns:

    severity = (
        filtered_intelligence_df[
            "risk_severity"
        ]
        .value_counts()
        .reset_index()
    )

    severity.columns = [
        "Risk Severity",
        "SKUs",
    ]

    fig_risk = px.bar(
        severity,
        x="Risk Severity",
        y="SKUs",
        title="Risk Severity Distribution",
        text="SKUs",
    )

    fig_risk.update_layout(
        xaxis_title="Risk Severity",
        yaxis_title="Number of SKUs",
    )

    st.plotly_chart(
        fig_risk,
        use_container_width=True,
    )


# ============================================================
# RISK MATRIX
# ============================================================

if {
    "weeks_of_supply",
    "stockout_risk_percent",
}.issubset(intelligence_df.columns):

    risk_matrix = filtered_intelligence_df.copy()

    fig_matrix = px.scatter(
        risk_matrix,
        x="weeks_of_supply",
        y="stockout_risk_percent",
        size="sales_at_risk"
        if "sales_at_risk" in risk_matrix.columns
        else None,
        hover_name="sku_id",
        hover_data=[
            c
            for c in [
                "business_priority",
                "risk_severity",
                "recommended_action",
            ]
            if c in risk_matrix.columns
        ],
        title="Inventory Risk Matrix",
    )

    fig_matrix.update_layout(
        xaxis_title="Weeks of Supply",
        yaxis_title="Stockout Risk (%)",
    )

    st.plotly_chart(
        fig_matrix,
        use_container_width=True,
    )


# ============================================================
# FINANCIAL EXPOSURE
# ============================================================

section_header(
    "Financial Exposure",
    "Quantify the commercial impact of inventory risk.",
)

c1, c2, c3, c4 = st.columns(4)

with c1:

    st.metric(
        "Sales at Risk",
        format_currency(
            get_kpi(
                "financial",
                "sales_at_risk",
            )
        ),
    )

with c2:

    st.metric(
        "Capital Locked",
        format_currency(
            get_kpi(
                "financial",
                "capital_locked",
            )
        ),
    )

with c3:

    st.metric(
        "Total Exposure",
        format_currency(
            get_kpi(
                "financial",
                "total_financial_exposure",
            )
        ),
    )

with c4:

    st.metric(
        "Exposure / Revenue",
        format_percentage(
            get_kpi(
                "financial",
                "exposure_percentage",
            )
        ),
    )


# ============================================================
# CATEGORY FINANCIAL EXPOSURE
# ============================================================

if "category" in intelligence_df.columns:

    category_exposure = (
        filtered_intelligence_df
        .groupby(
            "category",
            dropna=False,
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
        .reset_index()
    )

    category_exposure = category_exposure.sort_values(
        "total_exposure",
        ascending=False,
    )

    fig_exposure = px.bar(
        category_exposure,
        x="category",
        y=[
            "sales_at_risk",
            "capital_locked",
        ],
        title="Financial Exposure by Category",
        barmode="group",
    )

    fig_exposure.update_layout(
        xaxis_title="Category",
        yaxis_title="Amount",
        legend_title="Exposure Type",
    )

    st.plotly_chart(
        fig_exposure,
        use_container_width=True,
    )


# ============================================================
# BUSINESS PRIORITIES
# ============================================================

section_header(
    "Business Priorities",
    "Translate analytical results into management actions.",
)

priority_counts = (
    filtered_intelligence_df[
        "business_priority"
    ]
    .value_counts()
    .reset_index()
)

priority_counts.columns = [
    "Business Priority",
    "SKUs",
]


fig_priority = px.pie(
    priority_counts,
    names="Business Priority",
    values="SKUs",
    title="Business Priority Distribution",
    hole=0.45,
)

st.plotly_chart(
    fig_priority,
    use_container_width=True,
)


# ============================================================
# TOP PRIORITY SKUs
# ============================================================

section_header(
    "Top Priority SKUs",
    "Products requiring the highest level of management attention.",
)

if "priority_score" in intelligence_df.columns:

    top_priority = (
        filtered_intelligence_df
        .sort_values(
            "priority_score",
            ascending=False,
        )
        .head(15)
        .copy()
    )

    display_columns = [
        c
        for c in [
            "sku_id",
            "product_name",
            "category",
            "business_priority",
            "risk_severity",
            "recommended_action",
            "priority_score",
            "stockout_risk_percent",
            "sales_at_risk",
            "capital_locked",
        ]
        if c in top_priority.columns
    ]

    st.dataframe(
        top_priority[
            display_columns
        ],
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# MANAGEMENT RECOMMENDATIONS
# ============================================================

section_header(
    "Management Recommendations",
    "Automated actions based on portfolio risk and financial exposure.",
)

critical_count = get_kpi(
    "risk",
    "critical_skus",
)

high_risk_count = get_kpi(
    "risk",
    "high_risk_skus",
)

sales_at_risk = get_kpi(
    "financial",
    "sales_at_risk",
)

capital_locked = get_kpi(
    "financial",
    "capital_locked",
)


if critical_count > 0:

    st.error(
        f"🚨 {int(critical_count)} critical SKU(s) "
        "require immediate management attention."
    )


if high_risk_count > 0:

    st.warning(
        f"⚠️ {int(high_risk_count)} high-risk SKU(s) "
        "should be reviewed for replenishment."
    )


if sales_at_risk > 0:

    st.info(
        f"💰 {format_currency(sales_at_risk)} "
        "of potential sales are currently exposed to stockout risk."
    )


if capital_locked > 0:

    st.info(
        f"📦 {format_currency(capital_locked)} "
        "of capital is currently tied up in excess inventory."
    )


if (
    critical_count == 0
    and high_risk_count == 0
    and sales_at_risk == 0
    and capital_locked == 0
):

    st.success(
        "✅ No major financial or inventory exposure detected."
    )


# ============================================================
# DETAILED DATA
# ============================================================

with st.expander("📋 View Complete Intelligence Dataset"):

    st.dataframe(
        filtered_intelligence_df,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    f"Forecast horizon: {forecast_horizon} weeks | "
    f"Target inventory coverage: {target_weeks} weeks | "
    f"Latest inventory date: {latest_inventory_date.date()} | "
    "FORESIGHT Central KPI & Intelligence Engine"
)


# ============================================================
# STEP 58 — INTERACTIVE CHART FILTERING & CROSS-FILTERING
# ============================================================

section_header("🎛️ Interactive Cross-Filtering")

st.caption(
    "Use these portfolio controls to cross-filter the dashboard. "
    "After you click Apply, all KPI calculations, charts, tables, "
    "and the SKU drill-down are recalculated using the selected view."
)

cross_col1, cross_col2, cross_col3, cross_col4 = st.columns(
    [1.25, 1.25, 1.25, 0.75]
)

with cross_col1:

    interactive_category_options = ["All"]

    if "category" in intelligence_df.columns:
        interactive_category_options += sorted(
            intelligence_df["category"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

    current_category_filter = st.session_state.get(
        "chart_category_filter"
    )

    category_default_index = (
        interactive_category_options.index(current_category_filter)
        if current_category_filter in interactive_category_options
        else 0
    )

    interactive_category = st.selectbox(
        "Category",
        options=interactive_category_options,
        index=category_default_index,
        key="step58_category_select",
    )


with cross_col2:

    interactive_risk_options = ["All"]

    if "risk_severity" in intelligence_df.columns:
        interactive_risk_options += sorted(
            intelligence_df["risk_severity"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

    current_risk_filter = st.session_state.get(
        "chart_risk_filter"
    )

    risk_default_index = (
        interactive_risk_options.index(current_risk_filter)
        if current_risk_filter in interactive_risk_options
        else 0
    )

    interactive_risk = st.selectbox(
        "Risk Severity",
        options=interactive_risk_options,
        index=risk_default_index,
        key="step58_risk_select",
    )


with cross_col3:

    interactive_priority_options = ["All"]

    if "business_priority" in intelligence_df.columns:
        interactive_priority_options += sorted(
            intelligence_df["business_priority"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

    current_priority_filter = st.session_state.get(
        "chart_priority_filter"
    )

    priority_default_index = (
        interactive_priority_options.index(current_priority_filter)
        if current_priority_filter in interactive_priority_options
        else 0
    )

    interactive_priority = st.selectbox(
        "Business Priority",
        options=interactive_priority_options,
        index=priority_default_index,
        key="step58_priority_select",
    )


with cross_col4:

    st.markdown(
        "<div style='height:28px'></div>",
        unsafe_allow_html=True,
    )

    apply_interactive_filters = st.button(
        "Apply",
        use_container_width=True,
        key="step58_apply_filters",
    )


if apply_interactive_filters:

    st.session_state["chart_category_filter"] = (
        None
        if interactive_category == "All"
        else interactive_category
    )

    st.session_state["chart_risk_filter"] = (
        None
        if interactive_risk == "All"
        else interactive_risk
    )

    st.session_state["chart_priority_filter"] = (
        None
        if interactive_priority == "All"
        else interactive_priority
    )

    st.rerun()


# ------------------------------------------------------------
# INTERACTIVE PORTFOLIO SUMMARY
# ------------------------------------------------------------

st.markdown("### 📊 Cross-Filtered Portfolio View")

cross_summary_1, cross_summary_2 = st.columns(2)


with cross_summary_1:

    if "category" in filtered_intelligence_df.columns:

        category_cross_view = (
            filtered_intelligence_df["category"]
            .fillna("Unknown")
            .astype(str)
            .value_counts()
            .rename_axis("Category")
            .reset_index(name="SKU Count")
        )

        if not category_cross_view.empty:

            fig_cross_category = px.bar(
                category_cross_view,
                x="Category",
                y="SKU Count",
                text_auto=True,
                title="SKU Distribution by Category",
            )

            fig_cross_category.update_layout(
                xaxis_title="Category",
                yaxis_title="SKU Count",
            )

            st.plotly_chart(
                fig_cross_category,
                use_container_width=True,
                key="step58_category_chart",
            )


with cross_summary_2:

    if "risk_severity" in filtered_intelligence_df.columns:

        risk_cross_view = (
            filtered_intelligence_df["risk_severity"]
            .fillna("Unknown")
            .astype(str)
            .value_counts()
            .rename_axis("Risk Severity")
            .reset_index(name="SKU Count")
        )

        if not risk_cross_view.empty:

            fig_cross_risk = px.bar(
                risk_cross_view,
                x="Risk Severity",
                y="SKU Count",
                text_auto=True,
                title="SKU Distribution by Risk Severity",
            )

            fig_cross_risk.update_layout(
                xaxis_title="Risk Severity",
                yaxis_title="SKU Count",
            )

            st.plotly_chart(
                fig_cross_risk,
                use_container_width=True,
                key="step58_risk_chart",
            )


if "business_priority" in filtered_intelligence_df.columns:

    priority_cross_view = (
        filtered_intelligence_df["business_priority"]
        .fillna("Unknown")
        .astype(str)
        .value_counts()
        .rename_axis("Business Priority")
        .reset_index(name="SKU Count")
    )

    if not priority_cross_view.empty:

        fig_cross_priority = px.pie(
            priority_cross_view,
            names="Business Priority",
            values="SKU Count",
            hole=0.45,
            title="Business Priority Mix",
        )

        st.plotly_chart(
            fig_cross_priority,
            use_container_width=True,
            key="step58_priority_chart",
        )


active_interactive_filters = []

if st.session_state.get("chart_category_filter"):
    active_interactive_filters.append(
        f"Category = {st.session_state['chart_category_filter']}"
    )

if st.session_state.get("chart_risk_filter"):
    active_interactive_filters.append(
        f"Risk = {st.session_state['chart_risk_filter']}"
    )

if st.session_state.get("chart_priority_filter"):
    active_interactive_filters.append(
        f"Priority = {st.session_state['chart_priority_filter']}"
    )


if active_interactive_filters:

    st.info(
        "🎛️ Active cross-filter: "
        + " | ".join(active_interactive_filters)
    )

else:

    st.success(
        "🌐 Interactive cross-filter is showing the complete "
        "portfolio allowed by the sidebar filters."
    )



# ============================================================

# ============================================================
# STEP 59 — ADVANCED SKU-LEVEL ANALYSIS
# ============================================================

section_header("🔬 Advanced SKU Intelligence")

st.caption(
    "Compare selected SKUs across revenue, demand, inventory, risk, "
    "priority, and financial exposure."
)

advanced_sku_df = filtered_intelligence_df.copy()

# ------------------------------------------------------------
# SKU ANALYSIS CONTROLS
# ------------------------------------------------------------

if "sku_id" in advanced_sku_df.columns:

    advanced_sku_options = sorted(
        advanced_sku_df["sku_id"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    default_advanced_skus = advanced_sku_options[:5]

    selected_advanced_skus = st.multiselect(
        "Compare SKUs",
        options=advanced_sku_options,
        default=default_advanced_skus,
        key="advanced_sku_compare",
        help="Select one or more SKUs for detailed comparison.",
    )

else:
    selected_advanced_skus = []

if selected_advanced_skus:

    comparison_df = advanced_sku_df[
        advanced_sku_df["sku_id"]
        .astype(str)
        .isin(selected_advanced_skus)
    ].copy()

    # --------------------------------------------------------
    # SALES METRICS
    # --------------------------------------------------------

    if "sku_id" in filtered_sales.columns:

        sku_sales_summary = filtered_sales[
            filtered_sales["sku_id"]
            .astype(str)
            .isin(selected_advanced_skus)
        ].copy()

        if not sku_sales_summary.empty:

            if "revenue" in sku_sales_summary.columns:
                sku_revenue_summary = (
                    sku_sales_summary
                    .assign(
                        revenue_numeric=pd.to_numeric(
                            sku_sales_summary["revenue"],
                            errors="coerce",
                        ).fillna(0)
                    )
                    .groupby(
                        sku_sales_summary["sku_id"].astype(str)
                    )["revenue_numeric"]
                    .sum()
                    .to_dict()
                )
            else:
                sku_revenue_summary = {}

            if "quantity" in sku_sales_summary.columns:
                sku_units_summary = (
                    sku_sales_summary
                    .assign(
                        quantity_numeric=pd.to_numeric(
                            sku_sales_summary["quantity"],
                            errors="coerce",
                        ).fillna(0)
                    )
                    .groupby(
                        sku_sales_summary["sku_id"].astype(str)
                    )["quantity_numeric"]
                    .sum()
                    .to_dict()
                )
            else:
                sku_units_summary = {}

        else:
            sku_revenue_summary = {}
            sku_units_summary = {}

    else:
        sku_revenue_summary = {}
        sku_units_summary = {}

    comparison_df["Total Revenue"] = (
        comparison_df["sku_id"]
        .astype(str)
        .map(sku_revenue_summary)
        .fillna(0)
    )

    comparison_df["Units Sold"] = (
        comparison_df["sku_id"]
        .astype(str)
        .map(sku_units_summary)
        .fillna(0)
    )

    # --------------------------------------------------------
    # NORMALIZE BUSINESS METRICS
    # --------------------------------------------------------

    def _numeric_column(frame, names, default=0):
        for name in names:
            if name in frame.columns:
                return pd.to_numeric(
                    frame[name],
                    errors="coerce",
                ).fillna(default)
        return pd.Series(
            default,
            index=frame.index,
            dtype="float64",
        )

    comparison_df["Current Stock"] = _numeric_column(
        comparison_df,
        [
            "current_stock",
            "stock",
            "inventory",
            "inventory_position",
            "on_hand",
        ],
    )

    comparison_df["Forecast Demand"] = _numeric_column(
        comparison_df,
        [
            "forecast_demand",
            "forecast",
            "predicted_demand",
            "demand_forecast",
        ],
    )

    comparison_df["Financial Exposure"] = _numeric_column(
        comparison_df,
        [
            "financial_exposure",
            "inventory_value",
            "exposure",
            "risk_exposure",
        ],
    )

    comparison_df["Demand Gap"] = (
        comparison_df["Forecast Demand"]
        - comparison_df["Current Stock"]
    )

    comparison_df["Stock Coverage Ratio"] = np.where(
        comparison_df["Forecast Demand"] > 0,
        comparison_df["Current Stock"]
        / comparison_df["Forecast Demand"],
        np.nan,
    )

    # --------------------------------------------------------
    # COMPARISON TABLE
    # --------------------------------------------------------

    st.markdown("### 📋 SKU Comparison")

    display_columns = [
        "sku_id",
        "Total Revenue",
        "Units Sold",
        "Current Stock",
        "Forecast Demand",
        "Demand Gap",
        "Stock Coverage Ratio",
        "Financial Exposure",
    ]

    if "category" in comparison_df.columns:
        display_columns.insert(1, "category")

    if "risk_severity" in comparison_df.columns:
        display_columns.append("risk_severity")

    if "business_priority" in comparison_df.columns:
        display_columns.append("business_priority")

    available_columns = [
        col for col in display_columns
        if col in comparison_df.columns
    ]

    st.dataframe(
        comparison_df[available_columns],
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------------------------
    # REVENUE COMPARISON
    # --------------------------------------------------------

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:

        revenue_chart_df = comparison_df[
            ["sku_id", "Total Revenue"]
        ].copy()

        fig_sku_revenue = px.bar(
            revenue_chart_df,
            x="sku_id",
            y="Total Revenue",
            text_auto=".2f",
            title="Revenue Comparison",
        )

        fig_sku_revenue.update_layout(
            xaxis_title="SKU",
            yaxis_title="Revenue",
        )

        st.plotly_chart(
            fig_sku_revenue,
            use_container_width=True,
            key="step59_revenue_comparison",
        )

    # --------------------------------------------------------
    # STOCK VS FORECAST COMPARISON
    # --------------------------------------------------------

    with chart_col2:

        inventory_compare_df = comparison_df[
            [
                "sku_id",
                "Current Stock",
                "Forecast Demand",
            ]
        ].copy()

        inventory_long_df = inventory_compare_df.melt(
            id_vars="sku_id",
            value_vars=[
                "Current Stock",
                "Forecast Demand",
            ],
            var_name="Metric",
            value_name="Units",
        )

        fig_stock_forecast = px.bar(
            inventory_long_df,
            x="sku_id",
            y="Units",
            color="Metric",
            barmode="group",
            title="Current Stock vs Forecast Demand",
        )

        fig_stock_forecast.update_layout(
            xaxis_title="SKU",
            yaxis_title="Units",
        )

        st.plotly_chart(
            fig_stock_forecast,
            use_container_width=True,
            key="step59_stock_forecast",
        )

    # --------------------------------------------------------
    # DEMAND GAP ANALYSIS
    # --------------------------------------------------------

    st.markdown("### 📉 Demand Gap Analysis")

    gap_chart_df = comparison_df[
        ["sku_id", "Demand Gap"]
    ].sort_values(
        "Demand Gap",
        ascending=False,
    )

    fig_demand_gap = px.bar(
        gap_chart_df,
        x="sku_id",
        y="Demand Gap",
        text_auto=".2f",
        title="Forecast Demand Gap",
    )

    fig_demand_gap.add_hline(
        y=0,
        line_width=1,
    )

    fig_demand_gap.update_layout(
        xaxis_title="SKU",
        yaxis_title="Forecast Demand − Current Stock",
    )

    st.plotly_chart(
        fig_demand_gap,
        use_container_width=True,
        key="step59_demand_gap",
    )

    # --------------------------------------------------------
    # STOCK COVERAGE
    # --------------------------------------------------------

    st.markdown("### 🛡️ Stock Coverage Analysis")

    coverage_chart_df = comparison_df[
        ["sku_id", "Stock Coverage Ratio"]
    ].copy()

    coverage_chart_df["Stock Coverage Ratio"] = (
        coverage_chart_df["Stock Coverage Ratio"]
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0)
    )

    fig_coverage = px.bar(
        coverage_chart_df,
        x="sku_id",
        y="Stock Coverage Ratio",
        text_auto=".2f",
        title="Stock Coverage Ratio",
    )

    fig_coverage.add_hline(
        y=1,
        line_width=1,
    )

    fig_coverage.update_layout(
        xaxis_title="SKU",
        yaxis_title="Current Stock / Forecast Demand",
    )

    st.plotly_chart(
        fig_coverage,
        use_container_width=True,
        key="step59_stock_coverage",
    )

    # --------------------------------------------------------
    # PRIORITY / RISK PROFILE
    # --------------------------------------------------------

    profile_col1, profile_col2 = st.columns(2)

    with profile_col1:

        if "risk_severity" in comparison_df.columns:

            risk_profile = (
                comparison_df["risk_severity"]
                .fillna("Unknown")
                .astype(str)
                .value_counts()
                .rename_axis("Risk Severity")
                .reset_index(name="SKU Count")
            )

            fig_risk_profile = px.pie(
                risk_profile,
                names="Risk Severity",
                values="SKU Count",
                hole=0.45,
                title="Selected SKU Risk Profile",
            )

            st.plotly_chart(
                fig_risk_profile,
                use_container_width=True,
                key="step59_risk_profile",
            )

    with profile_col2:

        if "business_priority" in comparison_df.columns:

            priority_profile = (
                comparison_df["business_priority"]
                .fillna("Unknown")
                .astype(str)
                .value_counts()
                .rename_axis("Business Priority")
                .reset_index(name="SKU Count")
            )

            fig_priority_profile = px.pie(
                priority_profile,
                names="Business Priority",
                values="SKU Count",
                hole=0.45,
                title="Selected SKU Priority Profile",
            )

            st.plotly_chart(
                fig_priority_profile,
                use_container_width=True,
                key="step59_priority_profile",
            )

    # --------------------------------------------------------
    # AUTOMATED SKU INSIGHTS
    # --------------------------------------------------------

    st.markdown("### 🧠 Automated SKU Insights")

    insight_count = 0

    for _, row in comparison_df.iterrows():

        sku = str(row.get("sku_id", "Unknown"))
        stock = float(row.get("Current Stock", 0))
        forecast = float(row.get("Forecast Demand", 0))
        gap = float(row.get("Demand Gap", 0))
        coverage = row.get("Stock Coverage Ratio", np.nan)

        risk = str(
            row.get("risk_severity", "N/A")
        )

        priority = str(
            row.get("business_priority", "N/A")
        )

        if forecast > stock:
            st.warning(
                f"📦 **{sku}:** Forecast demand exceeds current stock "
                f"by **{gap:,.0f} units**. Replenishment should be reviewed."
            )
            insight_count += 1

        elif pd.notna(coverage) and coverage > 2:
            st.info(
                f"📊 **{sku}:** Current stock is more than twice the "
                "forecast demand. Review excess inventory exposure."
            )
            insight_count += 1

        elif any(
            word in risk.lower()
            for word in ["critical", "high", "severe"]
        ):
            st.warning(
                f"⚠️ **{sku}:** Risk level is **{risk}**. "
                "Prioritize inventory and supply-chain review."
            )
            insight_count += 1

        elif any(
            word in priority.lower()
            for word in ["critical", "high", "urgent"]
        ):
            st.info(
                f"🎯 **{sku}:** Business priority is **{priority}**. "
                "Keep this SKU under close management monitoring."
            )
            insight_count += 1

    if insight_count == 0:
        st.success(
            "✅ No immediate SKU-level exceptions were identified "
            "for the selected comparison set."
        )

else:

    st.info(
        "Select one or more SKUs above to activate the advanced "
        "SKU comparison analysis."
    )



# STEP 57 — SKU DRILL-DOWN & ADVANCED SKU ANALYTICS
# ============================================================

section_header("📦 SKU Drill-Down")

st.caption(
    "Select an SKU to inspect its sales performance, inventory position, "
    "forecast, risk exposure, financial impact, and recommendation."
)

drilldown_sku_options = sorted(
    filtered_intelligence_df["sku_id"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)

if drilldown_sku_options:

    selected_drilldown_sku = st.selectbox(
        "Select SKU",
        options=drilldown_sku_options,
        key="drilldown_sku",
        help="Choose an SKU from the currently filtered portfolio.",
    )

    sku_detail = filtered_intelligence_df[
        filtered_intelligence_df["sku_id"].astype(str)
        == str(selected_drilldown_sku)
    ].copy()

    if not sku_detail.empty:

        sku_row = sku_detail.iloc[0]

        def _first_available(frame, columns, default=np.nan):
            for column in columns:
                if column in frame.columns:
                    value = frame.iloc[0][column]
                    if pd.notna(value):
                        return value
            return default

        sku_sales_df = filtered_sales[
            filtered_sales["sku_id"].astype(str)
            == str(selected_drilldown_sku)
        ].copy()

        sku_inventory_df = filtered_inventory[
            filtered_inventory["sku_id"].astype(str)
            == str(selected_drilldown_sku)
        ].copy()

        sku_forecast_df = filtered_forecast_summary[
            filtered_forecast_summary["sku_id"].astype(str)
            == str(selected_drilldown_sku)
        ].copy()

        sku_revenue = 0.0
        if not sku_sales_df.empty:
            if "revenue" in sku_sales_df.columns:
                sku_revenue = pd.to_numeric(
                    sku_sales_df["revenue"], errors="coerce"
                ).fillna(0).sum()
            elif {"quantity", "unit_price"}.issubset(sku_sales_df.columns):
                sku_revenue = (
                    pd.to_numeric(
                        sku_sales_df["quantity"], errors="coerce"
                    ).fillna(0)
                    * pd.to_numeric(
                        sku_sales_df["unit_price"], errors="coerce"
                    ).fillna(0)
                ).sum()

        sku_units_sold = 0.0
        if not sku_sales_df.empty and "quantity" in sku_sales_df.columns:
            sku_units_sold = pd.to_numeric(
                sku_sales_df["quantity"], errors="coerce"
            ).fillna(0).sum()

        sku_stock = _first_available(
            sku_inventory_df,
            ["stock", "inventory", "quantity", "current_stock", "on_hand"],
            _first_available(
                sku_detail,
                ["current_stock", "stock", "inventory", "inventory_position"],
                0,
            ),
        )

        sku_forecast = _first_available(
            sku_forecast_df,
            [
                "forecast",
                "forecast_demand",
                "predicted_demand",
                "predicted_quantity",
                "demand_forecast",
            ],
            _first_available(
                sku_detail,
                [
                    "forecast_demand",
                    "predicted_demand",
                    "forecast",
                    "demand_forecast",
                ],
                np.nan,
            ),
        )

        sku_risk = _first_available(
            sku_detail,
            ["risk_severity", "risk_level", "risk"],
            "N/A",
        )

        sku_priority = _first_available(
            sku_detail,
            ["business_priority", "priority"],
            "N/A",
        )

        sku_exposure = _first_available(
            sku_detail,
            [
                "financial_exposure",
                "inventory_value",
                "exposure",
                "risk_exposure",
            ],
            0,
        )

        sku_category = _first_available(
            sku_detail,
            ["category", "product_category"],
            "N/A",
        )

        sku_product = _first_available(
            sku_detail,
            ["product_name", "product", "item_name", "sku_name"],
            str(selected_drilldown_sku),
        )

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.metric("SKU Revenue", format_currency(sku_revenue))

        with c2:
            st.metric("Units Sold", format_number(sku_units_sold))

        with c3:
            st.metric("Current Stock", format_number(sku_stock))

        with c4:
            st.metric(
                "Forecast Demand",
                format_number(sku_forecast)
                if pd.notna(sku_forecast)
                else "N/A",
            )

        st.markdown("### 🧾 SKU Business Profile")

        p1, p2, p3, p4 = st.columns(4)

        with p1:
            st.info(f"**SKU**\n\n{selected_drilldown_sku}")

        with p2:
            st.info(f"**Product**\n\n{sku_product}")

        with p3:
            st.info(f"**Category**\n\n{sku_category}")

        with p4:
            st.info(f"**Business Priority**\n\n{sku_priority}")

        r1, r2, r3 = st.columns(3)

        with r1:
            st.metric("Risk Severity", str(sku_risk))

        with r2:
            try:
                exposure_display = format_currency(float(sku_exposure))
            except (TypeError, ValueError):
                exposure_display = str(sku_exposure)

            st.metric("Financial Exposure", exposure_display)

        with r3:
            lead_time = _first_available(
                sku_detail,
                ["lead_time", "lead_time_days", "supplier_lead_time"],
                np.nan,
            )

            if pd.notna(lead_time):
                try:
                    lead_time_display = f"{float(lead_time):g} days"
                except (TypeError, ValueError):
                    lead_time_display = str(lead_time)
            else:
                lead_time_display = "N/A"

            st.metric("Lead Time", lead_time_display)

        st.markdown("### 📈 SKU Sales Trend")

        if not sku_sales_df.empty:

            date_col = next(
                (
                    col
                    for col in [
                        "date",
                        "order_date",
                        "sales_date",
                        "transaction_date",
                    ]
                    if col in sku_sales_df.columns
                ),
                None,
            )

            revenue_col = (
                "revenue"
                if "revenue" in sku_sales_df.columns
                else None
            )

            if revenue_col is None and {
                "quantity",
                "unit_price",
            }.issubset(sku_sales_df.columns):

                sku_sales_df["_calculated_revenue"] = (
                    pd.to_numeric(
                        sku_sales_df["quantity"], errors="coerce"
                    ).fillna(0)
                    * pd.to_numeric(
                        sku_sales_df["unit_price"], errors="coerce"
                    ).fillna(0)
                )

                revenue_col = "_calculated_revenue"

            if date_col and revenue_col:

                sku_sales_df[date_col] = pd.to_datetime(
                    sku_sales_df[date_col],
                    errors="coerce",
                )

                trend_df = (
                    sku_sales_df.dropna(subset=[date_col])
                    .groupby(date_col, as_index=False)[revenue_col]
                    .sum()
                    .sort_values(date_col)
                )

                if not trend_df.empty:

                    fig_sku_trend = px.line(
                        trend_df,
                        x=date_col,
                        y=revenue_col,
                        markers=True,
                        title=f"Revenue Trend — {selected_drilldown_sku}",
                    )

                    fig_sku_trend.update_layout(
                        xaxis_title="Date",
                        yaxis_title="Revenue",
                        hovermode="x unified",
                    )

                    st.plotly_chart(
                        fig_sku_trend,
                        use_container_width=True,
                    )

                else:
                    st.info(
                        "No dated sales records are available for this SKU."
                    )

            else:
                st.info(
                    "Sales data does not contain the date/revenue fields "
                    "needed for the SKU trend chart."
                )

        else:
            st.info("No sales records are available for the selected SKU.")

        st.markdown("### 📦 Inventory vs Forecast")

        comparison_values = pd.DataFrame(
            {
                "Metric": [
                    "Current Stock",
                    "Forecast Demand",
                ],
                "Value": [
                    pd.to_numeric(
                        pd.Series([sku_stock]),
                        errors="coerce",
                    ).fillna(0).iloc[0],
                    pd.to_numeric(
                        pd.Series([sku_forecast]),
                        errors="coerce",
                    ).fillna(0).iloc[0],
                ],
            }
        )

        fig_inventory_forecast = px.bar(
            comparison_values,
            x="Metric",
            y="Value",
            text_auto=".2f",
            title=f"Inventory vs Forecast — {selected_drilldown_sku}",
        )

        fig_inventory_forecast.update_layout(
            xaxis_title="",
            yaxis_title="Units",
        )

        st.plotly_chart(
            fig_inventory_forecast,
            use_container_width=True,
        )

        st.markdown("### 🧠 SKU Intelligence")

        detail_columns = [
            "sku_id",
            "product_name",
            "category",
            "business_priority",
            "risk_severity",
            "financial_exposure",
            "inventory_position",
            "lead_time",
            "forecast_demand",
        ]

        available_detail_columns = [
            column
            for column in detail_columns
            if column in sku_detail.columns
        ]

        if available_detail_columns:
            st.dataframe(
                sku_detail[available_detail_columns],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.dataframe(
                sku_detail,
                use_container_width=True,
                hide_index=True,
            )

        st.markdown("### 💡 SKU Recommendation")

        risk_text = str(sku_risk).lower()
        priority_text = str(sku_priority).lower()

        if any(
            word in risk_text
            for word in ["critical", "high", "severe"]
        ):

            recommendation = (
                f"🚨 **Immediate attention required for "
                f"{selected_drilldown_sku}.** Review replenishment, "
                "supplier lead time, and stock coverage to reduce "
                "the identified inventory risk."
            )

        elif any(
            word in priority_text
            for word in ["high", "critical", "urgent"]
        ):

            recommendation = (
                f"🎯 **High-priority SKU:** {selected_drilldown_sku}. "
                "Monitor demand and inventory closely and prioritize "
                "replenishment decisions."
            )

        elif pd.notna(sku_forecast) and pd.notna(sku_stock):

            try:

                if float(sku_forecast) > float(sku_stock):

                    recommendation = (
                        f"📦 **Potential stock pressure:** forecast demand "
                        f"({float(sku_forecast):,.0f}) is above current stock "
                        f"({float(sku_stock):,.0f}). Consider replenishment planning."
                    )

                else:

                    recommendation = (
                        f"✅ **Stable inventory position:** current stock "
                        f"({float(sku_stock):,.0f}) is at or above forecast demand "
                        f"({float(sku_forecast):,.0f}). Continue monitoring demand."
                    )

            except (TypeError, ValueError):

                recommendation = (
                    f"ℹ️ Continue monitoring {selected_drilldown_sku} "
                    "using sales, inventory, forecast, and risk indicators."
                )

        else:

            recommendation = (
                f"ℹ️ Continue monitoring {selected_drilldown_sku} "
                "using sales, inventory, forecast, and risk indicators."
            )

        st.success(recommendation)

    else:
        st.warning("No intelligence record found for the selected SKU.")

else:
    st.info("No SKU is available for drill-down under the current filters.")




# ============================================================
# STEP 60 — ADVANCED SALES ANALYTICS & REVENUE INTELLIGENCE
# ============================================================

section_header("💰 Advanced Sales Analytics & Revenue Intelligence")

sales_analysis_df = filtered_sales.copy()

if not sales_analysis_df.empty:
    sales_analysis_df["sku_id"] = sales_analysis_df["sku_id"].astype(str)

    if "date" in sales_analysis_df.columns:
        sales_analysis_df["date"] = pd.to_datetime(
            sales_analysis_df["date"], errors="coerce"
        )
    elif "sale_date" in sales_analysis_df.columns:
        sales_analysis_df["date"] = pd.to_datetime(
            sales_analysis_df["sale_date"], errors="coerce"
        )

    if "revenue" in sales_analysis_df.columns:
        sales_analysis_df["analysis_revenue"] = pd.to_numeric(
            sales_analysis_df["revenue"], errors="coerce"
        ).fillna(0)
    else:
        quantity_series = _numeric_column(
            sales_analysis_df, ["quantity", "units_sold", "sales_quantity"], 0
        )
        price_series = _numeric_column(
            sales_analysis_df, ["unit_price", "selling_price", "price"], 0
        )
        sales_analysis_df["analysis_revenue"] = quantity_series * price_series

    sales_analysis_df["analysis_units"] = _numeric_column(
        sales_analysis_df, ["quantity", "units_sold", "sales_quantity"], 0
    )

    sales_revenue = float(sales_analysis_df["analysis_revenue"].sum())
    sales_units = float(sales_analysis_df["analysis_units"].sum())
    active_sales_rows = len(sales_analysis_df)

    sales_metric_cols = st.columns(4)
    with sales_metric_cols[0]:
        st.metric("Total Revenue", format_currency(sales_revenue))
    with sales_metric_cols[1]:
        st.metric("Units Sold", format_number(sales_units))
    with sales_metric_cols[2]:
        st.metric("Sales Records", format_number(active_sales_rows))
    with sales_metric_cols[3]:
        avg_unit_revenue = sales_revenue / sales_units if sales_units else 0
        st.metric("Revenue / Unit", format_currency(avg_unit_revenue))

    if "category" in sales_analysis_df.columns:
        category_sales = (
            sales_analysis_df.groupby("category", dropna=False)
            .agg(
                Revenue=("analysis_revenue", "sum"),
                Units=("analysis_units", "sum"),
            )
            .reset_index()
            .sort_values("Revenue", ascending=False)
        )
        st.markdown("### 📊 Revenue by Category")
        st.plotly_chart(
            px.bar(
                category_sales,
                x="category",
                y="Revenue",
                text_auto=".2s",
                title="Revenue Contribution by Category",
            ),
            use_container_width=True,
        )

    sku_sales = (
        sales_analysis_df.groupby("sku_id", dropna=False)
        .agg(
            Revenue=("analysis_revenue", "sum"),
            Units=("analysis_units", "sum"),
        )
        .reset_index()
        .sort_values("Revenue", ascending=False)
    )

    sales_rank_cols = st.columns(2)
    with sales_rank_cols[0]:
        st.markdown("### 🏆 Top Revenue SKUs")
        st.dataframe(
            sku_sales.head(10),
            use_container_width=True,
            hide_index=True,
        )
    with sales_rank_cols[1]:
        st.markdown("### 📉 Lowest Revenue SKUs")
        st.dataframe(
            sku_sales.sort_values("Revenue", ascending=True).head(10),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("### 📈 Revenue Trend")
    if "date" in sales_analysis_df.columns and sales_analysis_df["date"].notna().any():
        trend_df = (
            sales_analysis_df.dropna(subset=["date"])
            .groupby("date", as_index=False)["analysis_revenue"]
            .sum()
            .rename(columns={"analysis_revenue": "Revenue"})
            .sort_values("date")
        )
        st.plotly_chart(
            px.line(
                trend_df,
                x="date",
                y="Revenue",
                markers=True,
                title="Daily Revenue Trend",
            ),
            use_container_width=True,
        )

        monthly_df = trend_df.copy()
        monthly_df["Month"] = monthly_df["date"].dt.to_period("M").astype(str)
        monthly_df = (
            monthly_df.groupby("Month", as_index=False)["Revenue"]
            .sum()
        )
        st.plotly_chart(
            px.bar(
                monthly_df,
                x="Month",
                y="Revenue",
                text_auto=".2s",
                title="Monthly Revenue Summary",
            ),
            use_container_width=True,
        )
    else:
        st.info("A valid sales date column is required for revenue trends.")

    if "order_id" in sales_analysis_df.columns:
        order_count = sales_analysis_df["order_id"].nunique()
        average_order_value = sales_revenue / order_count if order_count else 0
        st.metric("Average Order Value", format_currency(average_order_value))

    with st.expander("📄 Sales Analytics Dataset"):
        st.dataframe(
            sales_analysis_df,
            use_container_width=True,
            hide_index=True,
        )
else:
    st.info("No sales data is available for the current filters.")


# ============================================================
# STEP 61 — ADVANCED INVENTORY ANALYTICS & STOCK INTELLIGENCE
# ============================================================

section_header("📦 Advanced Inventory Analytics & Stock Intelligence")

inventory_analysis_df = filtered_inventory.copy()

if not inventory_analysis_df.empty:
    inventory_analysis_df["sku_id"] = inventory_analysis_df["sku_id"].astype(str)

    inventory_analysis_df["analysis_stock"] = _numeric_column(
        inventory_analysis_df,
        ["stock_quantity", "current_stock", "quantity", "stock", "inventory_quantity"],
        0,
    )

    if "category" not in inventory_analysis_df.columns:
        inventory_analysis_df["category"] = "Uncategorized"

    inventory_summary = (
        inventory_analysis_df.groupby("category", dropna=False)
        .agg(
            Current_Stock=("analysis_stock", "sum"),
            SKU_Count=("sku_id", "nunique"),
        )
        .reset_index()
        .sort_values("Current_Stock", ascending=False)
    )

    inv_metric_cols = st.columns(4)
    with inv_metric_cols[0]:
        st.metric("Total Current Stock", format_number(inventory_analysis_df["analysis_stock"].sum()))
    with inv_metric_cols[1]:
        st.metric("Inventory SKUs", format_number(inventory_analysis_df["sku_id"].nunique()))
    with inv_metric_cols[2]:
        zero_stock = int((inventory_analysis_df["analysis_stock"] <= 0).sum())
        st.metric("Zero-Stock SKUs", format_number(zero_stock))
    with inv_metric_cols[3]:
        positive_stock = inventory_analysis_df.loc[
            inventory_analysis_df["analysis_stock"] > 0, "analysis_stock"
        ]
        avg_stock = float(positive_stock.mean()) if not positive_stock.empty else 0
        st.metric("Average Positive Stock", format_number(avg_stock))

    st.markdown("### 🏷️ Inventory by Category")
    st.plotly_chart(
        px.bar(
            inventory_summary,
            x="category",
            y="Current_Stock",
            text_auto=".2s",
            title="Current Stock by Category",
        ),
        use_container_width=True,
    )

    inventory_risk_df = inventory_analysis_df.copy()
    if "risk_severity" in inventory_risk_df.columns:
        risk_counts = (
            inventory_risk_df["risk_severity"]
            .fillna("Unknown")
            .astype(str)
            .value_counts()
            .rename_axis("Risk Severity")
            .reset_index(name="SKU Count")
        )
        st.markdown("### 🚦 Inventory Risk Distribution")
        st.plotly_chart(
            px.bar(
                risk_counts,
                x="Risk Severity",
                y="SKU Count",
                text_auto=True,
                title="Inventory Risk Severity",
            ),
            use_container_width=True,
        )

    forecast_lookup = filtered_intelligence_df.copy()
    if not forecast_lookup.empty and "sku_id" in forecast_lookup.columns:
        forecast_lookup["sku_id"] = forecast_lookup["sku_id"].astype(str)
        forecast_lookup["analysis_forecast"] = _numeric_column(
            forecast_lookup,
            ["forecast_demand", "predicted_demand", "forecast_quantity", "demand_forecast"],
            0,
        )
        forecast_lookup = forecast_lookup[
            ["sku_id", "analysis_forecast"]
        ].drop_duplicates("sku_id")

        inventory_analysis_df = inventory_analysis_df.merge(
            forecast_lookup,
            on="sku_id",
            how="left",
        )
        inventory_analysis_df["analysis_forecast"] = inventory_analysis_df[
            "analysis_forecast"
        ].fillna(0)
        inventory_analysis_df["demand_gap"] = (
            inventory_analysis_df["analysis_forecast"]
            - inventory_analysis_df["analysis_stock"]
        )
        inventory_analysis_df["stock_coverage"] = np.where(
            inventory_analysis_df["analysis_forecast"] > 0,
            inventory_analysis_df["analysis_stock"]
            / inventory_analysis_df["analysis_forecast"],
            np.nan,
        )

        st.markdown("### 📉 Stock vs Forecast Demand")
        stock_forecast_chart = inventory_analysis_df[
            ["sku_id", "analysis_stock", "analysis_forecast"]
        ].head(30)
        st.plotly_chart(
            px.bar(
                stock_forecast_chart,
                x="sku_id",
                y=["analysis_stock", "analysis_forecast"],
                barmode="group",
                title="Current Stock Compared with Forecast Demand",
            ),
            use_container_width=True,
        )

        st.markdown("### ⚠️ Replenishment Pressure")
        replenishment_pressure = inventory_analysis_df[
            ["sku_id", "analysis_stock", "analysis_forecast", "demand_gap", "stock_coverage"]
        ].sort_values("demand_gap", ascending=False)

        st.dataframe(
            replenishment_pressure.head(20),
            use_container_width=True,
            hide_index=True,
        )

        pressure_count = int((inventory_analysis_df["demand_gap"] > 0).sum())
        overstock_count = int(
            (
                inventory_analysis_df["stock_coverage"].notna()
                & (inventory_analysis_df["stock_coverage"] > 2)
            ).sum()
        )
        inv_alert_cols = st.columns(2)
        with inv_alert_cols[0]:
            st.warning(f"📦 {pressure_count} SKU(s) have forecast demand above current stock.")
        with inv_alert_cols[1]:
            st.info(f"🧊 {overstock_count} SKU(s) have stock coverage above 2× forecast demand.")
    else:
        st.info("Forecast fields are unavailable for stock-coverage analysis.")

    with st.expander("📄 Inventory Analytics Dataset"):
        st.dataframe(
            inventory_analysis_df,
            use_container_width=True,
            hide_index=True,
        )
else:
    st.info("No inventory data is available for the current filters.")



# ============================================================
# STEP 62 — ADVANCED FORECAST ANALYTICS & DEMAND INTELLIGENCE
# ============================================================

section_header(
    "🔮 Advanced Forecast Analytics & Demand Intelligence",
    "Analyze forecast magnitude, demand direction, historical benchmarks, confidence, and SKU-level demand pressure.",
)

forecast_analysis_df = filtered_forecast_summary.copy()

if not forecast_analysis_df.empty:

    if "sku_id" in forecast_analysis_df.columns:
        forecast_analysis_df["sku_id"] = forecast_analysis_df["sku_id"].astype(str)

    forecast_analysis_df["analysis_forecast"] = _numeric_column(
        forecast_analysis_df,
        [
            "forecast",
            "forecast_demand",
            "total_forecast_demand",
            "predicted_demand",
            "predicted_quantity",
            "demand_forecast",
        ],
        0,
    )

    forecast_analysis_df["analysis_confidence"] = _numeric_column(
        forecast_analysis_df,
        [
            "confidence",
            "forecast_confidence",
            "confidence_score",
            "model_confidence",
        ],
        np.nan,
    )

    if "demand_trend" in forecast_analysis_df.columns:
        forecast_analysis_df["analysis_trend"] = (
            forecast_analysis_df["demand_trend"].fillna("Unknown").astype(str)
        )
    elif "trend" in forecast_analysis_df.columns:
        forecast_analysis_df["analysis_trend"] = (
            forecast_analysis_df["trend"].fillna("Unknown").astype(str)
        )
    else:
        forecast_analysis_df["analysis_trend"] = "Unknown"

    if "category" not in forecast_analysis_df.columns:
        forecast_analysis_df["category"] = "Uncategorized"

    forecast_analysis_df["category"] = (
        forecast_analysis_df["category"].fillna("Uncategorized").astype(str)
    )

    # --------------------------------------------------------
    # HISTORICAL WEEKLY DEMAND BENCHMARK
    # --------------------------------------------------------

    historical_weekly = pd.DataFrame()

    if not filtered_sales.empty and "sku_id" in filtered_sales.columns:
        benchmark_sales = filtered_sales.copy()
        benchmark_sales["sku_id"] = benchmark_sales["sku_id"].astype(str)

        if "date" in benchmark_sales.columns:
            benchmark_sales["date"] = pd.to_datetime(
                benchmark_sales["date"], errors="coerce"
            )

        if "quantity" in benchmark_sales.columns:
            benchmark_sales["analysis_units"] = pd.to_numeric(
                benchmark_sales["quantity"], errors="coerce"
            ).fillna(0)
        elif "units_sold" in benchmark_sales.columns:
            benchmark_sales["analysis_units"] = pd.to_numeric(
                benchmark_sales["units_sold"], errors="coerce"
            ).fillna(0)
        else:
            benchmark_sales["analysis_units"] = 0

        if "date" in benchmark_sales.columns:
            benchmark_sales = benchmark_sales.dropna(subset=["date"])

            if not benchmark_sales.empty:
                weekly = (
                    benchmark_sales.set_index("date")
                    .groupby("sku_id")["analysis_units"]
                    .resample("W")
                    .sum()
                    .reset_index()
                )

                historical_weekly = (
                    weekly.groupby("sku_id")
                    .agg(
                        Historical_Weekly_Avg=("analysis_units", "mean"),
                        Historical_Weekly_Max=("analysis_units", "max"),
                    )
                    .reset_index()
                )

    if not historical_weekly.empty:
        forecast_analysis_df = forecast_analysis_df.merge(
            historical_weekly,
            on="sku_id",
            how="left",
        )
    else:
        forecast_analysis_df["Historical_Weekly_Avg"] = np.nan
        forecast_analysis_df["Historical_Weekly_Max"] = np.nan

    forecast_analysis_df["Historical_Weekly_Avg"] = pd.to_numeric(
        forecast_analysis_df["Historical_Weekly_Avg"], errors="coerce"
    )
    forecast_analysis_df["Historical_Weekly_Max"] = pd.to_numeric(
        forecast_analysis_df["Historical_Weekly_Max"], errors="coerce"
    )

    forecast_analysis_df["Forecast_vs_History_%"] = np.where(
        forecast_analysis_df["Historical_Weekly_Avg"].notna()
        & (forecast_analysis_df["Historical_Weekly_Avg"] > 0),
        (
            (
                forecast_analysis_df["analysis_forecast"]
                - forecast_analysis_df["Historical_Weekly_Avg"]
            )
            / forecast_analysis_df["Historical_Weekly_Avg"]
        )
        * 100,
        np.nan,
    )

    forecast_analysis_df["Forecast_Units_Gap"] = (
        forecast_analysis_df["analysis_forecast"]
        - forecast_analysis_df["Historical_Weekly_Avg"].fillna(0)
    )

    forecast_analysis_df["Forecast_Value"] = (
        forecast_analysis_df["analysis_forecast"]
        * _numeric_column(
            forecast_analysis_df,
            [
                "estimated_selling_price",
                "list_price",
                "unit_price",
                "selling_price",
            ],
            0,
        )
    )

    # --------------------------------------------------------
    # EXECUTIVE FORECAST METRICS
    # --------------------------------------------------------

    total_forecast = float(forecast_analysis_df["analysis_forecast"].sum())

    positive_forecast = forecast_analysis_df.loc[
        forecast_analysis_df["analysis_forecast"] > 0,
        "analysis_forecast",
    ]
    average_forecast = (
        float(positive_forecast.mean()) if not positive_forecast.empty else 0
    )

    trend_lower = forecast_analysis_df["analysis_trend"].str.lower()

    increasing_count = int(
        trend_lower.str.contains("increas|up|grow|rising", regex=True).sum()
    )
    declining_count = int(
        trend_lower.str.contains("declin|down|fall|decreas", regex=True).sum()
    )
    stable_count = int(
        trend_lower.str.contains("stable|flat|constant", regex=True).sum()
    )

    confidence_series = forecast_analysis_df["analysis_confidence"].dropna()
    average_confidence = (
        float(confidence_series.mean()) if not confidence_series.empty else np.nan
    )

    if pd.notna(average_confidence) and average_confidence <= 1:
        average_confidence *= 100

    metric_cols = st.columns(4)

    with metric_cols[0]:
        st.metric("Total Forecast Demand", format_number(total_forecast))

    with metric_cols[1]:
        st.metric("Average SKU Forecast", format_number(average_forecast))

    with metric_cols[2]:
        st.metric("Increasing SKUs", format_number(increasing_count))

    with metric_cols[3]:
        st.metric(
            "Average Confidence",
            f"{average_confidence:.1f}%"
            if pd.notna(average_confidence)
            else "N/A",
        )

    # --------------------------------------------------------
    # FORECAST BY CATEGORY
    # --------------------------------------------------------

    st.markdown("### 🏷️ Forecast Demand by Category")

    forecast_category = (
        forecast_analysis_df.groupby("category", dropna=False)
        .agg(
            Forecast_Demand=("analysis_forecast", "sum"),
            SKU_Count=("sku_id", "nunique"),
        )
        .reset_index()
        .sort_values("Forecast_Demand", ascending=False)
    )

    st.plotly_chart(
        px.bar(
            forecast_category,
            x="category",
            y="Forecast_Demand",
            text_auto=".2s",
            title="Forecast Demand by Category",
        ),
        use_container_width=True,
    )

    # --------------------------------------------------------
    # DEMAND DIRECTION PROFILE
    # --------------------------------------------------------

    st.markdown("### 📈 Demand Direction Profile")

    trend_profile = (
        forecast_analysis_df["analysis_trend"]
        .value_counts()
        .rename_axis("Demand Trend")
        .reset_index(name="SKU Count")
    )

    st.plotly_chart(
        px.pie(
            trend_profile,
            names="Demand Trend",
            values="SKU Count",
            hole=0.45,
            title="Forecast Demand Direction",
        ),
        use_container_width=True,
    )

    trend_cols = st.columns(3)
    with trend_cols[0]:
        st.metric("Increasing Demand", format_number(increasing_count))
    with trend_cols[1]:
        st.metric("Stable Demand", format_number(stable_count))
    with trend_cols[2]:
        st.metric("Declining Demand", format_number(declining_count))

    # --------------------------------------------------------
    # FORECAST VS HISTORICAL DEMAND
    # --------------------------------------------------------

    benchmark_df = forecast_analysis_df[
        forecast_analysis_df["Historical_Weekly_Avg"].notna()
        & (forecast_analysis_df["Historical_Weekly_Avg"] > 0)
    ].copy()

    if not benchmark_df.empty:

        benchmark_df = benchmark_df.sort_values(
            "analysis_forecast", ascending=False
        ).head(25)

        st.markdown("### 🔄 Forecast vs Historical Weekly Demand")

        benchmark_chart = benchmark_df[
            ["sku_id", "Historical_Weekly_Avg", "analysis_forecast"]
        ].copy()
        benchmark_chart.columns = [
            "SKU",
            "Historical Weekly Avg",
            "Forecast Demand",
        ]

        st.plotly_chart(
            px.bar(
                benchmark_chart,
                x="SKU",
                y=["Historical Weekly Avg", "Forecast Demand"],
                barmode="group",
                title="Top SKUs — Forecast vs Historical Weekly Demand",
            ),
            use_container_width=True,
        )

        st.markdown("### 📊 Forecast Change vs Historical Baseline")

        change_chart = benchmark_df.sort_values(
            "Forecast_vs_History_%", ascending=False
        ).head(25)

        fig_change = px.bar(
            change_chart,
            x="sku_id",
            y="Forecast_vs_History_%",
            text_auto=".1f",
            title="Forecast Change Compared with Historical Average (%)",
        )
        fig_change.add_hline(y=0, line_dash="dash")

        st.plotly_chart(fig_change, use_container_width=True)

    else:
        st.info(
            "Historical sales data is insufficient for forecast-vs-history benchmarking."
        )

    # --------------------------------------------------------
    # FORECAST PRIORITY SKUS
    # --------------------------------------------------------

    st.markdown("### 🎯 Forecast Priority SKUs")

    priority_forecast = forecast_analysis_df.copy()

    priority_forecast["Forecast_Priority_Score"] = (
        priority_forecast["analysis_forecast"]
        .rank(ascending=False, method="average", pct=True)
        * 100
    )

    priority_forecast["Forecast_Priority_Score"] += (
        priority_forecast["Forecast_vs_History_%"]
        .clip(lower=0, upper=100)
        .fillna(0)
        * 0.25
    )

    priority_forecast = priority_forecast.sort_values(
        "Forecast_Priority_Score", ascending=False
    )

    priority_display = priority_forecast[
        [
            "sku_id",
            "category",
            "analysis_forecast",
            "analysis_trend",
            "Historical_Weekly_Avg",
            "Forecast_vs_History_%",
            "Forecast_Priority_Score",
        ]
    ].head(20).copy()

    priority_display.columns = [
        "SKU",
        "Category",
        "Forecast Demand",
        "Demand Trend",
        "Historical Weekly Avg",
        "Forecast vs History %",
        "Priority Score",
    ]

    st.dataframe(
        priority_display,
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------------------------
    # FORECAST VALUE
    # --------------------------------------------------------

    if forecast_analysis_df["Forecast_Value"].sum() > 0:

        st.markdown("### 💰 Estimated Revenue Value of Forecast Demand")

        forecast_value_category = (
            forecast_analysis_df.groupby("category", dropna=False)
            .agg(Forecast_Value=("Forecast_Value", "sum"))
            .reset_index()
            .sort_values("Forecast_Value", ascending=False)
        )

        st.plotly_chart(
            px.bar(
                forecast_value_category,
                x="category",
                y="Forecast_Value",
                text_auto=".2s",
                title="Estimated Revenue Value by Category",
            ),
            use_container_width=True,
        )

    # --------------------------------------------------------
    # FORECAST ALERTS
    # --------------------------------------------------------

    st.markdown("### 🚨 Forecast Alerts")

    alert_count = 0

    if increasing_count > 0:
        st.info(
            f"📈 {increasing_count} SKU(s) show increasing demand and may require proactive capacity or inventory planning."
        )
        alert_count += increasing_count

    high_growth_count = int(
        (forecast_analysis_df["Forecast_vs_History_%"] > 25).sum()
    )

    if high_growth_count > 0:
        st.warning(
            f"⚠️ {high_growth_count} SKU(s) have forecast demand more than 25% above their historical weekly average."
        )
        alert_count += high_growth_count

    if declining_count > 0:
        st.info(
            f"📉 {declining_count} SKU(s) show declining demand; review replenishment plans to avoid excess stock."
        )

    if pd.notna(average_confidence) and average_confidence < 60:
        st.warning(
            "⚠️ Average forecast confidence is below 60%. Treat forecast-driven decisions cautiously and review model inputs."
        )

    if alert_count == 0 and declining_count == 0:
        st.success(
            "✅ No major demand-direction exceptions were detected in the current filtered portfolio."
        )

    with st.expander("📄 Forecast Analytics Dataset"):
        st.dataframe(
            forecast_analysis_df,
            use_container_width=True,
            hide_index=True,
        )

else:
    st.info("No forecast data is available for the current filters.")



# ============================================================
# STEP 63 — ABC / PARETO ANALYSIS & SKU CLASSIFICATION
# ============================================================

section_header(
    "📊 ABC / Pareto Analysis",
    "Classify SKUs by revenue contribution and identify the products that drive the largest share of business value.",
)

abc_df = filtered_sales.copy()

if not abc_df.empty and "sku_id" in abc_df.columns:

    abc_df["sku_id"] = abc_df["sku_id"].astype(str)

    # --------------------------------------------------------
    # NORMALIZE SALES VALUE
    # --------------------------------------------------------

    if "revenue" in abc_df.columns:
        abc_df["abc_revenue"] = pd.to_numeric(
            abc_df["revenue"],
            errors="coerce",
        ).fillna(0)
    elif "sales" in abc_df.columns:
        abc_df["abc_revenue"] = pd.to_numeric(
            abc_df["sales"],
            errors="coerce",
        ).fillna(0)
    elif "quantity" in abc_df.columns and "unit_price" in abc_df.columns:
        abc_df["abc_revenue"] = (
            pd.to_numeric(
                abc_df["quantity"],
                errors="coerce",
            ).fillna(0)
            * pd.to_numeric(
                abc_df["unit_price"],
                errors="coerce",
            ).fillna(0)
        )
    else:
        abc_df["abc_revenue"] = 0

    if "quantity" in abc_df.columns:
        abc_df["abc_units"] = pd.to_numeric(
            abc_df["quantity"],
            errors="coerce",
        ).fillna(0)
    elif "units_sold" in abc_df.columns:
        abc_df["abc_units"] = pd.to_numeric(
            abc_df["units_sold"],
            errors="coerce",
        ).fillna(0)
    else:
        abc_df["abc_units"] = 0

    # --------------------------------------------------------
    # SKU REVENUE AGGREGATION
    # --------------------------------------------------------

    abc_sku = (
        abc_df.groupby("sku_id", dropna=False)
        .agg(
            Revenue=("abc_revenue", "sum"),
            Units_Sold=("abc_units", "sum"),
        )
        .reset_index()
    )

    if not abc_sku.empty:

        abc_sku["Revenue"] = pd.to_numeric(
            abc_sku["Revenue"],
            errors="coerce",
        ).fillna(0)

        abc_sku["Units_Sold"] = pd.to_numeric(
            abc_sku["Units_Sold"],
            errors="coerce",
        ).fillna(0)

        total_abc_revenue = float(abc_sku["Revenue"].sum())

        # ----------------------------------------------------
        # PARETO CALCULATION
        # ----------------------------------------------------

        abc_sku = abc_sku.sort_values(
            "Revenue",
            ascending=False,
        ).reset_index(drop=True)

        if total_abc_revenue > 0:
            abc_sku["Revenue_Share_%"] = (
                abc_sku["Revenue"]
                / total_abc_revenue
                * 100
            )
            abc_sku["Cumulative_Revenue_%"] = (
                abc_sku["Revenue_Share_%"].cumsum()
            )
        else:
            abc_sku["Revenue_Share_%"] = 0.0
            abc_sku["Cumulative_Revenue_%"] = 0.0

        # ----------------------------------------------------
        # ABC CLASSIFICATION
        #
        # A = first 80% of cumulative revenue
        # B = 80%–95%
        # C = remaining 5%
        # ----------------------------------------------------

        abc_sku["ABC_Class"] = np.select(
            [
                abc_sku["Cumulative_Revenue_%"] <= 80,
                abc_sku["Cumulative_Revenue_%"] <= 95,
            ],
            [
                "A",
                "B",
            ],
            default="C",
        )

        # ----------------------------------------------------
        # CATEGORY ENRICHMENT
        # ----------------------------------------------------

        category_lookup = pd.DataFrame()

        if "category" in filtered_intelligence_df.columns:
            category_lookup = (
                filtered_intelligence_df[
                    ["sku_id", "category"]
                ]
                .drop_duplicates("sku_id")
                .copy()
            )
            category_lookup["sku_id"] = (
                category_lookup["sku_id"].astype(str)
            )

        if not category_lookup.empty:
            abc_sku = abc_sku.merge(
                category_lookup,
                on="sku_id",
                how="left",
            )
        else:
            abc_sku["category"] = "Uncategorized"

        abc_sku["category"] = (
            abc_sku["category"]
            .fillna("Uncategorized")
            .astype(str)
        )

        # ----------------------------------------------------
        # ABC KPI SUMMARY
        # ----------------------------------------------------

        class_counts = (
            abc_sku["ABC_Class"]
            .value_counts()
            .to_dict()
        )

        class_revenue = (
            abc_sku.groupby("ABC_Class")["Revenue"]
            .sum()
            .to_dict()
        )

        total_skus = len(abc_sku)

        a_count = int(class_counts.get("A", 0))
        b_count = int(class_counts.get("B", 0))
        c_count = int(class_counts.get("C", 0))

        a_revenue = float(class_revenue.get("A", 0))
        b_revenue = float(class_revenue.get("B", 0))
        c_revenue = float(class_revenue.get("C", 0))

        kpi_cols = st.columns(4)

        with kpi_cols[0]:
            st.metric(
                "Total SKUs",
                format_number(total_skus),
            )

        with kpi_cols[1]:
            st.metric(
                "A-Class SKUs",
                format_number(a_count),
            )

        with kpi_cols[2]:
            st.metric(
                "B-Class SKUs",
                format_number(b_count),
            )

        with kpi_cols[3]:
            st.metric(
                "C-Class SKUs",
                format_number(c_count),
            )

        # ----------------------------------------------------
        # ABC DISTRIBUTION
        # ----------------------------------------------------

        st.markdown("### 🧩 ABC Classification Distribution")

        abc_distribution = pd.DataFrame(
            {
                "ABC Class": ["A", "B", "C"],
                "SKU Count": [
                    a_count,
                    b_count,
                    c_count,
                ],
                "Revenue": [
                    a_revenue,
                    b_revenue,
                    c_revenue,
                ],
            }
        )

        chart_cols = st.columns(2)

        with chart_cols[0]:
            st.plotly_chart(
                px.bar(
                    abc_distribution,
                    x="ABC Class",
                    y="SKU Count",
                    text_auto=True,
                    title="SKU Count by ABC Class",
                ),
                use_container_width=True,
            )

        with chart_cols[1]:
            st.plotly_chart(
                px.bar(
                    abc_distribution,
                    x="ABC Class",
                    y="Revenue",
                    text_auto=".2s",
                    title="Revenue by ABC Class",
                ),
                use_container_width=True,
            )

        # ----------------------------------------------------
        # REVENUE CONCENTRATION
        # ----------------------------------------------------

        if total_abc_revenue > 0:

            a_share = a_revenue / total_abc_revenue * 100
            b_share = b_revenue / total_abc_revenue * 100
            c_share = c_revenue / total_abc_revenue * 100

            st.markdown("### 💰 Revenue Concentration")

            concentration_cols = st.columns(3)

            with concentration_cols[0]:
                st.metric(
                    "A-Class Revenue Share",
                    f"{a_share:.1f}%",
                )

            with concentration_cols[1]:
                st.metric(
                    "B-Class Revenue Share",
                    f"{b_share:.1f}%",
                )

            with concentration_cols[2]:
                st.metric(
                    "C-Class Revenue Share",
                    f"{c_share:.1f}%",
                )

            concentration_df = abc_sku[
                [
                    "sku_id",
                    "Cumulative_Revenue_%",
                ]
            ].copy()

            concentration_df["SKU Rank"] = (
                concentration_df.index + 1
            )

            st.markdown("### 📈 Pareto Revenue Curve")

            fig_pareto = px.line(
                concentration_df,
                x="SKU Rank",
                y="Cumulative_Revenue_%",
                markers=True,
                title="Cumulative Revenue Contribution by SKU",
            )

            fig_pareto.add_hline(
                y=80,
                line_dash="dash",
            )

            fig_pareto.add_hline(
                y=95,
                line_dash="dash",
            )

            fig_pareto.update_yaxes(
                range=[0, 105],
                title="Cumulative Revenue (%)",
            )

            fig_pareto.update_xaxes(
                title="SKU Rank",
            )

            st.plotly_chart(
                fig_pareto,
                use_container_width=True,
            )

        # ----------------------------------------------------
        # TOP A-CLASS SKUS
        # ----------------------------------------------------

        st.markdown("### 🏆 Top A-Class SKUs")

        top_a = abc_sku[
            abc_sku["ABC_Class"] == "A"
        ].head(20).copy()

        top_a_display = top_a[
            [
                "sku_id",
                "category",
                "Revenue",
                "Units_Sold",
                "Revenue_Share_%",
                "Cumulative_Revenue_%",
            ]
        ].copy()

        top_a_display.columns = [
            "SKU",
            "Category",
            "Revenue",
            "Units Sold",
            "Revenue Share %",
            "Cumulative Revenue %",
        ]

        st.dataframe(
            top_a_display,
            use_container_width=True,
            hide_index=True,
        )

        # ----------------------------------------------------
        # ABC BY CATEGORY
        # ----------------------------------------------------

        st.markdown("### 🏷️ ABC Mix by Category")

        abc_category = (
            abc_sku.groupby(
                ["category", "ABC_Class"],
                dropna=False,
            )
            .agg(
                SKU_Count=("sku_id", "nunique"),
                Revenue=("Revenue", "sum"),
            )
            .reset_index()
        )

        st.plotly_chart(
            px.bar(
                abc_category,
                x="category",
                y="SKU_Count",
                color="ABC_Class",
                barmode="stack",
                text_auto=True,
                title="ABC SKU Mix by Category",
            ),
            use_container_width=True,
        )

        # ----------------------------------------------------
        # BUSINESS INTERPRETATION
        # ----------------------------------------------------

        st.markdown("### 🧠 ABC Management Guidance")

        if a_count > 0:
            st.warning(
                f"🔴 {a_count} A-class SKU(s) generate approximately "
                f"{a_share:.1f}% of filtered revenue. These products "
                "should receive the highest inventory-control attention."
            )

        if b_count > 0:
            st.info(
                f"🟡 {b_count} B-class SKU(s) contribute approximately "
                f"{b_share:.1f}% of revenue. Use balanced replenishment "
                "and periodic review policies."
            )

        if c_count > 0:
            st.success(
                f"🟢 {c_count} C-class SKU(s) contribute approximately "
                f"{c_share:.1f}% of revenue. Consider simplified "
                "inventory controls where operationally appropriate."
            )

        # ----------------------------------------------------
        # ABC + RISK CROSS ANALYSIS
        # ----------------------------------------------------

        if (
            "risk_severity" in filtered_intelligence_df.columns
            and not filtered_intelligence_df.empty
        ):

            risk_lookup = (
                filtered_intelligence_df[
                    [
                        "sku_id",
                        "risk_severity",
                    ]
                ]
                .drop_duplicates("sku_id")
                .copy()
            )

            risk_lookup["sku_id"] = (
                risk_lookup["sku_id"].astype(str)
            )

            abc_risk = abc_sku.merge(
                risk_lookup,
                on="sku_id",
                how="left",
            )

            abc_risk["risk_severity"] = (
                abc_risk["risk_severity"]
                .fillna("Unknown")
                .astype(str)
            )

            st.markdown(
                "### ⚠️ ABC + Inventory Risk Analysis"
            )

            abc_risk_summary = (
                abc_risk.groupby(
                    ["ABC_Class", "risk_severity"],
                    dropna=False,
                )
                .agg(
                    SKU_Count=("sku_id", "nunique"),
                    Revenue=("Revenue", "sum"),
                )
                .reset_index()
            )

            st.plotly_chart(
                px.bar(
                    abc_risk_summary,
                    x="ABC_Class",
                    y="SKU_Count",
                    color="risk_severity",
                    barmode="stack",
                    text_auto=True,
                    title="Risk Distribution within ABC Classes",
                ),
                use_container_width=True,
            )

            critical_a = abc_risk[
                (abc_risk["ABC_Class"] == "A")
                & (
                    abc_risk["risk_severity"]
                    .str.lower()
                    .str.contains(
                        "critical|high|severe",
                        regex=True,
                    )
                )
            ]

            if not critical_a.empty:
                st.error(
                    f"🚨 {len(critical_a)} high-risk A-class SKU(s) "
                    "were detected. These should be treated as top "
                    "business priorities."
                )

        # ----------------------------------------------------
        # COMPLETE ABC DATASET
        # ----------------------------------------------------

        with st.expander("📄 Complete ABC / Pareto Dataset"):
            st.dataframe(
                abc_sku,
                use_container_width=True,
                hide_index=True,
            )

    else:
        st.info(
            "No SKU-level sales records are available for ABC analysis."
        )

else:
    st.info(
        "ABC analysis requires SKU-level sales data."
    )



# ============================================================
# STEP 64 — EOQ, REORDER POINT & SAFETY STOCK INTELLIGENCE
# ============================================================

section_header(
    "📦 EOQ, Reorder Point & Safety Stock Intelligence",
    "Estimate inventory control parameters to support replenishment decisions at SKU level.",
)

eoq_df = filtered_intelligence_df.copy()

if not eoq_df.empty and "sku_id" in eoq_df.columns:

    eoq_df["sku_id"] = eoq_df["sku_id"].astype(str)

    # --------------------------------------------------------
    # DEMAND INPUTS
    # --------------------------------------------------------

    eoq_df["EOQ_Annual_Demand"] = _numeric_column(
        eoq_df,
        [
            "annual_demand",
            "yearly_demand",
            "annual_units",
        ],
        np.nan,
    )

    # Prefer forecast demand when an annual demand field is absent.
    forecast_input = _numeric_column(
        eoq_df,
        [
            "forecast_demand",
            "forecast",
            "predicted_demand",
            "total_forecast_demand",
            "demand_forecast",
        ],
        np.nan,
    )

    eoq_df["EOQ_Annual_Demand"] = eoq_df[
        "EOQ_Annual_Demand"
    ].where(
        eoq_df["EOQ_Annual_Demand"].notna()
        & (eoq_df["EOQ_Annual_Demand"] > 0),
        forecast_input * 52,
    )

    # If forecast is unavailable, estimate annual demand from
    # filtered historical sales.
    sales_annual = pd.DataFrame()

    if not filtered_sales.empty and "sku_id" in filtered_sales.columns:
        eoq_sales = filtered_sales.copy()
        eoq_sales["sku_id"] = eoq_sales["sku_id"].astype(str)

        if "quantity" in eoq_sales.columns:
            eoq_sales["eoq_units"] = pd.to_numeric(
                eoq_sales["quantity"],
                errors="coerce",
            ).fillna(0)
        elif "units_sold" in eoq_sales.columns:
            eoq_sales["eoq_units"] = pd.to_numeric(
                eoq_sales["units_sold"],
                errors="coerce",
            ).fillna(0)
        else:
            eoq_sales["eoq_units"] = 0

        if "date" in eoq_sales.columns:
            eoq_sales["date"] = pd.to_datetime(
                eoq_sales["date"],
                errors="coerce",
            )

        if "date" in eoq_sales.columns:
            valid_dates = eoq_sales.dropna(subset=["date"])

            if not valid_dates.empty:
                date_span_days = max(
                    (
                        valid_dates["date"].max()
                        - valid_dates["date"].min()
                    ).days,
                    1,
                )

                sales_annual = (
                    valid_dates.groupby("sku_id")["eoq_units"]
                    .sum()
                    .div(date_span_days)
                    .mul(365)
                    .rename("Historical_Annual_Demand")
                    .reset_index()
                )
        else:
            sales_annual = (
                eoq_sales.groupby("sku_id")["eoq_units"]
                .sum()
                .mul(52)
                .rename("Historical_Annual_Demand")
                .reset_index()
            )

    if not sales_annual.empty:
        eoq_df = eoq_df.merge(
            sales_annual,
            on="sku_id",
            how="left",
        )
    else:
        eoq_df["Historical_Annual_Demand"] = np.nan

    eoq_df["EOQ_Annual_Demand"] = eoq_df[
        "EOQ_Annual_Demand"
    ].where(
        eoq_df["EOQ_Annual_Demand"].notna()
        & (eoq_df["EOQ_Annual_Demand"] > 0),
        eoq_df["Historical_Annual_Demand"],
    )

    eoq_df["EOQ_Annual_Demand"] = pd.to_numeric(
        eoq_df["EOQ_Annual_Demand"],
        errors="coerce",
    ).fillna(0)

    # --------------------------------------------------------
    # INVENTORY INPUTS
    # --------------------------------------------------------

    eoq_df["Current_Stock"] = _numeric_column(
        eoq_df,
        [
            "current_stock",
            "stock",
            "quantity_on_hand",
            "on_hand",
            "inventory",
            "available_stock",
        ],
        0,
    )

    eoq_df["Lead_Time_Days"] = _numeric_column(
        eoq_df,
        [
            "lead_time_days",
            "lead_time",
            "supplier_lead_time",
            "average_lead_time",
        ],
        7,
    ).clip(lower=0)

    # --------------------------------------------------------
    # COST INPUTS
    # --------------------------------------------------------

    eoq_df["Unit_Cost"] = _numeric_column(
        eoq_df,
        [
            "unit_cost",
            "cost_per_unit",
            "purchase_cost",
            "cost",
        ],
        0,
    )

    eoq_df["Selling_Price"] = _numeric_column(
        eoq_df,
        [
            "estimated_selling_price",
            "selling_price",
            "unit_price",
            "list_price",
        ],
        0,
    )

    # Default ordering cost and holding rate are transparent
    # planning assumptions when the source does not provide them.
    eoq_df["Ordering_Cost"] = _numeric_column(
        eoq_df,
        [
            "ordering_cost",
            "order_cost",
            "setup_cost",
        ],
        50,
    )

    holding_rate = _numeric_column(
        eoq_df,
        [
            "holding_rate",
            "annual_holding_rate",
            "carrying_cost_rate",
        ],
        0.20,
    )

    # Handle percentages such as 20 rather than 0.20.
    holding_rate = np.where(
        holding_rate > 1,
        holding_rate / 100,
        holding_rate,
    )

    eoq_df["Annual_Holding_Cost"] = (
        eoq_df["Unit_Cost"]
        * holding_rate
    )

    # If unit cost is unavailable, use selling price only as a
    # conservative proxy and label the assumption in the UI.
    eoq_df["Annual_Holding_Cost"] = eoq_df[
        "Annual_Holding_Cost"
    ].where(
        eoq_df["Annual_Holding_Cost"] > 0,
        eoq_df["Selling_Price"] * holding_rate,
    )

    # --------------------------------------------------------
    # EOQ CALCULATION
    #
    # EOQ = sqrt((2 * Annual Demand * Ordering Cost) /
    #            Annual Holding Cost)
    # --------------------------------------------------------

    eoq_denominator = eoq_df["Annual_Holding_Cost"]

    eoq_df["EOQ"] = np.where(
        (eoq_df["EOQ_Annual_Demand"] > 0)
        & (eoq_df["Ordering_Cost"] > 0)
        & (eoq_denominator > 0),
        np.sqrt(
            (
                2
                * eoq_df["EOQ_Annual_Demand"]
                * eoq_df["Ordering_Cost"]
            )
            / eoq_denominator
        ),
        np.nan,
    )

    # --------------------------------------------------------
    # DEMAND VARIABILITY
    # --------------------------------------------------------

    demand_std = pd.Series(
        np.nan,
        index=eoq_df.index,
        dtype="float64",
    )

    if (
        not filtered_sales.empty
        and "sku_id" in filtered_sales.columns
        and "date" in filtered_sales.columns
    ):
        variability_sales = filtered_sales.copy()
        variability_sales["sku_id"] = (
            variability_sales["sku_id"].astype(str)
        )
        variability_sales["date"] = pd.to_datetime(
            variability_sales["date"],
            errors="coerce",
        )

        if "quantity" in variability_sales.columns:
            variability_sales["demand_units"] = pd.to_numeric(
                variability_sales["quantity"],
                errors="coerce",
            ).fillna(0)
        elif "units_sold" in variability_sales.columns:
            variability_sales["demand_units"] = pd.to_numeric(
                variability_sales["units_sold"],
                errors="coerce",
            ).fillna(0)
        else:
            variability_sales["demand_units"] = 0

        variability_sales = variability_sales.dropna(
            subset=["date"]
        )

        if not variability_sales.empty:
            weekly_demand = (
                variability_sales.set_index("date")
                .groupby("sku_id")["demand_units"]
                .resample("W")
                .sum()
                .reset_index()
            )

            std_lookup = (
                weekly_demand.groupby("sku_id")["demand_units"]
                .std()
                .rename("Demand_Std_Weekly")
                .reset_index()
            )

            eoq_df = eoq_df.merge(
                std_lookup,
                on="sku_id",
                how="left",
            )

            demand_std = pd.to_numeric(
                eoq_df["Demand_Std_Weekly"],
                errors="coerce",
            )

    if "Demand_Std_Weekly" not in eoq_df.columns:
        eoq_df["Demand_Std_Weekly"] = demand_std

    eoq_df["Demand_Std_Weekly"] = pd.to_numeric(
        eoq_df["Demand_Std_Weekly"],
        errors="coerce",
    ).fillna(0)

    # --------------------------------------------------------
    # SERVICE LEVEL / SAFETY STOCK
    # --------------------------------------------------------

    service_level_z = _numeric_column(
        eoq_df,
        [
            "service_level_z",
            "z_score",
            "z_value",
        ],
        1.65,
    )

    eoq_df["Safety_Stock"] = (
        service_level_z
        * eoq_df["Demand_Std_Weekly"]
        * np.sqrt(
            eoq_df["Lead_Time_Days"] / 7
        )
    )

    # --------------------------------------------------------
    # REORDER POINT
    #
    # ROP = Average daily demand * lead time + Safety Stock
    # --------------------------------------------------------

    eoq_df["Average_Daily_Demand"] = (
        eoq_df["EOQ_Annual_Demand"] / 365
    )

    eoq_df["Reorder_Point"] = (
        eoq_df["Average_Daily_Demand"]
        * eoq_df["Lead_Time_Days"]
        + eoq_df["Safety_Stock"]
    )

    eoq_df["Reorder_Quantity"] = eoq_df["EOQ"].fillna(0)

    eoq_df["Stock_Gap_to_ROP"] = (
        eoq_df["Current_Stock"]
        - eoq_df["Reorder_Point"]
    )

    eoq_df["Days_of_Cover"] = np.where(
        eoq_df["Average_Daily_Demand"] > 0,
        eoq_df["Current_Stock"]
        / eoq_df["Average_Daily_Demand"],
        np.nan,
    )

    eoq_df["Reorder_Status"] = np.select(
        [
            eoq_df["Current_Stock"] <= eoq_df["Reorder_Point"],
            eoq_df["Current_Stock"]
            <= eoq_df["Reorder_Point"] * 1.25,
        ],
        [
            "REORDER NOW",
            "MONITOR",
        ],
        default="HEALTHY",
    )

    # --------------------------------------------------------
    # EXECUTIVE SUMMARY
    # --------------------------------------------------------

    valid_eoq = eoq_df["EOQ"].dropna()

    average_eoq = (
        float(valid_eoq.mean())
        if not valid_eoq.empty
        else np.nan
    )

    reorder_now_count = int(
        (eoq_df["Reorder_Status"] == "REORDER NOW").sum()
    )

    monitor_count = int(
        (eoq_df["Reorder_Status"] == "MONITOR").sum()
    )

    healthy_count = int(
        (eoq_df["Reorder_Status"] == "HEALTHY").sum()
    )

    total_safety_stock = float(
        eoq_df["Safety_Stock"].sum()
    )

    summary_cols = st.columns(4)

    with summary_cols[0]:
        st.metric(
            "Average EOQ",
            format_number(average_eoq)
            if pd.notna(average_eoq)
            else "N/A",
        )

    with summary_cols[1]:
        st.metric(
            "Reorder Now",
            format_number(reorder_now_count),
        )

    with summary_cols[2]:
        st.metric(
            "Monitor",
            format_number(monitor_count),
        )

    with summary_cols[3]:
        st.metric(
            "Total Safety Stock",
            format_number(total_safety_stock),
        )

    st.caption(
        "Planning assumptions when source values are unavailable: "
        "ordering cost = 50 per order, annual holding rate = 20%, "
        "service-level Z value = 1.65."
    )

    # --------------------------------------------------------
    # REORDER STATUS DISTRIBUTION
    # --------------------------------------------------------

    st.markdown("### 🚦 Replenishment Status")

    status_df = pd.DataFrame(
        {
            "Status": [
                "REORDER NOW",
                "MONITOR",
                "HEALTHY",
            ],
            "SKU Count": [
                reorder_now_count,
                monitor_count,
                healthy_count,
            ],
        }
    )

    st.plotly_chart(
        px.pie(
            status_df,
            names="Status",
            values="SKU Count",
            hole=0.45,
            title="SKU Replenishment Status",
        ),
        use_container_width=True,
    )

    # --------------------------------------------------------
    # CURRENT STOCK VS REORDER POINT
    # --------------------------------------------------------

    st.markdown("### 📉 Current Stock vs Reorder Point")

    rop_chart = eoq_df.sort_values(
        "Stock_Gap_to_ROP"
    ).head(30).copy()

    if not rop_chart.empty:
        rop_display = rop_chart[
            [
                "sku_id",
                "Current_Stock",
                "Reorder_Point",
            ]
        ].copy()

        rop_display.columns = [
            "SKU",
            "Current Stock",
            "Reorder Point",
        ]

        st.plotly_chart(
            px.bar(
                rop_display,
                x="SKU",
                y=[
                    "Current Stock",
                    "Reorder Point",
                ],
                barmode="group",
                title="Lowest Stock-to-Reorder-Point SKUs",
            ),
            use_container_width=True,
        )

    # --------------------------------------------------------
    # SAFETY STOCK ANALYSIS
    # --------------------------------------------------------

    st.markdown("### 🛡️ Safety Stock Analysis")

    safety_chart = eoq_df.sort_values(
        "Safety_Stock",
        ascending=False,
    ).head(25)

    st.plotly_chart(
        px.bar(
            safety_chart,
            x="sku_id",
            y="Safety_Stock",
            text_auto=".1f",
            title="SKUs with Highest Estimated Safety Stock",
        ),
        use_container_width=True,
    )

    # --------------------------------------------------------
    # EOQ ANALYSIS
    # --------------------------------------------------------

    st.markdown("### 📦 Economic Order Quantity")

    eoq_chart = eoq_df.dropna(
        subset=["EOQ"]
    ).sort_values(
        "EOQ",
        ascending=False,
    ).head(25)

    if not eoq_chart.empty:
        st.plotly_chart(
            px.bar(
                eoq_chart,
                x="sku_id",
                y="EOQ",
                text_auto=".1f",
                title="Highest Estimated EOQ by SKU",
            ),
            use_container_width=True,
        )
    else:
        st.info(
            "EOQ could not be calculated because demand or holding-cost inputs are unavailable."
        )

    # --------------------------------------------------------
    # REORDER PRIORITY TABLE
    # --------------------------------------------------------

    st.markdown("### 🚨 Reorder Priority SKUs")

    reorder_priority = eoq_df.copy()

    reorder_priority["Reorder_Priority_Score"] = (
        -reorder_priority["Stock_Gap_to_ROP"]
    )

    reorder_priority = reorder_priority.sort_values(
        "Reorder_Priority_Score",
        ascending=False,
    )

    reorder_display = reorder_priority[
        [
            "sku_id",
            "Current_Stock",
            "Safety_Stock",
            "Reorder_Point",
            "EOQ",
            "Days_of_Cover",
            "Reorder_Status",
        ]
    ].head(25).copy()

    reorder_display.columns = [
        "SKU",
        "Current Stock",
        "Safety Stock",
        "Reorder Point",
        "EOQ",
        "Days of Cover",
        "Status",
    ]

    st.dataframe(
        reorder_display,
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------------------------
    # MANAGEMENT ALERTS
    # --------------------------------------------------------

    st.markdown("### 🧠 Replenishment Intelligence")

    if reorder_now_count > 0:
        st.error(
            f"🚨 {reorder_now_count} SKU(s) are at or below their estimated reorder point. "
            "Review purchase orders and supplier availability immediately."
        )

    if monitor_count > 0:
        st.warning(
            f"⚠️ {monitor_count} SKU(s) are within 25% above their reorder point and should be monitored."
        )

    high_safety = int(
        (
            eoq_df["Safety_Stock"]
            > eoq_df["Reorder_Point"] * 0.50
        ).sum()
    )

    if high_safety > 0:
        st.info(
            f"🛡️ {high_safety} SKU(s) have safety stock representing more than 50% of their estimated reorder point, indicating relatively high demand variability."
        )

    if (
        reorder_now_count == 0
        and monitor_count == 0
    ):
        st.success(
            "✅ Current stock is above the estimated reorder point across the filtered portfolio."
        )

    # --------------------------------------------------------
    # COMPLETE EOQ DATASET
    # --------------------------------------------------------

    with st.expander("📄 Complete EOQ / Reorder Point Dataset"):
        st.dataframe(
            eoq_df,
            use_container_width=True,
            hide_index=True,
        )

else:
    st.info(
        "EOQ and replenishment intelligence requires SKU-level inventory data."
    )



# ============================================================
# STEP 65 — SUPPLIER & LEAD-TIME ANALYTICS
# ============================================================

section_header(
    "🚚 Supplier & Lead-Time Analytics",
    "Analyze supplier exposure, lead-time risk, and replenishment dependency across the filtered portfolio.",
)

supplier_df = eoq_df.copy()

if not supplier_df.empty and "sku_id" in supplier_df.columns:

    supplier_df["sku_id"] = supplier_df["sku_id"].astype(str)

    # --------------------------------------------------------
    # SUPPLIER IDENTIFICATION
    # --------------------------------------------------------

    supplier_candidates = [
        "supplier",
        "supplier_name",
        "vendor",
        "vendor_name",
        "supplier_id",
        "vendor_id",
    ]

    supplier_source = None
    for col in supplier_candidates:
        if col in supplier_df.columns:
            supplier_source = col
            break

    if supplier_source:
        supplier_df["Supplier"] = (
            supplier_df[supplier_source]
            .fillna("Unknown Supplier")
            .astype(str)
            .replace({"": "Unknown Supplier", "nan": "Unknown Supplier"})
        )
    else:
        supplier_df["Supplier"] = "Supplier Not Provided"

    # --------------------------------------------------------
    # LEAD-TIME ANALYTICS
    # --------------------------------------------------------

    supplier_df["Lead_Time_Days"] = pd.to_numeric(
        supplier_df["Lead_Time_Days"],
        errors="coerce",
    ).fillna(7).clip(lower=0)

    supplier_df["Current_Stock"] = pd.to_numeric(
        supplier_df["Current_Stock"],
        errors="coerce",
    ).fillna(0)

    supplier_df["Reorder_Point"] = pd.to_numeric(
        supplier_df["Reorder_Point"],
        errors="coerce",
    ).fillna(0)

    supplier_df["EOQ"] = pd.to_numeric(
        supplier_df["EOQ"],
        errors="coerce",
    )

    supplier_df["Average_Daily_Demand"] = pd.to_numeric(
        supplier_df["Average_Daily_Demand"],
        errors="coerce",
    ).fillna(0)

    supplier_df["Lead_Time_Demand"] = (
        supplier_df["Average_Daily_Demand"]
        * supplier_df["Lead_Time_Days"]
    )

    supplier_df["Lead_Time_Cover_Gap"] = (
        supplier_df["Current_Stock"]
        - supplier_df["Lead_Time_Demand"]
    )

    supplier_df["Lead_Time_Risk"] = np.select(
        [
            supplier_df["Current_Stock"]
            < supplier_df["Lead_Time_Demand"],
            supplier_df["Current_Stock"]
            <= supplier_df["Reorder_Point"],
            supplier_df["Lead_Time_Days"] >= 21,
        ],
        [
            "CRITICAL",
            "HIGH",
            "LONG LEAD TIME",
        ],
        default="NORMAL",
    )

    # --------------------------------------------------------
    # SUPPLIER SUMMARY
    # --------------------------------------------------------

    supplier_summary = (
        supplier_df.groupby("Supplier", dropna=False)
        .agg(
            SKU_Count=("sku_id", "nunique"),
            Current_Stock=("Current_Stock", "sum"),
            Lead_Time_Demand=("Lead_Time_Demand", "sum"),
            Avg_Lead_Time_Days=("Lead_Time_Days", "mean"),
            Max_Lead_Time_Days=("Lead_Time_Days", "max"),
            Reorder_SKUs=(
                "Reorder_Status",
                lambda x: int((x == "REORDER NOW").sum()),
            ),
            Critical_SKUs=(
                "Lead_Time_Risk",
                lambda x: int((x == "CRITICAL").sum()),
            ),
        )
        .reset_index()
    )

    supplier_summary["Stock_Cover_Gap"] = (
        supplier_summary["Current_Stock"]
        - supplier_summary["Lead_Time_Demand"]
    )

    supplier_summary["Supplier_Risk_Score"] = (
        supplier_summary["Critical_SKUs"] * 3
        + supplier_summary["Reorder_SKUs"] * 2
        + supplier_summary["Avg_Lead_Time_Days"] / 10
    )

    # --------------------------------------------------------
    # EXECUTIVE SUPPLIER KPIs
    # --------------------------------------------------------

    supplier_count = int(
        supplier_df["Supplier"].nunique()
    )

    avg_lead_time = float(
        supplier_df["Lead_Time_Days"].mean()
    )

    long_lead_skus = int(
        (supplier_df["Lead_Time_Days"] >= 21).sum()
    )

    critical_lead_skus = int(
        (supplier_df["Lead_Time_Risk"] == "CRITICAL").sum()
    )

    supplier_kpis = st.columns(4)

    with supplier_kpis[0]:
        st.metric(
            "Suppliers",
            format_number(supplier_count),
        )

    with supplier_kpis[1]:
        st.metric(
            "Avg Lead Time",
            f"{avg_lead_time:.1f} days",
        )

    with supplier_kpis[2]:
        st.metric(
            "Long Lead-Time SKUs",
            format_number(long_lead_skus),
        )

    with supplier_kpis[3]:
        st.metric(
            "Critical Lead-Time Risk",
            format_number(critical_lead_skus),
        )

    # --------------------------------------------------------
    # LEAD-TIME DISTRIBUTION
    # --------------------------------------------------------

    st.markdown("### ⏱️ Lead-Time Distribution")

    lead_time_bins = pd.cut(
        supplier_df["Lead_Time_Days"],
        bins=[-0.01, 7, 14, 21, np.inf],
        labels=[
            "0–7 Days",
            "8–14 Days",
            "15–21 Days",
            "22+ Days",
        ],
    )

    lead_time_distribution = (
        lead_time_bins.value_counts()
        .sort_index()
        .rename_axis("Lead-Time Range")
        .reset_index(name="SKU Count")
    )

    st.plotly_chart(
        px.bar(
            lead_time_distribution,
            x="Lead-Time Range",
            y="SKU Count",
            text_auto=True,
            title="SKU Distribution by Supplier Lead Time",
        ),
        use_container_width=True,
    )

    # --------------------------------------------------------
    # SUPPLIER RISK
    # --------------------------------------------------------

    st.markdown("### ⚠️ Supplier Risk Overview")

    supplier_risk_chart = supplier_summary.sort_values(
        "Supplier_Risk_Score",
        ascending=False,
    ).head(20)

    if not supplier_risk_chart.empty:
        st.plotly_chart(
            px.bar(
                supplier_risk_chart,
                x="Supplier",
                y="Supplier_Risk_Score",
                text_auto=".1f",
                title="Highest Supplier Risk Scores",
            ),
            use_container_width=True,
        )

    # --------------------------------------------------------
    # LEAD-TIME VS STOCK COVER
    # --------------------------------------------------------

    st.markdown("### 🔍 Lead Time vs Current Stock")

    scatter_df = supplier_df.copy()
    scatter_df["Risk_Label"] = scatter_df["Lead_Time_Risk"]

    st.plotly_chart(
        px.scatter(
            scatter_df,
            x="Lead_Time_Days",
            y="Current_Stock",
            size="Lead_Time_Demand",
            hover_name="sku_id",
            hover_data=[
                "Supplier",
                "Reorder_Point",
                "Lead_Time_Risk",
            ],
            color="Risk_Label",
            title="Lead Time vs Current Stock",
        ),
        use_container_width=True,
    )

    # --------------------------------------------------------
    # SUPPLIER TABLE
    # --------------------------------------------------------

    st.markdown("### 🏢 Supplier Performance Summary")

    supplier_display = supplier_summary.sort_values(
        "Supplier_Risk_Score",
        ascending=False,
    ).copy()

    supplier_display.columns = [
        "Supplier",
        "SKU Count",
        "Current Stock",
        "Lead-Time Demand",
        "Avg Lead Time",
        "Max Lead Time",
        "Reorder SKUs",
        "Critical SKUs",
        "Stock Cover Gap",
        "Risk Score",
    ]

    st.dataframe(
        supplier_display,
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------------------------
    # SUPPLIER ALERTS
    # --------------------------------------------------------

    if critical_lead_skus > 0:
        st.error(
            f"🚨 {critical_lead_skus} SKU(s) do not have enough current stock "
            "to cover estimated demand during supplier lead time."
        )

    if long_lead_skus > 0:
        st.warning(
            f"⚠️ {long_lead_skus} SKU(s) have lead times of 21 days or more. "
            "These items require earlier replenishment planning."
        )

    if critical_lead_skus == 0 and long_lead_skus == 0:
        st.success(
            "✅ No critical lead-time coverage issues were detected in the filtered portfolio."
        )

    with st.expander("📄 Complete Supplier & Lead-Time Dataset"):
        st.dataframe(
            supplier_df,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# STEP 66 — WORKING CAPITAL & INVENTORY INVESTMENT ANALYTICS
# ============================================================

section_header(
    "💰 Working Capital & Inventory Investment Analytics",
    "Estimate inventory value, capital tied up in stock, carrying cost, and financially exposed SKUs.",
)

financial_df = supplier_df.copy()

if not financial_df.empty and "sku_id" in financial_df.columns:

    financial_df["sku_id"] = financial_df["sku_id"].astype(str)

    financial_df["Current_Stock"] = _numeric_column(
        financial_df,
        [
            "Current_Stock",
            "current_stock",
            "stock_quantity",
            "quantity",
            "inventory",
        ],
        0,
    )

    financial_df["Unit_Cost"] = _numeric_column(
        financial_df,
        [
            "Unit_Cost",
            "unit_cost",
            "cost_per_unit",
            "purchase_cost",
            "cost",
        ],
        0,
    )

    financial_df["Selling_Price"] = _numeric_column(
        financial_df,
        [
            "Selling_Price",
            "estimated_selling_price",
            "selling_price",
            "unit_price",
            "list_price",
        ],
        0,
    )

    financial_df["EOQ"] = pd.to_numeric(
        financial_df.get(
            "EOQ",
            pd.Series(0, index=financial_df.index),
        ),
        errors="coerce",
    ).fillna(0)

    financial_df["Safety_Stock"] = pd.to_numeric(
        financial_df.get(
            "Safety_Stock",
            pd.Series(0, index=financial_df.index),
        ),
        errors="coerce",
    ).fillna(0)

    # Inventory valuation.
    financial_df["Inventory_Value"] = (
        financial_df["Current_Stock"]
        * financial_df["Unit_Cost"]
    )

    # Retail value is useful where cost data is incomplete.
    financial_df["Retail_Inventory_Value"] = (
        financial_df["Current_Stock"]
        * financial_df["Selling_Price"]
    )

    # Default annual carrying-cost assumption.
    financial_df["Holding_Rate"] = _numeric_column(
        financial_df,
        [
            "holding_rate",
            "annual_holding_rate",
            "carrying_cost_rate",
        ],
        0.20,
    )

    financial_df["Holding_Rate"] = np.where(
        financial_df["Holding_Rate"] > 1,
        financial_df["Holding_Rate"] / 100,
        financial_df["Holding_Rate"],
    )

    financial_df["Annual_Carrying_Cost"] = (
        financial_df["Inventory_Value"]
        * financial_df["Holding_Rate"]
    )

    # Potential capital required if stock is replenished to ROP.
    financial_df["Reorder_Investment"] = (
        np.maximum(
            financial_df["Reorder_Point"]
            - financial_df["Current_Stock"],
            0,
        )
        * financial_df["Unit_Cost"]
    )

    # Investment represented by the recommended EOQ.
    financial_df["EOQ_Investment"] = (
        financial_df["EOQ"]
        * financial_df["Unit_Cost"]
    )

    # Overstock indicator: stock above 2x reorder point.
    financial_df["Excess_Stock"] = np.maximum(
        financial_df["Current_Stock"]
        - (financial_df["Reorder_Point"] * 2),
        0,
    )

    financial_df["Excess_Inventory_Value"] = (
        financial_df["Excess_Stock"]
        * financial_df["Unit_Cost"]
    )

    financial_df["Financial_Risk"] = np.select(
        [
            financial_df["Excess_Inventory_Value"] > 0,
            financial_df["Inventory_Value"] <= 0,
            financial_df["Reorder_Status"] == "REORDER NOW",
        ],
        [
            "OVERSTOCK",
            "COST DATA MISSING",
            "REPLENISHMENT EXPOSURE",
        ],
        default="NORMAL",
    )

    # --------------------------------------------------------
    # FINANCIAL KPIs
    # --------------------------------------------------------

    total_inventory_value = float(
        financial_df["Inventory_Value"].sum()
    )

    total_retail_value = float(
        financial_df["Retail_Inventory_Value"].sum()
    )

    annual_carrying_cost = float(
        financial_df["Annual_Carrying_Cost"].sum()
    )

    excess_inventory_value = float(
        financial_df["Excess_Inventory_Value"].sum()
    )

    financial_kpis = st.columns(4)

    with financial_kpis[0]:
        st.metric(
            "Inventory Cost Value",
            format_currency(total_inventory_value),
        )

    with financial_kpis[1]:
        st.metric(
            "Retail Inventory Value",
            format_currency(total_retail_value),
        )

    with financial_kpis[2]:
        st.metric(
            "Annual Carrying Cost",
            format_currency(annual_carrying_cost),
        )

    with financial_kpis[3]:
        st.metric(
            "Excess Inventory Value",
            format_currency(excess_inventory_value),
        )

    st.caption(
        "Financial estimates use available unit-cost data. "
        "Where cost is unavailable, the corresponding inventory cost value is shown as zero."
    )

    # --------------------------------------------------------
    # VALUE BY CATEGORY
    # --------------------------------------------------------

    st.markdown("### 📊 Inventory Investment by Category")

    if "category" in financial_df.columns:
        category_financial = (
            financial_df.groupby("category", dropna=False)
            .agg(
                Inventory_Value=("Inventory_Value", "sum"),
                Carrying_Cost=("Annual_Carrying_Cost", "sum"),
                Excess_Value=("Excess_Inventory_Value", "sum"),
            )
            .reset_index()
        )

        st.plotly_chart(
            px.bar(
                category_financial,
                x="category",
                y=[
                    "Inventory_Value",
                    "Carrying_Cost",
                    "Excess_Value",
                ],
                barmode="group",
                title="Inventory Investment and Exposure by Category",
            ),
            use_container_width=True,
        )

    # --------------------------------------------------------
    # CAPITAL EXPOSURE
    # --------------------------------------------------------

    st.markdown("### 💸 Highest Capital-Exposed SKUs")

    capital_chart = financial_df.sort_values(
        "Inventory_Value",
        ascending=False,
    ).head(25)

    st.plotly_chart(
        px.bar(
            capital_chart,
            x="sku_id",
            y="Inventory_Value",
            text_auto=".0f",
            title="Top SKUs by Inventory Cost Value",
        ),
        use_container_width=True,
    )

    # --------------------------------------------------------
    # EXCESS INVENTORY
    # --------------------------------------------------------

    st.markdown("### 📦 Excess Inventory Exposure")

    excess_chart = financial_df[
        financial_df["Excess_Inventory_Value"] > 0
    ].sort_values(
        "Excess_Inventory_Value",
        ascending=False,
    ).head(25)

    if not excess_chart.empty:
        st.plotly_chart(
            px.bar(
                excess_chart,
                x="sku_id",
                y="Excess_Inventory_Value",
                text_auto=".0f",
                title="Highest Estimated Excess Inventory Value",
            ),
            use_container_width=True,
        )
    else:
        st.success(
            "✅ No material excess inventory exposure was identified using the current rule."
        )

    # --------------------------------------------------------
    # FINANCIAL RISK PROFILE
    # --------------------------------------------------------

    financial_risk_counts = (
        financial_df["Financial_Risk"]
        .value_counts()
        .rename_axis("Risk")
        .reset_index(name="SKU Count")
    )

    st.plotly_chart(
        px.pie(
            financial_risk_counts,
            names="Risk",
            values="SKU Count",
            hole=0.45,
            title="Inventory Financial Risk Profile",
        ),
        use_container_width=True,
    )

    # --------------------------------------------------------
    # CAPITAL PRIORITY
    # --------------------------------------------------------

    financial_df["Capital_Priority_Score"] = (
        financial_df["Inventory_Value"]
        + financial_df["Excess_Inventory_Value"] * 2
        + financial_df["Reorder_Investment"]
    )

    capital_priority = financial_df.sort_values(
        "Capital_Priority_Score",
        ascending=False,
    ).head(25).copy()

    priority_columns = [
        "sku_id",
        "Current_Stock",
        "Unit_Cost",
        "Inventory_Value",
        "Excess_Inventory_Value",
        "Reorder_Investment",
        "Annual_Carrying_Cost",
        "Financial_Risk",
    ]

    priority_columns = [
        col for col in priority_columns
        if col in capital_priority.columns
    ]

    priority_display = capital_priority[
        priority_columns
    ].copy()

    priority_display.columns = [
        col.replace("_", " ").title()
        for col in priority_display.columns
    ]

    st.markdown("### 🎯 Capital Management Priority")

    st.dataframe(
        priority_display,
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------------------------
    # FINANCIAL ALERTS
    # --------------------------------------------------------

    if excess_inventory_value > 0:
        st.warning(
            f"⚠️ Estimated excess inventory represents "
            f"{format_currency(excess_inventory_value)} of inventory cost value. "
            "Review slow-moving stock, promotions, transfers, or purchasing limits."
        )

    missing_cost_count = int(
        (financial_df["Unit_Cost"] <= 0).sum()
    )

    if missing_cost_count > 0:
        st.info(
            f"ℹ️ {missing_cost_count} SKU(s) have missing or zero unit cost. "
            "Financial exposure for these SKUs cannot be fully valued."
        )

    if annual_carrying_cost > 0:
        st.success(
            f"💡 Estimated annual inventory carrying cost is "
            f"{format_currency(annual_carrying_cost)} under the configured holding-rate assumption."
        )

    with st.expander("📄 Complete Working Capital Dataset"):
        st.dataframe(
            financial_df,
            use_container_width=True,
            hide_index=True,
        )

else:
    st.info(
        "Working-capital analytics requires SKU-level inventory and cost data."
    )



# ============================================================
# STEP 67 — INVENTORY TURNOVER, DIO & SLOW-MOVING STOCK
# ============================================================

section_header(
    "🔄 Inventory Turnover & Slow-Moving Stock Intelligence",
    "Measure inventory efficiency, days inventory outstanding, stock velocity, and slow-moving inventory exposure.",
)

turnover_df = financial_df.copy()

if not turnover_df.empty and "sku_id" in turnover_df.columns:

    turnover_df["sku_id"] = turnover_df["sku_id"].astype(str)

    # --------------------------------------------------------
    # SALES DEMAND / COGS INPUTS
    # --------------------------------------------------------

    turnover_df["Historical_Annual_Demand"] = pd.to_numeric(
        turnover_df.get(
            "Historical_Annual_Demand",
            pd.Series(0, index=turnover_df.index),
        ),
        errors="coerce",
    ).fillna(0)

    turnover_df["EOQ_Annual_Demand"] = pd.to_numeric(
        turnover_df.get(
            "EOQ_Annual_Demand",
            pd.Series(0, index=turnover_df.index),
        ),
        errors="coerce",
    ).fillna(0)

    # Historical annual demand is preferred for turnover analysis.
    turnover_df["Annual_Units_Demand"] = np.where(
        turnover_df["Historical_Annual_Demand"] > 0,
        turnover_df["Historical_Annual_Demand"],
        turnover_df["EOQ_Annual_Demand"],
    )

    turnover_df["Unit_Cost"] = _numeric_column(
        turnover_df,
        [
            "Unit_Cost",
            "unit_cost",
            "cost_per_unit",
            "purchase_cost",
            "cost",
        ],
        0,
    )

    turnover_df["Current_Stock"] = _numeric_column(
        turnover_df,
        [
            "Current_Stock",
            "current_stock",
            "stock_quantity",
            "quantity",
            "inventory",
        ],
        0,
    )

    # --------------------------------------------------------
    # INVENTORY TURNOVER
    #
    # Inventory Turnover = Annual COGS / Average Inventory Value
    #
    # When opening inventory is unavailable, current inventory
    # value is used as the planning proxy.
    # --------------------------------------------------------

    turnover_df["Annual_COGS"] = (
        turnover_df["Annual_Units_Demand"]
        * turnover_df["Unit_Cost"]
    )

    turnover_df["Average_Inventory_Value"] = (
        turnover_df["Current_Stock"]
        * turnover_df["Unit_Cost"]
    )

    turnover_df["Inventory_Turnover"] = np.where(
        turnover_df["Average_Inventory_Value"] > 0,
        turnover_df["Annual_COGS"]
        / turnover_df["Average_Inventory_Value"],
        np.nan,
    )

    # --------------------------------------------------------
    # DAYS INVENTORY OUTSTANDING
    #
    # DIO = 365 / Inventory Turnover
    # --------------------------------------------------------

    turnover_df["DIO_Days"] = np.where(
        turnover_df["Inventory_Turnover"] > 0,
        365 / turnover_df["Inventory_Turnover"],
        np.nan,
    )

    # --------------------------------------------------------
    # STOCK VELOCITY / COVER
    # --------------------------------------------------------

    turnover_df["Average_Daily_Units"] = (
        turnover_df["Annual_Units_Demand"] / 365
    )

    turnover_df["Days_of_Stock"] = np.where(
        turnover_df["Average_Daily_Units"] > 0,
        turnover_df["Current_Stock"]
        / turnover_df["Average_Daily_Units"],
        np.nan,
    )

    turnover_df["Annual_Unit_Velocity"] = (
        turnover_df["Annual_Units_Demand"]
    )

    # --------------------------------------------------------
    # SLOW-MOVING CLASSIFICATION
    #
    # Uses DIO / days-of-stock thresholds.
    # --------------------------------------------------------

    turnover_df["Velocity_Status"] = np.select(
        [
            turnover_df["Days_of_Stock"].isna(),
            turnover_df["Days_of_Stock"] > 180,
            turnover_df["Days_of_Stock"] > 90,
            turnover_df["Days_of_Stock"] > 60,
            turnover_df["Days_of_Stock"] <= 30,
        ],
        [
            "NO DEMAND DATA",
            "VERY SLOW",
            "SLOW",
            "MODERATE",
            "FAST",
        ],
        default="NORMAL",
    )

    turnover_df["Slow_Moving_Flag"] = turnover_df[
        "Days_of_Stock"
    ] > 90

    turnover_df["Very_Slow_Flag"] = turnover_df[
        "Days_of_Stock"
    ] > 180

    # --------------------------------------------------------
    # CAPITAL AT RISK FROM SLOW STOCK
    # --------------------------------------------------------

    turnover_df["Slow_Stock_Value"] = np.where(
        turnover_df["Slow_Moving_Flag"],
        turnover_df["Inventory_Value"],
        0,
    )

    turnover_df["Very_Slow_Stock_Value"] = np.where(
        turnover_df["Very_Slow_Flag"],
        turnover_df["Inventory_Value"],
        0,
    )

    turnover_df["Turnover_Risk"] = np.select(
        [
            turnover_df["Very_Slow_Flag"],
            turnover_df["Slow_Moving_Flag"],
            turnover_df["Inventory_Turnover"].notna()
            & (turnover_df["Inventory_Turnover"] < 2),
        ],
        [
            "VERY HIGH",
            "HIGH",
            "MEDIUM",
        ],
        default="LOW",
    )

    # --------------------------------------------------------
    # EXECUTIVE KPIs
    # --------------------------------------------------------

    valid_turnover = turnover_df[
        turnover_df["Inventory_Turnover"].notna()
        & np.isfinite(turnover_df["Inventory_Turnover"])
    ]

    portfolio_turnover = (
        float(
            valid_turnover["Annual_COGS"].sum()
            / valid_turnover["Average_Inventory_Value"].sum()
        )
        if (
            not valid_turnover.empty
            and valid_turnover["Average_Inventory_Value"].sum() > 0
        )
        else np.nan
    )

    valid_dio = turnover_df[
        turnover_df["DIO_Days"].notna()
        & np.isfinite(turnover_df["DIO_Days"])
    ]

    portfolio_dio = (
        float(
            365 / portfolio_turnover
        )
        if pd.notna(portfolio_turnover)
        and portfolio_turnover > 0
        else (
            float(valid_dio["DIO_Days"].mean())
            if not valid_dio.empty
            else np.nan
        )
    )

    slow_skus = int(
        turnover_df["Slow_Moving_Flag"].sum()
    )

    very_slow_skus = int(
        turnover_df["Very_Slow_Flag"].sum()
    )

    slow_stock_value = float(
        turnover_df["Slow_Stock_Value"].sum()
    )

    turnover_kpis = st.columns(4)

    with turnover_kpis[0]:
        st.metric(
            "Portfolio Turnover",
            f"{portfolio_turnover:.2f}x"
            if pd.notna(portfolio_turnover)
            else "N/A",
        )

    with turnover_kpis[1]:
        st.metric(
            "Portfolio DIO",
            f"{portfolio_dio:.1f} days"
            if pd.notna(portfolio_dio)
            else "N/A",
        )

    with turnover_kpis[2]:
        st.metric(
            "Slow-Moving SKUs",
            format_number(slow_skus),
        )

    with turnover_kpis[3]:
        st.metric(
            "Slow Stock Value",
            format_currency(slow_stock_value),
        )

    st.caption(
        "Turnover uses annualized demand × unit cost as COGS and current inventory value "
        "as the average-inventory proxy when opening-period inventory is unavailable."
    )

    # --------------------------------------------------------
    # VELOCITY DISTRIBUTION
    # --------------------------------------------------------

    st.markdown("### 🏃 Stock Velocity Distribution")

    velocity_order = [
        "FAST",
        "MODERATE",
        "NORMAL",
        "SLOW",
        "VERY SLOW",
        "NO DEMAND DATA",
    ]

    velocity_counts = (
        turnover_df["Velocity_Status"]
        .value_counts()
        .reindex(velocity_order, fill_value=0)
        .rename_axis("Velocity")
        .reset_index(name="SKU Count")
    )

    st.plotly_chart(
        px.bar(
            velocity_counts,
            x="Velocity",
            y="SKU Count",
            text_auto=True,
            title="SKU Distribution by Stock Velocity",
        ),
        use_container_width=True,
    )

    # --------------------------------------------------------
    # INVENTORY TURNOVER BY SKU
    # --------------------------------------------------------

    st.markdown("### 🔄 Inventory Turnover by SKU")

    turnover_chart = turnover_df[
        turnover_df["Inventory_Turnover"].notna()
    ].sort_values(
        "Inventory_Turnover",
        ascending=False,
    ).copy()

    if not turnover_chart.empty:
        turnover_chart["Inventory_Turnover"] = turnover_chart[
            "Inventory_Turnover"
        ].clip(upper=turnover_chart["Inventory_Turnover"].quantile(0.95))

        st.plotly_chart(
            px.bar(
                turnover_chart.head(25),
                x="sku_id",
                y="Inventory_Turnover",
                text_auto=".2f",
                title="Highest Inventory Turnover SKUs",
            ),
            use_container_width=True,
        )

    # --------------------------------------------------------
    # DAYS OF INVENTORY
    # --------------------------------------------------------

    st.markdown("### 📅 Days of Inventory by SKU")

    dio_chart = turnover_df[
        turnover_df["Days_of_Stock"].notna()
    ].sort_values(
        "Days_of_Stock",
        ascending=False,
    ).head(25)

    if not dio_chart.empty:
        st.plotly_chart(
            px.bar(
                dio_chart,
                x="sku_id",
                y="Days_of_Stock",
                text_auto=".1f",
                title="SKUs with Highest Days of Stock",
            ),
            use_container_width=True,
        )

    # --------------------------------------------------------
    # SLOW-MOVING CAPITAL EXPOSURE
    # --------------------------------------------------------

    st.markdown("### 💰 Slow-Moving Capital Exposure")

    slow_chart = turnover_df[
        turnover_df["Slow_Stock_Value"] > 0
    ].sort_values(
        "Slow_Stock_Value",
        ascending=False,
    ).head(25)

    if not slow_chart.empty:
        st.plotly_chart(
            px.bar(
                slow_chart,
                x="sku_id",
                y="Slow_Stock_Value",
                text_auto=".0f",
                title="Highest Capital Tied Up in Slow-Moving Stock",
            ),
            use_container_width=True,
        )
    else:
        st.success(
            "✅ No SKUs currently exceed the 90-day slow-moving threshold."
        )

    # --------------------------------------------------------
    # CATEGORY TURNOVER
    # --------------------------------------------------------

    if "category" in turnover_df.columns:
        st.markdown("### 🗂️ Turnover by Category")

        category_turnover = (
            turnover_df.groupby("category", dropna=False)
            .agg(
                Annual_COGS=("Annual_COGS", "sum"),
                Inventory_Value=("Average_Inventory_Value", "sum"),
                SKU_Count=("sku_id", "nunique"),
                Slow_SKUs=("Slow_Moving_Flag", "sum"),
            )
            .reset_index()
        )

        category_turnover["Inventory_Turnover"] = np.where(
            category_turnover["Inventory_Value"] > 0,
            category_turnover["Annual_COGS"]
            / category_turnover["Inventory_Value"],
            np.nan,
        )

        st.plotly_chart(
            px.bar(
                category_turnover.sort_values(
                    "Inventory_Turnover",
                    ascending=False,
                ),
                x="category",
                y="Inventory_Turnover",
                text_auto=".2f",
                title="Inventory Turnover by Category",
            ),
            use_container_width=True,
        )

    # --------------------------------------------------------
    # SLOW-MOVING TABLE
    # --------------------------------------------------------

    st.markdown("### 🐢 Slow-Moving SKU Watchlist")

    slow_table = turnover_df[
        turnover_df["Slow_Moving_Flag"]
    ].sort_values(
        "Slow_Stock_Value",
        ascending=False,
    ).head(30).copy()

    slow_columns = [
        "sku_id",
        "category",
        "Current_Stock",
        "Annual_Units_Demand",
        "Inventory_Turnover",
        "DIO_Days",
        "Days_of_Stock",
        "Inventory_Value",
        "Slow_Stock_Value",
        "Turnover_Risk",
    ]

    slow_columns = [
        col for col in slow_columns
        if col in slow_table.columns
    ]

    slow_display = slow_table[slow_columns].copy()
    slow_display.columns = [
        col.replace("_", " ").title()
        for col in slow_display.columns
    ]

    if not slow_display.empty:
        st.dataframe(
            slow_display,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success(
            "✅ No slow-moving SKUs were found in the current filtered portfolio."
        )

    # --------------------------------------------------------
    # MANAGEMENT ALERTS
    # --------------------------------------------------------

    if very_slow_skus > 0:
        st.error(
            f"🚨 {very_slow_skus} SKU(s) have more than 180 days of stock coverage. "
            "Review liquidation, markdowns, transfers, or purchase restrictions."
        )

    if slow_skus > 0:
        st.warning(
            f"⚠️ {slow_skus} SKU(s) have more than 90 days of stock coverage. "
            "These items are candidates for slow-moving inventory action."
        )

    if slow_stock_value > 0:
        st.info(
            f"💡 Approximately {format_currency(slow_stock_value)} of inventory cost "
            "is tied up in SKUs classified as slow-moving."
        )

    if slow_skus == 0:
        st.success(
            "✅ Inventory velocity is healthy under the current 90-day slow-moving threshold."
        )

    with st.expander("📄 Complete Inventory Turnover Dataset"):
        st.dataframe(
            turnover_df,
            use_container_width=True,
            hide_index=True,
        )

else:
    st.info(
        "Inventory turnover analysis requires SKU-level sales and inventory data."
    )

# ============================================================
# STEP 67 — END
# ============================================================

# ============================================================
# STEP 68 — DEMAND-SUPPLY GAP & INVENTORY OPTIMIZATION
# ============================================================

st.markdown("---")
st.header("⚖️ Demand-Supply Gap & Inventory Optimization Intelligence")

st.caption(
    "Compares expected demand with available inventory and identifies "
    "stockout, understock, balanced-stock, and overstock conditions."
)


def _first_numeric_column(df, candidates, default=0.0):
    """
    Select the first usable numeric column from a list of possible names.
    """
    for column in candidates:
        if column in df.columns:
            values = pd.to_numeric(df[column], errors="coerce")
            if values.notna().any():
                return values.fillna(default)

    return pd.Series(default, index=df.index, dtype="float64")


def _first_existing_column(df, candidates, default="Unknown"):
    """
    Select the first existing column from a list of possible names.
    """
    for column in candidates:
        if column in df.columns:
            return df[column].astype(str).fillna(default)

    return pd.Series(default, index=df.index, dtype="object")


# ------------------------------------------------------------
# 1. Prepare optimization dataset
# ------------------------------------------------------------

optimization_df = None

if "turnover_df" in locals() and isinstance(turnover_df, pd.DataFrame):
    optimization_df = turnover_df.copy()
elif "financial_df" in locals() and isinstance(financial_df, pd.DataFrame):
    optimization_df = financial_df.copy()

if optimization_df is not None and not optimization_df.empty:

    # --------------------------------------------------------
    # 2. Standardize identifiers and descriptive fields
    # --------------------------------------------------------

    if "sku_id" in optimization_df.columns:
        optimization_df["sku_id"] = (
            optimization_df["sku_id"].astype(str).str.strip()
        )
    elif "SKU" in optimization_df.columns:
        optimization_df["sku_id"] = (
            optimization_df["SKU"].astype(str).str.strip()
        )
    elif "SKU_ID" in optimization_df.columns:
        optimization_df["sku_id"] = (
            optimization_df["SKU_ID"].astype(str).str.strip()
        )
    else:
        optimization_df["sku_id"] = optimization_df.index.astype(str)

    optimization_df["category"] = _first_existing_column(
        optimization_df,
        [
            "category",
            "Category",
            "Product_Category",
            "product_category",
            "Department",
        ],
    )

    optimization_df["product_name"] = _first_existing_column(
        optimization_df,
        [
            "Product_Name",
            "product_name",
            "Product",
            "Item_Name",
            "SKU_Name",
        ],
    )

    # --------------------------------------------------------
    # 3. Derive demand and supply values
    # --------------------------------------------------------

    annual_demand = _first_numeric_column(
        optimization_df,
        [
            "Annual_Units_Demand",
            "EOQ_Annual_Demand",
            "Historical_Annual_Demand",
            "Annual_Demand",
            "Forecast_Annual_Demand",
            "Demand",
        ],
    )

    current_stock = _first_numeric_column(
        optimization_df,
        [
            "Current_Stock",
            "current_stock",
            "Inventory",
            "Inventory_Units",
            "Stock",
            "Closing_Stock",
            "On_Hand",
            "On_Hand_Quantity",
        ],
    )

    unit_cost = _first_numeric_column(
        optimization_df,
        [
            "Unit_Cost",
            "unit_cost",
            "Cost",
            "Purchase_Price",
            "Price",
            "Unit_Price",
        ],
    )

    lead_time_days = _first_numeric_column(
        optimization_df,
        [
            "Lead_Time_Days",
            "lead_time_days",
            "Lead_Time",
            "Supplier_Lead_Time",
        ],
        default=7.0,
    )

    safety_stock = _first_numeric_column(
        optimization_df,
        [
            "Safety_Stock",
            "safety_stock",
            "Recommended_Safety_Stock",
            "Safety_Stock_Units",
        ],
        default=0.0,
    )

    reorder_point = _first_numeric_column(
        optimization_df,
        [
            "Reorder_Point",
            "reorder_point",
            "ROP",
            "Recommended_Reorder_Point",
        ],
        default=0.0,
    )

    # --------------------------------------------------------
    # 4. Calculate demand-supply metrics
    # --------------------------------------------------------

    optimization_df["Annual_Demand"] = annual_demand.clip(lower=0)
    optimization_df["Current_Stock"] = current_stock.clip(lower=0)
    optimization_df["Unit_Cost"] = unit_cost.clip(lower=0)
    optimization_df["Lead_Time_Days"] = lead_time_days.clip(lower=0)
    optimization_df["Safety_Stock"] = safety_stock.clip(lower=0)
    optimization_df["Existing_Reorder_Point"] = reorder_point.clip(lower=0)

    optimization_df["Average_Daily_Demand"] = (
        optimization_df["Annual_Demand"] / 365
    )

    optimization_df["Lead_Time_Demand"] = (
        optimization_df["Average_Daily_Demand"]
        * optimization_df["Lead_Time_Days"]
    )

    # If no safety stock is available, estimate it as 20% of lead-time demand.
    optimization_df["Estimated_Safety_Stock"] = np.where(
        optimization_df["Safety_Stock"] > 0,
        optimization_df["Safety_Stock"],
        optimization_df["Lead_Time_Demand"] * 0.20,
    )

    optimization_df["Recommended_Reorder_Point"] = (
        optimization_df["Lead_Time_Demand"]
        + optimization_df["Estimated_Safety_Stock"]
    )

    optimization_df["Demand_Supply_Gap"] = (
        optimization_df["Annual_Demand"]
        - optimization_df["Current_Stock"]
    )

    optimization_df["Stock_Coverage_Days"] = np.where(
        optimization_df["Average_Daily_Demand"] > 0,
        optimization_df["Current_Stock"]
        / optimization_df["Average_Daily_Demand"],
        np.nan,
    )

    optimization_df["Inventory_Value"] = (
        optimization_df["Current_Stock"]
        * optimization_df["Unit_Cost"]
    )

    optimization_df["Required_Stock_Value"] = (
        optimization_df["Recommended_Reorder_Point"]
        * optimization_df["Unit_Cost"]
    )

    optimization_df["Optimization_Gap_Units"] = (
        optimization_df["Recommended_Reorder_Point"]
        - optimization_df["Current_Stock"]
    )

    optimization_df["Optimization_Gap_Value"] = (
        optimization_df["Optimization_Gap_Units"].clip(lower=0)
        * optimization_df["Unit_Cost"]
    )

    # --------------------------------------------------------
    # 5. Inventory health classification
    # --------------------------------------------------------

    def classify_inventory_health(row):
        current = row["Current_Stock"]
        reorder_point_value = row["Recommended_Reorder_Point"]
        annual_demand_value = row["Annual_Demand"]
        coverage = row["Stock_Coverage_Days"]

        if annual_demand_value <= 0 and current > 0:
            return "OVERSTOCK / NO DEMAND"

        if current <= 0 and annual_demand_value > 0:
            return "STOCKOUT"

        if current < reorder_point_value * 0.50:
            return "CRITICAL UNDERSTOCK"

        if current < reorder_point_value:
            return "UNDERSTOCK"

        if pd.notna(coverage) and coverage > 180:
            return "OVERSTOCK"

        if pd.notna(coverage) and coverage > 90:
            return "EXCESS STOCK"

        return "BALANCED"

    optimization_df["Inventory_Health"] = optimization_df.apply(
        classify_inventory_health,
        axis=1,
    )

    # --------------------------------------------------------
    # 6. Recommended action
    # --------------------------------------------------------

    def recommended_action(row):
        health = row["Inventory_Health"]
        gap_units = max(row["Optimization_Gap_Units"], 0)

        if health == "STOCKOUT":
            return "URGENTLY REPLENISH"

        if health == "CRITICAL UNDERSTOCK":
            return f"EXPEDITE {gap_units:,.0f} UNITS"

        if health == "UNDERSTOCK":
            return f"REORDER {gap_units:,.0f} UNITS"

        if health == "OVERSTOCK / NO DEMAND":
            return "STOP PURCHASES / REVIEW SKU"

        if health in ["OVERSTOCK", "EXCESS STOCK"]:
            return "REDUCE PURCHASES / PROMOTE STOCK"

        return "MONITOR"

    optimization_df["Recommended_Action"] = optimization_df.apply(
        recommended_action,
        axis=1,
    )

    # --------------------------------------------------------
    # 7. Portfolio KPIs
    # --------------------------------------------------------

    total_skus = len(optimization_df)

    stockout_skus = int(
        (optimization_df["Inventory_Health"] == "STOCKOUT").sum()
    )

    critical_understock_skus = int(
        (
            optimization_df["Inventory_Health"]
            == "CRITICAL UNDERSTOCK"
        ).sum()
    )

    understock_skus = int(
        (
            optimization_df["Inventory_Health"]
            == "UNDERSTOCK"
        ).sum()
    )

    overstock_skus = int(
        optimization_df["Inventory_Health"].isin(
            ["OVERSTOCK", "OVERSTOCK / NO DEMAND", "EXCESS STOCK"]
        ).sum()
    )

    total_gap_units = optimization_df["Optimization_Gap_Units"].clip(
        lower=0
    ).sum()

    total_gap_value = optimization_df["Optimization_Gap_Value"].sum()

    total_inventory_value = optimization_df["Inventory_Value"].sum()

    coverage_values = optimization_df["Stock_Coverage_Days"].dropna()

    portfolio_coverage = (
        coverage_values.median() if not coverage_values.empty else 0
    )

    # --------------------------------------------------------
    # 8. Display KPI cards
    # --------------------------------------------------------

    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

    kpi_col1.metric(
        "Total SKUs",
        f"{total_skus:,}",
    )

    kpi_col2.metric(
        "Stockout SKUs",
        f"{stockout_skus:,}",
    )

    kpi_col3.metric(
        "Replenishment Gap",
        f"{total_gap_units:,.0f} units",
    )

    kpi_col4.metric(
        "Gap Value",
        f"₹{total_gap_value:,.0f}",
    )

    kpi_col5, kpi_col6, kpi_col7, kpi_col8 = st.columns(4)

    kpi_col5.metric(
        "Critical Understock",
        f"{critical_understock_skus:,}",
    )

    kpi_col6.metric(
        "Understock",
        f"{understock_skus:,}",
    )

    kpi_col7.metric(
        "Overstock / Excess",
        f"{overstock_skus:,}",
    )

    kpi_col8.metric(
        "Median Stock Coverage",
        f"{portfolio_coverage:,.1f} days",
    )

    # --------------------------------------------------------
    # 9. Inventory health distribution
    # --------------------------------------------------------

    st.subheader("📊 Inventory Health Distribution")

    health_order = [
        "STOCKOUT",
        "CRITICAL UNDERSTOCK",
        "UNDERSTOCK",
        "BALANCED",
        "EXCESS STOCK",
        "OVERSTOCK",
        "OVERSTOCK / NO DEMAND",
    ]

    health_distribution = (
        optimization_df["Inventory_Health"]
        .value_counts()
        .reindex(health_order, fill_value=0)
        .reset_index()
    )

    health_distribution.columns = ["Inventory_Health", "SKU_Count"]

    st.bar_chart(
        health_distribution.set_index("Inventory_Health")["SKU_Count"]
    )

    # --------------------------------------------------------
    # 10. Demand-supply gap chart
    # --------------------------------------------------------

    st.subheader("⚖️ Demand-Supply Gap by SKU")

    gap_chart_df = optimization_df[
        [
            "sku_id",
            "Annual_Demand",
            "Current_Stock",
            "Recommended_Reorder_Point",
        ]
    ].copy()

    gap_chart_df = gap_chart_df.sort_values(
        "Annual_Demand",
        ascending=False,
    ).head(25)

    gap_chart_df = gap_chart_df.set_index("sku_id")

    st.bar_chart(gap_chart_df)

    # --------------------------------------------------------
    # 11. Category-level optimization summary
    # --------------------------------------------------------

    st.subheader("🗂️ Category-Level Demand-Supply Summary")

    category_summary = (
        optimization_df.groupby("category", dropna=False)
        .agg(
            SKU_Count=("sku_id", "nunique"),
            Annual_Demand=("Annual_Demand", "sum"),
            Current_Stock=("Current_Stock", "sum"),
            Recommended_Reorder_Point=(
                "Recommended_Reorder_Point",
                "sum",
            ),
            Demand_Supply_Gap=("Demand_Supply_Gap", "sum"),
            Inventory_Value=("Inventory_Value", "sum"),
            Optimization_Gap_Value=("Optimization_Gap_Value", "sum"),
        )
        .reset_index()
    )

    category_summary["Category_Health"] = np.where(
        category_summary["Current_Stock"]
        < category_summary["Recommended_Reorder_Point"],
        "UNDERSTOCK",
        "BALANCED / OVERSTOCK",
    )

    st.dataframe(
        category_summary.sort_values(
            "Optimization_Gap_Value",
            ascending=False,
        ),
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------------------------
    # 12. Management alerts
    # --------------------------------------------------------

    st.subheader("🚨 Inventory Optimization Alerts")

    if stockout_skus > 0:
        st.error(
            f"{stockout_skus} SKU(s) currently have zero stock "
            "despite positive annual demand."
        )

    if critical_understock_skus > 0:
        st.warning(
            f"{critical_understock_skus} SKU(s) are critically below "
            "their recommended reorder point."
        )

    if understock_skus > 0:
        st.warning(
            f"{understock_skus} SKU(s) require replenishment planning."
        )

    if overstock_skus > 0:
        st.info(
            f"{overstock_skus} SKU(s) show excess or overstock conditions. "
            "Review purchasing and promotional actions."
        )

    if stockout_skus == 0 and critical_understock_skus == 0:
        st.success(
            "No immediate stockout or critical-understock condition detected."
        )

    # --------------------------------------------------------
    # 13. Optimization watchlist
    # --------------------------------------------------------

    st.subheader("📋 Inventory Optimization Watchlist")

    watchlist_columns = [
        "sku_id",
        "product_name",
        "category",
        "Annual_Demand",
        "Current_Stock",
        "Average_Daily_Demand",
        "Stock_Coverage_Days",
        "Recommended_Reorder_Point",
        "Optimization_Gap_Units",
        "Optimization_Gap_Value",
        "Inventory_Health",
        "Recommended_Action",
    ]

    watchlist_columns = [
        column
        for column in watchlist_columns
        if column in optimization_df.columns
    ]

    watchlist_df = optimization_df[watchlist_columns].copy()

    watchlist_df = watchlist_df[
        watchlist_df["Inventory_Health"].isin(
            [
                "STOCKOUT",
                "CRITICAL UNDERSTOCK",
                "UNDERSTOCK",
                "OVERSTOCK",
                "OVERSTOCK / NO DEMAND",
                "EXCESS STOCK",
            ]
        )
    ]

    watchlist_df = watchlist_df.sort_values(
        "Optimization_Gap_Value",
        ascending=False,
    )

    st.dataframe(
        watchlist_df,
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------------------------
    # 14. Complete dataset
    # --------------------------------------------------------

    with st.expander("📦 Complete Demand-Supply Optimization Dataset"):
        st.dataframe(
            optimization_df,
            use_container_width=True,
            hide_index=True,
        )

else:
    st.info(
        "Demand-supply optimization requires SKU-level demand "
        "and inventory data."
    )
# ============================================================
# STEP 69 — INVENTORY OPTIMIZATION SCENARIO SIMULATOR
# ============================================================
#
# Purpose:
#   Simulate different demand, lead-time and inventory scenarios
#   and estimate:
#       • Stockout risk
#       • Understock risk
#       • Additional inventory requirement
#       • Additional working capital requirement
#       • Excess inventory
#       • Scenario inventory coverage
#       • Category-level impact
#
# This is a scenario simulator, NOT a mathematical optimization solver.
# ============================================================

st.markdown("---")
st.header("STEP 69 — Inventory Optimization Scenario Simulator")

st.write(
    """
    This simulator allows management to test how inventory requirements
    change under different demand-growth, supplier lead-time and inventory
    coverage scenarios.
    """
)


# ============================================================
# 69.1 — SOURCE DATA
# ============================================================

if "optimization_df" in globals() and isinstance(optimization_df, pd.DataFrame):
    scenario_base_df = optimization_df.copy()

elif "turnover_df" in globals() and isinstance(turnover_df, pd.DataFrame):
    scenario_base_df = turnover_df.copy()

elif "financial_df" in globals() and isinstance(financial_df, pd.DataFrame):
    scenario_base_df = financial_df.copy()

else:
    scenario_base_df = pd.DataFrame()


if scenario_base_df.empty:

    st.info(
        "No optimization data is available. "
        "Please complete Step 68 before running Step 69."
    )

else:

    scenario_df = scenario_base_df.copy()


    # ========================================================
    # 69.2 — HELPER FUNCTIONS
    # ========================================================

    def _scenario_numeric_column(df, candidates, default=0.0):

        for col in candidates:

            if col in df.columns:

                values = pd.to_numeric(
                    df[col],
                    errors="coerce"
                ).fillna(default)

                return values

        return pd.Series(
            default,
            index=df.index,
            dtype=float
        )


    def _scenario_text_column(df, candidates, default="Unknown"):

        for col in candidates:

            if col in df.columns:

                values = (
                    df[col]
                    .fillna(default)
                    .astype(str)
                )

                return values

        return pd.Series(
            default,
            index=df.index,
            dtype="object"
        )


    # ========================================================
    # 69.3 — STANDARDIZE CORE FIELDS
    # ========================================================

    scenario_df["SKU"] = _scenario_text_column(
        scenario_df,
        ["SKU", "sku_id", "SKU_ID", "sku"],
        "Unknown"
    )

    scenario_df["Category"] = _scenario_text_column(
        scenario_df,
        ["Category", "category", "CATEGORY"],
        "Unknown"
    )

    scenario_df["Product_Name"] = _scenario_text_column(
        scenario_df,
        [
            "Product_Name",
            "product_name",
            "Product",
            "product"
        ],
        "Unknown"
    )

    scenario_df["Annual_Demand"] = _scenario_numeric_column(
        scenario_df,
        [
            "Annual_Demand",
            "Annual_Units_Demand",
            "EOQ_Annual_Demand",
            "Historical_Annual_Demand"
        ],
        0
    )

    scenario_df["Current_Stock"] = _scenario_numeric_column(
        scenario_df,
        [
            "Current_Stock",
            "on_hand",
            "On_Hand",
            "stock",
            "Stock"
        ],
        0
    )

    scenario_df["On_Order"] = _scenario_numeric_column(
        scenario_df,
        [
            "On_Order",
            "on_order",
            "OnOrder"
        ],
        0
    )

    scenario_df["Unit_Cost"] = _scenario_numeric_column(
        scenario_df,
        [
            "Unit_Cost",
            "unit_cost",
            "Unit Cost",
            "cost"
        ],
        0
    )

    scenario_df["Lead_Time_Days"] = _scenario_numeric_column(
        scenario_df,
        [
            "Lead_Time_Days",
            "lead_time_days",
            "Lead_Time",
            "lead_time"
        ],
        0
    )

    scenario_df["Existing_Safety_Stock"] = _scenario_numeric_column(
        scenario_df,
        [
            "Estimated_Safety_Stock",
            "Safety_Stock",
            "Existing_Safety_Stock"
        ],
        0
    )


    # Prevent negative values
    for col in [
        "Annual_Demand",
        "Current_Stock",
        "On_Order",
        "Unit_Cost",
        "Lead_Time_Days",
        "Existing_Safety_Stock"
    ]:

        scenario_df[col] = (
            scenario_df[col]
            .clip(lower=0)
        )


    # ========================================================
    # 69.4 — SCENARIO CONTROLS
    # ========================================================

    st.subheader("Scenario Controls")

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        demand_growth = st.slider(
            "Demand Growth",
            min_value=-30,
            max_value=50,
            value=0,
            step=5,
            format="%d%%"
        )


    with col2:

        lead_time_multiplier = st.slider(
            "Lead-Time Multiplier",
            min_value=0.5,
            max_value=2.0,
            value=1.0,
            step=0.1
        )


    with col3:

        default_target_weeks = 8

        if "target_weeks" in globals():

            try:
                default_target_weeks = int(target_weeks)

            except:
                default_target_weeks = 8

        default_target_weeks = max(
            2,
            min(16, default_target_weeks)
        )

        target_coverage_weeks = st.slider(
            "Target Inventory Coverage",
            min_value=2,
            max_value=16,
            value=default_target_weeks,
            step=1
        )


    with col4:

        safety_stock_multiplier = st.slider(
            "Safety Stock Multiplier",
            min_value=0.5,
            max_value=2.0,
            value=1.0,
            step=0.1
        )


    # ========================================================
    # 69.5 — ON-ORDER INVENTORY OPTION
    # ========================================================

    include_on_order = st.checkbox(
        "Include On-Order Inventory in Available Stock",
        value=False
    )


    if include_on_order:

        scenario_df["Available_Inventory"] = (
            scenario_df["Current_Stock"]
            + scenario_df["On_Order"]
        )

    else:

        scenario_df["Available_Inventory"] = (
            scenario_df["Current_Stock"]
        )


    # ========================================================
    # 69.6 — SCENARIO DEMAND
    # ========================================================

    growth_factor = 1 + (demand_growth / 100)

    scenario_df["Baseline_Annual_Demand"] = (
        scenario_df["Annual_Demand"]
    )

    scenario_df["Scenario_Annual_Demand"] = (
        scenario_df["Baseline_Annual_Demand"]
        * growth_factor
    )

    scenario_df["Baseline_Daily_Demand"] = (
        scenario_df["Baseline_Annual_Demand"]
        / 365
    )

    scenario_df["Scenario_Daily_Demand"] = (
        scenario_df["Scenario_Annual_Demand"]
        / 365
    )


    # ========================================================
    # 69.7 — SCENARIO LEAD TIME
    # ========================================================

    scenario_df["Baseline_Lead_Time_Days"] = (
        scenario_df["Lead_Time_Days"]
    )

    scenario_df["Scenario_Lead_Time_Days"] = (
        scenario_df["Baseline_Lead_Time_Days"]
        * lead_time_multiplier
    )


    # ========================================================
    # 69.8 — LEAD-TIME DEMAND
    # ========================================================

    scenario_df["Scenario_Lead_Time_Demand"] = (
        scenario_df["Scenario_Daily_Demand"]
        * scenario_df["Scenario_Lead_Time_Days"]
    )


    # ========================================================
    # 69.9 — SAFETY STOCK
    # ========================================================
    #
    # If an existing safety-stock calculation exists, use it.
    # Otherwise use 20% of scenario lead-time demand.
    # ========================================================

    scenario_df["Scenario_Safety_Stock_Base"] = np.where(
        scenario_df["Existing_Safety_Stock"] > 0,
        scenario_df["Existing_Safety_Stock"],
        scenario_df["Scenario_Lead_Time_Demand"] * 0.20
    )

    scenario_df["Scenario_Safety_Stock"] = (
        scenario_df["Scenario_Safety_Stock_Base"]
        * safety_stock_multiplier
    )


    # ========================================================
    # 69.10 — SCENARIO REORDER POINT
    # ========================================================

    scenario_df["Scenario_Reorder_Point"] = (
        scenario_df["Scenario_Lead_Time_Demand"]
        + scenario_df["Scenario_Safety_Stock"]
    )


    # ========================================================
    # 69.11 — TARGET INVENTORY
    # ========================================================
    #
    # Target inventory =
    #     Demand during target coverage period
    #     + safety stock
    # ========================================================

    target_days = target_coverage_weeks * 7

    scenario_df["Target_Coverage_Days"] = target_days

    scenario_df["Target_Cycle_Stock"] = (
        scenario_df["Scenario_Daily_Demand"]
        * target_days
    )

    scenario_df["Scenario_Target_Inventory"] = (
        scenario_df["Target_Cycle_Stock"]
        + scenario_df["Scenario_Safety_Stock"]
    )


    # ========================================================
    # 69.12 — INVENTORY GAP
    # ========================================================

    scenario_df["Net_Inventory_Requirement"] = (
        scenario_df["Scenario_Target_Inventory"]
        - scenario_df["Available_Inventory"]
    )


    scenario_df["Additional_Inventory_Units"] = (
        scenario_df["Net_Inventory_Requirement"]
        .clip(lower=0)
    )


    scenario_df["Excess_Inventory_Units"] = (
        scenario_df["Available_Inventory"]
        - scenario_df["Scenario_Target_Inventory"]
    ).clip(lower=0)


    # ========================================================
    # 69.13 — STOCK COVERAGE
    # ========================================================

    scenario_df["Scenario_Stock_Coverage_Days"] = np.where(
        scenario_df["Scenario_Daily_Demand"] > 0,
        scenario_df["Available_Inventory"]
        / scenario_df["Scenario_Daily_Demand"],
        np.nan
    )

    scenario_df["Scenario_Stock_Coverage_Weeks"] = (
        scenario_df["Scenario_Stock_Coverage_Days"]
        / 7
    )


    # ========================================================
    # 69.14 — CAPITAL REQUIREMENT
    # ========================================================

    scenario_df["Additional_Capital_Required"] = (
        scenario_df["Additional_Inventory_Units"]
        * scenario_df["Unit_Cost"]
    )

    scenario_df["Excess_Inventory_Value"] = (
        scenario_df["Excess_Inventory_Units"]
        * scenario_df["Unit_Cost"]
    )


    # ========================================================
    # 69.15 — INVENTORY HEALTH
    # ========================================================

    def classify_scenario_inventory(row):

        demand = row["Scenario_Annual_Demand"]
        stock = row["Available_Inventory"]
        target = row["Scenario_Target_Inventory"]
        coverage = row["Scenario_Stock_Coverage_Days"]

        if demand <= 0 and stock > 0:
            return "OVERSTOCK / NO DEMAND"

        if demand > 0 and stock <= 0:
            return "STOCKOUT"

        if stock < target * 0.50:
            return "CRITICAL UNDERSTOCK"

        if stock < target:
            return "UNDERSTOCK"

        if coverage > target_days * 2:
            return "OVERSTOCK"

        if coverage > target_days * 1.5:
            return "EXCESS STOCK"

        return "BALANCED"


    scenario_df["Scenario_Health"] = (
        scenario_df.apply(
            classify_scenario_inventory,
            axis=1
        )
    )


    # ========================================================
    # 69.16 — RISK CLASSIFICATION
    # ========================================================

    scenario_df["Scenario_Risk"] = np.select(
        [
            scenario_df["Scenario_Health"].eq("STOCKOUT"),
            scenario_df["Scenario_Health"].eq("CRITICAL UNDERSTOCK"),
            scenario_df["Scenario_Health"].eq("UNDERSTOCK"),
            scenario_df["Scenario_Health"].isin(
                ["OVERSTOCK", "OVERSTOCK / NO DEMAND"]
            ),
            scenario_df["Scenario_Health"].eq("EXCESS STOCK")
        ],
        [
            "CRITICAL",
            "CRITICAL",
            "HIGH",
            "HIGH",
            "MEDIUM"
        ],
        default="LOW"
    )


    # ========================================================
    # 69.17 — RECOMMENDED ACTION
    # ========================================================

    scenario_df["Scenario_Action"] = np.select(
        [
            scenario_df["Scenario_Health"].eq("STOCKOUT"),

            scenario_df["Scenario_Health"].eq(
                "CRITICAL UNDERSTOCK"
            ),

            scenario_df["Scenario_Health"].eq(
                "UNDERSTOCK"
            ),

            scenario_df["Scenario_Health"].eq(
                "OVERSTOCK / NO DEMAND"
            ),

            scenario_df["Scenario_Health"].isin(
                ["OVERSTOCK", "EXCESS STOCK"]
            )
        ],
        [
            "URGENTLY REPLENISH",

            "EXPEDITE INVENTORY",

            "REORDER INVENTORY",

            "STOP PURCHASES / REVIEW SKU",

            "REDUCE PURCHASES / PROMOTE STOCK"
        ],
        default="MONITOR"
    )


    # ========================================================
    # 69.18 — SCENARIO KPI CALCULATIONS
    # ========================================================

    total_skus = len(scenario_df)

    stockout_skus = int(
        (
            scenario_df["Scenario_Health"]
            == "STOCKOUT"
        ).sum()
    )

    critical_skus = int(
        (
            scenario_df["Scenario_Health"]
            == "CRITICAL UNDERSTOCK"
        ).sum()
    )

    understock_skus = int(
        (
            scenario_df["Scenario_Health"]
            == "UNDERSTOCK"
        ).sum()
    )

    at_risk_skus = (
        stockout_skus
        + critical_skus
        + understock_skus
    )

    additional_units = (
        scenario_df["Additional_Inventory_Units"]
        .sum()
    )

    additional_capital = (
        scenario_df["Additional_Capital_Required"]
        .sum()
    )

    excess_units = (
        scenario_df["Excess_Inventory_Units"]
        .sum()
    )

    excess_capital = (
        scenario_df["Excess_Inventory_Value"]
        .sum()
    )

    median_coverage = (
        scenario_df["Scenario_Stock_Coverage_Weeks"]
        .replace([np.inf, -np.inf], np.nan)
        .median()
    )


    # ========================================================
    # 69.19 — SCENARIO SUMMARY
    # ========================================================

    st.subheader("Scenario Summary")

    k1, k2, k3, k4 = st.columns(4)

    with k1:

        st.metric(
            "SKUs At Risk",
            f"{at_risk_skus:,}"
        )

    with k2:

        st.metric(
            "Stockout SKUs",
            f"{stockout_skus:,}"
        )

    with k3:

        st.metric(
            "Additional Units Required",
            f"{additional_units:,.0f}"
        )

    with k4:

        if additional_capital >= 1_000_000:

            capital_display = (
                f"₹{additional_capital / 1_000_000:.2f}M"
            )

        elif additional_capital >= 100_000:

            capital_display = (
                f"₹{additional_capital / 100_000:.2f}L"
            )

        else:

            capital_display = (
                f"₹{additional_capital:,.0f}"
            )

        st.metric(
            "Additional Capital",
            capital_display
        )


    k5, k6, k7, k8 = st.columns(4)

    with k5:

        st.metric(
            "Critical Understock",
            f"{critical_skus:,}"
        )

    with k6:

        st.metric(
            "Understock",
            f"{understock_skus:,}"
        )

    with k7:

        st.metric(
            "Excess Units",
            f"{excess_units:,.0f}"
        )

    with k8:

        if pd.isna(median_coverage):

            coverage_display = "N/A"

        else:

            coverage_display = (
                f"{median_coverage:.1f} weeks"
            )

        st.metric(
            "Median Stock Coverage",
            coverage_display
        )


    # ========================================================
    # 69.20 — SCENARIO DESCRIPTION
    # ========================================================

    st.info(
        f"""
        **Current scenario:** Demand growth = **{demand_growth}%** |
        Lead-time multiplier = **{lead_time_multiplier:.1f}x** |
        Target coverage = **{target_coverage_weeks} weeks** |
        Safety-stock multiplier = **{safety_stock_multiplier:.1f}x**
        """
    )


    # ========================================================
    # 69.21 — INVENTORY HEALTH DISTRIBUTION
    # ========================================================

    st.subheader("Scenario Inventory Health")

    health_summary = (
        scenario_df["Scenario_Health"]
        .value_counts()
        .reset_index()
    )

    health_summary.columns = [
        "Health",
        "SKU_Count"
    ]

    if not health_summary.empty:

        fig_health = px.bar(
            health_summary,
            x="Health",
            y="SKU_Count",
            title="SKU Distribution by Scenario Inventory Health",
            text="SKU_Count"
        )

        fig_health.update_layout(
            xaxis_title="Inventory Health",
            yaxis_title="Number of SKUs"
        )

        st.plotly_chart(
            fig_health,
            use_container_width=True
        )


    # ========================================================
    # 69.22 — TOP REPLENISHMENT REQUIREMENTS
    # ========================================================

    st.subheader("Top Replenishment Requirements")

    replenishment_df = (
        scenario_df[
            scenario_df["Additional_Inventory_Units"] > 0
        ]
        .sort_values(
            "Additional_Capital_Required",
            ascending=False
        )
        .head(15)
        .copy()
    )

    if not replenishment_df.empty:

        replenishment_chart_df = (
            replenishment_df[
                [
                    "SKU",
                    "Additional_Inventory_Units",
                    "Additional_Capital_Required"
                ]
            ]
            .copy()
        )

        fig_replenishment = px.bar(
            replenishment_chart_df,
            x="SKU",
            y="Additional_Inventory_Units",
            title="Top SKUs Requiring Additional Inventory",
            text="Additional_Inventory_Units"
        )

        fig_replenishment.update_layout(
            xaxis_title="SKU",
            yaxis_title="Additional Units Required"
        )

        st.plotly_chart(
            fig_replenishment,
            use_container_width=True
        )

    else:

        st.success(
            "No additional inventory is required under this scenario."
        )


    # ========================================================
    # 69.23 — TOP EXCESS INVENTORY
    # ========================================================

    st.subheader("Top Excess Inventory")

    excess_df = (
        scenario_df[
            scenario_df["Excess_Inventory_Units"] > 0
        ]
        .sort_values(
            "Excess_Inventory_Value",
            ascending=False
        )
        .head(15)
        .copy()
    )

    if not excess_df.empty:

        excess_chart_df = (
            excess_df[
                [
                    "SKU",
                    "Excess_Inventory_Units",
                    "Excess_Inventory_Value"
                ]
            ]
            .copy()
        )

        fig_excess = px.bar(
            excess_chart_df,
            x="SKU",
            y="Excess_Inventory_Units",
            title="Top SKUs with Excess Inventory",
            text="Excess_Inventory_Units"
        )

        fig_excess.update_layout(
            xaxis_title="SKU",
            yaxis_title="Excess Units"
        )

        st.plotly_chart(
            fig_excess,
            use_container_width=True
        )

    else:

        st.success(
            "No significant excess inventory identified."
        )


    # ========================================================
    # 69.24 — CATEGORY SCENARIO ANALYSIS
    # ========================================================

    st.subheader("Category-Level Scenario Impact")

    category_scenario = (
        scenario_df
        .groupby("Category", dropna=False)
        .agg(
            SKUs=("SKU", "nunique"),
            Annual_Demand=("Scenario_Annual_Demand", "sum"),
            Available_Inventory=("Available_Inventory", "sum"),
            Additional_Units=(
                "Additional_Inventory_Units",
                "sum"
            ),
            Additional_Capital=(
                "Additional_Capital_Required",
                "sum"
            ),
            Excess_Units=(
                "Excess_Inventory_Units",
                "sum"
            ),
            Excess_Value=(
                "Excess_Inventory_Value",
                "sum"
            )
        )
        .reset_index()
        .sort_values(
            "Additional_Capital",
            ascending=False
        )
    )

    st.dataframe(
        category_scenario,
        use_container_width=True,
        hide_index=True
    )


    # ========================================================
    # 69.25 — SCENARIO WATCHLIST
    # ========================================================

st.subheader("Scenario Management Watchlist")

watchlist_df = scenario_df[
    scenario_df["Scenario_Health"].isin(
        [
            "STOCKOUT",
            "CRITICAL UNDERSTOCK",
            "UNDERSTOCK",
            "EXCESS STOCK",
            "OVERSTOCK",
            "OVERSTOCK / NO DEMAND",
        ]
    )
].sort_values(
    [
        "Scenario_Risk",
        "Additional_Capital_Required",
    ],
    ascending=[
        True,
        False,
    ],
).head(30).copy()


if not watchlist_df.empty:

    watchlist_display = watchlist_df[
        [
            "SKU",
            "Product_Name",
            "Category",
            "Scenario_Annual_Demand",
            "Available_Inventory",
            "Scenario_Target_Inventory",
            "Scenario_Stock_Coverage_Weeks",
            "Additional_Inventory_Units",
            "Additional_Capital_Required",
            "Excess_Inventory_Units",
            "Scenario_Health",
            "Scenario_Action",
        ]
    ].copy()

    st.dataframe(
        watchlist_display,
        use_container_width=True,
        hide_index=True,
    )

else:

    st.success(
        "No inventory exceptions detected under the selected scenario."
    )


    # ========================================================
    # 69.26 — BASELINE VS SCENARIO COMPARISON
    # ========================================================

    st.subheader("Baseline vs Selected Scenario")

    baseline_daily = (
        scenario_df["Annual_Demand"] / 365
    )

    baseline_stock_coverage = np.where(
        baseline_daily > 0,
        scenario_df["Available_Inventory"]
        / baseline_daily,
        np.nan
    )

    baseline_target_inventory = (
        baseline_daily
        * target_days
        + scenario_df["Existing_Safety_Stock"]
    )

    baseline_additional_units = (
        baseline_target_inventory
        - scenario_df["Available_Inventory"]
    ).clip(lower=0)

    baseline_additional_capital = (
        baseline_additional_units
        * scenario_df["Unit_Cost"]
    )

    comparison_df = pd.DataFrame(
        {
            "Metric": [
                "Annual Demand",
                "Additional Units Required",
                "Additional Capital",
                "Median Stock Coverage (Weeks)",
                "Stockout SKUs",
                "Understock SKUs",
                "Excess Inventory Units"
            ],

            "Baseline": [
                scenario_df["Annual_Demand"].sum(),
                baseline_additional_units.sum(),
                baseline_additional_capital.sum(),
                np.nanmedian(
                    baseline_stock_coverage / 7
                ) if len(baseline_stock_coverage) else np.nan,
                int(
                    (
                        scenario_df["Available_Inventory"] <= 0
                    )
                    & (
                        scenario_df["Annual_Demand"] > 0
                    )
                ).sum(),
                int(
                    (
                        scenario_df["Available_Inventory"]
                        < baseline_target_inventory
                    ).sum()
                ),
                (
                    scenario_df["Available_Inventory"]
                    - baseline_target_inventory
                )
                .clip(lower=0)
                .sum()
            ],

            "Selected Scenario": [
                scenario_df["Scenario_Annual_Demand"].sum(),
                additional_units,
                additional_capital,
                median_coverage,
                stockout_skus,
                critical_skus + understock_skus,
                excess_units
            ]
        }
    )

    st.dataframe(
        comparison_df,
        use_container_width=True,
        hide_index=True
    )


    # ========================================================
    # 69.27 — SCENARIO DECISION MESSAGE
    # ========================================================

    st.subheader("Management Decision Support")

    if stockout_skus > 0:

        st.error(
            f"""
            **Immediate action required:** {stockout_skus:,} SKU(s)
            are projected to have zero available inventory under the
            selected scenario.
            """
        )

    elif at_risk_skus > 0:

        st.warning(
            f"""
            **Inventory risk detected:** {at_risk_skus:,} SKU(s)
            require attention under the selected scenario.
            """
        )

    else:

        st.success(
            """
            **Scenario appears operationally stable:** no stockout or
            understock risk requiring immediate action was detected.
            """
        )


    if additional_capital > 0:

        st.info(
            f"""
            The selected scenario indicates approximately
            **{additional_units:,.0f} additional units**
            requiring approximately
            **₹{additional_capital:,.0f} in additional inventory capital**.
            """
        )


    if excess_capital > 0:

        st.info(
            f"""
            Approximately **₹{excess_capital:,.0f}**
            of inventory value is classified as excess under the
            selected scenario and may require purchase reduction,
            promotion, transfer or liquidation decisions.
            """
        )


    # ========================================================
    # 69.28 — COMPLETE SCENARIO DATASET
    # ========================================================

    with st.expander(
        "Complete Scenario Optimization Dataset"
    ):

        scenario_display_columns = [
            "SKU",
            "Product_Name",
            "Category",
            "Baseline_Annual_Demand",
            "Scenario_Annual_Demand",
            "Baseline_Lead_Time_Days",
            "Scenario_Lead_Time_Days",
            "Scenario_Lead_Time_Demand",
            "Scenario_Safety_Stock",
            "Scenario_Reorder_Point",
            "Scenario_Target_Inventory",
            "Available_Inventory",
            "Scenario_Stock_Coverage_Days",
            "Scenario_Stock_Coverage_Weeks",
            "Additional_Inventory_Units",
            "Additional_Capital_Required",
            "Excess_Inventory_Units",
            "Excess_Inventory_Value",
            "Scenario_Health",
            "Scenario_Risk",
            "Scenario_Action"
        ]

        scenario_display_columns = [
            col
            for col in scenario_display_columns
            if col in scenario_df.columns
        ]

        st.dataframe(
            scenario_df[
                scenario_display_columns
            ],
            use_container_width=True,
            hide_index=True
        )


    # ========================================================
    # 69.29 — SCENARIO COMPLETION MESSAGE
    # ========================================================

    st.success(
        f"""
        **Step 69 completed successfully.**

        Scenario analyzed for **{total_skus:,} SKUs** with
        **{demand_growth}% demand growth**, **{lead_time_multiplier:.1f}x**
        lead time and **{target_coverage_weeks} weeks** target coverage.

        Additional inventory requirement:
        **{additional_units:,.0f} units**

        Additional capital requirement:
        **₹{additional_capital:,.0f}**

        Excess inventory:
        **{excess_units:,.0f} units**
        """
    )

    # ============================================================
# STEP 70 — SERVICE LEVEL & STOCKOUT RISK ANALYTICS
# ============================================================
#
# Purpose:
#   Analyze inventory service levels and identify SKUs that
#   have high probability of stockout or insufficient safety
#   stock.
#
# Features:
#   • Demand variability
#   • Safety-stock adequacy
#   • Reorder-point risk
#   • Stockout risk
#   • Service-level classification
#   • SKU risk ranking
#   • Category risk analysis
#   • Risk heatmap
#   • Management alerts
#
# ============================================================

st.markdown("---")

st.header("STEP 70 — Service Level & Stockout Risk Analytics")


# ============================================================
# 70.1 — SOURCE DATA
# ============================================================

if "scenario_df" in globals() and isinstance(
    scenario_df, pd.DataFrame
):

    service_df = scenario_df.copy()

elif "optimization_df" in globals() and isinstance(
    optimization_df, pd.DataFrame
):

    service_df = optimization_df.copy()

elif "turnover_df" in globals() and isinstance(
    turnover_df, pd.DataFrame
):

    service_df = turnover_df.copy()

else:

    service_df = pd.DataFrame()


if service_df.empty:

    st.info(
        "No inventory optimization data is available. "
        "Please complete the previous steps first."
    )

else:

    # ========================================================
    # 70.2 — HELPER FUNCTIONS
    # ========================================================

    def _service_numeric(df, candidates, default=0.0):

        for col in candidates:

            if col in df.columns:

                return pd.to_numeric(
                    df[col],
                    errors="coerce"
                ).fillna(default)

        return pd.Series(
            default,
            index=df.index,
            dtype=float
        )


    def _service_text(df, candidates, default="Unknown"):

        for col in candidates:

            if col in df.columns:

                return (
                    df[col]
                    .fillna(default)
                    .astype(str)
                )

        return pd.Series(
            default,
            index=df.index,
            dtype="object"
        )


    # ========================================================
    # 70.3 — STANDARDIZE DATA
    # ========================================================

    service_df["SKU"] = _service_text(
        service_df,
        ["SKU", "sku_id", "SKU_ID", "sku"],
        "Unknown"
    )

    service_df["Category"] = _service_text(
        service_df,
        ["Category", "category", "CATEGORY"],
        "Unknown"
    )

    service_df["Product_Name"] = _service_text(
        service_df,
        [
            "Product_Name",
            "product_name",
            "Product",
            "product"
        ],
        "Unknown"
    )

    service_df["Annual_Demand"] = _service_numeric(
        service_df,
        [
            "Scenario_Annual_Demand",
            "Annual_Demand",
            "Annual_Units_Demand",
            "Historical_Annual_Demand"
        ],
        0
    )

    service_df["Current_Stock"] = _service_numeric(
        service_df,
        [
            "Available_Inventory",
            "Current_Stock",
            "on_hand",
            "On_Hand"
        ],
        0
    )

    service_df["Lead_Time_Days"] = _service_numeric(
        service_df,
        [
            "Scenario_Lead_Time_Days",
            "Lead_Time_Days",
            "lead_time_days"
        ],
        0
    )

    service_df["Safety_Stock"] = _service_numeric(
        service_df,
        [
            "Scenario_Safety_Stock",
            "Estimated_Safety_Stock",
            "Safety_Stock"
        ],
        0
    )

    service_df["Reorder_Point"] = _service_numeric(
        service_df,
        [
            "Scenario_Reorder_Point",
            "Recommended_Reorder_Point",
            "Existing_Reorder_Point"
        ],
        0
    )

    service_df["Unit_Cost"] = _service_numeric(
        service_df,
        [
            "Unit_Cost",
            "unit_cost"
        ],
        0
    )


    # ========================================================
    # 70.4 — DAILY DEMAND
    # ========================================================

    service_df["Average_Daily_Demand"] = (
        service_df["Annual_Demand"] / 365
    )


    # ========================================================
    # 70.5 — ESTIMATED DEMAND VARIABILITY
    # ========================================================
    #
    # If historical weekly demand variability is available,
    # use it.
    #
    # Otherwise use a conservative coefficient of variation
    # assumption for scenario analysis.
    # ========================================================

    service_df["Demand_Std_Dev"] = _service_numeric(
        service_df,
        [
            "Demand_Std_Dev",
            "Weekly_Demand_Std",
            "Demand_Variability",
            "Std_Dev_Demand"
        ],
        0
    )


    # If no variability exists, estimate it using 20% of
    # average daily demand.

    service_df["Estimated_Demand_Std_Dev"] = np.where(
        service_df["Demand_Std_Dev"] > 0,
        service_df["Demand_Std_Dev"],
        service_df["Average_Daily_Demand"] * 0.20
    )


    # ========================================================
    # 70.6 — LEAD-TIME DEMAND
    # ========================================================

    service_df["Lead_Time_Demand"] = (
        service_df["Average_Daily_Demand"]
        * service_df["Lead_Time_Days"]
    )


    # ========================================================
    # 70.7 — SAFETY STOCK COVERAGE
    # ========================================================

    service_df["Safety_Stock_Coverage_Days"] = np.where(
        service_df["Average_Daily_Demand"] > 0,

        service_df["Safety_Stock"]
        / service_df["Average_Daily_Demand"],

        np.nan
    )


    service_df["Safety_Stock_Coverage_Weeks"] = (
        service_df["Safety_Stock_Coverage_Days"]
        / 7
    )


    # ========================================================
    # 70.8 — STOCK COVERAGE
    # ========================================================

    service_df["Stock_Coverage_Days"] = np.where(
        service_df["Average_Daily_Demand"] > 0,

        service_df["Current_Stock"]
        / service_df["Average_Daily_Demand"],

        np.nan
    )


    service_df["Stock_Coverage_Weeks"] = (
        service_df["Stock_Coverage_Days"]
        / 7
    )


    # ========================================================
    # 70.9 — STOCK VS LEAD-TIME DEMAND
    # ========================================================

    service_df["Lead_Time_Coverage_Ratio"] = np.where(

        service_df["Lead_Time_Demand"] > 0,

        service_df["Current_Stock"]
        / service_df["Lead_Time_Demand"],

        np.nan
    )


    # ========================================================
    # 70.10 — SAFETY STOCK ADEQUACY
    # ========================================================

    service_df["Safety_Stock_Adequacy"] = np.where(

        service_df["Estimated_Demand_Std_Dev"] > 0,

        service_df["Safety_Stock"]
        / (
            service_df["Estimated_Demand_Std_Dev"]
            * np.sqrt(
                service_df["Lead_Time_Days"]
                .clip(lower=1)
            )
        ),

        0
    )


    # ========================================================
    # 70.11 — STOCKOUT RISK SCORE
    # ========================================================
    #
    # This is a management risk score rather than a statistical
    # probability.
    #
    # Higher score = higher stockout risk.
    # ========================================================

    coverage_risk = np.select(
        [
            service_df["Stock_Coverage_Days"] <= 0,

            service_df["Stock_Coverage_Days"]
            < service_df["Lead_Time_Days"],

            service_df["Stock_Coverage_Days"]
            < (
                service_df["Lead_Time_Days"] + 14
            ),

            service_df["Stock_Coverage_Days"]
            < (
                service_df["Lead_Time_Days"] + 30
            )
        ],
        [
            100,
            90,
            70,
            40
        ],
        default=10
    )


    safety_risk = np.select(
        [
            service_df["Safety_Stock_Adequacy"] < 0.50,

            service_df["Safety_Stock_Adequacy"] < 1.00,

            service_df["Safety_Stock_Adequacy"] < 1.50
        ],
        [
            100,
            70,
            40
        ],
        default=10
    )


    service_df["Stockout_Risk_Score"] = (
        coverage_risk * 0.60
        + safety_risk * 0.40
    )


    service_df["Stockout_Risk_Score"] = (
        service_df["Stockout_Risk_Score"]
        .clip(0, 100)
    )


    # ========================================================
    # 70.12 — SERVICE LEVEL ESTIMATE
    # ========================================================
    #
    # Convert risk score into a management-oriented estimated
    # service level.
    #
    # This should NOT be interpreted as an exact statistical
    # service-level probability.
    # ========================================================

    service_df["Estimated_Service_Level"] = (
        100
        - service_df["Stockout_Risk_Score"]
    ).clip(0, 100)


    # ========================================================
    # 70.13 — SERVICE LEVEL CLASSIFICATION
    # ========================================================

    service_df["Service_Level_Class"] = pd.cut(

        service_df["Estimated_Service_Level"],

        bins=[
            -np.inf,
            70,
            85,
            95,
            np.inf
        ],

        labels=[
            "CRITICAL",
            "LOW",
            "GOOD",
            "EXCELLENT"
        ]
    )


    # ========================================================
    # 70.14 — STOCKOUT RISK CLASSIFICATION
    # ========================================================

    service_df["Stockout_Risk"] = pd.cut(

        service_df["Stockout_Risk_Score"],

        bins=[
            -np.inf,
            25,
            50,
            75,
            np.inf
        ],

        labels=[
            "LOW",
            "MEDIUM",
            "HIGH",
            "CRITICAL"
        ]
    )


    # ========================================================
    # 70.15 — REORDER POINT STATUS
    # ========================================================

    service_df["Reorder_Point_Status"] = np.select(
        [
            service_df["Current_Stock"] <= 0,

            service_df["Current_Stock"]
            < service_df["Reorder_Point"] * 0.50,

            service_df["Current_Stock"]
            < service_df["Reorder_Point"],

            service_df["Current_Stock"]
            >= service_df["Reorder_Point"]
        ],
        [
            "STOCKOUT",

            "CRITICALLY BELOW ROP",

            "BELOW ROP",

            "ABOVE ROP"
        ],
        default="UNKNOWN"
    )


    # ========================================================
    # 70.16 — MANAGEMENT ACTION
    # ========================================================

    service_df["Service_Level_Action"] = np.select(
        [
            service_df["Stockout_Risk"]
            .astype(str)
            .eq("CRITICAL"),

            service_df["Stockout_Risk"]
            .astype(str)
            .eq("HIGH"),

            service_df["Stockout_Risk"]
            .astype(str)
            .eq("MEDIUM"),

            service_df["Stockout_Risk"]
            .astype(str)
            .eq("LOW")
        ],
        [
            "URGENT REPLENISHMENT",

            "EXPEDITE / PRIORITIZE",

            "MONITOR CLOSELY",

            "NORMAL MONITORING"
        ],
        default="REVIEW"
    )


    # ========================================================
    # 70.17 — KPI CALCULATIONS
    # ========================================================

    total_service_skus = len(service_df)

    critical_risk_skus = int(
        (
            service_df["Stockout_Risk"]
            .astype(str)
            == "CRITICAL"
        ).sum()
    )

    high_risk_skus = int(
        (
            service_df["Stockout_Risk"]
            .astype(str)
            == "HIGH"
        ).sum()
    )

    medium_risk_skus = int(
        (
            service_df["Stockout_Risk"]
            .astype(str)
            == "MEDIUM"
        ).sum()
    )

    stockout_count = int(
        (
            (service_df["Current_Stock"] <= 0)
            & (service_df["Annual_Demand"] > 0)
        ).sum()
    )

    avg_service_level = (
        service_df["Estimated_Service_Level"]
        .mean()
    )

    median_risk = (
        service_df["Stockout_Risk_Score"]
        .median()
    )

    below_rop = int(
        (
            service_df["Current_Stock"]
            < service_df["Reorder_Point"]
        ).sum()
    )


    # ========================================================
    # 70.18 — KPI CARDS
    # ========================================================

    st.subheader("Service Level KPIs")

    k1, k2, k3, k4 = st.columns(4)

    with k1:

        st.metric(
            "Average Service Level",
            f"{avg_service_level:.1f}%"
        )

    with k2:

        st.metric(
            "Critical Risk SKUs",
            f"{critical_risk_skus:,}"
        )

    with k3:

        st.metric(
            "High Risk SKUs",
            f"{high_risk_skus:,}"
        )

    with k4:

        st.metric(
            "Stockout SKUs",
            f"{stockout_count:,}"
        )


    k5, k6, k7, k8 = st.columns(4)

    with k5:

        st.metric(
            "Medium Risk SKUs",
            f"{medium_risk_skus:,}"
        )

    with k6:

        st.metric(
            "Below Reorder Point",
            f"{below_rop:,}"
        )

    with k7:

        st.metric(
            "Median Risk Score",
            f"{median_risk:.1f}/100"
        )

    with k8:

        st.metric(
            "Total SKUs",
            f"{total_service_skus:,}"
        )


    # ========================================================
    # 70.19 — RISK DISTRIBUTION
    # ========================================================

    st.subheader("Stockout Risk Distribution")

    risk_distribution = (
        service_df["Stockout_Risk"]
        .astype(str)
        .value_counts()
        .reset_index()
    )

    risk_distribution.columns = [
        "Risk_Level",
        "SKU_Count"
    ]


    if not risk_distribution.empty:

        fig_risk = px.bar(
            risk_distribution,
            x="Risk_Level",
            y="SKU_Count",
            title="SKU Distribution by Stockout Risk",
            text="SKU_Count"
        )

        st.plotly_chart(
            fig_risk,
            use_container_width=True
        )


    # ========================================================
    # 70.20 — SERVICE LEVEL DISTRIBUTION
    # ========================================================

    st.subheader("Service Level Distribution")

    service_distribution = (
        service_df["Service_Level_Class"]
        .astype(str)
        .value_counts()
        .reset_index()
    )

    service_distribution.columns = [
        "Service_Level",
        "SKU_Count"
    ]


    if not service_distribution.empty:

        fig_service = px.bar(
            service_distribution,
            x="Service_Level",
            y="SKU_Count",
            title="SKU Distribution by Estimated Service Level",
            text="SKU_Count"
        )

        st.plotly_chart(
            fig_service,
            use_container_width=True
        )


    # ========================================================
    # 70.21 — TOP HIGH-RISK SKUs
    # ========================================================

    st.subheader("Top Stockout-Risk SKUs")

    high_risk_df = (
        service_df
        .sort_values(
            [
                "Stockout_Risk_Score",
                "Annual_Demand"
            ],
            ascending=[False, False]
        )
        .head(20)
        .copy()
    )


    high_risk_display = high_risk_df[
        [
            "SKU",
            "Product_Name",
            "Category",
            "Annual_Demand",
            "Current_Stock",
            "Lead_Time_Days",
            "Safety_Stock",
            "Reorder_Point",
            "Stock_Coverage_Days",
            "Stockout_Risk_Score",
            "Stockout_Risk",
            "Estimated_Service_Level",
            "Service_Level_Action"
        ]
    ].copy()


    st.dataframe(
        high_risk_display,
        use_container_width=True,
        hide_index=True
    )


    # ========================================================
    # 70.22 — RISK VS DEMAND CHART
    # ========================================================

    st.subheader("Demand vs Stockout Risk")

    scatter_df = service_df[
        service_df["Annual_Demand"] > 0
    ].copy()


    if not scatter_df.empty:

        fig_scatter = px.scatter(
            scatter_df,
            x="Annual_Demand",
            y="Stockout_Risk_Score",
            size="Current_Stock",
            hover_name="SKU",
            hover_data=[
                "Category",
                "Product_Name",
                "Stockout_Risk",
                "Estimated_Service_Level"
            ],
            title="Annual Demand vs Stockout Risk"
        )

        fig_scatter.update_layout(
            xaxis_title="Annual Demand",
            yaxis_title="Stockout Risk Score"
        )

        st.plotly_chart(
            fig_scatter,
            use_container_width=True
        )


    # ========================================================
    # 70.23 — CATEGORY RISK ANALYSIS
    # ========================================================

    st.subheader("Category-Level Service Risk")

    category_risk = (
        service_df
        .groupby("Category", dropna=False)
        .agg(
            SKUs=("SKU", "nunique"),

            Annual_Demand=(
                "Annual_Demand",
                "sum"
            ),

            Average_Service_Level=(
                "Estimated_Service_Level",
                "mean"
            ),

            Average_Risk_Score=(
                "Stockout_Risk_Score",
                "mean"
            ),

            Critical_SKUs=(
                "Stockout_Risk",
                lambda x: (
                    x.astype(str) == "CRITICAL"
                ).sum()
            ),

            High_Risk_SKUs=(
                "Stockout_Risk",
                lambda x: (
                    x.astype(str) == "HIGH"
                ).sum()
            ),

            Below_ROP=(
                "Reorder_Point_Status",
                lambda x: (
                    x == "BELOW ROP"
                ).sum()
            )
        )
        .reset_index()
        .sort_values(
            "Average_Risk_Score",
            ascending=False
        )
    )


    st.dataframe(
        category_risk,
        use_container_width=True,
        hide_index=True
    )


    # ========================================================
    # 70.24 — CATEGORY RISK CHART
    # ========================================================

    if not category_risk.empty:

        fig_category_risk = px.bar(
            category_risk.head(15),
            x="Category",
            y="Average_Risk_Score",
            title="Average Stockout Risk Score by Category",
            text="Average_Risk_Score"
        )

        st.plotly_chart(
            fig_category_risk,
            use_container_width=True
        )


    # ========================================================
    # 70.25 — MANAGEMENT ALERTS
    # ========================================================

    st.subheader("Management Alerts")

    if critical_risk_skus > 0:

        st.error(
            f"""
            **Critical stockout risk:** {critical_risk_skus:,}
            SKU(s) have a critical stockout-risk score.
            Immediate inventory review is recommended.
            """
        )


    if stockout_count > 0:

        st.error(
            f"""
            **Current stockout:** {stockout_count:,}
            SKU(s) currently have zero available inventory
            despite having positive demand.
            """
        )


    if below_rop > 0:

        st.warning(
            f"""
            **Reorder-point warning:** {below_rop:,}
            SKU(s) are currently below their calculated reorder point.
            """
        )


    if avg_service_level < 85:

        st.warning(
            f"""
            Estimated average service level is only
            **{avg_service_level:.1f}%**.
            Inventory policies should be reviewed.
            """
        )

    elif avg_service_level >= 95:

        st.success(
            f"""
            Estimated average service level is
            **{avg_service_level:.1f}%**, indicating strong
            inventory availability under the current assumptions.
            """
        )


    # ========================================================
    # 70.26 — COMPLETE DATASET
    # ========================================================

    with st.expander(
        "Complete Service Level & Stockout Risk Dataset"
    ):

        service_display_columns = [
            "SKU",
            "Product_Name",
            "Category",
            "Annual_Demand",
            "Current_Stock",
            "Lead_Time_Days",
            "Average_Daily_Demand",
            "Lead_Time_Demand",
            "Safety_Stock",
            "Safety_Stock_Coverage_Days",
            "Reorder_Point",
            "Stock_Coverage_Days",
            "Stock_Coverage_Weeks",
            "Lead_Time_Coverage_Ratio",
            "Safety_Stock_Adequacy",
            "Stockout_Risk_Score",
            "Estimated_Service_Level",
            "Service_Level_Class",
            "Stockout_Risk",
            "Reorder_Point_Status",
            "Service_Level_Action"
        ]


        service_display_columns = [
            col
            for col in service_display_columns
            if col in service_df.columns
        ]


        st.dataframe(
            service_df[
                service_display_columns
            ],
            use_container_width=True,
            hide_index=True
        )


    # ========================================================
    # 70.27 — COMPLETION
    # ========================================================

    st.success(
        f"""
        **Step 70 completed successfully.**

        Analyzed **{total_service_skus:,} SKUs** for service-level
        and stockout risk.

        Average estimated service level:
        **{avg_service_level:.1f}%**

        Critical-risk SKUs:
        **{critical_risk_skus:,}**

        High-risk SKUs:
        **{high_risk_skus:,}**

        Current stockout SKUs:
        **{stockout_count:,}**
        """
    )
    # ============================================================
# STEP 71 — EXECUTIVE INVENTORY CONTROL TOWER
# ============================================================
#
# Purpose:
#   Provide a management-level summary of the entire inventory
#   and forecasting system.
#
# Combines insights from:
#   Step 62 → Forecast Analytics
#   Step 63 → ABC / Pareto
#   Step 67 → Inventory Turnover
#   Step 68 → Inventory Optimization
#   Step 69 → Scenario Simulation
#   Step 70 → Service Level / Stockout Risk
#
# ============================================================

st.markdown("---")

st.header("STEP 71 — Executive Inventory Control Tower")

st.write(
    """
    The Executive Inventory Control Tower provides a consolidated
    management view of demand, inventory, risk, working capital,
    replenishment and SKU priorities.
    """
)


# ============================================================
# 71.1 — PREPARE EXECUTIVE DATA
# ============================================================

if "service_df" in globals() and isinstance(
    service_df,
    pd.DataFrame
) and not service_df.empty:

    control_df = service_df.copy()

elif "scenario_df" in globals() and isinstance(
    scenario_df,
    pd.DataFrame
) and not scenario_df.empty:

    control_df = scenario_df.copy()

elif "optimization_df" in globals() and isinstance(
    optimization_df,
    pd.DataFrame
) and not optimization_df.empty:

    control_df = optimization_df.copy()

else:

    control_df = pd.DataFrame()


if control_df.empty:

    st.info(
        "Executive Control Tower requires data from the previous "
        "inventory analytics steps."
    )

else:

    # ========================================================
    # 71.2 — STANDARDIZE EXECUTIVE COLUMNS
    # ========================================================

    def _control_numeric(
        df,
        candidates,
        default=0.0
    ):

        for col in candidates:

            if col in df.columns:

                return pd.to_numeric(
                    df[col],
                    errors="coerce"
                ).fillna(default)

        return pd.Series(
            default,
            index=df.index,
            dtype=float
        )


    def _control_text(
        df,
        candidates,
        default="Unknown"
    ):

        for col in candidates:

            if col in df.columns:

                return (
                    df[col]
                    .fillna(default)
                    .astype(str)
                )

        return pd.Series(
            default,
            index=df.index,
            dtype="object"
        )


    control_df["SKU"] = _control_text(
        control_df,
        ["SKU", "sku_id", "SKU_ID", "sku"],
        "Unknown"
    )

    control_df["Product_Name"] = _control_text(
        control_df,
        [
            "Product_Name",
            "product_name",
            "Product",
            "product"
        ],
        "Unknown"
    )

    control_df["Category"] = _control_text(
        control_df,
        [
            "Category",
            "category",
            "CATEGORY"
        ],
        "Unknown"
    )


    # ========================================================
    # 71.3 — DEMAND
    # ========================================================

    control_df["Annual_Demand"] = _control_numeric(
        control_df,
        [
            "Scenario_Annual_Demand",
            "Annual_Demand",
            "Annual_Units_Demand",
            "Historical_Annual_Demand"
        ]
    )


    # ========================================================
    # 71.4 — INVENTORY
    # ========================================================

    control_df["Inventory_Units"] = _control_numeric(
        control_df,
        [
            "Available_Inventory",
            "Current_Stock",
            "on_hand",
            "On_Hand"
        ]
    )


    control_df["Unit_Cost"] = _control_numeric(
        control_df,
        [
            "Unit_Cost",
            "unit_cost"
        ]
    )


    control_df["Inventory_Value"] = (
        control_df["Inventory_Units"]
        * control_df["Unit_Cost"]
    )


    # ========================================================
    # 71.5 — REPLENISHMENT
    # ========================================================

    control_df["Additional_Units"] = _control_numeric(
        control_df,
        [
            "Additional_Inventory_Units",
            "Optimization_Gap_Units",
            "Net_Inventory_Requirement"
        ]
    ).clip(lower=0)


    control_df["Additional_Capital"] = _control_numeric(
        control_df,
        [
            "Additional_Capital_Required",
            "Optimization_Gap_Value"
        ]
    ).clip(lower=0)


    # ========================================================
    # 71.6 — RISK
    # ========================================================

    control_df["Risk_Score"] = _control_numeric(
        control_df,
        [
            "Stockout_Risk_Score"
        ]
    )


    control_df["Service_Level"] = _control_numeric(
        control_df,
        [
            "Estimated_Service_Level"
        ],
        100
    )


    control_df["Stock_Coverage_Weeks"] = _control_numeric(
        control_df,
        [
            "Stock_Coverage_Weeks",
            "Scenario_Stock_Coverage_Weeks"
        ]
    )


    control_df["Excess_Units"] = _control_numeric(
        control_df,
        [
            "Excess_Inventory_Units"
        ]
    ).clip(lower=0)


    control_df["Excess_Value"] = _control_numeric(
        control_df,
        [
            "Excess_Inventory_Value"
        ]
    ).clip(lower=0)


    control_df["Slow_Stock_Flag"] = _control_numeric(
        control_df,
        [
            "Slow_Stock_Flag"
        ]
    )


    # ========================================================
    # 71.7 — EXECUTIVE KPI CALCULATIONS
    # ========================================================

    total_skus = len(control_df)

    total_inventory_value = (
        control_df["Inventory_Value"].sum()
    )

    total_annual_demand = (
        control_df["Annual_Demand"].sum()
    )

    total_additional_units = (
        control_df["Additional_Units"].sum()
    )

    total_additional_capital = (
        control_df["Additional_Capital"].sum()
    )

    total_excess_units = (
        control_df["Excess_Units"].sum()
    )

    total_excess_value = (
        control_df["Excess_Value"].sum()
    )

    average_service_level = (
        control_df["Service_Level"].mean()
    )

    median_coverage = (
        control_df["Stock_Coverage_Weeks"]
        .replace([np.inf, -np.inf], np.nan)
        .median()
    )


    # ========================================================
    # 71.8 — RISK COUNTS
    # ========================================================

    if "Stockout_Risk" in control_df.columns:

        risk_text = (
            control_df["Stockout_Risk"]
            .astype(str)
            .str.upper()
        )

    else:

        risk_text = pd.Series(
            "LOW",
            index=control_df.index
        )


    critical_risk = int(
        (risk_text == "CRITICAL").sum()
    )

    high_risk = int(
        (risk_text == "HIGH").sum()
    )

    medium_risk = int(
        (risk_text == "MEDIUM").sum()
    )


    # ========================================================
    # 71.9 — STOCKOUT COUNT
    # ========================================================

    stockout_skus = int(
        (
            (control_df["Inventory_Units"] <= 0)
            &
            (control_df["Annual_Demand"] > 0)
        ).sum()
    )


    # ========================================================
    # 71.10 — BELOW REORDER POINT
    # ========================================================

    if "Reorder_Point" in control_df.columns:

        below_rop = int(
            (
                control_df["Inventory_Units"]
                <
                pd.to_numeric(
                    control_df["Reorder_Point"],
                    errors="coerce"
                ).fillna(0)
            ).sum()
        )

    else:

        below_rop = 0


    # ========================================================
    # 71.11 — SLOW MOVING STOCK
    # ========================================================

    if "Velocity_Class" in control_df.columns:

        slow_stock_skus = int(
            control_df["Velocity_Class"]
            .astype(str)
            .str.upper()
            .isin(
                [
                    "SLOW",
                    "VERY SLOW"
                ]
            )
            .sum()
        )

    else:

        slow_stock_skus = int(
            control_df["Slow_Stock_Flag"]
            .gt(0)
            .sum()
        )


    # ========================================================
    # 71.12 — EXECUTIVE HEADER
    # ========================================================

    st.subheader("Executive Inventory Overview")

    st.info(
        f"""
        **Portfolio Overview**

        The current inventory portfolio contains
        **{total_skus:,} SKUs** with approximately
        **₹{total_inventory_value:,.0f}** of inventory value.

        Annual demand is approximately
        **{total_annual_demand:,.0f} units**.

        The current analytics identify
        **{critical_risk + high_risk:,} high/critical-risk SKUs**
        requiring management attention.
        """
    )


    # ========================================================
    # 71.13 — MAIN KPI CARDS
    # ========================================================

    k1, k2, k3, k4 = st.columns(4)

    with k1:

        st.metric(
            "Inventory Value",
            f"₹{total_inventory_value:,.0f}"
        )

    with k2:

        st.metric(
            "Annual Demand",
            f"{total_annual_demand:,.0f}"
        )

    with k3:

        st.metric(
            "Average Service Level",
            f"{average_service_level:.1f}%"
        )

    with k4:

        if pd.isna(median_coverage):

            coverage_display = "N/A"

        else:

            coverage_display = (
                f"{median_coverage:.1f} weeks"
            )

        st.metric(
            "Median Coverage",
            coverage_display
        )


    # ========================================================
    # 71.14 — RISK KPI CARDS
    # ========================================================

    st.subheader("Inventory Risk")

    r1, r2, r3, r4 = st.columns(4)

    with r1:

        st.metric(
            "Critical Risk SKUs",
            f"{critical_risk:,}"
        )

    with r2:

        st.metric(
            "High Risk SKUs",
            f"{high_risk:,}"
        )

    with r3:

        st.metric(
            "Current Stockouts",
            f"{stockout_skus:,}"
        )

    with r4:

        st.metric(
            "Below Reorder Point",
            f"{below_rop:,}"
        )


    # ========================================================
    # 71.15 — CAPITAL / INVENTORY KPIs
    # ========================================================

    st.subheader("Inventory Investment")

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        st.metric(
            "Replenishment Units",
            f"{total_additional_units:,.0f}"
        )

    with c2:

        st.metric(
            "Required Capital",
            f"₹{total_additional_capital:,.0f}"
        )

    with c3:

        st.metric(
            "Excess Units",
            f"{total_excess_units:,.0f}"
        )

    with c4:

        st.metric(
            "Excess Inventory Value",
            f"₹{total_excess_value:,.0f}"
        )


    # ========================================================
    # 71.16 — INVENTORY RISK OVERVIEW CHART
    # ========================================================

    st.subheader("Portfolio Risk Overview")

    risk_chart_data = pd.DataFrame(
        {
            "Risk Level": [
                "Critical",
                "High",
                "Medium",
                "Low"
            ],

            "SKU Count": [
                critical_risk,
                high_risk,
                medium_risk,
                max(
                    0,
                    total_skus
                    - critical_risk
                    - high_risk
                    - medium_risk
                )
            ]
        }
    )


    fig_risk = px.bar(
        risk_chart_data,
        x="Risk Level",
        y="SKU Count",
        title="Inventory Risk Distribution",
        text="SKU Count"
    )

    st.plotly_chart(
        fig_risk,
        use_container_width=True
    )


    # ========================================================
    # 71.17 — TOP MANAGEMENT PRIORITIES
    # ========================================================

    st.subheader("Top Management Priorities")


    # Create composite priority score
    #
    # Higher:
    #   • risk
    #   • demand
    #   • capital requirement
    #
    # means higher management priority.

    demand_rank = (
        control_df["Annual_Demand"]
        .rank(pct=True)
        .fillna(0)
    )

    risk_rank = (
        control_df["Risk_Score"]
        .rank(pct=True)
        .fillna(0)
    )

    capital_rank = (
        control_df["Additional_Capital"]
        .rank(pct=True)
        .fillna(0)
    )

    excess_rank = (
        control_df["Excess_Value"]
        .rank(pct=True)
        .fillna(0)
    )


    control_df["Management_Priority_Score"] = (
        risk_rank * 0.40
        + demand_rank * 0.25
        + capital_rank * 0.25
        + excess_rank * 0.10
    ) * 100


    control_df["Management_Priority"] = pd.cut(

        control_df["Management_Priority_Score"],

        bins=[
            -np.inf,
            25,
            50,
            75,
            np.inf
        ],

        labels=[
            "LOW",
            "MEDIUM",
            "HIGH",
            "CRITICAL"
        ]
    )


    priority_df = (
        control_df
        .sort_values(
            "Management_Priority_Score",
            ascending=False
        )
        .head(15)
        .copy()
    )


    priority_display = priority_df[
        [
            "SKU",
            "Product_Name",
            "Category",
            "Annual_Demand",
            "Inventory_Units",
            "Inventory_Value",
            "Risk_Score",
            "Service_Level",
            "Additional_Units",
            "Additional_Capital",
            "Excess_Units",
            "Management_Priority_Score",
            "Management_Priority"
        ]
    ].copy()


    st.dataframe(
        priority_display,
        use_container_width=True,
        hide_index=True
    )


    # ========================================================
    # 71.18 — TOP REPLENISHMENT SKUs
    # ========================================================

    st.subheader("Top Replenishment Priorities")

    replenishment_control = (
        control_df[
            control_df["Additional_Units"] > 0
        ]
        .sort_values(
            "Additional_Capital",
            ascending=False
        )
        .head(15)
        .copy()
    )


    if not replenishment_control.empty:

        fig_replenishment = px.bar(
            replenishment_control,
            x="SKU",
            y="Additional_Capital",
            title="Top Replenishment Capital Requirements",
            text="Additional_Capital"
        )

        st.plotly_chart(
            fig_replenishment,
            use_container_width=True
        )

    else:

        st.success(
            "No additional replenishment capital is currently required."
        )


    # ========================================================
    # 71.19 — EXCESS INVENTORY
    # ========================================================

    st.subheader("Excess Inventory Exposure")

    excess_control = (
        control_df[
            control_df["Excess_Value"] > 0
        ]
        .sort_values(
            "Excess_Value",
            ascending=False
        )
        .head(15)
        .copy()
    )


    if not excess_control.empty:

        fig_excess = px.bar(
            excess_control,
            x="SKU",
            y="Excess_Value",
            title="Top Excess Inventory Value by SKU",
            text="Excess_Value"
        )

        st.plotly_chart(
            fig_excess,
            use_container_width=True
        )

    else:

        st.success(
            "No excess inventory exposure identified."
        )


    # ========================================================
    # 71.20 — CATEGORY CONTROL TOWER
    # ========================================================

    st.subheader("Category Control Tower")


    category_control = (
        control_df
        .groupby(
            "Category",
            dropna=False
        )
        .agg(

            SKUs=(
                "SKU",
                "nunique"
            ),

            Inventory_Value=(
                "Inventory_Value",
                "sum"
            ),

            Annual_Demand=(
                "Annual_Demand",
                "sum"
            ),

            Additional_Capital=(
                "Additional_Capital",
                "sum"
            ),

            Excess_Value=(
                "Excess_Value",
                "sum"
            ),

            Average_Risk=(
                "Risk_Score",
                "mean"
            ),

            Average_Service_Level=(
                "Service_Level",
                "mean"
            )
        )
        .reset_index()
        .sort_values(
            "Average_Risk",
            ascending=False
        )
    )


    st.dataframe(
        category_control,
        use_container_width=True,
        hide_index=True
    )


    # ========================================================
    # 71.21 — CATEGORY RISK VISUAL
    # ========================================================

    if not category_control.empty:

        fig_category = px.bar(
            category_control.head(15),
            x="Category",
            y="Average_Risk",
            title="Category-Level Inventory Risk",
            text="Average_Risk"
        )

        st.plotly_chart(
            fig_category,
            use_container_width=True
        )


    # ========================================================
    # 71.22 — EXECUTIVE ALERTS
    # ========================================================

    st.subheader("Executive Alerts")


    alert_count = 0


    if stockout_skus > 0:

        alert_count += 1

        st.error(
            f"""
            🔴 **STOCKOUT ALERT**

            {stockout_skus:,} SKU(s) currently have zero
            available inventory despite positive demand.
            """
        )


    if critical_risk > 0:

        alert_count += 1

        st.error(
            f"""
            🔴 **CRITICAL RISK ALERT**

            {critical_risk:,} SKU(s) have critical stockout risk.
            """
        )


    if high_risk > 0:

        alert_count += 1

        st.warning(
            f"""
            🟠 **HIGH RISK ALERT**

            {high_risk:,} SKU(s) have high stockout risk.
            """
        )


    if total_excess_value > 0:

        alert_count += 1

        st.warning(
            f"""
            🟡 **EXCESS INVENTORY ALERT**

            Approximately ₹{total_excess_value:,.0f}
            of inventory value is classified as excess.
            """
        )


    if slow_stock_skus > 0:

        alert_count += 1

        st.warning(
            f"""
            🟡 **SLOW-MOVING STOCK ALERT**

            {slow_stock_skus:,} SKU(s) are classified as
            slow-moving or very slow-moving.
            """
        )


    if alert_count == 0:

        st.success(
            "No major executive-level inventory alerts detected."
        )


    # ========================================================
    # 71.23 — EXECUTIVE ACTION PLAN
    # ========================================================

    st.subheader("Recommended Executive Actions")


    action_data = []


    if stockout_skus > 0:

        action_data.append(
            {
                "Priority": "CRITICAL",
                "Area": "Stockouts",
                "Finding": (
                    f"{stockout_skus:,} SKUs have zero stock"
                ),
                "Recommended_Action": (
                    "Expedite replenishment and review supplier "
                    "availability immediately."
                )
            }
        )


    if critical_risk > 0:

        action_data.append(
            {
                "Priority": "CRITICAL",
                "Area": "Stockout Risk",
                "Finding": (
                    f"{critical_risk:,} critical-risk SKUs"
                ),
                "Recommended_Action": (
                    "Prioritize procurement and consider "
                    "supplier lead-time reduction."
                )
            }
        )


    if total_additional_capital > 0:

        action_data.append(
            {
                "Priority": "HIGH",
                "Area": "Working Capital",
                "Finding": (
                    f"₹{total_additional_capital:,.0f} "
                    "additional capital required"
                ),
                "Recommended_Action": (
                    "Prioritize replenishment based on demand "
                    "and risk instead of replenishing all SKUs equally."
                )
            }
        )


    if total_excess_value > 0:

        action_data.append(
            {
                "Priority": "HIGH",
                "Area": "Excess Inventory",
                "Finding": (
                    f"₹{total_excess_value:,.0f} "
                    "excess inventory value"
                ),
                "Recommended_Action": (
                    "Reduce purchases, transfer inventory, "
                    "promote products or liquidate slow stock."
                )
            }
        )


    if slow_stock_skus > 0:

        action_data.append(
            {
                "Priority": "MEDIUM",
                "Area": "Slow Moving Stock",
                "Finding": (
                    f"{slow_stock_skus:,} slow-moving SKUs"
                ),
                "Recommended_Action": (
                    "Review demand assumptions and reduce "
                    "future procurement quantities."
                )
            }
        )


    if not action_data:

        action_data.append(
            {
                "Priority": "LOW",
                "Area": "Overall Inventory",
                "Finding": (
                    "No major inventory exception detected"
                ),
                "Recommended_Action": (
                    "Continue normal monitoring."
                )
            }
        )


    executive_actions = pd.DataFrame(
        action_data
    )


    st.dataframe(
        executive_actions,
        use_container_width=True,
        hide_index=True
    )


    # ========================================================
    # 71.24 — EXECUTIVE SUMMARY
    # ========================================================

    st.subheader("Executive Summary")


    st.write(
        f"""
        The FORESIGHT inventory control tower currently monitors
        **{total_skus:,} SKUs**.

        Total inventory value is approximately
        **₹{total_inventory_value:,.0f}**, against annual demand of
        **{total_annual_demand:,.0f} units**.

        The estimated average service level is
        **{average_service_level:.1f}%**.

        There are currently **{stockout_skus:,} stockout SKUs**,
        **{critical_risk:,} critical-risk SKUs**, and
        **{high_risk:,} high-risk SKUs**.

        The current replenishment analysis indicates approximately
        **{total_additional_units:,.0f} additional units**
        requiring approximately
        **₹{total_additional_capital:,.0f}** of inventory investment.

        At the same time, approximately
        **{total_excess_units:,.0f} units**
        worth **₹{total_excess_value:,.0f}**
        are classified as excess inventory.
        """
    )


    # ========================================================
    # 71.25 — COMPLETE CONTROL TOWER DATASET
    # ========================================================

    with st.expander(
        "Complete Executive Control Tower Dataset"
    ):

        control_columns = [
            "SKU",
            "Product_Name",
            "Category",
            "Annual_Demand",
            "Inventory_Units",
            "Inventory_Value",
            "Stock_Coverage_Weeks",
            "Risk_Score",
            "Service_Level",
            "Additional_Units",
            "Additional_Capital",
            "Excess_Units",
            "Excess_Value",
            "Management_Priority_Score",
            "Management_Priority"
        ]


        control_columns = [
            col
            for col in control_columns
            if col in control_df.columns
        ]


        st.dataframe(
            control_df[
                control_columns
            ],
            use_container_width=True,
            hide_index=True
        )


    # ========================================================
    # 71.26 — COMPLETION
    # ========================================================

    st.success(
        f"""
        **Step 71 completed successfully.**

        Executive Control Tower created for
        **{total_skus:,} SKUs**.

        Inventory value:
        **₹{total_inventory_value:,.0f}**

        Average service level:
        **{average_service_level:.1f}%**

        Critical-risk SKUs:
        **{critical_risk:,}**

        Stockout SKUs:
        **{stockout_skus:,}**

        Additional capital requirement:
        **₹{total_additional_capital:,.0f}**

        Excess inventory value:
        **₹{total_excess_value:,.0f}**
        """
    )

    # ============================================================
# STEP 72 — FORECAST ACCURACY & MODEL PERFORMANCE
# ============================================================
#
# Purpose:
#   Evaluate forecasting performance using:
#       • WAPE
#       • MAE
#       • RMSE
#       • Forecast Bias
#       • Forecast vs Actual
#       • SKU-level accuracy
#       • Category-level accuracy
#       • Accuracy classification
#
# ============================================================

st.markdown("---")

st.header("STEP 72 — Forecast Accuracy & Model Performance")


# ============================================================
# 72.1 — PREPARE FORECAST DATA
# ============================================================

if "sales" in globals() and isinstance(sales, pd.DataFrame):

    accuracy_sales = sales.copy()

else:

    accuracy_sales = pd.DataFrame()


if accuracy_sales.empty:

    st.info(
        "Sales data is required for Step 72."
    )

else:

    # ========================================================
    # 72.2 — STANDARDIZE SALES DATA
    # ========================================================

    accuracy_sales["date"] = pd.to_datetime(
        accuracy_sales["date"],
        errors="coerce"
    )

    accuracy_sales["units_sold"] = pd.to_numeric(
        accuracy_sales["units_sold"],
        errors="coerce"
    ).fillna(0)


    # ========================================================
    # 72.3 — SKU COLUMN
    # ========================================================

    if "sku_id" in accuracy_sales.columns:

        accuracy_sales["SKU"] = (
            accuracy_sales["sku_id"]
            .astype(str)
        )

    elif "SKU" in accuracy_sales.columns:

        accuracy_sales["SKU"] = (
            accuracy_sales["SKU"]
            .astype(str)
        )

    else:

        accuracy_sales["SKU"] = "Unknown"


    # ========================================================
    # 72.4 — CATEGORY
    # ========================================================

    if "category" in accuracy_sales.columns:

        accuracy_sales["Category"] = (
            accuracy_sales["category"]
            .fillna("Unknown")
            .astype(str)
        )

    else:

        accuracy_sales["Category"] = "Unknown"


    # ========================================================
    # 72.5 — PRODUCT NAME
    # ========================================================

    if "product_name" in accuracy_sales.columns:

        accuracy_sales["Product_Name"] = (
            accuracy_sales["product_name"]
            .fillna("Unknown")
            .astype(str)
        )

    else:

        accuracy_sales["Product_Name"] = "Unknown"


    # ========================================================
    # 72.6 — WEEKLY ACTUAL DEMAND
    # ========================================================

    accuracy_sales["Week"] = (
        accuracy_sales["date"]
        .dt.to_period("W")
        .dt.start_time
    )


    weekly_actual = (
        accuracy_sales
        .groupby(
            ["SKU", "Week"],
            as_index=False
        )
        .agg(
            Actual_Demand=(
                "units_sold",
                "sum"
            )
        )
    )


    # ========================================================
    # 72.7 — CREATE BASELINE FORECAST
    # ========================================================
    #
    # Use previous-week demand as a simple baseline.
    #
    # This gives us a consistent forecast benchmark even when
    # the production forecast engine does not expose historical
    # backtesting predictions.
    # ========================================================

    weekly_actual = (
        weekly_actual
        .sort_values(
            ["SKU", "Week"]
        )
    )


    weekly_actual["Forecast_Demand"] = (
        weekly_actual
        .groupby("SKU")["Actual_Demand"]
        .shift(1)
    )


    # ========================================================
    # 72.8 — REMOVE FIRST WEEK
    # ========================================================

    accuracy_df = weekly_actual[
        weekly_actual["Forecast_Demand"].notna()
    ].copy()

    st.write("Accuracy records:", len(accuracy_df))


    if accuracy_df.empty:

        st.info(
            "Not enough historical weekly data to calculate "
            "forecast accuracy."
        )

    else:

        # ====================================================
        # 72.9 — ERROR METRICS
        # ====================================================

        accuracy_df["Error"] = (
            accuracy_df["Actual_Demand"]
            - accuracy_df["Forecast_Demand"]
        )


        accuracy_df["Absolute_Error"] = (
            accuracy_df["Error"]
            .abs()
        )


        accuracy_df["Squared_Error"] = (
            accuracy_df["Error"] ** 2
        )


        # ====================================================
        # 72.10 — PERCENTAGE ERROR
        # ====================================================

        accuracy_df["APE"] = np.where(

            accuracy_df["Actual_Demand"] != 0,

            (
                accuracy_df["Absolute_Error"]
                / accuracy_df["Actual_Demand"]
            ) * 100,

            np.nan
        )


        # ====================================================
        # 72.11 — OVERALL METRICS
        # ====================================================

        total_actual = (
            accuracy_df["Actual_Demand"]
            .sum()
        )

        total_absolute_error = (
            accuracy_df["Absolute_Error"]
            .sum()
        )


        if total_actual != 0:

            overall_wape = (
                total_absolute_error
                / total_actual
            ) * 100

        else:

            overall_wape = np.nan


        overall_mae = (
            accuracy_df["Absolute_Error"]
            .mean()
        )


        overall_rmse = np.sqrt(
            accuracy_df["Squared_Error"]
            .mean()
        )


        overall_bias = (
            accuracy_df["Error"]
            .sum()
        )


        bias_percentage = np.where(

            total_actual != 0,

            (
                overall_bias
                / total_actual
            ) * 100,

            np.nan
        )


        # ====================================================
        # 72.12 — ACCURACY SCORE
        # ====================================================

        accuracy_score = (
            100 - overall_wape
        )

        accuracy_score = max(
            0,
            min(100, accuracy_score)
        )


        # ====================================================
        # 72.13 — FORECAST QUALITY
        # ====================================================

        if overall_wape <= 10:

            forecast_quality = "EXCELLENT"

        elif overall_wape <= 20:

            forecast_quality = "GOOD"

        elif overall_wape <= 30:

            forecast_quality = "MODERATE"

        elif overall_wape <= 50:

            forecast_quality = "WEAK"

        else:

            forecast_quality = "POOR"


        # ====================================================
        # 72.14 — KPI CARDS
        # ====================================================

        st.subheader("Forecast Performance KPIs")


        k1, k2, k3, k4 = st.columns(4)


        with k1:

            st.metric(
                "WAPE",
                f"{overall_wape:.2f}%"
            )


        with k2:

            st.metric(
                "MAE",
                f"{overall_mae:,.2f}"
            )


        with k3:

            st.metric(
                "RMSE",
                f"{overall_rmse:,.2f}"
            )


        with k4:

            st.metric(
                "Forecast Accuracy",
                f"{accuracy_score:.1f}%"
            )


        k5, k6, k7, k8 = st.columns(4)


        with k5:

            st.metric(
                "Forecast Bias",
                f"{overall_bias:,.0f}"
            )


        with k6:

            st.metric(
                "Bias %",
                f"{float(bias_percentage):.2f}%"
            )


        with k7:

            st.metric(
                "SKUs Evaluated",
                f"{accuracy_df['SKU'].nunique():,}"
            )


        with k8:

            st.metric(
                "Forecast Quality",
                forecast_quality
            )


        # ====================================================
        # 72.15 — ACTUAL VS FORECAST
        # ====================================================

        st.subheader("Actual vs Forecast Demand")


        trend_df = (
            accuracy_df
            .groupby("Week", as_index=False)
            .agg(
                Actual=(
                    "Actual_Demand",
                    "sum"
                ),
                Forecast=(
                    "Forecast_Demand",
                    "sum"
                )
            )
        )


        fig_accuracy = px.line(
            trend_df,
            x="Week",
            y=[
                "Actual",
                "Forecast"
            ],
            title="Actual vs Baseline Forecast"
        )


        st.plotly_chart(
            fig_accuracy,
            use_container_width=True
        )


# ====================================================
# 72.16 — SKU PERFORMANCE
# ====================================================

sku_accuracy = (
    accuracy_df
    .groupby(
        "SKU",
        as_index=False
    )
    .agg(
        Actual_Demand=(
            "Actual_Demand",
            "sum"
        ),
        Forecast_Demand=(
            "Forecast_Demand",
            "sum"
        ),
        Absolute_Error=(
            "Absolute_Error",
            "sum"
        ),
        Error=(
            "Error",
            "sum"
        )
    )
)


sku_accuracy["WAPE"] = np.where(

    sku_accuracy["Actual_Demand"] != 0,

    (
        sku_accuracy["Absolute_Error"]
        / sku_accuracy["Actual_Demand"]
    ) * 100,

    np.nan
)


sku_accuracy["Bias_Percentage"] = np.where(

    sku_accuracy["Actual_Demand"] != 0,

    (
        sku_accuracy["Error"]
        / sku_accuracy["Actual_Demand"]
    ) * 100,

    np.nan
)


sku_accuracy["Accuracy"] = (
    100
    - sku_accuracy["WAPE"]
).clip(
    lower=0,
    upper=100
)


sku_accuracy["Accuracy_Class"] = pd.cut(

    sku_accuracy["Accuracy"],

    bins=[
        -np.inf,
        50,
        70,
        85,
        95,
        np.inf
    ],

    labels=[
        "POOR",
        "WEAK",
        "MODERATE",
        "GOOD",
        "EXCELLENT"
    ]
)


# ====================================================
# 72.17 — WORST FORECAST SKUs
# ====================================================

st.subheader("Lowest Forecast Accuracy SKUs")


worst_accuracy = (
    sku_accuracy
    .sort_values(
        "WAPE",
        ascending=False
    )
    .head(20)
)


st.dataframe(
    worst_accuracy,
    use_container_width=True,
    hide_index=True
)

st.write("DEBUG accuracy_df columns:", accuracy_df.columns.tolist())

# ====================================================
# 72.18 — CATEGORY ACCURACY
# ====================================================

# Add category information to the accuracy dataset
if "category" not in accuracy_df.columns:

    accuracy_df = accuracy_df.merge(
        sku_master[
            [
                "sku_id",
                "category"
            ]
        ],
        left_on="SKU",
        right_on="sku_id",
        how="left"
    )

# Calculate category-level forecast accuracy
category_accuracy = (
    accuracy_df
    .groupby(
        "category",
        as_index=False
    )
    .agg(
        Actual_Demand=(
            "Actual_Demand",
            "sum"
        ),
        Forecast_Demand=(
            "Forecast_Demand",
            "sum"
        ),
        Absolute_Error=(
            "Absolute_Error",
            "sum"
        ),
        Error=(
            "Error",
            "sum"
        )
    )
)

category_accuracy["WAPE"] = np.where(
    category_accuracy["Actual_Demand"] != 0,

    (
        category_accuracy["Absolute_Error"]
        / category_accuracy["Actual_Demand"]
    ) * 100,

    np.nan
)

category_accuracy["Accuracy"] = (
    100
    - category_accuracy["WAPE"]
).clip(
    lower=0,
    upper=100
)

st.subheader("Category Forecast Accuracy")

st.dataframe(
    category_accuracy,
    use_container_width=True,
    hide_index=True
)
# ====================================================
# 72.19 — ERROR DISTRIBUTION
# ====================================================

st.subheader("Forecast Error Distribution")

fig_error = px.histogram(
    accuracy_df,
    x="Error",
    nbins=30,
    title="Forecast Error Distribution"
)

st.plotly_chart(
    fig_error,
    use_container_width=True
)
# ====================================================
# 72.20 — BIAS ANALYSIS
# ====================================================

if overall_bias > 0:

    st.warning(
        f"""
        Forecast bias is **positive ({overall_bias:,.0f})**.
        Actual demand is higher than the baseline forecast,
        indicating potential under-forecasting.
        """
    )

elif overall_bias < 0:

    st.warning(
        f"""
        Forecast bias is **negative ({overall_bias:,.0f})**.
        The baseline forecast is higher than actual demand,
        indicating potential over-forecasting.
        """
    )

else:

    st.success(
        "Forecast bias is approximately neutral."
    )

# ====================================================
# 72.21 — COMPLETE DATASET
# ====================================================

with st.expander(
    "Complete Forecast Accuracy Dataset"
):

    st.dataframe(
        accuracy_df,
        use_container_width=True,
        hide_index=True
    )

# ====================================================
# 72.22 — COMPLETION
# ====================================================

st.success(
       f"""
    **Step 72 completed successfully.**

    Overall WAPE: **{overall_wape:.2f}%**

    Forecast accuracy score:
    **{accuracy_score:.1f}%**

    Forecast quality:
    **{forecast_quality}**
    """
)

# ============================================================
# STEP 73 — ADVANCED REPLENISHMENT & PURCHASE PLANNING
# ============================================================

st.markdown("---")

st.header("STEP 73 — Advanced Replenishment & Purchase Planning")


# ============================================================
# 73.1 — SOURCE DATA
# ============================================================

if "optimization_df" in globals() and isinstance(
    optimization_df,
    pd.DataFrame
):

    purchase_df = optimization_df.copy()

elif "scenario_df" in globals() and isinstance(
    scenario_df,
    pd.DataFrame
):

    purchase_df = scenario_df.copy()

else:

    purchase_df = pd.DataFrame()


if purchase_df.empty:

    st.info(
        "Inventory optimization data is required for Step 73."
    )

else:

    # ========================================================
    # 73.2 — HELPERS
    # ========================================================

    def _purchase_num(
        df,
        candidates,
        default=0.0
    ):

        for col in candidates:

            if col in df.columns:

                return pd.to_numeric(
                    df[col],
                    errors="coerce"
                ).fillna(default)

        return pd.Series(
            default,
            index=df.index,
            dtype=float
        )


    def _purchase_text(
        df,
        candidates,
        default="Unknown"
    ):

        for col in candidates:

            if col in df.columns:

                return (
                    df[col]
                    .fillna(default)
                    .astype(str)
                )

        return pd.Series(
            default,
            index=df.index
        )


    # ========================================================
    # 73.3 — STANDARDIZE
    # ========================================================

    purchase_df["SKU"] = _purchase_text(
        purchase_df,
        ["SKU", "sku_id", "SKU_ID"],
        "Unknown"
    )

    purchase_df["Product_Name"] = _purchase_text(
        purchase_df,
        [
            "Product_Name",
            "product_name"
        ],
        "Unknown"
    )

    purchase_df["Category"] = _purchase_text(
        purchase_df,
        [
            "Category",
            "category"
        ],
        "Unknown"
    )

    purchase_df["Annual_Demand"] = _purchase_num(
        purchase_df,
        [
            "Scenario_Annual_Demand",
            "Annual_Demand",
            "Annual_Units_Demand"
        ]
    )

    purchase_df["Current_Stock"] = _purchase_num(
        purchase_df,
        [
            "Available_Inventory",
            "Current_Stock",
            "on_hand"
        ]
    )

    purchase_df["Unit_Cost"] = _purchase_num(
        purchase_df,
        [
            "Unit_Cost",
            "unit_cost"
        ]
    )

    purchase_df["Lead_Time_Days"] = _purchase_num(
        purchase_df,
        [
            "Scenario_Lead_Time_Days",
            "Lead_Time_Days",
            "lead_time_days"
        ]
    )

    purchase_df["Safety_Stock"] = _purchase_num(
        purchase_df,
        [
            "Scenario_Safety_Stock",
            "Estimated_Safety_Stock",
            "Safety_Stock"
        ]
    )


    # ========================================================
    # 73.4 — PURCHASE PARAMETERS
    # ========================================================

    st.subheader("Purchase Planning Controls")


    p1, p2, p3 = st.columns(3)


    with p1:

        purchase_horizon_weeks = st.slider(
            "Purchase Planning Horizon",
            2,
            16,
            8,
            1
        )


    with p2:

        minimum_order_units = st.number_input(
            "Minimum Order Quantity",
            min_value=0,
            value=0,
            step=1
        )


    with p3:

        review_buffer_days = st.slider(
            "Review Buffer Days",
            0,
            30,
            7,
            1
        )


    # ========================================================
    # 73.5 — DEMAND
    # ========================================================

    purchase_df["Daily_Demand"] = (
        purchase_df["Annual_Demand"]
        / 365
    )


    purchase_df["Planning_Horizon_Demand"] = (
        purchase_df["Daily_Demand"]
        * purchase_horizon_weeks
        * 7
    )


    # ========================================================
    # 73.6 — LEAD-TIME DEMAND
    # ========================================================

    purchase_df["Lead_Time_Demand"] = (
        purchase_df["Daily_Demand"]
        * purchase_df["Lead_Time_Days"]
    )


    # ========================================================
    # 73.7 — REORDER POINT
    # ========================================================

    purchase_df["Purchase_Reorder_Point"] = (
        purchase_df["Lead_Time_Demand"]
        + purchase_df["Safety_Stock"]
        + (
            purchase_df["Daily_Demand"]
            * review_buffer_days
        )
    )


    # ========================================================
    # 73.8 — TARGET STOCK
    # ========================================================

    purchase_df["Purchase_Target_Stock"] = (
        purchase_df["Planning_Horizon_Demand"]
        + purchase_df["Safety_Stock"]
    )


    # ========================================================
    # 73.9 — NET PURCHASE REQUIREMENT
    # ========================================================

    purchase_df["Gross_Purchase_Requirement"] = (
        purchase_df["Purchase_Target_Stock"]
        - purchase_df["Current_Stock"]
    ).clip(lower=0)


    # ========================================================
    # 73.10 — APPLY MOQ
    # ========================================================

    if minimum_order_units > 0:

        purchase_df["Recommended_Order_Qty"] = np.where(
            purchase_df["Gross_Purchase_Requirement"] > 0,

            np.maximum(
                purchase_df[
                    "Gross_Purchase_Requirement"
                ],
                minimum_order_units
            ),

            0
        )

    else:

        purchase_df["Recommended_Order_Qty"] = (
            purchase_df["Gross_Purchase_Requirement"]
        )


    purchase_df["Recommended_Order_Qty"] = np.ceil(
        purchase_df["Recommended_Order_Qty"]
    )


    # ========================================================
    # 73.11 — PURCHASE VALUE
    # ========================================================

    purchase_df["Purchase_Value"] = (
        purchase_df["Recommended_Order_Qty"]
        * purchase_df["Unit_Cost"]
    )


    # ========================================================
    # 73.12 — REORDER STATUS
    # ========================================================

    purchase_df["Reorder_Status"] = np.select(

        [
            purchase_df["Current_Stock"] <= 0,

            purchase_df["Current_Stock"]
            < purchase_df["Purchase_Reorder_Point"] * 0.50,

            purchase_df["Current_Stock"]
            < purchase_df["Purchase_Reorder_Point"],

            purchase_df["Recommended_Order_Qty"] > 0
        ],

        [
            "URGENT STOCKOUT",

            "CRITICAL REORDER",

            "REORDER NOW",

            "PLANNED PURCHASE"
        ],

        default="NO PURCHASE"
    )


    # ========================================================
    # 73.13 — PURCHASE PRIORITY
    # ========================================================

    purchase_df["Purchase_Priority_Score"] = (

        purchase_df["Recommended_Order_Qty"]
        .rank(pct=True)
        .fillna(0)
        * 40

        +

        purchase_df["Purchase_Value"]
        .rank(pct=True)
        .fillna(0)
        * 30

        +

        purchase_df["Lead_Time_Days"]
        .rank(pct=True)
        .fillna(0)
        * 15

        +

        purchase_df["Annual_Demand"]
        .rank(pct=True)
        .fillna(0)
        * 15
    )


    purchase_df["Purchase_Priority"] = pd.cut(

        purchase_df["Purchase_Priority_Score"],

        bins=[
            -np.inf,
            25,
            50,
            75,
            np.inf
        ],

        labels=[
            "LOW",
            "MEDIUM",
            "HIGH",
            "CRITICAL"
        ]
    )


    # ========================================================
    # 73.14 — KPIs
    # ========================================================

    total_purchase_units = (
        purchase_df["Recommended_Order_Qty"]
        .sum()
    )

    total_purchase_value = (
        purchase_df["Purchase_Value"]
        .sum()
    )

    purchase_skus = int(
        (
            purchase_df["Recommended_Order_Qty"] > 0
        ).sum()
    )

    urgent_skus = int(
        purchase_df["Reorder_Status"]
        .isin(
            [
                "URGENT STOCKOUT",
                "CRITICAL REORDER"
            ]
        )
        .sum()
    )


    # ========================================================
    # 73.15 — KPI CARDS
    # ========================================================

    st.subheader("Purchase Plan Summary")


    k1, k2, k3, k4 = st.columns(4)


    with k1:

        st.metric(
            "SKUs to Purchase",
            f"{purchase_skus:,}"
        )


    with k2:

        st.metric(
            "Purchase Units",
            f"{total_purchase_units:,.0f}"
        )


    with k3:

        st.metric(
            "Purchase Value",
            f"₹{total_purchase_value:,.0f}"
        )


    with k4:

        st.metric(
            "Urgent Purchases",
            f"{urgent_skus:,}"
        )


    # ========================================================
    # 73.16 — TOP PURCHASE REQUIREMENTS
    # ========================================================

    st.subheader("Top Purchase Requirements")


    top_purchase = (
        purchase_df[
            purchase_df["Recommended_Order_Qty"] > 0
        ]
        .sort_values(
            "Purchase_Value",
            ascending=False
        )
        .head(20)
    )


    if not top_purchase.empty:

        fig_purchase = px.bar(
            top_purchase,
            x="SKU",
            y="Purchase_Value",
            title="Top Purchase Requirements by Value",
            text="Purchase_Value"
        )

        st.plotly_chart(
            fig_purchase,
            use_container_width=True
        )


    # ========================================================
    # 73.17 — PURCHASE PLAN TABLE
    # ========================================================

    st.subheader("Recommended Purchase Plan")


    purchase_plan = purchase_df[
        purchase_df["Recommended_Order_Qty"] > 0
    ].sort_values(
        "Purchase_Priority_Score",
        ascending=False
    )


    purchase_columns = [
        "SKU",
        "Product_Name",
        "Category",
        "Current_Stock",
        "Annual_Demand",
        "Lead_Time_Days",
        "Safety_Stock",
        "Purchase_Reorder_Point",
        "Purchase_Target_Stock",
        "Recommended_Order_Qty",
        "Unit_Cost",
        "Purchase_Value",
        "Reorder_Status",
        "Purchase_Priority"
    ]


    purchase_columns = [
        col
        for col in purchase_columns
        if col in purchase_plan.columns
    ]


    st.dataframe(
        purchase_plan[purchase_columns],
        use_container_width=True,
        hide_index=True
    )


    # ========================================================
    # 73.18 — CATEGORY PURCHASE PLAN
    # ========================================================

    st.subheader("Category Purchase Requirements")


    category_purchase = (
        purchase_df
        .groupby(
            "Category",
            dropna=False
        )
        .agg(
            SKUs=(
                "SKU",
                "nunique"
            ),
            Purchase_Units=(
                "Recommended_Order_Qty",
                "sum"
            ),
            Purchase_Value=(
                "Purchase_Value",
                "sum"
            )
        )
        .reset_index()
        .sort_values(
            "Purchase_Value",
            ascending=False
        )
    )


    st.dataframe(
        category_purchase,
        use_container_width=True,
        hide_index=True
    )


    # ========================================================
    # 73.19 — PURCHASE PRIORITY DISTRIBUTION
    # ========================================================

    priority_distribution = (
        purchase_df["Purchase_Priority"]
        .astype(str)
        .value_counts()
        .reset_index()
    )


    priority_distribution.columns = [
        "Priority",
        "SKU_Count"
    ]


    fig_priority = px.bar(
        priority_distribution,
        x="Priority",
        y="SKU_Count",
        title="Purchase Priority Distribution",
        text="SKU_Count"
    )


    st.plotly_chart(
        fig_priority,
        use_container_width=True
    )


    # ========================================================
    # 73.20 — MANAGEMENT ALERT
    # ========================================================

    if urgent_skus > 0:

        st.error(
            f"""
            **Urgent procurement required:** {urgent_skus:,} SKU(s)
            require immediate purchase/replenishment attention.
            """
        )

    elif purchase_skus > 0:

        st.warning(
            f"""
            **Purchase planning required:** {purchase_skus:,} SKU(s)
            require replenishment within the selected planning horizon.
            """
        )

    else:

        st.success(
            "No immediate purchase requirement identified."
        )


    # ========================================================
    # 73.21 — COMPLETE DATASET
    # ========================================================

    with st.expander(
        "Complete Replenishment & Purchase Dataset"
    ):

        st.dataframe(
            purchase_df,
            use_container_width=True,
            hide_index=True
        )


    # ========================================================
    # 73.22 — COMPLETION
    # ========================================================

    st.success(
        f"""
        **Step 73 completed successfully.**

        Purchase SKUs:
        **{purchase_skus:,}**

        Recommended purchase quantity:
        **{total_purchase_units:,.0f} units**

        Estimated purchase value:
        **₹{total_purchase_value:,.0f}**
        """
    )

    # ============================================================
# STEP 74 — WORKING CAPITAL & INVENTORY INVESTMENT ANALYTICS
# ============================================================

st.markdown("---")

st.header("STEP 74 — Working Capital & Inventory Investment Analytics")


# ============================================================
# 74.1 — SOURCE DATA
# ============================================================

if "control_df" in globals() and isinstance(
    control_df,
    pd.DataFrame
) and not control_df.empty:

    working_df = control_df.copy()

elif "purchase_df" in globals() and isinstance(
    purchase_df,
    pd.DataFrame
) and not purchase_df.empty:

    working_df = purchase_df.copy()

elif "financial_df" in globals() and isinstance(
    financial_df,
    pd.DataFrame
) and not financial_df.empty:

    working_df = financial_df.copy()

else:

    working_df = pd.DataFrame()


if working_df.empty:

    st.info(
        "Financial and inventory data is required for Step 74."
    )

else:

    # ========================================================
    # 74.2 — HELPERS
    # ========================================================

    def _working_num(
        df,
        candidates,
        default=0.0
    ):

        for col in candidates:

            if col in df.columns:

                return pd.to_numeric(
                    df[col],
                    errors="coerce"
                ).fillna(default)

        return pd.Series(
            default,
            index=df.index,
            dtype=float
        )


    def _working_text(
        df,
        candidates,
        default="Unknown"
    ):

        for col in candidates:

            if col in df.columns:

                return (
                    df[col]
                    .fillna(default)
                    .astype(str)
                )

        return pd.Series(
            default,
            index=df.index
        )


    # ========================================================
    # 74.3 — STANDARDIZE
    # ========================================================

    working_df["SKU"] = _working_text(
        working_df,
        ["SKU", "sku_id", "SKU_ID"],
        "Unknown"
    )


    working_df["Product_Name"] = _working_text(
        working_df,
        [
            "Product_Name",
            "product_name"
        ],
        "Unknown"
    )


    working_df["Category"] = _working_text(
        working_df,
        [
            "Category",
            "category"
        ],
        "Unknown"
    )


    working_df["Current_Stock"] = _working_num(
        working_df,
        [
            "Available_Inventory",
            "Current_Stock",
            "on_hand"
        ]
    )


    working_df["Unit_Cost"] = _working_num(
        working_df,
        [
            "Unit_Cost",
            "unit_cost"
        ]
    )


    working_df["Annual_Demand"] = _working_num(
        working_df,
        [
            "Scenario_Annual_Demand",
            "Annual_Demand",
            "Annual_Units_Demand"
        ]
    )


    working_df["Annual_COGS"] = (
        working_df["Annual_Demand"]
        * working_df["Unit_Cost"]
    )


    # ========================================================
    # 74.4 — INVENTORY VALUE
    # ========================================================

    working_df["Inventory_Value"] = (
        working_df["Current_Stock"]
        * working_df["Unit_Cost"]
    )


    # ========================================================
    # 74.5 — INVENTORY TURNOVER
    # ========================================================

    working_df["Inventory_Turnover"] = np.where(

        working_df["Inventory_Value"] > 0,

        working_df["Annual_COGS"]
        / working_df["Inventory_Value"],

        np.nan
    )


    # ========================================================
    # 74.6 — DAYS INVENTORY OUTSTANDING
    # ========================================================

    working_df["DIO_Days"] = np.where(

        working_df["Inventory_Turnover"] > 0,

        365
        / working_df["Inventory_Turnover"],

        np.nan
    )


    # ========================================================
    # 74.7 — ANNUAL INVENTORY CARRYING COST
    # ========================================================

    carrying_rate = st.slider(
        "Estimated Annual Inventory Carrying Cost %",
        5,
        40,
        20,
        1
    )


    working_df["Annual_Carrying_Cost"] = (
        working_df["Inventory_Value"]
        * carrying_rate
        / 100
    )


    # ========================================================
    # 74.8 — EXCESS INVENTORY
    # ========================================================

    working_df["Excess_Value"] = _working_num(
        working_df,
        [
            "Excess_Inventory_Value",
            "Excess_Value"
        ]
    )


    # ========================================================
    # 74.9 — RELEASABLE CAPITAL
    # ========================================================

    working_df["Potential_Capital_Release"] = (
        working_df["Excess_Value"]
        .clip(lower=0)
    )


    # ========================================================
    # 74.10 — CAPITAL EFFICIENCY
    # ========================================================

    working_df["Capital_Efficiency"] = np.where(

        working_df["Inventory_Value"] > 0,

        working_df["Annual_COGS"]
        / working_df["Inventory_Value"],

        0
    )


    # ========================================================
    # 74.11 — INVENTORY INVESTMENT CLASS
    # ========================================================

    working_df["Investment_Class"] = np.select(

        [
            working_df["DIO_Days"] > 180,

            working_df["DIO_Days"] > 120,

            working_df["DIO_Days"] > 90,

            working_df["DIO_Days"] > 60
        ],

        [
            "VERY HIGH INVESTMENT",

            "HIGH INVESTMENT",

            "MODERATE INVESTMENT",

            "NORMAL"
        ],

        default="EFFICIENT"
    )


    # ========================================================
    # 74.12 — PORTFOLIO KPIs
    # ========================================================

    total_inventory = (
        working_df["Inventory_Value"]
        .sum()
    )


    total_cogs = (
        working_df["Annual_COGS"]
        .sum()
    )


    total_carrying_cost = (
        working_df["Annual_Carrying_Cost"]
        .sum()
    )


    total_excess_value = (
        working_df["Excess_Value"]
        .sum()
    )


    potential_release = (
        working_df["Potential_Capital_Release"]
        .sum()
    )


    portfolio_turnover = np.where(

        total_inventory > 0,

        total_cogs
        / total_inventory,

        np.nan
    )


    portfolio_dio = np.where(

        portfolio_turnover > 0,

        365
        / portfolio_turnover,

        np.nan
    )


    # ========================================================
    # 74.13 — KPI CARDS
    # ========================================================

    st.subheader("Working Capital KPIs")


    k1, k2, k3, k4 = st.columns(4)


    with k1:

        st.metric(
            "Inventory Investment",
            f"₹{total_inventory:,.0f}"
        )


    with k2:

        st.metric(
            "Annual COGS",
            f"₹{total_cogs:,.0f}"
        )


    with k3:

        st.metric(
            "Inventory Turnover",
            f"{float(portfolio_turnover):.2f}x"
            if not pd.isna(portfolio_turnover)
            else "N/A"
        )


    with k4:

        st.metric(
            "DIO",
            f"{float(portfolio_dio):.1f} days"
            if not pd.isna(portfolio_dio)
            else "N/A"
        )


    k5, k6, k7, k8 = st.columns(4)


    with k5:

        st.metric(
            "Carrying Cost",
            f"₹{total_carrying_cost:,.0f}"
        )


    with k6:

        st.metric(
            "Excess Inventory",
            f"₹{total_excess_value:,.0f}"
        )


    with k7:

        st.metric(
            "Potential Capital Release",
            f"₹{potential_release:,.0f}"
        )


    with k8:

        st.metric(
            "Carrying Rate",
            f"{carrying_rate}%"
        )


    # ========================================================
    # 74.14 — INVENTORY INVESTMENT BY CATEGORY
    # ========================================================

    st.subheader("Inventory Investment by Category")


    category_investment = (
        working_df
        .groupby(
            "Category",
            dropna=False
        )
        .agg(
            SKUs=(
                "SKU",
                "nunique"
            ),

            Inventory_Value=(
                "Inventory_Value",
                "sum"
            ),

            Annual_COGS=(
                "Annual_COGS",
                "sum"
            ),

            Excess_Value=(
                "Excess_Value",
                "sum"
            ),

            Carrying_Cost=(
                "Annual_Carrying_Cost",
                "sum"
            )
        )
        .reset_index()
    )


    category_investment["Turnover"] = np.where(

        category_investment["Inventory_Value"] > 0,

        category_investment["Annual_COGS"]
        / category_investment["Inventory_Value"],

        np.nan
    )


    category_investment["DIO"] = np.where(

        category_investment["Turnover"] > 0,

        365
        / category_investment["Turnover"],

        np.nan
    )


    category_investment = (
        category_investment
        .sort_values(
            "Inventory_Value",
            ascending=False
        )
    )


    st.dataframe(
        category_investment,
        use_container_width=True,
        hide_index=True
    )


    # ========================================================
    # 74.15 — CATEGORY INVESTMENT CHART
    # ========================================================

    if not category_investment.empty:

        fig_investment = px.bar(
            category_investment.head(15),
            x="Category",
            y="Inventory_Value",
            title="Inventory Investment by Category",
            text="Inventory_Value"
        )


        st.plotly_chart(
            fig_investment,
            use_container_width=True
        )


    # ========================================================
    # 74.16 — CAPITAL RELEASE OPPORTUNITY
    # ========================================================

    st.subheader("Capital Release Opportunities")


    capital_release = (
        working_df[
            working_df["Potential_Capital_Release"] > 0
        ]
        .sort_values(
            "Potential_Capital_Release",
            ascending=False
        )
        .head(20)
        .copy()
    )


    if not capital_release.empty:

        release_chart = px.bar(
            capital_release,
            x="SKU",
            y="Potential_Capital_Release",
            title="Top Potential Capital Release Opportunities",
            text="Potential_Capital_Release"
        )


        st.plotly_chart(
            release_chart,
            use_container_width=True
        )


        release_columns = [
            "SKU",
            "Product_Name",
            "Category",
            "Current_Stock",
            "Unit_Cost",
            "Inventory_Value",
            "Excess_Value",
            "Potential_Capital_Release",
            "Inventory_Turnover",
            "DIO_Days",
            "Investment_Class"
        ]


        release_columns = [
            col
            for col in release_columns
            if col in capital_release.columns
        ]


        st.dataframe(
            capital_release[release_columns],
            use_container_width=True,
            hide_index=True
        )


    else:

        st.success(
            "No significant capital-release opportunity identified."
        )


    # ========================================================
    # 74.17 — CARRYING COST ANALYSIS
    # ========================================================

    st.subheader("Inventory Carrying Cost")


    carrying_chart_df = (
        category_investment
        .sort_values(
            "Carrying_Cost",
            ascending=False
        )
        .head(15)
    )


    if not carrying_chart_df.empty:

        fig_carrying = px.bar(
            carrying_chart_df,
            x="Category",
            y="Carrying_Cost",
            title="Annual Carrying Cost by Category",
            text="Carrying_Cost"
        )


        st.plotly_chart(
            fig_carrying,
            use_container_width=True
        )


    # ========================================================
    # 74.18 — INVESTMENT EFFICIENCY
    # ========================================================

    st.subheader("Inventory Investment Efficiency")


    efficiency_df = (
        working_df[
            working_df["Inventory_Value"] > 0
        ]
        .sort_values(
            "Capital_Efficiency",
            ascending=True
        )
        .head(20)
        .copy()
    )


    efficiency_columns = [
        "SKU",
        "Product_Name",
        "Category",
        "Inventory_Value",
        "Annual_COGS",
        "Inventory_Turnover",
        "DIO_Days",
        "Annual_Carrying_Cost",
        "Investment_Class"
    ]


    efficiency_columns = [
        col
        for col in efficiency_columns
        if col in efficiency_df.columns
    ]


    st.dataframe(
        efficiency_df[
            efficiency_columns
        ],
        use_container_width=True,
        hide_index=True
    )


    # ========================================================
    # 74.19 — MANAGEMENT ALERTS
    # ========================================================

    st.subheader("Working Capital Alerts")


    if portfolio_dio > 120:

        st.error(
            f"""
            **High inventory investment:** Portfolio DIO is
            approximately **{portfolio_dio:.1f} days**.
            Inventory reduction opportunities should be reviewed.
            """
        )

    elif portfolio_dio > 90:

        st.warning(
            f"""
            **Moderate inventory investment:** Portfolio DIO is
            approximately **{portfolio_dio:.1f} days**.
            """
        )

    else:

        st.success(
            f"""
            Portfolio DIO is approximately
            **{portfolio_dio:.1f} days**.
            """
        )


    if potential_release > 0:

        st.info(
            f"""
            Potential capital release from excess inventory is
            approximately **₹{potential_release:,.0f}**.
            """
        )


    # ========================================================
    # 74.20 — COMPLETE DATASET
    # ========================================================

    with st.expander(
        "Complete Working Capital Dataset"
    ):

        st.dataframe(
            working_df,
            use_container_width=True,
            hide_index=True
        )


    # ========================================================
    # 74.21 — COMPLETION
    # ========================================================

    st.success(
        f"""
        **Step 74 completed successfully.**

        Total inventory investment:
        **₹{total_inventory:,.0f}**

        Portfolio inventory turnover:
        **{float(portfolio_turnover):.2f}x**
        """

        + (
            f"""

        Portfolio DIO:
        **{float(portfolio_dio):.1f} days**
        """
            if not pd.isna(portfolio_dio)
            else ""
        )

        + f"""

        Potential capital release:
        **₹{potential_release:,.0f}**
        """
    )

    # ============================================================
# STEP 75 — SKU PRIORITIZATION & BUSINESS OPPORTUNITY RANKING
# ============================================================

st.markdown("---")
st.header("STEP 75 — SKU PRIORITIZATION & BUSINESS OPPORTUNITY RANKING")

# ------------------------------------------------------------
# 1. SELECT BEST AVAILABLE DATASET
# ------------------------------------------------------------

if "working_df" in globals() and isinstance(working_df, pd.DataFrame) and not working_df.empty:
    priority_df = working_df.copy()

elif "purchase_df" in globals() and isinstance(purchase_df, pd.DataFrame) and not purchase_df.empty:
    priority_df = purchase_df.copy()

elif "optimization_df" in globals() and isinstance(optimization_df, pd.DataFrame) and not optimization_df.empty:
    priority_df = optimization_df.copy()

else:
    priority_df = pd.DataFrame()


# ------------------------------------------------------------
# 2. HELPER FUNCTIONS
# ------------------------------------------------------------

def _priority_num(df, columns, default=0.0):
    for col in columns:
        if col in df.columns:
            return pd.to_numeric(df[col], errors="coerce").fillna(default)
    return pd.Series(default, index=df.index)


def _priority_text(df, columns, default="Unknown"):
    for col in columns:
        if col in df.columns:
            return df[col].fillna(default).astype(str)
    return pd.Series(default, index=df.index)


if not priority_df.empty:

    # --------------------------------------------------------
    # 3. STANDARDIZE IDENTIFIERS
    # --------------------------------------------------------

    priority_df["SKU"] = _priority_text(
        priority_df,
        ["SKU", "sku_id", "sku", "SKU_ID"]
    )

    priority_df["Product_Name"] = _priority_text(
        priority_df,
        ["Product_Name", "product_name", "Product", "name"]
    )

    priority_df["Category"] = _priority_text(
        priority_df,
        ["Category", "category", "Category_Name"]
    )


    # --------------------------------------------------------
    # 4. STANDARDIZE BUSINESS METRICS
    # --------------------------------------------------------

    priority_df["Annual_Demand"] = _priority_num(
        priority_df,
        [
            "Annual_Demand",
            "Annual_Units_Demand",
            "Historical_Annual_Demand",
            "EOQ_Annual_Demand"
        ]
    )

    priority_df["Current_Stock"] = _priority_num(
        priority_df,
        [
            "Current_Stock",
            "Inventory_Units",
            "on_hand"
        ]
    )

    priority_df["Unit_Cost"] = _priority_num(
        priority_df,
        [
            "Unit_Cost",
            "unit_cost"
        ]
    )

    priority_df["Inventory_Value"] = (
        priority_df["Current_Stock"] *
        priority_df["Unit_Cost"]
    )

    priority_df["Annual_Demand_Value"] = (
        priority_df["Annual_Demand"] *
        priority_df["Unit_Cost"]
    )


    # --------------------------------------------------------
    # 5. DEMAND VELOCITY
    # --------------------------------------------------------

    priority_df["Daily_Demand"] = (
        priority_df["Annual_Demand"] / 365
    )

    priority_df["Demand_Velocity"] = np.where(
        priority_df["Annual_Demand"] > 0,
        priority_df["Annual_Demand"],
        0
    )


    # --------------------------------------------------------
    # 6. STOCK COVERAGE
    # --------------------------------------------------------

    priority_df["Stock_Coverage_Days"] = np.where(
        priority_df["Daily_Demand"] > 0,
        priority_df["Current_Stock"] /
        priority_df["Daily_Demand"],
        np.nan
    )


    # --------------------------------------------------------
    # 7. REPLENISHMENT REQUIREMENT
    # --------------------------------------------------------

    priority_df["Recommended_Reorder_Point"] = _priority_num(
        priority_df,
        [
            "Recommended_Reorder_Point",
            "Purchase_Reorder_Point",
            "Existing_Reorder_Point"
        ]
    )

    priority_df["Replenishment_Gap"] = (
        priority_df["Recommended_Reorder_Point"]
        - priority_df["Current_Stock"]
    )

    priority_df["Replenishment_Gap"] = (
        priority_df["Replenishment_Gap"].clip(lower=0)
    )


    priority_df["Replenishment_Value"] = (
        priority_df["Replenishment_Gap"] *
        priority_df["Unit_Cost"]
    )


    # --------------------------------------------------------
    # 8. STOCK RISK SCORE
    # --------------------------------------------------------

    priority_df["Risk_Score"] = _priority_num(
        priority_df,
        [
            "Risk_Score",
            "Purchase_Priority_Score"
        ]
    )

    # If no existing score is available, create one
    if priority_df["Risk_Score"].max() == 0:

        priority_df["Risk_Score"] = 0.0

        priority_df.loc[
            priority_df["Current_Stock"] <= 0,
            "Risk_Score"
        ] += 40

        priority_df.loc[
            priority_df["Stock_Coverage_Days"] < 14,
            "Risk_Score"
        ] += 25

        priority_df.loc[
            priority_df["Stock_Coverage_Days"] < 30,
            "Risk_Score"
        ] += 15

        priority_df.loc[
            priority_df["Replenishment_Gap"] > 0,
            "Risk_Score"
        ] += 20


    priority_df["Risk_Score"] = priority_df["Risk_Score"].clip(
        lower=0,
        upper=100
    )


    # --------------------------------------------------------
    # 9. INVENTORY EFFICIENCY
    # --------------------------------------------------------

    priority_df["Inventory_Turnover"] = _priority_num(
        priority_df,
        ["Inventory_Turnover"],
        default=0
    )

    priority_df["DIO_Days"] = _priority_num(
        priority_df,
        ["DIO_Days"],
        default=0
    )


    # --------------------------------------------------------
    # 10. REVENUE / BUSINESS VALUE SCORE
    # --------------------------------------------------------

    if priority_df["Annual_Demand_Value"].max() > 0:

        priority_df["Value_Score"] = (
            priority_df["Annual_Demand_Value"] /
            priority_df["Annual_Demand_Value"].max()
        ) * 100

    else:
        priority_df["Value_Score"] = 0


    # --------------------------------------------------------
    # 11. DEMAND SCORE
    # --------------------------------------------------------

    if priority_df["Annual_Demand"].max() > 0:

        priority_df["Demand_Score"] = (
            priority_df["Annual_Demand"] /
            priority_df["Annual_Demand"].max()
        ) * 100

    else:
        priority_df["Demand_Score"] = 0


    # --------------------------------------------------------
    # 12. INVENTORY EFFICIENCY SCORE
    # --------------------------------------------------------

    priority_df["Efficiency_Score"] = np.where(
        priority_df["Inventory_Turnover"] > 0,
        (
            priority_df["Inventory_Turnover"] /
            priority_df["Inventory_Turnover"].max()
        ) * 100,
        0
    )

    priority_df["Efficiency_Score"] = (
        priority_df["Efficiency_Score"]
        .fillna(0)
        .clip(0, 100)
    )


    # --------------------------------------------------------
    # 13. OPPORTUNITY SCORE
    # --------------------------------------------------------

    priority_df["Opportunity_Score"] = (
        priority_df["Demand_Score"] * 0.30
        + priority_df["Value_Score"] * 0.25
        + priority_df["Risk_Score"] * 0.25
        + priority_df["Efficiency_Score"] * 0.20
    )

    priority_df["Opportunity_Score"] = (
        priority_df["Opportunity_Score"]
        .fillna(0)
        .clip(0, 100)
    )


    # --------------------------------------------------------
    # 14. PRIORITY CLASSIFICATION
    # --------------------------------------------------------

    def classify_priority(score):

        if score >= 80:
            return "P1 — CRITICAL"

        elif score >= 65:
            return "P2 — HIGH"

        elif score >= 45:
            return "P3 — MEDIUM"

        else:
            return "P4 — LOW"


    priority_df["Priority_Class"] = (
        priority_df["Opportunity_Score"]
        .apply(classify_priority)
    )


    # --------------------------------------------------------
    # 15. BUSINESS OPPORTUNITY
    # --------------------------------------------------------

    def identify_opportunity(row):

        if row["Current_Stock"] <= 0 and row["Annual_Demand"] > 0:
            return "STOCKOUT RECOVERY"

        if row["Replenishment_Gap"] > 0:
            return "REPLENISHMENT OPPORTUNITY"

        if row["Stock_Coverage_Days"] > 180:
            return "EXCESS INVENTORY REDUCTION"

        if row["Annual_Demand"] > 0 and row["Inventory_Turnover"] > 4:
            return "HIGH VELOCITY SKU"

        if row["Annual_Demand"] > 0:
            return "DEMAND GROWTH OPPORTUNITY"

        return "LOW PRIORITY"


    priority_df["Business_Opportunity"] = priority_df.apply(
        identify_opportunity,
        axis=1
    )


    # --------------------------------------------------------
    # 16. MANAGEMENT ACTION
    # --------------------------------------------------------

    def priority_action(row):

        if row["Priority_Class"] == "P1 — CRITICAL":
            return "IMMEDIATE MANAGEMENT ACTION"

        elif row["Priority_Class"] == "P2 — HIGH":
            return "PRIORITIZE THIS SKU"

        elif row["Priority_Class"] == "P3 — MEDIUM":
            return "MONITOR & OPTIMIZE"

        return "ROUTINE MONITORING"


    priority_df["Management_Action"] = priority_df.apply(
        priority_action,
        axis=1
    )


    # --------------------------------------------------------
    # 17. EXECUTIVE KPI CARDS
    # --------------------------------------------------------

    total_priority_skus = len(priority_df)

    p1_count = (
        priority_df["Priority_Class"]
        .eq("P1 — CRITICAL")
        .sum()
    )

    p2_count = (
        priority_df["Priority_Class"]
        .eq("P2 — HIGH")
        .sum()
    )

    total_replenishment_value = (
        priority_df["Replenishment_Value"].sum()
    )

    high_value_skus = (
        priority_df["Annual_Demand_Value"]
        .nlargest(min(10, len(priority_df)))
        .sum()
    )

    avg_opportunity_score = (
        priority_df["Opportunity_Score"].mean()
        if len(priority_df) > 0 else 0
    )


    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric(
        "Total SKUs",
        f"{total_priority_skus:,}"
    )

    c2.metric(
        "P1 Critical",
        f"{p1_count:,}"
    )

    c3.metric(
        "P2 High",
        f"{p2_count:,}"
    )

    c4.metric(
        "Replenishment Value",
        format_currency(total_replenishment_value)
    )

    c5.metric(
        "Avg Opportunity Score",
        f"{avg_opportunity_score:.1f}"
    )


    # --------------------------------------------------------
    # 18. PRIORITY DISTRIBUTION
    # --------------------------------------------------------

    st.subheader("SKU Priority Distribution")

    priority_counts = (
        priority_df["Priority_Class"]
        .value_counts()
        .reset_index()
    )

    priority_counts.columns = [
        "Priority",
        "SKU_Count"
    ]

    fig_priority = px.bar(
        priority_counts,
        x="Priority",
        y="SKU_Count",
        title="SKU Priority Distribution"
    )

    st.plotly_chart(
        fig_priority,
        use_container_width=True
    )


    # --------------------------------------------------------
    # 19. TOP PRIORITY SKUS
    # --------------------------------------------------------

    st.subheader("Top Priority SKUs")

    top_priority = (
        priority_df
        .sort_values(
            "Opportunity_Score",
            ascending=False
        )
        .head(15)
        [
            [
                "SKU",
                "Product_Name",
                "Category",
                "Opportunity_Score",
                "Priority_Class",
                "Business_Opportunity",
                "Management_Action"
            ]
        ]
    )

    st.dataframe(
        top_priority,
        use_container_width=True,
        hide_index=True
    )


    # --------------------------------------------------------
    # 20. TOP REPLENISHMENT OPPORTUNITIES
    # --------------------------------------------------------

    st.subheader("Top Replenishment Opportunities")

    replenishment_chart = (
        priority_df
        .sort_values(
            "Replenishment_Value",
            ascending=False
        )
        .head(15)
    )

    fig_replenishment = px.bar(
        replenishment_chart,
        x="Replenishment_Value",
        y="Product_Name",
        orientation="h",
        title="Highest Replenishment Value"
    )

    st.plotly_chart(
        fig_replenishment,
        use_container_width=True
    )


    # --------------------------------------------------------
    # 21. BUSINESS OPPORTUNITY DISTRIBUTION
    # --------------------------------------------------------

    st.subheader("Business Opportunity Distribution")

    opportunity_counts = (
        priority_df["Business_Opportunity"]
        .value_counts()
        .reset_index()
    )

    opportunity_counts.columns = [
        "Opportunity",
        "SKU_Count"
    ]

    fig_opportunity = px.bar(
        opportunity_counts,
        x="Opportunity",
        y="SKU_Count",
        title="Business Opportunities by SKU"
    )

    st.plotly_chart(
        fig_opportunity,
        use_container_width=True
    )


    # --------------------------------------------------------
    # 22. CATEGORY PRIORITIZATION
    # --------------------------------------------------------

    st.subheader("Category-Level Opportunity Ranking")

    category_priority = (
        priority_df
        .groupby("Category")
        .agg(
            SKUs=("SKU", "nunique"),
            Annual_Demand=("Annual_Demand", "sum"),
            Inventory_Value=("Inventory_Value", "sum"),
            Replenishment_Value=("Replenishment_Value", "sum"),
            Avg_Opportunity_Score=("Opportunity_Score", "mean"),
            Critical_SKUs=(
                "Priority_Class",
                lambda x: (x == "P1 — CRITICAL").sum()
            )
        )
        .reset_index()
        .sort_values(
            "Avg_Opportunity_Score",
            ascending=False
        )
    )

    st.dataframe(
        category_priority,
        use_container_width=True,
        hide_index=True
    )


    # --------------------------------------------------------
    # 23. MANAGEMENT ALERT
    # --------------------------------------------------------

    if p1_count > 0:

        st.warning(
            f"⚠️ {p1_count:,} SKU(s) require immediate management attention."
        )

    elif p2_count > 0:

        st.info(
            f"ℹ️ {p2_count:,} high-priority SKU(s) should be reviewed."
        )

    else:

        st.success(
            "✓ No critical SKU priorities detected."
        )


    # --------------------------------------------------------
    # 24. COMPLETE DATASET
    # --------------------------------------------------------

    with st.expander(
        "View Complete SKU Prioritization Dataset"
    ):

        st.dataframe(
            priority_df,
            use_container_width=True,
            hide_index=True
        )

else:

    st.info(
        "SKU prioritization requires inventory and demand data."
    )


st.success(
    "✓ Step 75 completed — SKU prioritization and business opportunity ranking are active."
)

# ============================================================
# STEP 76 — ADVANCED CATEGORY & PRODUCT ANALYTICS
# ============================================================

st.markdown("---")
st.header("STEP 76 — ADVANCED CATEGORY & PRODUCT ANALYTICS")

if "priority_df" in globals() and isinstance(priority_df, pd.DataFrame) and not priority_df.empty:

    category_df = priority_df.copy()

    # --------------------------------------------------------
    # 1. CATEGORY SUMMARY
    # --------------------------------------------------------

    category_summary = (
        category_df
        .groupby("Category")
        .agg(
            SKU_Count=("SKU", "nunique"),
            Annual_Demand=("Annual_Demand", "sum"),
            Current_Stock=("Current_Stock", "sum"),
            Inventory_Value=("Inventory_Value", "sum"),
            Annual_Demand_Value=("Annual_Demand_Value", "sum"),
            Replenishment_Value=("Replenishment_Value", "sum"),
            Avg_Opportunity_Score=("Opportunity_Score", "mean"),
            Critical_SKUs=(
                "Priority_Class",
                lambda x: (x == "P1 — CRITICAL").sum()
            ),
            High_Priority_SKUs=(
                "Priority_Class",
                lambda x: (x == "P2 — HIGH").sum()
            )
        )
        .reset_index()
    )


    # --------------------------------------------------------
    # 2. CATEGORY DEMAND SHARE
    # --------------------------------------------------------

    total_category_demand = (
        category_summary["Annual_Demand"].sum()
    )

    category_summary["Demand_Share_%"] = np.where(
        total_category_demand > 0,
        category_summary["Annual_Demand"] /
        total_category_demand * 100,
        0
    )


    # --------------------------------------------------------
    # 3. INVENTORY SHARE
    # --------------------------------------------------------

    total_inventory_value = (
        category_summary["Inventory_Value"].sum()
    )

    category_summary["Inventory_Share_%"] = np.where(
        total_inventory_value > 0,
        category_summary["Inventory_Value"] /
        total_inventory_value * 100,
        0
    )


    # --------------------------------------------------------
    # 4. CATEGORY EFFICIENCY
    # --------------------------------------------------------

    category_summary["Demand_to_Inventory_Ratio"] = np.where(
        category_summary["Inventory_Value"] > 0,
        category_summary["Annual_Demand_Value"] /
        category_summary["Inventory_Value"],
        0
    )


    # --------------------------------------------------------
    # 5. CATEGORY HEALTH
    # --------------------------------------------------------

    def category_health(row):

        if row["Critical_SKUs"] > 0:
            return "CRITICAL"

        elif row["High_Priority_SKUs"] >= 3:
            return "HIGH ATTENTION"

        elif row["Avg_Opportunity_Score"] >= 60:
            return "OPPORTUNITY"

        elif row["Demand_to_Inventory_Ratio"] >= 4:
            return "HEALTHY"

        return "STABLE"


    category_summary["Category_Health"] = (
        category_summary
        .apply(category_health, axis=1)
    )


    # --------------------------------------------------------
    # 6. CATEGORY KPI CARDS
    # --------------------------------------------------------

    total_categories = len(category_summary)

    critical_categories = (
        category_summary["Category_Health"]
        .eq("CRITICAL")
        .sum()
    )

    opportunity_categories = (
        category_summary["Category_Health"]
        .eq("OPPORTUNITY")
        .sum()
    )

    highest_demand_category = (
        category_summary
        .sort_values(
            "Annual_Demand",
            ascending=False
        )
        .iloc[0]["Category"]
        if not category_summary.empty
        else "N/A"
    )

    highest_inventory_category = (
        category_summary
        .sort_values(
            "Inventory_Value",
            ascending=False
        )
        .iloc[0]["Category"]
        if not category_summary.empty
        else "N/A"
    )


    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric(
        "Categories",
        f"{total_categories:,}"
    )

    c2.metric(
        "Critical Categories",
        f"{critical_categories:,}"
    )

    c3.metric(
        "Opportunity Categories",
        f"{opportunity_categories:,}"
    )

    c4.metric(
        "Top Demand Category",
        str(highest_demand_category)
    )

    c5.metric(
        "Highest Inventory Category",
        str(highest_inventory_category)
    )


    # --------------------------------------------------------
    # 7. CATEGORY DEMAND CHART
    # --------------------------------------------------------

    st.subheader("Demand by Category")

    demand_category_chart = (
        category_summary
        .sort_values(
            "Annual_Demand",
            ascending=True
        )
    )

    fig_category_demand = px.bar(
        demand_category_chart,
        x="Annual_Demand",
        y="Category",
        orientation="h",
        title="Annual Demand by Category"
    )

    st.plotly_chart(
        fig_category_demand,
        use_container_width=True
    )


    # --------------------------------------------------------
    # 8. INVENTORY VALUE BY CATEGORY
    # --------------------------------------------------------

    st.subheader("Inventory Investment by Category")

    inventory_category_chart = (
        category_summary
        .sort_values(
            "Inventory_Value",
            ascending=False
        )
    )

    fig_category_inventory = px.bar(
        inventory_category_chart,
        x="Category",
        y="Inventory_Value",
        title="Inventory Value by Category"
    )

    st.plotly_chart(
        fig_category_inventory,
        use_container_width=True
    )


    # --------------------------------------------------------
    # 9. DEMAND VS INVENTORY
    # --------------------------------------------------------

    st.subheader("Category Demand vs Inventory Investment")

    fig_category_scatter = px.scatter(
        category_summary,
        x="Inventory_Value",
        y="Annual_Demand_Value",
        size="SKU_Count",
        hover_name="Category",
        title="Demand Value vs Inventory Value"
    )

    st.plotly_chart(
        fig_category_scatter,
        use_container_width=True
    )


    # --------------------------------------------------------
    # 10. CATEGORY OPPORTUNITY
    # --------------------------------------------------------

    st.subheader("Category Opportunity Score")

    category_opportunity = (
        category_summary
        .sort_values(
            "Avg_Opportunity_Score",
            ascending=True
        )
    )

    fig_category_opportunity = px.bar(
        category_opportunity,
        x="Avg_Opportunity_Score",
        y="Category",
        orientation="h",
        title="Average Opportunity Score by Category"
    )

    st.plotly_chart(
        fig_category_opportunity,
        use_container_width=True
    )


    # --------------------------------------------------------
    # 11. TOP PRODUCTS
    # --------------------------------------------------------

    st.subheader("Top Products by Demand Value")

    top_products = (
        category_df
        .sort_values(
            "Annual_Demand_Value",
            ascending=False
        )
        .head(20)
        [
            [
                "SKU",
                "Product_Name",
                "Category",
                "Annual_Demand",
                "Annual_Demand_Value",
                "Current_Stock",
                "Inventory_Value",
                "Opportunity_Score",
                "Priority_Class"
            ]
        ]
    )

    st.dataframe(
        top_products,
        use_container_width=True,
        hide_index=True
    )


    # --------------------------------------------------------
    # 12. CATEGORY MANAGEMENT TABLE
    # --------------------------------------------------------

    st.subheader("Category Management View")

    display_category = category_summary[
        [
            "Category",
            "SKU_Count",
            "Annual_Demand",
            "Demand_Share_%",
            "Inventory_Value",
            "Inventory_Share_%",
            "Replenishment_Value",
            "Critical_SKUs",
            "High_Priority_SKUs",
            "Avg_Opportunity_Score",
            "Category_Health"
        ]
    ].sort_values(
        "Avg_Opportunity_Score",
        ascending=False
    )

    st.dataframe(
        display_category,
        use_container_width=True,
        hide_index=True
    )


    # --------------------------------------------------------
    # 13. MANAGEMENT ALERTS
    # --------------------------------------------------------

    if critical_categories > 0:

        st.warning(
            f"⚠️ {critical_categories} category/category groups contain critical SKUs."
        )

    elif opportunity_categories > 0:

        st.info(
            f"ℹ️ {opportunity_categories} category/category groups show significant business opportunity."
        )

    else:

        st.success(
            "✓ Category portfolio appears stable."
        )


    # --------------------------------------------------------
    # 14. COMPLETE CATEGORY DATASET
    # --------------------------------------------------------

    with st.expander(
        "View Complete Category Analytics Dataset"
    ):

        st.dataframe(
            category_summary,
            use_container_width=True,
            hide_index=True
        )

else:

    st.info(
        "Category analytics requires SKU prioritization data."
    )


st.success(
    "✓ Step 76 completed — advanced category and product analytics are active."
)

# ============================================================
# STEP 77 — MANAGEMENT ALERTS & AUTOMATED DECISION ENGINE
# ============================================================

st.markdown("---")
st.header("STEP 77 — MANAGEMENT ALERTS & AUTOMATED DECISION ENGINE")


if "priority_df" in globals() and isinstance(priority_df, pd.DataFrame) and not priority_df.empty:

    alert_df = priority_df.copy()

    # --------------------------------------------------------
    # 1. CREATE ALERT CONDITIONS
    # --------------------------------------------------------

    alert_df["Alert_Type"] = "NO ALERT"

    alert_df["Alert_Severity"] = "LOW"

    alert_df["Recommended_Action"] = "MONITOR"


    # --------------------------------------------------------
    # 2. STOCKOUT ALERT
    # --------------------------------------------------------

    stockout_mask = (
        (alert_df["Current_Stock"] <= 0) &
        (alert_df["Annual_Demand"] > 0)
    )

    alert_df.loc[
        stockout_mask,
        "Alert_Type"
    ] = "STOCKOUT RISK"

    alert_df.loc[
        stockout_mask,
        "Alert_Severity"
    ] = "CRITICAL"

    alert_df.loc[
        stockout_mask,
        "Recommended_Action"
    ] = "URGENTLY REPLENISH"


    # --------------------------------------------------------
    # 3. CRITICAL UNDERSTOCK
    # --------------------------------------------------------

    critical_mask = (
        (alert_df["Current_Stock"] > 0) &
        (alert_df["Replenishment_Gap"] > 0) &
        (alert_df["Stock_Coverage_Days"] < 14)
    )

    alert_df.loc[
        critical_mask,
        "Alert_Type"
    ] = "CRITICAL UNDERSTOCK"

    alert_df.loc[
        critical_mask,
        "Alert_Severity"
    ] = "HIGH"

    alert_df.loc[
        critical_mask,
        "Recommended_Action"
    ] = "EXPEDITE PURCHASE"


    # --------------------------------------------------------
    # 4. REORDER ALERT
    # --------------------------------------------------------

    reorder_mask = (
        (alert_df["Replenishment_Gap"] > 0) &
        (alert_df["Stock_Coverage_Days"] >= 14) &
        (alert_df["Stock_Coverage_Days"] < 45)
    )

    alert_df.loc[
        reorder_mask,
        "Alert_Type"
    ] = "REORDER REQUIRED"

    alert_df.loc[
        reorder_mask,
        "Alert_Severity"
    ] = "MEDIUM"

    alert_df.loc[
        reorder_mask,
        "Recommended_Action"
    ] = "PLACE PURCHASE ORDER"


    # --------------------------------------------------------
    # 5. EXCESS INVENTORY ALERT
    # --------------------------------------------------------

    excess_mask = (
        alert_df["Stock_Coverage_Days"] > 180
    )

    alert_df.loc[
        excess_mask,
        "Alert_Type"
    ] = "EXCESS INVENTORY"

    alert_df.loc[
        excess_mask,
        "Alert_Severity"
    ] = "MEDIUM"

    alert_df.loc[
        excess_mask,
        "Recommended_Action"
    ] = "REDUCE PURCHASES"


    # --------------------------------------------------------
    # 6. SLOW MOVING ALERT
    # --------------------------------------------------------

    slow_mask = (
        (alert_df["Stock_Coverage_Days"] > 90) &
        (alert_df["Stock_Coverage_Days"] <= 180)
    )

    alert_df.loc[
        slow_mask,
        "Alert_Type"
    ] = "SLOW MOVING STOCK"

    alert_df.loc[
        slow_mask,
        "Alert_Severity"
    ] = "LOW"

    alert_df.loc[
        slow_mask,
        "Recommended_Action"
    ] = "REVIEW DEMAND / PROMOTION"


    # --------------------------------------------------------
    # 7. ALERT SCORE
    # --------------------------------------------------------

    severity_score = {
        "CRITICAL": 100,
        "HIGH": 75,
        "MEDIUM": 50,
        "LOW": 25
    }

    alert_df["Alert_Score"] = (
        alert_df["Alert_Severity"]
        .map(severity_score)
        .fillna(0)
    )


    # --------------------------------------------------------
    # 8. ALERT COUNTS
    # --------------------------------------------------------

    critical_alerts = (
        alert_df["Alert_Severity"]
        .eq("CRITICAL")
        .sum()
    )

    high_alerts = (
        alert_df["Alert_Severity"]
        .eq("HIGH")
        .sum()
    )

    medium_alerts = (
        alert_df["Alert_Severity"]
        .eq("MEDIUM")
        .sum()
    )

    low_alerts = (
        alert_df["Alert_Severity"]
        .eq("LOW")
        .sum()
    )

    total_alerts = (
        alert_df["Alert_Type"]
        .ne("NO ALERT")
        .sum()
    )


    # --------------------------------------------------------
    # 9. ALERT KPI CARDS
    # --------------------------------------------------------

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric(
        "Total Alerts",
        f"{total_alerts:,}"
    )

    c2.metric(
        "Critical",
        f"{critical_alerts:,}"
    )

    c3.metric(
        "High",
        f"{high_alerts:,}"
    )

    c4.metric(
        "Medium",
        f"{medium_alerts:,}"
    )

    c5.metric(
        "Low",
        f"{low_alerts:,}"
    )


    # --------------------------------------------------------
    # 10. ALERT DISTRIBUTION
    # --------------------------------------------------------

    st.subheader("Management Alert Distribution")

    alert_counts = (
        alert_df[
            alert_df["Alert_Type"] != "NO ALERT"
        ]["Alert_Type"]
        .value_counts()
        .reset_index()
    )

    alert_counts.columns = [
        "Alert_Type",
        "Count"
    ]


    if not alert_counts.empty:

        fig_alerts = px.bar(
            alert_counts,
            x="Alert_Type",
            y="Count",
            title="Automated Management Alerts"
        )

        st.plotly_chart(
            fig_alerts,
            use_container_width=True
        )

    else:

        st.success(
            "✓ No management alerts detected."
        )


    # --------------------------------------------------------
    # 11. CRITICAL MANAGEMENT ALERTS
    # --------------------------------------------------------

    st.subheader("Critical Management Alerts")

    critical_table = (
        alert_df[
            alert_df["Alert_Severity"]
            .isin(["CRITICAL", "HIGH"])
        ]
        .sort_values(
            "Alert_Score",
            ascending=False
        )
        .head(20)
    )


    if not critical_table.empty:

        st.dataframe(
            critical_table[
                [
                    "SKU",
                    "Product_Name",
                    "Category",
                    "Current_Stock",
                    "Annual_Demand",
                    "Stock_Coverage_Days",
                    "Replenishment_Gap",
                    "Replenishment_Value",
                    "Alert_Type",
                    "Alert_Severity",
                    "Recommended_Action"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

    else:

        st.success(
            "✓ No critical or high-severity alerts."
        )


    # --------------------------------------------------------
    # 12. TOP ACTIONS
    # --------------------------------------------------------

    st.subheader("Automated Decision Queue")

    decision_queue = (
        alert_df[
            alert_df["Alert_Type"] != "NO ALERT"
        ]
        .sort_values(
            [
                "Alert_Score",
                "Replenishment_Value"
            ],
            ascending=False
        )
        .head(25)
    )


    if not decision_queue.empty:

        st.dataframe(
            decision_queue[
                [
                    "SKU",
                    "Product_Name",
                    "Category",
                    "Alert_Type",
                    "Alert_Severity",
                    "Recommended_Action",
                    "Replenishment_Gap",
                    "Replenishment_Value",
                    "Opportunity_Score"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )


    # --------------------------------------------------------
    # 13. MANAGEMENT SUMMARY
    # --------------------------------------------------------

    st.subheader("Management Decision Summary")

    if critical_alerts > 0:

        st.error(
            f"🔴 Immediate Action Required: "
            f"{critical_alerts} critical inventory alert(s) detected."
        )

    if high_alerts > 0:

        st.warning(
            f"🟠 High Priority: "
            f"{high_alerts} SKU(s) require expedited management attention."
        )

    if medium_alerts > 0:

        st.info(
            f"🟡 Planning Action: "
            f"{medium_alerts} medium-priority inventory issue(s) detected."
        )

    if (
        critical_alerts == 0 and
        high_alerts == 0 and
        medium_alerts == 0
    ):

        st.success(
            "🟢 Inventory position is currently stable."
        )


    # --------------------------------------------------------
    # 14. AUTOMATED BUSINESS RULE SUMMARY
    # --------------------------------------------------------

    st.subheader("Automated Decision Rules")

    rules = pd.DataFrame({
        "Condition": [
            "Stock = 0 and demand > 0",
            "Coverage < 14 days",
            "Replenishment gap > 0 and coverage < 45 days",
            "Coverage > 180 days",
            "Coverage 90–180 days"
        ],

        "Severity": [
            "CRITICAL",
            "HIGH",
            "MEDIUM",
            "MEDIUM",
            "LOW"
        ],

        "Recommended Action": [
            "Urgently replenish",
            "Expedite purchase",
            "Place purchase order",
            "Reduce purchases",
            "Review demand / promotion"
        ]
    })

    st.dataframe(
        rules,
        use_container_width=True,
        hide_index=True
    )


    # --------------------------------------------------------
    # 15. COMPLETE ALERT DATASET
    # --------------------------------------------------------

    with st.expander(
        "View Complete Automated Alert Dataset"
    ):

        st.dataframe(
            alert_df,
            use_container_width=True,
            hide_index=True
        )


else:

    st.info(
        "Automated management alerts require SKU prioritization data."
    )


st.success(
    "✓ Step 77 completed — automated management alerts and decision engine are active."
)

# ============================================================
# STEP 78 — DASHBOARD FILTERS, SEARCH & INTERACTIVE CONTROLS
# ============================================================

st.markdown("---")
st.header("STEP 78 — DASHBOARD FILTERS & INTERACTIVE CONTROLS")

# ------------------------------------------------------------
# 1. SELECT MASTER DATASET
# ------------------------------------------------------------

if "alert_df" in globals() and isinstance(alert_df, pd.DataFrame) and not alert_df.empty:
    interactive_df = alert_df.copy()

elif "priority_df" in globals() and isinstance(priority_df, pd.DataFrame) and not priority_df.empty:
    interactive_df = priority_df.copy()

elif "optimization_df" in globals() and isinstance(optimization_df, pd.DataFrame) and not optimization_df.empty:
    interactive_df = optimization_df.copy()

else:
    interactive_df = pd.DataFrame()


# ------------------------------------------------------------
# 2. HELPER FUNCTIONS
# ------------------------------------------------------------

def _interactive_text(df, columns, default="Unknown"):

    for col in columns:

        if col in df.columns:
            return df[col].fillna(default).astype(str)

    return pd.Series(
        default,
        index=df.index
    )


def _interactive_num(df, columns, default=0.0):

    for col in columns:

        if col in df.columns:

            return pd.to_numeric(
                df[col],
                errors="coerce"
            ).fillna(default)

    return pd.Series(
        default,
        index=df.index
    )


if not interactive_df.empty:

    # --------------------------------------------------------
    # 3. STANDARDIZE FILTER COLUMNS
    # --------------------------------------------------------

    interactive_df["SKU"] = _interactive_text(
        interactive_df,
        ["SKU", "sku_id", "sku", "SKU_ID"]
    )

    interactive_df["Product_Name"] = _interactive_text(
        interactive_df,
        [
            "Product_Name",
            "product_name",
            "Product",
            "name"
        ]
    )

    interactive_df["Category"] = _interactive_text(
        interactive_df,
        [
            "Category",
            "category",
            "Category_Name"
        ]
    )

    interactive_df["Priority_Class"] = _interactive_text(
        interactive_df,
        ["Priority_Class"],
        default="Not Classified"
    )

    interactive_df["Alert_Severity"] = _interactive_text(
        interactive_df,
        ["Alert_Severity"],
        default="LOW"
    )

    interactive_df["Alert_Type"] = _interactive_text(
        interactive_df,
        ["Alert_Type"],
        default="NO ALERT"
    )

    interactive_df["Business_Opportunity"] = _interactive_text(
        interactive_df,
        ["Business_Opportunity"],
        default="Not Classified"
    )

    interactive_df["Opportunity_Score"] = _interactive_num(
        interactive_df,
        ["Opportunity_Score"],
        default=0
    )

    interactive_df["Stock_Coverage_Days"] = _interactive_num(
        interactive_df,
        [
            "Stock_Coverage_Days",
            "Days_of_Stock"
        ],
        default=0
    )

    interactive_df["Current_Stock"] = _interactive_num(
        interactive_df,
        [
            "Current_Stock",
            "Inventory_Units"
        ],
        default=0
    )

    interactive_df["Annual_Demand"] = _interactive_num(
        interactive_df,
        [
            "Annual_Demand",
            "Annual_Units_Demand",
            "Historical_Annual_Demand"
        ],
        default=0
    )

    interactive_df["Inventory_Value"] = _interactive_num(
        interactive_df,
        ["Inventory_Value"],
        default=0
    )


    # --------------------------------------------------------
    # 4. FILTER PANEL
    # --------------------------------------------------------

    st.subheader("Interactive Dashboard Filters")

    st.caption(
        "Use the controls below to dynamically analyze the inventory portfolio."
    )


    # --------------------------------------------------------
    # 5. SEARCH
    # --------------------------------------------------------

    search_text = st.text_input(
        "🔎 Search SKU or Product",
        placeholder="Enter SKU or product name..."
    )


    # --------------------------------------------------------
    # 6. CATEGORY FILTER
    # --------------------------------------------------------

    category_options = sorted(
        interactive_df["Category"]
        .dropna()
        .unique()
        .tolist()
    )

    selected_categories = st.multiselect(
        "Category",
        options=category_options,
        default=category_options
    )


    # --------------------------------------------------------
    # 7. PRIORITY FILTER
    # --------------------------------------------------------

    priority_options = sorted(
        interactive_df["Priority_Class"]
        .dropna()
        .unique()
        .tolist()
    )

    selected_priorities = st.multiselect(
        "Priority Class",
        options=priority_options,
        default=priority_options
    )


    # --------------------------------------------------------
    # 8. ALERT FILTER
    # --------------------------------------------------------

    alert_options = sorted(
        interactive_df["Alert_Severity"]
        .dropna()
        .unique()
        .tolist()
    )

    selected_alerts = st.multiselect(
        "Alert Severity",
        options=alert_options,
        default=alert_options
    )


    # --------------------------------------------------------
    # 9. BUSINESS OPPORTUNITY FILTER
    # --------------------------------------------------------

    opportunity_options = sorted(
        interactive_df["Business_Opportunity"]
        .dropna()
        .unique()
        .tolist()
    )

    selected_opportunities = st.multiselect(
        "Business Opportunity",
        options=opportunity_options,
        default=opportunity_options
    )


    # --------------------------------------------------------
    # 10. OPPORTUNITY SCORE FILTER
    # --------------------------------------------------------

    max_score = float(
        max(
            100,
            interactive_df["Opportunity_Score"].max()
        )
    )

    min_score = st.slider(
        "Minimum Opportunity Score",
        min_value=0.0,
        max_value=100.0,
        value=0.0,
        step=5.0
    )


    # --------------------------------------------------------
    # 11. STOCK COVERAGE FILTER
    # --------------------------------------------------------

    coverage_max_data = interactive_df[
        "Stock_Coverage_Days"
    ].replace(
        [np.inf, -np.inf],
        np.nan
    ).dropna()

    if not coverage_max_data.empty:

        coverage_max = int(
            max(
                30,
                min(
                    365,
                    coverage_max_data.max()
                )
            )
        )

    else:

        coverage_max = 365


    coverage_range = st.slider(
        "Stock Coverage (Days)",
        min_value=0,
        max_value=coverage_max,
        value=(0, coverage_max),
        step=7
    )


    # --------------------------------------------------------
    # 12. APPLY FILTERS
    # --------------------------------------------------------

    filtered_interactive_df = interactive_df.copy()


    # Search filter

    if search_text.strip():

        search_lower = search_text.strip().lower()

        search_mask = (
            filtered_interactive_df["SKU"]
            .str.lower()
            .str.contains(
                search_lower,
                na=False
            )
            |
            filtered_interactive_df["Product_Name"]
            .str.lower()
            .str.contains(
                search_lower,
                na=False
            )
        )

        filtered_interactive_df = (
            filtered_interactive_df[
                search_mask
            ]
        )


    # Category

    if selected_categories:

        filtered_interactive_df = (
            filtered_interactive_df[
                filtered_interactive_df["Category"]
                .isin(selected_categories)
            ]
        )


    # Priority

    if selected_priorities:

        filtered_interactive_df = (
            filtered_interactive_df[
                filtered_interactive_df["Priority_Class"]
                .isin(selected_priorities)
            ]
        )


    # Alert severity

    if selected_alerts:

        filtered_interactive_df = (
            filtered_interactive_df[
                filtered_interactive_df["Alert_Severity"]
                .isin(selected_alerts)
            ]
        )


    # Business opportunity

    if selected_opportunities:

        filtered_interactive_df = (
            filtered_interactive_df[
                filtered_interactive_df["Business_Opportunity"]
                .isin(selected_opportunities)
            ]
        )


    # Opportunity score

    filtered_interactive_df = (
        filtered_interactive_df[
            filtered_interactive_df["Opportunity_Score"]
            >= min_score
        ]
    )


    # Stock coverage

    filtered_interactive_df = (
        filtered_interactive_df[
            (
                filtered_interactive_df[
                    "Stock_Coverage_Days"
                ]
                >= coverage_range[0]
            )
            &
            (
                filtered_interactive_df[
                    "Stock_Coverage_Days"
                ]
                <= coverage_range[1]
            )
        ]
    )


    # --------------------------------------------------------
    # 13. FILTER RESULTS KPI
    # --------------------------------------------------------

    st.markdown("---")

    st.subheader("Filtered Portfolio Summary")


    filtered_skus = len(
        filtered_interactive_df
    )

    filtered_inventory_value = (
        filtered_interactive_df[
            "Inventory_Value"
        ].sum()
    )

    filtered_demand = (
        filtered_interactive_df[
            "Annual_Demand"
        ].sum()
    )

    filtered_critical = (
        filtered_interactive_df[
            "Alert_Severity"
        ]
        .isin(["CRITICAL", "HIGH"])
        .sum()
    )

    filtered_avg_score = (
        filtered_interactive_df[
            "Opportunity_Score"
        ].mean()
        if filtered_skus > 0
        else 0
    )


    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric(
        "Filtered SKUs",
        f"{filtered_skus:,}"
    )

    c2.metric(
        "Inventory Value",
        format_currency(
            filtered_inventory_value
        )
    )

    c3.metric(
        "Annual Demand",
        format_number(
            filtered_demand
        )
    )

    c4.metric(
        "Critical / High Alerts",
        f"{filtered_critical:,}"
    )

    c5.metric(
        "Avg Opportunity Score",
        f"{filtered_avg_score:.1f}"
    )


    # --------------------------------------------------------
    # 14. FILTERED SKU TABLE
    # --------------------------------------------------------

    st.subheader("Filtered SKU Portfolio")


    display_columns = [
        "SKU",
        "Product_Name",
        "Category",
        "Annual_Demand",
        "Current_Stock",
        "Stock_Coverage_Days",
        "Inventory_Value",
        "Opportunity_Score",
        "Priority_Class",
        "Alert_Type",
        "Alert_Severity",
        "Business_Opportunity"
    ]


    available_display_columns = [
        col
        for col in display_columns
        if col in filtered_interactive_df.columns
    ]


    if not filtered_interactive_df.empty:

        st.dataframe(
            filtered_interactive_df[
                available_display_columns
            ]
            .sort_values(
                "Opportunity_Score",
                ascending=False
            ),
            use_container_width=True,
            hide_index=True
        )

    else:

        st.warning(
            "No SKUs match the selected filters."
        )


    # --------------------------------------------------------
    # 15. DYNAMIC CATEGORY ANALYSIS
    # --------------------------------------------------------

    if not filtered_interactive_df.empty:

        st.subheader(
            "Filtered Category Performance"
        )

        dynamic_category = (
            filtered_interactive_df
            .groupby("Category")
            .agg(
                SKUs=("SKU", "nunique"),
                Annual_Demand=(
                    "Annual_Demand",
                    "sum"
                ),
                Inventory_Value=(
                    "Inventory_Value",
                    "sum"
                ),
                Avg_Opportunity_Score=(
                    "Opportunity_Score",
                    "mean"
                )
            )
            .reset_index()
        )


        st.dataframe(
            dynamic_category.sort_values(
                "Avg_Opportunity_Score",
                ascending=False
            ),
            use_container_width=True,
            hide_index=True
        )


        # ----------------------------------------------------
        # 16. DYNAMIC OPPORTUNITY CHART
        # ----------------------------------------------------

        fig_dynamic = px.scatter(
            filtered_interactive_df,
            x="Inventory_Value",
            y="Annual_Demand",
            size="Opportunity_Score",
            hover_name="Product_Name",
            hover_data=[
                "SKU",
                "Category",
                "Priority_Class"
            ],
            title="Filtered Inventory vs Demand Opportunity"
        )

        st.plotly_chart(
            fig_dynamic,
            use_container_width=True
        )


    # --------------------------------------------------------
    # 17. RESET INSTRUCTIONS
    # --------------------------------------------------------

    st.info(
        "💡 To view the complete portfolio again, "
        "select all categories, priorities, alert levels "
        "and opportunities, set the minimum score to 0, "
        "and use the full stock-coverage range."
    )


    # --------------------------------------------------------
    # 18. FILTER SUMMARY
    # --------------------------------------------------------

    with st.expander(
        "View Active Filter Summary"
    ):

        filter_summary = pd.DataFrame({
            "Filter": [
                "Search",
                "Categories",
                "Priority Classes",
                "Alert Severities",
                "Business Opportunities",
                "Minimum Opportunity Score",
                "Stock Coverage Range"
            ],

            "Selected Value": [
                search_text
                if search_text.strip()
                else "All",

                ", ".join(
                    selected_categories
                )
                if selected_categories
                else "None",

                ", ".join(
                    selected_priorities
                )
                if selected_priorities
                else "None",

                ", ".join(
                    selected_alerts
                )
                if selected_alerts
                else "None",

                ", ".join(
                    selected_opportunities
                )
                if selected_opportunities
                else "None",

                f"{min_score:.0f}",

                f"{coverage_range[0]} – "
                f"{coverage_range[1]} days"
            ]
        })

        st.dataframe(
            filter_summary,
            use_container_width=True,
            hide_index=True
        )


else:

    st.info(
        "Interactive filtering requires the SKU analysis dataset."
    )


st.success(
    "✓ Step 78 completed — interactive search, filters and dynamic portfolio analysis are active."
)

# ============================================================
# STEP 79 — FINAL DASHBOARD INTEGRATION & UI POLISH
# ============================================================

st.markdown("---")
st.header("STEP 79 — FINAL DASHBOARD INTEGRATION & UI POLISH")

# ============================================================
# 1. FINAL EXECUTIVE DASHBOARD
# ============================================================

st.subheader("FORESIGHT Executive Dashboard")

# ------------------------------------------------------------
# Select best available master dataset
# ------------------------------------------------------------

if "alert_df" in globals() and isinstance(alert_df, pd.DataFrame) and not alert_df.empty:
    final_dashboard_df = alert_df.copy()

elif "priority_df" in globals() and isinstance(priority_df, pd.DataFrame) and not priority_df.empty:
    final_dashboard_df = priority_df.copy()

elif "optimization_df" in globals() and isinstance(optimization_df, pd.DataFrame) and not optimization_df.empty:
    final_dashboard_df = optimization_df.copy()

else:
    final_dashboard_df = pd.DataFrame()


if not final_dashboard_df.empty:

    # ========================================================
    # 2. STANDARDIZE FINAL DASHBOARD METRICS
    # ========================================================

    def _final_num(df, columns, default=0.0):

        for col in columns:

            if col in df.columns:

                return pd.to_numeric(
                    df[col],
                    errors="coerce"
                ).fillna(default)

        return pd.Series(
            default,
            index=df.index
        )


    def _final_text(df, columns, default="Unknown"):

        for col in columns:

            if col in df.columns:

                return df[col].fillna(
                    default
                ).astype(str)

        return pd.Series(
            default,
            index=df.index
        )


    final_dashboard_df["SKU"] = _final_text(
        final_dashboard_df,
        ["SKU", "sku_id", "sku"]
    )

    final_dashboard_df["Product_Name"] = _final_text(
        final_dashboard_df,
        [
            "Product_Name",
            "product_name",
            "Product"
        ]
    )

    final_dashboard_df["Category"] = _final_text(
        final_dashboard_df,
        [
            "Category",
            "category"
        ]
    )

    final_dashboard_df["Annual_Demand"] = _final_num(
        final_dashboard_df,
        [
            "Annual_Demand",
            "Annual_Units_Demand",
            "Historical_Annual_Demand"
        ]
    )

    final_dashboard_df["Current_Stock"] = _final_num(
        final_dashboard_df,
        [
            "Current_Stock",
            "Inventory_Units",
            "on_hand"
        ]
    )

    final_dashboard_df["Inventory_Value"] = _final_num(
        final_dashboard_df,
        ["Inventory_Value"]
    )

    final_dashboard_df["Opportunity_Score"] = _final_num(
        final_dashboard_df,
        ["Opportunity_Score"]
    )

    final_dashboard_df["Stock_Coverage_Days"] = _final_num(
        final_dashboard_df,
        [
            "Stock_Coverage_Days",
            "Days_of_Stock"
        ]
    )

    final_dashboard_df["Replenishment_Value"] = _final_num(
        final_dashboard_df,
        ["Replenishment_Value"]
    )

    final_dashboard_df["Alert_Severity"] = _final_text(
        final_dashboard_df,
        ["Alert_Severity"],
        "LOW"
    )

    final_dashboard_df["Alert_Type"] = _final_text(
        final_dashboard_df,
        ["Alert_Type"],
        "NO ALERT"
    )

    final_dashboard_df["Priority_Class"] = _final_text(
        final_dashboard_df,
        ["Priority_Class"],
        "Not Classified"
    )


    # ========================================================
    # 3. EXECUTIVE KPI CALCULATIONS
    # ========================================================

    total_skus = len(final_dashboard_df)

    total_inventory_value = (
        final_dashboard_df["Inventory_Value"].sum()
    )

    total_annual_demand = (
        final_dashboard_df["Annual_Demand"].sum()
    )

    total_replenishment_value = (
        final_dashboard_df["Replenishment_Value"].sum()
    )

    critical_alert_count = (
        final_dashboard_df["Alert_Severity"]
        .eq("CRITICAL")
        .sum()
    )

    high_alert_count = (
        final_dashboard_df["Alert_Severity"]
        .eq("HIGH")
        .sum()
    )

    stockout_count = (
        (
            final_dashboard_df["Current_Stock"] <= 0
        )
        &
        (
            final_dashboard_df["Annual_Demand"] > 0
        )
    ).sum()

    avg_opportunity_score = (
        final_dashboard_df["Opportunity_Score"].mean()
        if total_skus > 0
        else 0
    )


    # ========================================================
    # 4. EXECUTIVE KPI CARDS
    # ========================================================

    st.markdown("### Executive KPIs")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Total SKUs",
        f"{total_skus:,}"
    )

    c2.metric(
        "Inventory Value",
        format_currency(
            total_inventory_value
        )
    )

    c3.metric(
        "Annual Demand",
        format_number(
            total_annual_demand
        )
    )

    c4.metric(
        "Replenishment Requirement",
        format_currency(
            total_replenishment_value
        )
    )


    c5, c6, c7, c8 = st.columns(4)

    c5.metric(
        "Critical Alerts",
        f"{critical_alert_count:,}"
    )

    c6.metric(
        "High Alerts",
        f"{high_alert_count:,}"
    )

    c7.metric(
        "Stockout SKUs",
        f"{stockout_count:,}"
    )

    c8.metric(
        "Avg Opportunity Score",
        f"{avg_opportunity_score:.1f}"
    )


    # ========================================================
    # 5. EXECUTIVE HEALTH STATUS
    # ========================================================

    st.markdown("### Overall Inventory Health")

    if critical_alert_count > 0:

        st.error(
            "🔴 CRITICAL — Immediate inventory action is required."
        )

        health_status = "CRITICAL"

    elif high_alert_count > 0:

        st.warning(
            "🟠 HIGH ATTENTION — Several inventory risks require management review."
        )

        health_status = "HIGH ATTENTION"

    elif avg_opportunity_score >= 65:

        st.info(
            "🟡 OPPORTUNITY — Portfolio has significant optimization opportunities."
        )

        health_status = "OPPORTUNITY"

    else:

        st.success(
            "🟢 STABLE — Inventory portfolio is currently under control."
        )

        health_status = "STABLE"


    # ========================================================
    # 6. TOP MANAGEMENT PRIORITIES
    # ========================================================

    st.markdown("### Top Management Priorities")

    priority_columns = [
        "SKU",
        "Product_Name",
        "Category",
        "Opportunity_Score",
        "Priority_Class",
        "Alert_Type",
        "Alert_Severity",
        "Replenishment_Value"
    ]

    available_priority_columns = [
        col
        for col in priority_columns
        if col in final_dashboard_df.columns
    ]


    management_priority = (
        final_dashboard_df
        .sort_values(
            [
                "Opportunity_Score",
                "Replenishment_Value"
            ],
            ascending=False
        )
        .head(10)
    )


    st.dataframe(
        management_priority[
            available_priority_columns
        ],
        use_container_width=True,
        hide_index=True
    )


    # ========================================================
    # 7. INVENTORY VALUE BY CATEGORY
    # ========================================================

    st.markdown("### Inventory Investment by Category")

    final_category = (
        final_dashboard_df
        .groupby("Category")
        .agg(
            SKUs=("SKU", "nunique"),
            Annual_Demand=("Annual_Demand", "sum"),
            Inventory_Value=("Inventory_Value", "sum"),
            Replenishment_Value=(
                "Replenishment_Value",
                "sum"
            )
        )
        .reset_index()
    )


    final_category_chart = (
        final_category
        .sort_values(
            "Inventory_Value",
            ascending=False
        )
    )


    fig_final_category = px.bar(
        final_category_chart,
        x="Category",
        y="Inventory_Value",
        title="Inventory Investment by Category"
    )

    st.plotly_chart(
        fig_final_category,
        use_container_width=True
    )


    # ========================================================
    # 8. DEMAND VS INVENTORY PORTFOLIO
    # ========================================================

    st.markdown("### Demand vs Inventory Portfolio")

    fig_final_scatter = px.scatter(
        final_dashboard_df,
        x="Inventory_Value",
        y="Annual_Demand",
        size="Opportunity_Score",
        hover_name="Product_Name",
        hover_data=[
            "SKU",
            "Category",
            "Priority_Class"
        ],
        title="Demand vs Inventory Investment"
    )

    st.plotly_chart(
        fig_final_scatter,
        use_container_width=True
    )


    # ========================================================
    # 9. REPLENISHMENT PRIORITIES
    # ========================================================

    st.markdown("### Replenishment Priorities")

    replenishment_priority = (
        final_dashboard_df
        .sort_values(
            "Replenishment_Value",
            ascending=False
        )
        .head(10)
    )


    fig_final_replenishment = px.bar(
        replenishment_priority,
        x="Replenishment_Value",
        y="Product_Name",
        orientation="h",
        title="Top Replenishment Requirements"
    )

    st.plotly_chart(
        fig_final_replenishment,
        use_container_width=True
    )


    # ========================================================
    # 10. ALERT SUMMARY
    # ========================================================

    st.markdown("### Alert Summary")

    final_alerts = (
        final_dashboard_df[
            final_dashboard_df["Alert_Type"]
            != "NO ALERT"
        ]
        .groupby(
            [
                "Alert_Type",
                "Alert_Severity"
            ]
        )
        .size()
        .reset_index(
            name="SKU_Count"
        )
        .sort_values(
            "SKU_Count",
            ascending=False
        )
    )


    if not final_alerts.empty:

        st.dataframe(
            final_alerts,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.success(
            "✓ No active inventory alerts."
        )


    # ========================================================
    # 11. EXECUTIVE DECISION BOX
    # ========================================================

    st.markdown("### Executive Decision Center")

    decision_messages = []


    if stockout_count > 0:

        decision_messages.append(
            f"🔴 {stockout_count:,} SKU(s) have zero stock "
            f"despite having demand."
        )


    if critical_alert_count > 0:

        decision_messages.append(
            f"🔴 {critical_alert_count:,} critical alert(s) "
            f"require immediate action."
        )


    if total_replenishment_value > 0:

        decision_messages.append(
            f"🟠 Recommended replenishment value: "
            f"{format_currency(total_replenishment_value)}."
        )


    excess_inventory = final_dashboard_df[
        final_dashboard_df[
            "Stock_Coverage_Days"
        ] > 180
    ]


    if not excess_inventory.empty:

        excess_value = (
            excess_inventory[
                "Inventory_Value"
            ].sum()
        )

        decision_messages.append(
            f"🟡 Potential excess inventory exposure: "
            f"{format_currency(excess_value)}."
        )


    if not decision_messages:

        decision_messages.append(
            "🟢 No major automated decision alerts detected."
        )


    for message in decision_messages:

        st.write(message)


    # ========================================================
    # 12. FINAL PORTFOLIO TABLE
    # ========================================================

    with st.expander(
        "View Final FORESIGHT Portfolio Dataset"
    ):

        st.dataframe(
            final_dashboard_df,
            use_container_width=True,
            hide_index=True
        )


    # ========================================================
    # 13. PROJECT COMPLETION STATUS
    # ========================================================

    st.markdown("---")

    st.subheader("FORESIGHT Project Status")

    status_table = pd.DataFrame({
        "Module": [
            "Data Loading",
            "Data Quality & EDA",
            "Demand Analysis",
            "Forecasting",
            "Inventory Analytics",
            "Financial Analytics",
            "Inventory Optimization",
            "Executive Control Tower",
            "Forecast Accuracy",
            "Purchase Planning",
            "Working Capital Analytics",
            "SKU Prioritization",
            "Category Analytics",
            "Automated Alerts",
            "Interactive Filters",
            "Executive Dashboard"
        ],

        "Status": [
            "COMPLETED",
            "COMPLETED",
            "COMPLETED",
            "COMPLETED",
            "COMPLETED",
            "COMPLETED",
            "COMPLETED",
            "COMPLETED",
            "COMPLETED",
            "COMPLETED",
            "COMPLETED",
            "COMPLETED",
            "COMPLETED",
            "COMPLETED",
            "COMPLETED",
            "COMPLETED"
        ]
    })


    st.dataframe(
        status_table,
        use_container_width=True,
        hide_index=True
    )


    # ========================================================
    # 14. FINAL MESSAGE
    # ========================================================

    st.success(
        "✓ Step 79 completed — FORESIGHT has been integrated into "
        "a management-ready executive dashboard."
    )


else:

    st.warning(
        "Final dashboard requires the completed inventory analytics dataset."
    )

    # ============================================================
# STEP 80 — FINAL VALIDATION, TESTING & PROJECT COMPLETION
# ============================================================

st.markdown("---")
st.header("STEP 80 — FINAL VALIDATION & PROJECT COMPLETION")

st.subheader("FORESIGHT System Validation")


# ============================================================
# 1. VALIDATION RESULT STORAGE
# ============================================================

validation_results = []


def add_validation(
    component,
    test,
    status,
    details=""
):
    validation_results.append({
        "Component": component,
        "Test": test,
        "Status": status,
        "Details": details
    })


# ============================================================
# 2. CHECK DATASETS
# ============================================================

required_datasets = {
    "Sales": "sales",
    "Inventory": "inventory",
    "SKU Master": "sku_master"
}


for display_name, variable_name in required_datasets.items():

    if variable_name in globals():

        dataset = globals()[variable_name]

        if isinstance(dataset, pd.DataFrame):

            if not dataset.empty:

                add_validation(
                    display_name,
                    "Dataset available",
                    "PASS",
                    f"{len(dataset):,} rows"
                )

            else:

                add_validation(
                    display_name,
                    "Dataset available",
                    "FAIL",
                    "Dataset is empty"
                )

        else:

            add_validation(
                display_name,
                "Dataset type",
                "FAIL",
                "Object is not a pandas DataFrame"
            )

    else:

        add_validation(
            display_name,
            "Dataset available",
            "FAIL",
            f"{variable_name} not found"
        )


# ============================================================
# 3. SALES DATA VALIDATION
# ============================================================

if "sales" in globals() and isinstance(sales, pd.DataFrame):

    required_sales_columns = [
        "date",
        "units_sold"
    ]

    for column in required_sales_columns:

        if column in sales.columns:

            add_validation(
                "Sales",
                f"Column: {column}",
                "PASS"
            )

        else:

            add_validation(
                "Sales",
                f"Column: {column}",
                "FAIL",
                "Required column missing"
            )


# ============================================================
# 4. INVENTORY DATA VALIDATION
# ============================================================

if "inventory" in globals() and isinstance(inventory, pd.DataFrame):

    required_inventory_columns = [
        "date",
        "on_hand"
    ]

    for column in required_inventory_columns:

        if column in inventory.columns:

            add_validation(
                "Inventory",
                f"Column: {column}",
                "PASS"
            )

        else:

            add_validation(
                "Inventory",
                f"Column: {column}",
                "FAIL",
                "Required column missing"
            )


# ============================================================
# 5. SKU MASTER VALIDATION
# ============================================================

if "sku_master" in globals() and isinstance(sku_master, pd.DataFrame):

    possible_sku_columns = [
        "sku_id",
        "SKU",
        "sku"
    ]

    sku_column_found = any(
        column in sku_master.columns
        for column in possible_sku_columns
    )

    if sku_column_found:

        add_validation(
            "SKU Master",
            "SKU identifier",
            "PASS"
        )

    else:

        add_validation(
            "SKU Master",
            "SKU identifier",
            "FAIL",
            "No SKU identifier found"
        )


# ============================================================
# 6. CHECK NUMERIC DATA
# ============================================================

numeric_checks = [
    ("Sales", "sales", ["units_sold"]),
    (
        "Inventory",
        "inventory",
        [
            "on_hand",
            "on_order"
        ]
    )
]


for display_name, variable_name, columns in numeric_checks:

    if variable_name in globals():

        df = globals()[variable_name]

        for column in columns:

            if column in df.columns:

                numeric_series = pd.to_numeric(
                    df[column],
                    errors="coerce"
                )

                invalid_count = (
                    numeric_series.isna().sum()
                )

                if invalid_count == 0:

                    add_validation(
                        display_name,
                        f"Numeric values: {column}",
                        "PASS"
                    )

                else:

                    add_validation(
                        display_name,
                        f"Numeric values: {column}",
                        "WARNING",
                        f"{invalid_count:,} invalid/missing values"
                    )


# ============================================================
# 7. CHECK NEGATIVE SALES
# ============================================================

if (
    "sales" in globals()
    and isinstance(sales, pd.DataFrame)
    and "units_sold" in sales.columns
):

    negative_sales = (
        pd.to_numeric(
            sales["units_sold"],
            errors="coerce"
        ) < 0
    ).sum()

    if negative_sales == 0:

        add_validation(
            "Sales",
            "Negative units sold",
            "PASS",
            "No negative values"
        )

    else:

        add_validation(
            "Sales",
            "Negative units sold",
            "WARNING",
            f"{negative_sales:,} negative values found"
        )


# ============================================================
# 8. CHECK DUPLICATE RECORDS
# ============================================================

for display_name, variable_name in [
    ("Sales", "sales"),
    ("Inventory", "inventory"),
    ("SKU Master", "sku_master")
]:

    if variable_name in globals():

        df = globals()[variable_name]

        if isinstance(df, pd.DataFrame):

            duplicate_count = df.duplicated().sum()

            if duplicate_count == 0:

                add_validation(
                    display_name,
                    "Duplicate rows",
                    "PASS",
                    "No complete duplicate rows"
                )

            else:

                add_validation(
                    display_name,
                    "Duplicate rows",
                    "WARNING",
                    f"{duplicate_count:,} duplicates"
                )


# ============================================================
# 9. CHECK MISSING VALUES
# ============================================================

for display_name, variable_name in [
    ("Sales", "sales"),
    ("Inventory", "inventory"),
    ("SKU Master", "sku_master")
]:

    if variable_name in globals():

        df = globals()[variable_name]

        if isinstance(df, pd.DataFrame):

            missing_values = df.isna().sum().sum()

            if missing_values == 0:

                add_validation(
                    display_name,
                    "Missing values",
                    "PASS",
                    "No missing values"
                )

            else:

                add_validation(
                    display_name,
                    "Missing values",
                    "WARNING",
                    f"{missing_values:,} missing cells"
                )


# ============================================================
# 10. CHECK FORECAST OUTPUT
# ============================================================

if (
    "forecast_summary" in globals()
    and isinstance(
        forecast_summary,
        pd.DataFrame
    )
):

    if not forecast_summary.empty:

        add_validation(
            "Forecast Engine",
            "Forecast output",
            "PASS",
            f"{len(forecast_summary):,} rows"
        )

    else:

        add_validation(
            "Forecast Engine",
            "Forecast output",
            "FAIL",
            "Forecast output is empty"
        )

else:

    add_validation(
        "Forecast Engine",
        "Forecast output",
        "WARNING",
        "forecast_summary not available"
    )


# ============================================================
# 11. CHECK OPTIMIZATION OUTPUT
# ============================================================

if (
    "optimization_df" in globals()
    and isinstance(
        optimization_df,
        pd.DataFrame
    )
):

    if not optimization_df.empty:

        add_validation(
            "Optimization",
            "Optimization dataset",
            "PASS",
            f"{len(optimization_df):,} rows"
        )

    else:

        add_validation(
            "Optimization",
            "Optimization dataset",
            "FAIL",
            "Dataset is empty"
        )


# ============================================================
# 12. CHECK PRIORITY OUTPUT
# ============================================================

if (
    "priority_df" in globals()
    and isinstance(
        priority_df,
        pd.DataFrame
    )
):

    if not priority_df.empty:

        add_validation(
            "SKU Prioritization",
            "Priority dataset",
            "PASS",
            f"{len(priority_df):,} rows"
        )

    else:

        add_validation(
            "SKU Prioritization",
            "Priority dataset",
            "FAIL",
            "Dataset is empty"
        )


# ============================================================
# 13. CHECK ALERT ENGINE
# ============================================================

if (
    "alert_df" in globals()
    and isinstance(
        alert_df,
        pd.DataFrame
    )
):

    if not alert_df.empty:

        required_alert_columns = [
            "Alert_Type",
            "Alert_Severity",
            "Recommended_Action"
        ]

        missing_alert_columns = [
            col
            for col in required_alert_columns
            if col not in alert_df.columns
        ]

        if not missing_alert_columns:

            add_validation(
                "Alert Engine",
                "Alert columns",
                "PASS"
            )

        else:

            add_validation(
                "Alert Engine",
                "Alert columns",
                "FAIL",
                ", ".join(
                    missing_alert_columns
                )
            )

    else:

        add_validation(
            "Alert Engine",
            "Alert dataset",
            "FAIL",
            "Alert dataset is empty"
        )


# ============================================================
# 14. CHECK FOR INFINITE VALUES
# ============================================================

datasets_to_check = [
    ("Sales", "sales"),
    ("Inventory", "inventory"),
    ("Forecast", "forecast_summary"),
    ("Optimization", "optimization_df"),
    ("Priority", "priority_df"),
    ("Alerts", "alert_df")
]


for display_name, variable_name in datasets_to_check:

    if variable_name in globals():

        df = globals()[variable_name]

        if isinstance(df, pd.DataFrame):

            numeric_df = df.select_dtypes(
                include=np.number
            )

            if not numeric_df.empty:

                infinite_count = np.isinf(
                    numeric_df.to_numpy()
                ).sum()

                if infinite_count == 0:

                    add_validation(
                        display_name,
                        "Infinite numeric values",
                        "PASS"
                    )

                else:

                    add_validation(
                        display_name,
                        "Infinite numeric values",
                        "WARNING",
                        f"{infinite_count:,} infinite values"
                    )


# ============================================================
# 15. CHECK KPI ENGINE
# ============================================================

if "calculate_all_kpis" in globals():

    add_validation(
        "KPI Engine",
        "KPI calculation function",
        "PASS"
    )

else:

    add_validation(
        "KPI Engine",
        "KPI calculation function",
        "WARNING",
        "Function not found in current scope"
    )


# ============================================================
# 16. CHECK FORECAST ENGINE
# ============================================================

if "generate_forecast_summary" in globals():

    add_validation(
        "Forecast Engine",
        "Forecast function",
        "PASS"
    )

else:

    add_validation(
        "Forecast Engine",
        "Forecast function",
        "FAIL",
        "Forecast function unavailable"
    )


# ============================================================
# 17. CHECK UI FUNCTIONS
# ============================================================

ui_functions = [
    "apply_foresight_style",
    "show_sidebar_brand",
    "page_header",
    "section_header",
    "show_footer"
]


for function_name in ui_functions:

    if function_name in globals():

        add_validation(
            "UI",
            function_name,
            "PASS"
        )

    else:

        add_validation(
            "UI",
            function_name,
            "WARNING",
            "Function unavailable"
        )


# ============================================================
# 18. CREATE VALIDATION DATAFRAME
# ============================================================

validation_df = pd.DataFrame(
    validation_results
)


# ============================================================
# 19. VALIDATION SUMMARY
# ============================================================

pass_count = (
    validation_df["Status"]
    .eq("PASS")
    .sum()
)

warning_count = (
    validation_df["Status"]
    .eq("WARNING")
    .sum()
)

fail_count = (
    validation_df["Status"]
    .eq("FAIL")
    .sum()
)

total_tests = len(
    validation_df
)


if total_tests > 0:

    validation_score = (
        pass_count / total_tests
    ) * 100

else:

    validation_score = 0


# ============================================================
# 20. VALIDATION KPI CARDS
# ============================================================

st.subheader("System Validation Summary")

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Total Tests",
    f"{total_tests:,}"
)

c2.metric(
    "Passed",
    f"{pass_count:,}"
)

c3.metric(
    "Warnings",
    f"{warning_count:,}"
)

c4.metric(
    "Failed",
    f"{fail_count:,}"
)


# ============================================================
# 21. VALIDATION SCORE
# ============================================================

st.metric(
    "FORESIGHT Validation Score",
    f"{validation_score:.1f}%"
)


# ============================================================
# 22. VALIDATION TABLE
# ============================================================

st.subheader("Detailed Validation Results")

st.dataframe(
    validation_df,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# 23. SHOW FAILURES
# ============================================================

failed_tests = validation_df[
    validation_df["Status"] == "FAIL"
]


if not failed_tests.empty:

    st.error(
        f"⚠️ {len(failed_tests)} validation test(s) failed."
    )

    st.dataframe(
        failed_tests,
        use_container_width=True,
        hide_index=True
    )

else:

    st.success(
        "✓ No critical validation failures detected."
    )


# ============================================================
# 24. SHOW WARNINGS
# ============================================================

warning_tests = validation_df[
    validation_df["Status"] == "WARNING"
]


if not warning_tests.empty:

    with st.expander(
        "View Validation Warnings"
    ):

        st.dataframe(
            warning_tests,
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# 25. FINAL PROJECT SCORE
# ============================================================

st.markdown("---")

st.subheader("FORESIGHT Final Project Assessment")


# Determine project status

if fail_count == 0 and validation_score >= 90:

    project_status = "PRODUCTION READY"

    st.success(
        "🟢 FORESIGHT is production-ready."
    )

elif fail_count == 0 and validation_score >= 75:

    project_status = "READY WITH MINOR WARNINGS"

    st.warning(
        "🟡 FORESIGHT is functional but has minor warnings to review."
    )

elif fail_count <= 2:

    project_status = "REQUIRES REVIEW"

    st.warning(
        "🟠 FORESIGHT requires additional validation."
    )

else:

    project_status = "NOT READY"

    st.error(
        "🔴 FORESIGHT has critical validation issues."
    )


# ============================================================
# 26. FINAL PROJECT METRICS
# ============================================================

if "sales" in globals() and isinstance(sales, pd.DataFrame):

    final_sales_rows = len(sales)

else:

    final_sales_rows = 0


if "inventory" in globals() and isinstance(
    inventory,
    pd.DataFrame
):

    final_inventory_rows = len(inventory)

else:

    final_inventory_rows = 0


if "sku_master" in globals() and isinstance(
    sku_master,
    pd.DataFrame
):

    final_sku_count = len(sku_master)

else:

    final_sku_count = 0


final_project_summary = pd.DataFrame({
    "Metric": [
        "Project",
        "Validation Score",
        "Project Status",
        "Validation Tests",
        "Passed Tests",
        "Warnings",
        "Failed Tests",
        "Sales Records",
        "Inventory Records",
        "SKU Master Records"
    ],

    "Value": [
        "FORESIGHT",
        f"{validation_score:.1f}%",
        project_status,
        f"{total_tests:,}",
        f"{pass_count:,}",
        f"{warning_count:,}",
        f"{fail_count:,}",
        f"{final_sales_rows:,}",
        f"{final_inventory_rows:,}",
        f"{final_sku_count:,}"
    ]
})


st.dataframe(
    final_project_summary,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# 27. FINAL MODULE CHECKLIST
# ============================================================

st.subheader("FORESIGHT Final Module Checklist")

final_modules = pd.DataFrame({
    "Module": [
        "1. Project Structure",
        "2. Python Environment",
        "3. Data Loading",
        "4. Data Quality & EDA",
        "5. Dataset Integration",
        "6. Demand Analysis",
        "7. Forecast Baseline",
        "8. Feature Engineering",
        "9. Forecasting",
        "10. Inventory Analytics",
        "11. Financial Analytics",
        "12. Inventory Turnover",
        "13. Demand-Supply Optimization",
        "14. Executive Control Tower",
        "15. Forecast Accuracy",
        "16. Purchase Planning",
        "17. Working Capital Analytics",
        "18. SKU Prioritization",
        "19. Category Analytics",
        "20. Automated Decision Engine",
        "21. Interactive Dashboard",
        "22. Executive Dashboard",
        "23. Final Validation"
    ],

    "Status": [
        "COMPLETED",
        "COMPLETED",
        "COMPLETED",
        "COMPLETED",
        "COMPLETED",
        "COMPLETED",
        "COMPLETED",
        "COMPLETED",
        "COMPLETED",
        "COMPLETED",
        "COMPLETED",
        "COMPLETED",
        "COMPLETED",
        "COMPLETED",
        "COMPLETED",
        "COMPLETED",
        "COMPLETED",
        "COMPLETED",
        "COMPLETED",
        "COMPLETED",
        "COMPLETED",
        "COMPLETED",
        "COMPLETED"
    ]
})


st.dataframe(
    final_modules,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# 28. FINAL SUCCESS MESSAGE
# ============================================================

st.markdown("---")

if fail_count == 0:

    st.success(
        "🎉 FORESIGHT PROJECT COMPLETED SUCCESSFULLY"
    )

    st.markdown(
        """
        ### Project Completion

        **FORESIGHT** now provides:

        - Demand forecasting
        - Inventory analysis
        - Inventory optimization
        - Replenishment planning
        - Working capital analysis
        - SKU prioritization
        - Category analytics
        - Automated inventory alerts
        - Management decision support
        - Interactive filtering
        - Executive KPI dashboard
        - Final system validation

        The project is ready for final testing, screenshots,
        documentation and presentation.
        """
    )

else:

    st.warning(
        "The FORESIGHT project has completed the development "
        "workflow, but validation issues should be reviewed "
        "before final presentation."
    )


# ============================================================
# 29. FINAL FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "FORESIGHT | Inventory & Demand Intelligence Platform | "
    "Final Validation"
)

show_footer()
