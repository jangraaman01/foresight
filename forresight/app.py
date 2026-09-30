import streamlit as st


from src.ui import (
    apply_foresight_style,
    show_sidebar_brand,
    page_header,
    section_header,
    show_footer,
)


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="FORESIGHT | Intelligent Business Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
from src.auth import require_login, sidebar_user

require_login()

# ============================================================
# HELPERS
# ============================================================
# Streamlit's Markdown parser treats blank lines and 4+ space
# indentation as code blocks, so HTML is built as one compact string.

def card(icon, title, text, css_class="metric-card"):
    icon_html = f'<div style="font-size:28px;">{icon}</div>' if icon else ""
    st.markdown(
        f'<div class="{css_class}">'
        f"{icon_html}"
        f"<h3>{title}</h3>"
        f"<p>{text}</p>"
        f"</div>",
        unsafe_allow_html=True,
    )


# ============================================================
# GLOBAL UI
# ============================================================

apply_foresight_style()
show_sidebar_brand()
sidebar_user()

# ============================================================
# SIDEBAR NAVIGATION
# ============================================================

st.sidebar.markdown("---")

st.sidebar.markdown(
    '<div class="sidebar-section-title">EXECUTIVE</div>',
    unsafe_allow_html=True,
)

st.sidebar.page_link("pages/home.py", label="🏠  Home")
st.sidebar.page_link("pages/executive.py", label="📋  Executive Summary")
st.sidebar.page_link("pages/kpi_dashboard.py", label="📊  KPI Dashboard")


st.sidebar.markdown(
    '<div class="sidebar-section-title">ANALYTICS</div>',
    unsafe_allow_html=True,
)

st.sidebar.page_link("pages/sales.py", label="📈  Sales Analytics")
st.sidebar.page_link("pages/forecast.py", label="🔮  Demand Forecast")


st.sidebar.markdown(
    '<div class="sidebar-section-title">INVENTORY</div>',
    unsafe_allow_html=True,
)

st.sidebar.page_link("pages/inventory.py", label="📦  Inventory Dashboard")
st.sidebar.page_link("pages/risk.py", label="⚠️  Risk Dashboard")
st.sidebar.page_link("pages/business_impact.py", label="💰  Business Impact")


st.sidebar.markdown(
    '<div class="sidebar-section-title">PRODUCT</div>',
    unsafe_allow_html=True,
)

st.sidebar.page_link("pages/product.py", label="🔎  Product Details")
st.sidebar.page_link("pages/data_quality.py", label="🛡️  Data Quality")


# ============================================================
# SIDEBAR FOOTER
# ============================================================

st.sidebar.markdown("---")

st.sidebar.markdown(
    '<div style="text-align:center;color:#94A3B8;font-size:12px;'
    'line-height:1.6;padding:10px 4px;">'
    "<strong>FORESIGHT</strong><br>"
    "Intelligent Business Analytics<br>"
    '<span style="font-size:11px;">Decision Support Platform</span>'
    "</div>",
    unsafe_allow_html=True,
)


# ============================================================
# MAIN LANDING PAGE
# ============================================================

page_header(
    "📊 FORESIGHT",
    "Intelligent business analytics and decision-support platform.",
)


# ============================================================
# PLATFORM OVERVIEW
# ============================================================

section_header(
    "Platform Overview",
    "Use the navigation menu to explore business performance, demand, inventory and risk.",
)

col1, col2, col3, col4 = st.columns(4)

with col1:
    card(
        "📈",
        "Sales Analytics",
        "Analyze sales trends, product performance and business growth.",
    )

with col2:
    card(
        "🔮",
        "Demand Forecast",
        "Forecast future demand and identify increasing or declining products.",
    )

with col3:
    card(
        "📦",
        "Inventory Intelligence",
        "Monitor stock levels, weeks of supply and inventory health.",
    )

with col4:
    card(
        "⚠️",
        "Risk Management",
        "Detect stockout, overstock and financial exposure risks.",
    )


# ============================================================
# DECISION WORKFLOW
# ============================================================

section_header(
    "FORESIGHT Decision Workflow",
    "A unified analytical workflow from raw data to management action.",
)

workflow_cols = st.columns(5)

workflow = [
    ("01", "Data", "Sales + Inventory"),
    ("02", "Analyze", "Business Trends"),
    ("03", "Forecast", "Future Demand"),
    ("04", "Assess", "Risk + Exposure"),
    ("05", "Act", "Management Decisions"),
]

for col, (number, title, description) in zip(workflow_cols, workflow):
    with col:
        st.markdown(
            '<div class="metric-card" style="text-align:center;">'
            '<div style="font-size:14px;font-weight:700;margin-bottom:8px;">'
            f"STEP {number}"
            "</div>"
            f'<h3 style="margin-bottom:5px;">{title}</h3>'
            f'<p style="margin:0;">{description}</p>'
            "</div>",
            unsafe_allow_html=True,
        )


# ============================================================
# QUICK ACCESS
# ============================================================

section_header(
    "Quick Access",
    "Open the most important decision-support dashboards.",
)

q1, q2, q3, q4, q5 = st.columns(5)

with q1:
    st.page_link(
        "pages/executive.py",
        label="📋 Executive Summary",
        use_container_width=True,
    )

with q2:
    st.page_link(
        "pages/forecast.py",
        label="🔮 Demand Forecast",
        use_container_width=True,
    )

with q3:
    st.page_link(
        "pages/risk.py",
        label="⚠️ Risk Dashboard",
        use_container_width=True,
    )

with q4:
    st.page_link(
        "pages/business_impact.py",
        label="💰 Business Impact",
        use_container_width=True,
    )

with q5:
    st.page_link(
        "pages/kpi_dashboard.py",
        label="📊 KPI Dashboard",
        use_container_width=True,
    )


# ============================================================
# PRODUCT VALUE
# ============================================================

section_header(
    "What FORESIGHT Delivers",
    "Transform operational data into actionable business intelligence.",
)

value1, value2, value3 = st.columns(3)

with value1:
    card(
        "",
        "🎯 Better Decisions",
        "Identify the products and business areas that require immediate attention.",
        "recommendation-card",
    )

with value2:
    card(
        "",
        "📊 Data-Driven Planning",
        "Combine historical sales, inventory and forecast information for better planning.",
        "recommendation-card",
    )

with value3:
    card(
        "",
        "💰 Financial Protection",
        "Quantify sales-at-risk, excess inventory and capital locked in stock.",
        "recommendation-card",
    )


# ============================================================
# FOOTER
# ============================================================

show_footer()