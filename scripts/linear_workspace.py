"""Directory-scoped hook dispatch for existing and future portfolio repositories."""

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from linear_hook import HOOKS
from linear_snapshot import refresh

GIT_HOOKS = """applypatch-msg pre-applypatch post-applypatch pre-commit pre-merge-commit
prepare-commit-msg commit-msg post-commit pre-rebase post-checkout post-merge
pre-push pre-receive update proc-receive post-receive post-update
reference-transaction push-to-checkout pre-auto-gc post-rewrite sendemail-validate
fsmonitor-watchman p4-changelist p4-prepare-changelist p4-post-changelist p4-pre-submit
post-index-change""".split()


def dispatch(hook, args):
    directory = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        capture_output=True,
        text=True,
    )
    common = (
        Path(directory.stdout.strip())
        if directory.returncode == 0
        else Path(os.environ.get("GIT_COMMON_DIR", os.environ.get("GIT_DIR", ".git"))).resolve()
    )
    original = common / "hooks" / hook
    data = sys.stdin.buffer.read() if hook == "reference-transaction" else None
    if hook in HOOKS:
        try:
            policy = json.loads(Path(__file__).with_name("policy.json").read_text())
            remotes = subprocess.run(
                ["git", "config", "--get-regexp", r"^remote\..*\.url$"],
                capture_output=True,
                text=True,
            )
            organisation = re.escape(policy["organisation"])
            applies = any(
                re.fullmatch(
                    rf"(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/){organisation}/[^/]+/?",
                    line.split(" ", 1)[-1],
                    re.I,
                )
                for line in remotes.stdout.splitlines()
            )
            if applies:
                env = dict(
                    os.environ,
                    PORTFOLIO_LINEAR_SNAPSHOT=str(Path(__file__).with_name("issues.json")),
                )
                subprocess.run(
                    [
                        sys.executable,
                        str(Path(__file__).with_name("linear_hook.py")),
                        "check",
                        hook,
                        *args,
                    ],
                    input=data,
                    env=env,
                    check=True,
                )
        except (OSError, ValueError, KeyError, subprocess.CalledProcessError):
            print(
                "Linear warning: validation unavailable; Git operation remains allowed.",
                file=sys.stderr,
            )
    if original.is_file() and os.access(original, os.X_OK):
        if b"# portfolio-linear: managed soft check" in original.read_bytes()[:100]:
            return 0
        if data is not None:
            return subprocess.run([str(original), *args], input=data).returncode
        os.execv(str(original), [str(original), *args])
    return 0


def configure(workspace, snapshot=None, remove=False, policy_path=None):
    workspace = workspace.resolve()
    state = workspace / ".portfolio-linear"
    config = state / "gitconfig"
    key = f"includeIf.gitdir:{workspace}/.path"
    values = subprocess.run(
        ["git", "config", "--global", "--get-all", key], capture_output=True, text=True
    )
    if values.returncode not in (0, 1):
        raise ValueError("Cannot read global Git configuration")
    if remove:
        if str(config) in values.stdout.splitlines():
            subprocess.run(
                ["git", "config", "--global", "--fixed-value", "--unset-all", key, str(config)],
                check=True,
            )
        print("Removed portfolio include; repository-owned hooks are active again.")
        return
    existing = subprocess.run(
        ["git", "config", "--global", "--get", "core.hooksPath"],
        capture_output=True,
        text=True,
        cwd="/",
    )
    if existing.returncode == 0:
        raise ValueError(
            "Existing global hooksPath requires explicit integration; no configuration changed."
        )
    if existing.returncode != 1:
        raise ValueError("Cannot inspect global hooksPath")
    policy = json.loads(policy_path.read_text())
    if not re.fullmatch(r"[A-Za-z0-9-]+", policy["organisation"]) or not re.fullmatch(
        r"[A-Z][A-Z0-9]*", policy["issue_prefix"]
    ):
        raise ValueError("Invalid organisation or issue prefix")
    if snapshot is None:
        with tempfile.TemporaryDirectory() as temporary:
            snapshot = Path(temporary) / "issues.json"
            refresh(policy, snapshot)
            snapshot_data = json.loads(snapshot.read_text())
    else:
        snapshot_data = json.loads(snapshot.read_text())
    if snapshot_data.get("project_id") != policy["project_id"]:
        raise ValueError("Snapshot does not match the configured Linear project")
    snapshot_data["policy"] = policy
    state.mkdir(exist_ok=True)
    hooks = state / "hooks"
    hooks.mkdir(exist_ok=True)
    files = ("linear_hook.py", "linear_workspace.py", "linear_snapshot.py")
    for name in files:
        shutil.copyfile(Path(__file__).with_name(name), state / name)
    (state / "issues.json").write_text(json.dumps(snapshot_data) + "\n")
    (state / "policy.json").write_text(json.dumps(policy) + "\n")
    revision = subprocess.check_output(
        ["git", "-C", str(Path(__file__).resolve().parent), "rev-parse", "HEAD"], text=True
    ).strip()
    (state / "version.json").write_text(
        json.dumps(
            {
                "revision": revision,
                "sha256": {
                    name: hashlib.sha256((state / name).read_bytes()).hexdigest() for name in files
                },
            }
        )
        + "\n"
    )
    for name in GIT_HOOKS:
        path = hooks / name
        path.write_text(
            f'#!/bin/sh\nexec python3 {shlex.quote(str(state / "linear_workspace.py"))} dispatch {name} "$@"\n'
        )
        path.chmod(0o755)
    subprocess.run(
        ["git", "config", "--file", str(config), "core.hooksPath", str(hooks)], check=True
    )
    if str(config) not in values.stdout.splitlines():
        subprocess.run(["git", "config", "--global", "--add", key, str(config)], check=True)
    print(f"Automatic soft Linear hooks enabled under {workspace}")


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "dispatch":
        return dispatch(sys.argv[2], sys.argv[3:])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "remove", "refresh", "status"))
    parser.add_argument("workspace", type=Path)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument(
        "--policy",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "policies/portfolio-linear.json",
    )
    args = parser.parse_args()
    state = args.workspace.resolve() / ".portfolio-linear"
    if args.action == "refresh":
        policy = json.loads((state / "policy.json").read_text())
        print(f"Refreshed {refresh(policy, state / 'issues.json')} issue IDs.")
    elif args.action == "status":
        version = json.loads((state / "version.json").read_text())
        includes = subprocess.run(
            [
                "git",
                "config",
                "--global",
                "--get-all",
                f"includeIf.gitdir:{args.workspace.resolve()}/.path",
            ],
            capture_output=True,
            text=True,
        )
        version["enabled"] = str(state / "gitconfig") in includes.stdout.splitlines()
        print(json.dumps(version))
    else:
        configure(args.workspace, args.snapshot, args.action == "remove", args.policy)


if __name__ == "__main__":
    raise SystemExit(main())
