
from app.database import engine
from sqlalchemy import text

with engine.connect() as conexion:
    esquemas = conexion.execute(text("""
        SELECT schema_name
        FROM information_schema.schemata
        WHERE schema_name IN ('schema_testing', 'schema_production')
        ORDER BY schema_name
    """)).fetchall()

    print("Esquemas encontrados:")
    for fila in esquemas:
        print(fila[0])

    print("\nTablas de cada esquema:")
    tablas = conexion.execute(text("""
        SELECT schemaname, tablename
        FROM pg_catalog.pg_tables
        WHERE schemaname IN ('schema_testing', 'schema_production')
        ORDER BY schemaname, tablename
    """)).fetchall()

    for esquema, tabla in tablas:
        print(f"{esquema}.{tabla}")