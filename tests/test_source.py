import subprocess
import tempfile
import unittest
from pathlib import Path

from checks.source import changed_lines


class RenameDiffTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        (self.root / "modules").mkdir()
        self.original = "".join(f"# original line {i}\n" for i in range(30))
        (self.root / "modules/main.tf").write_text(self.original)
        self.git("add", ".")
        self.git("commit", "-qm", "base")
        self.base = self.git("rev-parse", "HEAD")
        (self.root / "terraform/modules").mkdir(parents=True)
        self.git("mv", "modules/main.tf", "terraform/modules/main.tf")

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args], text=True).strip()

    def test_unchanged_rename_has_no_changed_lines(self):
        self.assertEqual(changed_lines(self.root, self.base), {})

    def test_rename_with_edit_checks_the_edited_line(self):
        (self.root / "terraform/modules/main.tf").write_text(self.original + "# new comment\n")
        self.assertEqual(changed_lines(self.root, self.base), {"terraform/modules/main.tf": {31}})

    def test_new_untracked_file_remains_checked(self):
        (self.root / "terraform/modules/new.tf").write_text("# new file\n")
        self.assertEqual(changed_lines(self.root, self.base), {"terraform/modules/new.tf": {1}})

    def test_new_tracked_file_remains_checked(self):
        (self.root / "terraform/modules/new.tf").write_text("# new file\n")
        self.git("add", ".")
        self.assertEqual(changed_lines(self.root, self.base), {"terraform/modules/new.tf": {1}})
