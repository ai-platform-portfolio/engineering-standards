import importlib
import json
import subprocess
import sys
import unittest

import test_linear_hook as fixtures

SCRIPT = fixtures.SCRIPT

sys.path.insert(0, str(SCRIPT.parent))
refresh = importlib.import_module("linear_snapshot").refresh


class WorkspaceHookTest(unittest.TestCase):
    git = fixtures.LinearHookTest.git
    run_script = fixtures.LinearHookTest.run_script

    def setUp(self):
        fixtures.LinearHookTest.setUp(self)
        self.run_script("remove", str(self.repo))
        self.env["GIT_CONFIG_GLOBAL"] = str(self.root / "global-config")
        self.policy = json.loads(
            (SCRIPT.parent.parent / "policies/portfolio-linear.json").read_text()
        )
        snapshot = json.loads(self.snapshot.read_text())
        snapshot["project_id"] = self.policy["project_id"]
        self.snapshot.write_text(json.dumps(snapshot))
        self.workspace("install", "--snapshot", str(self.snapshot))
        self.git("remote", "add", "origin", "git@github.com:ai-platform-portfolio/example.git")

    def workspace(self, action, *args):
        return subprocess.run(
            [
                "python3",
                str(SCRIPT.with_name("linear_workspace.py")),
                action,
                str(self.root),
                *args,
            ],
            env=self.env,
            capture_output=True,
            text=True,
            check=True,
        )

    def test_new_repositories_clones_and_worktrees_inherit_scope(self):
        new = self.root / "nested" / "new"
        new.mkdir(parents=True)
        self.git("init", "-b", "main", repo=new)
        self.assertIn(
            ".portfolio-linear", self.git("config", "--get", "core.hooksPath", repo=new).stdout
        )
        clone = self.root / "clone"
        self.git("clone", str(self.repo), str(clone))
        self.git(
            "remote",
            "set-url",
            "origin",
            "https://github.com/ai-platform-portfolio/new.git",
            repo=clone,
        )
        self.assertIn("Linear warning", self.git("switch", "-c", "unlinked", repo=clone).stderr)
        worktree = self.root / "linked"
        self.assertNotIn(
            "Linear warning", self.git("worktree", "add", "-b", "ai-7-linked", str(worktree)).stderr
        )
        self.assertIn("Linear warning", self.git("switch", "-c", "unknown", repo=worktree).stderr)
        self.git("remote", "set-url", "origin", "git@github.com:unrelated-org/example.git")
        self.assertNotIn("Linear warning", self.git("switch", "-c", "unrelated").stderr)

    def test_existing_hooks_receive_stdin_and_can_still_reject(self):
        original = self.repo / ".git/hooks/reference-transaction"
        original.write_text(
            '#!/bin/sh\ncat >> "$GIT_TEST_CAPTURE"\nif [ "$1" = prepared ]; then exit 9; fi\n'
        )
        original.chmod(0o755)
        capture = self.root / "capture"
        self.env["GIT_TEST_CAPTURE"] = str(capture)
        with self.assertRaises(subprocess.CalledProcessError):
            self.git("branch", "ai-7-rejected-by-original")
        self.assertIn("refs/heads/ai-7-rejected-by-original", capture.read_text())
        self.assertIn("exit 9", original.read_text())

    def test_update_uninstall_and_local_override_preserved(self):
        self.workspace("install", "--snapshot", str(self.snapshot))
        self.assertIn("revision", self.workspace("status").stdout)
        self.git("config", "core.hooksPath", "custom-hooks")
        self.workspace("install", "--snapshot", str(self.snapshot))
        self.assertEqual(
            self.git("config", "--get", "core.hooksPath").stdout.strip(), "custom-hooks"
        )
        self.workspace("remove")
        self.assertEqual(
            self.git("config", "--get", "core.hooksPath").stdout.strip(), "custom-hooks"
        )

    def test_refresh_paginates_and_retains_cache_on_errors(self):
        destination = self.root / "snapshot"
        calls = []

        def fetch(project, cursor):
            calls.append((project, cursor))
            return {
                "data": {
                    "issues": {
                        "nodes": [{"identifier": "AI-7" if cursor is None else "AI-10"}],
                        "pageInfo": {"hasNextPage": cursor is None, "endCursor": "next"},
                    }
                }
            }

        self.assertEqual(refresh(self.policy, destination, fetch), 2)
        self.assertEqual(calls[1][1], "next")
        before = destination.read_bytes()
        with self.assertRaises(ValueError):
            refresh(self.policy, destination, lambda *_: {"errors": [{"message": "denied"}]})
        self.assertEqual(destination.read_bytes(), before)
