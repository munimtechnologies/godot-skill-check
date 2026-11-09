#!/usr/bin/env python3
# gdrst: find the GDScript in reStructuredText (Sphinx) files such as the official Godot docs, and
# prepare each block for Godot 4's own --check-only (complete scripts as they are, fragments wrapped).
# Part of godot-skill-check. By MV2 of Munim, Inc. (mv2@munimtech.com).
# Made with AI agents (Anthropic Claude) working in his name.
# SPDX-License-Identifier: Apache-2.0
"""gdrst: GDScript blocks in reStructuredText, for the godot-docs sample check.

Block sources (godot-docs sets highlight_language = "gdscript" in conf.py):
  code-tab         `.. code-tab:: gdscript GDScript` inside `.. tabs::`
  code-block       `.. code-block:: gdscript` (also `.. code::` / `.. sourcecode::`)
  literal-default  a `::` literal block with no `.. highlight::` in force (GDScript by default)
  literal-highlight a `::` literal block after `.. highlight:: gdscript`
A `.. code-block::` with no language takes the language in force, like Sphinx.

Fragments: declaration-only fragments are wrapped in `extends <base>`; statement fragments from
explicitly labelled GDScript blocks are wrapped in a function. <base> is the class the page's latest
checked complete script extends (fallback Node). Literal blocks that are only GDScript by default are
never statement-wrapped, because many of them are shell commands or console output.
"""
import re
import textwrap
from pathlib import Path

import gdcheck as g

VERSION = "0.1.0"
GD_LANGS = set(g.GD_LANGS) | {"gdscript"}

CODE_DIRECTIVE_RE = re.compile(r"^(\s*)\.\.\s+(code-tab|code-block|sourcecode|code)\s*::\s*(\S*)(.*)$", re.I)
HIGHLIGHT_RE = re.compile(r"^\s*\.\.\s+highlight\s*::\s*(\S+)", re.I)
TABS_RE = re.compile(r"^(\s*)\.\.\s+tabs\s*::", re.I)
EXPLICIT_RE = re.compile(r"^\s*\.\.(\s|$)")
# An explicit-markup line that is a comment: not a directive (`name::`), target (`_x:`), substitution
# (`|x|`) or footnote/citation (`[x]`).
COMMENT_RE = re.compile(r"^\s*\.\.(?:\s*$|\s+(?![\w:+-]+\s*::)(?![_|\[]))")
OPTION_RE = re.compile(r"^\s*:[\w -]+:")
ADORNMENT_RE = re.compile(r"""^([=\-~^"'`#*+._])\1{2,}$""")   # section title underlines

# Docs-specific markers of a deliberate error or "don't do this" example, in the prose just before a
# block or in the block's own comments (added to gdcheck 0.2's own markers).
DOC_CONTRAST_RE = re.compile(
    r"syntax error|parse error|"
    r"\b(will|would|can|could)\s+(cause|trigger|produce|throw|raise|result in|give|generate)\s+"
    r"(an?\s+)?([\w-]+\s+)?(error|errors|crash)\b|"
    r"\bnot (currently )?supported\b|\bunsupported\b|\bdisallowed\b|\bwould be (an? )?errors?\b|"
    r"\bwon'?t work\b|\bwill not work\b|\bdoesn'?t work\b|\bdoes not work\b|\bis invalid\b|\bnot valid\b|"
    r"\berror:", re.I | re.M)

# Errors that, in a wrapped fragment, only say a name lives elsewhere on the page (or in the wrapper).
CONTEXT_RES = [re.compile(x) for x in [
    r'^Identifier "[^"]+" not declared in the current scope',
    r'^Identifier not found: ',
    r'^Function "[^"]+" not found in base self',
    r'__gdcheck_fragment',
]]
BASE_FAIL_RE = re.compile(r'Could not find base class|Could not resolve super class|Could not resolve class')
EMPTY_BLOCK_RE = re.compile(r"^Expected (an )?indented block|^Expected statement")
ELIDED_RE = re.compile(r"^\s*(#.*(\.\.\.|…)|\.\.\.|…)\s*$", re.M)
SCRIPT_BASE_RE = re.compile(r"^(?:class_name\s+\w+\s+)?extends\s+([A-Za-z_]\w*)\s*(?:#.*)?$")
TOP_DECL_ONLY_RE = re.compile(r"^(static\s+func\b|func\b|class\s|class_name\b|extends\b|signal\b|enum\b|@)")


def indent_of(line):
    return len(line) - len(line.lstrip(" \t"))


# ================================================================ RST parsing
def _collect_indented(lines, start, parent_indent):
    """Indices [start, end) of the lines after a marker that belong to it (blank or deeper indented)."""
    j = start
    while j < len(lines):
        ln = lines[j]
        if ln.strip() and indent_of(ln) <= parent_indent:
            break
        j += 1
    end = j
    while end > start and not lines[end - 1].strip():
        end -= 1
    return end, j


def extract_rst_blocks(text, default_lang="gdscript"):
    """Code blocks in an RST file: dicts with lang, source, line (1-based marker line), first_line,
    code, context, end. Comments' bodies are ignored; directive bodies (notes, tabs) are searched."""
    lines = text.splitlines()
    blocks = []
    highlight = None          # language set by `.. highlight::`, None = Sphinx's default
    tabs_line, tabs_indent = None, -1
    i = 0
    while i < len(lines):
        ln = lines[i]
        if not ln.strip():
            i += 1
            continue
        ind = indent_of(ln)
        if tabs_line is not None and ind <= tabs_indent:
            tabs_line, tabs_indent = None, -1
        m = HIGHLIGHT_RE.match(ln)
        if m:
            highlight = m.group(1).strip().lower()
            i += 1
            continue
        m = TABS_RE.match(ln)
        if m:
            tabs_line, tabs_indent = i, ind
            i += 1
            continue
        m = CODE_DIRECTIVE_RE.match(ln)
        if m:
            kind = m.group(2).lower()
            lang = m.group(3).strip().lower()
            if kind != "code-tab" and not lang:
                lang = highlight or default_lang
            end, nxt = _collect_indented(lines, i + 1, ind)
            body = lines[i + 1:end]
            k = 0
            while k < len(body) and body[k].strip() and OPTION_RE.match(body[k]):
                k += 1
            body = body[k:]
            while body and not body[0].strip():
                body.pop(0)
            first = end - len(body) + 1
            source = "code-tab" if kind == "code-tab" else "code-block"
            anchor = tabs_line if (kind == "code-tab" and tabs_line is not None) else i
            blocks.append({"lang": lang, "source": source, "line": i + 1, "first_line": first,
                           "code": textwrap.dedent("\n".join(body)), "anchor": anchor, "end": nxt})
            i = nxt
            continue
        if EXPLICIT_RE.match(ln):
            if COMMENT_RE.match(ln):
                _, nxt = _collect_indented(lines, i + 1, ind)
                i = nxt
                continue
            i += 1
            continue
        if ln.rstrip().endswith("::"):
            # literal block: the following lines indented deeper than this paragraph line
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and indent_of(lines[j]) > ind:
                end, nxt = _collect_indented(lines, i + 1, ind)
                body = lines[j:end]
                lang = highlight or default_lang
                source = "literal-highlight" if highlight else "literal-default"
                blocks.append({"lang": lang, "source": source, "line": i + 1, "first_line": j + 1,
                               "code": textwrap.dedent("\n".join(body)), "anchor": i + 1, "end": nxt})
                i = nxt
                continue
        i += 1
    # context: up to three prose lines before each block's anchor, never reaching back past the end
    # of an earlier block
    ends = sorted(b["end"] for b in blocks)
    for b in blocks:
        floor = max([e for e in ends if e <= b["anchor"]] or [0])
        ctx = []
        for ln in lines[max(floor, b["anchor"] - 10):b["anchor"]]:
            s = ln.strip()
            if not s or OPTION_RE.match(ln) or ADORNMENT_RE.match(s):
                continue
            if EXPLICIT_RE.match(ln):
                continue
            ctx.append(s)
        b["context"] = "\n".join(ctx[-3:])
    return blocks


# ================================================================ planning
def is_contrast_rst(block):
    if g.is_contrast(block):
        return True
    if DOC_CONTRAST_RE.search(block.get("context", "")):
        return True
    for ln in block["code"].splitlines():
        comment = ln[len(g.split_code(ln)):]
        if comment and DOC_CONTRAST_RE.search(comment):
            return True
    return False


def script_base(code):
    """The class a complete script extends, if it is a plain class name."""
    for ln in code.splitlines():
        m = SCRIPT_BASE_RE.match(ln.strip())
        if m and not ln[:1].isspace():
            return m.group(1)
    return None


def wrap_fragment(code, base, allow_statements):
    """(kind, wrapped code, offset) or (None, reason, 0)."""
    if g.is_declaration_fragment(code):
        return "decl-fragment", f"extends {base}\n{code}", 1
    if not allow_statements:
        return None, "not a complete script or declaration fragment (literal block)", 0
    lines = code.splitlines()
    code_lines = [ln for ln in lines if ln.strip() and not ln.lstrip().startswith("#")]
    if not code_lines:
        return None, "no code", 0
    if code_lines[0][0] in " \t":
        return None, "first code line is indented", 0
    top = [ln for ln in code_lines if ln[0] not in " \t"]
    if any(TOP_DECL_ONLY_RE.match(ln) for ln in top):
        return None, "mixes declarations and statements", 0
    ind = "\t" if any(ln.startswith("\t") for ln in lines) else "    "
    body = "\n".join((ind + ln) if ln.strip() else "" for ln in lines)
    return "stmt-fragment", f"extends {base}\nfunc __gdcheck_fragment():\n{body}\n", 2


def plan_rst_text(text, file_label, default_lang="gdscript"):
    """Entries like gdcheck.plan_file's, plus source, base and (for checkable ones) code + offset."""
    entries = []
    base = None
    n = 0
    for b in extract_rst_blocks(text, default_lang):
        if b["lang"] not in GD_LANGS:
            continue
        n += 1
        code = b["code"]
        e = {"file": file_label, "line": b["first_line"], "marker_line": b["line"], "index": n,
             "source": b["source"], "kind": "script", "offset": 0, "severity": "error",
             "complete": g.is_complete(code), "block_code": code}
        if not g.first_code_line(code):
            e.update(status="skipped", reason="no code (comments only)")
        elif is_contrast_rst(b):
            e.update(status="skipped", reason="marked as a wrong, error or Godot 3 example")
        elif g.is_complete(code):
            if g.is_multi_file(code):
                e.update(status="skipped", reason="several scripts in one block")
            else:
                e.update(code=code)
                base = script_base(code) or base
        else:
            kind, wrapped, off = wrap_fragment(code, base or "Node",
                                               allow_statements=(b["source"] != "literal-default"))
            if kind is None:
                e.update(kind="fragment", status="fragment", reason=wrapped)
            else:
                e.update(kind=kind, code=wrapped, offset=off, severity="warning", base=base or "Node")
        entries.append(e)
    return entries


# ================================================================ classification
def reclassify(errors, code, fragment):
    """Apply the docs-study rules on top of gdcheck 0.2's categories (errors already classified).

    - fragment: names from elsewhere on the page (or the wrapper) -> "context";
    - an "Expected indented block" / "Expected statement" error in a block with an elided body
      (`# ...`, `...`) -> "elision";
    - an inference error on a line with a context or external error, or using a name declared on
      such a line -> cascade of that root.
    """
    lines = code.splitlines()
    for e in errors:
        if fragment and e["category"] in ("other", "external", "inference") and \
                any(rx.search(e["msg"]) for rx in CONTEXT_RES):
            e["category"] = "context"
            e.pop("follows", None)
        elif e["category"] == "other" and EMPTY_BLOCK_RE.search(e["msg"]) and ELIDED_RE.search(code):
            e["category"] = "elision"
    by_line = {}
    for e in errors:
        by_line.setdefault(e["script_line"], []).append(e)
    names = {}
    for e in errors:
        if e["category"] in ("external", "context") and e["script_line"] and e["script_line"] <= len(lines):
            m = g.DECLARED_RE.match(lines[e["script_line"] - 1])
            if m:
                names.setdefault(m.group(1), e["category"])
    for e in errors:
        if e["category"] not in ("inference", "cascade"):
            continue
        roots = [x for x in by_line.get(e["script_line"], [])
                 if x is not e and x["category"] not in ("inference", "cascade")]
        if roots:
            e["category"] = "cascade"
            e["follows"] = roots[0]["category"]
            continue
        if names and e["script_line"] and e["script_line"] <= len(lines):
            src = g.split_code(lines[e["script_line"] - 1])
            for nm, cat in names.items():
                if re.search(r"(?<![\w.])" + re.escape(nm) + r"\b", src):
                    e["category"] = "cascade"
                    e["follows"] = cat
                    break
    return errors


def status_of(errors, returncode, failed, timed_out):
    if timed_out:
        return "timeout"
    if not errors:
        return "fail-unknown" if (failed or returncode not in (0, None)) else "ok"
    cats = {e.get("follows", e["category"]) if e["category"] == "cascade" else e["category"] for e in errors}
    if cats & {"godot3", "inference", "other"}:
        return "error"
    if "elision" in cats:
        return "elision"
    if "context" in cats:
        return "context"
    return "external"


def base_failed(errors):
    return any(e.get("script_line") == 1 and BASE_FAIL_RE.search(e["msg"]) for e in errors)


def map_lines(entry, errors):
    """Give each error the RST line it points at (wrapper lines map to the block's first line)."""
    out = []
    for x in errors:
        y = dict(x)
        sl = y.get("script_line")
        if sl is None or sl <= entry["offset"]:
            y["line"] = entry["line"]
        else:
            y["line"] = entry["line"] + sl - entry["offset"] - 1
        out.append(y)
    return out


def check_entry(entry, runner, cache):
    """Run Godot on one planned entry (fills status, errors; retries a fragment with Node as base)."""
    if "status" in entry:
        entry.setdefault("errors", [])
        return entry
    fragment = entry["kind"] != "script"

    def run(code):
        if code not in cache:
            rc, out, to = runner(code)
            errs, failed = g.parse_output(out)
            g.classify_errors(errs, code)
            reclassify(errs, code, fragment)
            cache[code] = (status_of(errs, rc, failed, to), errs)
        return cache[code]

    st, errs = run(entry["code"])
    if fragment and entry.get("base", "Node") != "Node" and base_failed(errs):
        first, rest = entry["code"].split("\n", 1)
        entry["code"] = "extends Node\n" + rest
        entry["base_retry"] = entry["base"]
        entry["base"] = "Node"
        st, errs = run(entry["code"])
    entry["status"] = st
    entry["errors"] = map_lines(entry, errs)
    return entry


def docs_url(rel_path, version="4.7"):
    p = rel_path[:-4] if rel_path.endswith(".rst") else rel_path
    return f"https://docs.godotengine.org/en/{version}/{p}.html"


def plan_file(path, root):
    path = Path(path)
    rel = path.relative_to(root).as_posix()
    return plan_rst_text(path.read_text(encoding="utf-8", errors="replace"), rel)
