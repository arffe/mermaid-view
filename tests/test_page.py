"""viewer.html with the bundled Mermaid, in a WebKit view that's never shown.

These run real Mermaid, so run them after updating vendor/mermaid.min.js.
They need a graphical session (Wayland or X11) and are skipped without one.
"""
import json
import re
import unittest

from support import ROOT, load_viewer


def setUpModule():
    global mv, page
    mv = load_viewer()
    if mv.Gdk.Display.get_default() is None:
        raise unittest.SkipTest("needs a graphical session")
    page = Page()


class Page:
    def __init__(self):
        self.loop = mv.GLib.MainLoop()
        content = mv.WebKit.UserContentManager()
        content.register_script_message_handler("mv", None)  # showDiagram posts here
        self.window = mv.Gtk.Window()
        self.view = mv.WebKit.WebView(user_content_manager=content)
        self.window.set_child(self.view)
        self.view.connect("load-changed", self.on_load)
        self.view.load_uri((ROOT / "viewer.html").as_uri())
        self.wait()

    def on_load(self, _view, event):
        if event == mv.WebKit.LoadEvent.FINISHED:
            self.loop.quit()

    def wait(self):
        def too_slow():
            self.result = TimeoutError("page didn't respond")
            self.loop.quit()
            return mv.GLib.SOURCE_REMOVE
        timer = mv.GLib.timeout_add_seconds(30, too_slow)
        self.loop.run()
        if not isinstance(getattr(self, "result", None), TimeoutError):
            mv.GLib.source_remove(timer)

    def call(self, body):
        """Run an async JavaScript body; it returns a value that JSON can carry."""
        def done(view, res):
            try:
                self.result = json.loads(view.call_async_javascript_function_finish(res).to_string())
            except Exception as e:  # noqa: BLE001 - reported on the calling side
                self.result = e
            self.loop.quit()
        script = f"return JSON.stringify(await (async () => {{ {body} }})());"
        self.view.call_async_javascript_function(script, -1, None, None, None, None, done)
        self.wait()
        if isinstance(self.result, Exception):
            raise self.result
        return self.result

    def choose(self, text):
        candidates = [{"src": s, "label": mv.label_for(s)} for s in mv.extract(text)]
        return self.call(f"return await firstThatParses({json.dumps(candidates)});")

    def show(self, source):
        candidates = [{"src": source, "label": mv.label_for(source)}]
        about = {"when": "", "detail": "From clipboard · 12:00", "pos": ""}
        return self.call(f"""
            await showDiagram({json.dumps(candidates)}, null, {json.dumps(about)});
            return {{
              hasSvg: !!stage.querySelector('svg'),
              error: err.style.display === 'block' ? err.textContent : null,
              info: info.innerText,
              clusterWidths: [...stage.querySelectorAll('.cluster-label foreignObject > div')]
                .map(d => d.style.maxWidth),
            }};""")


class FindingTheEnd(unittest.TestCase):
    def test_whole_diagram(self):
        chosen = page.choose("flowchart LR\n  A --> B")
        self.assertEqual(chosen["src"], "flowchart LR\n  A --> B")
        self.assertEqual(chosen["dropped"], 0)

    def test_prose_after_is_cut_at_the_blank_line(self):
        chosen = page.choose("flowchart LR\n  A --> B\n\nLet me know.\nThanks!")
        self.assertEqual(chosen["src"], "flowchart LR\n  A --> B")
        self.assertEqual(chosen["dropped"], 2)

    def test_indented_diagram_above_unindented_prose(self):
        chosen = page.choose("Here:\n\n    flowchart LR\n      A --> B\n\nThat's it.")
        self.assertEqual(chosen["src"], "flowchart LR\n  A --> B")

    def test_blank_lines_inside_a_diagram_are_kept(self):
        chosen = page.choose("flowchart LR\n  A --> B\n\n  B --> C\n\nThat's it.")
        self.assertEqual(chosen["src"], "flowchart LR\n  A --> B\n\n  B --> C")
        self.assertEqual(chosen["dropped"], 1)

    def test_broken_diagram_does_not_shrink_into_a_valid_empty_one(self):
        # Cutting line by line used to leave just "flowchart LR": a blank window.
        self.assertIsNone(page.choose("flowchart LR\n  A -->\nmore prose"))

    def test_later_candidate_when_the_first_is_not_mermaid(self):
        chosen = page.choose("sequenceDiagram\nnot valid at all ((\n\nflowchart LR\n  A --> B")
        self.assertEqual(chosen["src"], "flowchart LR\n  A --> B")


class Showing(unittest.TestCase):
    def test_good_diagram(self):
        shown = page.show("flowchart LR\n  A --> B")
        self.assertTrue(shown["hasSvg"])
        self.assertIsNone(shown["error"])

    def test_two_line_label(self):
        lines = page.show("gantt\n  title Plan\n  section S\n  T : t1, 2026-01-01, 1d")["info"].split("\n")
        self.assertEqual(lines, ["Plan", "From clipboard · 12:00"])

    def test_broken_diagram_shows_the_error_and_source(self):
        shown = page.show("flowchart LR\n  A -->\nmore prose")
        self.assertFalse(shown["hasSvg"])
        self.assertIn("couldn't draw this", shown["error"])
        self.assertIn("more prose", shown["error"])

    def test_subgraph_titles_are_not_capped(self):
        # Workaround for Mermaid's 200px wrap on subgraph titles. If this fails
        # after a Mermaid update, check long subgraph titles by eye.
        shown = page.show('flowchart LR\n  subgraph S["A long subgraph title"]\n    A --> B\n  end')
        self.assertEqual(shown["clusterWidths"], ["none"])


class BundledMermaid(unittest.TestCase):
    def assertParses(self, source):
        result = page.call(f"""
            try {{ await mermaid.parse({json.dumps(source)}); return 'ok'; }}
            catch (e) {{ return String(e.message || e); }}""")
        self.assertEqual(result, "ok")

    def test_every_example_parses(self):
        files = sorted((ROOT / "examples").glob("*.mmd"))
        self.assertTrue(files)
        for path in files:
            with self.subTest(path.name):
                self.assertParses(path.read_text())

    def test_readme_diagrams_parse(self):
        blocks = re.findall(r"^```mermaid\n(.*?)^```", (ROOT / "README.md").read_text(), re.S | re.M)
        self.assertTrue(blocks)
        for block in blocks:
            self.assertParses(block)


if __name__ == "__main__":
    unittest.main()
