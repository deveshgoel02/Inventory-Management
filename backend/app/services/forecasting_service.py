"""Forecasting orchestration: pulls real historical sales out of the
database, hands them to the pure math in app/forecasting/methods.py, and
persists an explainable ForecastingResult per SKU.

Model selection is entirely a function of how much history exists — never a
fixed model applied blindly to every SKU (see docs/business-rules.md
'Forecast model selection'):

  < MIN_HISTORY_POINTS_FOR_ANY_MODEL days since first sale
      -> NEW_INSUFFICIENT_DATA: no statistical forecast is defensible yet.
  < 90 days of history
      -> simple moving average (a trend/seasonal model would overfit noise
         this early).
  < MIN_HISTORY_MONTHS_FOR_ADVANCED_MODEL months
      -> weighted moving average (more weight on recent demand, still no
         trend extrapolation).
  >= MIN_HISTORY_MONTHS_FOR_ADVANCED_MODEL months
      -> Holt's linear trend (level + trend), capped to prevent runaway
         extrapolation from a short hot/cold streak.

Every result stores its own backtested MAE/RMSE/MAPE against a same-length
naive baseline so accuracy claims are falsifiable, never asserted.
"""
import datetime
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings as app_settings
from app.forecasting import methods
from app.models.analytics import ForecastingResult, ProductSalesHistory
from app.models.catalog import ProductVariant
from app.models.sales import Sale, SaleItem
from app.services import inventory_service

MODEL_VERSION = "1.0.0"


def refresh_sales_history(db: Session) -> int:
    """Rebuilds product_sales_history (daily grain, aggregated across all
    warehouses per SKU) from sale_items + sales. Idempotent: safe to run
    repeatedly (e.g. nightly, or on-demand before a forecast run)."""
    db.query(ProductSalesHistory).delete()

    rows = (
        db.query(
            SaleItem.variant_id,
            Sale.sale_date,
            func.sum(SaleItem.quantity).label("qty"),
            func.sum(SaleItem.quantity * SaleItem.unit_price - SaleItem.discount).label("revenue"),
        )
        .join(Sale, Sale.id == SaleItem.sale_id)
        .group_by(SaleItem.variant_id, Sale.sale_date)
        .all()
    )
    for variant_id, sale_date, qty, revenue in rows:
        db.add(
            ProductSalesHistory(
                variant_id=variant_id,
                warehouse_id=None,
                period_date=sale_date,
                quantity_sold=int(qty or 0),
                revenue=float(revenue or 0),
            )
        )
    db.flush()
    return len(rows)


def get_daily_series(db: Session, variant_id: int, as_of: datetime.date | None = None) -> list[float]:
    """Zero-filled daily quantity-sold series from the first sale date
    through as_of (default today). Zero-filling matters: a SKU that sells 5
    units every Monday and 0 the rest of the week has a very different
    daily rate than one that sells 5/day, and only a zero-filled series
    captures that."""
    as_of = as_of or datetime.date.today()
    history = (
        db.query(ProductSalesHistory)
        .filter(ProductSalesHistory.variant_id == variant_id)
        .order_by(ProductSalesHistory.period_date.asc())
        .all()
    )
    if not history:
        return []

    by_date = {h.period_date: h.quantity_sold for h in history}
    start = history[0].period_date
    series = []
    d = start
    while d <= as_of:
        series.append(float(by_date.get(d, 0)))
        d += datetime.timedelta(days=1)
    return series


def _select_model_and_confidence(span_days: int, series: list[float]):
    min_any = app_settings.MIN_HISTORY_POINTS_FOR_ANY_MODEL
    advanced_days = app_settings.MIN_HISTORY_MONTHS_FOR_ADVANCED_MODEL * 30

    if span_days < min_any:
        return None, "LOW"
    if span_days < 90:
        confidence = "LOW" if span_days < 30 else "MEDIUM"
        return lambda s: methods.simple_moving_average(s), confidence
    if span_days < advanced_days:
        return lambda s: methods.weighted_moving_average(s), "MEDIUM"
    confidence = "HIGH" if span_days >= advanced_days else "MEDIUM"
    return lambda s: methods.holt_linear_trend(s, horizon_days=30), confidence


def _risk_level_from_mape(mape: float | None) -> str:
    if mape is None:
        return "HIGH"
    if mape <= 35:
        return "LOW"
    if mape <= 75:
        return "MEDIUM"
    return "HIGH"


@dataclass
class ForecastOutcome:
    variant_id: int
    span_days: int
    historical_avg_daily_sales: float
    recent_avg_daily_sales: float
    daily_rate: float
    model_name: str
    confidence: str
    risk_level: str
    mae: float | None
    rmse: float | None
    mape: float | None
    explanation: str
    forecasts: dict[int, float]  # horizon_days -> quantity


def run_forecast_for_variant(db: Session, variant_id: int, horizons: list[int] | None = None) -> ForecastOutcome:
    horizons = horizons or app_settings.DEFAULT_FORECAST_HORIZONS_DAYS
    series = get_daily_series(db, variant_id)
    span_days = len(series)
    historical_avg = sum(series) / span_days if span_days else 0.0
    recent_window = min(30, span_days)
    recent_avg = sum(series[-recent_window:]) / recent_window if recent_window else 0.0

    model_fn, confidence = _select_model_and_confidence(span_days, series)

    if model_fn is None:
        explanation = (
            f"Only {span_days} day(s) of sales history exist for this SKU — below the "
            f"{app_settings.MIN_HISTORY_POINTS_FOR_ANY_MODEL}-day minimum for any statistical "
            f"forecast. Showing zero forecast rather than a fabricated number until more "
            f"history accumulates."
        )
        return ForecastOutcome(
            variant_id=variant_id,
            span_days=span_days,
            historical_avg_daily_sales=round(historical_avg, 4),
            recent_avg_daily_sales=round(recent_avg, 4),
            daily_rate=0.0,
            model_name="insufficient_data",
            confidence="LOW",
            risk_level="HIGH",
            mae=None,
            rmse=None,
            mape=None,
            explanation=explanation,
            forecasts={h: 0.0 for h in horizons},
        )

    components = model_fn(series)

    holdout = min(14, max(0, span_days // 3))
    metrics = methods.backtest_error_metrics(series, model_fn, holdout) if holdout > 0 else {
        "mae": None, "rmse": None, "mape": None
    }
    naive_metrics = (
        methods.backtest_error_metrics(series, lambda s: methods.simple_moving_average(s, window=7), holdout)
        if holdout > 0
        else {"mae": None, "rmse": None, "mape": None}
    )

    risk_level = _risk_level_from_mape(metrics["mape"])

    trend_pct = None
    if span_days >= 14:
        first_half = series[: span_days // 2]
        second_half = series[span_days // 2 :]
        fh_avg = sum(first_half) / len(first_half) if first_half else 0
        sh_avg = sum(second_half) / len(second_half) if second_half else 0
        if fh_avg > 0:
            trend_pct = round(100 * (sh_avg - fh_avg) / fh_avg, 1)

    explanation_parts = [
        f"Model: {components.model_name.replace('_', ' ')} (selected because {span_days} days of "
        f"history are available).",
        f"Average daily sales over full history: {historical_avg:.2f} units/day; "
        f"last {recent_window} days: {recent_avg:.2f} units/day.",
    ]
    if trend_pct is not None:
        direction = "increased" if trend_pct >= 0 else "decreased"
        explanation_parts.append(f"Sales {direction} {abs(trend_pct):.0f}% comparing the first vs. second half of history.")
    if metrics["mape"] is not None:
        explanation_parts.append(
            f"Backtested accuracy over the most recent {holdout} days: MAPE {metrics['mape']:.0f}%, "
            f"MAE {metrics['mae']:.2f} units/day (naive baseline MAPE: "
            f"{naive_metrics['mape'] if naive_metrics['mape'] is not None else 'n/a'})."
        )
    explanation = " ".join(explanation_parts)

    forecasts = {h: round(components.daily_rate * h, 1) for h in horizons}

    return ForecastOutcome(
        variant_id=variant_id,
        span_days=span_days,
        historical_avg_daily_sales=round(historical_avg, 4),
        recent_avg_daily_sales=round(recent_avg, 4),
        daily_rate=components.daily_rate,
        model_name=components.model_name,
        confidence=confidence,
        risk_level=risk_level,
        mae=metrics["mae"],
        rmse=metrics["rmse"],
        mape=metrics["mape"],
        explanation=explanation,
        forecasts=forecasts,
    )


def persist_forecast(db: Session, outcome: ForecastOutcome, horizon_days: int) -> ForecastingResult:
    result = ForecastingResult(
        variant_id=outcome.variant_id,
        model_name=outcome.model_name,
        model_version=MODEL_VERSION,
        generated_at=datetime.datetime.now(datetime.timezone.utc),
        horizon_days=horizon_days,
        forecast_quantity=outcome.forecasts.get(horizon_days, 0.0),
        historical_avg_daily_sales=outcome.historical_avg_daily_sales,
        recent_avg_daily_sales=outcome.recent_avg_daily_sales,
        confidence=outcome.confidence,
        mae=outcome.mae,
        rmse=outcome.rmse,
        mape=outcome.mape,
        parameters_json={"span_days": outcome.span_days},
        explanation=outcome.explanation,
    )
    db.add(result)
    db.flush()
    return result


def run_forecast_all_variants(db: Session, horizons: list[int] | None = None) -> list[ForecastOutcome]:
    variant_ids = [v.id for v in db.query(ProductVariant.id).filter(ProductVariant.is_active.is_(True)).all()]
    outcomes = []
    for variant_id in variant_ids:
        outcome = run_forecast_for_variant(db, variant_id, horizons)
        outcomes.append(outcome)
        for h in outcome.forecasts:
            persist_forecast(db, outcome, h)
    return outcomes
