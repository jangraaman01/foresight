import streamlit as st
import plotly.io as pio

pio.templates.default = "plotly_dark"


# ============================================================
# GLOBAL FORESIGHT STYLE
# ============================================================

def apply_foresight_style():

    st.markdown(
        """
        <style>

        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@600;700;800&family=Inter:wght@400;500;600;700&display=swap');

        /* =====================================================
           GLOBAL
        ===================================================== */

        .stApp {
            background: #0B1220;
            font-family: 'Inter', sans-serif;
        }

        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1500px;
        }


        /* =====================================================
           SIDEBAR
        ===================================================== */

        section[data-testid="stSidebar"] {
            background: #070B14;
        }

        section[data-testid="stSidebar"] * {
            color: #E2E8F0;
        }

        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {
            color: #FFFFFF;
        }


        /* =====================================================
           HEADINGS
        ===================================================== */

        h1 {
            font-family: 'Manrope', sans-serif;
            font-size: 2.2rem !important;
            font-weight: 800 !important;
            letter-spacing: -0.01em;
            color: #F8FAFC;
        }

        h2 {
            font-family: 'Manrope', sans-serif;
            font-size: 1.5rem !important;
            font-weight: 700 !important;
            letter-spacing: -0.005em;
            color: #F1F5F9;
        }

        h3 {
            font-family: 'Manrope', sans-serif;
            font-size: 1.15rem !important;
            font-weight: 700 !important;
            color: #E2E8F0;
        }

        p, span, label, div, td, th {
            font-variant-numeric: tabular-nums;
        }


        /* =====================================================
           METRIC CARDS
        ===================================================== */

        div[data-testid="stMetric"] {
            background: #121A2B;
            border: 1px solid #1F2A3D;
            border-left: 3px solid #3B82F6;
            border-radius: 10px;
            padding: 16px 18px;
        }

        div[data-testid="stMetricLabel"] {
            color: #94A3B8;
            font-size: 0.82rem;
            font-weight: 600;
        }

        div[data-testid="stMetricValue"] {
            font-family: 'Manrope', sans-serif;
            color: #F1F5F9;
            font-size: 1.7rem;
            font-weight: 800;
        }


        /* =====================================================
           BUTTONS
        ===================================================== */

        .stButton > button {
            border-radius: 8px;
            border: 1px solid #1F2A3D;
            font-weight: 600;
            padding: 0.55rem 1rem;
            background: #121A2B;
            color: #E2E8F0;
        }

        .stButton > button:hover {
            border-color: #3B82F6;
            color: #60A5FA;
        }


        /* =====================================================
           DATAFRAMES
        ===================================================== */

        div[data-testid="stDataFrame"] {
            border-radius: 10px;
            overflow: hidden;
            border: 1px solid #1F2A3D;
        }


        /* =====================================================
           EXPANDERS
        ===================================================== */

        div[data-testid="stExpander"] {
            border: 1px solid #1F2A3D;
            border-radius: 10px;
            background: #121A2B;
        }


        /* =====================================================
           ALERTS
        ===================================================== */

        div[data-testid="stAlert"] {
            border-radius: 8px;
        }


        /* =====================================================
           SELECTBOX / MULTISELECT
        ===================================================== */

        div[data-baseweb="select"] > div {
            border-radius: 8px;
        }


        /* =====================================================
           CUSTOM FORESIGHT BRAND
        ===================================================== */

        .foresight-brand {
            padding: 8px 0 20px 0;
        }

        .foresight-brand-title {
            font-family: 'Manrope', sans-serif;
            font-size: 1.3rem;
            font-weight: 800;
            letter-spacing: 0.03em;
            color: #FFFFFF;
        }

        .foresight-brand-subtitle {
            font-size: 0.75rem;
            color: #94A3B8;
            margin-top: 2px;
        }


        /* =====================================================
           PAGE HEADER
           No card/shadow here — a quiet banner with a single
           accent rule underneath, so it reads as the top of the
           page rather than another card competing with the ones
           below it.
        ===================================================== */

        .foresight-header {
            padding: 4px 0 20px 0;
            margin-bottom: 20px;
            border-bottom: 1px solid #1F2A3D;
        }

        .foresight-header-title {
            font-family: 'Manrope', sans-serif;
            font-size: 1.9rem;
            font-weight: 800;
            letter-spacing: -0.01em;
            color: #F8FAFC;
            margin: 0 0 6px 0;
            line-height: 1.25;
        }

        .foresight-header-description {
            color: #94A3B8;
            font-size: 0.95rem;
            max-width: 640px;
            line-height: 1.5;
        }

        .foresight-header-rule {
            height: 3px;
            width: 56px;
            margin-top: 14px;
            background: #3B82F6;
            border-radius: 2px;
        }


        /* =====================================================
           SECTION HEADER
        ===================================================== */

        .foresight-section {
            margin-top: 30px;
            margin-bottom: 14px;
        }

        .foresight-section-title {
            font-family: 'Manrope', sans-serif;
            font-size: 1.2rem;
            font-weight: 700;
            color: #F1F5F9;
            margin: 0;
            line-height: 1.3;
        }

        .foresight-section-subtitle {
            font-size: 0.82rem;
            color: #94A3B8;
            margin-top: 2px;
        }


        /* =====================================================
           STATUS BADGES
        ===================================================== */

        .status-critical {
            background: rgba(248, 113, 113, 0.12);
            color: #FCA5A5;
            border: 1px solid rgba(248, 113, 113, 0.35);
        }

        .status-high {
            background: rgba(251, 146, 60, 0.12);
            color: #FDBA74;
            border: 1px solid rgba(251, 146, 60, 0.35);
        }

        .status-medium {
            background: rgba(250, 204, 21, 0.12);
            color: #FDE047;
            border: 1px solid rgba(250, 204, 21, 0.35);
        }

        .status-low {
            background: rgba(74, 222, 128, 0.12);
            color: #86EFAC;
            border: 1px solid rgba(74, 222, 128, 0.35);
        }

        .foresight-badge {
            display: inline-block;
            padding: 5px 11px;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 700;
        }


        /* =====================================================
           METRIC / FEATURE CARD
           (used for the landing-page feature and workflow tiles)
        ===================================================== */

        .metric-card {
            background: #121A2B;
            border: 1px solid #1F2A3D;
            border-radius: 10px;
            padding: 16px 18px;
            margin-bottom: 10px;
        }


        /* =====================================================
           RECOMMENDATION CARD
        ===================================================== */

        .recommendation-card {
            background: #121A2B;
            border: 1px solid #1F2A3D;
            border-left: 3px solid #3B82F6;
            border-radius: 10px;
            padding: 16px 18px;
            margin-bottom: 10px;
        }

        .recommendation-title {
            font-family: 'Manrope', sans-serif;
            font-weight: 700;
            color: #F1F5F9;
            margin-bottom: 4px;
        }

        .recommendation-text {
            color: #94A3B8;
            font-size: 0.9rem;
            line-height: 1.5;
        }


        /* =====================================================
           FOOTER
        ===================================================== */

        .foresight-footer {
            text-align: center;
            padding: 25px 0 5px 0;
            color: #7C8DA6;
            font-size: 0.78rem;
        }

        </style>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# BRANDING
# ============================================================

def show_sidebar_brand():

    with st.sidebar:

        st.markdown(
            '<div class="foresight-brand">'
            '<div class="foresight-brand-title">📊 FORESIGHT</div>'
            '<div class="foresight-brand-subtitle">Decision Intelligence Platform</div>'
            '</div>',
            unsafe_allow_html=True
        )


# ============================================================
# PAGE HEADER
# ============================================================

def page_header(title, description=""):

    description_html = (
        f'<div class="foresight-header-description">{description}</div>'
        if description else ""
    )

    st.markdown(
        '<div class="foresight-header">'
        f'<h1 class="foresight-header-title">{title}</h1>'
        f'{description_html}'
        '<div class="foresight-header-rule"></div>'
        '</div>',
        unsafe_allow_html=True
    )


# ============================================================
# SECTION HEADER
# ============================================================

def section_header(title, subtitle=""):

    subtitle_html = (
        f'<div class="foresight-section-subtitle">{subtitle}</div>'
        if subtitle else ""
    )

    st.markdown(
        '<div class="foresight-section">'
        f'<h2 class="foresight-section-title">{title}</h2>'
        f'{subtitle_html}'
        '</div>',
        unsafe_allow_html=True
    )


# ============================================================
# RISK BADGE
# ============================================================

def risk_badge(level):

    level = str(level)

    css_class = {
        "Critical": "status-critical",
        "High": "status-high",
        "Medium": "status-medium",
        "Low": "status-low"
    }.get(level, "status-low")

    return f'<span class="foresight-badge {css_class}">{level}</span>'


# ============================================================
# RECOMMENDATION
# ============================================================

def recommendation_card(title, text):

    st.markdown(
        '<div class="recommendation-card">'
        f'<div class="recommendation-title">{title}</div>'
        f'<div class="recommendation-text">{text}</div>'
        '</div>',
        unsafe_allow_html=True
    )


# ============================================================
# FOOTER
# ============================================================

def show_footer():

    st.markdown(
        '<div class="foresight-footer">'
        'FORESIGHT · Sales · Demand · Inventory · Risk Intelligence'
        '</div>',
        unsafe_allow_html=True
    )
