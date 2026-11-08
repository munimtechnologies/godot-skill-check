#!/usr/bin/env python3
# godot-skill-check: do the GDScript examples in Godot agent skills pass Godot 4's own check?
# By MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents (Anthropic Claude).
# SPDX-License-Identifier: Apache-2.0
"""Pre-registered check of the GDScript code in Godot agent skills listed on skills.sh.

Stages (see PREREGISTRATION.md for the exact rules and predictions):
  collect  - skills.sh search for "godot" and "gdscript", shallow-clone each source repo,
             locate every listed skill's folder and record its files.
  scan     - extract GDScript code blocks (and .gd files), run the fixed Godot-3-pattern scan
             on every block, and run Godot 4 `--check-only` on every eligible complete script.
  report   - compute the pre-registered numbers P1-P6 and the method gates M1-M2.

Only the Python standard library is used. Git and a Godot 4 binary are needed for collect/scan.
"""
import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import textwrap
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

VERSION = "0.1.0"
UA = ("godot-skill-check/0.1.0 (MV2 of Munim, Inc.; "
      "+https://github.com/munimtechnologies/godot-skill-check)")
SEARCH_URL = "https://skills.sh/api/search?q={q}&limit=200"
QUERIES = ["godot", "gdscript"]
GD_LANGS = {"gdscript", "gd", "gdscript2", "gdscript4"}
MAX_SCRIPTS = 3000
GODOT_TIMEOUT = 60
EXPECTED_GODOT = "4.7.2"

# ---------------------------------------------------------------- contrast markers
# Words that mark a block or line as a deliberate "wrong / Godot 3" example.
CONTRAST = re.compile(
    r"❌|✗|\bbad\b|\bwrong\b|incorrect|anti-?pattern|godot\s*3|gdscript\s*1|deprecated|"
    r"legacy|outdated|\bold\b|don'?t|do not|avoid|never|mistake|pitfall|before:|common error",
    re.I)
STRONG_CONTRAST = re.compile(
    r"❌|✗|\bbad\b|\bwrong\b|incorrect|anti-?pattern|godot\s*3|gdscript\s*1|deprecated|"
    r"legacy|outdated|old way|before:", re.I)

# ---------------------------------------------------------------- Godot 3 patterns
# Fixed before any skill was read. Each is Godot 3 API or syntax that Godot 4 renamed or removed
# (docs.godotengine.org/en/stable/tutorials/migrating/upgrading_to_godot_4.html and the
# Godot 4 @GlobalScope / GDScript references).
RENAMED_CLASSES = [
    "KinematicBody2D", "KinematicBody", "Spatial", "SpatialMaterial", "Position2D", "Position3D",
    "AnimatedSprite", "Sprite", "Particles2D", "Particles", "VisibilityNotifier2D",
    "VisibilityNotifier", "VisibilityEnabler2D", "VisibilityEnabler", "YSort", "Navigation2D",
    "Navigation", "ARVRCamera", "ARVROrigin", "ARVRController", "ARVRServer", "VisualServer",
    "Physics2DServer", "TextureProgress", "VideoPlayer", "ViewportContainer", "ShortCut",
    "GIProbe", "StreamTexture", "GradientTexture", "CubeMesh", "ProceduralSky", "PanoramaSky",
    "NavigationMeshInstance", "NavigationPolygonInstance",
]
RENAMED_FUNCS = [
    "rand_range", "deg2rad", "rad2deg", "stepify", "range_lerp", "linear2db", "db2linear",
    "str2var", "var2str", "bytes2var", "var2bytes", "dict2inst", "inst2dict", "funcref", "ColorN",
    "polar2cartesian", "cartesian2polar",
]
G3_PATTERNS = [
    ("yield", r"(?<![\w.])yield\s*\(", "nostr"),
    ("onready-keyword", r"^\s*onready\s+var\b", "nostr"),
    ("export-keyword", r"^\s*export\s*(\(|var\b)", "nostr"),
    ("tool-keyword", r"^\s*tool\s*$", "nostr"),
    ("setget", r"\bsetget\b", "nostr"),
    ("instance-call", r"\.instance\s*\(\s*\)", "nostr"),
    ("renamed-global-function", r"(?<![\w.])(" + "|".join(RENAMED_FUNCS) + r")\s*\(", "nostr"),
    ("pool-array", r"\bPool(String|Vector2|Vector3|Int|Real|Byte|Color)Array\b", "nostr"),
    ("string-connect-with-self", r"\bconnect\s*\(\s*\"[^\"]+\"\s*,\s*self\s*,", "code"),
    ("change-scene", r"\bchange_scene\s*\(", "nostr"),
    ("file-directory-new", r"(?<![\w.])(File|Directory)\.new\s*\(", "nostr"),
    ("rpc-keyword", r"^\s*(remote|master|puppet|remotesync|mastersync|puppetsync)\s+func\b", "nostr"),
    ("is-network-master", r"\bis_network_master\s*\(", "nostr"),
    ("move-and-slide-args", r"\bmove_and_slide\s*\(\s*[^\s)]", "nostr"),
    ("editor-hint-property", r"\bEngine\.editor_hint\b", "nostr"),
    ("os-moved-method", r"\bOS\.(get_ticks_msec|get_ticks_usec|get_unix_time|get_datetime|"
                        r"get_system_time_secs|get_screen_size|window_size|set_window_fullscreen|"
                        r"window_fullscreen|window_position)\b", "nostr"),
    ("tween-node-api", r"\binterpolate_property\s*\(|(?<![\w.])Tween\.new\s*\(", "nostr"),
    ("mouse-button-constant", r"(?<![\w.])BUTTON_(LEFT|RIGHT|MIDDLE|WHEEL_UP|WHEEL_DOWN)\b", "nostr"),
    ("renamed-class", r"(?<![\w$%/.@])(" + "|".join(RENAMED_CLASSES) + r")\b", "nostr"),
]
G3_COMPILED = [(n, re.compile(rx), mode) for n, rx, mode in G3_PATTERNS]
G3_IDENTS = set(RENAMED_CLASSES) | set(RENAMED_FUNCS) | {
    "yield", "setget", "onready", "export", "tool", "PoolStringArray", "PoolVector2Array",
    "PoolVector3Array", "PoolIntArray", "PoolRealArray", "PoolByteArray", "PoolColorArray",
    "change_scene", "is_network_master", "editor_hint", "interpolate_property", "instance",
    "File", "Directory", "BUTTON_LEFT", "BUTTON_RIGHT", "BUTTON_MIDDLE", "BUTTON_WHEEL_UP",
    "BUTTON_WHEEL_DOWN", "remote", "master", "puppet", "remotesync", "mastersync", "puppetsync",
}

# ---------------------------------------------------------------- Godot output classification
EXTERNAL_RES = [re.compile(x) for x in [
    r'Could not find type "', r'Could not find base class "', r'Could not resolve class "',
    r'Could not resolve super class', r'Could not resolve script "',
    r'Could not resolve external class member', r'Preload file "[^"]*" does not exist',
    r'Could not preload resource', r'Could not load the base class',
    r'Could not find (?:script|class) for class name', r"couldn't be fully loaded",
    r'Identifier "[A-Z][a-z0-9]\w*" not declared in the current scope',
]]
ERR_RE = re.compile(r"SCRIPT ERROR:\s*(?:Parse Error:\s*)?(.*)")
AT_RE = re.compile(r"at:\s*.*\((res://[^:)]+):(\d+)\)")
QUOTED_RE = re.compile(r'"([^"]+)"')
ELISION_RE = re.compile(r'"(\.\.\.|…)"|…')

FENCE_OPEN = re.compile(r"^(\s*)(`{3,}|~{3,})\s*([^\s`]*)")
FENCE_CLOSE = re.compile(r"^\s*(`{3,}|~{3,})\s*$")
COMPLETE_RE = re.compile(r"^(extends\b|class_name\b|@tool\b|tool\s*$|@icon\s*\(|@static_unload\b|@abstract\b)")
FM_NAME = re.compile(r"^name:\s*['\"]?([^'\"\n]+?)['\"]?\s*$", re.M)

PROJECT_GODOT = 'config_version=5\n\n[application]\n\nconfig/name="skillcheck"\n'

# Controls (M1). Expected: good -> clean, g3 -> real-error, external -> external-only.
CONTROL_GOOD = textwrap.dedent('''\
    extends CharacterBody2D

    const SPEED := 200.0
    @export var jump_velocity: float = -400.0
    @onready var timer: Timer = $Timer

    signal landed

    func _physics_process(delta: float) -> void:
    \tif not is_on_floor():
    \t\tvelocity += get_gravity() * delta
    \tvar dir := Input.get_axis("ui_left", "ui_right")
    \tvelocity.x = dir * SPEED
    \tmove_and_slide()

    func wait_a_bit() -> void:
    \tawait get_tree().create_timer(0.5).timeout
    \tlanded.emit()
    ''')
CONTROL_G3 = textwrap.dedent('''\
    extends KinematicBody2D

    onready var timer = $Timer
    var velocity = Vector2()

    func _physics_process(delta):
    \tvelocity = move_and_slide(velocity, Vector2.UP)
    \tyield(get_tree().create_timer(rand_range(0.1, 0.5)), "timeout")
    ''')
CONTROL_EXTERNAL = textwrap.dedent('''\
    extends Node

    var stats: PlayerStatsResource

    func _ready() -> void:
    \tstats = PlayerStatsResource.new()
    ''')
CONTROLS = {"control-good": (CONTROL_GOOD, "clean"),
            "control-g3": (CONTROL_G3, "real-error"),
            "control-external": (CONTROL_EXTERNAL, "external-only")}


# ================================================================ text helpers
def split_code(line):
    """Return (code, nostr): the line without its # comment, and the same with string contents blanked."""
    code, nostr = [], []
    q = None
    i, n = 0, len(line)
    while i < n:
        c = line[i]
        if q is None:
            if c == "#":
                break
            if c in "\"'":
                q = c
            code.append(c)
            nostr.append(c)
            i += 1
            continue
        if c == "\\" and i + 1 < n:
            code.append(line[i:i + 2])
            nostr.append("__")
            i += 2
            continue
        if c == q:
            q = None
            code.append(c)
            nostr.append(c)
        else:
            code.append(c)
            nostr.append("_")
        i += 1
    return "".join(code), "".join(nostr)


def comment_of(line):
    return line[len(split_code(line)[0]):]


def extract_blocks(text):
    """Fenced code blocks: list of dicts with lang, start_line (1-based fence line), code, context."""
    lines = text.splitlines()
    blocks = []
    i = 0
    while i < len(lines):
        m = FENCE_OPEN.match(lines[i])
        if not m:
            i += 1
            continue
        fence = m.group(2)
        lang = re.split(r"[:,{]", m.group(3).strip().lower())[0].strip(".")
        start = i
        j = i + 1
        body = []
        while j < len(lines):
            m2 = FENCE_CLOSE.match(lines[j])
            if m2 and m2.group(1)[0] == fence[0] and len(m2.group(1)) >= len(fence):
                break
            body.append(lines[j])
            j += 1
        ctx = [ln for ln in lines[max(0, start - 8):start] if ln.strip()][-3:]
        blocks.append({"lang": lang, "start_line": start + 1,
                       "code": textwrap.dedent("\n".join(body)),
                       "context": "\n".join(ctx), "closed": j < len(lines)})
        i = j + 1
    return blocks


def first_code_line(code):
    for ln in code.splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        return s
    return ""


def is_complete(code):
    return bool(COMPLETE_RE.match(first_code_line(code)))


def is_multi_file(code):
    ext = sum(1 for ln in code.splitlines() if re.match(r"^extends\b", ln))
    cls = sum(1 for ln in code.splitlines() if re.match(r"^class_name\b", ln))
    return ext > 1 or cls > 1


def block_contrast(block):
    """True if the block is marked as a deliberate wrong/old example (rule E1 in the preregistration)."""
    if CONTRAST.search(block.get("context", "")):
        return True
    if STRONG_CONTRAST.search(re.sub(r"[_\-./]", " ", block.get("path_hint", ""))):
        return True
    for ln in block["code"].splitlines():
        if STRONG_CONTRAST.search(comment_of(ln)):
            return True
    return False


def scan_static(code):
    """Godot 3 pattern hits: list of {line, pattern, text}. Lines whose comment has a contrast marker are skipped."""
    hits = []
    for n, line in enumerate(code.splitlines(), 1):
        code_part, nostr = split_code(line)
        if CONTRAST.search(line[len(code_part):]):
            continue
        for name, rx, mode in G3_COMPILED:
            target = nostr if mode == "nostr" else code_part
            if rx.search(target):
                hits.append({"line": n, "pattern": name, "text": line.strip()[:200]})
    return hits


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
        errors.append({"msg": m.group(1).strip(), "line": line_no})
    failed = any(("Failed to load script" in ln) or ("Failed loading resource" in ln) for ln in lines)
    return errors, failed


def classify_error(msg, static_lines=(), line=None):
    """One of: godot3, external, elision, inference, other."""
    quoted = set()
    for q in QUOTED_RE.findall(msg):
        quoted.add(q.rstrip("()"))
    if quoted & G3_IDENTS or (line is not None and line in set(static_lines)):
        return "godot3"
    if any(rx.search(msg) for rx in EXTERNAL_RES):
        return "external"
    if ELISION_RE.search(msg):
        return "elision"
    if re.search(r"infer", msg, re.I):
        return "inference"
    return "other"


def classify_script(returncode, output, timed_out, static_lines=()):
    """Return (status, errors). status: clean | real-error | external-only | elision-only | unclassified-fail | timeout."""
    if timed_out:
        return "timeout", []
    errors, failed = parse_output(output)
    for e in errors:
        e["category"] = classify_error(e["msg"], static_lines, e["line"])
    if not errors:
        if failed or (returncode not in (0, None)):
            return "unclassified-fail", []
        return "clean", []
    cats = {e["category"] for e in errors}
    if cats & {"godot3", "inference", "other"}:
        return "real-error", errors
    if "elision" in cats:
        return "elision-only", errors
    return "external-only", errors


# ================================================================ network + repos
def http_json(url, tries=4):
    last = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 429 or e.code >= 500:
                try:
                    wait = int(e.headers.get("Retry-After") or 30)
                except ValueError:
                    wait = 30
                time.sleep(min(max(wait, 5), 300))
                continue
            raise
        except urllib.error.URLError as e:
            last = e
            time.sleep(15)
    raise RuntimeError(f"failed {url}: {last}")


def search_results(data):
    """The list of result objects in a skills.sh search response, whatever its key is called."""
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    for key in ("skills", "data", "results"):
        v = data.get(key)
        if isinstance(v, list):
            return [r for r in v if isinstance(r, dict)]
    for v in data.values():
        if isinstance(v, list) and v and isinstance(v[0], dict) and "id" in v[0]:
            return v
    return []


def index_repo(root):
    idx_name, idx_dir = {}, {}
    for p in sorted(Path(root).rglob("SKILL.md")):
        if ".git" in p.parts:
            continue
        d = p.parent
        txt = p.read_text(encoding="utf-8", errors="replace")
        fm = ""
        if txt.startswith("---"):
            end = txt.find("\n---", 3)
            if end > 0:
                fm = txt[3:end]
        m = FM_NAME.search(fm)
        if m:
            idx_name.setdefault(m.group(1).strip(), []).append(d)
        idx_dir.setdefault(d.name, []).append(d)
    return idx_name, idx_dir


def pick_dir(cands):
    return sorted(cands, key=lambda d: (len(d.parts), str(d)))[0]


def locate(skill_id, idx_name, idx_dir):
    if skill_id in idx_name:
        return pick_dir(idx_name[skill_id]), "frontmatter-name", len(idx_name[skill_id])
    if skill_id in idx_dir:
        return pick_dir(idx_dir[skill_id]), "folder-name", len(idx_dir[skill_id])
    return None, "not-found", 0


def skill_files(d):
    d = Path(d)
    nested = {p.parent for p in d.rglob("SKILL.md") if p.parent != d and ".git" not in p.parts}
    out = []
    for p in d.rglob("*"):
        if not p.is_file() or ".git" in p.parts:
            continue
        if any(n in p.parents for n in nested):
            continue
        if p.suffix.lower() in (".md", ".gd") and p.stat().st_size <= 2_000_000:
            out.append(p)
    return sorted(out, key=lambda p: p.as_posix())


def git(args, cwd=None, timeout=900):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True,
                          timeout=timeout, env=env, errors="replace")


# ================================================================ stages
def stage_collect(out, work):
    out, work = Path(out), Path(work)
    out.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    found = {}
    raw = {}
    for q in QUERIES:
        data = http_json(SEARCH_URL.format(q=urllib.parse.quote(q)))
        if isinstance(data, dict):
            raw[q] = {"count": data.get("count"), "searchType": data.get("searchType")}
        else:
            raw[q] = {"count": len(data), "searchType": None}
        for r in search_results(data):
            rid = r.get("id")
            if rid and rid not in found:
                found[rid] = {"id": rid, "source": r.get("source", ""), "skillId": r.get("skillId") or r.get("slug") or rid.split("/")[-1],
                              "name": r.get("name", ""), "installs": r.get("installs") or 0, "queries": [q]}
            elif rid:
                found[rid]["queries"].append(q)
        time.sleep(3)
    (out / "population.json").write_text(json.dumps({"retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                                     "queries": raw, "skills": list(found.values())}, indent=1))
    repos = {}
    for s in found.values():
        src = s["source"]
        if src.count("/") != 1 or "." in src.split("/")[0]:
            s["status"] = "not-github"
            continue
        if src not in repos:
            dest = work / src.replace("/", "__")
            try:
                r = git(["clone", "--depth", "1", "--quiet", f"https://github.com/{src}.git", str(dest)])
            except subprocess.TimeoutExpired:
                r = None
            if r is None or r.returncode != 0:
                repos[src] = {"ok": False, "err": "timeout" if r is None else r.stderr[-300:]}
            else:
                sha = git(["rev-parse", "HEAD"], cwd=dest).stdout.strip()
                repos[src] = {"ok": True, "dir": str(dest), "sha": sha, "index": index_repo(dest)}
            time.sleep(2)
        rep = repos[src]
        if not rep["ok"]:
            s["status"] = "clone-failed"
            continue
        d, how, ncand = locate(s["skillId"], *rep["index"])
        if d is None:
            s["status"] = "not-found"
            continue
        files = skill_files(d)
        root = Path(rep["dir"])
        text_all = ""
        for f in files:
            if f.suffix.lower() == ".md":
                text_all += f.read_text(encoding="utf-8", errors="replace")
        mentions = bool(re.search(r"godot|gdscript", s["skillId"] + " " + s["name"], re.I)) or \
            bool(re.search(r"godot|gdscript", text_all, re.I))
        s.update({"status": "located", "how": how, "candidates": ncand, "sha": rep["sha"],
                  "dir": str(d.relative_to(root)).replace("\\", "/"),
                  "files": [str(f.relative_to(root)).replace("\\", "/") for f in files],
                  "mentions_godot": mentions,
                  "names_godot4": bool(re.search(r"godot\s*4", text_all, re.I))})
    meta = {src: {k: v for k, v in r.items() if k != "index"} for src, r in repos.items()}
    (out / "collect.json").write_text(json.dumps({"version": VERSION, "repos": meta,
                                                  "skills": list(found.values())}, indent=1))
    print(f"collect: {len(found)} search results, {len(repos)} repos, "
          f"{sum(1 for s in found.values() if s.get('status') == 'located')} located")


def gather_blocks(collect, work):
    """Per skill, list of block dicts (labeled GDScript fenced blocks and .gd files)."""
    per_skill = {}
    for s in collect["skills"]:
        if s.get("status") != "located" or not s.get("mentions_godot"):
            continue
        rep = collect["repos"][s["source"]]
        root = Path(rep["dir"])
        blocks = []
        for rel in s["files"]:
            p = root / rel
            txt = p.read_text(encoding="utf-8", errors="replace")
            if rel.lower().endswith(".gd"):
                blocks.append({"file": rel, "start_line": 0, "lang": "gd-file", "code": txt,
                               "context": "", "path_hint": rel, "is_file": True})
                continue
            for b in extract_blocks(txt):
                if b["lang"] in GD_LANGS:
                    b.update({"file": rel, "path_hint": "", "is_file": False})
                    blocks.append(b)
        per_skill[s["id"]] = blocks
    return per_skill


def run_godot(godot, proj, rel):
    cmd = [godot, "--headless", "--path", str(proj), "--check-only", "--script", "res://" + rel]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=GODOT_TIMEOUT, errors="replace")
        return p.returncode, (p.stdout or "") + "\n" + (p.stderr or ""), False
    except subprocess.TimeoutExpired:
        return None, "", True


def stage_scan(out, work, godot, proj):
    out, proj = Path(out), Path(proj)
    collect = json.loads((out / "collect.json").read_text())
    per_skill = gather_blocks(collect, work)
    (proj / "s").mkdir(parents=True, exist_ok=True)
    (proj / "project.godot").write_text(PROJECT_GODOT)
    priv = out / "private"
    (priv / "godot-output").mkdir(parents=True, exist_ok=True)
    ver = subprocess.run([godot, "--headless", "--version"], capture_output=True, text=True,
                         timeout=120, errors="replace")
    godot_version = (ver.stdout or "").strip().splitlines()[-1] if (ver.stdout or "").strip() else ""

    # controls (M1)
    controls = {}
    for name, (code, expect) in CONTROLS.items():
        rel = f"s/{name}.gd"
        (proj / rel).write_text(code)
        rc, outp, to = run_godot(godot, proj, rel)
        st, errs = classify_script(rc, outp, to)
        controls[name] = {"expected": expect, "got": st, "returncode": rc, "errors": errs}
        (priv / "godot-output" / f"{name}.txt").write_text(outp)

    hits_out = []
    scripts = {}   # hash -> info
    skill_rows = []
    for sid, blocks in per_skill.items():
        s = next(x for x in collect["skills"] if x["id"] == sid)
        src, sha = s["source"], s["sha"]
        n_lab = n_complete = n_excl = n_hits = 0
        hashes = []
        for b in blocks:
            if not b["is_file"]:
                n_lab += 1
            excluded = block_contrast(b)
            complete = b["is_file"] or is_complete(b["code"])
            if complete and not b["is_file"]:
                n_complete += 1
            if excluded:
                n_excl += 1
                continue
            hs = scan_static(b["code"])
            for h in hs:
                fline = b["start_line"] + h["line"] if not b["is_file"] else h["line"]
                hits_out.append({"skill": sid, "source": src, "file": b["file"], "line": fline,
                                 "pattern": h["pattern"], "text": h["text"],
                                 "url": f"https://github.com/{src}/blob/{sha}/{b['file']}#L{fline}"})
            n_hits += len(hs)
            if complete:
                h = hashlib.sha256(b["code"].encode("utf-8")).hexdigest()[:16]
                info = scripts.setdefault(h, {"hash": h, "code": b["code"], "multi_file": is_multi_file(b["code"]),
                                              "static_lines": sorted({x["line"] for x in hs}),
                                              "locations": [], "skills": []})
                info["locations"].append({"skill": sid, "file": b["file"], "start_line": b["start_line"],
                                          "url": f"https://github.com/{src}/blob/{sha}/{b['file']}"
                                                 + (f"#L{b['start_line']}" if b["start_line"] else "")})
                if sid not in info["skills"]:
                    info["skills"].append(sid)
                hashes.append(h)
        skill_rows.append({"id": sid, "source": src, "installs": s.get("installs", 0),
                           "names_godot4": s.get("names_godot4"), "labeled_blocks": n_lab,
                           "gd_files": sum(1 for b in blocks if b["is_file"]),
                           "complete_blocks": n_complete, "excluded_blocks": n_excl,
                           "static_hits": n_hits, "script_hashes": sorted(set(hashes))})

    eligible = sorted(h for h, i in scripts.items() if not i["multi_file"])
    sampled = eligible[:MAX_SCRIPTS]   # hash order = deterministic pseudo-random order
    for k, h in enumerate(sampled):
        info = scripts[h]
        rel = f"s/{h}.gd"
        (proj / rel).write_text(info["code"])
        rc, outp, to = run_godot(godot, proj, rel)
        st, errs = classify_script(rc, outp, to, info["static_lines"])
        info.update({"status": st, "returncode": rc, "errors": errs})
        (priv / "godot-output" / f"{h}.txt").write_text(outp)
        if k % 100 == 0:
            print(f"scan: {k}/{len(sampled)} scripts checked", flush=True)
    for h, info in scripts.items():
        if info["multi_file"]:
            info["status"] = "multi-file"
        elif "status" not in info:
            info["status"] = "not-sampled"

    (priv / "scripts").mkdir(parents=True, exist_ok=True)
    for h, info in scripts.items():
        (priv / "scripts" / f"{h}.gd").write_text(info["code"])
    with open(out / "static-hits.jsonl", "w", encoding="utf-8") as f:
        for h in hits_out:
            f.write(json.dumps(h) + "\n")
    with open(out / "script-results.jsonl", "w", encoding="utf-8") as f:
        for h in sorted(scripts):
            info = {k: v for k, v in scripts[h].items() if k != "code"}
            f.write(json.dumps(info) + "\n")
    (out / "skills.json").write_text(json.dumps(skill_rows, indent=1))
    (out / "scan-meta.json").write_text(json.dumps({"version": VERSION, "godot_version": godot_version,
                                                    "controls": controls, "eligible_scripts": len(eligible),
                                                    "checked_scripts": len(sampled)}, indent=1))
    print(f"scan: {len(skill_rows)} skills, {len(scripts)} unique complete scripts, "
          f"{len(sampled)} checked, {len(hits_out)} static hits; godot {godot_version}")


def compute_predictions(skills, scripts, meta):
    """Pre-registered numbers. skills: list of skill rows; scripts: dict hash->result; meta: scan-meta."""
    with_code = [s for s in skills if s["labeled_blocks"] + s["gd_files"] > 0]
    n_code = len(with_code)
    static_skills = [s for s in with_code if s["static_hits"] > 0]
    share_static = len(static_skills) / n_code if n_code else None

    graded = {h: i for h, i in scripts.items() if i.get("status") in
              ("clean", "real-error", "external-only", "elision-only", "unclassified-fail")}
    real = {h for h, i in graded.items() if i["status"] in ("real-error", "unclassified-fail")}
    share_real = len(real) / len(graded) if graded else None

    with_scripts = [s for s in with_code if any(h in graded for h in s["script_hashes"])]
    top10 = sorted(with_scripts, key=lambda s: (-(s.get("installs") or 0), s["id"]))[:10]
    top10_bad = [s["id"] for s in top10 if any(h in real for h in s["script_hashes"])]

    def has_cat(i, cat):
        return any(e.get("category") == cat for e in i.get("errors", []))
    n_infer = sum(1 for h in real if has_cat(graded[h], "inference"))
    n_g3 = sum(1 for h in real if has_cat(graded[h], "godot3"))

    n_labeled = sum(s["labeled_blocks"] for s in skills)
    n_complete_blocks = sum(s["complete_blocks"] for s in skills)
    share_complete = n_complete_blocks / n_labeled if n_labeled else None

    controls = meta.get("controls", {})
    m1 = bool(controls) and all(c["expected"] == c["got"] for c in controls.values())
    m2 = str(meta.get("godot_version", "")).startswith(EXPECTED_GODOT)
    parse_ok = m1 and m2

    def verdict(cond, gradable=True):
        if not gradable or cond is None:
            return "not gradable"
        return "held" if cond else "failed"

    status_counts = {}
    for i in scripts.values():
        status_counts[i.get("status", "?")] = status_counts.get(i.get("status", "?"), 0) + 1
    return {
        "M1_controls_ok": m1, "M2_godot_version_ok": m2, "godot_version": meta.get("godot_version"),
        "controls": {k: {"expected": v["expected"], "got": v["got"]} for k, v in controls.items()},
        "skills_in_population": len(skills),
        "script_status_counts": status_counts,
        "P1": {"skills_with_code": n_code, "verdict": verdict(n_code >= 80)},
        "P2_core": {"skills_with_static_hit": len(static_skills), "share": share_static,
                    "verdict": verdict(None if share_static is None else 0.02 <= share_static <= 0.20)},
        "P3_core": {"graded_scripts": len(graded), "real_error_scripts": len(real), "share": share_real,
                    "verdict": verdict(None if share_real is None else 0.10 <= share_real <= 0.50, parse_ok)},
        "P4": {"top10": [s["id"] for s in top10], "top10_with_real_error": top10_bad,
               "verdict": verdict(len(top10_bad) >= 3 if len(top10) == 10 else None, parse_ok)},
        "P5": {"inference_scripts": n_infer, "godot3_scripts": n_g3,
               "verdict": verdict(n_infer > n_g3, parse_ok)},
        "P6": {"labeled_blocks": n_labeled, "complete_blocks": n_complete_blocks, "share": share_complete,
               "verdict": verdict(None if share_complete is None else share_complete < 0.40)},
    }


def stage_report(out):
    out = Path(out)
    skills = json.loads((out / "skills.json").read_text())
    meta = json.loads((out / "scan-meta.json").read_text())
    scripts = {}
    with open(out / "script-results.jsonl", encoding="utf-8") as f:
        for ln in f:
            if ln.strip():
                i = json.loads(ln)
                scripts[i["hash"]] = i
    res = compute_predictions(skills, scripts, meta)
    res["version"] = VERSION
    # descriptive extras (not predictions)
    pat = {}
    with open(out / "static-hits.jsonl", encoding="utf-8") as f:
        for ln in f:
            if ln.strip():
                h = json.loads(ln)
                pat[h["pattern"]] = pat.get(h["pattern"], 0) + 1
    res["static_hits_by_pattern"] = dict(sorted(pat.items(), key=lambda x: -x[1]))
    msgs = {}
    for i in scripts.values():
        for e in i.get("errors", []):
            if e.get("category") != "external":
                key = re.sub(r'"[^"]*"', '"X"', e["msg"])[:120]
                msgs[key] = msgs.get(key, 0) + 1
    res["top_error_messages"] = sorted(msgs.items(), key=lambda x: -x[1])[:25]
    with open(out / "skills.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "source", "installs", "names_godot4", "labeled_blocks", "gd_files",
                    "complete_blocks", "excluded_blocks", "static_hits", "scripts", "real_error_scripts"])
        for s in skills:
            nre = sum(1 for h in s["script_hashes"] if scripts.get(h, {}).get("status") in ("real-error", "unclassified-fail"))
            w.writerow([s["id"], s["source"], s.get("installs", 0), s.get("names_godot4"), s["labeled_blocks"],
                        s["gd_files"], s["complete_blocks"], s["excluded_blocks"], s["static_hits"],
                        len(s["script_hashes"]), nre])
    (out / "summary.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1)[:6000])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("stage", choices=["collect", "scan", "report"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--work", default="/tmp/repos")
    ap.add_argument("--godot", default="godot")
    ap.add_argument("--proj", default="/tmp/proj")
    a = ap.parse_args(argv)
    if a.stage == "collect":
        stage_collect(a.out, a.work)
    elif a.stage == "scan":
        stage_scan(a.out, a.work, a.godot, a.proj)
    else:
        stage_report(a.out)


if __name__ == "__main__":
    main()
