# Shoe Xpress Inventory Intelligence

A production-grade inventory management and sales intelligence platform for
Shoe Xpress, a footwear distribution business (Skechers, Reebok, adidas,
Wildcraft). Built to be the authoritative source of truth for stock,
sales, aging, deadlines, and AI-assisted purchasing decisions — not a demo.

See **[docs/business-rules.md](docs/business-rules.md)** for exactly how
every number (stock, aging, forecast, recommendation, stock health score,
data quality score) is calculated. Read that before trusting or explaining
any figure the app shows.

## Architecture

```
/backend    FastAPI + SQLAlchemy + Alembic + Pydantic (Python 3.14)
/frontend   React 19 + TypeScript + Vite + Tailwind CSS v4 + Recharts
/docs       Business rules and calculation methodology
/docker     Optional docker-compose for local PostgreSQL
```

**Backend layers** (`backend/app/`):
- `api/routes/` — FastAPI routers, one per domain (auth, catalog, inventory,
  sales, purchasing, deadlines, analytics, imports, reports, settings,
  users, audit). Routes stay thin: they validate input, call a service, and
  return a schema.
- `services/` — all business logic and calculations (inventory ledger,
  forecasting, recommendations, aging, classification, stock health,
  data quality, insights, imports, audit, alerts).
- `forecasting/` — pure, dependency-free forecasting math, unit tested in
  isolation from the database.
- `importing/` — the reusable column-mapping engine and tolerant value
  parsers for the historical data import pipeline.
- `models/` — SQLAlchemy ORM models (the 27-table schema below).
- `schemas/` — Pydantic request/response models.
- `auth/` — JWT issuance/verification, password hashing, and the
  permission-based RBAC dependency used by every protected route.

**Frontend** (`frontend/src/`): `pages/` (one per nav item), `components/`
(Layout, StatCard, Badge, PageHeader, ProtectedRoute), `api/` (typed axios
client + TS interfaces mirroring the backend schemas), `state/`
(AuthContext), `lib/` (currency/date formatting).

## Database schema

27 tables covering users/roles/permissions, brands/categories/products/
product_variants (SKUs), warehouses/inventory_locations,
inventory_batches/inventory_transactions/stock_receipts(+items), sales(+items)
/customers, suppliers/purchase_orders(+items), stock_deadlines/alerts,
product_sales_history/forecasting_results/ai_recommendations,
data_import_jobs, audit_logs, business_settings. Managed with Alembic
migrations (`backend/alembic/versions/`) — never hand-edit the schema.

The **inventory ledger** (`inventory_transactions`) is the single source of
truth for stock on hand; nothing stores a mutable "current stock" number.
See business-rules.md §1.

## Prerequisites

- Python 3.11+ (developed and tested on 3.14)
- Node.js 20+ / npm
- SQLite (bundled with Python — zero setup) for local development.
  PostgreSQL for production (`docker/docker-compose.yml` provides a local
  instance if you want to test against it before deploying).

## Setup

### Backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env        # Windows; use `cp` on macOS/Linux — then edit SECRET_KEY

alembic upgrade head           # creates/updates the database schema
python scripts/seed_demo_data.py   # optional: realistic demo data, clearly flagged is_demo=True

uvicorn app.main:app --reload --port 8000
```

The API is now at `http://127.0.0.1:8000` (interactive docs at `/docs`). A
bootstrap admin account is created automatically on first run:
`admin@shoexpress.co.in` / `ChangeMe123!` (override via `INITIAL_ADMIN_EMAIL`
/ `INITIAL_ADMIN_PASSWORD` env vars before the first run) — **change this
password immediately in any real deployment.**

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite dev server proxies `/api/*` to
`http://127.0.0.1:8000`, so no CORS configuration is needed in development.

## Running tests

```bash
cd backend
pytest -q
```

34 tests cover: inventory ledger math (opening balance, sales, returns,
adjustments, insufficient-stock rejection, per-warehouse isolation),
forecasting math (each model + backtesting), the column-mapping engine,
tolerant value parsing (dates/quantities/prices, including the exact
malformed-input cases a real spreadsheet produces), RBAC (permission
enforcement, role-based rejection), deadline status/escalation logic, and a
full end-to-end API simulation (create product → SKU → receive → sell →
return → adjust → oversell-rejected → deadline → aging → forecast →
recommendation → export → audit trail).

## Importing your first real historical dataset

Do **not** hand this straight to a bulk-insert script. Use the Import
Center (`/imports` in the UI, or `POST /api/imports/jobs`):

1. Upload the spreadsheet and pick a target: Sales, Purchases, Opening
   Stock, or Products/SKUs.
2. The column-mapping engine proposes a mapping (it recognizes common
   aliases like "Product Code" / "Item Code" / "Style Code" for `sku`) —
   review and correct it.
3. Validate. You get exact counts of valid/invalid/duplicate rows and a
   per-row error list (missing SKU, invalid date, negative quantity,
   malformed price, unknown SKU, in-file duplicate).
4. Only after you explicitly confirm does anything get written — inside a
   single transaction, so a failure partway through rolls back completely
   rather than leaving a half-imported dataset.

If your data references brands/products that don't exist in **Products**
imports, they're created automatically (flagged as a warning so you notice)
— but **Sales/Purchases/Opening Stock imports require the SKU to already
exist**, so import Products first for genuinely new SKUs.

See business-rules.md §10 for the exact validation rules.

## Backups & data safety

- SQLite (dev): back up by copying `backend/shoexpress.db` while the server
  is stopped (or use `sqlite3 shoexpress.db ".backup backup.db"` for a
  live, consistent snapshot).
- PostgreSQL (production): use `pg_dump`/`pg_restore` on a regular schedule;
  keep at least 30 days of daily backups given this data drives purchasing
  decisions.
- All master data uses soft deletion (`is_active` flag) — nothing is
  hard-deleted through the API. The `audit_logs` table is append-only and
  is never written to by anything except `audit_service.log_action`.
- Every stock-affecting operation goes through `record_transaction`, which
  runs inside the request's database transaction — a failure partway
  through a multi-item sale or receipt rolls back entirely.

## Known limitations / not yet built

- **PDF export** is not implemented (CSV and Excel are). Recharts-based
  in-app charts can be screenshotted in the interim.
- **Email/WhatsApp/SMS notifications** are not wired up; the alert system
  is in-app only, but its data model (`alerts` table + `alert_service`) is
  already structured so a notification channel can subscribe to new/updated
  alerts without changing business logic.
- **Barcode scanner integration** is prepared for (every SKU has a
  `barcode` field, and search-by-barcode works on the Inventory/Sales SKU
  lookups) but no physical scanner has been tested against it.
- **Warehouse-level (rather than company-wide) forecasting** is not
  implemented — see the documented assumption in business-rules.md §13.
- **PO receiving against a purchase order** currently happens via the
  separate Stock Receipt endpoint rather than a "receive against this PO"
  action that auto-updates `quantity_received` on `purchase_order_items` —
  the data model supports it (`stock_receipts.purchase_order_id`) but the
  linking UI/logic is not yet built.
- The bundled Vite production build is a single ~700KB JS chunk (code
  splitting via route-based `React.lazy` would reduce initial load time but
  wasn't prioritized over functional completeness this pass).

## Recommended next priorities

1. Wire PO receiving to auto-decrement `quantity_ordered` outstanding.
2. Add PDF export (e.g. via a headless-Chromium or ReportLab pass over the
   same `report_service.build_report_rows` data).
3. Route-based code splitting on the frontend.
4. A scheduled job (cron/Celery/APScheduler) to run
   `forecasting_service.refresh_sales_history` +
   `run_forecast_all_variants` + `deadline_service.refresh_all_deadline_statuses`
   nightly, instead of only on-demand via the API.
5. Notification channel adapters (email/WhatsApp) subscribing to the
   existing `alerts` table.
