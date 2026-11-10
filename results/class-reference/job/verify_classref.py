#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# By MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents (Anthropic Claude).
"""classref-verify 0.1.0: the verification step of PREREGISTRATION-class-reference.md.

For every class-reference block labelled `real` in results/class-reference/handcheck.csv (labels
written 2026-11-10, before this script first ran), four checks with Godot 4.7.2:

  A  the block exactly as gdcheck 0.3 checks it (`checked_code` in errors.jsonl, trailing newline
     added as gdcheck 0.3 does) still gives the key error recorded for it;
  C  the block inside the smallest script that supplies the names its page assumes (header below),
     unchanged, gives the key error;
  B  the same script with the correction written below gives no error at all;
  D  the correction applied to the checked code removes the key error (other messages are listed).

A `real` label stands only if A and B hold: these are (a) and (b) of the pre-registration. C and D
are reported alongside. Group X: extra cases with expectations written before the first run,
reported but never used for a label. Group P: facts from Godot's ClassDB that the labels rely on.
Every expectation is fixed before the first run and never changed after it.

Code quoted from the Godot class reference (godot-docs 4.7 @ 9adca4c1c72917bfe1b7be3108abed5ce26696a6)
stays under the docs' licence, CC BY 3.0 (Juan Linietsky, Ariel Manzur and the Godot community).
"""
import argparse
import csv
import io
import json
import re
import subprocess
import sys
from pathlib import Path

VERSION = "0.1.0"
LABELS = "results/class-reference/handcheck.csv"
ERRORS = "results/godot-docs/errors.jsonl"
FUNC = "func demo():\n"

CASES = [
    {"id": "R01", "file": "classes/class_@gdscript.rst", "line": 642,
     "key": '"@export_multiline" annotation requires',
     "header": "extends Node\n", "indent": 0,
     "fix": [("var character_biography", "var character_biography: String")]},
    {"id": "R02", "file": "classes/class_@gdscript.rst", "line": 706,
     "key": 'Variable "number" has the same name',
     "header": "extends Node\n", "indent": 0,
     "fix": [("@export_range(0, 20) var number\n", "@export_range(0, 20) var number: int\n"),
             ("@export_range(-10, 20) var number\n", "@export_range(-10, 20) var number2: int\n"),
             ("var number: float", "var number3: float"),
             ("var power_percent", "var power_percent: int"),
             ("var health_delta", "var health_delta: int"),
             ("var angle_radians", "var angle_radians: float"),
             ("var angle_degrees", "var angle_degrees: float"),
             ("var target_offset", "var target_offset: float")]},
    {"id": "R03", "file": "classes/class_@globalscope.rst", "line": 6415,
     "key": 'Could not find base class "Sprite"',
     "header": "", "indent": 0,
     "fix": [("extends Sprite\n", "extends Sprite2D\n")]},
    {"id": "R04", "file": "classes/class_@globalscope.rst", "line": 7737,
     "key": 'Variable "a" has the same name',
     "header": "extends Node\n", "indent": 0,
     "fix": [("var a = wrap(7, 5, 10)", "var b = wrap(7, 5, 10)"),
             ("var a = wrap(10.5, 5, 10)", "var c = wrap(10.5, 5, 10)")]},
    {"id": "R06", "file": "classes/class_displayserver.rst", "line": 4499,
     "key": 'Expected end of statement after expression, found "Identifier"',
     "header": "extends Node\n" + FUNC, "indent": 4,
     "fix": [("val uri", "var uri"), ("val persist", "var persist")]},
    {"id": "R07", "file": "classes/class_dtlsserver.rst", "line": 115,
     "key": 'argument 2 should be "String" but is "bool"',
     "header": "", "indent": 0,
     "fix": [("dtls.connect_to_peer(udp, false)",
              'dtls.connect_to_peer(udp, "127.0.0.1", TLSOptions.client_unsafe())')]},
    {"id": "R10", "file": "classes/class_linkbutton.rst", "line": 294,
     "key": "Invalid escape in string",
     "header": "extends LinkButton\n" + FUNC, "indent": 4,
     "fix": [(r'"C:\SomeFolder"', r'"C:\\SomeFolder"'),
             (r'"C:\SomeImage.png"', r'"C:\\SomeImage.png"')]},
    {"id": "R13", "file": "classes/class_node.rst", "line": 2033,
     "key": 'Variable "b" has the same name',
     "header": "extends Node\n", "indent": 0,
     "fix": [("var c = get_child(-1)", "var d = get_child(-1)"),
             ("var b = get_child(2)", "var c = get_child(2)")]},
    {"id": "R14", "file": "classes/class_popupmenu.rst", "line": 913,
     "key": "Unindent doesn't match the previous indentation level",
     "header": "extends PopupMenu\n", "indent": 0,
     "fix": [("re", r"(?m)^[ \t]+\)[ \t]*$", "    )")]},
    {"id": "R15", "file": "classes/class_renderingdevice.rst", "line": 3263,
     "key": 'Cannot find member "STORAGE_BUFFER_USAGE_SHADER_DEVICE_ADDRESS"',
     "header": ("extends Node\nvar rd: RenderingDevice\nvar storage_buffer: RID\nvar storage_buffer_address: int\n"
                "func demo(bytes: PackedByteArray):\n"), "indent": 4,
     "fix": [("RenderingDevice.STORAGE_BUFFER_USAGE_SHADER_DEVICE_ADDRESS",
              "0, RenderingDevice.BUFFER_CREATION_DEVICE_ADDRESS_BIT")]},
    {"id": "R16", "file": "classes/class_renderingdevice.rst", "line": 6854,
     "key": "cannot be constructed as it is abstract",
     "header": ("extends Node\nvar vertex_buffer: RID\nvar index_buffer: RID\nvar geometries: Array = []\n"
                "var blas: RID\nvar tlas: RID\nvar hit_sbt: RID\nvar raytracing_pipeline: RID\n"
                "var uniform_set: RID\n" + FUNC), "indent": 4,
     "fix": [("RenderingDevice.new()", "RenderingServer.create_local_rendering_device()")]},
    {"id": "R18", "file": "classes/class_spinbox.rst", "line": 36,
     "key": 'Cannot find member "HORIZONTAL_ALIGNMENT_RIGHT" in base "LineEdit"',
     "header": "extends Node\n" + FUNC, "indent": 4,
     "fix": [("spin_box.horizontal_alignment = LineEdit.HORIZONTAL_ALIGNMENT_RIGHT",
              "spin_box.alignment = HORIZONTAL_ALIGNMENT_RIGHT")]},
]

# Extra cases: the standalone script of `base` with a different change. Reported only.
EXTRA = [
    {"id": "X1", "base": "R02", "about": "names made distinct but no types added: untyped @export_range fails too",
     "fix": [("@export_range(-10, 20) var number\n", "@export_range(-10, 20) var number2\n"),
             ("var number: float", "var number3: float")],
     "expect": "error", "must": ['"@export_range"'], "forbid": ["has the same name"]},
    {"id": "X2", "base": "R18", "about": "only LineEdit. dropped: --check-only does not see the wrong property "
                                         "name horizontal_alignment on an inferred type",
     "fix": [("LineEdit.HORIZONTAL_ALIGNMENT_RIGHT", "HORIZONTAL_ALIGNMENT_RIGHT")],
     "expect": "ok", "must": [], "forbid": []},
    {"id": "X3", "base": "R07", "about": "hostname only, default TLS options",
     "fix": [("dtls.connect_to_peer(udp, false)", 'dtls.connect_to_peer(udp, "127.0.0.1")')],
     "expect": "ok", "must": [], "forbid": []},
]

PROBE = '''extends SceneTree
func _init():
    print("PROBE sprite_exists=", ClassDB.class_exists("Sprite"))
    print("PROBE sprite2d_exists=", ClassDB.class_exists("Sprite2D"))
    print("PROBE rd_can_instantiate=", ClassDB.can_instantiate("RenderingDevice"))
    print("PROBE rd_storage_shader_device_address=", ClassDB.class_has_integer_constant("RenderingDevice", "STORAGE_BUFFER_USAGE_SHADER_DEVICE_ADDRESS"))
    print("PROBE rd_buffer_creation_device_address_bit=", ClassDB.class_has_integer_constant("RenderingDevice", "BUFFER_CREATION_DEVICE_ADDRESS_BIT"))
    print("PROBE lineedit_horizontal_alignment_right=", ClassDB.class_has_integer_constant("LineEdit", "HORIZONTAL_ALIGNMENT_RIGHT"))
    var names = []
    for p in ClassDB.class_get_property_list("SpinBox", false):
        names.append(p["name"])
    print("PROBE spinbox_horizontal_alignment=", "horizontal_alignment" in names)
    print("PROBE spinbox_alignment=", "alignment" in names)
    for m in ClassDB.class_get_method_list("PacketPeerDTLS", true):
        if m["name"] == "connect_to_peer":
            print("PROBE dtls_arg2_type=", m["args"][1]["type"])
    quit()
'''
PROBE_EXPECT = {"sprite_exists": "false", "sprite2d_exists": "true", "rd_can_instantiate": "false",
                "rd_storage_shader_device_address": "false", "rd_buffer_creation_device_address_bit": "true",
                "lineedit_horizontal_alignment_right": "false", "spinbox_horizontal_alignment": "false",
                "spinbox_alignment": "true", "dtls_arg2_type": "4"}


def apply_fixes(text, fixes):
    """Apply each change in order. Each must match exactly once. Returns (text, None) or (None, reason)."""
    for f in fixes:
        if f[0] == "re":
            _, pat, repl = f
            n = len(re.findall(pat, text))
            if n != 1:
                return None, "pattern %r matched %d times" % (pat, n)
            text = re.sub(pat, repl, text, count=1)
        else:
            old, new = f
            n = text.count(old)
            if n != 1:
                return None, "%r found %d times" % (old, n)
            text = text.replace(old, new)
    return text, None


def standalone(case, block):
    """The block inside the smallest script that supplies the names its page assumes."""
    pad = " " * case["indent"]
    body = "\n".join((pad + ln) if ln.strip() else "" for ln in block.rstrip("\n").split("\n"))
    return case["header"] + body + "\n"


def evaluate(expect, status, msgs, must=(), forbid=()):
    """(held, reason) for one check."""
    if expect == "ok":
        good = status == "ok" and not msgs
        return good, ("" if good else "expected no errors")
    if not msgs:
        return False, "expected errors, got none (status %s)" % status
    for m in must:
        if not any(m in x for x in msgs):
            return False, "missing an error containing %r" % m
    for f in forbid:
        if any(f in x for x in msgs):
            return False, "has a forbidden error containing %r" % f
    return True, ""


def read_labels(text):
    rows = list(csv.DictReader(io.StringIO(text)))
    return {(r["file"], int(r["line"])): r["label"] for r in rows}


def norm(text):
    return "\n".join(ln.rstrip() for ln in text.replace("\r\n", "\n").strip().split("\n"))


def parse_probe(text):
    out = {}
    for ln in text.splitlines():
        if ln.startswith("PROBE ") and "=" in ln:
            k, v = ln[6:].split("=", 1)
            out[k.strip()] = v.strip().lower()
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--gsc", required=True, help="clone of munimtechnologies/godot-skill-check")
    ap.add_argument("--godot", required=True)
    ap.add_argument("--labels", required=True, help="local copy of handcheck.csv shipped with this job")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    gsc = Path(a.gsc)
    public = gsc / LABELS
    if not public.exists():
        print("GATE: %s is not in the repository yet; stopping" % LABELS)
        return 3
    if norm(public.read_text(encoding="utf-8")) != norm(Path(a.labels).read_text(encoding="utf-8")):
        print("GATE: the public labels differ from the copy shipped with this job; stopping")
        return 5
    labels = read_labels(public.read_text(encoding="utf-8"))
    real = {k for k, v in labels.items() if v == "real"}
    mine = {(c["file"], c["line"]) for c in CASES}
    if real != mine:
        print("GATE: real labels and cases differ: %s" % sorted(real ^ mine))
        return 4
    records = {}
    for ln in (gsc / ERRORS).read_text(encoding="utf-8").splitlines():
        if ln.strip():
            r = json.loads(ln)
            if r.get("stratum") == "classes":
                records[(r["file"], r["line"])] = r
    sys.path.insert(0, str(gsc))
    import gdcheck  # noqa: E402

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    runner = gdcheck.GodotRunner(a.godot)

    def check(code):
        rc, text, to = runner(code)
        errs, failed = gdcheck.parse_output(text)
        gdcheck.classify_errors(errs, code)
        return gdcheck.status_of(errs, rc, failed, to), [e["msg"] for e in errs]

    rows, extra_rows, probe_rows = [], [], []
    try:
        godot_version = runner.version()
        by_id = {}
        for c in CASES:
            rec = records[(c["file"], c["line"])]
            block, checked = rec["block_code"], rec["checked_code"]
            by_id[c["id"]] = (c, block)
            recorded = [e["msg"] for e in rec.get("errors", [])]
            row = {"id": c["id"], "file": c["file"], "line": c["line"], "key": c["key"],
                   "key_recorded": any(c["key"] in m for m in recorded)}
            st, msgs = check(checked)
            held, why = evaluate("error", st, msgs, must=[c["key"]])
            row["A"] = {"status": st, "msgs": msgs, "held": held and row["key_recorded"],
                        "why_not": why or ("" if row["key_recorded"] else "key not in recorded errors")}
            st, msgs = check(standalone(c, block))
            held, why = evaluate("error", st, msgs, must=[c["key"]])
            row["C"] = {"status": st, "msgs": msgs, "held": held, "why_not": why}
            fixed, ferr = apply_fixes(block, c["fix"])
            if ferr:
                row["B"] = {"status": "not-applied", "msgs": [], "held": False, "why_not": ferr}
            else:
                code = standalone(c, fixed)
                st, msgs = check(code)
                held, why = evaluate("ok", st, msgs)
                row["B"] = {"status": st, "msgs": msgs, "held": held, "why_not": why, "code": code}
            fixed_checked, ferr = apply_fixes(checked, c["fix"])
            if ferr:
                row["D"] = {"status": "not-applied", "msgs": [], "held": False, "why_not": ferr}
            else:
                st, msgs = check(fixed_checked)
                gone = not any(c["key"] in m for m in msgs)
                row["D"] = {"status": st, "msgs": msgs, "held": gone, "why_not": "" if gone else "key error remains"}
            row["verified"] = row["A"]["held"] and row["B"]["held"]
            rows.append(row)
            print("%s A=%s C=%s B=%s D=%s verified=%s  %s:%d" % (
                c["id"], row["A"]["held"], row["C"]["held"], row["B"]["held"], row["D"]["held"],
                row["verified"], c["file"], c["line"]))
        for x in EXTRA:
            c, block = by_id[x["base"]]
            fixed, ferr = apply_fixes(block, x["fix"])
            if ferr:
                r = {"status": "not-applied", "msgs": [], "held": False, "why_not": ferr}
            else:
                st, msgs = check(standalone(c, fixed))
                held, why = evaluate(x["expect"], st, msgs, must=x["must"], forbid=x["forbid"])
                r = {"status": st, "msgs": msgs, "held": held, "why_not": why}
            r.update({"id": x["id"], "base": x["base"], "about": x["about"], "expect": x["expect"]})
            extra_rows.append(r)
            print("%s held=%s status=%s  %s" % (x["id"], r["held"], r["status"], x["about"]))
        (runner.proj / "probe.gd").write_text(PROBE, encoding="utf-8", newline="\n")
        p = subprocess.run([a.godot, "--headless", "--path", str(runner.proj), "--script", "res://probe.gd"],
                           capture_output=True, text=True, timeout=120, errors="replace")
        probe = parse_probe((p.stdout or "") + "\n" + (p.stderr or ""))
        for k, v in PROBE_EXPECT.items():
            probe_rows.append({"key": k, "expect": v, "got": probe.get(k), "held": probe.get(k) == v})
            print("P %s expect=%s got=%s" % (k, v, probe.get(k)))
    finally:
        runner.close()
    summary = {"classref_verify": VERSION, "godot_version": godot_version,
               "real_labels": len(rows), "verified": sum(r["verified"] for r in rows),
               "unverified": [r["id"] for r in rows if not r["verified"]],
               "A_held": sum(r["A"]["held"] for r in rows), "B_held": sum(r["B"]["held"] for r in rows),
               "C_held": sum(r["C"]["held"] for r in rows), "D_held": sum(r["D"]["held"] for r in rows),
               "extra_held": [sum(r["held"] for r in extra_rows), len(extra_rows)],
               "probe_held": [sum(r["held"] for r in probe_rows), len(probe_rows)]}
    (out / "classref-verify.json").write_text(
        json.dumps({"summary": summary, "cases": rows, "extra": extra_rows, "probe": probe_rows},
                   indent=1, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
