import numpy as np


def classify_stockout_risk(stockout_risk_percent):
    if stockout_risk_percent >= 70:
        return "High"
    elif stockout_risk_percent >= 30:
        return "Medium"
    return "Low"


def classify_overstock_risk(weeks_of_supply):
    if weeks_of_supply >= 12:
        return "High"
    elif weeks_of_supply >= 8:
        return "Medium"
    return "Low"


def calculate_action(stockout_risk_percent, weeks_of_supply):

    stockout_high = stockout_risk_percent >= 70
    overstock_high = weeks_of_supply >= 12

    if stockout_high and overstock_high:
        return "Watch / Volatile"

    elif stockout_high:
        return "Reorder Now"

    elif overstock_high:
        return "Markdown / Clear"

    return "Healthy"


def calculate_priority_score(
    stockout_risk_percent,
    weeks_of_supply
):

    stockout_component = np.clip(
        stockout_risk_percent,
        0,
        100
    )

    overstock_component = np.clip(
        (weeks_of_supply - 8) * 10,
        0,
        100
    )

    priority_score = (
        0.60 * stockout_component
        + 0.40 * overstock_component
    )

    return round(float(priority_score), 2)