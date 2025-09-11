# Notes — User Guide

## Purpose
Support Obsidian-style project docs and Notes.md entries: project discovery, reading/writing note text, and querying dated entries.

## Tools

### `NOTES_GET_project_hierarchy`
- Summary: Return a simplified hierarchy: root names and immediate child names only.
- Example Prompt: show my project hierarchy
- Example Args: {"base_dir": "string(optional)"}
- Returns: plain-text hierarchy list.

### `NOTES_GET_project_text`
- Summary: Return the root project page text and note page text for a given project.
- Example Prompt: show the text for project Eco AI
- Example Args: {"project_id": "string[id or display name]", "base_dir": "string(optional)"}
- Returns: {"project_id", "root_page_path", "root_page_text", "note_page_path", "note_page_text"}.

### `NOTES_GET_notes_by_date_range`
- Summary: Return dated note entries within [start_date, end_date] (MM/DD/YY), newest-first.
- Example Prompt: find my notes between 06/01/24 and 06/15/24
- Example Args: {"start_date": "MM/DD/YY", "end_date": "MM/DD/YY", "base_dir": "string(optional)"}
- Returns: {"start_date", "end_date", "entries": [{"file", "date", "date_str", "content"}]}.

### `NOTES_UPDATE_project_note`
- Summary: Append content to today's dated note entry for a project (creates file/entry if needed).
- Example Prompt: add 'ship MVP' under 'Milestones' for project Eco AI
- Example Args: {"project_id": "string", "content": "string", "section_id": "string(optional)", "base_dir": "string(optional)"}
- Returns: {"project_id", "note_file", "created_file", "created_entry", "appended", "date_str"}.
