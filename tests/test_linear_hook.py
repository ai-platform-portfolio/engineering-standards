import importlib.util
import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/linear_hook.py"
spec = importlib.util.spec_from_file_location("linear_hook", SCRIPT)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)


class LinearHookTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.env = dict(
            os.environ,
            GIT_CONFIG_GLOBAL=os.devnull,
            GIT_CONFIG_NOSYSTEM="1",
            GIT_AUTHOR_NAME="Fixture",
            GIT_AUTHOR_EMAIL="fixture@example.invalid",
            GIT_COMMITTER_NAME="Fixture",
            GIT_COMMITTER_EMAIL="fixture@example.invalid",
        )
        self.git("init", "-b", "main")
        tree = self.git("write-tree").stdout.strip()
        commit = self.git("commit-tree", tree, "-m", "fixture").stdout.strip()
        self.git("update-ref", "refs/heads/main", commit)
        self.snapshot = self.root / "issues.json"
        self.snapshot.write_text(json.dumps({"verified_at": time.time(), "issues": ["AI-7"]}))
        self.run_script("install", str(self.repo), "--snapshot", str(self.snapshot))

    def git(self, *args, repo=None):
        return subprocess.run(
            ["git", "-C", str(repo or self.repo), *args],
            env=self.env,
            capture_output=True,
            text=True,
            check=True,
        )

    def run_script(self, *args, check=True):
        return subprocess.run(
            ["python3", str(SCRIPT), *args],
            env=self.env,
            capture_output=True,
            text=True,
            check=check,
        )

    def test_branch_creation_warns_without_blocking(self):
        self.assertNotIn("Linear warning", self.git("switch", "-c", "ai-7-valid").stderr)
        self.assertIn("include a Linear issue", self.git("branch", "unlinked").stderr)
        self.assertIn("not in the verified", self.git("switch", "-c", "ai-999-unknown").stderr)

    def test_worktrees_share_checks_for_new_and_existing_branches(self):
        worktree = self.root / "new"
        result = self.git("worktree", "add", "-b", "ai-7-worktree", str(worktree))
        self.assertNotIn("Linear warning", result.stderr)
        self.assertIn(
            "include a Linear issue", self.git("switch", "-c", "unlinked", repo=worktree).stderr
        )
        self.git("branch", "another-unlinked")
        result = self.git("worktree", "add", str(self.root / "existing"), "another-unlinked")
        self.assertIn("include a Linear issue", result.stderr)

    def test_missing_stale_and_corrupt_snapshots_warn(self):
        cache = self.repo / ".git/portfolio-linear/issues.json"
        for data in (None, "{}", json.dumps({"verified_at": 0, "issues": ["AI-7"]})):
            if data is None:
                cache.unlink()
            else:
                cache.write_text(data)
            self.assertIn("Linear warning", self.git("switch", "-C", "ai-7-offline").stderr)

    def test_reinstall_remove_and_existing_hook_preservation(self):
        self.run_script("install", str(self.repo), "--snapshot", str(self.snapshot))
        self.run_script("remove", str(self.repo))
        self.assertNotIn("Linear warning", self.git("switch", "-c", "no-hook").stderr)
        existing = self.repo / ".git/hooks/post-checkout"
        existing.write_text("#!/bin/sh\nexit 0\n")
        result = self.run_script(
            "install", str(self.repo), "--snapshot", str(self.snapshot), check=False
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(existing.read_text(), "#!/bin/sh\nexit 0\n")
        self.assertFalse((existing.parent / "reference-transaction").exists())
