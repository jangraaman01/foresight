import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

from src.data_loader import (
    load_sales,
    load_sku_master
)

from src.forecast_engine import (
    generate_all_forecasts,
    generate_forecast_summary
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
    page_title="FORESIGHT | Demand Forecast",
    page_icon="📈",
    layout="wide"
)

apply_foresight_style()
show_sidebar_brand()


# =========================================================
# PAGE HEADER
# =========================================================

page_header(
    "📈 Demand Forecast",
    "AI-powered weekly demand forecasting with trend analysis and forecast uncertainty."
)


# =========================================================
# LOAD DATA
# =========================================================

sales = load_sales()
sku_master = load_sku_master()


if sales is None or sales.empty:

    st.error(
        "Sales data could not be loaded."
    )

    st.stop()


# =========================================================
# CLEAN SALES DATA
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
# SIDEBAR SETTINGS
# =========================================================

st.sidebar.markdown(
    "### ⚙️ Forecast Settings"
)

forecast_horizon = st.sidebar.slider(
    "Forecast Horizon (Weeks)",
    min_value=1,
    max_value=16,
    value=8,
    step=1
)

historical_weeks = st.sidebar.slider(
    "Historical Demand Window (Weeks)",
    min_value=4,
    max_value=52,
    value=12,
    step=1
)

top_n = st.sidebar.slider(
    "Top Products",
    min_value=5,
    max_value=30,
    value=15,
    step=5
)


# =========================================================
# GENERATE FORECAST
# =========================================================

with st.spinner(
    "Generating AI demand forecasts..."
):

    forecasts = generate_all_forecasts(
        sales,
        horizon=forecast_horizon
    )

    summary = generate_forecast_summary(
        sales,
        horizon=forecast_horizon
    )


if forecasts.empty:

    st.warning(
        "No forecast could be generated from the available sales data."
    )

    st.stop()


# =========================================================
# PRODUCT INFORMATION
# =========================================================

if sku_master is not None and not sku_master.empty:

    product_columns = [
        col for col in [
            "sku_id",
            "product_name",
            "category",
            "subcategory"
        ]
        if col in sku_master.columns
    ]

    product_info = sku_master[
        product_columns
    ].drop_duplicates(
        subset=["sku_id"]
    )

    summary = summary.merge(
        product_info,
        on="sku_id",
        how="left"
    )

    forecasts = forecasts.merge(
        product_info,
        on="sku_id",
        how="left"
    )

else:

    summary["product_name"] = (
        summary["sku_id"]
        .astype(str)
    )

    summary["category"] = "Unknown"

    summary["subcategory"] = "Unknown"

    forecasts["product_name"] = (
        forecasts["sku_id"]
        .astype(str)
    )

    forecasts["category"] = "Unknown"


# =========================================================
# HISTORICAL DEMAND
# =========================================================

latest_date = sales["date"].max()

historical_start = (
    latest_date
    - pd.Timedelta(
        weeks=historical_weeks
    )
)

historical_sales = sales[
    sales["date"] >= historical_start
].copy()


historical_weekly = (
    historical_sales
    .set_index("date")
    .groupby("sku_id")["units_sold"]
    .resample("W")
    .sum()
    .reset_index()
)


historical_avg = (
    historical_weekly
    .groupby("sku_id", as_index=False)
    .agg(
        historical_avg_weekly_demand=(
            "units_sold",
            "mean"
        )
    )
)


summary = summary.merge(
    historical_avg,
    on="sku_id",
    how="left"
)

summary["historical_avg_weekly_demand"] = (
    summary["historical_avg_weekly_demand"]
    .fillna(0)
)


# =========================================================
# FORECAST CHANGE
# =========================================================

summary["forecast_change_pct"] = np.where(
    summary["historical_avg_weekly_demand"] > 0,

    (
        (
            summary["avg_weekly_demand"]
            - summary["historical_avg_weekly_demand"]
        )
        /
        summary["historical_avg_weekly_demand"]
    ) * 100,

    0
)


# =========================================================
# DEMAND TREND
# =========================================================

def classify_trend(change):

    if change >= 10:
        return "Increasing"

    if change <= -10:
        return "Declining"

    return "Stable"


# Prefer engine-generated trend
if "demand_trend" not in summary.columns:

    summary["demand_trend"] = (
        summary["forecast_change_pct"]
        .apply(classify_trend)
    )


# =========================================================
# FILTERS
# =========================================================

section_header(
    "🔎 Forecast Filters",
    "Filter the forecast portfolio by category, demand trend and SKU."
)


filter_col1, filter_col2, filter_col3 = st.columns(
    [1, 1, 2]
)


with filter_col1:

    categories = sorted(
        summary["category"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    selected_categories = st.multiselect(
        "Category",
        categories,
        default=categories
    )


with filter_col2:

    trends = [
        "Increasing",
        "Stable",
        "Declining"
    ]

    selected_trends = st.multiselect(
        "Demand Trend",
        trends,
        default=trends
    )


with filter_col3:

    sku_options = (
        summary["sku_id"]
        .dropna()
        .astype(str)
        .tolist()
    )

    selected_skus = st.multiselect(
        "SKU",
        sku_options
    )


# =========================================================
# APPLY FILTERS
# =========================================================

filtered_summary = summary.copy()

if selected_categories:

    filtered_summary = filtered_summary[
        filtered_summary["category"]
        .astype(str)
        .isin(selected_categories)
    ]

if selected_trends:

    filtered_summary = filtered_summary[
        filtered_summary["demand_trend"]
        .isin(selected_trends)
    ]

if selected_skus:

    filtered_summary = filtered_summary[
        filtered_summary["sku_id"]
        .astype(str)
        .isin(selected_skus)
    ]


filtered_forecasts = forecasts[
    forecasts["sku_id"].isin(
        filtered_summary["sku_id"]
    )
].copy()


if filtered_summary.empty:

    st.warning(
        "No products match the selected filters."
    )

    st.stop()


# =========================================================
# EXECUTIVE FORECAST KPIs
# =========================================================

section_header(
    "📊 Forecast Overview",
    "Portfolio-level demand outlook generated by the FORESIGHT forecasting engine."
)


kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)


with kpi1:

    st.metric(
        "SKUs Forecasted",
        f"{len(filtered_summary):,}"
    )


with kpi2:

    st.metric(
        "Forecast Demand",
        f"{filtered_summary['total_forecast_demand'].sum():,.0f}"
    )


with kpi3:

    st.metric(
        "Avg Weekly Demand",
        f"{filtered_summary['avg_weekly_demand'].sum():,.0f}"
    )


with kpi4:

    increasing = (
        filtered_summary["demand_trend"]
        == "Increasing"
    ).sum()

    st.metric(
        "Increasing Demand",
        f"{increasing:,}"
    )


with kpi5:

    high_confidence = (
        filtered_summary["forecast_confidence"]
        == "High"
    ).sum()

    st.metric(
        "High Confidence",
        f"{high_confidence:,}"
    )


# =========================================================
# TREND DISTRIBUTION
# =========================================================

section_header(
    "📈 Demand Trend Distribution",
    "Products are classified according to their forecasted demand direction."
)


trend_counts = (
    filtered_summary["demand_trend"]
    .value_counts()
    .reindex(
        [
            "Increasing",
            "Stable",
            "Declining"
        ],
        fill_value=0
    )
    .reset_index()
)

trend_counts.columns = [
    "Demand Trend",
    "SKU Count"
]


fig_trend = px.bar(
    trend_counts,
    x="Demand Trend",
    y="SKU Count",
    text="SKU Count",
    title="Demand Trend by SKU"
)

fig_trend.update_layout(
    height=380,
    showlegend=False
)

st.plotly_chart(
    fig_trend,
    use_container_width=True
)


# =========================================================
# HISTORICAL VS FORECAST
# =========================================================

section_header(
    "📊 Historical vs Forecast Demand",
    "Comparison of recent weekly demand with expected future demand."
)


comparison = filtered_summary.copy()

comparison["Demand Type"] = "Forecast"

historical_comparison = comparison[
    [
        "sku_id",
        "product_name",
        "historical_avg_weekly_demand"
    ]
].copy()

historical_comparison["Demand Type"] = (
    "Historical"
)

historical_comparison = (
    historical_comparison
    .rename(
        columns={
            "historical_avg_weekly_demand":
            "Demand"
        }
    )
)

forecast_comparison = comparison[
    [
        "sku_id",
        "product_name",
        "avg_weekly_demand"
    ]
].copy()

forecast_comparison["Demand Type"] = (
    "Forecast"
)

forecast_comparison = (
    forecast_comparison
    .rename(
        columns={
            "avg_weekly_demand":
            "Demand"
        }
    )
)

comparison_chart = pd.concat(
    [
        historical_comparison,
        forecast_comparison
    ],
    ignore_index=True
)

top_comparison_skus = (
    filtered_summary
    .nlargest(
        top_n,
        "total_forecast_demand"
    )["sku_id"]
)

comparison_chart = comparison_chart[
    comparison_chart["sku_id"].isin(
        top_comparison_skus
    )
]


fig_comparison = px.bar(
    comparison_chart,
    x="product_name",
    y="Demand",
    color="Demand Type",
    barmode="group",
    title=f"Top {top_n} SKUs — Historical vs Forecast"
)

fig_comparison.update_layout(
    height=500,
    xaxis_title="Product",
    yaxis_title="Weekly Units"
)

st.plotly_chart(
    fig_comparison,
    use_container_width=True
)


# =========================================================
# TOP FORECAST DEMAND
# =========================================================

section_header(
    "🔥 Highest Forecast Demand",
    "Products expected to generate the largest volume of demand."
)


top_demand = (
    filtered_summary
    .nlargest(
        top_n,
        "total_forecast_demand"
    )
    .copy()
)

top_demand["Display Name"] = np.where(
    top_demand["product_name"].notna(),
    top_demand["product_name"],
    top_demand["sku_id"].astype(str)
)


fig_top = px.bar(
    top_demand,
    x="total_forecast_demand",
    y="Display Name",
    orientation="h",
    text="total_forecast_demand",
    title="Top Products by Forecast Demand"
)

fig_top.update_layout(
    height=max(
        450,
        len(top_demand) * 30
    ),
    yaxis={
        "categoryorder": "total ascending"
    }
)

st.plotly_chart(
    fig_top,
    use_container_width=True
)


# =========================================================
# FASTEST INCREASING DEMAND
# =========================================================

section_header(
    "🚀 Fastest Increasing Demand",
    "Products with the strongest expected demand growth."
)


increasing_products = (
    filtered_summary
    .sort_values(
        "forecast_change_pct",
        ascending=False
    )
    .head(top_n)
    .copy()
)

increasing_products["Display Name"] = np.where(
    increasing_products["product_name"].notna(),
    increasing_products["product_name"],
    increasing_products["sku_id"].astype(str)
)


fig_increasing = px.bar(
    increasing_products,
    x="forecast_change_pct",
    y="Display Name",
    orientation="h",
    text="forecast_change_pct",
    title="Forecast Demand Growth (%)"
)

fig_increasing.update_traces(
    texttemplate="%{text:.1f}%",
    textposition="outside"
)

fig_increasing.update_layout(
    height=max(
        450,
        len(increasing_products) * 30
    )
)

st.plotly_chart(
    fig_increasing,
    use_container_width=True
)


# =========================================================
# WEEK-BY-WEEK FORECAST
# =========================================================

section_header(
    "📅 Week-by-Week Forecast",
    "Detailed future demand trajectory for an individual SKU."
)


sku_lookup = filtered_summary[
    [
        "sku_id",
        "product_name"
    ]
].copy()

sku_lookup["label"] = (
    sku_lookup["sku_id"].astype(str)
    + " — "
    + sku_lookup["product_name"]
    .fillna("")
    .astype(str)
)

sku_lookup = sku_lookup.sort_values(
    "label"
)


selected_forecast_sku = st.selectbox(
    "Select SKU for detailed forecast",
    sku_lookup["sku_id"].tolist(),
    format_func=lambda x: sku_lookup.loc[
        sku_lookup["sku_id"] == x,
        "label"
    ].iloc[0]
)


selected_forecast = filtered_forecasts[
    filtered_forecasts["sku_id"]
    == selected_forecast_sku
].copy()


selected_summary = filtered_summary[
    filtered_summary["sku_id"]
    == selected_forecast_sku
].iloc[0]


# =========================================================
# FORECAST DETAIL METRICS
# =========================================================

detail1, detail2, detail3, detail4 = st.columns(4)


with detail1:

    st.metric(
        "Avg Forecast / Week",
        f"{selected_summary['avg_weekly_demand']:,.0f}"
    )


with detail2:

    st.metric(
        "Total Forecast",
        f"{selected_summary['total_forecast_demand']:,.0f}"
    )


with detail3:

    st.metric(
        "Forecast Range",
        f"{selected_summary['min_forecast_demand']:,.0f}"
        + " – "
        + f"{selected_summary['max_forecast_demand']:,.0f}"
    )


with detail4:

    st.metric(
        "Confidence",
        selected_summary["forecast_confidence"]
    )


# =========================================================
# FORECAST CHART WITH CONFIDENCE BAND
# =========================================================

fig_forecast = go.Figure()


fig_forecast.add_trace(
    go.Scatter(
        x=selected_forecast["date"],
        y=selected_forecast["upper_bound"],
        mode="lines",
        line=dict(
            width=0
        ),
        name="Upper Bound"
    )
)


fig_forecast.add_trace(
    go.Scatter(
        x=selected_forecast["date"],
        y=selected_forecast["lower_bound"],
        mode="lines",
        line=dict(
            width=0
        ),
        fill="tonexty",
        name="Confidence Range"
    )
)


fig_forecast.add_trace(
    go.Scatter(
        x=selected_forecast["date"],
        y=selected_forecast["predicted_demand"],
        mode="lines+markers",
        name="Forecast Demand"
    )
)


# Historical weekly demand for selected SKU
selected_historical = historical_weekly[
    historical_weekly["sku_id"]
    == selected_forecast_sku
].copy()

selected_historical = selected_historical[
    selected_historical["date"]
    >= historical_start
]


fig_forecast.add_trace(
    go.Scatter(
        x=selected_historical["date"],
        y=selected_historical["units_sold"],
        mode="lines+markers",
        name="Historical Demand"
    )
)


fig_forecast.update_layout(
    title=(
        f"Weekly Demand Forecast — "
        f"{selected_forecast_sku}"
    ),
    xaxis_title="Week",
    yaxis_title="Units",
    height=520,
    hovermode="x unified"
)


st.plotly_chart(
    fig_forecast,
    use_container_width=True
)


# =========================================================
# WEEKLY FORECAST TABLE
# =========================================================

section_header(
    "📋 Forecast Detail",
    "Expected demand and uncertainty range for each forecast week."
)


display_forecast = selected_forecast[
    [
        "date",
        "predicted_demand",
        "lower_bound",
        "upper_bound"
    ]
].copy()

display_forecast.columns = [
    "Forecast Week",
    "Predicted Demand",
    "Lower Bound",
    "Upper Bound"
]

display_forecast["Forecast Week"] = (
    pd.to_datetime(
        display_forecast["Forecast Week"]
    ).dt.strftime(
        "%d %b %Y"
    )
)

for column in [
    "Predicted Demand",
    "Lower Bound",
    "Upper Bound"
]:

    display_forecast[column] = (
        display_forecast[column]
        .round(0)
        .astype(int)
    )


st.dataframe(
    display_forecast,
    use_container_width=True,
    hide_index=True
)


# =========================================================
# FORECAST CONFIDENCE
# =========================================================

section_header(
    "🎯 Forecast Confidence",
    "Confidence is estimated from historical demand variability."
)


confidence_counts = (
    filtered_summary["forecast_confidence"]
    .value_counts()
    .reindex(
        [
            "High",
            "Medium",
            "Low"
        ],
        fill_value=0
    )
    .reset_index()
)

confidence_counts.columns = [
    "Confidence",
    "SKU Count"
]


fig_confidence = px.bar(
    confidence_counts,
    x="Confidence",
    y="SKU Count",
    text="SKU Count",
    title="Forecast Confidence Distribution"
)

fig_confidence.update_layout(
    height=380,
    showlegend=False
)

st.plotly_chart(
    fig_confidence,
    use_container_width=True
)


# =========================================================
# MANAGEMENT INSIGHTS
# =========================================================

section_header(
    "💡 Management Insights",
    "Automatically generated observations from the demand forecast."
)


total_skus = len(filtered_summary)

increasing_count = (
    filtered_summary["demand_trend"]
    == "Increasing"
).sum()

declining_count = (
    filtered_summary["demand_trend"]
    == "Declining"
).sum()

high_confidence_count = (
    filtered_summary["forecast_confidence"]
    == "High"
).sum()


if increasing_count > 0:

    st.info(
        f"🚀 **{increasing_count} SKUs** show increasing "
        "forecast demand. These products should be monitored "
        "for additional replenishment requirements."
    )


if declining_count > 0:

    st.warning(
        f"📉 **{declining_count} SKUs** show declining "
        "demand. Review purchasing plans and consider "
        "inventory reduction where appropriate."
    )


if high_confidence_count > 0:

    confidence_pct = (
        high_confidence_count
        / max(total_skus, 1)
    ) * 100

    st.success(
        f"🎯 **{confidence_pct:.1f}%** of filtered SKUs "
        "have high forecast confidence based on historical "
        "demand stability."
    )


# =========================================================
# COMPLETE FORECAST TABLE
# =========================================================

section_header(
    "📑 Complete Forecast Summary",
    "SKU-level forecast portfolio for management review."
)


complete_columns = [
    col for col in [
        "sku_id",
        "product_name",
        "category",
        "historical_avg_weekly_demand",
        "avg_weekly_demand",
        "total_forecast_demand",
        "min_forecast_demand",
        "max_forecast_demand",
        "forecast_change_pct",
        "demand_trend",
        "forecast_confidence"
    ]
    if col in filtered_summary.columns
]


complete_table = (
    filtered_summary[
        complete_columns
    ]
    .sort_values(
        "total_forecast_demand",
        ascending=False
    )
    .copy()
)


if "forecast_change_pct" in complete_table.columns:

    complete_table[
        "forecast_change_pct"
    ] = (
        complete_table[
            "forecast_change_pct"
        ].round(1)
    )


st.dataframe(
    complete_table.head(100),
    use_container_width=True,
    hide_index=True
)


# =========================================================
# METHODOLOGY
# =========================================================

with st.expander(
    "📘 Forecast Methodology"
):

    st.markdown(
        """
        ### FORESIGHT Forecasting Method

        **1. Data Preparation**

        Historical SKU-level sales are converted into weekly
        demand observations.

        **2. Machine Learning**

        The existing FORESIGHT ML forecasting engine is used
        to generate recursive future weekly predictions.

        **3. Fallback Forecast**

        If an ML model cannot be trained for a SKU, the system
        uses recent average weekly demand as a fallback.

        **4. Confidence Range**

        Forecast uncertainty is estimated from historical
        demand variability.

        **5. Demand Trend**

        Products are classified as:

        - 🚀 Increasing
        - ➡️ Stable
        - 📉 Declining

        **6. Forecast Confidence**

        Historical demand variability determines:

        - High confidence
        - Medium confidence
        - Low confidence

        The forecast should be treated as a decision-support
        signal rather than a guaranteed future outcome.
        """
    )


# =========================================================
# FOOTER
# =========================================================

show_footer()