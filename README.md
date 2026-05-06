# pycliped

A small Python GUI app that lets you live-edit the contents of the system clipboard with custom Python code, every time you copy something new.

When pycliped is running and **Enabled**, it watches the clipboard. Each time new, non-empty text is copied, your Python function is called with that text as the argument `text`. Whatever your function `return`s becomes the new clipboard contents.

## Install

```
pip install pycliped
```

The only third-party dependency is [`pyperclip`](https://pypi.org/project/pyperclip/) — `tkinter` (which ships with the standard library) provides the GUI.

## Run

```
pycliped
```

or:

```
python -m pycliped
```

On Windows there is also `pycliped-gui`, which launches without a console window.

## How it works

The code editor in the middle of the window contains the **body** of a function whose only argument is `text` (a `str`). You don't write `def …(text):` — pycliped wraps your code automatically. Use `return` to set the new clipboard contents. Returning `None` (or not returning anything) leaves the clipboard unchanged.

Example custom code (the default "Custom" preset):

```python
"""Put your Python code here."""
return text
```

A more interesting example:

```python
import re
return re.sub(r"\\s+", " ", text).strip()
```

You may freely `import` any standard-library module.

## Built-in presets

Pick a preset from the dropdown to load it into the editor. Most presets expose `UPPERCASE` configuration constants at the top — edit them in place to tune the behaviour. Selecting a different preset immediately re-runs it against the **original** clipboard text (not the previously transformed result), so you can compare presets without re-copying.

Bundled presets include:

- Custom (default)
- Uppercase / Lowercase / Title Case / Sentence case
- Trim Whitespace / Strip Trailing Whitespace
- Indent / Dedent
- Remove Line Breaks
- Find and Replace (with optional regex)
- Remove Duplicate Lines
- Replace Accented Letters with Unaccented
- Add Commas to Numbers
- Add Line Numbers / Remove Line Numbers
- Smart Quotes ↔ Straight Quotes
- Spaces ↔ Tabs
- Justify Text / Word Wrap / Center Text
- URL Encode / URL Decode
- HTML Escape / HTML Unescape
- Extract URLs / Emails / Phone Numbers
- Reverse Line Order / Sort Lines
- ROT13
- Slugify

## Settings

- **Enabled** — toggles the live-edit behaviour. Defaults to enabled. While disabled, the app still watches the clipboard but never modifies it.
- **Run now** — runs your code against the current clipboard contents immediately, regardless of whether they changed.
- **Poll (ms)** — how often the clipboard is checked. Default 500 ms.
- **Preview (collapsible)** — shows the most recent original clipboard text and the function's result side by side, each with a line-number gutter (the line numbers are decorative; they are not part of the clipboard text).
- **History (collapsible)** — the last 20 transformations. Click an entry to load it back into the preview panes.

## Configuration / persistence

pycliped saves your last-used code, selected preset, enabled state, poll interval, window geometry, and history to:

- macOS / Linux: `~/.config/pycliped/config.json`
- Windows: `%APPDATA%\pycliped\config.json`

Delete the file to reset to defaults.

## License

MIT — see [LICENSE](LICENSE).
