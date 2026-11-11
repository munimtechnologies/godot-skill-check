#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# By MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents (Anthropic Claude).
"""classref-c5 0.1.0: upstream status of the verified class-reference blocks (C5 of
PREREGISTRATION-class-reference.md). Read-only: fetches public files and runs public searches;
never files, comments or proposes anything anywhere. Method: EXPECTATIONS.md, fixed before the
first run."""
import argparse
import difflib
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

VERSION = "0.1.0"
UA = "munimtechnologies-classref-c5/0.1 (mv2@munimtech.com)"
ERRORS = "results/godot-docs/errors.jsonl"
GLANCED = {"R01", "R06", "R07", "R10", "R18"}

XML = {
    "classes/class_@gdscript.rst": "modules/gdscript/doc_classes/@GDScript.xml",
    "classes/class_@globalscope.rst": "doc/classes/@GlobalScope.xml",
    "classes/class_displayserver.rst": "doc/classes/DisplayServer.xml",
    "classes/class_dtlsserver.rst": "doc/classes/DTLSServer.xml",
    "classes/class_linkbutton.rst": "doc/classes/LinkButton.xml",
    "classes/class_node.rst": "doc/classes/Node.xml",
    "classes/class_popupmenu.rst": "doc/classes/PopupMenu.xml",
    "classes/class_renderingdevice.rst": "doc/classes/RenderingDevice.xml",
    "classes/class_spinbox.rst": "doc/classes/SpinBox.xml",
}

QUERIES = {
    "R01": '"character_biography"',
    "R02": '"export_range" "power_percent"',
    "R03": '"lerp_angle" "extends Sprite"',
    "R04": '"wrap(10.5, 5, 10)"',
    "R06": '"updatePersistableUriPermission"',
    "R07": '"connect_to_peer(udp, false)"',
    "R10": '"SomeFolder" LinkButton',
    "R13": '"get_child(-1).name"',
    "R14": '"add_multistate_item" lambda',
    "R15": '"STORAGE_BUFFER_USAGE_SHADER_DEVICE_ADDRESS"',
    "R16": '"RenderingDevice.new()"',
    "R18": '"LineEdit.HORIZONTAL_ALIGNMENT_RIGHT"',
}

BLOCK_RE = re.compile(r"\[(codeblock|gdscript)(?:\s[^\]]*)?\](.*?)\[/\1\]", re.S)


def norm_lines(text):
    """Normalised lines: trailing space stripped, leading tabs -> 4 spaces, common indent removed,
    blank lines at start and end dropped. Blank lines inside become ''."""
    out = []
    for ln in text.replace("\r\n", "\n").split("\n"):
        ln = ln.rstrip()
        m = re.match(r"[ \t]*", ln)
        lead = m.group(0).replace("\t", "    ")
        out.append(lead + ln[m.end():] if ln else "")
    while out and not out[0]:
        out.pop(0)
    while out and not out[-1]:
        out.pop()
    ind = [len(ln) - len(ln.lstrip(" ")) for ln in out if ln]
    cut = min(ind) if ind else 0
    return [ln[cut:] if ln else "" for ln in out]


def stripped(lines):
    return [ln.strip() for ln in lines if ln.strip()]


def contains(hay, needle):
    """True if needle is a contiguous run of lines in hay (both lists of str)."""
    n = len(needle)
    if n == 0:
        return False
    return any(hay[i:i + n] == needle for i in range(len(hay) - n + 1))


def xml_blocks(xml_text):
    """Every codeblock / gdscript section, unescaped, as raw text."""
    out = []
    for m in BLOCK_RE.finditer(xml_text):
        t = html.unescape(m.group(2)).replace("[lb]", "[").replace("[rb]", "]")
        out.append(t)
    return out


def compare(block_code, blocks, fixed_code=None):
    """Return the comparison of one docs block against the XML blocks of one ref."""
    want = norm_lines(block_code)
    want_s = stripped(want)
    res = {"same": False, "same_ignoring_ws": False, "fixed_present": False,
           "best_ratio": 0.0, "best_index": -1, "n_blocks": len(blocks)}
    fixed = norm_lines(fixed_code) if fixed_code else None
    for i, b in enumerate(blocks):
        have = norm_lines(b)
        if contains(have, want):
            res["same"] = True
        if contains(stripped(have), want_s):
            res["same_ignoring_ws"] = True
        if fixed and contains(stripped(have), stripped(fixed)):
            res["fixed_present"] = True
        r = difflib.SequenceMatcher(None, "\n".join(want), "\n".join(have)).ratio()
        if r > res["best_ratio"]:
            res["best_ratio"], res["best_index"] = round(r, 4), i
    return res


def get(url, tries=4):
    last = None
    for k in range(tries):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/vnd.github+json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (403, 429) or e.code >= 500:
                time.sleep(65 * (k + 1))
                continue
            raise
        except urllib.error.URLError as e:
            last = e
            time.sleep(10)
    raise RuntimeError("giving up on %s: %s" % (url, last))


def resolve(ref):
    data = json.loads(get("https://api.github.com/repos/godotengine/godot/commits/" + ref))
    return data["sha"], data["commit"]["committer"]["date"]


def fetch_xml(sha, path):
    return get("https://raw.githubusercontent.com/godotengine/godot/%s/%s"
               % (sha, urllib.parse.quote(path, safe="/"))).decode("utf-8")


def search(q):
    full = q + " repo:godotengine/godot repo:godotengine/godot-docs"
    data = json.loads(get("https://api.github.com/search/issues?per_page=30&q=" + urllib.parse.quote(full)))
    items = [{"repo": it["repository_url"].rsplit("/", 1)[-1], "number": it["number"],
              "title": it["title"], "state": it["state"], "is_pr": "pull_request" in it,
              "created_at": it["created_at"], "url": it["html_url"]} for it in data.get("items", [])]
    return {"query": full, "total_count": data.get("total_count"), "items": items}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--gsc", required=True, help="clone of munimtechnologies/godot-skill-check")
    ap.add_argument("--verified", required=True,
                    help="comma-separated ids verified by classref-verify-v1 (classref-verify.json)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--delay", type=float, default=7.0)
    ap.add_argument("--no-search", action="store_true")
    a = ap.parse_args(argv)
    sys.path.insert(0, str(Path(a.gsc) / "results" / "class-reference" / "job"))
    import verify_classref as vc  # the published 0.1.0 script, for the corrections

    out = Path(a.out)
    (out / "c5-blocks").mkdir(parents=True, exist_ok=True)
    verified = [x.strip() for x in a.verified.split(",") if x.strip()]
    records = {}
    for ln in (Path(a.gsc) / ERRORS).read_text(encoding="utf-8").splitlines():
        if ln.strip():
            r = json.loads(ln)
            if r.get("stratum") == "classes":
                records[(r["file"], r["line"])] = r
    refs = {}
    for name in ("master", "4.7"):
        sha, date = resolve(name)
        refs[name] = {"sha": sha, "date": date}
        print("REF %s %s %s" % (name, sha, date))
    cache = {}
    rows = []
    for c in vc.CASES:
        if c["id"] not in verified:
            continue
        block = records[(c["file"], c["line"])]["block_code"]
        fixed, ferr = vc.apply_fixes(block, c["fix"])
        row = {"id": c["id"], "file": c["file"], "line": c["line"], "xml": XML[c["file"]],
               "glanced": c["id"] in GLANCED}
        for name, ref in refs.items():
            key = (ref["sha"], row["xml"])
            if key not in cache:
                cache[key] = xml_blocks(fetch_xml(ref["sha"], row["xml"]))
            blocks = cache[key]
            res = compare(block, blocks, None if ferr else fixed)
            if res["best_index"] >= 0:
                best = blocks[res["best_index"]]
                (out / "c5-blocks" / ("%s-%s.txt" % (c["id"], name.replace(".", "_")))).write_text(
                    "# %s %s @ %s, block %d, ratio %s\n# repr of the raw block follows the text\n%s\n\n%r\n"
                    % (c["id"], row["xml"], ref["sha"], res["best_index"], res["best_ratio"], best, best),
                    encoding="utf-8")
            row[name] = res
        rows.append(row)
        print("%s master same=%s ws=%s fixed=%s ratio=%s | control same=%s  %s:%d" % (
            c["id"], row["master"]["same"], row["master"]["same_ignoring_ws"], row["master"]["fixed_present"],
            row["master"]["best_ratio"], row["4.7"]["same"], c["file"], c["line"]))
    searches = {}
    if not a.no_search:
        for r in rows:
            time.sleep(a.delay)
            try:
                searches[r["id"]] = search(QUERIES[r["id"]])
            except Exception as e:  # reported, never fatal
                searches[r["id"]] = {"query": QUERIES[r["id"]], "error": str(e)}
            s = searches[r["id"]]
            print("S %s total=%s %s" % (r["id"], s.get("total_count"), s.get("error", "")))
            for it in s.get("items", [])[:10]:
                print("   %s#%s %s %s %s" % (it["repo"], it["number"], "PR" if it["is_pr"] else "issue",
                                            it["state"], it["title"][:100]))
    same = [r["id"] for r in rows if r["master"]["same"]]
    same15 = [i for i in same if i not in GLANCED]
    n15 = sum(1 for r in rows if not r["glanced"])
    summary = {"classref_c5": VERSION, "refs": refs, "verified": len(rows),
               "same_in_master": len(same), "same_in_master_ids": same,
               "same_in_master_15": [len(same15), n15],
               "control_same": sum(r["4.7"]["same"] for r in rows),
               "control_failed": [r["id"] for r in rows if not r["4.7"]["same"]],
               "c5_threshold_20": (len(rows) + 1) // 2, "c5_threshold_15": (n15 + 1) // 2}
    (out / "c5.json").write_text(json.dumps({"summary": summary, "cases": rows, "searches": searches},
                                            indent=1, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
