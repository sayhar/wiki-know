#!/usr/bin/env python3
"""
Script to sample tests and archive the rest, then clean up git history.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from collections import defaultdict


def load_config():
    """Load the current config.json"""
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("Error: config.json not found")
        sys.exit(1)


def get_all_tests_with_timestamps():
    """Get all tests with their timestamps, sorted chronologically"""
    tests = []
    report_dir = Path("static/report")

    if not report_dir.exists():
        print("Error: static/report directory not found")
        sys.exit(1)

    for test_dir in report_dir.iterdir():
        if not test_dir.is_dir():
            continue

        meta_file = test_dir / "meta.csv"
        if not meta_file.exists():
            continue

        try:
            with open(meta_file, "r") as f:
                lines = f.readlines()
                if len(lines) < 2:  # Need header + at least one data row
                    continue

                # Get timestamp from the last data row (most recent)
                data_row = lines[-1].strip().split(",")
                if len(data_row) >= 14:  # timestamp is field 14
                    timestamp = int(data_row[13].strip('"'))
                    tests.append((timestamp, test_dir.name))

        except Exception as e:
            print(f"Warning: Could not process {test_dir.name}: {e}")
            continue

    # Sort by timestamp (chronological order)
    tests.sort(key=lambda x: x[0])
    return tests


def sample_tests_evenly(tests, target_count=30):
    """Sample tests evenly across the chronological range"""
    if len(tests) <= target_count:
        return [t[1] for t in tests]

    # Calculate step size to sample evenly
    step = len(tests) / target_count
    sampled = []

    for i in range(target_count):
        index = int(i * step)
        if index < len(tests):
            sampled.append(tests[index][1])

    return sampled


def main():
    print("Loading configuration...")
    config = load_config()
    interesting_tests = set(config.get("interesting_tests", []))

    print(f"Found {len(interesting_tests)} interesting tests in config")

    print("Getting all tests with timestamps...")
    all_tests = get_all_tests_with_timestamps()
    print(f"Found {len(all_tests)} total tests")

    # Keep interesting tests
    tests_to_keep = set(interesting_tests)

    # Sample additional tests (excluding interesting ones)
    remaining_tests = [t for t in all_tests if t[1] not in interesting_tests]
    sampled_tests = sample_tests_evenly(remaining_tests, 30)

    # Add sampled tests to keep list
    tests_to_keep.update(sampled_tests)

    print(f"Keeping {len(tests_to_keep)} tests total:")
    print(f"  - {len(interesting_tests)} interesting tests")
    print(f"  - {len(sampled_tests)} sampled tests")

    # Create archive directory
    archive_dir = Path("static-archive/report")
    archive_dir.mkdir(parents=True, exist_ok=True)

    # Move tests to archive
    moved_count = 0
    for timestamp, test_name in all_tests:
        if test_name not in tests_to_keep:
            source = Path("static/report") / test_name
            dest = archive_dir / test_name

            if source.exists():
                shutil.move(str(source), str(dest))
                moved_count += 1
                print(f"Moved to archive: {test_name}")

    print(f"\nMoved {moved_count} tests to archive")

    # Update .gitignore
    gitignore_path = Path(".gitignore")
    if not gitignore_path.exists():
        gitignore_path.write_text("")

    gitignore_content = gitignore_path.read_text()
    if "static-archive/" not in gitignore_content:
        gitignore_content += "\n# Archive directory\nstatic-archive/\n"
        gitignore_path.write_text(gitignore_content)
        print("Updated .gitignore to exclude archive")

    print("\nNext steps:")
    print("1. Review the changes")
    print("2. Commit the current state")
    print("3. Run git history cleanup to remove archived files from history")
    print("\nTo clean git history, run:")
    print(
        "git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch -r static-archive/' --prune-empty --tag-name-filter cat -- --all"
    )


if __name__ == "__main__":
    main()
