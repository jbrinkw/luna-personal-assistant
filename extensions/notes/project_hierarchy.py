#!/usr/bin/env python3
"""
Generate a hierarchy of projects from YAML frontmatter in Markdown files.

Rules:
- A "project" is any Markdown file whose frontmatter contains `project_id:`.
- Parent/child relationships are determined via `project_parent:` matching a parent's `project_id`.
- Depth is unbounded (recursive).
- For each project, print its human-friendly name and all frontmatter tags.
- If a corresponding notes file declares `note_project_id:` matching the project, include its path in the output.

Usage:
  python scripts/generate_project_hierarchy.py [BASE_DIR]

Defaults:
  BASE_DIR defaults to the Obsidian vault root: "Obsidian Vault"
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def read_frontmatter(file_path: Path) -> Tuple[Dict[str, str], int]:
    """Return (frontmatter_dict, end_line_idx) for YAML frontmatter at top of file.
    If no frontmatter, returns ({}, -1).
    Naive parser: lines between the first two '---' delimiters at the top.
    """
    try:
        text = file_path.read_text(encoding="utf-8")
    except Exception:
        return {}, -1

    lines = text.splitlines()
    if not lines:
        return {}, -1
    first = lines[0].lstrip("\ufeff").strip()
    if first != "---":
        return {}, -1

    fm: Dict[str, str] = {}
    end_idx = -1
    for idx in range(1, len(lines)):
        raw = lines[idx]
        line = raw.lstrip("\ufeff")
        if line.strip() == "---":
            end_idx = idx
            break
        if not line.strip():
            continue
        # naive key: value
        if ":" in line:
            key, value = line.split(":", 1)
            # strip inline comments after a space + '#'
            val = value.strip()
            if " #" in val:
                val = val.split(" #", 1)[0].rstrip()
            fm[key.strip()] = val
    return fm, end_idx


class Project:
    def __init__(self, project_id: str, file_path: Path, frontmatter: Dict[str, str]):
        self.project_id: str = project_id
        self.file_path: Path = file_path
        self.frontmatter: Dict[str, str] = frontmatter
        self.parent_id: Optional[str] = frontmatter.get("project_parent") or None
        self.children: List[str] = []  # child project_ids
        self.display_name: str = self._derive_display_name()
        self.note_file: Optional[Path] = None

    def _derive_display_name(self) -> str:
        # Prefer folder name if file stem equals folder name; else use file stem; fall back to project_id
        stem = self.file_path.stem
        parent = self.file_path.parent.name
        if stem.lower() == parent.lower():
            return parent
        return stem or self.project_id


def find_markdown_files(base_dir: Path) -> List[Path]:
    return list(base_dir.rglob("*.md"))


def build_projects(base_dir: Path) -> Dict[str, Project]:
    projects: Dict[str, Project] = {}
    for md_path in find_markdown_files(base_dir):
        fm, _ = read_frontmatter(md_path)
        pid = fm.get("project_id")
        if not pid:
            continue
        project = Project(pid, md_path, fm)
        if pid in projects:
            print(f"WARNING: duplicate project_id '{pid}' at {md_path} and {projects[pid].file_path}", file=sys.stderr)
        projects[pid] = project
    # Populate children
    for project in projects.values():
        if project.parent_id and project.parent_id in projects:
            projects[project.parent_id].children.append(project.project_id)
    # Sort children for stable output
    for project in projects.values():
        project.children.sort(key=lambda cid: projects[cid].display_name.lower())
    return projects


def link_notes(base_dir: Path, projects: Dict[str, Project]) -> None:
    # Look for notes files with `note_project_id:` frontmatter and link them
    for md_path in find_markdown_files(base_dir):
        fm, _ = read_frontmatter(md_path)
        nid = fm.get("note_project_id")
        if not nid:
            continue
        project = projects.get(nid)
        if project and project.note_file is None:
            project.note_file = md_path


def roots_of(projects: Dict[str, Project]) -> List[str]:
    # A root is a project whose parent_id is missing or not a known project_id
    roots: List[str] = []
    for pid, proj in projects.items():
        if not proj.parent_id or proj.parent_id not in projects:
            roots.append(pid)
    return sorted(roots, key=lambda pid: projects[pid].display_name.lower())


def format_info_lines(frontmatter: Dict[str, str], level: int) -> List[str]:
    # Print all tags as key: value lines; for nested levels, prefix with hyphens per depth
    lines: List[str] = []
    prefix = ("-" * (level + 1) + " ") if level > 0 else ""
    for key, value in frontmatter.items():
        lines.append(f"{prefix}{key}: {value}")
    return lines


def print_tree(projects: Dict[str, Project]) -> None:
    def recurse(pid: str, level: int) -> None:
        proj = projects[pid]
        indent = "  " * level
        if level == 0:
            print(f"{proj.display_name}")
        else:
            print(f"{indent}- {proj.display_name}")

        # Info lines (all tags)
        for line in format_info_lines(proj.frontmatter, level):
            print(f"{indent}{line}")
        if proj.note_file:
            note_prefix = ("-" * (level + 1) + " ") if level > 0 else ""
            print(f"{indent}{note_prefix}note_file: {proj.note_file}")

        # Children
        if proj.children:
            print(f"{indent}child projects:")
            for child_id in proj.children:
                recurse(child_id, level + 1)

    for root_id in roots_of(projects):
        recurse(root_id, 0)
        print("")


def main() -> None:
    # Default base dir is the Obsidian vault
    if len(sys.argv) > 1:
        base_dir = Path(sys.argv[1])
    else:
        # Use absolute path relative to this script's location
        script_dir = Path(__file__).parent
        base_dir = script_dir / "Obsidian Vault"
    if not base_dir.exists():
        print(f"Base directory not found: {base_dir}", file=sys.stderr)
        sys.exit(1)

    projects = build_projects(base_dir)
    link_notes(base_dir, projects)
    print_tree(projects)


if __name__ == "__main__":
    main()



