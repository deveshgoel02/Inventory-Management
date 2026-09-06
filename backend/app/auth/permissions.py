"""Canonical permission codes and the default role -> permission matrix.

This is the single source of truth seeded into the `permissions` and
`role_permissions` tables at bootstrap time. Both API routes (via the
`require_permission` dependency) and the frontend (which reads the current
user's permission list from /auth/me) key off these exact string codes —
never off role name directly, so that permissions can be fine-tuned per role
later without changing route code.
"""

PERMISSIONS: dict[str, str] = {
    "inventory:view": "View inventory levels, ledger, and aging",
    "inventory:adjust": "Create manual stock adjustments",
    "product:view": "View brands, categories, products, SKUs",
    "product:manage": "Create/edit/deactivate brands, categories, products, SKUs",
    "sales:view": "View sales records",
    "sales:create": "Record new sales and returns",
    "allotment:view": "View salesman quantity allotments and their execution progress",
    "allotment:manage": "Assign and cancel salesman quantity allotments",
    "purchase:view": "View suppliers and purchase orders",
    "purchase:manage": "Create/edit suppliers, purchase orders, stock receipts",
    "import:run": "Upload and commit data import jobs",
    "export:run": "Export reports (CSV/Excel/PDF)",
    "deadline:manage": "Create/edit stock deadlines",
    "alert:manage": "Acknowledge/resolve alerts",
    "ai:view": "View forecasts and purchase recommendations",
    "ai:manage": "Adjust forecasting/recommendation configuration",
    "user:manage": "Create/edit users and role assignments",
    "settings:manage": "Edit business settings (aging rules, brands, warehouses, etc.)",
    "audit:view": "View the audit log",
}

_ALL = list(PERMISSIONS.keys())
_VIEW_ONLY = [p for p in _ALL if p.endswith(":view")] + ["export:run"]
_OPERATIONAL = [
    "inventory:view",
    "inventory:adjust",
    "product:view",
    "sales:view",
    "sales:create",
    "allotment:view",
    "purchase:view",
    "import:run",
    "export:run",
    "ai:view",
]
_MANAGERIAL = [p for p in _ALL if p not in ("user:manage",)]

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "ADMIN": _ALL,
    "MANAGER": _MANAGERIAL,
    "INVENTORY_STAFF": _OPERATIONAL,
    "VIEWER": _VIEW_ONLY,
}
