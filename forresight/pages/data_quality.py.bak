import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

from src.data_loader import (
    load_sales,
    load_inventory,
    load_sku_master,
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
    page_title="Data Quality | FORESIGHT",
    page_icon="🧹",
    layout="wide",
)

apply_foresight_style()
show_sidebar_brand()

page_header(
    "🧹 Data Quality",
    "Validate the data foundation used by FORESIGHT forecasting, inventory and risk models.",
)


# ============================================================
# LOAD DATA
# ============================================================
@st.cache_data
def load_quality_data():

    sales = load_sales()
    inventory = load_inventory()
    sku_master = load_sku_master()

    return sales, inventory, sku_master


sales, inventory, sku_master = load_quality_data()


# ============================================================
# VALIDATION
# ============================================================
if sales.empty:
    st.error("Sales dataset is empty.")
    st.stop()

if inventory.empty:
    st.error("Inventory dataset is empty.")
    st.stop()

if sku_master.empty:
    st.error("SKU master dataset is empty.")
    st.stop()


# ============================================================
# COPY DATA
# ============================================================
sales = sales.copy()
inventory = inventory.copy()
sku_master = sku_master.copy()


# ============================================================
# BASIC TYPE CONVERSION
# ============================================================
if "date" in sales.columns:

    sales["date"] = pd.to_datetime(
        sales["date"],
        errors="coerce",
    )

if "date" in inventory.columns:

    inventory["date"] = pd.to_datetime(
        inventory["date"],
        errors="coerce",
    )


# ============================================================
# DATASET CONFIGURATION
# ============================================================
datasets = {
    "Sales": sales,
    "Inventory": inventory,
    "SKU Master": sku_master,
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================
def safe_percentage(numerator, denominator):

    if denominator == 0:
        return 0.0

    return (
        numerator / denominator
    ) * 100


def calculate_dataset_quality(df, dataset_name):

    total_cells = (
        df.shape[0] * df.shape[1]
    )

    missing_cells = int(
        df.isna().sum().sum()
    )

    duplicate_rows = int(
        df.duplicated().sum()
    )

    rows = len(df)

    columns = len(df.columns)

    missing_percent = safe_percentage(
        missing_cells,
        total_cells,
    )

    duplicate_percent = safe_percentage(
        duplicate_rows,
        rows,
    )

    # --------------------------------------------------------
    # Component scores
    # --------------------------------------------------------
    completeness_score = max(
        0,
        100 - missing_percent,
    )

    uniqueness_score = max(
        0,
        100 - duplicate_percent,
    )

    # Data validity starts at 100 and is reduced by
    # dataset-specific anomalies below.
    validity_score = 100.0

    # --------------------------------------------------------
    # Date validation
    # --------------------------------------------------------
    invalid_dates = 0

    if "date" in df.columns:

        invalid_dates = int(
            df["date"].isna().sum()
        )

        invalid_date_percent = safe_percentage(
            invalid_dates,
            rows,
        )

        validity_score -= min(
            invalid_date_percent,
            30,
        )

    # --------------------------------------------------------
    # Overall score
    # --------------------------------------------------------
    overall_score = (
        completeness_score * 0.40
        + uniqueness_score * 0.20
        + validity_score * 0.40
    )

    overall_score = round(
        max(
            0,
            min(
                overall_score,
                100,
            ),
        ),
        2,
    )

    if overall_score >= 95:
        status = "Excellent"

    elif overall_score >= 85:
        status = "Good"

    elif overall_score >= 70:
        status = "Needs Attention"

    else:
        status = "Critical"

    return {
        "Dataset": dataset_name,
        "Rows": rows,
        "Columns": columns,
        "Missing Cells": missing_cells,
        "Missing %": round(
            missing_percent,
            2,
        ),
        "Duplicate Rows": duplicate_rows,
        "Duplicate %": round(
            duplicate_percent,
            2,
        ),
        "Invalid Dates": invalid_dates,
        "Quality Score": overall_score,
        "Status": status,
    }


# ============================================================
# DATASET QUALITY SUMMARY
# ============================================================
quality_results = []

for dataset_name, df in datasets.items():

    quality_results.append(
        calculate_dataset_quality(
            df,
            dataset_name,
        )
    )


quality_df = pd.DataFrame(
    quality_results
)


# ============================================================
# SALES QUALITY CHECKS
# ============================================================
sales_checks = []


# ------------------------------------------------------------
# Missing SKU
# ------------------------------------------------------------
missing_sales_sku = int(
    sales["sku_id"].isna().sum()
) if "sku_id" in sales.columns else len(sales)

sales_checks.append(
    {
        "Check": "Missing SKU IDs",
        "Issue Count": missing_sales_sku,
        "Status": (
            "Pass"
            if missing_sales_sku == 0
            else "Fail"
        ),
    }
)


# ------------------------------------------------------------
# Missing dates
# ------------------------------------------------------------
missing_sales_dates = int(
    sales["date"].isna().sum()
)

sales_checks.append(
    {
        "Check": "Invalid / Missing Dates",
        "Issue Count": missing_sales_dates,
        "Status": (
            "Pass"
            if missing_sales_dates == 0
            else "Fail"
        ),
    }
)


# ------------------------------------------------------------
# Negative units
# ------------------------------------------------------------
negative_sales_units = int(
    (
        pd.to_numeric(
            sales["units_sold"],
            errors="coerce",
        )
        < 0
    ).sum()
) if "units_sold" in sales.columns else 0


sales_checks.append(
    {
        "Check": "Negative Units Sold",
        "Issue Count": negative_sales_units,
        "Status": (
            "Pass"
            if negative_sales_units == 0
            else "Fail"
        ),
    }
)


# ------------------------------------------------------------
# Zero sales
# ------------------------------------------------------------
zero_sales_units = int(
    (
        pd.to_numeric(
            sales["units_sold"],
            errors="coerce",
        )
        == 0
    ).sum()
) if "units_sold" in sales.columns else 0


sales_checks.append(
    {
        "Check": "Zero-Unit Sales Records",
        "Issue Count": zero_sales_units,
        "Status": "Info",
    }
)


# ------------------------------------------------------------
# Negative revenue
# ------------------------------------------------------------
if "revenue" in sales.columns:

    negative_revenue = int(
        (
            pd.to_numeric(
                sales["revenue"],
                errors="coerce",
            )
            < 0
        ).sum()
    )

else:

    negative_revenue = 0


sales_checks.append(
    {
        "Check": "Negative Revenue",
        "Issue Count": negative_revenue,
        "Status": (
            "Pass"
            if negative_revenue == 0
            else "Fail"
        ),
    }
)


sales_checks_df = pd.DataFrame(
    sales_checks
)


# ============================================================
# INVENTORY QUALITY CHECKS
# ============================================================
inventory_checks = []


# ------------------------------------------------------------
# Missing SKU
# ------------------------------------------------------------
missing_inventory_sku = int(
    inventory["sku_id"].isna().sum()
) if "sku_id" in inventory.columns else len(inventory)


inventory_checks.append(
    {
        "Check": "Missing SKU IDs",
        "Issue Count": missing_inventory_sku,
        "Status": (
            "Pass"
            if missing_inventory_sku == 0
            else "Fail"
        ),
    }
)


# ------------------------------------------------------------
# Missing dates
# ------------------------------------------------------------
missing_inventory_dates = int(
    inventory["date"].isna().sum()
)

inventory_checks.append(
    {
        "Check": "Invalid / Missing Dates",
        "Issue Count": missing_inventory_dates,
        "Status": (
            "Pass"
            if missing_inventory_dates == 0
            else "Fail"
        ),
    }
)


# ------------------------------------------------------------
# Negative inventory
# ------------------------------------------------------------
if "on_hand_units" in inventory.columns:

    negative_on_hand = int(
        (
            pd.to_numeric(
                inventory["on_hand_units"],
                errors="coerce",
            )
            < 0
        ).sum()
    )

else:

    negative_on_hand = 0


inventory_checks.append(
    {
        "Check": "Negative On-Hand Inventory",
        "Issue Count": negative_on_hand,
        "Status": (
            "Pass"
            if negative_on_hand == 0
            else "Fail"
        ),
    }
)


# ------------------------------------------------------------
# Negative on-order
# ------------------------------------------------------------
if "on_order_units" in inventory.columns:

    negative_on_order = int(
        (
            pd.to_numeric(
                inventory["on_order_units"],
                errors="coerce",
            )
            < 0
        ).sum()
    )

else:

    negative_on_order = 0


inventory_checks.append(
    {
        "Check": "Negative On-Order Units",
        "Issue Count": negative_on_order,
        "Status": (
            "Pass"
            if negative_on_order == 0
            else "Fail"
        ),
    }
)


# ------------------------------------------------------------
# Invalid lead time
# ------------------------------------------------------------
if "lead_time_days" in inventory.columns:

    invalid_lead_time = int(
        (
            pd.to_numeric(
                inventory["lead_time_days"],
                errors="coerce",
            )
            < 0
        ).sum()
    )

else:

    invalid_lead_time = 0


inventory_checks.append(
    {
        "Check": "Negative Lead Time",
        "Issue Count": invalid_lead_time,
        "Status": (
            "Pass"
            if invalid_lead_time == 0
            else "Fail"
        ),
    }
)


inventory_checks_df = pd.DataFrame(
    inventory_checks
)


# ============================================================
# SKU MASTER QUALITY CHECKS
# ============================================================
sku_checks = []


# ------------------------------------------------------------
# Duplicate SKUs
# ------------------------------------------------------------
if "sku_id" in sku_master.columns:

    duplicate_skus = int(
        sku_master["sku_id"]
        .duplicated()
        .sum()
    )

else:

    duplicate_skus = len(sku_master)


sku_checks.append(
    {
        "Check": "Duplicate SKU IDs",
        "Issue Count": duplicate_skus,
        "Status": (
            "Pass"
            if duplicate_skus == 0
            else "Fail"
        ),
    }
)


# ------------------------------------------------------------
# Missing product names
# ------------------------------------------------------------
if "product_name" in sku_master.columns:

    missing_product_names = int(
        sku_master[
            "product_name"
        ].isna().sum()
    )

else:

    missing_product_names = len(
        sku_master
    )


sku_checks.append(
    {
        "Check": "Missing Product Names",
        "Issue Count": missing_product_names,
        "Status": (
            "Pass"
            if missing_product_names == 0
            else "Fail"
        ),
    }
)


# ------------------------------------------------------------
# Negative cost
# ------------------------------------------------------------
if "unit_cost" in sku_master.columns:

    negative_cost = int(
        (
            pd.to_numeric(
                sku_master["unit_cost"],
                errors="coerce",
            )
            < 0
        ).sum()
    )

else:

    negative_cost = 0


sku_checks.append(
    {
        "Check": "Negative Unit Cost",
        "Issue Count": negative_cost,
        "Status": (
            "Pass"
            if negative_cost == 0
            else "Fail"
        ),
    }
)


# ------------------------------------------------------------
# Negative list price
# ------------------------------------------------------------
if "list_price" in sku_master.columns:

    negative_price = int(
        (
            pd.to_numeric(
                sku_master["list_price"],
                errors="coerce",
            )
            < 0
        ).sum()
    )

else:

    negative_price = 0


sku_checks.append(
    {
        "Check": "Negative List Price",
        "Issue Count": negative_price,
        "Status": (
            "Pass"
            if negative_price == 0
            else "Fail"
        ),
    }
)


# ------------------------------------------------------------
# Cost greater than price
# ------------------------------------------------------------
if (
    "unit_cost" in sku_master.columns
    and "list_price" in sku_master.columns
):

    cost_above_price = int(
        (
            pd.to_numeric(
                sku_master["unit_cost"],
                errors="coerce",
            )
            >
            pd.to_numeric(
                sku_master["list_price"],
                errors="coerce",
            )
        ).sum()
    )

else:

    cost_above_price = 0


sku_checks.append(
    {
        "Check": "Unit Cost > List Price",
        "Issue Count": cost_above_price,
        "Status": (
            "Info"
            if cost_above_price > 0
            else "Pass"
        ),
    }
)


sku_checks_df = pd.DataFrame(
    sku_checks
)


# ============================================================
# CROSS-DATASET SKU CONSISTENCY
# ============================================================
section_header(
    "SKU Consistency",
    "Check whether sales and inventory records reference valid products in the SKU master.",
)


master_skus = set(
    sku_master["sku_id"]
    .dropna()
    .unique()
) if "sku_id" in sku_master.columns else set()


sales_skus = set(
    sales["sku_id"]
    .dropna()
    .unique()
) if "sku_id" in sales.columns else set()


inventory_skus = set(
    inventory["sku_id"]
    .dropna()
    .unique()
) if "sku_id" in inventory.columns else set()


sales_unknown_skus = (
    sales_skus - master_skus
)

inventory_unknown_skus = (
    inventory_skus - master_skus
)

master_without_sales = (
    master_skus - sales_skus
)

master_without_inventory = (
    master_skus - inventory_skus
)


col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Master SKUs",
    f"{len(master_skus):,}",
)

col2.metric(
    "Unknown Sales SKUs",
    f"{len(sales_unknown_skus):,}",
)

col3.metric(
    "Unknown Inventory SKUs",
    f"{len(inventory_unknown_skus):,}",
)

col4.metric(
    "Unused Master SKUs",
    f"{len(master_without_sales):,}",
)


if sales_unknown_skus:

    st.warning(
        f"{len(sales_unknown_skus)} SKU(s) appear in sales "
        "but not in the SKU master."
    )

else:

    st.success(
        "Sales SKU references are consistent with the SKU master."
    )


if inventory_unknown_skus:

    st.warning(
        f"{len(inventory_unknown_skus)} SKU(s) appear in inventory "
        "but not in the SKU master."
    )

else:

    st.success(
        "Inventory SKU references are consistent with the SKU master."
    )


# ============================================================
# DATASET QUALITY SCORE
# ============================================================
section_header(
    "Overall Data Quality",
    "Quality scores used to assess the reliability of the analytical foundation.",
)


overall_quality_score = round(
    quality_df["Quality Score"].mean(),
    2,
)


if overall_quality_score >= 95:

    quality_status = "Excellent"

elif overall_quality_score >= 85:

    quality_status = "Good"

elif overall_quality_score >= 70:

    quality_status = "Needs Attention"

else:

    quality_status = "Critical"


col1, col2, col3 = st.columns(3)

col1.metric(
    "Overall Quality Score",
    f"{overall_quality_score:.1f}%",
)

col2.metric(
    "Quality Status",
    quality_status,
)

col3.metric(
    "Datasets Checked",
    f"{len(datasets):,}",
)


fig = px.bar(
    quality_df,
    x="Dataset",
    y="Quality Score",
    text="Quality Score",
    title="Dataset Quality Scores",
)

fig.update_traces(
    texttemplate="%{text:.1f}%",
    textposition="outside",
)

fig.update_yaxes(
    range=[0, 105]
)

st.plotly_chart(
    fig,
    use_container_width=True,
)


# ============================================================
# DATASET SUMMARY
# ============================================================
section_header(
    "Dataset Summary",
    "Completeness, uniqueness and validity indicators for every source dataset.",
)


st.dataframe(
    quality_df,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# SALES VALIDATION
# ============================================================
section_header(
    "Sales Data Validation",
    "Checks that directly affect demand analysis and forecasting.",
)


st.dataframe(
    sales_checks_df,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# INVENTORY VALIDATION
# ============================================================
section_header(
    "Inventory Data Validation",
    "Checks that directly affect stockout, overstock and replenishment analysis.",
)


st.dataframe(
    inventory_checks_df,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# SKU MASTER VALIDATION
# ============================================================
section_header(
    "SKU Master Validation",
    "Checks that validate product attributes and financial assumptions.",
)


st.dataframe(
    sku_checks_df,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# DATE COVERAGE
# ============================================================
section_header(
    "Data Coverage",
    "Date ranges available to the analytical system.",
)


coverage_rows = []


if "date" in sales.columns:

    coverage_rows.append(
        {
            "Dataset": "Sales",
            "Start Date": sales["date"].min(),
            "End Date": sales["date"].max(),
            "Days Covered": (
                sales["date"].max()
                - sales["date"].min()
            ).days,
        }
    )


if "date" in inventory.columns:

    coverage_rows.append(
        {
            "Dataset": "Inventory",
            "Start Date": inventory["date"].min(),
            "End Date": inventory["date"].max(),
            "Days Covered": (
                inventory["date"].max()
                - inventory["date"].min()
            ).days,
        }
    )


coverage_df = pd.DataFrame(
    coverage_rows
)


if not coverage_df.empty:

    st.dataframe(
        coverage_df,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# DUPLICATE ANALYSIS
# ============================================================
section_header(
    "Duplicate Analysis",
    "Identify duplicate records that could distort analytics.",
)


duplicate_summary = []

for name, df in datasets.items():

    duplicate_summary.append(
        {
            "Dataset": name,
            "Duplicate Rows": int(
                df.duplicated().sum()
            ),
            "Duplicate %": round(
                safe_percentage(
                    df.duplicated().sum(),
                    len(df),
                ),
                2,
            ),
        }
    )


duplicate_df = pd.DataFrame(
    duplicate_summary
)


st.dataframe(
    duplicate_df,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# MISSING VALUE ANALYSIS
# ============================================================
section_header(
    "Missing Value Analysis",
    "Columns containing missing values across the three core datasets.",
)


missing_rows = []

for name, df in datasets.items():

    for column in df.columns:

        missing_count = int(
            df[column].isna().sum()
        )

        if missing_count > 0:

            missing_rows.append(
                {
                    "Dataset": name,
                    "Column": column,
                    "Missing Values": missing_count,
                    "Missing %": round(
                        safe_percentage(
                            missing_count,
                            len(df),
                        ),
                        2,
                    ),
                }
            )


missing_df = pd.DataFrame(
    missing_rows
)


if missing_df.empty:

    st.success(
        "No missing values detected."
    )

else:

    missing_df = missing_df.sort_values(
        "Missing %",
        ascending=False,
    )

    st.dataframe(
        missing_df,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# AUTOMATED QUALITY RECOMMENDATIONS
# ============================================================
section_header(
    "Data Quality Recommendations",
    "Actions generated from the validation results.",
)


failed_sales = (
    sales_checks_df["Status"]
    == "Fail"
).sum()

failed_inventory = (
    inventory_checks_df["Status"]
    == "Fail"
).sum()

failed_sku = (
    sku_checks_df["Status"]
    == "Fail"
).sum()


if overall_quality_score >= 95:

    recommendation_card(
        "Data Foundation Healthy",
        (
            "The core datasets have a strong quality score. "
            "FORESIGHT analytical and forecasting workflows can proceed normally."
        ),
    )

elif overall_quality_score >= 85:

    recommendation_card(
        "Minor Data Quality Issues",
        (
            "The data foundation is generally usable, but "
            "minor issues should be reviewed before production deployment."
        ),
    )

elif overall_quality_score >= 70:

    recommendation_card(
        "Data Quality Needs Attention",
        (
            "Several quality issues may affect analytical reliability. "
            "Review missing values, duplicates and invalid records."
        ),
    )

else:

    recommendation_card(
        "Critical Data Quality",
        (
            "The data foundation contains significant issues. "
            "Resolve critical validation failures before relying on forecasts or risk scores."
        ),
    )


if failed_sales > 0:

    recommendation_card(
        "Review Sales Data",
        (
            f"{failed_sales} sales validation check(s) failed. "
            "These issues may directly affect demand forecasting."
        ),
    )


if failed_inventory > 0:

    recommendation_card(
        "Review Inventory Data",
        (
            f"{failed_inventory} inventory validation check(s) failed. "
            "These issues may affect stockout and overstock calculations."
        ),
    )


if failed_sku > 0:

    recommendation_card(
        "Review SKU Master",
        (
            f"{failed_sku} SKU master validation check(s) failed. "
            "Product and financial attributes should be corrected."
        ),
    )


if sales_unknown_skus:

    recommendation_card(
        "Fix Sales SKU References",
        (
            f"{len(sales_unknown_skus)} sales SKU(s) do not exist "
            "in the SKU master."
        ),
    )


if inventory_unknown_skus:

    recommendation_card(
        "Fix Inventory SKU References",
        (
            f"{len(inventory_unknown_skus)} inventory SKU(s) do not exist "
            "in the SKU master."
        ),
    )


# ============================================================
# PRODUCTION READINESS
# ============================================================
section_header(
    "Production Readiness",
    "Determine whether the data foundation is ready for operational use.",
)


critical_conditions = [
    overall_quality_score < 70,
    len(sales_unknown_skus) > 0,
    len(inventory_unknown_skus) > 0,
    negative_sales_units > 0,
    negative_on_hand > 0,
    missing_sales_dates > 0,
    missing_inventory_dates > 0,
]


if any(critical_conditions):

    st.error(
        "🔴 NOT PRODUCTION READY — resolve critical data-quality issues before relying on automated decisions."
    )

elif overall_quality_score < 85:

    st.warning(
        "🟠 CONDITIONALLY READY — the system can be used for analysis, but data-quality issues should be reviewed."
    )

else:

    st.success(
        "🟢 PRODUCTION READY — the core data foundation passed the major validation checks."
    )


# ============================================================
# RAW DATA PREVIEW
# ============================================================
with st.expander(
    "🔍 Raw Data Preview"
):

    preview_dataset = st.selectbox(
        "Select Dataset",
        list(datasets.keys()),
    )

    preview_rows = st.slider(
        "Rows to Preview",
        min_value=5,
        max_value=50,
        value=10,
    )

    st.dataframe(
        datasets[
            preview_dataset
        ].head(preview_rows),
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# METHODOLOGY
# ============================================================
with st.expander(
    "ℹ️ Data Quality Methodology"
):

    st.markdown(
        """
### Completeness

Measures the percentage of cells containing valid,
non-missing information.

### Uniqueness

Measures duplicate records that could distort
aggregations and analytical results.

### Validity

Checks whether important fields such as dates,
quantities, prices and inventory values contain
logical values.

### SKU Consistency

Checks that SKU IDs used by Sales and Inventory
exist in the SKU Master.

### Production Readiness

The dashboard combines the quality score with
critical validation failures to determine whether
the data foundation is suitable for operational use.

The quality score is a decision-support indicator,
not a formal data-governance certification.
"""
    )


# ============================================================
# FOOTER
# ============================================================
show_footer()