from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.auth.deps import get_current_user, require_permission
from app.core.database import get_db
from app.models.auth import User
from app.models.catalog import Brand, Category, Product, ProductVariant
from app.schemas.catalog import (
    BrandCreate,
    BrandOut,
    BrandUpdate,
    CategoryCreate,
    CategoryOut,
    ProductCreate,
    ProductOut,
    ProductUpdate,
    ProductVariantCreate,
    ProductVariantDetailOut,
    ProductVariantOut,
    ProductVariantUpdate,
)
from app.services import inventory_service
from app.services.audit_service import log_action

router = APIRouter(prefix="/api", tags=["catalog"])


# ---- Brands ----

@router.get("/brands", response_model=list[BrandOut])
def list_brands(db: Session = Depends(get_db), _: User = Depends(require_permission("product:view"))):
    return db.query(Brand).order_by(Brand.name).all()


@router.post("/brands", response_model=BrandOut, status_code=201)
def create_brand(
    payload: BrandCreate, db: Session = Depends(get_db), user: User = Depends(require_permission("product:manage"))
):
    if db.query(Brand).filter(Brand.code == payload.code).first():
        raise HTTPException(400, f"Brand code '{payload.code}' already exists")
    brand = Brand(**payload.model_dump())
    db.add(brand)
    db.flush()
    log_action(db, user_id=user.id, action="CREATE", entity_type="brand", entity_id=brand.id, after=payload.model_dump())
    db.commit()
    db.refresh(brand)
    return brand


@router.patch("/brands/{brand_id}", response_model=BrandOut)
def update_brand(
    brand_id: int,
    payload: BrandUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("product:manage")),
):
    brand = db.get(Brand, brand_id)
    if not brand:
        raise HTTPException(404, "Brand not found")
    before = {"name": brand.name, "code": brand.code, "is_active": brand.is_active}
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(brand, field, value)
    db.flush()
    log_action(db, user_id=user.id, action="UPDATE", entity_type="brand", entity_id=brand.id, before=before, after=payload.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(brand)
    return brand


# ---- Categories ----

@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db), _: User = Depends(require_permission("product:view"))):
    return db.query(Category).order_by(Category.name).all()


@router.post("/categories", response_model=CategoryOut, status_code=201)
def create_category(
    payload: CategoryCreate, db: Session = Depends(get_db), user: User = Depends(require_permission("product:manage"))
):
    category = Category(**payload.model_dump())
    db.add(category)
    db.flush()
    log_action(db, user_id=user.id, action="CREATE", entity_type="category", entity_id=category.id, after=payload.model_dump())
    db.commit()
    db.refresh(category)
    return category


# ---- Products ----

@router.get("/products", response_model=list[ProductOut])
def list_products(
    brand_id: int | None = None,
    category_id: int | None = None,
    q: str | None = Query(None, description="Free-text search on product name/model code"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("product:view")),
):
    query = db.query(Product).filter(Product.is_active.is_(True))
    if brand_id:
        query = query.filter(Product.brand_id == brand_id)
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if q:
        like = f"%{q}%"
        query = query.filter((Product.name.ilike(like)) | (Product.model_code.ilike(like)))
    return query.order_by(Product.name).limit(500).all()


@router.post("/products", response_model=ProductOut, status_code=201)
def create_product(
    payload: ProductCreate, db: Session = Depends(get_db), user: User = Depends(require_permission("product:manage"))
):
    if not db.get(Brand, payload.brand_id):
        raise HTTPException(400, "Invalid brand_id")
    product = Product(**payload.model_dump())
    db.add(product)
    db.flush()
    log_action(db, user_id=user.id, action="CREATE", entity_type="product", entity_id=product.id, after=payload.model_dump())
    db.commit()
    db.refresh(product)
    return product


@router.patch("/products/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("product:manage")),
):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    updates = payload.model_dump(exclude_unset=True)
    before = {k: getattr(product, k) for k in updates}
    for field, value in updates.items():
        setattr(product, field, value)
    db.flush()
    log_action(db, user_id=user.id, action="UPDATE", entity_type="product", entity_id=product.id, before=before, after=updates)
    db.commit()
    db.refresh(product)
    return product


# ---- Product Variants (SKUs) ----

@router.get("/variants", response_model=list[ProductVariantOut])
def list_variants(
    product_id: int | None = None,
    sku: str | None = None,
    brand_id: int | None = None,
    q: str | None = Query(None, description="Free-text search on SKU/barcode/product name"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("product:view")),
):
    query = db.query(ProductVariant).join(Product).filter(ProductVariant.is_active.is_(True))
    if product_id:
        query = query.filter(ProductVariant.product_id == product_id)
    if sku:
        query = query.filter(ProductVariant.sku == sku)
    if brand_id:
        query = query.filter(Product.brand_id == brand_id)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (ProductVariant.sku.ilike(like)) | (ProductVariant.barcode.ilike(like)) | (Product.name.ilike(like))
        )
    return query.order_by(ProductVariant.sku).limit(500).all()


@router.get("/variants/{variant_id}", response_model=ProductVariantDetailOut)
def get_variant_detail(
    variant_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("product:view"))
):
    variant = (
        db.query(ProductVariant)
        .options(joinedload(ProductVariant.product).joinedload(Product.brand), joinedload(ProductVariant.product).joinedload(Product.category))
        .filter(ProductVariant.id == variant_id)
        .one_or_none()
    )
    if not variant:
        raise HTTPException(404, "SKU not found")
    stock = inventory_service.get_stock_on_hand(db, variant_id)
    return ProductVariantDetailOut(
        **ProductVariantOut.model_validate(variant).model_dump(),
        product_name=variant.product.name,
        brand_name=variant.product.brand.name,
        category_name=variant.product.category.name if variant.product.category else None,
        current_stock=stock,
    )


@router.post("/variants", response_model=ProductVariantOut, status_code=201)
def create_variant(
    payload: ProductVariantCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("product:manage")),
):
    if not db.get(Product, payload.product_id):
        raise HTTPException(400, "Invalid product_id")
    if db.query(ProductVariant).filter(ProductVariant.sku == payload.sku).first():
        raise HTTPException(400, f"SKU '{payload.sku}' already exists")
    variant = ProductVariant(**payload.model_dump())
    db.add(variant)
    db.flush()
    log_action(db, user_id=user.id, action="CREATE", entity_type="product_variant", entity_id=variant.id, after=payload.model_dump())
    db.commit()
    db.refresh(variant)
    return variant


@router.patch("/variants/{variant_id}", response_model=ProductVariantOut)
def update_variant(
    variant_id: int,
    payload: ProductVariantUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("product:manage")),
):
    variant = db.get(ProductVariant, variant_id)
    if not variant:
        raise HTTPException(404, "SKU not found")
    updates = payload.model_dump(exclude_unset=True)
    before = {k: getattr(variant, k) for k in updates}
    for field, value in updates.items():
        setattr(variant, field, value)
    db.flush()
    log_action(db, user_id=user.id, action="UPDATE", entity_type="product_variant", entity_id=variant.id, before=before, after=updates)
    db.commit()
    db.refresh(variant)
    return variant
