"""
Comprehensive Database Tests for Luna
Tests Postgres database operations for automation_memory extension
"""
import pytest
import psycopg
import os
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Load environment
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


def get_db_conninfo():
    """Get database connection string from environment."""
    host = os.getenv('DB_HOST', os.getenv('PGHOST', '127.0.0.1'))
    port = os.getenv('DB_PORT', os.getenv('PGPORT', '5432'))
    database = os.getenv('DB_NAME', os.getenv('PGDATABASE', 'luna'))
    user = os.getenv('DB_USER', os.getenv('PGUSER', 'postgres'))
    password = os.getenv('DB_PASSWORD', os.getenv('PGPASSWORD', ''))
    
    return f"host={host} port={port} dbname={database} user={user} password={password}"


@pytest.fixture(scope="session")
def db_connection():
    """Create a database connection for the test session."""
    conninfo = get_db_conninfo()
    try:
        conn = psycopg.connect(conninfo)
        yield conn
        conn.close()
    except psycopg.Error as e:
        pytest.skip(f"Database not available: {e}")


@pytest.fixture
def db_cursor(db_connection):
    """Create a cursor for each test."""
    cursor = db_connection.cursor()
    yield cursor
    db_connection.commit()
    cursor.close()


@pytest.fixture(autouse=True)
def cleanup_test_data(db_connection, db_cursor):
    """Clean up test data after each test."""
    yield
    # Rollback any failed transactions
    try:
        db_connection.rollback()
    except:
        pass
    # Clean up test data
    try:
        db_cursor.execute("DELETE FROM task_flows WHERE call_name LIKE 'test_%'")
        db_cursor.execute("DELETE FROM scheduled_prompts WHERE prompt LIKE 'TEST:%'")
        db_cursor.execute("DELETE FROM memories WHERE content LIKE 'TEST:%'")
        db_connection.commit()
    except:
        db_connection.rollback()


class TestDatabaseConnection:
    """Test basic database connectivity."""
    
    def test_can_connect(self, db_connection):
        """Test that we can connect to the database."""
        assert db_connection is not None
        assert not db_connection.closed
    
    def test_database_name(self, db_cursor):
        """Test that we're connected to the correct database."""
        db_cursor.execute("SELECT current_database()")
        db_name = db_cursor.fetchone()[0]
        expected_db = os.getenv('DB_NAME', os.getenv('PGDATABASE', 'luna'))
        assert db_name == expected_db
    
    def test_tables_exist(self, db_cursor):
        """Test that all required tables exist."""
        db_cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = [row[0] for row in db_cursor.fetchall()]
        
        assert 'task_flows' in tables
        assert 'scheduled_prompts' in tables
        assert 'memories' in tables


class TestTaskFlows:
    """Test task_flows table operations."""
    
    def test_create_task_flow(self, db_cursor):
        """Test creating a task flow."""
        db_cursor.execute("""
            INSERT INTO task_flows (call_name, prompts, agent)
            VALUES (%s, %s, %s)
            RETURNING id
        """, ('test_flow_1', json.dumps(['prompt 1', 'prompt 2']), 'simple_agent'))
        
        flow_id = db_cursor.fetchone()[0]
        assert flow_id is not None
    
    def test_read_task_flow(self, db_cursor):
        """Test reading a task flow."""
        # Create
        db_cursor.execute("""
            INSERT INTO task_flows (call_name, prompts, agent)
            VALUES (%s, %s, %s)
            RETURNING id
        """, ('test_flow_2', json.dumps(['prompt 1']), 'passthrough_agent'))
        flow_id = db_cursor.fetchone()[0]
        
        # Read
        db_cursor.execute("SELECT call_name, prompts, agent FROM task_flows WHERE id = %s", (flow_id,))
        result = db_cursor.fetchone()
        
        assert result[0] == 'test_flow_2'
        assert result[1] == ['prompt 1']
        assert result[2] == 'passthrough_agent'
    
    def test_update_task_flow(self, db_cursor):
        """Test updating a task flow."""
        # Create
        db_cursor.execute("""
            INSERT INTO task_flows (call_name, prompts, agent)
            VALUES (%s, %s, %s)
            RETURNING id
        """, ('test_flow_3', json.dumps(['old prompt']), 'simple_agent'))
        flow_id = db_cursor.fetchone()[0]
        
        # Update
        db_cursor.execute("""
            UPDATE task_flows 
            SET prompts = %s, agent = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (json.dumps(['new prompt']), 'passthrough_agent', flow_id))
        
        # Verify
        db_cursor.execute("SELECT prompts, agent FROM task_flows WHERE id = %s", (flow_id,))
        result = db_cursor.fetchone()
        assert result[0] == ['new prompt']
        assert result[1] == 'passthrough_agent'
    
    def test_delete_task_flow(self, db_cursor):
        """Test deleting a task flow."""
        # Create
        db_cursor.execute("""
            INSERT INTO task_flows (call_name, prompts, agent)
            VALUES (%s, %s, %s)
            RETURNING id
        """, ('test_flow_4', json.dumps([]), 'simple_agent'))
        flow_id = db_cursor.fetchone()[0]
        
        # Delete
        db_cursor.execute("DELETE FROM task_flows WHERE id = %s", (flow_id,))
        
        # Verify
        db_cursor.execute("SELECT COUNT(*) FROM task_flows WHERE id = %s", (flow_id,))
        count = db_cursor.fetchone()[0]
        assert count == 0
    
    def test_unique_call_name(self, db_cursor):
        """Test that call_name must be unique."""
        db_cursor.execute("""
            INSERT INTO task_flows (call_name, prompts, agent)
            VALUES (%s, %s, %s)
        """, ('test_unique_flow', json.dumps([]), 'simple_agent'))
        
        # Try to insert duplicate
        with pytest.raises(psycopg.errors.UniqueViolation):
            db_cursor.execute("""
                INSERT INTO task_flows (call_name, prompts, agent)
                VALUES (%s, %s, %s)
            """, ('test_unique_flow', json.dumps([]), 'simple_agent'))


class TestScheduledPrompts:
    """Test scheduled_prompts table operations."""
    
    def test_create_schedule(self, db_cursor):
        """Test creating a scheduled prompt."""
        db_cursor.execute("""
            INSERT INTO scheduled_prompts (time_of_day, days_of_week, prompt, agent, enabled)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, ('09:00', json.dumps([True, True, True, True, True, False, False]), 
              'TEST: Morning check', 'simple_agent', True))
        
        schedule_id = db_cursor.fetchone()[0]
        assert schedule_id is not None
    
    def test_read_schedule(self, db_cursor):
        """Test reading a scheduled prompt."""
        # Create
        db_cursor.execute("""
            INSERT INTO scheduled_prompts (time_of_day, days_of_week, prompt, agent, enabled)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, ('14:30', json.dumps([False, False, False, False, False, True, True]),
              'TEST: Weekend task', 'passthrough_agent', False))
        schedule_id = db_cursor.fetchone()[0]
        
        # Read
        db_cursor.execute("""
            SELECT time_of_day, days_of_week, prompt, agent, enabled 
            FROM scheduled_prompts WHERE id = %s
        """, (schedule_id,))
        result = db_cursor.fetchone()
        
        assert result[0] == '14:30'
        assert result[1] == [False, False, False, False, False, True, True]
        assert result[2] == 'TEST: Weekend task'
        assert result[3] == 'passthrough_agent'
        assert result[4] == False
    
    def test_toggle_enabled(self, db_cursor):
        """Test toggling the enabled flag."""
        # Create
        db_cursor.execute("""
            INSERT INTO scheduled_prompts (time_of_day, days_of_week, prompt, agent, enabled)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, ('10:00', json.dumps([True]*7), 'TEST: Daily task', 'simple_agent', True))
        schedule_id = db_cursor.fetchone()[0]
        
        # Toggle off
        db_cursor.execute("UPDATE scheduled_prompts SET enabled = FALSE WHERE id = %s", (schedule_id,))
        db_cursor.execute("SELECT enabled FROM scheduled_prompts WHERE id = %s", (schedule_id,))
        assert db_cursor.fetchone()[0] == False
        
        # Toggle on
        db_cursor.execute("UPDATE scheduled_prompts SET enabled = TRUE WHERE id = %s", (schedule_id,))
        db_cursor.execute("SELECT enabled FROM scheduled_prompts WHERE id = %s", (schedule_id,))
        assert db_cursor.fetchone()[0] == True


class TestMemories:
    """Test memories table operations."""
    
    def test_create_memory(self, db_cursor):
        """Test creating a memory."""
        db_cursor.execute("""
            INSERT INTO memories (content)
            VALUES (%s)
            RETURNING id
        """, ('TEST: This is a test memory',))
        
        memory_id = db_cursor.fetchone()[0]
        assert memory_id is not None
    
    def test_read_memory(self, db_cursor):
        """Test reading a memory."""
        # Create
        test_content = 'TEST: Important information to remember'
        db_cursor.execute("""
            INSERT INTO memories (content)
            VALUES (%s)
            RETURNING id
        """, (test_content,))
        memory_id = db_cursor.fetchone()[0]
        
        # Read
        db_cursor.execute("SELECT content FROM memories WHERE id = %s", (memory_id,))
        result = db_cursor.fetchone()
        assert result[0] == test_content
    
    def test_update_memory(self, db_cursor):
        """Test updating a memory."""
        # Create
        db_cursor.execute("""
            INSERT INTO memories (content)
            VALUES (%s)
            RETURNING id
        """, ('TEST: Original content',))
        memory_id = db_cursor.fetchone()[0]
        
        # Update
        new_content = 'TEST: Updated content'
        db_cursor.execute("""
            UPDATE memories SET content = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (new_content, memory_id))
        
        # Verify
        db_cursor.execute("SELECT content FROM memories WHERE id = %s", (memory_id,))
        assert db_cursor.fetchone()[0] == new_content
    
    def test_list_memories(self, db_cursor):
        """Test listing memories."""
        # Create multiple
        for i in range(3):
            db_cursor.execute("""
                INSERT INTO memories (content)
                VALUES (%s)
            """, (f'TEST: Memory {i+1}',))
        
        # List
        db_cursor.execute("SELECT content FROM memories WHERE content LIKE 'TEST:%' ORDER BY id")
        results = db_cursor.fetchall()
        assert len(results) >= 3


class TestTimestamps:
    """Test timestamp handling."""
    
    def test_created_at_auto_set(self, db_cursor):
        """Test that created_at is automatically set."""
        db_cursor.execute("""
            INSERT INTO memories (content)
            VALUES (%s)
            RETURNING id, created_at
        """, ('TEST: Timestamp test',))
        
        result = db_cursor.fetchone()
        assert result[1] is not None
        assert isinstance(result[1], datetime)
    
    def test_updated_at_auto_set(self, db_cursor):
        """Test that updated_at is automatically set."""
        db_cursor.execute("""
            INSERT INTO memories (content)
            VALUES (%s)
            RETURNING id, updated_at
        """, ('TEST: Timestamp test',))
        
        result = db_cursor.fetchone()
        assert result[1] is not None
        assert isinstance(result[1], datetime)
    
    def test_timestamps_are_utc(self, db_cursor):
        """Test that timestamps are stored in UTC."""
        db_cursor.execute("""
            INSERT INTO memories (content)
            VALUES (%s)
            RETURNING created_at
        """, ('TEST: UTC test',))
        
        created_at = db_cursor.fetchone()[0]
        # TIMESTAMPTZ includes timezone info
        assert created_at.tzinfo is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

