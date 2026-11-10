#!/usr/bin/env python3
# gdcheck: check the GDScript in Markdown files (agent skills, docs, READMEs) with Godot 4 itself.
# Part of godot-skill-check. By MV2 of Munim, Inc. (mv2@munimtech.com).
# Made with AI agents (Anthropic Claude) working in his name.
# SPDX-License-Identifier: Apache-2.0
"""gdcheck: check the GDScript code blocks in Markdown files with Godot 4's own --check-only.

Usage:
  python gdcheck.py --godot /path/to/godot [options] PATH [PATH ...]

Each PATH is a Markdown file (.md, .markdown, .mdx), a .gd file (with --gd-files) or a folder
(searched recursively). Every fenced block labelled gdscript/gd is read:

  * a complete script (its first code line is `extends`, `class_name`, `@tool`, ...) is checked
    by Godot as it is;
  * a block preceded by `<!-- gdcheck: extends Node2D -->` is wrapped in that base class and
    checked as an error-level script;
  * with --fragments, other fragments made only of declarations (func, var, const, signal, enum,
    class, annotations) are wrapped in `extends Node` and checked; their errors are warnings;
  * `<!-- gdcheck: skip -->` before a block skips it, and so (unless --no-auto-skip) does a block
    marked as a deliberate wrong or Godot 3 example (a "Bad", "Wrong", "Before:", "# 3.x",
    "deprecated", "results in an error", ... marker in the three lines before it or in its own
    comments).

Errors about names defined elsewhere (a class_name or autoload from another file, a missing
preload path) are reported as "external" warnings, not errors, and so are errors that only follow
from them (rules from godot-skill-check's 2026 study of 2,239 skill scripts). A block header whose
body is only a comment, or a signature with no body at the end of the block, is "elision" (a
deliberate placeholder). Exit code: 0 clean, 1 if any error (or any external warning with
--fail-on-external), 2 on a usage problem.

Code from Markdown is written to Godot with a trailing newline: Godot 4 rejects a file whose last
token closes a lambda when no newline follows (godotengine/godot#96228, still in 4.7.2), and a
fenced block has no newline of its own. A .gd file is checked exactly as it is on disk.

Only the Python standard library is used. Godot 4 (any 4.x; tested with 4.7.2) must be installed.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

VERSION = "0.3.0"
GD_LANGS = {"gdscript", "gd", "gdscript2", "gdscript4"}
MD_SUFFIXES = {".md", ".markdown", ".mdx"}
SKIP_DIRS = {".git", "node_modules", ".godot", ".import", "__pycache__", ".venv", "venv"}
DEFAULT_TIMEOUT = 60
PROJECT_GODOT = 'config_version=5\n\n[application]\n\nconfig/name="gdcheck"\n'
EOF_LAMBDA_HINT = ("the file does not end with a newline; Godot 4 rejects a lambda at the very end of a file "
                   "without one (godotengine/godot#96228). Add a newline at the end of the file.")

# ---------------------------------------------------------------- markers
MARK_RE = re.compile(r"<!--\s*gdcheck\s*:\s*(skip|ignore|extends\s+[A-Za-z_][\w.]*)\s*-->", re.I)
# A block counts as a deliberate wrong / Godot 3 example if one of these appears in the three
# non-blank lines before it or in one of its own # comments. v0.2 added "# Before", "# 3.x" and
# "Problem:"; v0.3 adds "results in an error" and "compile time error" (the godot-docs hand check
# found both unmarked).
CONTRAST_RE = re.compile(
    r"❌|✗|✘|\bbad\b|\bwrong\b|incorrect|anti-?pattern|godot\s*3\b|"
    r"gdscript\s*1\b|deprecated|legacy|outdated|old way|\bbefore\b\s*(:|\(|$)|"
    r"\b3\.x\b|problem:|don'?t do|do not do|"
    r"\bresults? in an? (parse |compile |compilation |script )?error\b|\bcompile[- ]time error\b", re.I | re.M)

FENCE_OPEN = re.compile(r"^(\s*)(`{3,}|~{3,})\s*([^\s`]*)")
FENCE_CLOSE = re.compile(r"^\s*(`{3,}|~{3,})\s*$")
COMPLETE_RE = re.compile(r"^(extends\b|class_name\b|@tool\b|tool\s*$|@icon\s*\(|@static_unload\b|@abstract\b)")
DECL_RE = re.compile(r"^(static\s+(func|var)\b|func\b|var\b|const\b|signal\b|enum\b|class\s|@\w+)")

# ---------------------------------------------------------------- Godot output
ERR_RE = re.compile(r"SCRIPT ERROR:\s*(?:Parse Error:\s*|Compile Error:\s*)?(.*)")
AT_RE = re.compile(r"at:\s*.*\((res://[^:)]+):(\d+)\)")
QUOTED_RE = re.compile(r'"([^"]+)"')
ELISION_RE = re.compile(r'"(\.\.\.|…)"|…')
INDENT_BLOCK_RE = re.compile(r"^Expected indented block after")
CONST_NOT_TYPE_RE = re.compile(r'^"([A-Za-z_]\w*)" is a constant but does not contain a type')
EOF_RE = re.compile(r"^Expected end of file")
EXTERNAL_RES = [re.compile(x) for x in [
    r'Could not find type "', r'Could not find base class "', r'Could not resolve class "',
    r'Could not resolve super class', r'Could not resolve script "',
    r'Could not resolve external class member', r'Preload file "[^"]*" does not exist',
    r'Could not preload resource', r'Could not load the base class',
    r'Could not find (?:script|class) for class name', r"couldn't be fully loaded",
    r'Identifier "[A-Z][a-z0-9]\w*" not declared in the current scope',
    # v0.2: Godot's compile-stage wording for the same thing (e.g. "Identifier not found: BigNumber")
    r'Identifier not found: [A-Z][a-z0-9]\w*\s*$',
]]
# Godot 3 names whose appearance in an error message means the code is Godot 3 API.
# v0.2 drops change_scene: user-defined change_scene() helpers are common (v0.1 hand check).
G3_IDENTS = {
    "KinematicBody2D", "KinematicBody", "Spatial", "SpatialMaterial", "Position2D", "Position3D",
    "AnimatedSprite", "Sprite", "Particles2D", "Particles", "VisibilityNotifier2D", "YSort",
    "Navigation2D", "VisualServer", "Physics2DServer", "TextureProgress", "VideoPlayer",
    "ViewportContainer", "ShortCut", "GIProbe", "StreamTexture", "rand_range", "deg2rad", "rad2deg",
    "stepify", "range_lerp", "linear2db", "db2linear", "str2var", "var2str", "funcref", "ColorN",
    "yield", "setget", "onready", "export", "tool", "PoolStringArray", "PoolVector2Array",
    "PoolVector3Array", "PoolIntArray", "PoolRealArray", "PoolByteArray", "PoolColorArray",
    "is_network_master", "editor_hint", "interpolate_property", "instance", "File", "Directory",
    "BUTTON_LEFT", "BUTTON_RIGHT", "BUTTON_MIDDLE", "remote", "master", "puppet", "remotesync",
}
G3_TEXT_RE = re.compile(r"was removed in Godot 4|in Godot 4\b.*\binstead", re.I)
DECLARED_RE = re.compile(r"^\s*(?:@\w+(?:\([^)]*\))?\s+)*(?:static\s+)?(?:var|const)\s+([A-Za-z_]\w*)")


# ================================================================ Markdown
def split_code(line):
    """The part of a GDScript line before its # comment (string contents respected)."""
    q = None
    i, n = 0, len(line)
    while i < n:
        c = line[i]
        if q is None:
            if c == "#":
                return line[:i]
            if c in "\"'":
                q = c
        elif c == "\\":
            i += 1
        elif c == q:
            q = None
        i += 1
    return line


def extract_blocks(text):
    """Fenced code blocks: dicts with lang, fence_line (1-based), code, context, mark."""
    lines = text.splitlines()
    blocks = []
    i = 0
    prev_end = 0   # context never reaches back past the previous block's closing fence
    while i < len(lines):
        m = FENCE_OPEN.match(lines[i])
        if not m:
            i += 1
            continue
        fence = m.group(2)
        lang = re.split(r"[:,{]", m.group(3).strip().lower())[0].strip(".") if m.group(3) else ""
        start = i
        j = i + 1
        body = []
        while j < len(lines):
            m2 = FENCE_CLOSE.match(lines[j])
            if m2 and m2.group(1)[0] == fence[0] and len(m2.group(1)) >= len(fence):
                break
            body.append(lines[j])
            j += 1
        before = [ln for ln in lines[max(prev_end, start - 8):start] if ln.strip()][-3:]
        mark = None
        for ln in before:
            mm = MARK_RE.search(ln)
            if mm:
                mark = re.sub(r"\s+", " ", mm.group(1).strip())
        blocks.append({"lang": lang, "fence_line": start + 1, "code": textwrap.dedent("\n".join(body)),
                       "context": "\n".join(MARK_RE.sub("", ln) for ln in before), "mark": mark,
                       "closed": j < len(lines)})
        i = j + 1
        prev_end = i
    return blocks


def first_code_line(code):
    for ln in code.splitlines():
        s = ln.strip()
        if s and not s.startswith("#"):
            return s
    return ""


def is_complete(code):
    return bool(COMPLETE_RE.match(first_code_line(code)))


def is_multi_file(code):
    lines = code.splitlines()
    return (sum(1 for ln in lines if re.match(r"^extends\b", ln)) > 1 or
            sum(1 for ln in lines if re.match(r"^class_name\b", ln)) > 1)


def is_declaration_fragment(code):
    """True if every top-level (unindented) code line is a declaration, so the block can be wrapped."""
    seen = False
    for ln in code.splitlines():
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        if ln[0] in " \t":
            if not seen:
                return False
            continue
        if not DECL_RE.match(ln):
            return False
        seen = True
    return seen


def is_contrast(block):
    if CONTRAST_RE.search(block.get("context", "")):
        return True
    for ln in block["code"].splitlines():
        comment = ln[len(split_code(ln)):]
        if comment and CONTRAST_RE.search(comment):
            return True
    return False


def _indent(ln):
    return len(ln) - len(ln.lstrip(" \t"))


def placeholder_body(code):
    """True if some block header (a code line ending in ':') has a placeholder body: only comments
    up to the next line that is not indented deeper, or nothing at all up to the end of the code.
    A header followed directly by code at the same indentation (a real missing indent) is not one."""
    lines = code.splitlines()
    for i, ln in enumerate(lines):
        c = split_code(ln).rstrip()
        if not c.strip() or not c.endswith(":"):
            continue
        ind = _indent(ln)
        comments = 0
        j = i + 1
        while j < len(lines):
            s = lines[j].strip()
            if not s:
                j += 1
                continue
            if s.startswith("#"):
                comments += 1
                j += 1
                continue
            break
        if j < len(lines) and _indent(lines[j]) > ind:
            continue  # the header has a real body
        if comments or j >= len(lines):
            return True
    return False


# ================================================================ planning
def find_files(paths, gd_files=False):
    out = []
    for p in paths:
        p = Path(p)
        if p.is_file():
            out.append(p)
            continue
        if not p.is_dir():
            raise FileNotFoundError(str(p))
        for root, dirs, files in os.walk(p):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            for f in files:
                fp = Path(root) / f
                suf = fp.suffix.lower()
                if suf in MD_SUFFIXES or (gd_files and suf == ".gd"):
                    out.append(fp)
    seen, uniq = set(), []
    for f in out:
        k = f.resolve().as_posix()
        if k not in seen:
            seen.add(k)
            uniq.append(f)
    return sorted(uniq, key=lambda f: f.as_posix())


def display_path(p):
    try:
        return Path(os.path.relpath(Path(p).resolve(), Path.cwd().resolve())).as_posix()
    except ValueError:
        return Path(p).as_posix()


def plan_file(path, fragments=False, auto_skip=True):
    """Entries for one file: each has file, line, index, kind, and either code to check or a status."""
    path = Path(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    shown = display_path(path)
    if path.suffix.lower() == ".gd":
        return [{"file": shown, "line": 1, "index": 1, "kind": "gd-file", "code": text, "offset": 0,
                 "severity": "error"}]
    entries = []
    n = 0
    for b in extract_blocks(text):
        if b["lang"] not in GD_LANGS:
            continue
        n += 1
        e = {"file": shown, "line": b["fence_line"], "index": n, "kind": "script", "offset": 0,
             "severity": "error"}
        code = b["code"]
        mark = (b["mark"] or "").lower()
        if mark in ("skip", "ignore"):
            e.update(status="skipped", reason="gdcheck: skip marker")
        elif not b["closed"]:
            e.update(status="skipped", reason="unclosed code fence")
        elif auto_skip and is_contrast(b):
            e.update(status="skipped", reason="marked as a wrong or Godot 3 example")
        elif mark.startswith("extends"):
            base = b["mark"].split(None, 1)[1]
            if is_complete(code):
                e.update(code=code)
            else:
                e.update(kind="fragment", code=f"extends {base}\n" + code, offset=1)
        elif is_complete(code):
            if is_multi_file(code):
                e.update(status="skipped", reason="several scripts in one block")
            else:
                e.update(code=code)
        elif fragments and is_declaration_fragment(code):
            e.update(kind="fragment", code="extends Node\n" + code, offset=1, severity="warning")
        else:
            e.update(status="fragment", reason="not a complete script (not checked)")
        entries.append(e)
    return entries


# ================================================================ Godot output
def parse_output(text):
    errors = []
    lines = text.splitlines()
    for k, ln in enumerate(lines):
        m = ERR_RE.search(ln)
        if not m:
            continue
        line_no = None
        for l2 in lines[k + 1:k + 3]:
            a = AT_RE.search(l2)
            if a:
                line_no = int(a.group(2))
                break
        errors.append({"msg": m.group(1).strip(), "script_line": line_no})
    failed = any(("Failed to load script" in ln) or ("Failed loading resource" in ln) for ln in lines)
    return errors, failed


def base_category(msg):
    quoted = {q.rstrip("()") for q in QUOTED_RE.findall(msg)}
    if quoted & G3_IDENTS or G3_TEXT_RE.search(msg):
        return "godot3"
    if any(rx.search(msg) for rx in EXTERNAL_RES):
        return "external"
    if ELISION_RE.search(msg):
        return "elision"
    if re.search(r"infer", msg, re.I):
        return "inference"
    return "other"


def classify_errors(errors, code):
    """Give each error a category: godot3, external, cascade, elision, inference or other.

    v0.2 cascade rule: an inference error is "cascade" (it follows from another error, so it takes
    that error's place) when another error is reported on the same line, or when its line uses a
    variable or constant declared on a line that has an external error.
    v0.3: '"X" is a constant but does not contain a type' is a cascade of external when X is
    declared on a line with an external error (a missing preload); "Expected indented block" is
    elision when the code has a placeholder body (see placeholder_body).
    """
    lines = code.splitlines()
    for e in errors:
        e["category"] = base_category(e["msg"])
    by_line = {}
    for e in errors:
        by_line.setdefault(e["script_line"], []).append(e)
    ext_names = set()
    for e in errors:
        if e["category"] == "external" and e["script_line"] and e["script_line"] <= len(lines):
            m = DECLARED_RE.match(lines[e["script_line"] - 1])
            if m:
                ext_names.add(m.group(1))
    placeholder = None
    for e in errors:
        if e["category"] == "other":
            mc = CONST_NOT_TYPE_RE.match(e["msg"])
            if mc and mc.group(1) in ext_names:
                e["category"] = "cascade"
                e["follows"] = "external"
                continue
            if INDENT_BLOCK_RE.match(e["msg"]):
                if placeholder is None:
                    placeholder = placeholder_body(code)
                if placeholder:
                    e["category"] = "elision"
            continue
        if e["category"] != "inference":
            continue
        roots = [x for x in by_line.get(e["script_line"], []) if x is not e and x["category"] != "inference"]
        if roots:
            e["category"] = "cascade"
            e["follows"] = roots[0]["category"]
            continue
        if ext_names and e["script_line"] and e["script_line"] <= len(lines):
            src = split_code(lines[e["script_line"] - 1])
            if any(re.search(r"(?<![\w.])" + re.escape(nm) + r"\b", src) for nm in ext_names):
                e["category"] = "cascade"
                e["follows"] = "external"
    return errors


def status_of(errors, returncode, failed, timed_out):
    if timed_out:
        return "timeout"
    if not errors:
        return "fail-unknown" if (failed or returncode not in (0, None)) else "ok"
    cats = set()
    for e in errors:
        cats.add(e.get("follows", e["category"]) if e["category"] == "cascade" else e["category"])
    if cats & {"godot3", "inference", "other"}:
        return "error"
    if "elision" in cats:
        return "elision"
    return "external"


# ================================================================ running Godot
class GodotRunner:
    def __init__(self, godot, timeout=DEFAULT_TIMEOUT):
        self.godot = godot
        self.timeout = timeout
        self.proj = Path(tempfile.mkdtemp(prefix="gdcheck-"))
        (self.proj / "s").mkdir()
        (self.proj / "project.godot").write_text(PROJECT_GODOT, encoding="utf-8")

    def version(self):
        try:
            p = subprocess.run([self.godot, "--headless", "--version"], capture_output=True, text=True,
                               timeout=120, errors="replace")
        except (OSError, subprocess.TimeoutExpired):
            return ""
        out = (p.stdout or "").strip().splitlines()
        return out[-1].strip() if out else ""

    def __call__(self, code, keep_eof=False):
        """Check one script. Unless keep_eof, a missing trailing newline is added first (v0.3)."""
        if not keep_eof and not code.endswith("\n"):
            code += "\n"
        h = hashlib.sha256(code.encode("utf-8")).hexdigest()[:16]
        rel = f"s/{h}.gd"
        (self.proj / rel).write_text(code, encoding="utf-8", newline="\n")
        cmd = [self.godot, "--headless", "--path", str(self.proj), "--check-only", "--script", "res://" + rel]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout, errors="replace")
            return p.returncode, (p.stdout or "") + "\n" + (p.stderr or ""), False
        except subprocess.TimeoutExpired:
            return None, "", True

    def close(self):
        shutil.rmtree(self.proj, ignore_errors=True)


def check_entries(entries, runner):
    """Run every checkable entry (identical code is checked once) and fill in status and errors."""
    cache = {}
    for e in entries:
        if "status" in e:
            e.setdefault("errors", [])
            continue
        code = e["code"]
        raw = e["kind"] == "gd-file"
        key = (code, raw)
        if key not in cache:
            rc, out, to = runner(code, keep_eof=True) if raw else runner(code)
            errs, failed = parse_output(out)
            classify_errors(errs, code)
            if raw and not code.endswith("\n"):
                for x in errs:
                    if EOF_RE.match(x["msg"]):
                        x["hint"] = EOF_LAMBDA_HINT
            cache[key] = (status_of(errs, rc, failed, to), errs)
        st, errs = cache[key]
        e["status"] = st
        e["errors"] = []
        for x in errs:
            y = dict(x)
            sl = y.get("script_line")
            if sl is not None:
                y["line"] = sl if e["kind"] == "gd-file" else e["line"] + sl - e["offset"]
                if e["offset"] and sl <= e["offset"]:
                    y["line"] = e["line"]
            else:
                y["line"] = e["line"]
            e["errors"].append(y)
    for e in entries:
        e.pop("code", None)
    return entries


# ================================================================ reporting
def counts_of(entries):
    c = {}
    for e in entries:
        c[e["status"]] = c.get(e["status"], 0) + 1
    return dict(sorted(c.items()))


def exit_code_of(entries, fail_on_external=False):
    for e in entries:
        if e["status"] in ("error", "timeout", "fail-unknown") and e["severity"] == "error":
            return 1
        if fail_on_external and e["status"] == "external" and e["severity"] == "error":
            return 1
    return 0


def gh_escape(s, prop=False):
    s = s.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    if prop:
        s = s.replace(":", "%3A").replace(",", "%2C")
    return s


def annotation_level(e, fail_on_external=False):
    if e["status"] in ("error", "timeout", "fail-unknown"):
        return e["severity"]
    if e["status"] == "external":
        return "error" if (fail_on_external and e["severity"] == "error") else "warning"
    if e["status"] == "elision":
        return "notice"
    return None


def problem_lines(e):
    if e["status"] == "timeout":
        return [(e["line"], "Godot timed out checking this block", "timeout")]
    if e["status"] == "fail-unknown":
        return [(e["line"], "Godot failed to load this script without a parse error", "fail-unknown")]
    out = []
    for x in e["errors"]:
        cat = x["category"] if x["category"] != "cascade" else f"cascade of {x.get('follows', '?')}"
        msg = x["msg"] + (f" (hint: {x['hint']})" if x.get("hint") else "")
        out.append((x["line"], msg, cat))
    return out


def format_github(entries, godot_version, fail_on_external=False):
    title = gh_escape(f"gdcheck (Godot {godot_version or '4'})", prop=True)
    out = []
    for e in entries:
        level = annotation_level(e, fail_on_external)
        if not level:
            continue
        for line, msg, cat in problem_lines(e):
            out.append(f"::{level} file={gh_escape(e['file'], True)},line={line},title={title}::"
                       f"{gh_escape(msg)} [{cat}; {e['kind']} block at line {e['line']}]")
    return out


def format_text(entries, fail_on_external=False):
    out = []
    for e in entries:
        level = annotation_level(e, fail_on_external)
        if level:
            for line, msg, cat in problem_lines(e):
                out.append(f"{e['file']}:{line}: {level}: {msg} [{cat}]")
    return out


def summary_markdown(entries, godot_version):
    c = counts_of(entries)
    rows = ["| Result | Blocks |", "|---|---|"] + [f"| {k} | {v} |" for k, v in c.items()]
    bad = [e for e in entries if e["status"] in ("error", "timeout", "fail-unknown")]
    lines = [f"### gdcheck {VERSION} (Godot {godot_version or '?'})", ""] + rows + [""]
    if bad:
        lines += ["| File | Block line | First problem |", "|---|---|---|"]
        for e in bad[:50]:
            pl = problem_lines(e)
            msg = pl[0][1].replace("|", "\\|") if pl else ""
            lines.append(f"| {e['file']} | {e['line']} | {msg} |")
        lines.append("")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="gdcheck", description=__doc__.splitlines()[0])
    ap.add_argument("paths", nargs="+", help="Markdown files, .gd files or folders")
    ap.add_argument("--godot", default=os.environ.get("GDCHECK_GODOT") or "godot",
                    help="Godot 4 binary (default: $GDCHECK_GODOT or 'godot' on PATH)")
    ap.add_argument("--format", choices=["text", "github", "json"], default="text")
    ap.add_argument("--json-out", help="also write the full JSON report to this file")
    ap.add_argument("--summary", help="append a Markdown summary to this file (e.g. $GITHUB_STEP_SUMMARY)")
    ap.add_argument("--fragments", action="store_true",
                    help="also check declaration-only fragments wrapped in 'extends Node' (as warnings)")
    ap.add_argument("--gd-files", action="store_true", help="also check .gd files found in folders")
    ap.add_argument("--no-auto-skip", action="store_true",
                    help="check blocks marked as wrong or Godot 3 examples too")
    ap.add_argument("--fail-on-external", action="store_true",
                    help="treat names defined elsewhere (external) as errors")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="seconds per script")
    ap.add_argument("--version", action="version", version=f"gdcheck {VERSION}")
    a = ap.parse_args(argv)

    godot = shutil.which(a.godot) or (a.godot if Path(a.godot).is_file() else None)
    if not godot:
        print(f"gdcheck: Godot binary not found: {a.godot} (use --godot)", file=sys.stderr)
        return 2
    try:
        files = find_files(a.paths, a.gd_files)
    except FileNotFoundError as ex:
        print(f"gdcheck: no such file or folder: {ex}", file=sys.stderr)
        return 2
    entries = []
    for f in files:
        entries += plan_file(f, fragments=a.fragments, auto_skip=not a.no_auto_skip)
    runner = GodotRunner(godot, a.timeout)
    try:
        gv = runner.version()
        check_entries(entries, runner)
    finally:
        runner.close()
    code = exit_code_of(entries, a.fail_on_external)
    report = {"tool": "gdcheck", "version": VERSION, "godot_version": gv, "files": len(files),
              "counts": counts_of(entries), "exit_code": code, "results": entries}
    if a.json_out:
        Path(a.json_out).write_text(json.dumps(report, indent=1), encoding="utf-8")
    if a.summary:
        with open(a.summary, "a", encoding="utf-8") as fh:
            fh.write(summary_markdown(entries, gv))
    if a.format == "json":
        print(json.dumps(report, indent=1))
    else:
        lines = format_github(entries, gv, a.fail_on_external) if a.format == "github" \
            else format_text(entries, a.fail_on_external)
        for ln in lines:
            print(ln)
        c = report["counts"]
        print(f"gdcheck {VERSION}: Godot {gv or '?'}; {len(files)} files, {len(entries)} GDScript blocks: "
              + ", ".join(f"{k} {v}" for k, v in c.items()) + f"; exit {code}")
    return code


if __name__ == "__main__":
    sys.exit(main())
