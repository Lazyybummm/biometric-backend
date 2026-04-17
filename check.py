import psycopg2

try:
    # ✅ Updated connection string
    conn = psycopg2.connect(
        "postgresql://grid:strongpassword@187.127.139.208:5432/app_db",
        connect_timeout=5
    )

    cur = conn.cursor()

    # ✅ Test query
    cur.execute("SELECT * FROM users;")
    rows = cur.fetchall()

    print("✅ Connected successfully!")
    print("Data:", rows)

    cur.close()
    conn.close()

except Exception as e:
    print("❌ Error:", e)