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

from src.data_loader import load_sales, load_sku_master


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Sales Analytics",
    page_icon="📊",
    layout="wide"
)
apply_foresight_style()
show_sidebar_brand()

# ============================================================
# PAGE TITLE
# ============================================================

page_header(
    "📈 Sales Analytics",
    "Analyze historical sales performance, trends and product demand."
)

# ============================================================
# LOAD DATA
# ============================================================

sales = load_sales()
sku_master = load_sku_master()


# ============================================================
# VALIDATION
# ============================================================

if sales.empty:
    st.error("Sales data could not be loaded.")
    st.stop()


# ============================================================
# COPY DATA
# ============================================================

sales = sales.copy()
sku_master = sku_master.copy()


# ============================================================
# DATA CLEANING
# ============================================================

sales["date"] = pd.to_datetime(
    sales["date"],
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

else:

    sales["revenue"] = 0


sales = sales.dropna(
    subset=["date", "sku_id"]
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


    product_columns = list(
        dict.fromkeys(product_columns)
    )


    product_information = (
        sku_master[
            product_columns
        ]
        .drop_duplicates("sku_id")
    )


    sales = sales.merge(
        product_information,
        on="sku_id",
        how="left"
    )


# ============================================================
# DATE RANGE
# ============================================================

min_date = sales["date"].min()
max_date = sales["date"].max()


# ============================================================
# ANALYSIS SETTINGS
# ============================================================

st.subheader("⚙️ Sales Analysis Settings")


setting_col1, setting_col2 = st.columns(2)


with setting_col1:

    selected_date_range = st.date_input(
        "Select Date Range",
        value=(
            min_date.date(),
            max_date.date()
        ),
        min_value=min_date.date(),
        max_value=max_date.date()
    )


with setting_col2:

    aggregation_level = st.selectbox(
        "Sales Aggregation",
        options=[
            "Daily",
            "Weekly",
            "Monthly"
        ],
        index=1
    )


# ============================================================
# VALIDATE DATE RANGE
# ============================================================

if isinstance(
    selected_date_range,
    tuple
) and len(selected_date_range) == 2:

    start_date = pd.Timestamp(
        selected_date_range[0]
    )

    end_date = pd.Timestamp(
        selected_date_range[1]
    )

else:

    start_date = min_date
    end_date = max_date


# ============================================================
# FILTER DATE
# ============================================================

filtered_sales = sales[
    (
        sales["date"] >= start_date
    )
    &
    (
        sales["date"] <= end_date
    )
].copy()


# ============================================================
# FILTER CONTROLS
# ============================================================

st.divider()

st.subheader("🔎 Sales Filters")


filter_col1, filter_col2, filter_col3 = (
    st.columns(3)
)


# ============================================================
# CATEGORY FILTER
# ============================================================

with filter_col1:

    if "category" in filtered_sales.columns:

        category_options = sorted(
            filtered_sales["category"]
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
# SKU FILTER
# ============================================================

with filter_col2:

    sku_options = sorted(
        filtered_sales["sku_id"]
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
# TOP SKU COUNT
# ============================================================

with filter_col3:

    top_n = st.slider(
        "Top SKUs to Display",
        min_value=5,
        max_value=30,
        value=10
    )


# ============================================================
# APPLY FILTERS
# ============================================================

if selected_categories:

    filtered_sales = filtered_sales[
        filtered_sales["category"]
        .astype(str)
        .isin(selected_categories)
    ]


if selected_skus:

    filtered_sales = filtered_sales[
        filtered_sales["sku_id"]
        .astype(str)
        .isin(selected_skus)
    ]


# ============================================================
# EMPTY DATA CHECK
# ============================================================

if filtered_sales.empty:

    st.warning(
        "No sales data matches the selected filters."
    )

    st.stop()


st.caption(
    f"Showing sales from "
    f"{start_date.strftime('%d %b %Y')} "
    f"to "
    f"{end_date.strftime('%d %b %Y')}."
)


# ============================================================
# KPI CALCULATIONS
# ============================================================

total_units = (
    filtered_sales["units_sold"].sum()
)


total_revenue = (
    filtered_sales["revenue"].sum()
)


unique_skus = (
    filtered_sales["sku_id"]
    .nunique()
)


average_daily_units = (
    total_units
    / max(
        (
            filtered_sales["date"].max()
            - filtered_sales["date"].min()
        ).days + 1,
        1
    )
)


# ============================================================
# KPI CARDS
# ============================================================

st.divider()

st.subheader("📈 Sales Performance Overview")


kpi1, kpi2, kpi3, kpi4 = st.columns(4)


with kpi1:

    st.metric(
        "Total Units Sold",
        f"{total_units:,.0f}"
    )


with kpi2:

    st.metric(
        "Total Revenue",
        f"₹{total_revenue:,.0f}"
    )


with kpi3:

    st.metric(
        "Active SKUs",
        f"{unique_skus:,}"
    )


with kpi4:

    st.metric(
        "Average Daily Units",
        f"{average_daily_units:,.1f}"
    )


# ============================================================
# SALES TREND DATA
# ============================================================

st.divider()

st.subheader("📈 Sales Trend")


if aggregation_level == "Daily":

    trend_data = (
        filtered_sales
        .groupby("date", as_index=False)
        .agg(
            units_sold=(
                "units_sold",
                "sum"
            ),
            revenue=(
                "revenue",
                "sum"
            )
        )
        .sort_values("date")
    )


elif aggregation_level == "Weekly":

    trend_data = (
        filtered_sales
        .set_index("date")
        .resample("W")
        .agg(
            units_sold=(
                "units_sold",
                "sum"
            ),
            revenue=(
                "revenue",
                "sum"
            )
        )
        .reset_index()
    )


else:

    trend_data = (
        filtered_sales
        .set_index("date")
        .resample("MS")
        .agg(
            units_sold=(
                "units_sold",
                "sum"
            ),
            revenue=(
                "revenue",
                "sum"
            )
        )
        .reset_index()
    )


trend_chart_col1, trend_chart_col2 = (
    st.columns(2)
)


# ============================================================
# UNITS TREND
# ============================================================

with trend_chart_col1:

    fig_units = px.line(
        trend_data,
        x="date",
        y="units_sold",
        markers=True,
        title=f"{aggregation_level} Units Sold",
        labels={
            "date": "Date",
            "units_sold": "Units Sold"
        },
        template="plotly_dark"
    )


    st.plotly_chart(
        fig_units,
        use_container_width=True
    )


# ============================================================
# REVENUE TREND
# ============================================================

with trend_chart_col2:

    fig_revenue = px.line(
        trend_data,
        x="date",
        y="revenue",
        markers=True,
        title=f"{aggregation_level} Revenue",
        labels={
            "date": "Date",
            "revenue": "Revenue (₹)"
        },
        template="plotly_dark"
    )


    st.plotly_chart(
        fig_revenue,
        use_container_width=True
    )


# ============================================================
# TOP SELLING SKUs
# ============================================================

st.divider()

st.subheader("🏆 Top Selling SKUs")


top_skus = (
    filtered_sales
    .groupby("sku_id", as_index=False)
    .agg(
        units_sold=(
            "units_sold",
            "sum"
        ),
        revenue=(
            "revenue",
            "sum"
        )
    )
    .sort_values(
        "units_sold",
        ascending=False
    )
    .head(top_n)
)


fig_top_skus = px.bar(
    top_skus,
    x="sku_id",
    y="units_sold",
    text="units_sold",
    title=f"Top {top_n} SKUs by Units Sold",
    labels={
        "sku_id": "SKU",
        "units_sold": "Units Sold"
    },
    template="plotly_dark"
)


fig_top_skus.update_traces(
    textposition="outside"
)


st.plotly_chart(
    fig_top_skus,
    use_container_width=True
)


# ============================================================
# TOP REVENUE SKUs
# ============================================================

st.subheader("💰 Top Revenue-Generating SKUs")


top_revenue_skus = (
    filtered_sales
    .groupby("sku_id", as_index=False)
    .agg(
        revenue=(
            "revenue",
            "sum"
        )
    )
    .sort_values(
        "revenue",
        ascending=False
    )
    .head(top_n)
)


fig_revenue_skus = px.bar(
    top_revenue_skus,
    x="sku_id",
    y="revenue",
    text="revenue",
    title=f"Top {top_n} SKUs by Revenue",
    labels={
        "sku_id": "SKU",
        "revenue": "Revenue (₹)"
    },
    template="plotly_dark"
)


fig_revenue_skus.update_traces(
    texttemplate="₹%{text:,.0f}",
    textposition="outside"
)


st.plotly_chart(
    fig_revenue_skus,
    use_container_width=True
)


# ============================================================
# CATEGORY PERFORMANCE
# ============================================================

if "category" in filtered_sales.columns:

    st.divider()

    st.subheader("🗂️ Category Performance")


    category_data = (
        filtered_sales
        .groupby(
            "category",
            as_index=False
        )
        .agg(
            units_sold=(
                "units_sold",
                "sum"
            ),
            revenue=(
                "revenue",
                "sum"
            )
        )
        .sort_values(
            "revenue",
            ascending=False
        )
    )


    category_col1, category_col2 = (
        st.columns(2)
    )


    with category_col1:

        fig_category_units = px.bar(
            category_data,
            x="category",
            y="units_sold",
            text="units_sold",
            title="Units Sold by Category",
            labels={
                "category": "Category",
                "units_sold": "Units Sold"
            },
            template="plotly_dark"
        )


        fig_category_units.update_traces(
            textposition="outside"
        )


        st.plotly_chart(
            fig_category_units,
            use_container_width=True
        )


    with category_col2:

        fig_category_revenue = px.bar(
            category_data,
            x="category",
            y="revenue",
            text="revenue",
            title="Revenue by Category",
            labels={
                "category": "Category",
                "revenue": "Revenue (₹)"
            },
            template="plotly_dark"
        )


        fig_category_revenue.update_traces(
            texttemplate="₹%{text:,.0f}",
            textposition="outside"
        )


        st.plotly_chart(
            fig_category_revenue,
            use_container_width=True
        )


# ============================================================
# REVENUE CONTRIBUTION
# ============================================================

st.subheader("🥧 Revenue Contribution")


revenue_distribution = (
    filtered_sales
    .groupby("sku_id", as_index=False)
    .agg(
        revenue=(
            "revenue",
            "sum"
        )
    )
    .sort_values(
        "revenue",
        ascending=False
    )
)


if len(revenue_distribution) > 10:

    top_revenue = revenue_distribution.head(10)

    other_revenue = (
        revenue_distribution.iloc[10:]["revenue"]
        .sum()
    )


    revenue_distribution = pd.concat(
        [
            top_revenue,
            pd.DataFrame(
                {
                    "sku_id": ["Other"],
                    "revenue": [other_revenue]
                }
            )
        ],
        ignore_index=True
    )


fig_pie = px.pie(
    revenue_distribution,
    names="sku_id",
    values="revenue",
    title="Revenue Contribution by SKU",
    hole=0.4,
    template="plotly_dark"
)


st.plotly_chart(
    fig_pie,
    use_container_width=True
)


# ============================================================
# SKU SALES DRILL-DOWN
# ============================================================

st.divider()

st.header("🔍 SKU Sales Drill-Down")


drilldown_skus = sorted(
    filtered_sales["sku_id"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)


selected_sku = st.selectbox(
    "Select SKU",
    options=drilldown_skus,
    key="sales_dashboard_sku"
)


sku_sales = filtered_sales[
    filtered_sales["sku_id"]
    .astype(str)
    == selected_sku
].copy()


# ============================================================
# SKU KPIs
# ============================================================

sku_total_units = (
    sku_sales["units_sold"].sum()
)


sku_total_revenue = (
    sku_sales["revenue"].sum()
)


sku_active_days = (
    sku_sales["date"].nunique()
)


sku_average_daily = (
    sku_total_units
    / max(sku_active_days, 1)
)


sku_kpi1, sku_kpi2, sku_kpi3, sku_kpi4 = (
    st.columns(4)
)


with sku_kpi1:

    st.metric(
        "Units Sold",
        f"{sku_total_units:,.0f}"
    )


with sku_kpi2:

    st.metric(
        "Revenue",
        f"₹{sku_total_revenue:,.0f}"
    )


with sku_kpi3:

    st.metric(
        "Active Sales Days",
        f"{sku_active_days:,}"
    )


with sku_kpi4:

    st.metric(
        "Average Daily Units",
        f"{sku_average_daily:,.1f}"
    )


# ============================================================
# SKU DAILY SALES
# ============================================================

sku_daily = (
    sku_sales
    .groupby(
        "date",
        as_index=False
    )
    .agg(
        units_sold=(
            "units_sold",
            "sum"
        ),
        revenue=(
            "revenue",
            "sum"
        )
    )
    .sort_values("date")
)


sku_daily["rolling_7_day"] = (
    sku_daily["units_sold"]
    .rolling(
        7,
        min_periods=1
    )
    .mean()
)


# ============================================================
# SKU SALES CHART
# ============================================================

st.subheader(
    f"📈 Sales Trend — {selected_sku}"
)


fig_sku_sales = go.Figure()


fig_sku_sales.add_trace(
    go.Scatter(
        x=sku_daily["date"],
        y=sku_daily["units_sold"],
        mode="lines",
        name="Daily Units"
    )
)


fig_sku_sales.add_trace(
    go.Scatter(
        x=sku_daily["date"],
        y=sku_daily["rolling_7_day"],
        mode="lines",
        name="7-Day Moving Average"
    )
)


fig_sku_sales.update_layout(
    title=f"Daily Sales Trend — {selected_sku}",
    xaxis_title="Date",
    yaxis_title="Units Sold",
    template="plotly_dark"
)


st.plotly_chart(
    fig_sku_sales,
    use_container_width=True
)


# ============================================================
# SKU REVENUE TREND
# ============================================================

st.subheader(
    f"💰 Revenue Trend — {selected_sku}"
)


fig_sku_revenue = px.line(
    sku_daily,
    x="date",
    y="revenue",
    markers=True,
    title=f"Daily Revenue — {selected_sku}",
    labels={
        "date": "Date",
        "revenue": "Revenue (₹)"
    },
    template="plotly_dark"
)


st.plotly_chart(
    fig_sku_revenue,
    use_container_width=True
)


# ============================================================
# WEEKLY SKU PERFORMANCE
# ============================================================

st.subheader(
    f"📅 Weekly Performance — {selected_sku}"
)


sku_weekly = (
    sku_sales
    .set_index("date")
    .resample("W")
    .agg(
        units_sold=(
            "units_sold",
            "sum"
        ),
        revenue=(
            "revenue",
            "sum"
        )
    )
    .reset_index()
)


fig_sku_weekly = px.bar(
    sku_weekly,
    x="date",
    y="units_sold",
    title=f"Weekly Units Sold — {selected_sku}",
    labels={
        "date": "Week",
        "units_sold": "Units Sold"
    },
    template="plotly_dark"
)


st.plotly_chart(
    fig_sku_weekly,
    use_container_width=True
)


# ============================================================
# SALES SUMMARY TABLE
# ============================================================

st.subheader("📋 Sales Summary")


sales_summary = pd.DataFrame(
    {
        "Metric": [
            "SKU",
            "Total Units Sold",
            "Total Revenue",
            "Active Sales Days",
            "Average Daily Units",
            "Average Revenue per Day"
        ],
        "Value": [
            selected_sku,
            f"{sku_total_units:,.0f}",
            f"₹{sku_total_revenue:,.0f}",
            f"{sku_active_days:,}",
            f"{sku_average_daily:,.2f}",
            (
                f"₹{sku_total_revenue / max(sku_active_days, 1):,.2f}"
            )
        ]
    }
)


st.dataframe(
    sales_summary,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# SALES DATA TABLE
# ============================================================

with st.expander(
    "📋 View Raw Sales Records for Selected SKU"
):

    st.dataframe(
        sku_sales.sort_values(
            "date",
            ascending=False
        ),
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# BUSINESS INSIGHTS
# ============================================================

st.divider()

st.header("🧠 Sales Business Insights")


# ------------------------------------------------------------
# BEST PERFORMING SKU
# ------------------------------------------------------------

best_sku_row = (
    filtered_sales
    .groupby("sku_id")["units_sold"]
    .sum()
    .sort_values(
        ascending=False
    )
)


if not best_sku_row.empty:

    best_sku = best_sku_row.index[0]

    best_units = best_sku_row.iloc[0]


    st.success(
        f"🏆 **Top-selling SKU:** "
        f"{best_sku} with "
        f"{best_units:,.0f} units sold "
        f"during the selected period."
    )


# ------------------------------------------------------------
# HIGHEST REVENUE SKU
# ------------------------------------------------------------

best_revenue_row = (
    filtered_sales
    .groupby("sku_id")["revenue"]
    .sum()
    .sort_values(
        ascending=False
    )
)


if not best_revenue_row.empty:

    best_revenue_sku = (
        best_revenue_row.index[0]
    )

    best_revenue = (
        best_revenue_row.iloc[0]
    )


    st.info(
        f"💰 **Highest revenue-generating SKU:** "
        f"{best_revenue_sku} generated "
        f"₹{best_revenue:,.0f}."
    )


# ------------------------------------------------------------
# SELECTED SKU INSIGHT
# ------------------------------------------------------------

if sku_total_units > 0:

    st.info(
        f"📌 **Selected SKU {selected_sku}** generated "
        f"{sku_total_units:,.0f} units of sales and "
        f"₹{sku_total_revenue:,.0f} revenue."
    )


# ============================================================
# METHODOLOGY
# ============================================================

st.divider()

with st.expander(
    "📘 Sales Analytics Methodology"
):

    st.markdown(
        """
### Total Units Sold

Total units represent the sum of `units_sold`
for the selected date range and filters.

### Total Revenue

Revenue is calculated from the `revenue` field
in the sales dataset.

### Average Daily Units

Average daily sales are calculated as:

**Total Units Sold ÷ Number of Active Days**

### Sales Trends

Sales can be aggregated at:

- Daily
- Weekly
- Monthly

### Top-Selling SKUs

SKUs are ranked according to total units sold.

### Revenue Leaders

SKUs are ranked according to total revenue generated.

### Category Performance

Categories are compared using both:

- Units sold
- Revenue

### Moving Average

The 7-day moving average is used to smooth short-term
sales fluctuations and make demand trends easier to interpret.

### Business Use

Sales analytics helps management identify:

- High-performing products
- Revenue-generating products
- Demand trends
- Weak-selling products
- Category performance
- SKU-level sales patterns
"""
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "FORESIGHT • AI-Driven Demand Forecasting, "
    "Sales Analytics & Business Intelligence"
)
# ============================================================
# FOOTER
# ============================================================

show_footer()