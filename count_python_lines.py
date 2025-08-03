#!/usr/bin/env python3
"""
Script to count lines of Python code in the project.
Recursively scans all directories and counts lines in .py files.
"""

import os
import sys
from pathlib import Path
from collections import defaultdict


def count_lines_in_file(file_path):
    """Count total lines, code lines, and comment lines in a Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        code_lines = 0
        comment_lines = 0
        blank_lines = 0
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                blank_lines += 1
            elif stripped.startswith('#'):
                comment_lines += 1
            elif stripped.startswith('"""') or stripped.startswith("'''"):
                comment_lines += 1
            else:
                code_lines += 1
        
        return {
            'total': total_lines,
            'code': code_lines,
            'comments': comment_lines,
            'blank': blank_lines
        }
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return {'total': 0, 'code': 0, 'comments': 0, 'blank': 0}


def scan_project(root_dir):
    """Scan project directory for Python files and count lines."""
    root_path = Path(root_dir)
    
    # Statistics
    total_stats = {'total': 0, 'code': 0, 'comments': 0, 'blank': 0}
    dir_stats = defaultdict(lambda: {'total': 0, 'code': 0, 'comments': 0, 'blank': 0, 'files': 0})
    file_list = []
    
    # Find all Python files
    for py_file in root_path.rglob('*.py'):
        # Skip hidden directories and files
        if any(part.startswith('.') for part in py_file.parts):
            continue
            
        # Get relative path for display
        rel_path = py_file.relative_to(root_path)
        
        # Count lines in this file
        stats = count_lines_in_file(py_file)
        
        # Update totals
        for key in total_stats:
            total_stats[key] += stats[key]
        
        # Update directory stats
        dir_name = str(rel_path.parent) if rel_path.parent != Path('.') else 'root'
        for key in stats:
            dir_stats[dir_name][key] += stats[key]
        dir_stats[dir_name]['files'] += 1
        
        # Store file info
        file_list.append((rel_path, stats))
    
    return total_stats, dir_stats, file_list


def print_results(total_stats, dir_stats, file_list):
    """Print formatted results."""
    print("=" * 80)
    print("PYTHON CODE LINE COUNT REPORT")
    print("=" * 80)
    
    # Overall statistics
    print(f"\nOVERALL STATISTICS:")
    print(f"  Total Python files: {len(file_list)}")
    print(f"  Total lines:        {total_stats['total']:,}")
    print(f"  Code lines:         {total_stats['code']:,}")
    print(f"  Comment lines:      {total_stats['comments']:,}")
    print(f"  Blank lines:        {total_stats['blank']:,}")
    
    # Directory breakdown
    print(f"\nBREAKDOWN BY DIRECTORY:")
    print(f"{'Directory':<30} {'Files':<6} {'Total':<8} {'Code':<8} {'Comments':<9} {'Blank':<6}")
    print("-" * 80)
    
    for dir_name in sorted(dir_stats.keys()):
        stats = dir_stats[dir_name]
        print(f"{dir_name:<30} {stats['files']:<6} {stats['total']:<8} {stats['code']:<8} {stats['comments']:<9} {stats['blank']:<6}")
    
    # Largest files
    print(f"\nLARGEST FILES (by total lines):")
    print(f"{'File':<50} {'Total':<8} {'Code':<8} {'Comments':<9} {'Blank':<6}")
    print("-" * 80)
    
    # Sort files by total lines and show top 10
    sorted_files = sorted(file_list, key=lambda x: x[1]['total'], reverse=True)
    for file_path, stats in sorted_files[:10]:
        file_str = str(file_path)
        if len(file_str) > 47:
            file_str = "..." + file_str[-44:]
        print(f"{file_str:<50} {stats['total']:<8} {stats['code']:<8} {stats['comments']:<9} {stats['blank']:<6}")
    
    print("\n" + "=" * 80)


def main():
    """Main function."""
    # Get project root directory
    if len(sys.argv) > 1:
        project_dir = sys.argv[1]
    else:
        project_dir = os.getcwd()
    
    if not os.path.isdir(project_dir):
        print(f"Error: '{project_dir}' is not a valid directory")
        sys.exit(1)
    
    print(f"Scanning Python files in: {os.path.abspath(project_dir)}")
    
    # Scan the project
    total_stats, dir_stats, file_list = scan_project(project_dir)
    
    if not file_list:
        print("No Python files found in the project directory.")
        return
    
    # Print results
    print_results(total_stats, dir_stats, file_list)


if __name__ == "__main__":
    main()