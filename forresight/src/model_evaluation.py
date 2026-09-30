import numpy as np


def calculate_wape(y_true, y_pred):
    """
    Calculate Weighted Absolute Percentage Error (WAPE).

    WAPE = sum(|actual - predicted|) / sum(|actual|) * 100
    """

    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)

    denominator = np.sum(np.abs(y_true))

    if denominator == 0:
        return 0.0

    return (np.sum(np.abs(y_true - y_pred)) / denominator) * 100

def seasonal_naive_forecast(
    series,
    season_length=52
):
    """
    Seasonal-naive forecast.
    Uses the value from the same season in the previous cycle.
    """

    series = pd.Series(series).reset_index(drop=True)

    predictions = []

    for i in range(len(series)):

        if i < season_length:

            predictions.append(np.nan)

        else:

            predictions.append(
                series.iloc[i - season_length]
            )

    return pd.Series(predictions)


def evaluate_seasonal_naive(
    weekly_demand,
    season_length=52
):

    weekly_demand = (
        weekly_demand
        .sort_index()
        .astype(float)
    )

    predictions = seasonal_naive_forecast(
        weekly_demand,
        season_length
    )

    evaluation = pd.DataFrame({

        "actual": weekly_demand.values,

        "predicted": predictions.values

    })

    evaluation = evaluation.dropna()

    if evaluation.empty:

        return {
            "wape": np.nan,
            "evaluation": evaluation
        }

    wape = calculate_wape(
        evaluation["actual"],
        evaluation["predicted"]
    )

    return {
        "wape": wape,
        "evaluation": evaluation
    }