from __future__ import annotations

from sqlalchemy import inspect, text

revision = "0010"

PROD_ADR_COLUMNS = (
    ("id", "VARCHAR(36) PRIMARY KEY"),
    ("tenant_id", "VARCHAR(36) NOT NULL"),
    ("product_id", "VARCHAR(36) NOT NULL"),
    ("source_product_id", "VARCHAR(36)"),
    ("source_product_id_2", "VARCHAR(36)"),
    ("source_product_id_3", "VARCHAR(36)"),
    ("source_quantity_liters", "NUMERIC(10, 3)"),
    ("category", "VARCHAR(50)"),
    ("packaging_type", "VARCHAR(50)"),
    ("net_weight_kg", "NUMERIC(10, 2)"),
    ("net_volume_m3", "NUMERIC(10, 4)"),
    ("un_number", "VARCHAR(10)"),
    ("cargo_description", "TEXT"),
    ("label", "VARCHAR(50)"),
    ("tunnel_restriction", "VARCHAR(10)"),
    ("subline_id", "VARCHAR(36)"),
    ("factor", "INTEGER"),
    ("points", "INTEGER"),
    ("unit_measure", "VARCHAR(20)"),
    ("valid_from", "DATE NOT NULL"),
    ("valid_to", "DATE"),
    ("created_by", "VARCHAR(36) NOT NULL"),
    ("created_at", "TIMESTAMPTZ"),
)

PROD_ADR_INDEXES = (
    ("ix_prod_adr_tenant_id", "tenant_id"),
    ("ix_prod_adr_product_id", "product_id"),
    ("ix_prod_adr_source_product_id", "source_product_id"),
    ("ix_prod_adr_subline_id", "subline_id"),
    ("ix_prod_adr_created_by", "created_by"),
)


def upgrade(db) -> None:
    bind = db.connection()
    inspector = inspect(bind)

    if inspector.has_table("prod_adr"):
        bind.execute(text("DROP TABLE IF EXISTS prod_adr CASCADE"))

    if inspector.has_table("prod_groups"):
        columns = {column["name"] for column in inspector.get_columns("prod_groups")}
        if "gas_product_id" in columns:
            bind.execute(text("ALTER TABLE prod_groups DROP COLUMN gas_product_id"))
        for index_name in ("ix_prod_groups_gas_product_id",):
            bind.execute(text(f"DROP INDEX IF EXISTS {index_name}"))


def downgrade(db) -> None:
    bind = db.connection()
    inspector = inspect(bind)

    if inspector.has_table("prod_groups"):
        columns = {column["name"] for column in inspector.get_columns("prod_groups")}
        if "gas_product_id" not in columns:
            bind.execute(text("ALTER TABLE prod_groups ADD COLUMN gas_product_id VARCHAR(36)"))

    if not inspector.has_table("prod_adr"):
        columns_sql = ", ".join(f"{name} {definition}" for name, definition in PROD_ADR_COLUMNS)
        bind.execute(text(f"CREATE TABLE prod_adr ({columns_sql})"))
        for index_name, column in PROD_ADR_INDEXES:
            bind.execute(
                text(f"CREATE INDEX IF NOT EXISTS {index_name} ON prod_adr ({column})")
            )
        bind.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_prod_adr_prod_valid "
                "ON prod_adr (product_id, valid_from DESC)"
            )
        )
