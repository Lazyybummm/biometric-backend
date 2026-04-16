

import psycopg
from datetime import datetime

# ⚠️ Replace with your real DB URL or use env variable
DATABASE_URL = "postgresql://neondb_owner:npg_Z2IF5LQRSxuq@ep-autumn-dew-an4wsq8n-pooler.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require"

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_file = f"neon_backup_{timestamp}.sql"


def quote_ident(name):
    return '"' + name.replace('"', '""') + '"'


def get_table_columns(cur, table):
    cur.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position;
    """, (table,))
    return cur.fetchall()


def generate_create_table(table, columns):
    col_defs = []
    for col, dtype, nullable in columns:
        col_def = f'{quote_ident(col)} {dtype}'
        if nullable == "NO":
            col_def += " NOT NULL"
        col_defs.append(col_def)

    return f"CREATE TABLE {quote_ident(table)} (\n  " + ",\n  ".join(col_defs) + "\n);\n"


def export_db():
    print("🚀 Starting robust export...")

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:

            # Get all tables
            cur.execute("""
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public';
            """)
            tables = [row[0] for row in cur.fetchall()]

            with open(backup_file, "w", encoding="utf-8") as f:

                f.write("-- PostgreSQL database export\n")
                f.write(f"-- Generated at {timestamp}\n\n")

                for table in tables:
                    print(f"📦 Exporting {table}...")

                    qt = quote_ident(table)

                    # ---- CREATE TABLE ----
                    columns = get_table_columns(cur, table)
                    create_sql = generate_create_table(table, columns)

                    f.write(f"\n-- Table: {table}\n")
                    f.write(f"DROP TABLE IF EXISTS {qt} CASCADE;\n")
                    f.write(create_sql)

                    # ---- DATA EXPORT (COPY) ----
                    f.write(f"\nCOPY {qt} FROM STDIN WITH (FORMAT csv, NULL 'NULL');\n")

                    with conn.cursor() as copy_cur:
                        with copy_cur.copy(f"COPY {qt} TO STDOUT WITH CSV NULL 'NULL'") as copy:
                            for row in copy:
                                # ✅ FIX: convert memoryview → string
                                f.write(row.tobytes().decode("utf-8"))

                    f.write("\\.\n")  # End COPY block

    print(f"\n✅ Export completed: {backup_file}")


if __name__ == "__main__":
    export_db()