#!/usr/bin/env python3
"""Review and reconcile the files managed by agent-setup."""

import argparse
import difflib
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parent.parent
SHARED = (ROOT / "standards" / "shared.md").read_text().strip()
SIGNAL = (ROOT / "profiles" / "signal.md").read_text()


def signal_body():
    if not SIGNAL.startswith("---\n"):
        raise ValueError("Signal profile needs YAML frontmatter")
    _, _, remainder = SIGNAL.partition("---\n")
    _, separator, body = remainder.partition("\n---\n")
    if not separator:
        raise ValueError("Signal profile frontmatter is not closed")
    return body.strip()


def managed_block(name, content):
    return (
        "<!-- agent-setup:" + name + ":start -->\n"
        + content.strip() + "\n"
        + "<!-- agent-setup:" + name + ":end -->\n"
    )


def merge_block(existing, name, content):
    start = "<!-- agent-setup:" + name + ":start -->"
    end = "<!-- agent-setup:" + name + ":end -->"
    starts, ends = existing.count(start), existing.count(end)
    if starts != ends or starts > 1:
        raise ValueError("incomplete or duplicate " + name + " markers")
    block = managed_block(name, content)
    if starts == 0:
        if not existing:
            return block
        separator = "" if existing.endswith("\n\n") else "\n" if existing.endswith("\n") else "\n\n"
        return existing + separator + block
    if existing.index(start) > existing.index(end):
        raise ValueError("reversed " + name + " markers")
    before, rest = existing.split(start, 1)
    _, after = rest.split(end, 1)
    if after.startswith("\n"):
        after = after[1:]
    return before + block + after


def targets(home, profile):
    codex = home / ".codex" / "AGENTS.md"
    if profile == "portfolio":
        content = (ROOT / "profiles" / "portfolio.md").read_text()
        return [
            (codex, "portfolio", content),
            (home / ".claude" / "CLAUDE.md", "portfolio", content),
        ]
    if profile == "shared":
        return [
            (codex, "shared", SHARED),
            (home / ".claude" / "CLAUDE.md", "shared", SHARED),
        ]
    return [
        (codex, "signal", signal_body()),
        (home / ".claude" / "output-styles" / "signal.md", None, SIGNAL),
    ]


def proposed(path, name, content):
    if path.is_symlink():
        raise ValueError("symlink: review its target manually")
    if path.exists() and not path.is_file():
        raise ValueError("not a regular file")
    if path.exists():
        with path.open("r", newline="") as stream:
            current = stream.read()
    else:
        current = ""
    wanted = merge_block(current, name, content) if name else content
    return current, wanted


def show_diff(path, current, wanted):
    diff = difflib.unified_diff(
        current.splitlines(keepends=True),
        wanted.splitlines(keepends=True),
        fromfile=str(path) + " (current)",
        tofile=str(path) + " (proposed)",
    )
    sys.stdout.writelines(diff)


def write_with_backup(path, current, wanted):
    # Recheck after the prompt so a concurrent edit is never overwritten.
    latest, _ = proposed(path, None, wanted)
    if latest != current:
        raise ValueError("file changed during review; run plan again")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = path.with_name(path.name + ".backup." + stamp + "." + str(os.getpid()))
        shutil.copy2(path, backup)
        print("Backup:", backup)
    descriptor, temporary = tempfile.mkstemp(prefix=".agent-setup-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", newline="") as stream:
            stream.write(wanted)
        if path.exists():
            os.chmod(temporary, stat.S_IMODE(path.stat().st_mode))
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "apply", "verify"))
    parser.add_argument("profile", choices=("shared", "signal", "portfolio"))
    parser.add_argument("--home", type=Path, default=Path(os.environ.get("AGENT_SETUP_HOME", Path.home())))
    args = parser.parse_args()
    changes = []
    blocked = False

    for path, name, content in targets(args.home, args.profile):
        try:
            current, wanted = proposed(path, name, content)
        except (OSError, ValueError) as error:
            print("Manual review:", path, "—", error)
            blocked = True
            continue

        if current == wanted:
            print("Current:", path)
            continue
        print("Missing:" if not path.exists() else "Change proposed:", path)
        changes.append((path, name, content, current, wanted))
        if args.action != "verify":
            show_diff(path, current, wanted)

    if args.action == "verify":
        return 1 if blocked or changes else 0
    if blocked:
        print("No files changed; resolve the manual review items first.")
        return 1
    if args.action == "plan" or not changes:
        return 0

    try:
        answer = input("Apply all proposed changes? [y/N] ")
    except EOFError:
        answer = ""
    if answer.lower() not in ("y", "yes"):
        print("No files changed.")
        return 1

    # Recheck every target before writing the first one.
    for path, name, content, current, wanted in changes:
        try:
            latest, _ = proposed(path, name, content)
        except (OSError, ValueError) as error:
            print("No files changed:", path, "—", error)
            return 1
        if latest != current:
            print("No files changed:", path, "changed during review")
            return 1

    for path, _, _, current, wanted in changes:
        try:
            write_with_backup(path, current, wanted)
        except (OSError, ValueError) as error:
            print("Not applied:", path, "—", error)
            return 1
        print("Installed:", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
