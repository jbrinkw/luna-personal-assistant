#!/usr/bin/env python3
"""
Test PostgreSQL connection and configuration.
This script helps diagnose connection issues and provides setup guidance.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

def test_environment():
    """Test if environment variables are properly set"""
    print("🔍 Checking environment variables...")
    
    required_vars = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
    missing_vars = []
    
    for var in required_vars:
        value = os.environ.get(var)
        if not value:
            missing_vars.append(var)
            print(f"❌ {var}: Not set")
        else:
            if var == 'DB_PASSWORD':
                print(f"✅ {var}: {'*' * len(value)}")
            else:
                print(f"✅ {var}: {value}")
    
    if missing_vars:
        print(f"\n⚠️  Missing environment variables: {', '.join(missing_vars)}")
        print("\nTo fix this, either:")
        print("1. Set environment variables:")
        for var in missing_vars:
            if var == 'DB_PASSWORD':
                print(f"   export {var}=your_password_here")
            else:
                print(f"   export {var}=value")
        print("\n2. Or create a .env file with:")
        print("   DB_HOST=192.168.0.239")
        print("   DB_PORT=5432")
        print("   DB_NAME=workout_tracker")
        print("   DB_USER=postgres")
        print("   DB_PASSWORD=your_password_here")
        return False
    
    return True

def test_connection():
    """Test actual database connection"""
    print("\n🔌 Testing database connection...")
    
    try:
        import psycopg2
        from db_config import get_db_config
        
        config = get_db_config()
        print(f"Attempting to connect to {config['host']}:{config['port']}")
        
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            database=config['database'],
            user=config['user'],
            password=config['password']
        )
        
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        print(f"✅ Connected successfully!")
        print(f"   PostgreSQL version: {version}")
        
        cur.close()
        conn.close()
        return True
        
    except psycopg2.OperationalError as e:
        print(f"❌ Connection failed: {e}")
        return False
    except ImportError:
        print("❌ psycopg2 not installed. Run: pip install psycopg2-binary")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_database_setup():
    """Test if database schema exists"""
    print("\n🏗️  Testing database schema...")
    
    try:
        import psycopg2
        from db_config import get_db_config
        
        config = get_db_config()
        conn = psycopg2.connect(**config)
        cur = conn.cursor()
        
        # Check if tables exist
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('exercises', 'daily_logs', 'planned_sets', 'completed_sets')
        """)
        
        existing_tables = [row[0] for row in cur.fetchall()]
        required_tables = ['exercises', 'daily_logs', 'planned_sets', 'completed_sets']
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        if missing_tables:
            print(f"❌ Missing tables: {', '.join(missing_tables)}")
            print("Run: python -c \"import db; db.init_db(sample=True)\"")
            cur.close()
            conn.close()
            return False
        else:
            print("✅ All required tables exist")
            
            # Check for sample data
            cur.execute("SELECT COUNT(*) FROM exercises")
            exercise_count = cur.fetchone()[0]
            print(f"   Exercises in database: {exercise_count}")
            
            cur.close()
            conn.close()
            return True
            
    except Exception as e:
        print(f"❌ Schema test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 PostgreSQL Connection Test")
    print("=" * 40)
    
    # Test 1: Environment variables
    env_ok = test_environment()
    
    if not env_ok:
        print("\n💡 Quick fix: Create a .env file in the coachbyte directory with:")
        print("DB_HOST=192.168.0.239")
        print("DB_PORT=5432")
        print("DB_NAME=workout_tracker")
        print("DB_USER=postgres")
        print("DB_PASSWORD=your_actual_password")
        return
    
    # Test 2: Connection
    conn_ok = test_connection()
    
    if not conn_ok:
        print("\n💡 Connection troubleshooting:")
        print("1. Verify PostgreSQL is running on 192.168.0.239:5432")
        print("2. Check if the password is correct")
        print("3. Ensure network connectivity: ping 192.168.0.239")
        print("4. Check firewall settings")
        return
    
    # Test 3: Schema
    schema_ok = test_database_setup()
    
    if schema_ok:
        print("\n🎉 All tests passed! Your database is ready to use.")
    else:
        print("\n💡 To initialize the database, run:")
        print("python -c \"import db; db.init_db(sample=True)\"")

if __name__ == "__main__":
    main() 