# Business Rules & Calculation Methodology

This document explains, in plain language, exactly how every number on the
Shoe Xpress Inventory Intelligence platform is calculated. If a dashboard
figure looks wrong, this is the first place to check — every rule below
corresponds directly to code in `backend/app/services/`.

---

## 1. How current stock is calculated

**There is no "current stock" column anywhere in the database.** Stock on
hand is always computed live by summing signed quantities from the
`inventory_transactions` ledger table (`app/services/inventory_service.py`):

```
current_stock(SKU, warehouse) = SUM(±quantity) over all inventory_transactions
                                  for that SKU/warehouse
```

Each transaction type has a fixed direction (never inferred from the name at
runtime — see `TRANSACTION_DIRECTION` in `app/models/enums.py`):

| Type | Direction | Type | Direction |
|---|---|---|---|
| OPENING_BALANCE | + | SALE | − |
| PURCHASE | + | PURCHASE_RETURN | − |
| SALE_RETURN | + | STOCK_ADJUSTMENT_OUT | − |
| STOCK_ADJUSTMENT_IN | + | TRANSFER_OUT | − |
| TRANSFER_IN | + | | |

A sale is rejected with a clear error if it would drive stock negative
(unless explicitly flagged as a historical import, since old spreadsheets
sometimes contain sequencing gaps). This makes stock numbers fully
auditable: every unit can be traced back to the transaction(s) that put it
there, and `GET /api/inventory/ledger/{variant_id}` shows the complete
history for any SKU.

## 2. Inventory aging

Age is computed **per receiving batch**, not per SKU — a SKU with multiple
lots received at different times can straddle several aging buckets
simultaneously. For a batch with remaining quantity > 0:

```
age_days = as_of_date − batch.received_date
```

Buckets are configurable (`business_settings.aging_buckets_days`, default
`[30, 60, 90, 180, 365, 730]` producing 0–30, 31–60, 61–90, 91–180,
181–365, 366–730, and 731+ day buckets). Change them from Settings without
a code deploy.

## 3. Movement classification (fast / slow / dead stock)

Computed in `app/services/classification_service.py` from each SKU's actual
sales history — never fixed thresholds applied blindly:

1. **NEW_INSUFFICIENT_DATA** — fewer than `MIN_HISTORY_POINTS_FOR_ANY_MODEL`
   (default 6) days of history exist. No classification is attempted.
2. **DEAD_STOCK** — stock on hand > 0 and no sale recorded in the last
   `dead_stock_no_sale_days` (default 180) days.
3. Otherwise, **days of cover** = current_stock ÷ recent 30-day average daily
   sales, and the SKU is classified by configurable thresholds:
   - `days_of_cover ≤ fast_mover_days_of_cover_max` (default 21) → **FAST_MOVING**
   - `days_of_cover ≥ very_slow_mover_days_of_cover_min` (default 240) → **VERY_SLOW**
   - `days_of_cover ≥ slow_mover_days_of_cover_min` (default 120) → **SLOW_MOVING**
   - otherwise → **HEALTHY**

Every classification returned by the API includes the exact numbers used
(`sales_velocity_per_day`, `days_of_cover`) and a plain-English explanation.

## 4. Forecast model selection

`app/services/forecasting_service.py` picks a model based on how much daily
sales history exists for a SKU (`app/forecasting/methods.py` has the pure
math, unit-tested in isolation):

| History available | Model used | Why |
|---|---|---|
| < 6 days | None — "insufficient data" | Any statistical forecast would be fabricated |
| 6–89 days | Simple moving average | Too little history to trust a trend/seasonal fit |
| 90 days – 12 months | Weighted moving average | More weight on recent demand, still no trend extrapolation |
| ≥ 12 months | Holt's linear trend (level + trend) | Enough history to project a trend, capped at ±20%/day to prevent a short hot streak from extrapolating into an implausible number |

The daily series is **zero-filled** — days with no sale count as zero
demand — because a SKU that sells 5 units every Monday behaves very
differently from one that sells steadily at 5/day, and only a zero-filled
series captures that difference.

## 5. Forecast confidence & accuracy

**Confidence** reflects how much history backs the model (LOW/MEDIUM/HIGH,
per the table above). **Risk level** is separate: it reflects the model's
own backtested accuracy, not just how much data exists — a SKU can have
HIGH confidence (lots of history) but MEDIUM/HIGH risk (that history is
volatile and hard to predict).

Every forecast is backtested: the model is fit on all history except the
most recent `min(14, span/3)` days, used to predict those held-out days,
and compared against what actually happened using MAE, RMSE, and MAPE — the
same metrics are computed for a naive 7-day-average baseline so "is this
model actually better than doing nothing clever" is always answerable, not
assumed.

```
risk_level: MAPE ≤ 35%  → LOW
            MAPE ≤ 75%  → MEDIUM
            otherwise / unavailable → HIGH
```

## 6. Purchase recommendation formula

`app/services/recommendation_service.py`:

```
Suggested Order Quantity =
    max(0, ForecastDemandDuringLeadTime + SafetyStock
            − CurrentStock − IncomingStock)
```

- `ForecastDemandDuringLeadTime = daily_sales_rate × supplier_lead_time_days`
  (lead time comes from the SKU's most recent purchase order's supplier, or
  the configurable `default_lead_time_days` setting if none exists).
- `SafetyStock = daily_sales_rate × safety_stock_days` (configurable,
  default 14 days).
- `IncomingStock` = quantity already on open (SENT/PARTIALLY_RECEIVED)
  purchase orders for that SKU.
- The result is rounded **up** to the nearest multiple of the SKU's minimum
  order quantity, if one is set.

Every recommendation stores every one of these numbers in `reasoning`, so
"why 200 units?" always has a concrete, inspectable answer. Recommendations
are never auto-converted into purchase orders — a human always reviews and
explicitly accepts or dismisses each one.

## 7. Stock health score (0–100, fully transparent)

`app/services/stock_health_service.py` — four weighted, individually
explained factors, never a black-box composite:

| Factor | Max points | Basis |
|---|---|---|
| Movement classification | 40 | FAST_MOVING=40, HEALTHY=32, SLOW_MOVING=20, VERY_SLOW=8, DEAD_STOCK=0, NEW=20 |
| Inventory aging | 25 | Linear falloff from 25 (0 days old) to 0 (≥730 days), stock-weighted |
| Deadline proximity | 20 | NORMAL=20, APPROACHING=12, DUE=5, OVERDUE=0 (20 if no deadline applies) |
| Sales trend | 15 | Ratio of recent 30-day average to full-history average |

Score bands: ≥75 **Healthy**, 50–74 **Watch**, 25–49 **At Risk**, <25
**Critical**. The API always returns the per-factor breakdown alongside the
score.

## 8. Stock deadlines & alert escalation

Deadline status is recomputed from `deadline_date`, `warning_days`, and
today's date on every read (never trusted from a stale stored value):

- `days_remaining < 0` → **OVERDUE**
- `days_remaining == 0` → **DUE**
- `days_remaining ≤ warning_days` → **APPROACHING_DEADLINE**
- otherwise → **NORMAL**

Escalation level increases as `days_remaining` crosses configurable
thresholds (`deadline_escalation_days`, default `[7, 3, 0]`), plus one more
level once overdue.

**Alert de-duplication**: alerts are keyed by
`{alert_type}:{entity_type}:{entity_id}`. A condition that stays true for
weeks produces exactly one alert row (refreshed in place), not one per
check — see `app/services/alert_service.py`.

## 9. Data quality score

`app/services/data_quality_service.py` runs a fixed set of checks (missing
category, missing cost/price, sale items missing cost, duplicate barcodes,
stock adjustments with no notes) and applies a documented penalty per issue
type:

```
score = max(0, 100 − Σ(issue_count × weight))
```

Weights range from 0.3 (a missing cost on one sale line) to 2.0 (a
duplicate barcode). Every issue is returned with a link back to the
specific record, never just a bare count.

## 10. Historical data import validation

`app/importing/column_mapping.py` maps arbitrary spreadsheet headers onto a
fixed set of canonical fields per import target (Sales / Purchases /
Opening Stock / Products) using an alias dictionary plus fuzzy matching —
"Product Code", "Item Code", "Style Code", and "SKU" all resolve to the same
canonical `sku` field. Nothing is written to business tables until:

1. The user reviews/edits the suggested mapping.
2. Every row is validated (missing SKU, invalid date, non-positive
   quantity, malformed/negative price, unknown SKU, in-file duplicates) and
   the user sees the exact counts and per-row error list.
3. The user explicitly clicks "Confirm & Import."

Rows with errors are skipped, not corrected silently. A duplicate is a row
whose (type-specific) key fields exactly match an earlier row in the same
file. Unknown brands referenced by a PRODUCTS import are created
automatically but flagged as a warning so the user notices.

## 11. Role-based access control

Four roles (`app/auth/permissions.py`): **ADMIN** (everything),
**MANAGER** (everything except user management), **INVENTORY_STAFF**
(view + adjust stock + record sales/receipts + run imports/exports),
**VIEWER** (view + export only). Every API route checks the permission
server-side via `require_permission(...)` — the frontend hiding a button is
a UX convenience, never the actual security boundary.

## 12. Currency & business configuration

Currency (`INR`/`₹` by default), aging buckets, forecast horizons, lead
times, safety-stock days, and movement-classification thresholds are all
rows in the `business_settings` table, editable from Settings without a
code deploy. Nothing above is hard-coded in route or service logic beyond a
bootstrap default used only the first time the table is seeded.

## 13. Documented assumptions

- **SKU = product_variant.** The spec's "product_variants" and "SKUs" are
  modeled as one table: a SKU is a specific size/color combination of a
  product. This avoids a redundant join for the most common query pattern
  (every inventory/sales/purchasing operation is at this grain).
- **Forecasting is company-wide per SKU**, not per-warehouse. A footwear
  distributor's demand planning is normally done at the SKU level across
  the business; warehouse-level stock allocation is a separate, physical
  concern already handled by the ledger being warehouse-aware.
- **Demo data is seeded with a fixed random seed** (42) so it is
  reproducible, and every demo row is flagged `is_demo=True` — real
  business data entered later is never at risk of being confused with it.
