from __future__ import annotations

from sqlalchemy import text

revision = "0012"


def upgrade(db) -> None:
    bind = db.connection()
    rows = bind.execute(
        text("""
            SELECT id, tenant_id, legacy_id, sku
            FROM prod_products
            WHERE sku ~ '^[0-9]+$'
              AND length(sku) IN (8, 12, 13, 14)
            ORDER BY tenant_id, created_at, id
        """)
    ).mappings().all()

    tenant_skus: dict[str, set[str]] = {}
    for row in bind.execute(text("SELECT tenant_id, sku FROM prod_products")).mappings():
        tenant_skus.setdefault(row["tenant_id"], set()).add(row["sku"])
    tenant_next_indexes = {
        tenant_id: _next_numeric_sku_index(skus) for tenant_id, skus in tenant_skus.items()
    }

    for row in rows:
        tenant_id = row["tenant_id"]
        product_id = row["id"]
        sku = row["sku"]
        identical_barcode = bind.execute(
            text("""
                SELECT id, product_id, is_primary
                FROM prod_barcodes
                WHERE tenant_id = :tenant_id AND barcode = :barcode
                LIMIT 1
            """),
            {"tenant_id": tenant_id, "barcode": sku},
        ).mappings().first()
        primary_barcode = bind.execute(
            text("""
                SELECT id, barcode
                FROM prod_barcodes
                WHERE product_id = :product_id AND is_primary = true
                LIMIT 1
            """),
            {"product_id": product_id},
        ).mappings().first()

        if identical_barcode is None and (
            primary_barcode is None or primary_barcode["barcode"] == sku
        ):
            if primary_barcode is None:
                bind.execute(
                    text("""
                        UPDATE prod_barcodes
                        SET is_primary = false, updated_at = now()
                        WHERE product_id = :product_id AND is_primary = true
                    """),
                    {"product_id": product_id},
                )
            bind.execute(
                text("""
                    INSERT INTO prod_barcodes (
                        id, tenant_id, product_id, barcode_type, barcode,
                        is_primary, is_active, created_at, updated_at
                    )
                    VALUES (
                        :id, :tenant_id, :product_id, 'GS1', :barcode,
                        true, true, now(), now()
                    )
                    ON CONFLICT (tenant_id, barcode_type, barcode) DO NOTHING
                """),
                {
                    "id": _barcode_id(product_id, sku),
                    "tenant_id": tenant_id,
                    "product_id": product_id,
                    "barcode": sku,
                },
            )
        elif (
            identical_barcode is not None
            and identical_barcode["product_id"] == product_id
            and primary_barcode is None
        ):
            bind.execute(
                text("""
                    UPDATE prod_barcodes
                    SET is_primary = true, updated_at = now()
                    WHERE id = :id
                """),
                {"id": identical_barcode["id"]},
            )

        new_sku = _generated_sku(
            tenant_skus.setdefault(tenant_id, set()),
            tenant_next_indexes,
            tenant_id,
        )
        tenant_skus[tenant_id].discard(sku)
        tenant_skus[tenant_id].add(new_sku)
        bind.execute(
            text("""
                UPDATE prod_products
                SET sku = :new_sku, updated_at = now()
                WHERE id = :product_id AND sku = :old_sku
            """),
            {"product_id": product_id, "old_sku": sku, "new_sku": new_sku},
        )


def downgrade(db) -> None:
    # Data migration is intentionally not reversed to avoid deleting real barcodes
    # or restoring barcode-like SKUs after users have edited products.
    return None


def _generated_sku(
    existing: set[str],
    tenant_next_indexes: dict[str, int],
    tenant_id: str,
) -> str:
    index = tenant_next_indexes.get(tenant_id, 1)
    while True:
        candidate = f"PROD-{index:06d}"
        tenant_next_indexes[tenant_id] = index + 1
        if candidate not in existing:
            return candidate
        index += 1


def _next_numeric_sku_index(existing: set[str]) -> int:
    max_index = 0
    for sku in existing:
        if sku.startswith("PROD-") and sku[5:].isdigit():
            max_index = max(max_index, int(sku[5:]))
    return max_index + 1


def _barcode_id(product_id: str, sku: str) -> str:
    normalized = str(product_id).replace("-", "")[:20]
    return f"SKU{normalized}{sku}"[:36]
