#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# By MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents (Anthropic Claude).
"""Exploratory: why did classref-verify-v1's R04 check D (R04's correction applied to the block gdcheck
checked) list 'Could not find base class "Sprite"', an error that belongs to R03's block?

Suspicion (written before the first run): gdcheck 0.3.0's GodotRunner keeps every checked script in one
project folder (s/<hash>.gd) and parse_output() reads every 'SCRIPT ERROR' line without looking at the
res:// path on its 'at:' line, so an error Godot reports for an OLDER script in the folder is counted
for the current one.

S1  fresh runner, only R04-D                               -> expected: no Sprite message
S2  fresh runner, the R03 then R04 checks in verify order    -> expected: Sprite message in R04-D again
S3  as S2, but every error's res:// path is compared with the file being checked
Raw Godot output is saved for every check so the cause can be read, not guessed."""
import json
import re
import sys
from pathlib import Path

AT = re.compile(r"at:\s*.*\((res://[^:)]+):(\d+)\)")
ERR = re.compile(r"SCRIPT ERROR:\s*(?:Parse Error:\s*|Compile Error:\s*)?(.*)")


def errors_with_paths(text):
    lines = text.splitlines()
    out = []
    for k, ln in enumerate(lines):
        m = ERR.search(ln)
        if not m:
            continue
        path = None
        for l2 in lines[k + 1:k + 3]:
            a = AT.search(l2)
            if a:
                path = a.group(1)
                break
        out.append({"msg": m.group(1).strip(), "path": path})
    return out


def main():
    gsc, godot, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(gsc))
    sys.path.insert(0, str(gsc / "results" / "class-reference" / "job"))
    import gdcheck
    import hashlib
    import verify_classref as vc

    records = {}
    for ln in (gsc / vc.ERRORS).read_text(encoding="utf-8").splitlines():
        if ln.strip():
            r = json.loads(ln)
            if r.get("stratum") == "classes":
                records[(r["file"], r["line"])] = r
    cases = {c["id"]: c for c in vc.CASES}

    def four(cid):
        c = cases[cid]
        rec = records[(c["file"], c["line"])]
        block, checked = rec["block_code"], rec["checked_code"]
        return [(cid + "-A", checked), (cid + "-C", vc.standalone(c, block)),
                (cid + "-B", vc.standalone(c, vc.apply_fixes(block, c["fix"])[0])),
                (cid + "-D", vc.apply_fixes(checked, c["fix"])[0])]

    def run(seq, label):
        runner = gdcheck.GodotRunner(godot)
        rows = []
        try:
            for name, code in seq:
                code2 = code if code.endswith("\n") else code + "\n"
                own = "res://s/" + hashlib.sha256(code2.encode("utf-8")).hexdigest()[:16] + ".gd"
                rc, text, to = runner(code)
                errs, failed = gdcheck.parse_output(text)
                withp = errors_with_paths(text)
                rows.append({"check": name, "own_path": own, "rc": rc, "gdcheck_msgs": [e["msg"] for e in errs],
                             "errors_with_paths": withp,
                             "foreign": [e for e in withp if e["path"] and e["path"] != own],
                             "files_in_project": sorted(p.name for p in (runner.proj / "s").iterdir())})
                (out / ("%s-%s.txt" % (label, name))).write_text(text, encoding="utf-8")
        finally:
            runner.close()
        return rows

    res = {"S1": run([x for x in four("R04") if x[0] == "R04-D"], "S1"),
           "S2": run(four("R03") + four("R04"), "S2")}
    for k, rows in res.items():
        for r in rows:
            print("%s %s gdcheck=%s foreign=%s" % (k, r["check"], r["gdcheck_msgs"], r["foreign"]))
    sprite = lambda r: any('"Sprite"' in m for m in r["gdcheck_msgs"])
    d1 = [r for r in res["S1"] if r["check"] == "R04-D"][0]
    d2 = [r for r in res["S2"] if r["check"] == "R04-D"][0]
    summary = {"S1_sprite_in_R04D": sprite(d1), "S2_sprite_in_R04D": sprite(d2),
               "S2_foreign_errors_total": sum(len(r["foreign"]) for r in res["S2"])}
    print(json.dumps(summary, indent=1))
    (out / "r04-anomaly.json").write_text(json.dumps({"summary": summary, "runs": res}, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
