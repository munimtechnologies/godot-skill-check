#!/usr/bin/env python3
# The godot-docs sample check: do the GDScript examples in the official Godot 4.7 docs pass
# Godot 4.7.2's own --check-only? Runs the rules in PREREGISTRATION-godot-docs.md exactly.
# Part of godot-skill-check. By MV2 of Munim, Inc. (mv2@munimtech.com).
# Made with AI agents (Anthropic Claude) working in his name.
# SPDX-License-Identifier: Apache-2.0
import argparse
import hashlib
import json
import random
import re
import subprocess
import sys
import time
from pathlib import Path

import gdcheck as g
import gdrst as r

STUDY_VERSION = "1.0.0"
CHECKED_OUT = {"skipped", "fragment"}          # statuses that mean Godot never saw the block
FRAGMENT_KINDS = {"decl-fragment", "stmt-fragment"}
SAMPLE_SEED = 20261109
SAMPLE_SIZE = 40
PREDICTIONS = {
    "P1": "The manual holds between 1,500 and 4,500 GDScript blocks.",
    "P2": "Complete scripts are between 5% and 25% of the manual's GDScript blocks.",
    "P3": "Between 2% and 12% of the manual's checked complete scripts get status error.",
    "P4": "At least half of the manual's complete-script errors are confirmed real by hand (graded later).",
    "P5": "At most 1% of the manual's checked blocks have a Godot 3 API error.",
    "P6": "Among the manual's checked fragments, context-only blocks outnumber error blocks.",
    "P7": "Between 3% and 20% of the manual's checked fragments get status error.",
}


def stratum(rel):
    return "classes" if rel.startswith("classes/") else "manual"


def rst_files(root):
    out = []
    for p in sorted(root.rglob("*.rst")):
        rel = p.relative_to(root)
        if any(part.startswith(("_", ".")) for part in rel.parts[:-1]):
            continue
        out.append(p)
    return out


def pct(a, b):
    return round(100.0 * a / b, 2) if b else None


def norm_msg(msg):
    return re.sub(r'"[^"]*"', '"…"', msg)[:160]


def root_categories(entry):
    return sorted({e.get("follows", e["category"]) if e["category"] == "cascade" else e["category"]
                   for e in entry.get("errors", [])})


def grade(entries):
    man = [e for e in entries if e["stratum"] == "manual"]
    checked = [e for e in man if e["status"] not in CHECKED_OUT]
    complete = [e for e in man if e["complete"]]
    checked_complete = [e for e in checked if e["kind"] == "script"]
    err_complete = [e for e in checked_complete if e["status"] == "error"]
    frags = [e for e in checked if e["kind"] in FRAGMENT_KINDS]
    frag_err = [e for e in frags if e["status"] == "error"]
    frag_ctx = [e for e in frags if e["status"] == "context"]
    g3 = [e for e in checked if "godot3" in root_categories(e)]
    n = len(man)
    res = {}
    res["P1"] = {"value": n, "held": 1500 <= n <= 4500}
    v = pct(len(complete), n)
    res["P2"] = {"value_pct": v, "complete": len(complete), "of": n, "held": v is not None and 5 <= v <= 25}
    v = pct(len(err_complete), len(checked_complete))
    res["P3"] = {"value_pct": v, "errors": len(err_complete), "of": len(checked_complete),
                 "held": v is not None and 2 <= v <= 12}
    res["P4"] = {"held": None, "note": "graded by hand in a later run; not gradable if P3 found no errors",
                 "to_check": len(err_complete)}
    v = pct(len(g3), len(checked))
    res["P5"] = {"value_pct": v, "godot3_blocks": len(g3), "of": len(checked), "held": v is not None and v <= 1}
    res["P6"] = {"context_only": len(frag_ctx), "error": len(frag_err), "held": len(frag_ctx) > len(frag_err)}
    v = pct(len(frag_err), len(frags))
    res["P7"] = {"value_pct": v, "errors": len(frag_err), "of": len(frags), "held": v is not None and 3 <= v <= 20}
    for k in res:
        res[k]["prediction"] = PREDICTIONS[k]
    return res


def table(entries, key):
    out = {}
    for e in entries:
        k = key(e)
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items()))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", required=True)
    ap.add_argument("--godot", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pinned-sha", default="")
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--limit-files", type=int, default=0, help="for a dry run only")
    a = ap.parse_args(argv)
    root = Path(a.docs)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(root), capture_output=True,
                         text=True).stdout.strip()
    files = rst_files(root)
    if a.limit_files:
        files = files[:a.limit_files]

    entries, langs = [], {}
    for f in files:
        rel = f.relative_to(root).as_posix()
        text = f.read_text(encoding="utf-8", errors="replace")
        for b in r.extract_rst_blocks(text):
            k = (stratum(rel), b["lang"] or "?")
            langs[k] = langs.get(k, 0) + 1
        for e in r.plan_rst_text(text, rel):
            e["stratum"] = stratum(rel)
            entries.append(e)
    print(f"{len(files)} .rst files, {len(entries)} GDScript blocks", flush=True)

    runner = g.GodotRunner(a.godot, a.timeout)
    cache = {}
    try:
        gv = runner.version()
        for k, e in enumerate(entries):
            r.check_entry(e, runner, cache)
            if k % 250 == 0:
                print(f"  {k}/{len(entries)} checked, {len(cache)} Godot runs, {round(time.time() - t0)} s",
                      flush=True)
    finally:
        runner.close()

    rows = []
    for e in entries:
        code = e.get("block_code", "")
        row = {k: v for k, v in e.items() if k not in ("code", "block_code")}
        row["code_sha"] = hashlib.sha256(code.encode("utf-8")).hexdigest()[:16]
        row["roots"] = root_categories(e)
        rows.append(row)
    with open(out / "blocks.jsonl", "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    bad = [e for e in entries if e["status"] in ("error", "timeout", "fail-unknown")]
    with open(out / "errors.jsonl", "w", encoding="utf-8") as fh:
        for e in bad:
            fh.write(json.dumps({
                "stratum": e["stratum"], "file": e["file"], "line": e["line"], "kind": e["kind"],
                "source": e["source"], "status": e["status"], "base": e.get("base"),
                "docs_url": r.docs_url(e["file"]),
                "source_url": f"https://github.com/godotengine/godot-docs/blob/{sha}/{e['file']}#L{e['line']}",
                "errors": e["errors"], "block_code": e["block_code"], "checked_code": e.get("code")},
                ensure_ascii=False) + "\n")

    man_frag_err = sorted([e for e in bad if e["stratum"] == "manual" and e["kind"] in FRAGMENT_KINDS
                           and e["status"] == "error"], key=lambda e: (e["file"], e["line"]))
    sample = random.Random(SAMPLE_SEED).sample(man_frag_err, min(SAMPLE_SIZE, len(man_frag_err)))
    (out / "handcheck-fragments.json").write_text(json.dumps(
        [{"file": e["file"], "line": e["line"]} for e in sample], indent=1))
    man_script_err = [e for e in bad if e["stratum"] == "manual" and e["kind"] == "script"
                      and e["status"] == "error"]
    (out / "handcheck-scripts.json").write_text(json.dumps(
        [{"file": e["file"], "line": e["line"]} for e in man_script_err], indent=1))

    msgs = {}
    for e in entries:
        if e["status"] != "error":
            continue
        for x in e["errors"]:
            if x["category"] in ("godot3", "inference", "other"):
                key = (e["stratum"], x["category"], norm_msg(x["msg"]))
                msgs[key] = msgs.get(key, 0) + 1
    top = sorted(msgs.items(), key=lambda kv: -kv[1])[:60]

    summary = {
        "study": "godot-docs sample check", "study_version": STUDY_VERSION, "gdrst_version": r.VERSION,
        "gdcheck_version": g.VERSION, "godot_version": gv, "docs_sha": sha, "pinned_sha": a.pinned_sha,
        "pinned_sha_used": (sha == a.pinned_sha) if a.pinned_sha else None,
        "rst_files": len(files), "gdscript_blocks": len(entries), "godot_runs": len(cache),
        "seconds": round(time.time() - t0, 1),
        "code_blocks_by_language": {f"{s}/{l}": n for (s, l), n in sorted(langs.items())},
        "by_stratum_kind_status": table(entries, lambda e: f"{e['stratum']}/{e['kind']}/{e['status']}"),
        "by_stratum_source": table(entries, lambda e: f"{e['stratum']}/{e['source']}"),
        "skip_reasons": table([e for e in entries if e["status"] in CHECKED_OUT],
                              lambda e: f"{e['stratum']}/{e['status']}/{e.get('reason', '')}"),
        "root_categories_of_error_blocks": table(
            [e for e in entries if e["status"] == "error"],
            lambda e: f"{e['stratum']}/{e['kind']}/{'+'.join(root_categories(e))}"),
        "base_retries": sum(1 for e in entries if e.get("base_retry")),
        "top_error_messages": [{"stratum": s, "category": c, "msg": m, "blocks": n} for (s, c, m), n in top],
        "predictions": grade(entries),
        "handcheck": {"scripts": len(man_script_err), "fragment_sample": len(sample),
                      "fragment_errors": len(man_frag_err), "seed": SAMPLE_SEED},
        "limited_dry_run": bool(a.limit_files),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    print(json.dumps({k: summary[k] for k in ("godot_version", "docs_sha", "rst_files", "gdscript_blocks",
                                              "godot_runs", "seconds", "predictions")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
