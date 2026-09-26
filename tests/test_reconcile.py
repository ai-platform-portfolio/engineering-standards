import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def run(home, action, profile, answer=""):
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts/reconcile.py"), action, profile, "--home", str(home)],
        input=answer, text=True, capture_output=True, check=False,
    )


class ReconcileTest(unittest.TestCase):
    def test_preserves_existing_files_and_second_apply_is_noop(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            codex = home / ".codex/AGENTS.md"
            claude = home / ".claude/CLAUDE.md"
            codex.parent.mkdir()
            claude.parent.mkdir()
            original_codex = b"# Personal rules\r\nKeep this.\r\n"
            original_claude = b"# Claude rules\nKeep this too.\n"
            codex.write_bytes(original_codex)
            claude.write_bytes(original_claude)

            self.assertEqual(run(home, "plan", "shared").returncode, 0)
            self.assertEqual(codex.read_bytes(), original_codex)
            self.assertEqual(run(home, "apply", "shared", "y\n").returncode, 0)
            self.assertTrue(codex.read_bytes().startswith(original_codex))
            self.assertTrue(claude.read_bytes().startswith(original_claude))
            self.assertEqual(next(codex.parent.glob("AGENTS.md.backup.*")).read_bytes(), original_codex)
            self.assertEqual(next(claude.parent.glob("CLAUDE.md.backup.*")).read_bytes(), original_claude)

            installed = (codex.read_bytes(), claude.read_bytes())
            self.assertEqual(run(home, "apply", "shared").returncode, 0)
            self.assertEqual((codex.read_bytes(), claude.read_bytes()), installed)
            self.assertEqual(len(list(codex.parent.glob("AGENTS.md.backup.*"))), 1)
            self.assertEqual(run(home, "verify", "shared").returncode, 0)

    def test_conflict_or_declined_review_changes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            codex = home / ".codex/AGENTS.md"
            claude = home / ".claude/CLAUDE.md"
            codex.parent.mkdir()
            claude.parent.mkdir()
            claude.write_text("Keep my rules.\n")
            original = home / "source.md"
            original.write_text("Keep this target.\n")
            codex.symlink_to(original)

            conflict = run(home, "apply", "shared", "y\n")
            self.assertEqual(conflict.returncode, 1)
            self.assertIn("Manual review", conflict.stdout)
            self.assertEqual(claude.read_text(), "Keep my rules.\n")
            self.assertEqual(original.read_text(), "Keep this target.\n")

            codex.unlink()
            codex.write_text("Keep Codex rules.\n")
            self.assertEqual(run(home, "apply", "shared", "n\n").returncode, 1)
            self.assertEqual(codex.read_text(), "Keep Codex rules.\n")
            self.assertEqual(claude.read_text(), "Keep my rules.\n")

    def test_signal_requires_separate_opt_in(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            style = home / ".claude/output-styles/signal.md"
            style.parent.mkdir(parents=True)
            style.write_text("my style\n")
            self.assertEqual(run(home, "apply", "shared", "y\n").returncode, 0)
            codex = home / ".codex/AGENTS.md"
            self.assertNotIn("agent-setup:signal", codex.read_text())
            self.assertEqual(style.read_text(), "my style\n")

            self.assertEqual(run(home, "apply", "signal", "y\n").returncode, 0)
            self.assertIn("agent-setup:signal:start", codex.read_text())
            self.assertEqual(style.read_text(), (ROOT / "profiles/signal.md").read_text())
            self.assertEqual(next(style.parent.glob("signal.md.backup.*")).read_text(), "my style\n")

    def test_portfolio_is_opt_in_and_survives_shared_reconciliation(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            targets = [home / ".codex/AGENTS.md", home / ".claude/CLAUDE.md"]
            self.assertEqual(run(home, "apply", "shared", "y\n").returncode, 0)
            for target in targets:
                self.assertNotIn("agent-setup:portfolio", target.read_text())
            self.assertEqual(run(home, "apply", "portfolio", "y\n").returncode, 0)
            self.assertEqual(run(home, "apply", "shared").returncode, 0)
            for target in targets:
                self.assertEqual(target.read_text().count("agent-setup:portfolio:start"), 1)
                self.assertIn("agent-setup:shared:start", target.read_text())
            self.assertEqual(run(home, "verify", "portfolio").returncode, 0)


if __name__ == "__main__":
    unittest.main()
