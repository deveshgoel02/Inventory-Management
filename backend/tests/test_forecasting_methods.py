from app.forecasting import methods


def test_simple_moving_average_uses_recent_window():
    series = [0, 0, 0, 10, 10, 10]
    result = methods.simple_moving_average(series, window=3)
    assert result.daily_rate == 10.0


def test_weighted_moving_average_favours_recent_days():
    series = [10, 10, 0]  # oldest -> newest: heavy early, drops to zero recently
    result = methods.weighted_moving_average(series, window=3)
    # weights 1,2,3 for values 10,10,0 -> (10*1+10*2+0*3)/6 = 5.0
    assert result.daily_rate == 5.0


def test_simple_exponential_smoothing_between_min_and_max():
    series = [5, 5, 5, 20]
    result = methods.simple_exponential_smoothing(series, alpha=0.5)
    assert 5 <= result.daily_rate <= 20


def test_holt_linear_trend_projects_upward_for_growing_series():
    series = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    result = methods.holt_linear_trend(series, horizon_days=10)
    assert result.daily_rate > series[-1] * 0.5  # projects a continued positive trend, not flat/negative


def test_holt_linear_trend_caps_runaway_extrapolation():
    # A single huge spike shouldn't be extrapolated into an implausible trend.
    series = [1] * 20 + [500]
    result = methods.holt_linear_trend(series, horizon_days=30)
    # Capped trend means daily_rate should stay in a sane range, not scale to thousands.
    assert result.daily_rate < 500


def test_backtest_error_metrics_zero_for_perfect_constant_series():
    series = [5.0] * 30
    metrics = methods.backtest_error_metrics(series, methods.simple_moving_average, holdout_days=10)
    assert metrics["mae"] == 0.0
    assert metrics["rmse"] == 0.0
    assert metrics["mape"] == 0.0


def test_backtest_error_metrics_none_when_not_enough_history():
    series = [1.0, 2.0]
    metrics = methods.backtest_error_metrics(series, methods.simple_moving_average, holdout_days=10)
    assert metrics == {"mae": None, "rmse": None, "mape": None}
