"""Notes tools and system prompt.

Domain: Notes — Interact with Obsidian-style project pages and dated Notes.md files.

This extension provides:
- Project hierarchy discovery from Markdown frontmatter (`project_id`, `project_parent`).
- Retrieval of project page and linked note page text by `project_id` or display name.
- Query of dated note entries within a date range across `*Notes.md` files.
- Update/append content into today's dated entry for a project note, optionally under a section.

Environment:
- Uses dotenv if available. Base directory resolves from env (OBSIDIAN_VAULT_DIR or NOTES_BASE_DIR),
  otherwise defaults to the packaged "Obsidian Vault" folder adjacent to this file unless overridden per-call.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, List, Dict, Any

try:  # pragma: no cover
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()

# Local imports from the refactored modules
from extensions.notes import project_hierarchy as gen

from pydantic import BaseModel, Field


NAME = "Notes"

SYSTEM_PROMPT = """
Support the user's note-taking and project documentation in an Obsidian-style vault.
Understand projects (via project_id/frontmatter), read/update Notes.md entries by date,
and return structured results when possible.

Prefer precise operations: when asked to update notes, find or create today's entry,
optionally place content under a specified markdown section.
""".strip()


# ---------- Pydantic response models ----------

class OperationResult(BaseModel):
    success: bool
    message: str


class ProjectTextResponse(BaseModel):
    project_id: str
    root_page_path: Optional[str] = None
    root_page_text: Optional[str] = None
    note_page_path: Optional[str] = None
    note_page_text: Optional[str] = None
    error: Optional[str] = None


class NoteEntry(BaseModel):
    file: str
    date: str
    date_str: str
    content: str


class NotesByDateResponse(BaseModel):
    start_date: str
    end_date: str
    entries: list[NoteEntry] = Field(default_factory=list)


class UpdateProjectNoteResponse(BaseModel):
    project_id: str
    note_file: str
    created_file: bool
    created_entry: bool
    appended: bool
    date_str: str

# Ensure forward refs are resolved when using postponed evaluation of annotations
try:  # pragma: no cover
    NotesByDateResponse.model_rebuild()
except Exception:
    pass


# ---------- Helper ----------

def _base_dir(path: Optional[str]) -> Path:
    if path:
        base = Path(path)
    else:
        env_path = os.getenv("OBSIDIAN_VAULT_DIR") or os.getenv("NOTES_BASE_DIR")
        base = Path(env_path) if env_path else (Path(__file__).parent / "Obsidian Vault")
    if not base.exists():
        raise FileNotFoundError(f"Base directory not found: {base}")
    return base


# ---------- Tools ----------

def NOTES_GET_project_hierarchy(base_dir: Optional[str] = None) -> str:
    """Return a simplified hierarchy: root names and immediate child names only.
    Example Prompt: "show my project hierarchy"
    Example Response: "Eco AI\n- Roadmap\n- Research"
    Example Args: {"base_dir": "string[optional override path]"}
    """
    base = _base_dir(base_dir)
    projects = gen.build_projects(base)
    gen.link_notes(base, projects)
    lines: List[str] = []
    for root_id in gen.roots_of(projects):
        root = projects[root_id]
        lines.append(f"{root.display_name}")
        for child_id in root.children:
            child = projects[child_id]
            lines.append(f"- {child.display_name}")
        lines.append("")
    if lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def NOTES_GET_project_text(project_id: str, base_dir: Optional[str] = None) -> ProjectTextResponse:
    """Return the root project page text and note page text for a given project_id or display name.
    Example Prompt: "show the text for project Eco AI"
    Example Response: {"project_id": "Eco AI", "root_page_path": "...", "root_page_text": "# Eco AI ...", "note_page_path": "...", "note_page_text": "..."}
    Example Args: {"project_id": "string[id or display name]", "base_dir": "string[optional path]"}
    """
    if not project_id:
        return ProjectTextResponse(project_id="", error="project_id is required")
    base = _base_dir(base_dir)
    projects = gen.build_projects(base)
    gen.link_notes(base, projects)

    lookup = {pid.lower(): pid for pid in projects.keys()}
    canonical = lookup.get(project_id.lower())
    if canonical is None:
        dn_lookup = {p.display_name.lower(): p.project_id for p in projects.values()}
        canonical = dn_lookup.get(project_id.lower())
    if canonical is None:
        return ProjectTextResponse(project_id=project_id, error=f"Project not found: {project_id}")

    proj = projects[canonical]
    root_page_path = str(proj.file_path)
    try:
        root_page_text = proj.file_path.read_text(encoding="utf-8")
    except Exception:
        root_page_text = None

    note_page_path = str(proj.note_file) if proj.note_file else None
    if proj.note_file and Path(proj.note_file).exists():
        try:
            note_page_text = Path(proj.note_file).read_text(encoding="utf-8")
        except Exception:
            note_page_text = None
    else:
        note_page_text = None

    return ProjectTextResponse(
        project_id=canonical,
        root_page_path=root_page_path,
        root_page_text=root_page_text,
        note_page_path=note_page_path,
        note_page_text=note_page_text,
    )


# Import note parsing/updating logic by reusing the original module behavior
import re
from datetime import datetime


_DATE_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{2})(?::)?\s*$")


def _parse_frontmatter(lines: List[str]):
    if not lines or lines[0].strip() != "---":
        return [], 0
    fm_lines: List[str] = [lines[0]]
    idx = 1
    while idx < len(lines):
        fm_lines.append(lines[idx])
        if lines[idx].strip() == "---":
            return fm_lines, idx + 1
        idx += 1
    return [], 0


def _iter_note_entries(lines: List[str]):
    current_date: Optional[datetime] = None
    current_header: Optional[str] = None
    current_body: List[str] = []

    def flush():
        nonlocal current_date, current_header, current_body
        if current_date is not None and current_header is not None:
            yield current_date, current_header, current_body[:]
        current_date = None
        current_header = None
        current_body = []

    idx = 0
    while idx < len(lines):
        line = lines[idx]
        m = _DATE_RE.match(line.strip())
        if m:
            if current_date is not None:
                yield from flush()
            month, day, yy = m.groups()
            year = 2000 + int(yy)
            try:
                current_date = datetime(year, int(month), int(day))
                current_header = line if line.endswith("\n") else (line + "\n")
            except ValueError:
                if current_date is not None:
                    current_body.append(line)
        else:
            if current_date is not None:
                current_body.append(line if line.endswith("\n") else (line + "\n"))
        idx += 1

    if current_date is not None and current_header is not None:
        yield current_date, current_header, current_body[:]


def _find_notes_files(base_dir: Path) -> List[Path]:
    paths: List[Path] = []
    for pat in ("*Notes.md", "*notes.md"):
        paths.extend(base_dir.rglob(pat))
    seen = set()
    result: List[Path] = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            result.append(p)
    return result


def NOTES_GET_notes_by_date_range(start_date: str, end_date: str, base_dir: Optional[str] = None) -> NotesByDateResponse | OperationResult:
    """Return dated note entries within [start_date, end_date] (MM/DD/YY), newest-first.
    Example Prompt: "find my notes between 06/01/24 and 06/15/24"
    Example Response: {"start_date": "06/01/24", "end_date": "06/15/24", "entries": [{"file": "...Notes.md", "date": "2024-06-01", "date_str": "6/1/24", "content": "..."}]}
    Example Args: {"start_date": "string[MM/DD/YY]", "end_date": "string[MM/DD/YY]", "base_dir": "string[optional path]"}
    """
    def parse_mdyy(s: str) -> datetime:
        m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{2})$", s.strip())
        if not m:
            raise ValueError("Dates must be in MM/DD/YY format")
        month, day, yy = m.groups()
        return datetime(2000 + int(yy), int(month), int(day))

    try:
        start_dt = parse_mdyy(start_date)
        end_dt = parse_mdyy(end_date)
    except Exception as e:
        return OperationResult(success=False, message=str(e))
    if end_dt < start_dt:
        start_dt, end_dt = end_dt, start_dt

    base = _base_dir(base_dir)

    results: List[Dict[str, Any]] = []
    for md_path in _find_notes_files(base):
        try:
            text = md_path.read_text(encoding="utf-8")
        except Exception:
            continue
        lines = [l if l.endswith("\n") else l + "\n" for l in text.splitlines(True)]
        _, body_idx = _parse_frontmatter(lines)
        body = lines[body_idx:]

        for dt, header, content_lines in _iter_note_entries(body):
            if start_dt <= dt <= end_dt:
                content = "".join(content_lines).rstrip("\n")
                results.append({
                    "file": str(md_path.relative_to(base)),
                    "date": dt.date().isoformat(),
                    "date_str": header.strip().rstrip(':'),
                    "content": content,
                })

    results.sort(key=lambda r: r["date"], reverse=True)
    entries = [NoteEntry(**e) for e in results]
    return NotesByDateResponse(start_date=start_date, end_date=end_date, entries=entries)


def NOTES_UPDATE_project_note(project_id: str, content: str, section_id: Optional[str] = None, base_dir: Optional[str] = None) -> UpdateProjectNoteResponse | OperationResult:
    """Append content to today's dated note entry for a project. Creates file/entry if needed.
    Example Prompt: "add 'ship MVP' under 'Milestones' for project Eco AI"
    Example Response: {"project_id": "Eco AI", "note_file": ".../Notes.md", "created_file": false, "created_entry": true, "appended": true, "date_str": "6/1/24"}
    Example Args: {"project_id": "string[id or display name]", "content": "string[text to append]", "section_id": "string[optional section]", "base_dir": "string[optional path]"}
    """
    if not project_id:
        return OperationResult(success=False, message="project_id is required")
    if not content:
        return OperationResult(success=False, message="content is required")

    base = _base_dir(base_dir)
    projects = gen.build_projects(base)
    gen.link_notes(base, projects)

    lookup = {pid.lower(): pid for pid in projects.keys()}
    canonical_id = lookup.get(project_id.lower())
    if canonical_id is None:
        dn_lookup = {p.display_name.lower(): p.project_id for p in projects.values()}
        canonical_id = dn_lookup.get(project_id.lower())
    if canonical_id is None:
        return OperationResult(success=False, message=f"Project not found: {project_id}")

    proj = projects[canonical_id]

    created_file = False
    if proj.note_file and Path(proj.note_file).exists():
        note_path = Path(proj.note_file)
    else:
        note_path = proj.file_path.parent / "Notes.md"
        if not note_path.exists():
            created_file = True
            note_path.write_text("---\n" f"note_project_id: {proj.project_id}\n" "---\n\n", encoding="utf-8")

    text = note_path.read_text(encoding="utf-8")
    lines = [l if l.endswith("\n") else l + "\n" for l in text.splitlines(True)]

    fm_lines, body_idx = _parse_frontmatter(lines)
    body = lines[body_idx:]

    today = datetime.now()
    m = today.month
    d = today.day
    yy = today.year % 100
    today_str = f"{m}/{d}/{yy:02d}"

    date_indices = [i for i, ln in enumerate(body) if _DATE_RE.match(ln.strip().rstrip(':'))]

    def match_date_line(ln: str) -> bool:
        s = ln.strip()
        if s.endswith(":"):
            s = s[:-1]
        return s == today_str

    first_date_idx = date_indices[0] if date_indices else None
    today_start = None
    for i in date_indices:
        if match_date_line(body[i]):
            today_start = i
            break

    def find_entry_end(start_idx: int) -> int:
        for j in date_indices:
            if j > start_idx:
                return j
        return len(body)

    created_entry = False
    appended = False

    if today_start is None:
        entry_lines: List[str] = []
        entry_lines.append(today_str + "\n")
        entry_lines.append("\n")
        if section_id:
            entry_lines.append(f"## {section_id}\n\n")
        content_block = content if content.endswith("\n") else content + "\n"
        entry_lines.append(content_block)

        insert_pos = first_date_idx if first_date_idx is not None else len(body)
        new_body = body[:insert_pos] + entry_lines + (body[insert_pos:] if insert_pos is not None else [])
        lines = fm_lines + new_body
        note_path.write_text("".join(lines), encoding="utf-8")
        created_entry = True
    else:
        entry_end = find_entry_end(today_start)

        if section_id:
            sec_pat = re.compile(rf"^\s*#{{1,6}}\s+{re.escape(section_id)}\s*$", re.IGNORECASE)
            sec_start = None
            for idx in range(today_start + 1, entry_end):
                if sec_pat.match(body[idx].rstrip("\n")):
                    sec_start = idx
                    break

            if sec_start is None:
                insert_at = entry_end
                if insert_at > today_start + 1 and body[insert_at - 1].strip() != "":
                    body.insert(insert_at, "\n")
                    insert_at += 1
                body.insert(insert_at, f"## {section_id}\n")
                insert_at += 1
                body.insert(insert_at, "\n")
                insert_at += 1
                content_block = content if content.endswith("\n") else content + "\n"
                body.insert(insert_at, content_block)
                appended = True
            else:
                sec_end = entry_end
                for idx in range(sec_start + 1, entry_end):
                    if re.match(r"^\s*#{{1,6}}\s+", body[idx]):
                        sec_end = idx
                        break
                insert_at = sec_end
                if insert_at > sec_start + 1 and body[insert_at - 1].strip() != "":
                    body.insert(insert_at, "\n")
                    insert_at += 1
                content_block = content if content.endswith("\n") else content + "\n"
                body.insert(insert_at, content_block)
                appended = True
        else:
            insert_at = entry_end
            if body[insert_at - 1].strip() != "":
                body.insert(insert_at, "\n")
                insert_at += 1
            content_block = content if content.endswith("\n") else content + "\n"
            body.insert(insert_at, content_block)
            appended = True

        lines = fm_lines + body
        note_path.write_text("".join(lines), encoding="utf-8")

    return UpdateProjectNoteResponse(
        project_id=canonical_id,
        note_file=str(note_path.relative_to(base)),
        created_file=created_file,
        created_entry=created_entry,
        appended=appended,
        date_str=today_str,
    )


TOOLS = [
    NOTES_GET_project_hierarchy,
    NOTES_GET_project_text,
    NOTES_GET_notes_by_date_range,
    NOTES_UPDATE_project_note,
]



