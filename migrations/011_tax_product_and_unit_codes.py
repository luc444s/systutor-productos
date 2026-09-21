from __future__ import annotations

from sqlalchemy import inspect, text

revision = "0011"

TAX_UNITS = (
    ("NIU", "Unidad"),
    ("KGM", "Kilogramo"),
    ("GRM", "Gramo"),
    ("LTR", "Litro"),
    ("MLT", "Mililitro"),
    ("MTR", "Metro"),
    ("MTK", "Metro cuadrado"),
    ("MTQ", "Metro cubico"),
    ("HUR", "Hora"),
    ("DAY", "Dia"),
    ("ZZ", "Unidad de servicio"),
)

TAX_PRODUCTS_BY_LINE = {
    "BEBIDAS": (
        ("50202301", "Agua"),
        ("50202306", "Refrescos"),
        ("50202305", "Jugo fresco"),
        ("50202304", "Jugos de repisa"),
        ("50202309", "Bebidas deportivas o de energia"),
        ("50202310", "Agua mineral"),
        ("50202311", "Bebida mixta de polvo"),
        ("50202201", "Cerveza"),
        ("50201706", "Cafe"),
        ("50201710", "Te de hoja"),
    ),
    "ABARROTES": (
        ("50221101", "Grano de cereal"),
        ("50192901", "Pasta sencilla o fideos"),
        ("50192902", "Pasta o fideos de repisa"),
        ("50151513", "Aceites vegetales comestibles"),
        ("50221301", "Harina vegetal"),
        ("50221303", "Almidon o harina comestible"),
        ("50161509", "Azucares naturales o endulzantes"),
        ("50192403", "Miel"),
        ("50131704", "Leche en polvo"),
    ),
    "CONSERVAS": (
        ("50467007", "Atun enlatada"),
        ("50121901", "Pulpo en escabeche"),
        ("50121902", "Huevos de abadejo salado"),
        ("50121903", "Camaron salado"),
        ("50192401", "Mermeladas o preservativos de fruta"),
    ),
    "DESAYUNO": (
        ("50201709", "Cafe instantaneo"),
        ("50201713", "Bolsas de te"),
        ("50221201", "Listo para comer o cereal caliente"),
        ("50131704", "Leche en polvo"),
        ("50201706", "Cafe"),
        ("50192403", "Miel"),
    ),
    "GALLETAS": (
        ("50181903", "Galletas sencillas de sal"),
        ("50181905", "Galletas de dulce"),
        ("50181909", "Galletas de soda"),
        ("50182005", "Galletas de arroz"),
        ("50181904", "Pan seco o cascaras de pan o pan tostado"),
    ),
    "GOLOSINAS": (
        ("50161813", "Chocolate o sustituto de chocolate, confite"),
        ("50161814", "Azucar o sustituto de azucar, confite"),
        ("50161815", "Goma de mascar"),
        ("50161511", "Chocolate o sustituto de chocolate"),
    ),
    "HIGIENE": (
        ("53131608", "Jabones"),
        ("53131606", "Desodorantes"),
        ("53131602", "Articulos para el cuidado del cabello"),
        ("53131604", "Cepillos o peinillas para el cabello"),
        ("53131609", "Productos de proteccion solar"),
        ("53131612", "Geles de bano"),
    ),
    "LACTEOS": (
        ("50131701", "Productos de leche o mantequilla frescos"),
        ("50131702", "Productos de leche o mantequilla de estante"),
        ("50131801", "Queso natural"),
        ("50131802", "Queso procesado"),
        ("50131704", "Leche en polvo"),
    ),
    "LIMPIEZA": (
        ("47131801", "Limpiadores de pisos"),
        ("47131803", "Desinfectantes para uso domestico"),
        ("47131805", "Limpiadores de proposito general"),
        ("47131807", "Blanqueadores"),
        ("47131811", "Productos de lavanderia"),
        ("47131810", "Productos para el lavaplatos"),
        ("47121803", "Esponjas o esponjillas"),
        ("47121804", "Baldes para limpieza"),
    ),
    "PANIFICADOS": (
        ("50181901", "Pan fresco"),
        ("50181902", "Pan congelado"),
        ("50181906", "Pan de repisa"),
        ("50181904", "Pan seco o cascaras de pan o pan tostado"),
    ),
    "SALSAS": (
        ("50171830", "Salsas o condimentos o cremas de untar o marinados"),
        ("50171831", "Salsas para cocinar"),
        ("50171832", "Salsas para ensaladas o dips"),
        ("50171833", "Cremas de untar saladas o pates"),
    ),
    "SNACKS": (
        ("50192109", "Papas fritas de talego o mezclas"),
        ("50192110", "Nueces o fruta disecada"),
        ("50192112", "Maiz pira"),
        ("50192111", "Carne seca o procesada"),
    ),
}


def upgrade(db) -> None:
    bind = db.connection()
    inspector = inspect(bind)

    bind.execute(text("""
        CREATE TABLE IF NOT EXISTS tax_products (
            id VARCHAR(36) PRIMARY KEY,
            scheme VARCHAR(20) NOT NULL DEFAULT 'UNSPSC',
            code VARCHAR(20) NOT NULL,
            description VARCHAR(255) NOT NULL,
            segment_code VARCHAR(8),
            segment_name VARCHAR(255),
            family_code VARCHAR(8),
            family_name VARCHAR(255),
            class_code VARCHAR(8),
            class_name VARCHAR(255),
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_tax_product_scheme_code UNIQUE (scheme, code)
        )
    """))
    bind.execute(text("""
        CREATE TABLE IF NOT EXISTS tax_product_hints (
            scheme VARCHAR(20) NOT NULL DEFAULT 'UNSPSC',
            code VARCHAR(20) NOT NULL,
            hint_level VARCHAR(20) NOT NULL,
            hint_value VARCHAR(60) NOT NULL,
            PRIMARY KEY (scheme, code, hint_level, hint_value)
        )
    """))
    bind.execute(text("""
        CREATE TABLE IF NOT EXISTS tax_units (
            id VARCHAR(36) PRIMARY KEY,
            scheme VARCHAR(20) NOT NULL DEFAULT 'SUNAT_03',
            code VARCHAR(10) NOT NULL,
            name VARCHAR(100) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_tax_unit_scheme_code UNIQUE (scheme, code)
        )
    """))

    _add_column_if_missing(inspector, bind, "prod_products", "tax_product_code", "VARCHAR(20)")
    _add_column_if_missing(inspector, bind, "prod_products", "tax_product_scheme", "VARCHAR(20)")
    _add_column_if_missing(inspector, bind, "prod_units", "tax_unit_code", "VARCHAR(10)")
    _add_column_if_missing(inspector, bind, "prod_units", "tax_unit_scheme", "VARCHAR(20)")

    for code, name in TAX_UNITS:
        bind.execute(
            text("""
                INSERT INTO tax_units (id, scheme, code, name)
                VALUES (:id, 'SUNAT_03', :code, :name)
                ON CONFLICT (scheme, code) DO UPDATE SET name = EXCLUDED.name, updated_at = now()
            """),
            {"id": f"SUNAT_03-{code}", "code": code, "name": name},
        )

    products: dict[str, str] = {}
    for line, entries in TAX_PRODUCTS_BY_LINE.items():
        for code, description in entries:
            products.setdefault(code, description)
            bind.execute(
                text("""
                    INSERT INTO tax_product_hints (scheme, code, hint_level, hint_value)
                    VALUES ('UNSPSC', :code, 'line', :line)
                    ON CONFLICT (scheme, code, hint_level, hint_value) DO NOTHING
                """),
                {"code": code, "line": line},
            )
    for code, description in products.items():
        bind.execute(
            text("""
                INSERT INTO tax_products (id, scheme, code, description)
                VALUES (:id, 'UNSPSC', :code, :description)
                ON CONFLICT (scheme, code) DO UPDATE
                SET description = EXCLUDED.description, updated_at = now()
            """),
            {"id": f"UNSPSC-{code}", "code": code, "description": description},
        )


def downgrade(db) -> None:
    bind = db.connection()
    inspector = inspect(bind)

    _drop_column_if_exists(inspector, bind, "prod_units", "tax_unit_scheme")
    _drop_column_if_exists(inspector, bind, "prod_units", "tax_unit_code")
    _drop_column_if_exists(inspector, bind, "prod_products", "tax_product_scheme")
    _drop_column_if_exists(inspector, bind, "prod_products", "tax_product_code")
    bind.execute(text("DROP TABLE IF EXISTS tax_product_hints"))
    bind.execute(text("DROP TABLE IF EXISTS tax_products"))
    bind.execute(text("DROP TABLE IF EXISTS tax_units"))


def _add_column_if_missing(inspector, bind, table_name: str, column_name: str, definition: str) -> None:
    if not inspector.has_table(table_name):
        return
    columns = {column["name"] for column in inspector.get_columns(table_name)}
    if column_name not in columns:
        bind.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"))


def _drop_column_if_exists(inspector, bind, table_name: str, column_name: str) -> None:
    if not inspector.has_table(table_name):
        return
    columns = {column["name"] for column in inspector.get_columns(table_name)}
    if column_name in columns:
        bind.execute(text(f"ALTER TABLE {table_name} DROP COLUMN {column_name}"))
