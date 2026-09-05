import datetime

from pydantic import BaseModel


class ForecastRow(BaseModel):
    variant_id: int
    sku: str
    product_name: str
    brand_name: str
    current_stock: int
    historical_avg_daily_sales: float
    recent_avg_daily_sales: float
    forecast_30d: float
    forecast_60d: float
    forecast_90d: float
    recommended_stock_level: float
    suggested_purchase_qty: int
    confidence: str
    risk_level: str
    model_name: str
    reason: str
    mae: float | None = None
    rmse: float | None = None
    mape: float | None = None


class RecommendationOut(BaseModel):
    id: int
    variant_id: int
    sku: str
    product_name: str
    brand_name: str
    generated_at: datetime.datetime
    recommended_order_qty: int
    forecast_demand_lead_time: float
    safety_stock: float
    current_stock: int
    incoming_stock: int
    confidence: str
    risk_level: str
    status: str
    reasoning: dict


class MovementClassificationRow(BaseModel):
    variant_id: int
    sku: str
    product_name: str
    brand_name: str
    classification: str
    sales_velocity_per_day: float
    days_of_cover: float | None
    current_stock: int
    explanation: str


class StockHealthOut(BaseModel):
    variant_id: int
    sku: str
    score: int
    status: str
    factors: list[dict]


class BusinessInsight(BaseModel):
    id: str
    category: str
    severity: str
    text: str
    supporting_data: dict


class DashboardSummary(BaseModel):
    total_skus: int
    total_units_in_stock: int
    total_inventory_cost_value: float
    total_inventory_selling_value: float
    fast_moving_sku_count: int
    slow_moving_sku_count: int
    dead_stock_sku_count: int
    overdue_stock_count: int
    upcoming_deadline_count: int
    open_alert_count: int
    recent_sales_total_30d: float
    recent_purchases_total_30d: float
    data_quality_score: float
