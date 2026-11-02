"""The labels mermaid-pick shows, with a stand-in menu that records its rows."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from support import ROOT


class Pick(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.history = self.tmp / ".cache/mermaid-view/history"
        self.history.mkdir(parents=True)
        self.rows = self.tmp / "rows"
        menu = self.tmp / "bin/omarchy-menu-select"
        menu.parent.mkdir()
        # Record the rows, then exit as if the menu was cancelled.
        menu.write_text(f"""#!/bin/bash\nprintf '%s\\n' "$@" > '{self.rows}'\nexit 1\n""")
        menu.chmod(0o755)
        shutil.copy(ROOT / "mermaid-pick", self.tmp / "mermaid-pick")

    def label_for(self, text):
        (self.history / "20261102-091500-01.mmd").write_text(text)
        result = subprocess.run([self.tmp / "mermaid-pick"], capture_output=True, text=True, timeout=10,
                                env={**os.environ, "HOME": str(self.tmp),
                                     "PATH": f"{self.tmp / 'bin'}:{os.environ['PATH']}"})
        self.assertEqual(result.returncode, 0, result.stderr)
        row = self.rows.read_text().splitlines()[1:]
        return "\n".join(row).split("\t")[1]

    def test_plain_diagram(self):
        self.assertEqual(self.label_for("flowchart LR\n  A --> B\n"), "02/11 09:15  flowchart LR")

    def test_title(self):
        self.assertEqual(self.label_for('pie\n  title "Pets"\n'), "02/11 09:15  Pets")

    def test_multi_line_init_block(self):
        text = '%%{init: {\n  "theme": "base"\n}}%%\nsequenceDiagram\n  A->>B: Hi\n'
        self.assertEqual(self.label_for(text), "02/11 09:15  sequenceDiagram")

    def test_single_line_init_block(self):
        text = '%%{init: {"theme": "base"}}%%\ngantt\n  section S\n'
        self.assertEqual(self.label_for(text), "02/11 09:15  gantt")

    def test_front_matter_without_a_title(self):
        text = "---\nconfig:\n  look: neo\n---\nflowchart LR\n  A --> B\n"
        self.assertEqual(self.label_for(text), "02/11 09:15  flowchart LR")


if __name__ == "__main__":
    unittest.main()
