import streamlit as st


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
            background: #F7F9FC;
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
            background: #0F172A;
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
            color: #0F172A;
        }

        h2 {
            font-family: 'Manrope', sans-serif;
            font-size: 1.5rem !important;
            font-weight: 700 !important;
            letter-spacing: -0.005em;
            color: #0F172A;
        }

        h3 {
            font-family: 'Manrope', sans-serif;
            font-size: 1.15rem !important;
            font-weight: 700 !important;
            color: #1E293B;
        }

        p, span, label, div, td, th {
            font-variant-numeric: tabular-nums;
        }


        /* =====================================================
           METRIC CARDS
        ===================================================== */

        div[data-testid="stMetric"] {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-left: 3px solid #2563EB;
            border-radius: 10px;
            padding: 16px 18px;
        }

        div[data-testid="stMetricLabel"] {
            color: #64748B;
            font-size: 0.82rem;
            font-weight: 600;
        }

        div[data-testid="stMetricValue"] {
            font-family: 'Manrope', sans-serif;
            color: #0F172A;
            font-size: 1.7rem;
            font-weight: 800;
        }


        /* =====================================================
           BUTTONS
        ===================================================== */

        .stButton > button {
            border-radius: 8px;
            border: 1px solid #CBD5E1;
            font-weight: 600;
            padding: 0.55rem 1rem;
            background: #FFFFFF;
        }

        .stButton > button:hover {
            border-color: #2563EB;
            color: #2563EB;
        }


        /* =====================================================
           DATAFRAMES
        ===================================================== */

        div[data-testid="stDataFrame"] {
            border-radius: 10px;
            overflow: hidden;
            border: 1px solid #E2E8F0;
        }


        /* =====================================================
           EXPANDERS
        ===================================================== */

        div[data-testid="stExpander"] {
            border: 1px solid #E2E8F0;
            border-radius: 10px;
            background: #FFFFFF;
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
            border-bottom: 1px solid #E2E8F0;
        }

        .foresight-header-title {
            font-family: 'Manrope', sans-serif;
            font-size: 1.9rem;
            font-weight: 800;
            letter-spacing: -0.01em;
            color: #0F172A;
            margin-bottom: 6px;
        }

        .foresight-header-description {
            color: #64748B;
            font-size: 0.95rem;
            max-width: 640px;
            line-height: 1.5;
        }

        .foresight-header-rule {
            height: 3px;
            width: 56px;
            margin-top: 14px;
            background: #2563EB;
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
            color: #0F172A;
        }

        .foresight-section-subtitle {
            font-size: 0.82rem;
            color: #64748B;
            margin-top: 2px;
        }


        /* =====================================================
           STATUS BADGES
        ===================================================== */

        .status-critical {
            background: #FEF2F2;
            color: #991B1B;
            border: 1px solid #FECACA;
        }

        .status-high {
            background: #FFF7ED;
            color: #9A3412;
            border: 1px solid #FED7AA;
        }

        .status-medium {
            background: #FEFCE8;
            color: #854D0E;
            border: 1px solid #FEF08A;
        }

        .status-low {
            background: #F0FDF4;
            color: #166534;
            border: 1px solid #BBF7D0;
        }

        .foresight-badge {
            display: inline-block;
            padding: 5px 11px;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 700;
        }


        /* =====================================================
           RECOMMENDATION CARD
        ===================================================== */

        .recommendation-card {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-left: 3px solid #2563EB;
            border-radius: 10px;
            padding: 16px 18px;
            margin-bottom: 10px;
        }

        .recommendation-title {
            font-family: 'Manrope', sans-serif;
            font-weight: 700;
            color: #0F172A;
            margin-bottom: 4px;
        }

        .recommendation-text {
            color: #475569;
            font-size: 0.9rem;
            line-height: 1.5;
        }


        /* =====================================================
           FOOTER
        ===================================================== */

        .foresight-footer {
            text-align: center;
            padding: 25px 0 5px 0;
            color: #94A3B8;
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
            """
            <div class="foresight-brand">

                <div class="foresight-brand-title">
                    📊 FORESIGHT
                </div>

                <div class="foresight-brand-subtitle">
                    Decision Intelligence Platform
                </div>

            </div>
            """,
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
        f"""
        <div class="foresight-header">

            <div class="foresight-header-title">
                {title}
            </div>

            {description_html}

            <div class="foresight-header-rule"></div>

        </div>
        """,
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
        f"""
        <div class="foresight-section">

            <div class="foresight-section-title">
                {title}
            </div>

            {subtitle_html}

        </div>
        """,
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

    return f"""
        <span class="foresight-badge {css_class}">
            {level}
        </span>
    """


# ============================================================
# RECOMMENDATION
# ============================================================

def recommendation_card(title, text):

    st.markdown(
        f"""
        <div class="recommendation-card">

            <div class="recommendation-title">
                {title}
            </div>

            <div class="recommendation-text">
                {text}
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# FOOTER
# ============================================================

def show_footer():

    st.markdown(
        """
        <div class="foresight-footer">

            FORESIGHT · Sales · Demand · Inventory · Risk Intelligence

        </div>
        """,
        unsafe_allow_html=True
    )
