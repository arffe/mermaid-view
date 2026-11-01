"""The Claude Code Stop hook, run as Claude Code runs it, in a throwaway home."""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from support import ROOT

HOOK = ROOT / "mermaid-capture-hook"


def fenced(body):
    return f"Some text\n```mermaid\n{body}\n```\nMore text\n"


class Hook(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name)
        self.history = self.home / ".cache/mermaid-view/history"

    def run_hook(self, stdin):
        if not isinstance(stdin, str):
            stdin = json.dumps(stdin)
        return subprocess.run([HOOK], input=stdin, text=True, capture_output=True,
                              env={**os.environ, "HOME": str(self.home)}, timeout=10)

    def saved(self):
        return sorted(p.read_text().strip() for p in self.history.glob("*.mmd"))

    def test_saves_a_block(self):
        self.run_hook({"last_assistant_message": fenced("flowchart LR\n  A --> B")})
        self.assertEqual(self.saved(), ["flowchart LR\n  A --> B"])

    def test_saves_every_block(self):
        message = fenced("pie") + fenced("gantt")
        self.run_hook({"last_assistant_message": message})
        self.assertEqual(self.saved(), ["gantt", "pie"])

    def test_names_sort_in_order(self):
        message = "".join(fenced(f"pie title {n}") for n in range(12))
        self.run_hook({"last_assistant_message": message})
        names = sorted(p.name for p in self.history.glob("*.mmd"))
        self.assertTrue(names[1].endswith("-02.mmd"), names[1])
        self.assertTrue(names[9].endswith("-10.mmd"), names[9])

    def test_skips_duplicates(self):
        # Delete the saved file between runs: a second run in the same second
        # would overwrite it, which would look the same as skipping it.
        message = {"last_assistant_message": fenced("pie")}
        self.run_hook(message)
        for path in self.history.glob("*.mmd"):
            path.unlink()
        self.run_hook(message)
        self.assertEqual(self.saved(), [])

    def test_skips_a_block_repeated_in_one_reply(self):
        self.run_hook({"last_assistant_message": fenced("pie") + fenced("pie")})
        self.assertEqual(len(list(self.history.glob("*.mmd"))), 1)

    def test_keeps_the_newest_50(self):
        self.history.mkdir(parents=True)
        for n in range(60):
            (self.history / f"20000101-000000-{n:02d}.mmd").write_text("pie\n")
        self.run_hook({"last_assistant_message": fenced("gantt")})
        names = sorted(p.name for p in self.history.glob("*.mmd"))
        self.assertEqual(len(names), 50)
        self.assertNotIn("20000101-000000-00.mmd", names)
        self.assertIn("gantt", self.saved())

    def test_nothing_to_save(self):
        self.run_hook({"last_assistant_message": "No diagrams here"})
        self.assertFalse(self.history.exists())

    def test_reads_the_whole_turn_from_the_transcript(self):
        def said(role, content):
            return json.dumps({"type": role, "message": {"content": content}})
        text = [{"type": "text", "text": fenced("gantt")}]
        transcript = self.home / "t.jsonl"
        transcript.write_text("\n".join([
            said("user", "first prompt"),
            said("assistant", [{"type": "text", "text": fenced("pie title old")}]),
            said("user", "second prompt"),
            said("assistant", text),
            # A tool result isn't a new prompt, so the turn carries on.
            said("user", [{"type": "tool_result", "content": "ok"}]),
            said("assistant", [{"type": "text", "text": "Done."}]),
        ]))
        self.run_hook({"transcript_path": str(transcript), "last_assistant_message": "Done."})
        self.assertEqual(self.saved(), ["gantt"])

    def test_never_fails_and_never_prints(self):
        # A failing hook would reach Claude, so bad input must stay silent.
        for stdin in ["", "not json", "[]", json.dumps({"transcript_path": "/no/such/file"})]:
            with self.subTest(stdin):
                result = self.run_hook(stdin)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout + result.stderr, "")


if __name__ == "__main__":
    unittest.main()
