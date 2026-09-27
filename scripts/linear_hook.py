"""Opt-in portfolio branch warnings using a locally verified Linear issue snapshot."""

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

HOOKS = ("reference-transaction", "post-checkout")


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def common_dir(repo):
    return Path(git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir"))


def warning(branch, snapshot):
    policy = (snapshot or {}).get("policy", {})
    if branch in policy.get("exempt_branches", ["main", "master"]):
        return None
    prefix = policy.get("issue_prefix", "AI")
    match = re.search(rf"(?:^|/)({re.escape(prefix)}-[1-9][0-9]*)(?=$|[-/])", branch, re.I)
    if not match:
        return f"{branch}: include a Linear issue, e.g. {prefix.lower()}-7-description."
    if not snapshot or not 0 <= time.time() - snapshot["verified_at"] <= policy.get(
        "max_age_seconds", 86400
    ):
        return f"{branch}: Linear snapshot missing or stale; verify the issue in Linear and refresh it."
    if match[1].upper() not in snapshot["issues"]:
        return f"{branch}: issue not in the verified project snapshot; check Linear and refresh it."
    return None


def check(hook, args):
    try:
        branches = []
        if hook == "reference-transaction":
            updates = sys.stdin.read().splitlines()
            if args == ["committed"]:
                for line in updates:
                    old, new, ref = line.split()
                    if set(old) == {"0"} and set(new) != {"0"} and ref.startswith("refs/heads/"):
                        branches.append(ref.removeprefix("refs/heads/"))
        elif args and args[-1] == "1":
            branch = git(".", "branch", "--show-current")
            if branch:
                branches.append(branch)
        path = Path(
            os.environ.get(
                "PORTFOLIO_LINEAR_SNAPSHOT", common_dir(".") / "portfolio-linear" / "issues.json"
            )
        )
        snapshot = json.loads(path.read_text()) if path.exists() else None
        for branch in branches:
            message = warning(branch, snapshot)
            if message:
                print(f"Linear warning: {message} Git operation remains allowed.", file=sys.stderr)
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError):
        print(
            "Linear warning: validation unavailable; Git operation remains allowed.",
            file=sys.stderr,
        )


def wrapper(script, hook):
    return (
        f"#!/bin/sh\n# portfolio-linear: managed soft check\n"
        f'python3 {shlex.quote(str(script))} check {hook} "$@" || '
        'echo "Linear warning: hook unavailable; Git operation remains allowed." >&2\nexit 0\n'
    )


def install(repo, snapshot_path, remove=False):
    configured = subprocess.run(
        ["git", "-C", str(repo), "config", "--get", "core.hooksPath"], capture_output=True
    )
    if configured.returncode != 1:
        raise ValueError(
            "Custom hooksPath detected or config unreadable; refusing to replace existing configuration."
        )
    common = common_dir(repo)
    hooks, state = common / "hooks", common / "portfolio-linear"
    script = state / "linear_hook.py"
    for hook in HOOKS:
        path = hooks / hook
        if path.is_symlink() or (path.exists() and path.read_text() != wrapper(script, hook)):
            raise ValueError(f"Existing {hook} is not ours; no hooks changed.")
    if remove:
        for hook in HOOKS:
            (hooks / hook).unlink(missing_ok=True)
        for name in ("linear_hook.py", "issues.json"):
            (state / name).unlink(missing_ok=True)
        print(f"Removed portfolio Linear hooks: {repo}")
        return
    snapshot = json.loads(snapshot_path.read_text())
    if type(snapshot.get("verified_at")) not in (int, float) or not isinstance(
        snapshot.get("issues"), list
    ):
        raise ValueError("Snapshot requires verified_at and an issues list from Linear.")
    if any(
        not isinstance(issue, str) or not re.fullmatch(r"AI-[1-9][0-9]*", issue)
        for issue in snapshot["issues"]
    ):
        raise ValueError("Snapshot contains an invalid issue identifier.")
    state.mkdir(exist_ok=True)
    hooks.mkdir(exist_ok=True)
    shutil.copyfile(__file__, script)
    (state / "issues.json").write_text(json.dumps(snapshot) + "\n")
    for hook in HOOKS:
        path = hooks / hook
        path.write_text(wrapper(script, hook))
        path.chmod(0o755)
    print(f"Installed soft Linear hooks for repository and linked worktrees: {repo}")


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "check":
        check(sys.argv[2], sys.argv[3:])
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "remove"))
    parser.add_argument("repo", type=Path)
    parser.add_argument("--snapshot", type=Path)
    args = parser.parse_args()
    if args.action == "install" and args.snapshot is None:
        parser.error("install requires --snapshot from a verified Linear lookup")
    install(args.repo, args.snapshot, remove=args.action == "remove")


if __name__ == "__main__":
    main()
