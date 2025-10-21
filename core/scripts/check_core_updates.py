#!/usr/bin/env python3
"""
Check Core Updates Script
Check if Luna core updates are available from git repository
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime


def get_current_commit():
    """Get current commit hash"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error getting current commit: {e}", file=sys.stderr)
        return None


def get_remote_commit():
    """Get latest commit hash from remote"""
    try:
        # Fetch latest from remote without pulling
        subprocess.run(
            ["git", "fetch", "origin"],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Get remote commit
        result = subprocess.run(
            ["git", "rev-parse", "origin/main"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error getting remote commit: {e}", file=sys.stderr)
        return None


def get_commit_date(commit_hash):
    """Get the date of a commit"""
    try:
        result = subprocess.run(
            ["git", "show", "-s", "--format=%ci", commit_hash],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error getting commit date: {e}", file=sys.stderr)
        return None


def get_commit_message(commit_hash):
    """Get the commit message"""
    try:
        result = subprocess.run(
            ["git", "show", "-s", "--format=%s", commit_hash],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error getting commit message: {e}", file=sys.stderr)
        return None


def get_commits_between(from_commit, to_commit, max_count=10):
    """Get list of commits between two commits"""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", f"{from_commit}..{to_commit}", f"-{max_count}"],
            capture_output=True,
            text=True,
            check=True
        )
        lines = result.stdout.strip().split('\n')
        return [line for line in lines if line]
    except subprocess.CalledProcessError as e:
        print(f"Error getting commits: {e}", file=sys.stderr)
        return []


def format_version_from_date(date_str):
    """Format a git date string into MM-DD-YY version format"""
    try:
        # Parse git date format: "2025-10-20 12:34:56 -0400"
        dt = datetime.strptime(date_str[:19], "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%m-%d-%y")
    except Exception as e:
        print(f"Error parsing date: {e}", file=sys.stderr)
        return "unknown"


def main():
    """Main entry point"""
    # Change to repository directory if needed
    if len(sys.argv) > 1:
        repo_path = Path(sys.argv[1])
        os.chdir(repo_path)
    
    # Get current and remote commits
    current_commit = get_current_commit()
    remote_commit = get_remote_commit()
    
    if not current_commit or not remote_commit:
        print(json.dumps({
            "error": "Failed to check for updates",
            "update_available": False
        }))
        return 1
    
    # Check if update is available
    update_available = current_commit != remote_commit
    
    # Get commit info
    current_date = get_commit_date(current_commit)
    remote_date = get_commit_date(remote_commit)
    
    current_version = format_version_from_date(current_date) if current_date else "unknown"
    remote_version = format_version_from_date(remote_date) if remote_date else "unknown"
    
    # Get commits between if update available
    commits = []
    if update_available:
        commits = get_commits_between(current_commit, remote_commit, max_count=10)
    
    # Build result
    result = {
        "update_available": update_available,
        "current": {
            "commit": current_commit[:7],
            "version": current_version,
            "date": current_date,
            "message": get_commit_message(current_commit)
        },
        "remote": {
            "commit": remote_commit[:7],
            "version": remote_version,
            "date": remote_date,
            "message": get_commit_message(remote_commit)
        },
        "commits_between": len(commits),
        "recent_commits": commits[:5] if commits else []
    }
    
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())


