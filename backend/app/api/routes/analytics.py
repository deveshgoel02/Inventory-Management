from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import require_permission
from app.core.database import get_db
from app.models.analytics import AIRecommendation
from app.models.auth import User
from app.models.catalog import ProductVariant
from app.schemas.analytics import DashboardSummary
from app.services import (
    classification_service,
    dashboard_service,
    data_quality_service,
    forecasting_service,
    insights_service,
    recommendation_service,
    stock_health_service,
)

router = APIRouter(prefix="/api", tags=["analytics"])


@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db), _: User = Depends(require_permission("inventory:view"))):
    return dashboard_service.compute_dashboard_summary(db)


@router.get("/insights")
def business_insights(db: Session = Depends(get_db), _: User = Depends(require_permission("ai:view"))):
    return insights_service.generate_all_insights(db)


@router.get("/data-quality")
def data_quality(db: Session = Depends(get_db), _: User = Depends(require_permission("inventory:view"))):
    return data_quality_service.run_data_quality_checks(db)


@router.get("/classification")
def movement_classification(db: Session = Depends(get_db), _: User = Depends(require_permission("ai:view"))):
    return classification_service.classify_all_variants(db)


@router.get("/stock-health/{variant_id}")
def stock_health(variant_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("ai:view"))):
    try:
        return stock_health_service.compute_stock_health(db, variant_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/forecasting/refresh")
def refresh_forecasts(db: Session = Depends(get_db), user: User = Depends(require_permission("ai:manage"))):
    forecasting_service.refresh_sales_history(db)
    outcomes = forecasting_service.run_forecast_all_variants(db)
    db.commit()
    return {"variants_forecasted": len(outcomes)}


@router.get("/forecasting/{variant_id}")
def get_forecast(variant_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("ai:view"))):
    variant = db.get(ProductVariant, variant_id)
    if not variant:
        raise HTTPException(404, "SKU not found")
    forecasting_service.refresh_sales_history(db)
    outcome = forecasting_service.run_forecast_for_variant(db, variant_id)
    db.commit()
    return {
        "variant_id": variant_id,
        "sku": variant.sku,
        "model_name": outcome.model_name,
        "confidence": outcome.confidence,
        "risk_level": outcome.risk_level,
        "historical_avg_daily_sales": outcome.historical_avg_daily_sales,
        "recent_avg_daily_sales": outcome.recent_avg_daily_sales,
        "forecasts": outcome.forecasts,
        "mae": outcome.mae,
        "rmse": outcome.rmse,
        "mape": outcome.mape,
        "explanation": outcome.explanation,
    }


@router.post("/recommendations/generate")
def generate_recommendations(db: Session = Depends(get_db), user: User = Depends(require_permission("ai:manage"))):
    forecasting_service.refresh_sales_history(db)
    recs = recommendation_service.generate_recommendations_for_all(db)
    db.commit()
    return {"recommendations_generated": len(recs)}


@router.get("/recommendations")
def list_recommendations(status: str | None = None, db: Session = Depends(get_db), _: User = Depends(require_permission("ai:view"))):
    query = db.query(AIRecommendation)
    if status:
        query = query.filter(AIRecommendation.status == status)
    recs = query.order_by(AIRecommendation.generated_at.desc()).limit(500).all()
    result = []
    for r in recs:
        variant = r.variant_id and db.get(ProductVariant, r.variant_id)
        result.append(
            {
                "id": r.id,
                "variant_id": r.variant_id,
                "sku": variant.sku if variant else None,
                "product_name": variant.product.name if variant else None,
                "brand_name": variant.product.brand.name if variant else None,
                "generated_at": r.generated_at,
                "recommended_order_qty": r.recommended_order_qty,
                "forecast_demand_lead_time": float(r.forecast_demand_lead_time),
                "safety_stock": float(r.safety_stock),
                "current_stock": r.current_stock,
                "incoming_stock": r.incoming_stock,
                "confidence": r.confidence,
                "risk_level": r.risk_level,
                "status": r.status,
                "reasoning": r.reasoning,
            }
        )
    return result


@router.post("/recommendations/{recommendation_id}/review")
def review_recommendation(
    recommendation_id: int, decision: str, db: Session = Depends(get_db), user: User = Depends(require_permission("ai:manage"))
):
    if decision.upper() not in ("ACCEPTED", "DISMISSED"):
        raise HTTPException(400, "decision must be ACCEPTED or DISMISSED")
    rec = db.get(AIRecommendation, recommendation_id)
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    import datetime

    rec.status = decision.upper()
    rec.reviewed_by = user.id
    rec.reviewed_at = datetime.datetime.now(datetime.timezone.utc)
    db.commit()
    return {"id": rec.id, "status": rec.status}
