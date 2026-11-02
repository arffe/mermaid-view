# Contributing

Bug reports and pull requests are welcome.

## Scope

mermaid-view is deliberately small: it shows a diagram, and you can zoom, pan
and save it. Good contributions include:

- Bug fixes
- Support for more desktops, menus or display setups
- Clearer documentation
- Mermaid updates

Probably out of scope, so please open an issue first:

- Editing or live reload
- Toolbars, settings or export options
- Heavy new dependencies

## Running from a clone

The scripts run directly, with no build step:

```bash
./install.sh                 # or run ./mermaid-view FILE without installing
```

Requirements are listed in the [README](README.md#requirements).

## Tests

From the repo folder:

```bash
python3 -W ignore::DeprecationWarning -m unittest discover -s tests
```

The `-W` part hides a warning from PyGObject on recent Python versions. The
tests use only Python's standard library and don't touch your clipboard,
config or saved diagrams. They run in about a second.

| File | Covers | Needs |
|---|---|---|
| `tests/test_extract.py` | Finding Mermaid in copied text; clipboard, then highlight | GTK + WebKitGTK |
| `tests/test_hook.py` | The Claude Code hook | Python only |
| `tests/test_install.py` | `install.sh` | Bash and basic system tools |
| `tests/test_pick.py` | The labels in the `mermaid-pick` menu | Bash and basic system tools |
| `tests/test_page.py` | `viewer.html` with the real Mermaid, including SVG saving and theme colours; opens no visible window | GTK + WebKitGTK and a graphical session |

Tests are skipped if what they need isn't available, so check the summary line
for `skipped`.

When you fix a bug, please add a test that fails without the fix.

## Check by eye

The tests don't cover how things look. If you change `viewer.html` or the
window code, run through these:

1. Open `examples/01-flowchart-with-subgraphs.mmd` and press `→` through all
   the examples. Each should draw, with readable colours.
2. Wheel zoom stays sharp, drag pans, `0` refits and `1` shows actual size.
3. `S` and `P` save files to `~/Pictures/mermaid/` that open correctly.
4. Long subgraph titles stay on one line, and the XY chart's background
   matches the theme.
5. On Omarchy, try one dark and one light theme, and check the mind map and
   Gantt examples are readable in both.
6. Open a saved SVG in a non-browser app such as Pinta or Inkscape: all the
   text should be there, on the theme's background.

## Updating Mermaid

Run `tools/update-mermaid <version>`, then the tests and the checks above. See
[`vendor/README.md`](vendor/README.md). Please don't edit
`vendor/mermaid.min.js` by hand.

## Pull requests

- Keep each one to a single change, and explain why it's needed.
- Say what you tested it on (distribution, compositor, display scale).
- Match the style of the code around your change.

By contributing, you agree that your work is released under the project's
[MIT licence](LICENSE).
