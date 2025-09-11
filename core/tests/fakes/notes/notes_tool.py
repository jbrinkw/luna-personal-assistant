"""Auto-generated fake tools for tests. DO NOT EDIT BY HAND."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


NAME = "Notes"

SYSTEM_PROMPT = """Support the user's note-taking and project documentation in an Obsidian-style vault.
Understand projects (via project_id/frontmatter), read/update Notes.md entries by date,
and return structured results when possible.

Prefer precise operations: when asked to update notes, find or create today's entry,
optionally place content under a specified markdown section."""



def NOTES_GET_project_hierarchy(base_dir: 'Optional[str]' = None):
	"""Return a simplified hierarchy: root names and immediate child names only.
    Example: "show my project hierarchy"
    Example Response: "Eco AI
- Roadmap
- Research"
    Example: {"base_dir": "string[optional override path]"}
    
	"""
	return '"Eco AI'


def NOTES_GET_project_text(project_id: 'str', base_dir: 'Optional[str]' = None):
	"""Return the root project page text and note page text for a given project_id or display name.
Example: "show the text for project Eco AI"
Example Response: {"project_id": "Eco AI", "root_page_path": "...", "root_page_text": "# Eco AI ...", "note_page_path": "...", "note_page_text": "..."}
Example: {"project_id": "string[id or display name]", "base_dir": "string[optional path]"}
	"""
	return '{"project_id": "Eco AI", "root_page_path": "...", "root_page_text": "# Eco AI ...", "note_page_path": "...", "note_page_text": "..."}'


def NOTES_GET_notes_by_date_range(start_date: 'str', end_date: 'str', base_dir: 'Optional[str]' = None):
	"""Return dated note entries within [start_date, end_date] (MM/DD/YY), newest-first.
Example: "find my notes between 06/01/24 and 06/15/24"
Example Response: {"start_date": "06/01/24", "end_date": "06/15/24", "entries": [{"file": "...Notes.md", "date": "2024-06-01", "date_str": "6/1/24", "content": "..."}]}
Example: {"start_date": "string[MM/DD/YY]", "end_date": "string[MM/DD/YY]", "base_dir": "string[optional path]"}
	"""
	return '{"start_date": "06/01/24", "end_date": "06/15/24", "entries": [{"file": "...Notes.md", "date": "2024-06-01", "date_str": "6/1/24", "content": "..."}]}'


def NOTES_UPDATE_project_note(project_id: 'str', content: 'str', section_id: 'Optional[str]' = None, base_dir: 'Optional[str]' = None):
	"""Append content to today's dated note entry for a project. Creates file/entry if needed.
Example: "add 'ship MVP' under 'Milestones' for project Eco AI"
Example Response: {"project_id": "Eco AI", "note_file": ".../Notes.md", "created_file": false, "created_entry": true, "appended": true, "date_str": "6/1/24"}
Example: {"project_id": "string[id or display name]", "content": "string[text to append]", "section_id": "string[optional section]", "base_dir": "string[optional path]"}
	"""
	return '{"project_id": "Eco AI", "note_file": ".../Notes.md", "created_file": false, "created_entry": true, "appended": true, "date_str": "6/1/24"}'


TOOLS = [
	NOTES_GET_project_hierarchy,
	NOTES_GET_project_text,
	NOTES_GET_notes_by_date_range,
	NOTES_UPDATE_project_note
]
