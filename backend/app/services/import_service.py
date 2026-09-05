"""Import workflow orchestration: upload -> map columns -> validate ->
preview -> confirm -> commit -> report.

Nothing is written to business tables before `commit_job` is explicitly
called by the user after reviewing the validation report (spec: "Do NOT
blindly insert imported rows"). `commit_job` runs inside a single DB
transaction — if anything raises partway through, the whole import rolls
back rather than leaving a half-imported dataset.
"""
import datetime
from collections import defaultdict

from sqlalchemy.orm import Session

from app.importing import column_mapping, parsers
from app.importing.value_parsing import clean_text, parse_date, parse_price, parse_quantity
from app.models.catalog import Brand, Category, Product, ProductVariant
from app.models.importing import DataImportJob
from app.models.inventory import InventoryBatch
from app.models.purchasing import Supplier
from app.models.sales import Customer, Sale, SaleItem
from app.models.warehouse import Warehouse
from app.services import inventory_service
from app.services.inventory_service import InsufficientStockError, TransactionRequest
from app.models.enums import TransactionType


class ImportError_(Exception):
    pass


def create_import_job(
    db: Session, *, filename: str, content: bytes, target_entity: str | None, user_id: int | None
) -> DataImportJob:
    """`target_entity=None` (or "AUTO") auto-detects Sales vs. Purchases vs.
    Opening Stock vs. Products from the file's own column headers — a
    distributor's sales file and purchases file are never ambiguous with
    each other (one has a cost column, the other a price column), so the
    user shouldn't have to say which is which up front."""
    headers, rows = parsers.parse_upload(filename, content)
    if not rows:
        raise ImportError_("The uploaded file contains no data rows.")

    if target_entity in (None, "AUTO"):
        target_entity, suggested = column_mapping.detect_target_entity(headers)
    else:
        if target_entity not in column_mapping.ENTITY_FIELDS:
            raise ImportError_(f"Unknown import target: {target_entity}")
        suggested = column_mapping.suggest_mapping(headers, target_entity)

    job = DataImportJob(
        filename=filename,
        target_entity=target_entity,
        uploaded_by=user_id,
        uploaded_at=datetime.datetime.now(datetime.timezone.utc),
        status="UPLOADED",
        column_mapping={field: info["header"] for field, info in suggested.items()},
        total_rows=len(rows),
        raw_rows_cache={"headers": headers, "rows": rows},
    )
    db.add(job)
    db.flush()
    return job


def get_suggested_mapping(job: DataImportJob) -> dict:
    headers = job.raw_rows_cache["headers"]
    return column_mapping.suggest_mapping(headers, job.target_entity)


def set_mapping(db: Session, job: DataImportJob, mapping: dict[str, str | None]) -> DataImportJob:
    errors = column_mapping.validate_mapping_complete(mapping, job.target_entity)
    if errors:
        raise ImportError_("; ".join(errors))
    job.column_mapping = mapping
    job.status = "MAPPED"
    db.flush()
    return job


def _extract(row: dict, mapping: dict[str, str | None], field: str) -> str | None:
    header = mapping.get(field)
    if not header:
        return None
    return row.get(header)


def validate_job(db: Session, job: DataImportJob) -> DataImportJob:
    if job.column_mapping is None:
        raise ImportError_("Column mapping must be set before validation.")

    rows = job.raw_rows_cache["rows"]
    mapping = job.column_mapping
    target = job.target_entity

    known_skus = {v.sku for v in db.query(ProductVariant.sku).all()}
    known_brands = {b.name.lower() for b in db.query(Brand.name).all()}
    known_warehouses = {w.code.lower(): w.id for w in db.query(Warehouse.code, Warehouse.id).all()}

    seen_dedupe_keys: set[tuple] = set()
    row_reports = []
    valid_count = 0
    invalid_count = 0
    duplicate_count = 0
    parsed_rows = []

    for idx, row in enumerate(rows):
        errors: list[str] = []
        warnings: list[str] = []
        parsed: dict = {}

        sku = clean_text(_extract(row, mapping, "sku"))
        if not sku:
            errors.append("Missing SKU")
        parsed["sku"] = sku

        if target in ("SALES", "PURCHASES"):
            date_raw = _extract(row, mapping, "date")
            try:
                parsed["date"] = parse_date(date_raw)
            except ValueError as e:
                errors.append(str(e))

            qty_raw = _extract(row, mapping, "quantity")
            try:
                parsed["quantity"] = parse_quantity(qty_raw)
            except ValueError as e:
                errors.append(str(e))

            price_field = "unit_price" if target == "SALES" else "unit_cost"
            try:
                parsed[price_field] = parse_price(_extract(row, mapping, price_field), allow_none=False)
            except ValueError as e:
                errors.append(str(e))

            if sku and sku not in known_skus:
                errors.append(f"Unknown SKU '{sku}' — create the product/SKU first or import via PRODUCTS.")

            warehouse_code = clean_text(_extract(row, mapping, "warehouse_code"))
            if warehouse_code and warehouse_code.lower() not in known_warehouses:
                warnings.append(f"Unknown warehouse code '{warehouse_code}' — will use the default warehouse.")
            parsed["warehouse_code"] = warehouse_code

            if target == "SALES":
                parsed["customer_name"] = clean_text(_extract(row, mapping, "customer_name"))
                try:
                    parsed["discount"] = parse_price(_extract(row, mapping, "discount")) or 0
                except ValueError as e:
                    errors.append(str(e))
                try:
                    parsed["tax"] = parse_price(_extract(row, mapping, "tax")) or 0
                except ValueError as e:
                    errors.append(str(e))
                dedupe_key = (
                    "SALES",
                    sku,
                    str(parsed.get("date")),
                    parsed.get("quantity"),
                    parsed.get("unit_price"),
                    parsed.get("customer_name"),
                )
            else:
                parsed["supplier_name"] = clean_text(_extract(row, mapping, "supplier_name"))
                dedupe_key = (
                    "PURCHASES",
                    sku,
                    str(parsed.get("date")),
                    parsed.get("quantity"),
                    parsed.get("unit_cost"),
                )

        elif target == "OPENING_STOCK":
            qty_raw = _extract(row, mapping, "quantity")
            try:
                parsed["quantity"] = parse_quantity(qty_raw)
            except ValueError as e:
                errors.append(str(e))
            try:
                parsed["unit_cost"] = parse_price(_extract(row, mapping, "unit_cost"))
            except ValueError as e:
                errors.append(str(e))
            warehouse_code = clean_text(_extract(row, mapping, "warehouse_code"))
            parsed["warehouse_code"] = warehouse_code
            if warehouse_code and warehouse_code.lower() not in known_warehouses:
                warnings.append(f"Unknown warehouse code '{warehouse_code}' — will use the default warehouse.")
            if sku and sku not in known_skus:
                errors.append(f"Unknown SKU '{sku}' — create the product/SKU first or import via PRODUCTS.")
            dedupe_key = ("OPENING_STOCK", sku, warehouse_code)

        elif target == "PRODUCTS":
            brand = clean_text(_extract(row, mapping, "brand"))
            product_name = clean_text(_extract(row, mapping, "product_name"))
            if not brand:
                errors.append("Missing brand")
            elif brand.lower() not in known_brands:
                warnings.append(f"Unknown brand '{brand}' — a new brand record will be created.")
            if not product_name:
                errors.append("Missing product name")
            parsed["brand"] = brand
            parsed["product_name"] = product_name
            parsed["category"] = clean_text(_extract(row, mapping, "category"))
            parsed["size"] = clean_text(_extract(row, mapping, "size"))
            parsed["color"] = clean_text(_extract(row, mapping, "color"))
            parsed["gender"] = clean_text(_extract(row, mapping, "gender"))
            parsed["barcode"] = clean_text(_extract(row, mapping, "barcode"))
            for price_field in ("unit_cost", "unit_price", "mrp"):
                try:
                    parsed[price_field] = parse_price(_extract(row, mapping, price_field))
                except ValueError as e:
                    errors.append(str(e))
            if sku and sku in known_skus:
                warnings.append(f"SKU '{sku}' already exists — this row will update it, not create a duplicate.")
            dedupe_key = ("PRODUCTS", sku)
        else:
            dedupe_key = ("UNKNOWN", sku)

        is_duplicate = dedupe_key in seen_dedupe_keys
        if is_duplicate:
            duplicate_count += 1
            warnings.append("Duplicate of another row in this file.")
        else:
            seen_dedupe_keys.add(dedupe_key)

        is_valid = not errors and not is_duplicate
        if is_valid:
            valid_count += 1
        else:
            invalid_count += 1

        parsed_rows.append({"row_index": idx, "is_valid": is_valid, "data": {k: (str(v) if isinstance(v, datetime.date) else v) for k, v in parsed.items()}})
        if errors or warnings:
            row_reports.append({"row_index": idx, "errors": errors, "warnings": warnings})

    job.valid_rows = valid_count
    job.invalid_rows = invalid_count
    job.duplicate_rows = duplicate_count
    job.error_report = {"row_issues": row_reports[:1000]}
    job.raw_rows_cache = {**job.raw_rows_cache, "parsed_rows": parsed_rows}
    job.status = "VALIDATED" if valid_count > 0 else "FAILED"
    db.flush()
    return job


def _get_or_create_warehouse(db: Session, code: str | None) -> Warehouse:
    if code:
        wh = db.query(Warehouse).filter(Warehouse.code.ilike(code)).one_or_none()
        if wh:
            return wh
    default = db.query(Warehouse).order_by(Warehouse.id.asc()).first()
    if default is None:
        raise ImportError_("No warehouse exists to assign imported records to. Create a warehouse first.")
    return default


def _get_or_create_customer(db: Session, name: str | None) -> Customer | None:
    if not name:
        return None
    customer = db.query(Customer).filter(Customer.name.ilike(name)).one_or_none()
    if customer:
        return customer
    customer = Customer(name=name)
    db.add(customer)
    db.flush()
    return customer


def _get_or_create_supplier(db: Session, name: str | None) -> Supplier | None:
    if not name:
        return None
    supplier = db.query(Supplier).filter(Supplier.name.ilike(name)).one_or_none()
    if supplier:
        return supplier
    supplier = Supplier(name=name)
    db.add(supplier)
    db.flush()
    return supplier


def commit_job(db: Session, job: DataImportJob, user_id: int | None) -> DataImportJob:
    if job.status != "VALIDATED":
        raise ImportError_(f"Import job must be VALIDATED before commit (current status: {job.status}).")

    parsed_rows = job.raw_rows_cache.get("parsed_rows")
    if parsed_rows is None:
        raise ImportError_("No validated rows found — run validation again.")

    imported = 0
    skipped = 0

    for entry in parsed_rows:
        if not entry["is_valid"]:
            skipped += 1
            continue
        data = entry["data"]

        if job.target_entity == "SALES":
            variant = db.query(ProductVariant).filter(ProductVariant.sku == data["sku"]).one()
            warehouse = _get_or_create_warehouse(db, data.get("warehouse_code"))
            customer = _get_or_create_customer(db, data.get("customer_name"))
            sale_date = datetime.date.fromisoformat(data["date"])
            quantity = int(data["quantity"])
            unit_price = float(data["unit_price"])
            discount = float(data.get("discount") or 0)
            tax = float(data.get("tax") or 0)
            subtotal = quantity * unit_price
            total = subtotal - discount + tax

            sale = Sale(
                invoice_number=f"IMP-{job.id}-{entry['row_index']}",
                customer_id=customer.id if customer else None,
                warehouse_id=warehouse.id,
                sale_date=sale_date,
                subtotal=subtotal,
                discount_total=discount,
                tax_total=tax,
                total=total,
                created_by=user_id,
                is_historical_import=True,
            )
            db.add(sale)
            db.flush()
            db.add(
                SaleItem(
                    sale_id=sale.id,
                    variant_id=variant.id,
                    quantity=quantity,
                    unit_price=unit_price,
                    unit_cost=float(variant.purchase_cost) if variant.purchase_cost else None,
                    discount=discount,
                    tax=tax,
                )
            )
            inventory_service.record_transaction(
                db,
                TransactionRequest(
                    variant_id=variant.id,
                    warehouse_id=warehouse.id,
                    transaction_type=TransactionType.SALE,
                    quantity=quantity,
                    transaction_date=datetime.datetime.combine(sale_date, datetime.time.min),
                    unit_price=unit_price,
                    reference_type="SALE",
                    reference_id=sale.id,
                    user_id=user_id,
                    notes=f"Imported from {job.filename}",
                    is_historical_import=True,
                    allow_negative_stock=True,
                ),
            )
            imported += 1

        elif job.target_entity == "PURCHASES":
            variant = db.query(ProductVariant).filter(ProductVariant.sku == data["sku"]).one()
            warehouse = _get_or_create_warehouse(db, data.get("warehouse_code"))
            _get_or_create_supplier(db, data.get("supplier_name"))
            receipt_date = datetime.date.fromisoformat(data["date"])
            quantity = int(data["quantity"])
            unit_cost = float(data["unit_cost"])

            batch = InventoryBatch(
                variant_id=variant.id,
                warehouse_id=warehouse.id,
                batch_code=f"IMP-{job.id}-{entry['row_index']}",
                received_date=receipt_date,
                unit_cost=unit_cost,
                quantity_received=quantity,
                is_demo=False,
            )
            db.add(batch)
            db.flush()
            inventory_service.record_transaction(
                db,
                TransactionRequest(
                    variant_id=variant.id,
                    warehouse_id=warehouse.id,
                    batch_id=batch.id,
                    transaction_type=TransactionType.PURCHASE,
                    quantity=quantity,
                    transaction_date=datetime.datetime.combine(receipt_date, datetime.time.min),
                    unit_cost=unit_cost,
                    reference_type="IMPORT",
                    reference_id=job.id,
                    user_id=user_id,
                    notes=f"Imported from {job.filename}",
                    is_historical_import=True,
                ),
            )
            imported += 1

        elif job.target_entity == "OPENING_STOCK":
            variant = db.query(ProductVariant).filter(ProductVariant.sku == data["sku"]).one()
            warehouse = _get_or_create_warehouse(db, data.get("warehouse_code"))
            quantity = int(data["quantity"])
            unit_cost = float(data["unit_cost"]) if data.get("unit_cost") else float(variant.purchase_cost or 0)
            received_date = datetime.date.today()

            batch = InventoryBatch(
                variant_id=variant.id,
                warehouse_id=warehouse.id,
                batch_code=f"OPENING-{job.id}-{entry['row_index']}",
                received_date=received_date,
                unit_cost=unit_cost,
                quantity_received=quantity,
                is_demo=False,
            )
            db.add(batch)
            db.flush()
            inventory_service.record_transaction(
                db,
                TransactionRequest(
                    variant_id=variant.id,
                    warehouse_id=warehouse.id,
                    batch_id=batch.id,
                    transaction_type=TransactionType.OPENING_BALANCE,
                    quantity=quantity,
                    transaction_date=datetime.datetime.combine(received_date, datetime.time.min),
                    unit_cost=unit_cost,
                    reference_type="IMPORT",
                    reference_id=job.id,
                    user_id=user_id,
                    notes=f"Imported opening stock from {job.filename}",
                    is_historical_import=True,
                ),
            )
            imported += 1

        elif job.target_entity == "PRODUCTS":
            brand = db.query(Brand).filter(Brand.name.ilike(data["brand"])).one_or_none()
            if brand is None:
                brand = Brand(name=data["brand"], code=data["brand"][:10].upper().replace(" ", ""))
                db.add(brand)
                db.flush()

            category = None
            if data.get("category"):
                category = db.query(Category).filter(Category.name.ilike(data["category"])).one_or_none()
                if category is None:
                    category = Category(name=data["category"])
                    db.add(category)
                    db.flush()

            product = (
                db.query(Product)
                .filter(Product.brand_id == brand.id, Product.name.ilike(data["product_name"]))
                .one_or_none()
            )
            if product is None:
                product = Product(
                    brand_id=brand.id,
                    category_id=category.id if category else None,
                    name=data["product_name"],
                    gender=data.get("gender"),
                )
                db.add(product)
                db.flush()

            variant = db.query(ProductVariant).filter(ProductVariant.sku == data["sku"]).one_or_none()
            if variant is None:
                variant = ProductVariant(
                    product_id=product.id,
                    sku=data["sku"],
                    barcode=data.get("barcode"),
                    size=data.get("size"),
                    color=data.get("color"),
                    purchase_cost=data.get("unit_cost"),
                    selling_price=data.get("unit_price"),
                    mrp=data.get("mrp"),
                )
                db.add(variant)
            else:
                if data.get("unit_cost") is not None:
                    variant.purchase_cost = data["unit_cost"]
                if data.get("unit_price") is not None:
                    variant.selling_price = data["unit_price"]
                if data.get("mrp") is not None:
                    variant.mrp = data["mrp"]
            db.flush()
            imported += 1

    job.status = "IMPORTED"
    job.committed_at = datetime.datetime.now(datetime.timezone.utc)
    db.flush()
    return job
