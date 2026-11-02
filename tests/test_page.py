"""viewer.html with the bundled Mermaid, in a WebKit view that's never shown.

These run real Mermaid, so run them after updating vendor/mermaid.min.js.
They need a graphical session (Wayland or X11) and are skipped without one.
"""
import json
import re
import unittest
import xml.etree.ElementTree as ET

from support import ROOT, load_viewer


SVG = "{http://www.w3.org/2000/svg}"


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

    def show(self, source, theme=None):
        candidates = [{"src": source, "label": mv.label_for(source)}]
        about = {"when": "", "detail": "From clipboard · 12:00", "pos": ""}
        return self.call(f"""
            await showDiagram({json.dumps(candidates)}, {json.dumps(theme)}, {json.dumps(about)});
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


FLOWCHART = 'flowchart LR\n  subgraph S["Group title"]\n    A[First box] -->|an edge| B[Second box]\n  end'
JOURNEY = "journey\n  title Trip\n  section Go\n    A rather long task label to wrap: 3: Me"


class SavedSvg(unittest.TestCase):
    def saved(self, source):
        page.show(source)
        data = page.call("return svgForSaving();")
        # Must be well-formed XML, or other apps won't open it at all.
        return data, ET.fromstring(data)

    def test_no_labels_rely_on_html(self):
        for source in [FLOWCHART, JOURNEY]:
            with self.subTest(source.split()[0]):
                data, _ = self.saved(source)
                self.assertNotIn("foreignObject", data)

    def test_label_text_survives_as_svg_text(self):
        _, root = self.saved(FLOWCHART)
        texts = {"".join(t.itertext()) for t in root.iter(SVG + "text")}
        self.assertLessEqual({"Group title", "First box", "Second box", "an edge"}, texts)

    def test_no_label_is_left_in_a_switch(self):
        # A <switch> draws only its first child, which lost wrapped lines.
        data, root = self.saved(JOURNEY)
        self.assertNotIn("<switch", data)
        words = " ".join("".join(t.itertext()) for t in root.iter(SVG + "text"))
        self.assertIn("task label", words)

    def test_background_is_a_real_shape(self):
        _, root = self.saved(FLOWCHART)
        first = next(child for child in root if child.tag == SVG + "rect")
        self.assertIn("fill:", first.get("style"))
        self.assertEqual(first.get("width"), root.get("viewBox").split()[2])

    def test_on_screen_diagram_is_unchanged(self):
        page.show(FLOWCHART)
        page.call("svgForSaving(); return 0;")
        self.assertGreater(page.call("return stage.querySelectorAll('foreignObject').length;"), 0)


# Trimmed from stock themes: a low-contrast light one, and one whose accents
# are too dark for dark text.
LIGHT = {"mode": "light", "background": "#faf4ed", "foreground": "#575279",
         "dark_background": "#f2e9e1", "light_foreground": "#6e6a86", "dark_foreground": "#9893a5",
         "cyan": "#d7827e", "magenta": "#907aa9", "accent": "#56949f"}
DARK_ACCENTS = {"mode": "light", "background": "#ffffff", "foreground": "#000000",
                "dark_background": "#f5f5f5", "cyan": "#3e3e3e", "magenta": "#2e2e2e"}
MINDMAP = "mindmap\n  root((Centre))\n    One\n      Two\n    Three"


class Themes(unittest.TestCase):
    def theme(self, colors):
        return {"colors": colors, "font": ""}

    def label_contrast(self):
        return page.call("""
            const out = [];
            for (const node of stage.querySelectorAll('[class*="section-"]')) {
              const m = node.getAttribute('class').match(/section-(\\d+)/);
              const label = node.querySelector('.nodeLabel');
              if (!m || !label || !accents[m[1]]) continue;
              const [r, g, b] = getComputedStyle(label).color.match(/\\d+/g).map(Number);
              const hex = '#' + [r, g, b].map(v => v.toString(16).padStart(2, '0')).join('');
              out.push(contrast(hex, accents[m[1]]));
            }
            return out;""")

    def test_light_text_is_darkened_for_contrast(self):
        page.show(FLOWCHART, self.theme(LIGHT))
        text = page.call("return getComputedStyle(document.documentElement).getPropertyValue('--fg').trim();")
        self.assertGreaterEqual(page.call(f"return contrast('{text}', '{LIGHT['background']}');"), 10)

    def test_light_text_is_heavier(self):
        page.show(FLOWCHART, self.theme(LIGHT))
        weight = page.call("return getComputedStyle(stage.querySelector('.nodeLabel')).fontWeight;")
        self.assertEqual(weight, "500")

    def test_dark_theme_text_is_not_changed(self):
        dark = {"mode": "dark", "background": "#1a1b26", "foreground": "#a9b1d6", "cyan": "#7dcfff"}
        page.show(FLOWCHART, self.theme(dark))
        self.assertEqual(page.call("return getComputedStyle(document.documentElement).getPropertyValue('--fg').trim();"),
                         dark["foreground"])
        weight = page.call("return getComputedStyle(stage.querySelector('.nodeLabel')).fontWeight;")
        self.assertEqual(weight, "400")

    def test_mind_map_labels_stay_readable_on_dark_accents(self):
        page.show(MINDMAP, self.theme(DARK_ACCENTS))
        contrasts = self.label_contrast()
        self.assertTrue(contrasts)
        self.assertGreaterEqual(min(contrasts), 4.5)


    def test_mind_map_centre_is_readable_on_a_dark_theme(self):
        dark = {"mode": "dark", "background": "#1a1b26", "foreground": "#a9b1d6",
                "lighter_background": "#414868", "cyan": "#7dcfff"}
        page.show(MINDMAP, self.theme(dark))
        colours = page.call("""
            const hex = (c) => '#' + c.match(/\\d+/g).slice(0, 3)
              .map(v => Number(v).toString(16).padStart(2, '0')).join('');
            const root = stage.querySelector('.section-root');
            return [hex(getComputedStyle(root.querySelector('.nodeLabel')).color),
                    hex(getComputedStyle(root.querySelector('circle, rect, path, polygon')).fill)];""")
        self.assertGreaterEqual(page.call(f"return contrast('{colours[0]}', '{colours[1]}');"), 4.5)


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
