from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from systutor.api.deps import get_db_session
from systutor.kernel.auth.dependencies import (
    get_current_tenant_context,
    require_permission,
)
from systutor.kernel.tenants.context import TenantContext

from plugins.productos.backend.common import build_action_context
from plugins.productos.backend.models import (
    ProductBrand,
    ProductCategory,
    ProductCondition,
    ProductGroup,
    ProductInsumoType,
    ProductLine,
    ProductStatus,
    ProductSubcategory,
    ProductSubline,
    ProductUnit,
)
from plugins.productos.backend.schemas import (
    NamedCatalogCreateRequest,
    NamedCatalogRead,
    NamedCatalogUpdateRequest,
    ProductBarcodeCreateRequest,
    ProductBarcodeRead,
    ProductBarcodeUpdateRequest,
    ProductConditionRead,
    ProductCostCreateRequest,
    ProductCostRead,
    ProductCostSupersedeRequest,
    ProductCreateRequest,
    ProductGroupCreateRequest,
    ProductGroupRead,
    ProductGroupUpdateRequest,
    ProductLineCreateRequest,
    ProductLineRead,
    ProductLineUpdateRequest,
    ProductListItemRead,
    ProductMediaRead,
    ProductPageRead,
    ProductPriceBulkUpdateRequest,
    ProductPriceCreateRequest,
    ProductPriceRead,
    ProductPriceSupersedeRequest,
    ProductPromotionCreateRequest,
    ProductPromotionRead,
    ProductPromotionUpdateRequest,
    ProductRead,
    ProductSearchItemRead,
    ProductStatusRead,
    ProductSublineCreateRequest,
    ProductSublineRead,
    ProductSublineUpdateRequest,
    ProductTaxConfigRead,
    ProductTaxConfigUpdateRequest,
    ProductToggleActiveRequest,
    ProductUnitCreateRequest,
    ProductUnitRead,
    ProductUnitUpdateRequest,
    ProductUpdateRequest,
)
from plugins.productos.backend.services.barcode import (
    create_barcode,
    delete_barcode,
    list_barcodes,
    require_barcode,
    set_primary_barcode,
    update_barcode,
)
from plugins.productos.backend.services.catalog import (
    create_brand,
    create_category,
    create_group,
    create_insumo_type,
    create_line,
    create_subcategory,
    create_subline,
    create_unit,
    get_tenant_entity_or_none,
    list_brands,
    list_categories,
    list_conditions,
    list_groups,
    list_insumo_types,
    list_lines,
    list_status,
    list_subcategories,
    list_subline,
    list_units,
    update_brand,
    update_category,
    update_group,
    update_insumo_type,
    update_line,
    update_subcategory,
    update_subline,
    update_unit,
)
from plugins.productos.backend.services.media import (
    create_media,
    delete_media,
    list_media,
    require_media,
    resolve_media_path,
    set_primary_media,
)
from plugins.productos.backend.services.pricing import (
    create_cost,
    create_price,
    list_costs,
    list_prices,
    list_tax_configs,
    replace_tax_configs,
    require_cost,
    require_price,
    supersede_cost,
    supersede_price,
    update_all_prices,
)
from plugins.productos.backend.services.products import (
    create_product,
    get_product,
    list_products,
    require_product,
    search_products,
    serialize_product,
    toggle_product_active,
    update_product,
)
from plugins.productos.backend.services.promotions import (
    create_promotion,
    delete_promotion,
    list_promotions,
    require_promotion,
    update_promotion,
)

router = APIRouter(tags=["productos"])
DB_SESSION = Depends(get_db_session)
TENANT_CONTEXT = Depends(get_current_tenant_context)
UPLOAD_FILE = File(...)


REQUIRE_CATALOG_READ = Depends(require_permission("productos.catalog.read"))
REQUIRE_CATALOG_MANAGE = Depends(require_permission("productos.catalog.manage"))
REQUIRE_PRODUCT_READ = Depends(require_permission("productos.product.read"))
REQUIRE_PRODUCT_CREATE = Depends(require_permission("productos.product.create"))
REQUIRE_PRODUCT_UPDATE = Depends(require_permission("productos.product.update"))
REQUIRE_PRODUCT_DELETE = Depends(require_permission("productos.product.delete"))
REQUIRE_PRICE_READ = Depends(require_permission("productos.price.read"))
REQUIRE_PRICE_MANAGE = Depends(require_permission("productos.price.manage"))
REQUIRE_COST_READ = Depends(require_permission("productos.cost.read"))
REQUIRE_COST_MANAGE = Depends(require_permission("productos.cost.manage"))
REQUIRE_MEDIA_MANAGE = Depends(require_permission("productos.media.manage"))
REQUIRE_PROMOTION_READ = Depends(require_permission("productos.promotion.read"))
REQUIRE_PROMOTION_MANAGE = Depends(require_permission("productos.promotion.manage"))


def _bad_request(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


def _not_found(entity_name: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{entity_name} not found")


def _serialize_named(items: Sequence[object]) -> list[NamedCatalogRead]:
    return [NamedCatalogRead.model_validate(item) for item in items]


def _require_product_or_404(db: Session, *, tenant_id: str, product_id: str):
    try:
        return require_product(db, tenant_id=tenant_id, product_id=product_id)
    except ValueError as exc:
        raise _not_found("Product") from exc


@router.get(
    "/catalog/categories",
    response_model=list[NamedCatalogRead],
    dependencies=[REQUIRE_CATALOG_READ],
)
def get_categories(
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> list[NamedCatalogRead]:
    return _serialize_named(
        list_categories(db, tenant_id=tenant_context.current_tenant_id)
    )


@router.post(
    "/catalog/categories",
    response_model=NamedCatalogRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[REQUIRE_CATALOG_MANAGE],
)
def post_category(
    payload: NamedCatalogCreateRequest,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> NamedCatalogRead:
    item = create_category(
        db,
        tenant_id=tenant_context.current_tenant_id,
        payload=payload,
        action_context=build_action_context(request, tenant_context),
    )
    db.commit()
    return NamedCatalogRead.model_validate(item)


@router.put(
    "/catalog/categories/{category_id}",
    response_model=NamedCatalogRead,
    dependencies=[REQUIRE_CATALOG_MANAGE],
)
def put_category(
    category_id: str,
    payload: NamedCatalogUpdateRequest,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> NamedCatalogRead:
    category = get_tenant_entity_or_none(
        db, ProductCategory, tenant_id=tenant_context.current_tenant_id, entity_id=category_id
    )
    if category is None:
        raise _not_found("Category")
    item = update_category(
        db,
        category=category,
        payload=payload,
        action_context=build_action_context(request, tenant_context),
    )
    db.commit()
    return NamedCatalogRead.model_validate(item)


@router.get(
    "/catalog/lines", response_model=list[ProductLineRead], dependencies=[REQUIRE_CATALOG_READ]
)
def get_lines(
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> list[ProductLineRead]:
    return [
        ProductLineRead.model_validate(item)
        for item in list_lines(db, tenant_id=tenant_context.current_tenant_id)
    ]


@router.post(
    "/catalog/lines",
    response_model=ProductLineRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[REQUIRE_CATALOG_MANAGE],
)
def post_line(
    payload: ProductLineCreateRequest,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> ProductLineRead:
    item = create_line(
        db,
        tenant_id=tenant_context.current_tenant_id,
        payload=payload,
        action_context=build_action_context(request, tenant_context),
    )
    db.commit()
    return ProductLineRead.model_validate(item)


@router.put(
    "/catalog/lines/{line_id}",
    response_model=ProductLineRead,
    dependencies=[REQUIRE_CATALOG_MANAGE],
)
def put_line(
    line_id: str,
    payload: ProductLineUpdateRequest,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> ProductLineRead:
    line = get_tenant_entity_or_none(
        db, ProductLine, tenant_id=tenant_context.current_tenant_id, entity_id=line_id
    )
    if line is None:
        raise _not_found("Line")
    item = update_line(
        db,
        line=line,
        payload=payload,
        action_context=build_action_context(request, tenant_context),
    )
    db.commit()
    return ProductLineRead.model_validate(item)


@router.get(
    "/catalog/subline", response_model=list[ProductSublineRead], dependencies=[REQUIRE_CATALOG_READ]
)
def get_subline(
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> list[ProductSublineRead]:
    return [
        ProductSublineRead.model_validate(item)
        for item in list_subline(db, tenant_id=tenant_context.current_tenant_id)
    ]


@router.post(
    "/catalog/subline",
    response_model=ProductSublineRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[REQUIRE_CATALOG_MANAGE],
)
def post_subline(
    payload: ProductSublineCreateRequest,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> ProductSublineRead:
    item = create_subline(
        db,
        tenant_id=tenant_context.current_tenant_id,
        payload=payload,
        action_context=build_action_context(request, tenant_context),
    )
    db.commit()
    return ProductSublineRead.model_validate(item)


@router.put(
    "/catalog/subline/{subline_id}",
    response_model=ProductSublineRead,
    dependencies=[REQUIRE_CATALOG_MANAGE],
)
def put_subline(
    subline_id: str,
    payload: ProductSublineUpdateRequest,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> ProductSublineRead:
    subline = get_tenant_entity_or_none(
        db, ProductSubline, tenant_id=tenant_context.current_tenant_id, entity_id=subline_id
    )
    if subline is None:
        raise _not_found("Subline")
    item = update_subline(
        db,
        subline=subline,
        payload=payload,
        action_context=build_action_context(request, tenant_context),
    )
    db.commit()
    return ProductSublineRead.model_validate(item)


@router.get(
    "/catalog/brands", response_model=list[NamedCatalogRead], dependencies=[REQUIRE_CATALOG_READ]
)
def get_brands(
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> list[NamedCatalogRead]:
    return _serialize_named(list_brands(db, tenant_id=tenant_context.current_tenant_id))


@router.post(
    "/catalog/brands",
    response_model=NamedCatalogRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[REQUIRE_CATALOG_MANAGE],
)
def post_brand(
    payload: NamedCatalogCreateRequest,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> NamedCatalogRead:
    item = create_brand(
        db,
        tenant_id=tenant_context.current_tenant_id,
        payload=payload,
        action_context=build_action_context(request, tenant_context),
    )
    db.commit()
    return NamedCatalogRead.model_validate(item)


@router.put(
    "/catalog/brands/{brand_id}",
    response_model=NamedCatalogRead,
    dependencies=[REQUIRE_CATALOG_MANAGE],
)
def put_brand(
    brand_id: str,
    payload: NamedCatalogUpdateRequest,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> NamedCatalogRead:
    brand = get_tenant_entity_or_none(
        db, ProductBrand, tenant_id=tenant_context.current_tenant_id, entity_id=brand_id
    )
    if brand is None:
        raise _not_found("Brand")
    item = update_brand(
        db,
        brand=brand,
        payload=payload,
        action_context=build_action_context(request, tenant_context),
    )
    db.commit()
    return NamedCatalogRead.model_validate(item)


@router.get(
    "/catalog/insumo-types",
    response_model=list[NamedCatalogRead],
    dependencies=[REQUIRE_CATALOG_READ],
)
def get_insumo_types(
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> list[NamedCatalogRead]:
    return _serialize_named(
        list_insumo_types(db, tenant_id=tenant_context.current_tenant_id)
    )


@router.post(
    "/catalog/insumo-types",
    response_model=NamedCatalogRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[REQUIRE_CATALOG_MANAGE],
)
def post_insumo_type(
    payload: NamedCatalogCreateRequest,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> NamedCatalogRead:
    item = create_insumo_type(
        db,
        tenant_id=tenant_context.current_tenant_id,
        payload=payload,
        action_context=build_action_context(request, tenant_context),
    )
    db.commit()
    return NamedCatalogRead.model_validate(item)


@router.put(
    "/catalog/insumo-types/{insumo_type_id}",
    response_model=NamedCatalogRead,
    dependencies=[REQUIRE_CATALOG_MANAGE],
)
def put_insumo_type(
    insumo_type_id: str,
    payload: NamedCatalogUpdateRequest,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> NamedCatalogRead:
    insumo_type = get_tenant_entity_or_none(
        db,
        ProductInsumoType,
        tenant_id=tenant_context.current_tenant_id,
        entity_id=insumo_type_id,
    )
    if insumo_type is None:
        raise _not_found("Insumo type")
    item = update_insumo_type(
        db,
        insumo_type=insumo_type,
        payload=payload,
        action_context=build_action_context(request, tenant_context),
    )
    db.commit()
    return NamedCatalogRead.model_validate(item)


@router.get(
    "/catalog/units", response_model=list[ProductUnitRead], dependencies=[REQUIRE_CATALOG_READ]
)
def get_units(
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> list[ProductUnitRead]:
    return [
        ProductUnitRead.model_validate(item)
        for item in list_units(db, tenant_id=tenant_context.current_tenant_id)
    ]


@router.post(
    "/catalog/units",
    response_model=ProductUnitRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[REQUIRE_CATALOG_MANAGE],
)
def post_unit(
    payload: ProductUnitCreateRequest,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> ProductUnitRead:
    item = create_unit(
        db,
        tenant_id=tenant_context.current_tenant_id,
        payload=payload,
        action_context=build_action_context(request, tenant_context),
    )
    db.commit()
    return ProductUnitRead.model_validate(item)


@router.put(
    "/catalog/units/{unit_id}",
    response_model=ProductUnitRead,
    dependencies=[REQUIRE_CATALOG_MANAGE],
)
def put_unit(
    unit_id: str,
    payload: ProductUnitUpdateRequest,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> ProductUnitRead:
    unit = get_tenant_entity_or_none(
        db, ProductUnit, tenant_id=tenant_context.current_tenant_id, entity_id=unit_id
    )
    if unit is None:
        raise _not_found("Unit")
    item = update_unit(
        db,
        unit=unit,
        payload=payload,
        action_context=build_action_context(request, tenant_context),
    )
    db.commit()
    return ProductUnitRead.model_validate(item)


@router.get(
    "/catalog/subcategories",
    response_model=list[NamedCatalogRead],
    dependencies=[REQUIRE_CATALOG_READ],
)
def get_subcategories(
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> list[NamedCatalogRead]:
    return _serialize_named(
        list_subcategories(db, tenant_id=tenant_context.current_tenant_id)
    )


@router.post(
    "/catalog/subcategories",
    response_model=NamedCatalogRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[REQUIRE_CATALOG_MANAGE],
)
def post_subcategory(
    payload: NamedCatalogCreateRequest,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> NamedCatalogRead:
    item = create_subcategory(
        db,
        tenant_id=tenant_context.current_tenant_id,
        payload=payload,
        action_context=build_action_context(request, tenant_context),
    )
    db.commit()
    return NamedCatalogRead.model_validate(item)


@router.put(
    "/catalog/subcategories/{subcategory_id}",
    response_model=NamedCatalogRead,
    dependencies=[REQUIRE_CATALOG_MANAGE],
)
def put_subcategory(
    subcategory_id: str,
    payload: NamedCatalogUpdateRequest,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> NamedCatalogRead:
    subcategory = get_tenant_entity_or_none(
        db,
        ProductSubcategory,
        tenant_id=tenant_context.current_tenant_id,
        entity_id=subcategory_id,
    )
    if subcategory is None:
        raise _not_found("Subcategory")
    item = update_subcategory(
        db,
        subcategory=subcategory,
        payload=payload,
        action_context=build_action_context(request, tenant_context),
    )
    db.commit()
    return NamedCatalogRead.model_validate(item)


@router.get(
    "/catalog/groups", response_model=list[ProductGroupRead], dependencies=[REQUIRE_CATALOG_READ]
)
def get_groups(
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> list[ProductGroupRead]:
    return [
        ProductGroupRead.model_validate(item)
        for item in list_groups(db, tenant_id=tenant_context.current_tenant_id)
    ]


@router.post(
    "/catalog/groups",
    response_model=ProductGroupRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[REQUIRE_CATALOG_MANAGE],
)
def post_group(
    payload: ProductGroupCreateRequest,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> ProductGroupRead:
    item = create_group(
        db,
        tenant_id=tenant_context.current_tenant_id,
        payload=payload,
        action_context=build_action_context(request, tenant_context),
    )
    db.commit()
    return ProductGroupRead.model_validate(item)


@router.put(
    "/catalog/groups/{group_id}",
    response_model=ProductGroupRead,
    dependencies=[REQUIRE_CATALOG_MANAGE],
)
def put_group(
    group_id: str,
    payload: ProductGroupUpdateRequest,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> ProductGroupRead:
    group = get_tenant_entity_or_none(
        db, ProductGroup, tenant_id=tenant_context.current_tenant_id, entity_id=group_id
    )
    if group is None:
        raise _not_found("Group")
    item = update_group(
        db,
        group=group,
        payload=payload,
        action_context=build_action_context(request, tenant_context),
    )
    db.commit()
    return ProductGroupRead.model_validate(item)


@router.get(
    "/catalog/conditions",
    response_model=list[ProductConditionRead],
    dependencies=[REQUIRE_CATALOG_READ],
)
def get_conditions(request: Request, db: Session = DB_SESSION) -> list[ProductConditionRead]:
    return [ProductConditionRead.model_validate(item) for item in list_conditions(db)]


@router.get(
    "/catalog/status",
    response_model=list[ProductStatusRead],
    dependencies=[REQUIRE_CATALOG_READ],
)
def get_status_catalog(request: Request, db: Session = DB_SESSION) -> list[ProductStatusRead]:
    return [ProductStatusRead.model_validate(item) for item in list_status(db)]


@router.get("/products", response_model=ProductPageRead, dependencies=[REQUIRE_PRODUCT_READ])
def get_products(
    request: Request,
    db: Session = DB_SESSION,
    sku: str | None = Query(default=None),
    name: str | None = Query(default=None),
    line_id: str | None = Query(default=None),
    brand_id: str | None = Query(default=None),
    condition_code: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> ProductPageRead:
    items, total = list_products(
        db,
        tenant_id=tenant_context.current_tenant_id,
        sku=sku,
        name=name,
        line_id=line_id,
        brand_id=brand_id,
        condition_code=condition_code,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )
    return ProductPageRead(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/products/search",
    response_model=list[ProductSearchItemRead],
    dependencies=[REQUIRE_PRODUCT_READ],
)
def get_product_search(
    request: Request,
    db: Session = DB_SESSION,
    q: str = Query(..., min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> list[ProductSearchItemRead]:
    return search_products(
        db, tenant_id=tenant_context.current_tenant_id, query=q, limit=limit
    )


@router.get(
    "/products/flat",
    response_model=list[ProductListItemRead],
    dependencies=[REQUIRE_PRODUCT_READ],
)
def get_products_flat(
    request: Request,
    db: Session = DB_SESSION,
    is_active: bool | None = Query(default=None),
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> list[ProductListItemRead]:
    items, _ = list_products(
        db,
        tenant_id=tenant_context.current_tenant_id,
        is_active=is_active,
        limit=10000,
        offset=0,
    )
    return items


@router.get(
    "/products/{product_id}", response_model=ProductRead, dependencies=[REQUIRE_PRODUCT_READ]
)
def get_product_detail(
    product_id: str,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> ProductRead:
    product = get_product(db, tenant_id=tenant_context.current_tenant_id, product_id=product_id)
    if product is None:
        raise _not_found("Product")
    result = serialize_product(product)

    row = db.get(ProductLine, product.line_id) if product.line_id is not None else None
    result.line_name = row.name if row else None
    row = db.get(ProductSubline, product.subline_id) if product.subline_id is not None else None
    result.subline_name = row.name if row else None
    row = db.get(ProductBrand, product.brand_id) if product.brand_id is not None else None
    result.brand_name = row.name if row else None
    row = db.get(ProductUnit, product.unit_id) if product.unit_id is not None else None
    result.unit_name = row.name if row else None
    row = (
        db.get(ProductInsumoType, product.insumo_type_id)
        if product.insumo_type_id is not None
        else None
    )
    result.insumo_type_name = row.name if row else None
    row = (
        db.get(ProductSubcategory, product.subcategory_id)
        if product.subcategory_id is not None
        else None
    )
    result.subcategory_name = row.name if row else None
    row = db.get(ProductGroup, product.group_id) if product.group_id is not None else None
    result.group_name = row.name if row else None
    row = (
        db.get(ProductCondition, product.condition_code)
        if product.condition_code is not None
        else None
    )
    result.condition_name = row.name if row else None
    row = db.get(ProductStatus, product.status_code) if product.status_code is not None else None
    result.status_name = row.name if row else None
    return result


@router.post(
    "/products",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[REQUIRE_PRODUCT_CREATE],
)
def post_product(
    payload: ProductCreateRequest,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> ProductRead:
    try:
        product = create_product(
            db,
            tenant_id=tenant_context.current_tenant_id,
            actor_user_id=tenant_context.current_user_id,
            payload=payload,
            action_context=build_action_context(request, tenant_context),
        )
        item = serialize_product(product)
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc
    db.commit()
    return item


@router.put(
    "/products/{product_id}", response_model=ProductRead, dependencies=[REQUIRE_PRODUCT_UPDATE]
)
def put_product(
    product_id: str,
    payload: ProductUpdateRequest,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> ProductRead:
    try:
        product = require_product(
            db, tenant_id=tenant_context.current_tenant_id, product_id=product_id
        )
        updated = update_product(
            db,
            product=product,
            payload=payload,
            action_context=build_action_context(request, tenant_context),
        )
        item = serialize_product(updated)
    except ValueError as exc:
        if str(exc) == "Product not found":
            raise _not_found("Product") from exc
        raise _bad_request(str(exc)) from exc
    db.commit()
    return item


@router.patch(
    "/products/{product_id}/status",
    response_model=ProductRead,
    dependencies=[REQUIRE_PRODUCT_DELETE],
)
def patch_product_status(
    product_id: str,
    payload: ProductToggleActiveRequest,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> ProductRead:
    try:
        product = require_product(
            db, tenant_id=tenant_context.current_tenant_id, product_id=product_id
        )
        updated = toggle_product_active(
            db,
            product=product,
            is_active=payload.is_active,
            reason=payload.reason,
            action_context=build_action_context(request, tenant_context),
        )
        item = serialize_product(updated)
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc
    db.commit()
    return item


@router.get(
    "/products/{product_id}/barcodes",
    response_model=list[ProductBarcodeRead],
    dependencies=[REQUIRE_PRODUCT_READ],
)
def get_product_barcodes(
    product_id: str,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> list[ProductBarcodeRead]:
    _require_product_or_404(
        db, tenant_id=tenant_context.current_tenant_id, product_id=product_id
    )
    return [
        ProductBarcodeRead.model_validate(item)
        for item in list_barcodes(db, product_id=product_id)
    ]


@router.post(
    "/products/{product_id}/barcodes",
    response_model=ProductBarcodeRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[REQUIRE_PRODUCT_UPDATE],
)
def post_product_barcode(
    product_id: str,
    payload: ProductBarcodeCreateRequest,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> ProductBarcodeRead:
    try:
        product = require_product(
            db, tenant_id=tenant_context.current_tenant_id, product_id=product_id
        )
        item = create_barcode(
            db,
            product=product,
            payload=payload,
            action_context=build_action_context(request, tenant_context),
        )
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc
    db.commit()
    return ProductBarcodeRead.model_validate(item)


@router.put(
    "/products/{product_id}/barcodes/{barcode_id}",
    response_model=ProductBarcodeRead,
    dependencies=[REQUIRE_PRODUCT_UPDATE],
)
def put_product_barcode(
    product_id: str,
    barcode_id: str,
    payload: ProductBarcodeUpdateRequest,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> ProductBarcodeRead:
    try:
        require_product(db, tenant_id=tenant_context.current_tenant_id, product_id=product_id)
        barcode = require_barcode(db, product_id=product_id, barcode_id=barcode_id)
        item = update_barcode(
            db,
            barcode=barcode,
            payload=payload,
            action_context=build_action_context(request, tenant_context),
        )
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc
    db.commit()
    return ProductBarcodeRead.model_validate(item)


@router.delete(
    "/products/{product_id}/barcodes/{barcode_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[REQUIRE_PRODUCT_UPDATE],
)
def delete_product_barcode(
    product_id: str,
    barcode_id: str,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> None:
    try:
        require_product(db, tenant_id=tenant_context.current_tenant_id, product_id=product_id)
        barcode = require_barcode(db, product_id=product_id, barcode_id=barcode_id)
        delete_barcode(
            db, barcode=barcode, action_context=build_action_context(request, tenant_context)
        )
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc
    db.commit()


@router.post(
    "/products/{product_id}/barcodes/{barcode_id}/set-primary",
    response_model=ProductBarcodeRead,
    dependencies=[REQUIRE_PRODUCT_UPDATE],
)
def post_set_primary_barcode(
    product_id: str,
    barcode_id: str,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> ProductBarcodeRead:
    try:
        require_product(db, tenant_id=tenant_context.current_tenant_id, product_id=product_id)
        barcode = require_barcode(db, product_id=product_id, barcode_id=barcode_id)
        item = set_primary_barcode(
            db,
            barcode=barcode,
            action_context=build_action_context(request, tenant_context),
        )
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc
    db.commit()
    return ProductBarcodeRead.model_validate(item)


@router.get(
    "/products/{product_id}/prices",
    response_model=list[ProductPriceRead],
    dependencies=[REQUIRE_PRICE_READ],
)
def get_product_prices(
    product_id: str,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> list[ProductPriceRead]:
    _require_product_or_404(
        db, tenant_id=tenant_context.current_tenant_id, product_id=product_id
    )
    return [
        ProductPriceRead.model_validate(item) for item in list_prices(db, product_id=product_id)
    ]


@router.post(
    "/products/{product_id}/prices",
    response_model=ProductPriceRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[REQUIRE_PRICE_MANAGE],
)
def post_product_price(
    product_id: str,
    payload: ProductPriceCreateRequest,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> ProductPriceRead:
    try:
        product = require_product(
            db, tenant_id=tenant_context.current_tenant_id, product_id=product_id
        )
        item = create_price(
            db,
            product=product,
            actor_user_id=tenant_context.current_user_id,
            payload=payload,
            action_context=build_action_context(request, tenant_context),
        )
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc
    db.commit()
    return ProductPriceRead.model_validate(item)


@router.post(
    "/products/{product_id}/prices/{price_id}/supersede",
    response_model=ProductPriceRead,
    dependencies=[REQUIRE_PRICE_MANAGE],
)
def post_supersede_price(
    product_id: str,
    price_id: str,
    payload: ProductPriceSupersedeRequest,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> ProductPriceRead:
    try:
        require_product(db, tenant_id=tenant_context.current_tenant_id, product_id=product_id)
        price = require_price(db, product_id=product_id, price_id=price_id)
        item = supersede_price(
            db,
            price=price,
            actor_user_id=tenant_context.current_user_id,
            payload=payload,
            action_context=build_action_context(request, tenant_context),
        )
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc
    db.commit()
    return ProductPriceRead.model_validate(item)


@router.post(
    "/products/{product_id}/prices/update-all",
    response_model=list[ProductPriceRead],
    dependencies=[REQUIRE_PRICE_MANAGE],
)
def post_update_all_prices(
    product_id: str,
    payload: ProductPriceBulkUpdateRequest,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> list[ProductPriceRead]:
    try:
        product = require_product(
            db, tenant_id=tenant_context.current_tenant_id, product_id=product_id
        )
        items = update_all_prices(
            db,
            product=product,
            actor_user_id=tenant_context.current_user_id,
            payload=payload,
            action_context=build_action_context(request, tenant_context),
        )
        item = [ProductPriceRead.model_validate(item) for item in items]
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc
    db.commit()
    return item


@router.get(
    "/products/{product_id}/costs",
    response_model=list[ProductCostRead],
    dependencies=[REQUIRE_COST_READ],
)
def get_product_costs(
    product_id: str,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> list[ProductCostRead]:
    _require_product_or_404(
        db, tenant_id=tenant_context.current_tenant_id, product_id=product_id
    )
    return [
        ProductCostRead.model_validate(item) for item in list_costs(db, product_id=product_id)
    ]


@router.post(
    "/products/{product_id}/costs",
    response_model=ProductCostRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[REQUIRE_COST_MANAGE],
)
def post_product_cost(
    product_id: str,
    payload: ProductCostCreateRequest,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> ProductCostRead:
    try:
        product = require_product(
            db, tenant_id=tenant_context.current_tenant_id, product_id=product_id
        )
        item = create_cost(
            db,
            product=product,
            actor_user_id=tenant_context.current_user_id,
            payload=payload,
            action_context=build_action_context(request, tenant_context),
        )
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc
    db.commit()
    return ProductCostRead.model_validate(item)


@router.post(
    "/products/{product_id}/costs/{cost_id}/supersede",
    response_model=ProductCostRead,
    dependencies=[REQUIRE_COST_MANAGE],
)
def post_supersede_cost(
    product_id: str,
    cost_id: str,
    payload: ProductCostSupersedeRequest,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> ProductCostRead:
    try:
        require_product(db, tenant_id=tenant_context.current_tenant_id, product_id=product_id)
        cost = require_cost(db, product_id=product_id, cost_id=cost_id)
        item = supersede_cost(
            db,
            cost=cost,
            actor_user_id=tenant_context.current_user_id,
            payload=payload,
            action_context=build_action_context(request, tenant_context),
        )
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc
    db.commit()
    return ProductCostRead.model_validate(item)


@router.get(
    "/products/{product_id}/tax",
    response_model=list[ProductTaxConfigRead],
    dependencies=[REQUIRE_PRODUCT_READ],
)
def get_product_tax(
    product_id: str,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> list[ProductTaxConfigRead]:
    _require_product_or_404(
        db, tenant_id=tenant_context.current_tenant_id, product_id=product_id
    )
    return [
        ProductTaxConfigRead.model_validate(item)
        for item in list_tax_configs(db, product_id=product_id)
    ]


@router.put(
    "/products/{product_id}/tax",
    response_model=list[ProductTaxConfigRead],
    dependencies=[REQUIRE_PRODUCT_UPDATE],
)
def put_product_tax(
    product_id: str,
    payload: ProductTaxConfigUpdateRequest,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> list[ProductTaxConfigRead]:
    try:
        product = require_product(
            db, tenant_id=tenant_context.current_tenant_id, product_id=product_id
        )
        items = replace_tax_configs(
            db,
            product=product,
            payload=payload,
            action_context=build_action_context(request, tenant_context),
        )
        item = [ProductTaxConfigRead.model_validate(item) for item in items]
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc
    db.commit()
    return item


@router.get(
    "/products/{product_id}/media",
    response_model=list[ProductMediaRead],
    dependencies=[REQUIRE_PRODUCT_READ],
)
def get_product_media(
    product_id: str,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> list[ProductMediaRead]:
    _require_product_or_404(
        db, tenant_id=tenant_context.current_tenant_id, product_id=product_id
    )
    return [
        ProductMediaRead.model_validate(item) for item in list_media(db, product_id=product_id)
    ]


@router.post(
    "/products/{product_id}/media",
    response_model=ProductMediaRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[REQUIRE_MEDIA_MANAGE],
)
async def post_product_media(
    product_id: str,
    request: Request,
    db: Session = DB_SESSION,
    media_type: str = Query(..., min_length=1, max_length=20),
    is_primary: bool = Query(default=False),
    file: UploadFile = UPLOAD_FILE,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> ProductMediaRead:
    content = await file.read()
    try:
        product = require_product(
            db, tenant_id=tenant_context.current_tenant_id, product_id=product_id
        )
        item = create_media(
            db,
            product=product,
            media_type=media_type,
            is_primary=is_primary,
            filename=file.filename or "archivo",
            content=content,
            action_context=build_action_context(request, tenant_context),
        )
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc
    db.commit()
    return ProductMediaRead.model_validate(item)


@router.get(
    "/products/{product_id}/media/{media_id}/download/{stored_name}",
    dependencies=[REQUIRE_PRODUCT_READ],
)
def get_product_media_download(
    product_id: str,
    media_id: str,
    stored_name: str,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> FileResponse:
    _require_product_or_404(
        db, tenant_id=tenant_context.current_tenant_id, product_id=product_id
    )
    media = require_media(db, product_id=product_id, media_id=media_id)
    path = resolve_media_path(media)
    if path.name != Path(stored_name).name or not path.exists():
        raise _not_found("Media file")
    return FileResponse(path)


@router.delete(
    "/products/{product_id}/media/{media_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[REQUIRE_MEDIA_MANAGE],
)
def delete_product_media(
    product_id: str,
    media_id: str,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> None:
    try:
        require_product(db, tenant_id=tenant_context.current_tenant_id, product_id=product_id)
        media = require_media(db, product_id=product_id, media_id=media_id)
        delete_media(
            db, media=media, action_context=build_action_context(request, tenant_context)
        )
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc
    db.commit()


@router.post(
    "/products/{product_id}/media/{media_id}/set-primary",
    response_model=ProductMediaRead,
    dependencies=[REQUIRE_MEDIA_MANAGE],
)
def post_set_primary_media(
    product_id: str,
    media_id: str,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> ProductMediaRead:
    try:
        require_product(db, tenant_id=tenant_context.current_tenant_id, product_id=product_id)
        media = require_media(db, product_id=product_id, media_id=media_id)
        item = set_primary_media(
            db,
            media=media,
            action_context=build_action_context(request, tenant_context),
        )
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc
    db.commit()
    return ProductMediaRead.model_validate(item)


@router.get(
    "/products/{product_id}/promotions",
    response_model=list[ProductPromotionRead],
    dependencies=[REQUIRE_PROMOTION_READ],
)
def get_product_promotions(
    product_id: str,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> list[ProductPromotionRead]:
    _require_product_or_404(
        db, tenant_id=tenant_context.current_tenant_id, product_id=product_id
    )
    return [
        ProductPromotionRead.model_validate(item)
        for item in list_promotions(db, product_id=product_id)
    ]


@router.post(
    "/products/{product_id}/promotions",
    response_model=ProductPromotionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[REQUIRE_PROMOTION_MANAGE],
)
def post_product_promotion(
    product_id: str,
    payload: ProductPromotionCreateRequest,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> ProductPromotionRead:
    try:
        product = require_product(
            db, tenant_id=tenant_context.current_tenant_id, product_id=product_id
        )
        item = create_promotion(
            db,
            product=product,
            actor_user_id=tenant_context.current_user_id,
            payload=payload,
            action_context=build_action_context(request, tenant_context),
        )
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc
    db.commit()
    return ProductPromotionRead.model_validate(item)


@router.put(
    "/promotions/{promotion_id}",
    response_model=ProductPromotionRead,
    dependencies=[REQUIRE_PROMOTION_MANAGE],
)
def put_promotion(
    promotion_id: str,
    payload: ProductPromotionUpdateRequest,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> ProductPromotionRead:
    try:
        promotion = require_promotion(db, promotion_id=promotion_id)
        require_product(
            db, tenant_id=tenant_context.current_tenant_id, product_id=promotion.product_id
        )
        item = update_promotion(
            db,
            promotion=promotion,
            payload=payload,
            action_context=build_action_context(request, tenant_context),
        )
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc
    db.commit()
    return ProductPromotionRead.model_validate(item)


@router.delete(
    "/promotions/{promotion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[REQUIRE_PROMOTION_MANAGE],
)
def delete_promotion_endpoint(
    promotion_id: str,
    request: Request,
    db: Session = DB_SESSION,
    tenant_context: TenantContext = TENANT_CONTEXT,
) -> None:
    try:
        promotion = require_promotion(db, promotion_id=promotion_id)
        require_product(
            db, tenant_id=tenant_context.current_tenant_id, product_id=promotion.product_id
        )
        delete_promotion(
            db,
            promotion=promotion,
            action_context=build_action_context(request, tenant_context),
        )
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc
    db.commit()
