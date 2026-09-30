import os
from pathlib import Path

import pandas as pd
import streamlit as st

# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# ============================================================
# EXPECTED SCHEMAS
# ============================================================

SALES_REQUIRED_COLUMNS = [
    "date",
    "sku_id",
    "units_sold",
]

SALES_OPTIONAL_COLUMNS = [
    "revenue",
]

INVENTORY_REQUIRED_COLUMNS = [
    "date",
    "sku_id",
    "on_hand_units",
    "on_order_units",
    "lead_time_days",
]

INVENTORY_OPTIONAL_COLUMNS = [
    "reorder_point",
]

SKU_MASTER_REQUIRED_COLUMNS = [
    "sku_id",
    "product_name",
    "category",
    "subcategory",
    "unit_cost",
    "list_price",
]

# ============================================================
# GENERIC CSV LOADER
# ============================================================

def _load_csv(filename: str) -> pd.DataFrame:
    file_path = DATA_DIR / filename

    if not file_path.exists():
        raise FileNotFoundError(
            f"Required data file was not found:\n{file_path}"
        )

    try:
        df = pd.read_csv(file_path)
    except Exception as exc:
        raise RuntimeError(
            f"Could not read {filename}: {exc}"
        ) from exc

    if df.empty:
        raise ValueError(
            f"{filename} exists but contains no records."
        )

    # Normalize column names.
    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
    )

    return df


# ============================================================
# COLUMN VALIDATION
# ============================================================

def _validate_columns(
    df: pd.DataFrame,
    required_columns: list,
    dataset_name: str,
):

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"{dataset_name} is missing required column(s): "
            + ", ".join(missing_columns)
        )


# ============================================================
# SALES COLUMN STANDARDIZATION
# ============================================================

def _standardize_sales_columns(
    df: pd.DataFrame,
) -> pd.DataFrame:

    df = df.copy()

    rename_map = {}

    # sales_daily.csv contains "SKU".
    # _load_csv() converts it to "sku".
    # The application expects "sku_id".

    if "sku" in df.columns and "sku_id" not in df.columns:
        rename_map["sku"] = "sku_id"

    if rename_map:
        df = df.rename(columns=rename_map)

    return df


# ============================================================
# INVENTORY COLUMN STANDARDIZATION
# ============================================================

def _standardize_inventory_columns(
    df: pd.DataFrame,
) -> pd.DataFrame:
    df = df.copy()

    rename_map = {
        "snapshot_date": "date",
        "sku": "sku_id",
        "current_stock": "on_hand_units",
        "on_order": "on_order_units",
        "lead_time_days": "lead_time_days",
        "safety_stock": "safety_stock",
        "reorder_point": "reorder_point",
        "inventory_value": "inventory_value",
        "warehouse_zone": "warehouse_zone",
        "total_available": "total_available",
        "is_below_reorder": "is_below_reorder",
    }

    existing_map = {
        old: new
        for old, new in rename_map.items()
        if old in df.columns
    }

    df = df.rename(columns=existing_map)

    return df

# ============================================================
# SKU MASTER COLUMN STANDARDIZATION
# ============================================================

def _standardize_sku_master_columns(
    df: pd.DataFrame,
) -> pd.DataFrame:

    df = df.copy()

    rename_map = {
        "sku": "sku_id",
        "product_name": "product_name",
        "category": "category",
        "subcategory": "subcategory",
        "launch_date": "launch_date",
        "cost_price": "unit_cost",
        "selling_price": "list_price",
        "gross_margin_per_unit": "gross_margin_per_unit",
        "supplier_region": "supplier_region",
        "margin_percent": "margin_percent",
        "price_tier": "price_tier",
    }

    existing_map = {
        old: new
        for old, new in rename_map.items()
        if old in df.columns
    }

    df = df.rename(columns=existing_map)

    return df

# ============================================================
# SKU NORMALIZATION
# ============================================================

def _normalize_sku_column(
    df: pd.DataFrame,
) -> pd.DataFrame:

    df = df.copy()

    if "sku_id" in df.columns:

        df["sku_id"] = (
            df["sku_id"]
            .astype("string")
            .str.strip()
        )

        df["sku_id"] = df["sku_id"].replace(
            "",
            pd.NA,
        )

    return df


# ============================================================
# DATE NORMALIZATION
# ============================================================

def _normalize_date_column(
    df: pd.DataFrame,
) -> pd.DataFrame:

    df = df.copy()

    if "date" in df.columns:

        df["date"] = pd.to_datetime(
            df["date"],
            errors="coerce",
        )

        df["date"] = df["date"].dt.normalize()

    return df


# ============================================================
# NUMERIC NORMALIZATION
# ============================================================

def _normalize_numeric_columns(
    df: pd.DataFrame,
    columns: list,
) -> pd.DataFrame:

    df = df.copy()

    for column in columns:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    return df


# ============================================================
# SALES CLEANING
# ============================================================

def _clean_sales(
    df: pd.DataFrame,
) -> pd.DataFrame:

    df = df.copy()

    # Convert source names to project-standard names.
    df = _standardize_sales_columns(df)

    _validate_columns(
        df,
        SALES_REQUIRED_COLUMNS,
        "Sales dataset",
    )

    df = _normalize_sku_column(df)

    df = _normalize_date_column(df)

    numeric_columns = [
        "units_sold",
        "revenue",
        "price",
        "promotion",
        "month",
    ]

    df = _normalize_numeric_columns(
        df,
        numeric_columns,
    )

    # Remove records with unusable primary keys.
    df = df.dropna(
        subset=[
            "date",
            "sku_id",
        ]
    )

    # Sales quantities cannot be negative.
    if "units_sold" in df.columns:
        df = df[
            df["units_sold"] >= 0
        ]

    # Revenue cannot be negative.
    if "revenue" in df.columns:
        df = df[
            df["revenue"] >= 0
        ]

    # Price cannot be negative.
    if "price" in df.columns:
        df = df[
            df["price"] >= 0
        ]

    # Promotion cannot be negative.
    if "promotion" in df.columns:
        df = df[
            df["promotion"] >= 0
        ]

    # Remove exact duplicate records.
    df = df.drop_duplicates()

    return df.sort_values(
        ["date", "sku_id"]
    ).reset_index(
        drop=True
    )


# ============================================================
# INVENTORY CLEANING
# ============================================================

def _clean_inventory(
    df: pd.DataFrame,
) -> pd.DataFrame:

    df = df.copy()

    # Convert source names to project-standard names.
    df = _standardize_inventory_columns(df)

    _validate_columns(
        df,
        INVENTORY_REQUIRED_COLUMNS,
        "Inventory dataset",
    )

    df = _normalize_sku_column(df)

    df = _normalize_date_column(df)

    numeric_columns = [
        "on_hand_units",
        "on_order_units",
        "lead_time_days",
        "reorder_point",
    ]

    df = _normalize_numeric_columns(
        df,
        numeric_columns,
    )

    # Remove records without primary keys.
    df = df.dropna(
        subset=[
            "date",
            "sku_id",
        ]
    )

    # Inventory quantities cannot be negative.
    for column in [
        "on_hand_units",
        "on_order_units",
        "reorder_point",
    ]:

        if column in df.columns:
            df = df[
                df[column] >= 0
            ]

    # Lead time cannot be negative.
    if "lead_time_days" in df.columns:
        df = df[
            df["lead_time_days"] >= 0
        ]

    # Remove exact duplicates.
    df = df.drop_duplicates()

    return df.sort_values(
        ["date", "sku_id"]
    ).reset_index(
        drop=True
    )

# ============================================================
# SKU MASTER CLEANING
# ============================================================

def _clean_sku_master(
    df: pd.DataFrame,
) -> pd.DataFrame:

    df = df.copy()

    # Convert source column names to project-standard names.
    df = _standardize_sku_master_columns(df)

    # Validate after standardization.
    _validate_columns(
        df,
        SKU_MASTER_REQUIRED_COLUMNS,
        "SKU master dataset",
    )

    df = _normalize_sku_column(df)

    # Normalize launch date if available.
    if "launch_date" in df.columns:
        df["launch_date"] = pd.to_datetime(
            df["launch_date"],
            errors="coerce",
        )

    numeric_columns = [
        "unit_cost",
        "list_price",
        "gross_margin_per_unit",
        "margin_percent",
    ]

    df = _normalize_numeric_columns(
        df,
        numeric_columns,
    )

    # Remove records without SKU.
    df = df.dropna(
        subset=["sku_id"]
    )

    # Remove exact duplicates.
    df = df.drop_duplicates()

    # Keep one master record per SKU.
    df = df.drop_duplicates(
        subset=["sku_id"],
        keep="last",
    )

    # Financial values cannot be negative.
    for column in [
        "unit_cost",
        "list_price",
    ]:

        if column in df.columns:
            df = df[
                df[column] >= 0
            ]

    # Clean text fields.
    for column in [
        "product_name",
        "category",
        "subcategory",
        "supplier_region",
        "price_tier",
    ]:

        if column in df.columns:

            df[column] = (
                df[column]
                .astype("string")
                .str.strip()
            )

    return df.sort_values(
        "sku_id"
    ).reset_index(
        drop=True
    )

# ============================================================
# CROSS-DATASET SKU VALIDATION
# ============================================================

def _validate_sku_references(
    sales: pd.DataFrame,
    inventory: pd.DataFrame,
    sku_master: pd.DataFrame,
):

    master_skus = set(
        sku_master["sku_id"]
        .dropna()
        .astype(str)
    )

    sales_skus = set(
        sales["sku_id"]
        .dropna()
        .astype(str)
    )

    inventory_skus = set(
        inventory["sku_id"]
        .dropna()
        .astype(str)
    )

    unknown_sales = (
        sales_skus - master_skus
    )

    unknown_inventory = (
        inventory_skus - master_skus
    )

    if unknown_sales:

        st.warning(
            f"⚠️ {len(unknown_sales)} SKU(s) "
            "in Sales are not present in SKU Master."
        )

    if unknown_inventory:

        st.warning(
            f"⚠️ {len(unknown_inventory)} SKU(s) "
            "in Inventory are not present in SKU Master."
        )


# ============================================================
# SALES LOADER
# ============================================================

@st.cache_data
def load_sales() -> pd.DataFrame:

    df = _load_csv(
        "sales_daily.csv"
    )

    return _clean_sales(df)


# ============================================================
# INVENTORY LOADER
# ============================================================

@st.cache_data
def load_inventory() -> pd.DataFrame:

    df = _load_csv(
        "inventory_snapshots.csv"
    )

    return _clean_inventory(df)


# ============================================================
# SKU MASTER LOADER
# ============================================================

@st.cache_data
def load_sku_master() -> pd.DataFrame:

    df = _load_csv(
        "sku_master.csv"
    )

    return _clean_sku_master(df)


# ============================================================
# LOAD ALL DATASETS
# ============================================================

@st.cache_data
def load_all_data():

    sales = load_sales()

    inventory = load_inventory()

    sku_master = load_sku_master()

    _validate_sku_references(
        sales,
        inventory,
        sku_master,
    )

    return (
        sales,
        inventory,
        sku_master,
    )


# ============================================================
# DATASET HEALTH REPORT
# ============================================================

def get_data_health_report():

    report = []

    loaders = [
        (
            "Sales",
            load_sales,
        ),
        (
            "Inventory",
            load_inventory,
        ),
        (
            "SKU Master",
            load_sku_master,
        ),
    ]

    for dataset_name, loader in loaders:

        try:

            df = loader()

            report.append(
                {
                    "Dataset": dataset_name,
                    "Status": "Healthy",
                    "Rows": len(df),
                    "Columns": len(df.columns),
                    "Error": "",
                }
            )

        except Exception as exc:

            report.append(
                {
                    "Dataset": dataset_name,
                    "Status": "Error",
                    "Rows": 0,
                    "Columns": 0,
                    "Error": str(exc),
                }
            )

    return pd.DataFrame(report)


# ============================================================
# CACHE RESET
# ============================================================

def clear_data_cache():

    load_sales.clear()
    load_inventory.clear()
    load_sku_master.clear()
    load_all_data.clear()