"""Built-in preset Python snippets for pycliped.

Each value in PRESETS is the *body* of a function whose single argument is
``text`` (a str). The body may freely use ``import`` statements and may use
``return`` to set the new clipboard contents. ``return None`` (or no return)
leaves the clipboard unchanged.

The first preset in PRESETS is the default loaded on first launch.
"""

from collections import OrderedDict


_CUSTOM = '''\
"""Put your Python code here.

The argument `text` is the new clipboard text (a str).
Use `return` to set the new clipboard contents.
You can `import` any standard-library module (e.g. `import re`).
Returning `None` (or not returning anything) leaves the clipboard unchanged.
"""
return text
'''

_UPPERCASE = '''\
"""Convert the clipboard text to UPPERCASE."""
return text.upper()
'''

_LOWERCASE = '''\
"""Convert the clipboard text to lowercase."""
return text.lower()
'''

_TITLECASE = '''\
"""Convert the clipboard text to Title Case (each word capitalised)."""
return text.title()
'''

_SENTENCECASE = '''\
"""Convert the clipboard text to Sentence case.

Lowercases everything, then capitalises the first letter of each sentence.
Tweak SENTENCE_END to change which characters mark a sentence boundary.
"""
import re
SENTENCE_END = r"([.!?]\\s+|^)"
lowered = text.lower()
parts = re.split(SENTENCE_END, lowered)
out = []
for part in parts:
    if part and part[0].isalpha():
        out.append(part[0].upper() + part[1:])
    else:
        out.append(part)
return "".join(out)
'''

_STRIP_TRAILING = '''\
"""Remove trailing whitespace from every line."""
return "\\n".join(line.rstrip() for line in text.splitlines())
'''

_INDENT = '''\
"""Indent every line by INDENT.

Tweak INDENT (e.g. "  ", "\\t", "    ") to change the indentation string.
"""
INDENT = "    "
return "\\n".join(INDENT + line for line in text.splitlines())
'''

_DEDENT = '''\
"""Remove the longest common leading whitespace from every line."""
import textwrap
return textwrap.dedent(text)
'''

_REMOVE_LINEBREAKS = '''\
"""Replace line breaks with SEPARATOR (default: a single space).

Tweak SEPARATOR to use ", ", " | ", or anything else.
"""
SEPARATOR = " "
return SEPARATOR.join(line for line in text.splitlines() if line != "")
'''

_FIND_REPLACE = '''\
"""Find and replace.

Tweak FIND, REPLACE. Set USE_REGEX = True to treat FIND as a regular expression.
"""
import re
FIND = "foo"
REPLACE = "bar"
USE_REGEX = False
if USE_REGEX:
    return re.sub(FIND, REPLACE, text)
return text.replace(FIND, REPLACE)
'''

_REMOVE_DUPES = '''\
"""Remove duplicate lines.

If KEEP_FIRST is True, the first occurrence of each line is kept (order preserved).
If False, only consecutive duplicates are collapsed.
"""
KEEP_FIRST = True
lines = text.splitlines()
if KEEP_FIRST:
    seen = set()
    out = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            out.append(line)
    return "\\n".join(out)
out = []
prev = object()
for line in lines:
    if line != prev:
        out.append(line)
        prev = line
return "\\n".join(out)
'''

_UNACCENT = '''\
"""Replace accented letters with their unaccented equivalents.

For example, "café" -> "cafe", "naïve" -> "naive", "Ñoño" -> "Nono".
"""
import unicodedata
nfkd = unicodedata.normalize("NFKD", text)
return "".join(ch for ch in nfkd if not unicodedata.combining(ch))
'''

_ADD_COMMAS = '''\
"""Insert thousands-separators into runs of digits.

For example, "1234567 was sold for 9876" -> "1,234,567 was sold for 9,876".
Tweak SEP to use "." or " " instead of ",".
"""
import re
SEP = ","
def _format(match):
    digits = match.group(0)
    n = len(digits)
    parts = []
    for i, ch in enumerate(digits):
        if i and (n - i) % 3 == 0:
            parts.append(SEP)
        parts.append(ch)
    return "".join(parts)
return re.sub(r"\\d+", _format, text)
'''

_ADD_LINE_NUMBERS = '''\
"""Prefix each line with a line number.

STYLE controls the format. The string "{n}" is replaced with the number:
    "{n}: "    -> "1: hello"
    "{n}) "    -> "1) hello"
    "[{n}] "   -> "[1] hello"
    "{n}. "    -> "1. hello"
START is the first number used. PAD = True right-aligns numbers (so all
numbers occupy the same width).
"""
STYLE = "{n}: "
START = 1
PAD = True
lines = text.splitlines()
last = START + len(lines) - 1
width = len(str(last)) if PAD else 0
out = []
for i, line in enumerate(lines):
    n = str(START + i).rjust(width) if PAD else str(START + i)
    out.append(STYLE.replace("{n}", n) + line)
return "\\n".join(out)
'''

_REMOVE_LINE_NUMBERS = '''\
"""Strip leading line numbers (and a separator) from every line.

PATTERN is a regex matching the leading line-number portion to remove.
The default handles styles like "1:", "12)", "[3]", and "4." possibly preceded
by whitespace and followed by a space.
"""
import re
PATTERN = r"^\\s*(?:\\[\\s*\\d+\\s*\\]|\\d+)[\\.:\\)]?\\s+"
return "\\n".join(re.sub(PATTERN, "", line) for line in text.splitlines())
'''

_SMART_TO_STRAIGHT = '''\
"""Replace smart/curly quotes with straight ASCII quotes."""
table = {
    ord("\\u2018"): "'", ord("\\u2019"): "'",
    ord("\\u201A"): "'", ord("\\u201B"): "'",
    ord("\\u201C"): '"', ord("\\u201D"): '"',
    ord("\\u201E"): '"', ord("\\u201F"): '"',
    ord("\\u2032"): "'", ord("\\u2033"): '"',
    ord("\\u00AB"): '"', ord("\\u00BB"): '"',
}
return text.translate(table)
'''

_STRAIGHT_TO_SMART = '''\
"""Replace straight quotes with smart/curly quotes.

A simple heuristic: a quote after whitespace or at the start of the string
becomes an opening quote; otherwise a closing quote.
"""
import re
def _smart(match):
    pre = match.group(1)
    q = match.group(2)
    opening = pre == "" or pre.isspace() or pre in "([{"
    if q == '"':
        return pre + ("\\u201C" if opening else "\\u201D")
    return pre + ("\\u2018" if opening else "\\u2019")
return re.sub(r"(^|.)([\\"\\'])", _smart, text)
'''

_SPACES_TO_TABS = '''\
"""Convert leading spaces to tabs.

TAB_WIDTH spaces become one tab. Only the leading whitespace of each line
is converted; embedded spaces are left alone.
"""
import re
TAB_WIDTH = 4
def _convert(line):
    m = re.match(r"^( +)", line)
    if not m:
        return line
    spaces = m.group(1)
    tabs = "\\t" * (len(spaces) // TAB_WIDTH)
    rest_spaces = " " * (len(spaces) % TAB_WIDTH)
    return tabs + rest_spaces + line[len(spaces):]
return "\\n".join(_convert(l) for l in text.splitlines())
'''

_TABS_TO_SPACES = '''\
"""Convert tabs to spaces. TAB_WIDTH controls how many spaces per tab."""
TAB_WIDTH = 4
return text.expandtabs(TAB_WIDTH)
'''

_JUSTIFY = '''\
"""Justify text by inserting extra spaces between words on each line.

WIDTH is the target column width. Lines that are too short have spaces
distributed between their words; the last line of each paragraph is left as-is.
"""
WIDTH = 80
def _justify_line(line):
    words = line.split()
    if len(words) <= 1:
        return line
    total_chars = sum(len(w) for w in words)
    gaps = len(words) - 1
    spaces_needed = WIDTH - total_chars
    if spaces_needed <= gaps:
        return " ".join(words)
    base, extra = divmod(spaces_needed, gaps)
    out = []
    for i, w in enumerate(words):
        out.append(w)
        if i < gaps:
            out.append(" " * (base + (1 if i < extra else 0)))
    return "".join(out)
paragraphs = text.split("\\n\\n")
result = []
for para in paragraphs:
    lines = para.splitlines()
    if not lines:
        result.append(para)
        continue
    justified = [_justify_line(l) for l in lines[:-1]]
    justified.append(lines[-1])
    result.append("\\n".join(justified))
return "\\n\\n".join(result)
'''

_WORD_WRAP = '''\
"""Wrap each paragraph at WIDTH columns.

If BREAK_LONG is True, words longer than WIDTH are broken; otherwise they
are left intact (and may exceed WIDTH).
"""
import textwrap
WIDTH = 80
BREAK_LONG = False
paragraphs = text.split("\\n\\n")
return "\\n\\n".join(
    textwrap.fill(p, width=WIDTH, break_long_words=BREAK_LONG, break_on_hyphens=False)
    for p in paragraphs
)
'''

_CENTER = '''\
"""Centre each line within a column width of WIDTH."""
WIDTH = 80
return "\\n".join(line.strip().center(WIDTH) for line in text.splitlines())
'''

_URL_ENCODE = '''\
"""Percent-encode the text so it is safe to place in a URL.

By default ``/`` is left alone (so a full URL stays readable). To encode
slashes too, set SAFE = "".
"""
import urllib.parse
SAFE = "/"
return urllib.parse.quote(text, safe=SAFE)
'''

_URL_DECODE = '''\
"""Decode percent-encoded characters (e.g. %20 -> space)."""
import urllib.parse
return urllib.parse.unquote(text)
'''

_HTML_ESCAPE = '''\
"""Escape HTML special characters (&, <, >, ', \\")."""
import html
QUOTE = True
return html.escape(text, quote=QUOTE)
'''

_HTML_UNESCAPE = '''\
"""Decode HTML entities (&amp; -> &, &lt; -> <, ...)."""
import html
return html.unescape(text)
'''

_EXTRACT_URLS = '''\
"""Return one URL per line, extracted from the text. http/https/ftp scheme."""
import re
PATTERN = r"\\b(?:https?|ftp)://[^\\s<>\\"\\']+"
return "\\n".join(re.findall(PATTERN, text))
'''

_EXTRACT_EMAILS = '''\
"""Return one email address per line, extracted from the text."""
import re
PATTERN = r"\\b[\\w.+-]+@[\\w-]+\\.[\\w.-]+\\b"
return "\\n".join(re.findall(PATTERN, text))
'''

_EXTRACT_PHONES = '''\
"""Return one phone number per line, extracted from the text.

Matches a few common North-American/E.164-ish formats. Tweak PATTERN for
your locale.
"""
import re
PATTERN = r"(?:\\+?\\d{1,3}[\\s.-]?)?(?:\\(\\d{2,4}\\)|\\d{2,4})[\\s.-]?\\d{3,4}[\\s.-]?\\d{3,4}"
matches = re.findall(PATTERN, text)
return "\\n".join(m.strip() for m in matches if m.strip())
'''

_REVERSE_LINES = '''\
"""Reverse the order of lines."""
return "\\n".join(reversed(text.splitlines()))
'''

_SORT_LINES = '''\
"""Sort lines alphabetically.

REVERSE = True for descending. CASE_INSENSITIVE = True ignores case when sorting.
"""
REVERSE = False
CASE_INSENSITIVE = False
key = (lambda s: s.lower()) if CASE_INSENSITIVE else None
return "\\n".join(sorted(text.splitlines(), key=key, reverse=REVERSE))
'''

_ROT13 = '''\
"""Apply the ROT13 cipher (letters shifted by 13)."""
import codecs
return codecs.encode(text, "rot_13")
'''

_SLUGIFY = '''\
"""Turn the text into a URL-safe slug.

Lowercases, replaces non-alphanumerics with SEP, and strips leading/trailing SEP.
"""
import re
import unicodedata
SEP = "-"
nfkd = unicodedata.normalize("NFKD", text)
ascii_text = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
slug = re.sub(r"[^A-Za-z0-9]+", SEP, ascii_text).strip(SEP).lower()
return slug
'''

_TRIM = '''\
"""Strip leading and trailing whitespace from the entire clipboard."""
return text.strip()
'''


PRESETS: "OrderedDict[str, str]" = OrderedDict(
    [
        ("Custom", _CUSTOM),
        ("Uppercase", _UPPERCASE),
        ("Lowercase", _LOWERCASE),
        ("Title Case", _TITLECASE),
        ("Sentence case", _SENTENCECASE),
        ("Trim Whitespace", _TRIM),
        ("Strip Trailing Whitespace", _STRIP_TRAILING),
        ("Indent", _INDENT),
        ("Dedent", _DEDENT),
        ("Remove Line Breaks", _REMOVE_LINEBREAKS),
        ("Find and Replace", _FIND_REPLACE),
        ("Remove Duplicate Lines", _REMOVE_DUPES),
        ("Replace Accented Letters", _UNACCENT),
        ("Add Commas to Numbers", _ADD_COMMAS),
        ("Add Line Numbers", _ADD_LINE_NUMBERS),
        ("Remove Line Numbers", _REMOVE_LINE_NUMBERS),
        ("Smart Quotes -> Straight Quotes", _SMART_TO_STRAIGHT),
        ("Straight Quotes -> Smart Quotes", _STRAIGHT_TO_SMART),
        ("Spaces to Tabs", _SPACES_TO_TABS),
        ("Tabs to Spaces", _TABS_TO_SPACES),
        ("Justify Text", _JUSTIFY),
        ("Word Wrap", _WORD_WRAP),
        ("Center Text", _CENTER),
        ("URL Encode", _URL_ENCODE),
        ("URL Decode", _URL_DECODE),
        ("HTML Escape", _HTML_ESCAPE),
        ("HTML Unescape", _HTML_UNESCAPE),
        ("Extract URLs", _EXTRACT_URLS),
        ("Extract Emails", _EXTRACT_EMAILS),
        ("Extract Phone Numbers", _EXTRACT_PHONES),
        ("Reverse Line Order", _REVERSE_LINES),
        ("Sort Lines", _SORT_LINES),
        ("ROT13", _ROT13),
        ("Slugify", _SLUGIFY),
    ]
)

DEFAULT_PRESET = next(iter(PRESETS))
