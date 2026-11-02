"""Finding Mermaid in copied text, and which source the viewer reads."""
import unittest
from unittest import mock

from support import load_viewer


def setUpModule():
    global mv
    mv = load_viewer()


class StartsDiagram(unittest.TestCase):
    def test_real_first_lines(self):
        for line in ["flowchart LR", "graph TD;", "  sequenceDiagram", "pie title Pets",
                     "pie showData", "xychart-beta horizontal", "gitGraph LR:",
                     "stateDiagram-v2", "timeline", "mindmap %% note", "---", "%%{init: {}}%%"]:
            with self.subTest(line):
                self.assertTrue(mv.starts_diagram(line))

    def test_sentences_starting_with_a_keyword_are_not_diagrams(self):
        # Mermaid's timeline grammar accepts almost any text, so this check is
        # what stops "timeline of…" swallowing a whole reply.
        for line in ["timeline of events is below", "graph of results", "journey to the shops",
                     "pie chart coming up", "block of text", "flowchart:"]:
            with self.subTest(line):
                self.assertFalse(mv.starts_diagram(line))

    def test_other_text(self):
        for line in ["", "Here is the diagram:", "A --> B"]:
            with self.subTest(line):
                self.assertFalse(mv.starts_diagram(line))


class Extract(unittest.TestCase):
    def test_bare_diagram(self):
        self.assertEqual(mv.extract("flowchart LR\n  A --> B"), ["flowchart LR\n  A --> B"])

    def test_fenced_block_wins_over_the_text_around_it(self):
        text = "timeline\nprose\n```mermaid\nflowchart LR\n  A --> B\n```\nmore prose"
        self.assertEqual(mv.extract(text), ["flowchart LR\n  A --> B"])

    def test_only_the_first_fenced_block_is_used(self):
        text = "```mermaid\npie\n```\n\n```mermaid\ngantt\n```"
        self.assertEqual(mv.extract(text), ["pie"])

    def test_indented_fenced_block_is_dedented(self):
        text = "  ```mermaid\n    flowchart LR\n      A --> B\n  ```"
        self.assertEqual(mv.extract(text), ["flowchart LR\n  A --> B"])

    def test_empty_fenced_block_finds_nothing(self):
        self.assertEqual(mv.extract("```mermaid\n\n```"), [])

    def test_prose_before_is_skipped(self):
        text = "Here you go:\n\nflowchart LR\n  A --> B"
        self.assertEqual(mv.extract(text), ["flowchart LR\n  A --> B"])

    def test_false_start_is_not_a_candidate(self):
        text = "timeline of events below\n\nsequenceDiagram\n  A->>B: Hi"
        self.assertEqual(mv.extract(text), ["sequenceDiagram\n  A->>B: Hi"])

    def test_each_header_starts_a_candidate_that_runs_to_the_end(self):
        text = "timeline\nprose\n\nflowchart LR\n  A --> B"
        self.assertEqual(mv.extract(text), [text, "flowchart LR\n  A --> B"])

    def test_bare_fence_lines_are_dropped(self):
        self.assertEqual(mv.extract("```\nflowchart LR\n  A --> B\n```"),
                         ["flowchart LR\n  A --> B"])

    def test_front_matter_stays_with_its_diagram(self):
        text = "---\ntitle: T\n---\nflowchart LR\n  A --> B"
        self.assertEqual(mv.extract(text)[0], text)

    def test_no_mermaid(self):
        for text in ["", "just some words", "A --> B"]:
            with self.subTest(text):
                self.assertEqual(mv.extract(text), [])


class LabelFor(unittest.TestCase):
    def test_title_forms(self):
        for source in ["---\ntitle: Plan\n---\nflowchart LR", "gantt\n  title Plan",
                       'xychart-beta\n  title "Plan"']:
            with self.subTest(source):
                self.assertEqual(mv.label_for(source), "Plan")

    def test_first_real_line_without_a_title(self):
        self.assertEqual(mv.label_for("%% note\nflowchart LR\n  A --> B"), "flowchart LR")

    def test_multi_line_init_block_is_skipped(self):
        source = '%%{init: {\n  "theme": "base"\n}}%%\nsequenceDiagram\n  A->>B: Hi'
        self.assertEqual(mv.label_for(source), "sequenceDiagram")

    def test_front_matter_without_a_title_is_skipped(self):
        source = "---\nconfig:\n  look: handDrawn\n---\nflowchart LR\n  A --> B"
        self.assertEqual(mv.label_for(source), "flowchart LR")

    def test_long_labels_are_cut(self):
        self.assertEqual(len(mv.label_for("flowchart LR " + "x" * 100)), 70)


class Siblings(unittest.TestCase):
    def test_numbers_sort_as_numbers(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            for name in ["a-10.mmd", "a-2.mmd", "a-1.mmd", "other.md"]:
                (Path(d) / name).touch()
            names = [p.name for p in mv.siblings(Path(d) / "a-1.mmd")]
        self.assertEqual(names, ["a-1.mmd", "a-2.mmd", "a-10.mmd"])


class WhichSource(unittest.TestCase):
    """main() reads the clipboard first, then the highlighted text."""
    DIAGRAM = "flowchart LR\n  A --> B"

    def run_main(self, clipboard, highlight):
        def read(primary=False):
            return highlight if primary else clipboard

        def connect(signal, callback):
            callback(mock.Mock())

        with mock.patch.object(mv, "read_clipboard", read), \
                mock.patch.object(mv, "Viewer") as viewer, \
                mock.patch.object(mv, "notify") as notify, \
                mock.patch.object(mv.Gtk, "Application") as app, \
                mock.patch.object(mv.GLib, "set_prgname"), \
                mock.patch("sys.argv", ["mermaid-view"]):
            app.return_value.connect.side_effect = connect
            app.return_value.run.return_value = 0
            code = mv.main()
        return code, viewer, notify

    def test_clipboard_wins(self):
        _, viewer, _ = self.run_main(self.DIAGRAM, "pie")
        self.assertEqual(viewer.call_args.args[1:], ([self.DIAGRAM], None, "clipboard"))

    def test_highlight_is_the_fallback(self):
        _, viewer, _ = self.run_main("not a diagram", self.DIAGRAM)
        self.assertEqual(viewer.call_args.args[1:], ([self.DIAGRAM], None, "highlighted text"))

    def test_neither_notifies_and_opens_nothing(self):
        code, viewer, notify = self.run_main("words", "more words")
        self.assertEqual(code, 1)
        viewer.assert_not_called()
        notify.assert_called_once()


if __name__ == "__main__":
    unittest.main()
