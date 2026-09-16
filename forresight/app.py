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


# ============================================================
# GLOBAL UI
# ============================================================

apply_foresight_style()
show_sidebar_brand()


# ============================================================
# SIDEBAR NAVIGATION
# ============================================================

st.sidebar.markdown("---")

st.sidebar.markdown(
    '<div class="sidebar-section-title">EXECUTIVE</div>',
    unsafe_allow_html=True,
)

st.sidebar.page_link(
    "pages/home.py",
    label="🏠  Home",
)

st.sidebar.page_link(
    "pages/executive.py",
    label="📋  Executive Summary",
)

st.sidebar.page_link(
    "pages/kpi_dashboard.py",
    label="📊  KPI Dashboard",
)

st.sidebar.markdown(
    '<div class="sidebar-section-title">ANALYTICS</div>',
    unsafe_allow_html=True,
)

st.sidebar.page_link(
    "pages/sales.py",
    label="📈  Sales Analytics",
)

st.sidebar.page_link(
    "pages/forecast.py",
    label="🔮  Demand Forecast",
)


st.sidebar.markdown(
    '<div class="sidebar-section-title">INVENTORY</div>',
    unsafe_allow_html=True,
)

st.sidebar.page_link(
    "pages/inventory.py",
    label="📦  Inventory Dashboard",
)

st.sidebar.page_link(
    "pages/risk.py",
    label="⚠️  Risk Dashboard",
)

st.sidebar.page_link(
    "pages/business_impact.py",
    label="💰  Business Impact",
)


st.sidebar.markdown(
    '<div class="sidebar-section-title">PRODUCT</div>',
    unsafe_allow_html=True,
)

st.sidebar.page_link(
    "pages/product.py",
    label="🔎  Product Details",
)

st.sidebar.page_link(
    "pages/data_quality.py",
    label="🛡️  Data Quality",
)


# ============================================================
# SIDEBAR FOOTER
# ============================================================

st.sidebar.markdown("---")

st.sidebar.markdown(
    """
    <div style="
        text-align:center;
        color:#94A3B8;
        font-size:12px;
        line-height:1.6;
        padding:10px 4px;
    ">
        <strong>FORESIGHT</strong><br>
        Intelligent Business Analytics<br>
        <span style="font-size:11px;">
            Decision Support Platform
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# MAIN LANDING PAGE
# ============================================================

page_header(
    "📊 FORESIGHT",
    "Intelligent business analytics and decision-support platform."
)


# ============================================================
# PLATFORM OVERVIEW
# ============================================================

section_header(
    "Platform Overview",
    "Use the navigation menu to explore business performance, demand, inventory and risk."
)


col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(
        """
        <div class="metric-card">
            <div style="font-size:28px;">📈</div>
            <h3>Sales Analytics</h3>
            <p>
                Analyze sales trends, product performance and
                business growth.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        """
        <div class="metric-card">
            <div style="font-size:28px;">🔮</div>
            <h3>Demand Forecast</h3>
            <p>
                Forecast future demand and identify increasing
                or declining products.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        """
        <div class="metric-card">
            <div style="font-size:28px;">📦</div>
            <h3>Inventory Intelligence</h3>
            <p>
                Monitor stock levels, weeks of supply and
                inventory health.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col4:
    st.markdown(
        """
        <div class="metric-card">
            <div style="font-size:28px;">⚠️</div>
            <h3>Risk Management</h3>
            <p>
                Detect stockout, overstock and financial
                exposure risks.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# DECISION WORKFLOW
# ============================================================

section_header(
    "FORESIGHT Decision Workflow",
    "A unified analytical workflow from raw data to management action."
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
            f"""
            <div class="metric-card" style="text-align:center;">
                <div style="
                    font-size:14px;
                    font-weight:700;
                    margin-bottom:8px;
                ">
                    STEP {number}
                </div>

                <h3 style="margin-bottom:5px;">
                    {title}
                </h3>

                <p style="margin:0;">
                    {description}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# QUICK ACCESS
# ============================================================

section_header(
    "Quick Access",
    "Open the most important decision-support dashboards."
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
    "Transform operational data into actionable business intelligence."
)

value1, value2, value3 = st.columns(3)

with value1:
    st.markdown(
        """
        <div class="recommendation-card">
            <h3>🎯 Better Decisions</h3>
            <p>
                Identify the products and business areas that
                require immediate attention.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with value2:
    st.markdown(
        """
        <div class="recommendation-card">
            <h3>📊 Data-Driven Planning</h3>
            <p>
                Combine historical sales, inventory and forecast
                information for better planning.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with value3:
    st.markdown(
        """
        <div class="recommendation-card">
            <h3>💰 Financial Protection</h3>
            <p>
                Quantify sales-at-risk, excess inventory and
                capital locked in stock.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# FOOTER
# ============================================================

show_footer()