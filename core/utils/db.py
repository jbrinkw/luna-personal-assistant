"""Database utilities for Luna - Postgres connection pool and helpers.

All timestamps are stored in UTC (TIMESTAMPTZ) and should be displayed in America/New_York timezone.
"""
import os
from typing import Optional, Any, Dict, List
from datetime import datetime
import psycopg
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


class Database:
    """Postgres connection pool manager."""
    
    def __init__(self):
        self._pool: Optional[ConnectionPool] = None
        self._initialized = False
    
    def initialize(self, minconn: int = 1, maxconn: int = 10):
        """Initialize the connection pool with database credentials from environment."""
        if self._initialized:
            return
        
        # Build connection string for psycopg3
        host = os.getenv('DB_HOST', os.getenv('PGHOST', os.getenv('POSTGRES_HOST', '127.0.0.1')))
        port = os.getenv('DB_PORT', os.getenv('PGPORT', '5432'))
        database = os.getenv('DB_NAME', os.getenv('PGDATABASE', 'luna'))
        user = os.getenv('DB_USER', os.getenv('PGUSER', 'postgres'))
        password = os.getenv('DB_PASSWORD', os.getenv('PGPASSWORD', ''))
        
        conninfo = f"host={host} port={port} dbname={database} user={user} password={password}"
        
        self._pool = ConnectionPool(conninfo, min_size=minconn, max_size=maxconn)
        self._initialized = True
    
    def get_connection(self):
        """Get a connection from the pool."""
        if not self._initialized:
            self.initialize()
        return self._pool.getconn()
    
    def put_connection(self, conn):
        """Return a connection to the pool."""
        if self._pool:
            self._pool.putconn(conn)
    
    def execute(self, query: str, params: Optional[tuple] = None, fetch: bool = True) -> Optional[List[Dict[str, Any]]]:
        """Execute a query and optionally fetch results as list of dicts."""
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(query, params or ())
                if fetch:
                    results = cursor.fetchall()
                    return [dict(row) for row in results]
                else:
                    conn.commit()
                    return None
        finally:
            if conn:
                self.put_connection(conn)
    
    def execute_one(self, query: str, params: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
        """Execute a query and fetch a single result as dict."""
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(query, params or ())
                result = cursor.fetchone()
                return dict(result) if result else None
        finally:
            if conn:
                self.put_connection(conn)
    
    def close_all(self):
        """Close all connections in the pool."""
        if self._pool:
            self._pool.close()
            self._initialized = False


# Global database instance
db = Database()


def get_db() -> Database:
    """Get the global database instance."""
    return db


def utc_now() -> datetime:
    """Get current UTC timestamp."""
    return datetime.utcnow()


def format_ny_time(utc_timestamp: datetime) -> str:
    """Format a UTC timestamp for display in America/New_York timezone.
    
    Args:
        utc_timestamp: UTC datetime object
        
    Returns:
        Formatted string in NY timezone
    """
    try:
        import pytz
        ny_tz = pytz.timezone('America/New_York')
        ny_time = utc_timestamp.replace(tzinfo=pytz.UTC).astimezone(ny_tz)
        return ny_time.strftime('%Y-%m-%d %H:%M:%S %Z')
    except Exception:
        # Fallback if pytz not available
        return utc_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')


# ============================================================================
# Memory Functions
# ============================================================================

def fetch_all_memories() -> List[Dict[str, Any]]:
    """Fetch all memories from the database.
    
    Returns:
        List of memory dictionaries with id and content
    """
    return db.execute("SELECT id, content FROM memories ORDER BY id ASC") or []


def fetch_memory_by_id(memory_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a single memory by ID.
    
    Args:
        memory_id: The memory ID to fetch
        
    Returns:
        Memory dictionary or None if not found
    """
    return db.execute_one("SELECT id, content FROM memories WHERE id = %s", (memory_id,))
