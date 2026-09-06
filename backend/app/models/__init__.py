"""Import every model module so Base.metadata is fully populated for Alembic
autogenerate and for Base.metadata.create_all() in tests."""

from app.models import (  # noqa: F401
    allotments,
    analytics,
    audit,
    auth,
    catalog,
    deadlines,
    importing,
    inventory,
    purchasing,
    sales,
    settings,
    warehouse,
)
