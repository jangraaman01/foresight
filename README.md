# FORESIGHT — Inventory & Demand Forecasting Intelligence Platform

## Overview

FORESIGHT is an inventory and demand forecasting analytics platform designed to help businesses
understand demand patterns, monitor inventory health, identify replenishment requirements, and 
support data-driven inventory decisions.

The platform combines historical sales, inventory, SKU master data, forecasting, KPI analysis, 
inventory optimization, working-capital analytics, and executive decision support into an interactive
Streamlit dashboard.

## Key Features

* Sales and inventory data analysis
* Data quality validation
* Exploratory data analysis
* Weekly demand analysis
* Seasonal-naive forecasting baseline
* Demand feature engineering
* Forecast generation
* SKU-level forecasting
* Forecast performance analysis
* ABC/Pareto analysis
* Inventory turnover analysis
* Days Inventory Outstanding (DIO)
* Slow-moving inventory detection
* Demand-supply gap analysis
* Inventory optimization
* Reorder-point analysis
* Executive inventory control tower
* Forecast accuracy analysis
* Purchase planning
* Working-capital analysis
* Inventory investment analytics
* Management alerts
* SKU prioritization
* Interactive dashboard controls

## Technology Stack

* Python
* Pandas
* NumPy
* Scikit-learn
* Plotly
* Streamlit
* Jupyter Notebook

## Project Architecture

```text
FORESIGHT/
│
├── app.py
│
├── data/
│
├── notebooks/
│
├── src/
│   ├── data_loader.py
│   ├── forecast_engine.py
│   ├── intelligence.py
│   ├── kpi_engine.py
│   └── ui.py
│
├── assets/
│
└── docs/
```

## Main Business Questions Answered

FORESIGHT helps answer questions such as:

1. What is the expected future demand?
2. Which SKUs are likely to face stockouts?
3. Which products are overstocked?
4. How much inventory should be replenished?
5. Which products require urgent purchasing?
6. Which SKUs are slow-moving?
7. How efficiently is inventory being utilized?
8. How much working capital is tied up in inventory?
9. Where can inventory capital potentially be released?
10. Which SKUs require management attention?

## Running the Application

Install the required packages:

```bash
pip install -r requirements.txt
```

Run the Streamlit application:

```bash
streamlit run app.py
```

The dashboard will open in the browser.

## Project Objective

The primary objective of FORESIGHT is to transform historical sales and inventory data 
into actionable business intelligence for demand planning, replenishment, inventory optimization, 
and management decision-making.


## Project Status

Completed — 80-step analytical and dashboard development roadmap.
