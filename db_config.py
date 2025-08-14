"""
Compatibility shim to expose db_config at repo root for legacy imports.
Delegates to core.shared.db_config.
"""

from core.shared.db_config import *  # noqa: F401,F403


