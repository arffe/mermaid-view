#!/bin/bash
# Link mermaid-view and mermaid-pick into ~/.local/bin, check dependencies,
# and print the Hyprland and Claude Code snippets to add by hand. It never
# edits your config files.
#   ./install.sh              install
#   ./install.sh --uninstall  remove the links (your config is left alone)

set -euo pipefail

repo="$(cd "$(dirname "$0")" && pwd)"
bin="$HOME/.local/bin"
commands=(mermaid-view mermaid-pick)

if [[ ${1:-} == --uninstall ]]; then
  for cmd in "${commands[@]}"; do
    # Only remove links that point into this checkout.
    if [[ -L $bin/$cmd && $(readlink -f "$bin/$cmd") == "$repo/$cmd" ]]; then
      rm "$bin/$cmd" && echo "Removed $bin/$cmd"
    fi
  done
  echo "Also remove the key bindings, window rule and Claude Code hook if you added them."
  echo "Saved diagrams stay in ~/.cache/mermaid-view and ~/Pictures/mermaid."
  exit 0
fi

# --- Dependencies -----------------------------------------------------------
missing=()
command -v python3 >/dev/null || missing+=(python)
command -v wl-paste >/dev/null || missing+=(wl-clipboard)
if command -v python3 >/dev/null && ! python3 -c '
import gi
gi.require_version("Gtk", "4.0"); gi.require_version("WebKit", "6.0")
from gi.repository import Gtk, WebKit' 2>/dev/null; then
  missing+=(python-gobject webkitgtk-6.0)
fi
if (( ${#missing[@]} )); then
  echo "Missing: ${missing[*]}"
  if command -v omarchy >/dev/null; then
    echo "Install with:  omarchy pkg add ${missing[*]}"
  else
    echo "Install with your package manager (Arch: sudo pacman -S ${missing[*]})."
  fi
  exit 1
fi

# --- Links ------------------------------------------------------------------
mkdir -p "$bin"
for cmd in "${commands[@]}"; do
  if [[ -e $bin/$cmd && ! -L $bin/$cmd ]]; then
    echo "$bin/$cmd exists and isn't a link; leaving it alone." >&2
    exit 1
  fi
  ln -sfn "$repo/$cmd" "$bin/$cmd"
  echo "Linked $bin/$cmd"
done

# --- What to add by hand ----------------------------------------------------
# Claude Code runs the hook through a shell, so a path with spaces needs
# quotes, written as \" inside the JSON.
hook="$repo/mermaid-capture-hook"
[[ $hook == *" "* ]] && hook="\\\"$hook\\\""

cat <<EOF

Installed. Try it: copy some Mermaid text, then run  mermaid-view

Next, add these by hand (see README.md for other setups):

1. Key bindings. Omarchy 4 (~/.config/hypr/bindings.lua):

   o.bind("SUPER + CTRL + M", "Mermaid viewer (clipboard)", o.launch("mermaid-view"))
   o.bind("SUPER + CTRL + SHIFT + M", "Mermaid viewer (recent from Claude)", o.launch("mermaid-pick"))

2. Window rule. Omarchy 4 (~/.config/hypr/hyprland.lua):

   o.window("^mermaid-view\$", {
     float = true,
     center = true,
     size = { "(monitor_w*0.8)", "(monitor_h*0.8)" },
     tag = "-default-opacity",
     opacity = "1 1",
   })

   Then check with:  hyprctl reload && hyprctl configerrors

3. Optional, Claude Code auto-capture. In ~/.claude/settings.json, add this
   next to the other top-level settings:

   "hooks": {
     "Stop": [{ "hooks": [{ "type": "command",
       "command": "$hook",
       "async": true, "timeout": 10 }] }]
   },

   Commas matter: keep the one after the closing } if more settings follow it,
   remove it if this is the last setting, and add one to the line before if
   you paste it at the end. If you already have "hooks", add only the "Stop"
   part inside it (see README.md if you already have a "Stop" hook).

   Then check the file:  python3 -m json.tool ~/.claude/settings.json >/dev/null
   No output means it's fine; otherwise it names the line to fix. A mistake
   here can stop Claude Code reading the whole settings file.
EOF
