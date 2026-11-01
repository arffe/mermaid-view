"""install.sh, on a copy of the repo with a throwaway home and a stand-in PATH."""
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from support import ROOT

COMMANDS = ["mermaid-view", "mermaid-pick"]
TOOLS = ["dirname", "mkdir", "ln", "readlink", "rm", "cat"]


class Install(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.bin = self.home / ".local/bin"
        self.repo = self.clone(self.tmp / "code")
        # A PATH with only what's needed, so the real machine's python3,
        # wl-paste and omarchy don't affect the result.
        self.path = self.tmp / "path"
        self.path.mkdir()
        for tool in TOOLS:
            (self.path / tool).symlink_to(shutil.which(tool))
        self.stub("python3")
        self.stub("wl-paste")

    def clone(self, parent):
        repo = parent / "mermaid-view"
        repo.mkdir(parents=True)
        shutil.copy(ROOT / "install.sh", repo)
        for cmd in COMMANDS:
            (repo / cmd).touch()
        return repo

    def stub(self, name, code=0):
        script = self.path / name
        script.write_text(f"#!/bin/bash\nexit {code}\n")
        script.chmod(0o755)

    def install(self, *args, repo=None):
        return subprocess.run([(repo or self.repo) / "install.sh", *args], text=True,
                              capture_output=True, timeout=10,
                              env={**os.environ, "HOME": str(self.home), "PATH": str(self.path)})

    def assertLinkedTo(self, repo):
        for cmd in COMMANDS:
            self.assertTrue((self.bin / cmd).is_symlink(), cmd)
            self.assertEqual((self.bin / cmd).resolve(), (repo / cmd).resolve())

    def test_links_the_commands(self):
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertLinkedTo(self.repo)

    def test_running_again_is_fine(self):
        self.install()
        self.assertEqual(self.install().returncode, 0)
        self.assertLinkedTo(self.repo)

    def test_moving_the_folder_then_reinstalling_updates_the_links(self):
        self.install()
        moved = self.clone(self.tmp / "elsewhere")
        self.assertEqual(self.install(repo=moved).returncode, 0)
        self.assertLinkedTo(moved)

    def test_never_replaces_a_real_file(self):
        self.bin.mkdir(parents=True)
        (self.bin / "mermaid-view").write_text("mine")
        result = self.install()
        self.assertEqual(result.returncode, 1)
        self.assertEqual((self.bin / "mermaid-view").read_text(), "mine")

    def test_missing_wl_clipboard(self):
        (self.path / "wl-paste").unlink()
        result = self.install()
        self.assertEqual(result.returncode, 1)
        self.assertIn("Missing: wl-clipboard", result.stdout)
        self.assertFalse(self.bin.exists())

    def test_missing_gtk_or_webkit(self):
        self.stub("python3", code=1)  # the import check fails
        result = self.install()
        self.assertEqual(result.returncode, 1)
        self.assertIn("python-gobject webkitgtk-6.0", result.stdout)
        self.assertFalse(self.bin.exists())

    def test_suggests_omarchy_pkg_on_omarchy(self):
        (self.path / "wl-paste").unlink()
        self.stub("omarchy")
        self.assertIn("omarchy pkg add wl-clipboard", self.install().stdout)

    def test_uninstall_removes_its_links(self):
        self.install()
        self.assertEqual(self.install("--uninstall").returncode, 0)
        for cmd in COMMANDS:
            self.assertFalse((self.bin / cmd).is_symlink())

    def test_uninstall_leaves_other_files_alone(self):
        self.bin.mkdir(parents=True)
        (self.bin / "mermaid-view").write_text("mine")
        other = self.clone(self.tmp / "other")
        (self.bin / "mermaid-pick").symlink_to(other / "mermaid-pick")
        self.install("--uninstall")
        self.assertEqual((self.bin / "mermaid-view").read_text(), "mine")
        self.assertTrue((self.bin / "mermaid-pick").is_symlink())

    def printed_hook(self, repo):
        """The printed "hooks" section, and the command Claude Code would run."""
        out = self.install(repo=repo).stdout
        section = re.search(r'^   "hooks": \{.*?^   \},$', out, re.S | re.M).group(0)
        settings = json.loads('{"theme": "dark",\n' + section + '\n"editorMode": "vim"}')
        return settings["hooks"]["Stop"][0]["hooks"][0]["command"]

    def test_printed_hook_is_valid_json_with_settings_after_it(self):
        self.assertEqual(self.printed_hook(self.repo),
                         str(self.repo / "mermaid-capture-hook"))

    def test_printed_hook_survives_spaces_in_the_path(self):
        repo = self.clone(self.tmp / "my code")
        words = shlex.split(self.printed_hook(repo))
        self.assertEqual(words, [str(repo / "mermaid-capture-hook")])


if __name__ == "__main__":
    unittest.main()
