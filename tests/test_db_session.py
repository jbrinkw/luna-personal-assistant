import sys
import types

if "agents" not in sys.modules:
    stub = types.SimpleNamespace(function_tool=lambda f: f)
    sys.modules["agents"] = stub

from db.db_functions import db_session

def test_db_session_closes_connection():
    with db_session(verbose=False) as (db, tables):
        assert db.conn is not None
        assert "inventory" in tables
    assert db.conn is None
