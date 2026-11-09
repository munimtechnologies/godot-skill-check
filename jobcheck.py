#!/usr/bin/env python3
# Sandbox test for gdcheck: real Godot against the fixtures, the Action's own shell step, and two
# public skill collections as a demonstration. By MV2 of Munim, Inc. Made with AI agents (Anthropic Claude).
# SPDX-License-Identifier: Apache-2.0
import json
import os
import re
import subprocess
import sys
import textwrap
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else Path("/out")
DEMOS = [
    ("wshobson-agents", "https://github.com/wshobson/agents.git"),
    ("gamedev-skills", "https://github.com/gamedev-skills/awesome-gamedev-agent-skills.git"),
]


def sh(cmd, **kw):
    kw.setdefault("capture_output", True)
    kw.setdefault("text", True)
    kw.setdefault("errors", "replace")
    return subprocess.run(cmd, **kw)


def install_godot():
    env = dict(os.environ, RUNNER_TEMP="/tmp/rt", GITHUB_ENV="/tmp/ghenv", GODOT_VERSION="4.7.2")
    Path("/tmp/rt").mkdir(parents=True, exist_ok=True)
    p = sh(["bash", str(HERE / "install_godot.sh")], env=env)
    print(p.stdout[-2000:], p.stderr[-2000:])
    godot = None
    if Path("/tmp/ghenv").exists():
        for ln in Path("/tmp/ghenv").read_text().splitlines():
            if ln.startswith("GDCHECK_GODOT="):
                godot = ln.split("=", 1)[1].strip()
    return p.returncode, godot


def run_gdcheck(godot, args, fmt="json"):
    p = sh([sys.executable, str(HERE / "gdcheck.py"), "--godot", godot, "--format", fmt] + args, cwd=str(HERE))
    return p


def key_results(report):
    return {f"{r['file']}#{r['index']}": r for r in report["results"]}


def compare(run, report, code):
    bad = []
    if code != run["exit"]:
        bad.append(f"{run['name']}: exit {code}, expected {run['exit']}")
    got = key_results(report)
    for k, exp in run["blocks"].items():
        r = got.get(k)
        if r is None:
            bad.append(f"{run['name']}: {k} missing")
            continue
        if r["status"] != exp["status"]:
            bad.append(f"{run['name']}: {k} status {r['status']}, expected {exp['status']} "
                       f"(errors: {[e['msg'] for e in r['errors']][:3]})")
        if "severity" in exp and r["severity"] != exp["severity"]:
            bad.append(f"{run['name']}: {k} severity {r['severity']}, expected {exp['severity']}")
        if "first_error_line" in exp:
            fl = r["errors"][0]["line"] if r["errors"] else None
            if fl != exp["first_error_line"]:
                bad.append(f"{run['name']}: {k} first error line {fl}, expected {exp['first_error_line']}")
        if "first_category" in exp:
            fc = r["errors"][0]["category"] if r["errors"] else None
            if fc != exp["first_category"]:
                bad.append(f"{run['name']}: {k} first category {fc}, expected {exp['first_category']}")
    return bad


def action_step_script():
    """The shell of the Action's 'Check GDScript blocks' step, taken from action.yml as written."""
    lines = (HERE / "action.yml").read_text().splitlines()
    i = next(k for k, ln in enumerate(lines) if "name: Check GDScript blocks" in ln)
    j = next(k for k in range(i, len(lines)) if lines[k].strip() == "run: |")
    body = []
    for ln in lines[j + 1:]:
        if ln.strip() and not ln.startswith(" " * 8):
            break
        body.append(ln)
    return textwrap.dedent("\n".join(body)) + "\n"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    rc, godot = install_godot()
    report["install_exit"] = rc
    report["godot"] = godot
    if rc != 0 or not godot:
        report["passed"] = False
        (OUT / "job-report.json").write_text(json.dumps(report, indent=1))
        print("install failed")
        return 1

    expected = json.loads((HERE / "fixtures" / "expected.json").read_text())
    mismatches = []
    for run in expected["runs"]:
        p = run_gdcheck(godot, run["args"])
        (OUT / f"fixtures-{run['name']}.json").write_text(p.stdout)
        try:
            rep = json.loads(p.stdout)
        except json.JSONDecodeError:
            mismatches.append(f"{run['name']}: no JSON (exit {p.returncode}): {p.stderr[-500:]}")
            continue
        mismatches += compare(run, rep, p.returncode)
        report.setdefault("godot_version", rep.get("godot_version"))
    p = run_gdcheck(godot, expected["runs"][0]["args"], fmt="github")
    (OUT / "fixtures-main-github.txt").write_text(p.stdout + p.stderr)
    p = run_gdcheck(godot, expected["runs"][0]["args"], fmt="text")
    (OUT / "fixtures-main-text.txt").write_text(p.stdout + p.stderr)
    report["fixture_mismatches"] = mismatches

    # The agent skill's own examples must pass gdcheck (and the README has no GDScript blocks to fail).
    p = run_gdcheck(godot, ["skills", "README.md"])
    (OUT / "self-check.json").write_text(p.stdout)
    try:
        rep = json.loads(p.stdout)
        self_ok = (p.returncode == 0 and rep["counts"].get("ok", 0) >= 2
                   and set(rep["counts"]) == {"ok"})
        report["self_check"] = {"exit": p.returncode, "counts": rep["counts"], "ok": self_ok,
                                "problems": [[r["file"], r["line"], [e["msg"] for e in r["errors"]]]
                                             for r in rep["results"] if r["status"] != "ok"]}
    except (json.JSONDecodeError, KeyError):
        self_ok = False
        report["self_check"] = {"exit": p.returncode, "stderr": p.stderr[-500:], "ok": False}

    # The Action's own check step, run with bash as GitHub would (bash -e -o pipefail).
    script = action_step_script()
    Path("/tmp/step2.sh").write_text(script)
    env = dict(os.environ, GITHUB_ACTION_PATH=str(HERE), GITHUB_STEP_SUMMARY=str(OUT / "step-summary.md"),
               GDCHECK_GODOT=godot, GDCHECK_PATHS="fixtures/good.md fixtures/bad.md",
               GDCHECK_FRAGMENTS="false", GDCHECK_GD_FILES="false", GDCHECK_FAIL_EXTERNAL="false")
    p = sh(["bash", "--noprofile", "--norc", "-eo", "pipefail", "/tmp/step2.sh"], env=env, cwd=str(HERE))
    (OUT / "action-step.txt").write_text(script + "\n----\n" + p.stdout + p.stderr)
    action_ok = (p.returncode == 1 and "::error file=fixtures/bad.md,line=14," in p.stdout
                 and (OUT / "step-summary.md").exists())
    env["GDCHECK_PATHS"] = "fixtures/good.md"
    p2 = sh(["bash", "--noprofile", "--norc", "-eo", "pipefail", "/tmp/step2.sh"], env=env, cwd=str(HERE))
    action_ok = action_ok and p2.returncode == 0
    report["action_step"] = {"bad_exit": p.returncode, "good_exit": p2.returncode, "ok": action_ok}

    # Demonstration on public skill collections (exploratory, not a test).
    demos = {}
    for name, url in DEMOS:
        dest = Path("/tmp/demo") / name
        c = sh(["git", "clone", "--depth", "1", "--quiet", url, str(dest)], timeout=900)
        if c.returncode != 0:
            demos[name] = {"clone_error": c.stderr[-300:]}
            continue
        sha = sh(["git", "rev-parse", "HEAD"], cwd=str(dest)).stdout.strip()
        dirs = sorted({str(pth.parent) for pth in dest.rglob("SKILL.md")
                       if re.search(r"godot|gdscript", pth.parent.name, re.I) and ".git" not in pth.parts})
        if not dirs:
            demos[name] = {"sha": sha, "skill_dirs": 0}
            continue
        t0 = time.time()
        p = sh([sys.executable, str(HERE / "gdcheck.py"), "--godot", godot, "--format", "text",
                "--json-out", str(OUT / f"demo-{name}.json")] + dirs, cwd=str(dest))
        (OUT / f"demo-{name}.txt").write_text(p.stdout + p.stderr)
        try:
            rep = json.loads((OUT / f"demo-{name}.json").read_text())
            counts = rep["counts"]
        except (OSError, json.JSONDecodeError):
            counts = None
        demos[name] = {"sha": sha, "skill_dirs": len(dirs), "exit": p.returncode, "counts": counts,
                       "seconds": round(time.time() - t0, 1),
                       "dirs": [str(Path(d).relative_to(dest)).replace("\\", "/") for d in dirs]}
    report["demos"] = demos
    report["passed"] = (not mismatches) and action_ok and self_ok
    report["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    (OUT / "job-report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1)[:8000])
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
