"""Shared helpers: mermaid-view has no .py extension, so load it by path."""
import importlib.machinery
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True
_viewer = None


def load_viewer():
    """The mermaid-view script as a module; skips if GTK or WebKit is missing."""
    global _viewer
    if _viewer is None:
        try:
            import gi
            gi.require_version("Gtk", "4.0")
            gi.require_version("WebKit", "6.0")
        except (ImportError, ValueError) as e:
            raise unittest.SkipTest(f"needs GTK 4 and WebKitGTK 6.0: {e}")
        loader = importlib.machinery.SourceFileLoader("mermaid_view", str(ROOT / "mermaid-view"))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        _viewer = importlib.util.module_from_spec(spec)
        loader.exec_module(_viewer)
    return _viewer
