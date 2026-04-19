import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

# Connection string
DATABASE_URL = "postgresql://grid:strongpassword@187.127.139.208:5432/biometric"

def test_connection():
    """Test the database connection and display table information"""
    
    try:
        # Connect to the database
        print("🔌 Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        print("✅ Connected successfully!\n")
        
        # Create a cursor
        cur = conn.cursor()
        
        # 1. Check PostgreSQL version
        print("📊 PostgreSQL Version:")
        cur.execute("SELECT version();")
        version = cur.fetchone()
        print(f"   {version[0]}\n")
        
        # 2. List all tables in public schema
        print("📋 Tables in 'biometric' database:")
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = cur.fetchall()
        
        if tables:
            print(f"   Found {len(tables)} tables:")
            for table in tables:
                print(f"   - {table[0]}")
        else:
            print("   No tables found in public schema")
        
        print("\n" + "="*50 + "\n")
        
        # 3. Get row counts for each table
        print("📈 Row counts (should be 0 for empty tables):")
        for table in tables:
            table_name = table[0]
            cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table_name)))
            count = cur.fetchone()[0]
            print(f"   {table_name}: {count} row(s)")
        
        print("\n" + "="*50 + "\n")
        
        # 4. Check structure of 'users' table if it exists
        users_exists = any(table[0] == 'users' for table in tables)
        
        if users_exists:
            print("👥 Users table structure:")
            cur.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'users'
                ORDER BY ordinal_position;
            """)
            columns = cur.fetchall()
            for col in columns:
                print(f"   - {col[0]}: {col[1]} (nullable: {col[2]})")
        
        print("\n" + "="*50 + "\n")
        
        # 5. Sample query - get first 5 users if any exist
        if users_exists:
            cur.execute("SELECT id, name, email, role FROM users LIMIT 5;")
            users = cur.fetchall()
            
            if users:
                print("👤 Sample users (first 5):")
                for user in users:
                    print(f"   ID: {user[0]}, Name: {user[1]}, Email: {user[2]}, Role: {user[3]}")
            else:
                print("👤 No users found in the database (table is empty)")
        
        # 6. Check for any attendance records
        attendance_exists = any(table[0] == 'attendance_logs' for table in tables)
        
        if attendance_exists:
            cur.execute("SELECT COUNT(*) FROM attendance_logs;")
            attendance_count = cur.fetchone()[0]
            print(f"\n📅 Attendance records: {attendance_count}")
        
        # Close cursor and connection
        cur.close()
        conn.close()
        
        print("\n" + "="*50)
        print("✅ Database test completed successfully!")
        
    except psycopg2.OperationalError as e:
        print(f"❌ Connection failed: {e}")
        print("\nPossible issues:")
        print("   - Wrong host/IP address")
        print("   - Database port is not accessible")
        print("   - Username or password incorrect")
        print("   - Database 'biometric' doesn't exist")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def run_custom_query(query):
    """Run a custom query on the database"""
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        print(f"🔍 Running query: {query}\n")
        cur.execute(query)
        results = cur.fetchall()
        
        if results:
            print(f"📊 Results ({len(results)} row(s)):")
            for row in results:
                print(dict(row))
        else:
            print("No results found")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    # Run the main test
    test_connection()
    
    # Uncomment below to run a custom query
    # print("\n" + "="*50)
    # print("Running custom query...")
    # run_custom_query("SELECT * FROM tenants LIMIT 3;")