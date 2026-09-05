"""Pure, deterministic forecasting math — no database access, no I/O, so it
can be unit tested directly against known inputs/outputs.

All methods take a daily time series (list of floats, zero-filled for days
with no sales) and return a projected constant daily rate, which the caller
multiplies by the horizon length. This mirrors how a demand planner would
reason about it: "what is the expected average daily demand going forward,"
not a day-by-day curve (footwear retail demand at SKU grain is too noisy for
day-level curve fitting to be meaningful without far more history).
"""
import math
from dataclasses import dataclass


@dataclass
class ForecastComponents:
    daily_rate: float
    model_name: str
    parameters: dict


def simple_moving_average(series: list[float], window: int | None = None) -> ForecastComponents:
    window = window or len(series)
    window = min(window, len(series)) or 1
    tail = series[-window:] if series else [0.0]
    rate = sum(tail) / len(tail)
    return ForecastComponents(daily_rate=rate, model_name="simple_moving_average", parameters={"window": window})


def weighted_moving_average(series: list[float], window: int | None = None) -> ForecastComponents:
    """Linearly increasing weights so the most recent day counts most —
    more responsive to a recent demand shift than a plain SMA."""
    window = window or min(30, len(series))
    window = min(window, len(series)) or 1
    tail = series[-window:] if series else [0.0]
    weights = list(range(1, len(tail) + 1))
    weighted_sum = sum(v * w for v, w in zip(tail, weights))
    rate = weighted_sum / sum(weights) if weights else 0.0
    return ForecastComponents(
        daily_rate=rate, model_name="weighted_moving_average", parameters={"window": window}
    )


def simple_exponential_smoothing(series: list[float], alpha: float = 0.3) -> ForecastComponents:
    if not series:
        return ForecastComponents(0.0, "simple_exponential_smoothing", {"alpha": alpha})
    level = series[0]
    for value in series[1:]:
        level = alpha * value + (1 - alpha) * level
    return ForecastComponents(daily_rate=level, model_name="simple_exponential_smoothing", parameters={"alpha": alpha})


def holt_linear_trend(series: list[float], alpha: float = 0.3, beta: float = 0.1, horizon_days: int = 30) -> ForecastComponents:
    """Holt's double exponential smoothing (level + trend). Returns the
    *average* projected daily rate over the requested horizon (not just the
    day-1 rate), and clamps the trend so a short hot streak can't
    extrapolate into an implausible runaway number — the projected level is
    floored at 0 and the per-step trend contribution is capped at +/-20% of
    the current level."""
    if len(series) < 2:
        return simple_exponential_smoothing(series, alpha)

    level = series[0]
    trend = series[1] - series[0]
    for value in series[1:]:
        prev_level = level
        level = alpha * value + (1 - alpha) * (level + trend)
        trend = beta * (level - prev_level) + (1 - beta) * trend

    max_step = abs(level) * 0.2 + 0.01
    trend = max(-max_step, min(max_step, trend))

    daily_rates = []
    for h in range(1, horizon_days + 1):
        projected = max(0.0, level + trend * h)
        daily_rates.append(projected)
    avg_rate = sum(daily_rates) / len(daily_rates) if daily_rates else 0.0

    return ForecastComponents(
        daily_rate=avg_rate,
        model_name="holt_linear_trend",
        parameters={"alpha": alpha, "beta": beta, "level": level, "trend": trend},
    )


def backtest_error_metrics(
    series: list[float], forecast_fn, holdout_days: int
) -> dict[str, float | None]:
    """Fits `forecast_fn` on series[:-holdout_days], predicts a constant
    daily rate, compares against the actual held-out days. Returns MAE,
    RMSE, and MAPE (None where the actuals are all zero, since MAPE is
    undefined in that case)."""
    if holdout_days <= 0 or len(series) <= holdout_days:
        return {"mae": None, "rmse": None, "mape": None}

    train = series[:-holdout_days]
    actual = series[-holdout_days:]
    if not train:
        return {"mae": None, "rmse": None, "mape": None}

    predicted_rate = forecast_fn(train).daily_rate
    errors = [predicted_rate - a for a in actual]
    mae = sum(abs(e) for e in errors) / len(errors)
    rmse = math.sqrt(sum(e * e for e in errors) / len(errors))

    nonzero_actuals = [a for a in actual if a > 0]
    if nonzero_actuals:
        mape_terms = [abs(predicted_rate - a) / a for a in actual if a > 0]
        mape = 100 * sum(mape_terms) / len(mape_terms)
    else:
        mape = None

    return {"mae": round(mae, 4), "rmse": round(rmse, 4), "mape": round(mape, 4) if mape is not None else None}
