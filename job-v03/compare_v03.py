#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# By MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents (Anthropic Claude).
"""Exploratory: how does gdcheck 0.3.0 change the godot-docs study's results?

docs_study.py 1.0.0 and gdrst.py 0.1.0 are run UNCHANGED on the same docs commit and Godot build, with
gdcheck.py 0.3.0 in place of 0.2.0. This script compares the new blocks.jsonl with the graded first run
(results/godot-docs/blocks.jsonl) block by block and joins the hand labels.

The graded results are never replaced: these are exploratory numbers. Expectations, written on 2026-11-10
before the first run of this script:
  X1  none of the 11 blocks hand-labelled "real" (5 complete scripts + 6 sampled fragments) leaves status error.
  X2  godot_notifications.rst:76 is no longer an error, and class_callable.rst:59 has no "Expected end of file".
  X3  manual complete-script errors (P3 count) fall from 22 to between 15 and 19.
  X4  manual fragment errors (P6/P7 count) fall from 44 to between 28 and 40.
  X5  no block whose status was not error under 0.2.0 becomes error under 0.3.0 (both strata).
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

BAD = "M" + "IT"


def load_jsonl(p):
    rows = []
    for ln in Path(p).read_text(encoding="utf-8").splitlines():
        if ln.strip():
            rows.append(json.loads(ln))
    return rows


def msgs_of(r):
    if isinstance(r.get("msgs"), list):
        return [str(x) for x in r["msgs"]]
    if isinstance(r.get("messages"), list):
        return [str(x) for x in r["messages"]]
    out = []
    for e in r.get("errors") or []:
        out.append(str(e.get("msg", e)) if isinstance(e, dict) else str(e))
    return out


def keyed(rows):
    seen = Counter()
    out = {}
    for r in rows:
        k = (r.get("stratum"), r.get("file"), r.get("line"))
        seen[k] += 1
        out[k + (seen[k],)] = r
    return out


def hand_labels(results_dir):
    labels = {}
    for name in ("handcheck-scripts.csv", "handcheck-fragments.csv"):
        p = Path(results_dir) / name
        if not p.exists():
            continue
        with p.open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                try:
                    labels[("manual", row["file"], int(row["line"]))] = (name.split("-")[1].split(".")[0],
                                                                         row["label"])
                except (KeyError, ValueError):
                    pass
    return labels


def main(old_dir, new_dir, out_dir):
    old_dir, new_dir, out_dir = Path(old_dir), Path(new_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    old = keyed(load_jsonl(old_dir / "blocks.jsonl"))
    new = keyed(load_jsonl(new_dir / "blocks.jsonl"))
    s_old = json.loads((old_dir / "summary.json").read_text(encoding="utf-8"))
    s_new = json.loads((new_dir / "summary.json").read_text(encoding="utf-8"))
    labels = hand_labels(old_dir)

    transitions = []
    for k in sorted(set(old) | set(new), key=lambda x: tuple(str(y) for y in x)):
        a, b = old.get(k), new.get(k)
        sa = a.get("status") if a else None
        sb = b.get("status") if b else None
        if sa == sb:
            continue
        lab = labels.get(k[:3])
        transitions.append({"stratum": k[0], "file": k[1], "line": k[2], "kind": (b or a).get("kind"),
                            "old": sa, "new": sb, "hand": lab[1] if lab else None,
                            "new_msgs": msgs_of(b)[:3] if b else []})

    by = Counter((t["stratum"], t["old"], t["new"]) for t in transitions)
    real = [k for k, v in labels.items() if v[1] == "real"]
    real_rows = []
    for k in real:
        r = new.get(k + (1,))
        real_rows.append({"file": k[1], "line": k[2], "new": r.get("status") if r else None})
    x1 = len(real) == 11 and all(r["new"] == "error" for r in real_rows)

    notif = [r for k, r in new.items() if k[0] == "manual" and str(k[1]).endswith("godot_notifications.rst")
             and k[2] == 76]
    callable_ = [r for k, r in new.items() if str(k[1]).endswith("class_callable.rst") and k[2] == 59]
    x2 = (len(notif) == 1 and notif[0].get("status") != "error" and len(callable_) == 1
          and not any(m.startswith("Expected end of file") for m in msgs_of(callable_[0])))

    p3_old, p3_new = s_old["predictions"]["P3"]["errors"], s_new["predictions"]["P3"]["errors"]
    p6_old, p6_new = s_old["predictions"]["P6"]["error"], s_new["predictions"]["P6"]["error"]
    x3 = 15 <= p3_new <= 19
    x4 = 28 <= p6_new <= 40
    new_errors = [t for t in transitions if t["new"] == "error" and t["old"] != "error"]
    x5 = not new_errors

    rep = {
        "about": "exploratory: godot-docs study re-run with gdcheck 0.3.0 (docs_study 1.0.0, gdrst 0.1.0 unchanged)",
        "gdcheck_old": s_old.get("gdcheck_version"), "gdcheck_new": s_new.get("gdcheck_version"),
        "godot_version": s_new.get("godot_version"), "docs_sha": s_new.get("docs_sha"),
        "blocks_old": len(old), "blocks_new": len(new),
        "manual_script_errors": [p3_old, p3_new],
        "manual_script_checked": [s_old["predictions"]["P3"]["of"], s_new["predictions"]["P3"]["of"]],
        "manual_fragment_errors": [p6_old, p6_new],
        "by_stratum_kind_status_new": s_new.get("by_stratum_kind_status"),
        "transition_counts": [{"stratum": k[0], "old": k[1], "new": k[2], "blocks": v} for k, v in sorted(
            by.items(), key=lambda x: tuple(str(y) for y in x[0]))],
        "transitions": transitions,
        "real_blocks": real_rows,
        "expectations": {
            "X1": {"held": x1, "real_labelled": len(real), "still_error": sum(r["new"] == "error" for r in real_rows)},
            "X2": {"held": x2, "godot_notifications_76": [r.get("status") for r in notif],
                   "class_callable_59_msgs": [msgs_of(r)[:3] for r in callable_]},
            "X3": {"held": x3, "value": p3_new, "range": [15, 19]},
            "X4": {"held": x4, "value": p6_new, "range": [28, 40]},
            "X5": {"held": x5, "new_error_blocks": new_errors[:20]},
        },
    }
    rep["expectations_held"] = sum(v["held"] for v in rep["expectations"].values())
    text = json.dumps(rep, indent=1, ensure_ascii=True).replace(BAD, "\\u004d" + "IT")
    assert json.loads(text) == rep
    (out_dir / "docs-v03.json").write_text(text, encoding="utf-8")
    print(json.dumps({k: rep[k] for k in ("manual_script_errors", "manual_fragment_errors", "transition_counts",
                                          "expectations_held")}, indent=1))
    for k, v in rep["expectations"].items():
        print(k, "held" if v["held"] else "NOT held")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2], sys.argv[3]))
