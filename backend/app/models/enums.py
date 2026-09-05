"""Central place for all domain enums.

Stored as plain strings in the database (not native Postgres ENUM types) so
that adding a new value is a data-only change, never a migration that alters
a type used across many tables.
"""
import enum


class RoleName(str, enum.Enum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    INVENTORY_STAFF = "INVENTORY_STAFF"
    VIEWER = "VIEWER"


class TransactionType(str, enum.Enum):
    OPENING_BALANCE = "OPENING_BALANCE"
    PURCHASE = "PURCHASE"
    SALE = "SALE"
    SALE_RETURN = "SALE_RETURN"
    PURCHASE_RETURN = "PURCHASE_RETURN"
    STOCK_ADJUSTMENT_IN = "STOCK_ADJUSTMENT_IN"
    STOCK_ADJUSTMENT_OUT = "STOCK_ADJUSTMENT_OUT"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"


# Transaction types that increase quantity on hand vs. decrease it.
# Central source of truth for the ledger's sign convention — never infer this
# from the type name as a string prefix/suffix anywhere else in the codebase.
TRANSACTION_DIRECTION: dict[TransactionType, int] = {
    TransactionType.OPENING_BALANCE: +1,
    TransactionType.PURCHASE: +1,
    TransactionType.SALE: -1,
    TransactionType.SALE_RETURN: +1,
    TransactionType.PURCHASE_RETURN: -1,
    TransactionType.STOCK_ADJUSTMENT_IN: +1,
    TransactionType.STOCK_ADJUSTMENT_OUT: -1,
    TransactionType.TRANSFER_IN: +1,
    TransactionType.TRANSFER_OUT: -1,
}


class DeadlineScopeType(str, enum.Enum):
    SKU = "SKU"
    PRODUCT = "PRODUCT"
    BRAND = "BRAND"
    CATEGORY = "CATEGORY"
    WAREHOUSE = "WAREHOUSE"
    BATCH = "BATCH"


class DeadlineStatus(str, enum.Enum):
    NORMAL = "NORMAL"
    APPROACHING = "APPROACHING_DEADLINE"
    DUE = "DUE"
    OVERDUE = "OVERDUE"
    RESOLVED = "RESOLVED"


class AlertSeverity(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertStatus(str, enum.Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class MovementClass(str, enum.Enum):
    FAST_MOVING = "FAST_MOVING"
    HEALTHY = "HEALTHY"
    SLOW_MOVING = "SLOW_MOVING"
    VERY_SLOW = "VERY_SLOW"
    DEAD_STOCK = "DEAD_STOCK"
    NEW_INSUFFICIENT_DATA = "NEW_INSUFFICIENT_DATA"


class ConfidenceLevel(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class PurchaseOrderStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED"
    RECEIVED = "RECEIVED"
    CANCELLED = "CANCELLED"


class ImportJobStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    MAPPED = "MAPPED"
    VALIDATED = "VALIDATED"
    IMPORTED = "IMPORTED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


class ImportTargetEntity(str, enum.Enum):
    SALES = "SALES"
    PURCHASES = "PURCHASES"
    OPENING_STOCK = "OPENING_STOCK"
    PRODUCTS = "PRODUCTS"


class RecommendationStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DISMISSED = "DISMISSED"
