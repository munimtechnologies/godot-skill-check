#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# By MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents (Anthropic Claude).
"""fragverify 0.1.0: test, with Godot itself, the hypotheses from the hand check of the
godot-docs fragment sample (results/godot-docs/handcheck-fragments.json).

Every case below has its expected outcome written BEFORE the first run (2026-11-10). The job
reports each case as held / not held and never changes an expectation after the run.

Groups
  A  end-of-file lambdas: are the "Expected end of file" errors on two blocks caused by the
     file having no trailing newline (a gdcheck artifact), not by the docs code?
  B  proposed fixes for fragments labelled "real": the code as shown must fail, the fixed
     code must pass (in the smallest context that supplies the names the page assumes).
  C  probe: facts from Godot's ClassDB used in the labels (property and argument names).

Code quoted from the Godot docs (godot-docs 4.7 @ 9adca4c1c72917bfe1b7be3108abed5ce26696a6)
stays under the docs' licence, CC BY 3.0 (Juan Linietsky, Ariel Manzur and the Godot community).
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

VERSION = "0.1.0"


def S(text):
    """Strip the one newline that follows the opening triple quote."""
    return text[1:] if text.startswith("\n") else text


NOTIF = S('''
extends Node
# Allows for recurring operations that don't trigger script logic
# every frame (or even every fixed frame).
func _ready():
    var timer = Timer.new()
    timer.autostart = true
    timer.wait_time = 0.5
    add_child(timer)
    timer.timeout.connect(func():
        print("This block runs every 0.5 seconds")
    )
''')

CALLABLE = S('''
extends Node
func _init():
    var my_lambda = func (message):
        print(message)

    # Prints "Hello everyone!"
    my_lambda.call("Hello everyone!")

    # Prints "Attack!", when the button_pressed signal is emitted.
    button_pressed.connect(func(): print("Attack!"))
''')

SYN_MULTI = S('''
extends Node
func _ready():
    var t = Timer.new()
    t.timeout.connect(func():
        print(1)
    )
''')

SYN_SINGLE = S('''
extends Node
func _ready():
    var t = Timer.new()
    t.timeout.connect(func(): print(1))
''')

SYN_SINGLE_NOT_LAST = S('''
extends Node
func _ready():
    var t = Timer.new()
    t.timeout.connect(func(): print(1))
    print(2)
''')

SYN_PLAIN = S('''
extends Node
func _ready():
    print(1)
''')

ANIM98_HEAD = S('''
extends Node
@onready var animation_tree: AnimationTree = $AnimationTree
func demo():
    # Play child animation connected to "shot" port.
    animation_tree.set("parameters/OneShot/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)
    # Alternative syntax (same result).
    animation_tree["parameters/OneShot/request"] = AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE

    # Abort child animation connected to "shot" port.
    animation_tree.set("parameters/OneShot/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_ABORT)
    # Alternative syntax (same result).
    animation_tree["parameters/OneShot/request"] = AnimationNodeOneShot.ONE_SHOT_REQUEST_ABORT

    # Get current state (read-only).
''')
ANIM98_TAIL = S('''
    # Alternative syntax (same result).
    animation_tree["parameters/OneShot/active"]
''')
ANIM98_ASIS = ANIM98_HEAD + '    animation_tree.get("parameters/OneShot/active"))\n' + ANIM98_TAIL
ANIM98_FIXED = ANIM98_HEAD + '    animation_tree.get("parameters/OneShot/active")\n' + ANIM98_TAIL

ANIM173_HEAD = S('''
extends Node
@onready var animation_tree: AnimationTree = $AnimationTree
func demo():
    # Play child animation connected to "state_2" port.
    animation_tree.set("parameters/Transition/transition_request", "state_2")
    # Alternative syntax (same result).
    animation_tree["parameters/Transition/transition_request"] = "state_2"

    # Get current state name (read-only).
    animation_tree.get("parameters/Transition/current_state")
    # Alternative syntax (same result).
    animation_tree["parameters/Transition/current_state"]

    # Get current state index (read-only).
''')
ANIM173_TAIL = S('''
    # Alternative syntax (same result).
    animation_tree["parameters/Transition/current_index"]
''')
ANIM173_ASIS = ANIM173_HEAD + '    animation_tree.get("parameters/Transition/current_index"))\n' + ANIM173_TAIL
ANIM173_FIXED = ANIM173_HEAD + '    animation_tree.get("parameters/Transition/current_index")\n' + ANIM173_TAIL

MP_HEAD = S('''
extends Node
func demo():
    # This goes after `multiplayer.multiplayer_peer = peer`.
''')
MP_BODY = S('''
        # We have to set this on the client for the `peer_authenticating`
        # signal to emit.
        pass
    multiplayer.peer_authenticating.connect(func(peer_id: int):
            var auth_data = {
                "username": "username",
                "password": "password",
            }
            multiplayer.send_auth(1, JSON.stringify(auth_data).to_utf8_buffer())

            # Tell the MultiplayerAPI that the authentication was successful.
            multiplayer.complete_auth(peer_id)
''')
MP_ASIS = MP_HEAD + "    multiplayer.auth_callback = func:\n" + MP_BODY
MP_FIX_PARENS_ONLY = MP_HEAD + "    multiplayer.auth_callback = func():\n" + MP_BODY
MP_FIXED = MP_FIX_PARENS_ONLY + "    )\n"

SERVERS_BODY = S('''
# PhysicsServer2D expects references to be kept around.
var body
var shape


func _body_moved(state, index):
    # Created your own canvas item; use it here.
    # `ci_rid` from the sprite example above needs to be moved to a
    # member variable (instead of within `_ready()`) so it can be referenced here.
    RenderingServer.canvas_item_set_transform(ci_rid, state.transform)


func _ready():
    # Create the body.
    body = PhysicsServer2D.body_create()
    PhysicsServer2D.body_set_mode(body, PhysicsServer2D.BODY_MODE_RIGID)
    # Add a shape.
    shape = PhysicsServer2D.rectangle_shape_create()
    # Set rectangle extents.
    PhysicsServer2D.shape_set_data(shape, Vector2(10, 10))
    # Make sure to keep the shape reference!
    PhysicsServer2D.body_add_shape(body, shape)
    # Set space, so it collides in the same space as current scene.
    PhysicsServer2D.body_set_space(body, get_world_2d().space)
    # Move initial position.
    PhysicsServer2D.body_set_state(body, PhysicsServer2D.BODY_STATE_TRANSFORM, Transform2D(0, Vector2(10, 20)))
    # Add the transform callback, when body moves
    # The last parameter is optional, can be used as index
    # if you have many bodies and a single callback.
''')
SERVERS_ASIS = "extends Node2D\n" + SERVERS_BODY + \
    '    PhysicsServer2D.body_set_force_integration_callback(body, self, "_body_moved", 0)\n'
SERVERS_FIXED = "extends Node2D\nvar ci_rid: RID\n" + SERVERS_BODY + \
    "    PhysicsServer2D.body_set_force_integration_callback(body, _body_moved, 0)\n"


def case(cid, group, about, code, eof_newline, expect, must=(), allow=(), forbid=()):
    code = code.rstrip("\n") + ("\n" if eof_newline else "")
    return {"id": cid, "group": group, "about": about, "code": code, "eof_newline": eof_newline,
            "expect": expect, "must": list(must), "allow": list(allow), "forbid": list(forbid)}


EOF = "Expected end of file"
CASES = [
    # ---- A: end-of-file lambdas (hypothesis H1: the error goes away with a trailing newline)
    case("A1", "A", "godot_notifications.rst:76 exactly as checked (no trailing newline)", NOTIF, False,
         "error", must=[EOF]),
    case("A2", "A", "godot_notifications.rst:76 plus a trailing newline", NOTIF, True, "ok"),
    case("A3", "A", "classes/class_callable.rst:59 exactly as checked (no trailing newline)", CALLABLE, False,
         "error", must=[EOF]),
    case("A4", "A", "classes/class_callable.rst:59 plus a trailing newline: only the context name is left",
         CALLABLE, True, "error", must=["button_pressed"], allow=["button_pressed"], forbid=[EOF]),
    case("A5", "A", "synthetic: multi-line lambda in parentheses last, no trailing newline", SYN_MULTI, False,
         "error", must=[EOF]),
    case("A6", "A", "synthetic: same with a trailing newline", SYN_MULTI, True, "ok"),
    case("A7", "A", "synthetic: one-line lambda last, no trailing newline", SYN_SINGLE, False,
         "error", must=[EOF]),
    case("A8", "A", "synthetic: one-line lambda not last, no trailing newline", SYN_SINGLE_NOT_LAST, False, "ok"),
    case("A9", "A", "synthetic control: no lambda, no trailing newline", SYN_PLAIN, False, "ok"),
    # ---- B: proposed fixes for fragments labelled real
    case("B1a", "B", "animation_tree.rst:98 as shown (stray ')')", ANIM98_ASIS, True,
         "error", must=['Closing ")"']),
    case("B1b", "B", "animation_tree.rst:98 with the stray ')' removed", ANIM98_FIXED, True, "ok"),
    case("B2a", "B", "animation_tree.rst:173 as shown (stray ')')", ANIM173_ASIS, True,
         "error", must=['Closing ")"']),
    case("B2b", "B", "animation_tree.rst:173 with the stray ')' removed", ANIM173_FIXED, True, "ok"),
    case("B3a", "B", "high_level_multiplayer.rst:708 as shown ('func:' without parentheses)", MP_ASIS, True,
         "error", must=['Expected opening "("']),
    case("B3b", "B", "high_level_multiplayer.rst:708 with 'func():' only (connect( still unclosed)",
         MP_FIX_PARENS_ONLY, True, "error"),
    case("B3c", "B", "high_level_multiplayer.rst:708 with 'func():' and the closing ')' added", MP_FIXED, True, "ok"),
    case("B4a", "B", "gdscript_exports.rst:146 as shown (untyped @export_multiline)",
         "extends Node\n@export_multiline var text\n", True, "error", must=['"@export_multiline" annotation requires']),
    case("B4b", "B", "gdscript_exports.rst:146 typed as String",
         "extends Node\n@export_multiline var text: String\n", True, "ok"),
    case("B5a", "B", "gdscript_exports.rst:155 as shown (@export_custom with one argument)",
         "extends Node\n@export_custom(PROPERTY_HINT_INPUT_NAME) var my_input\n", True,
         "error", must=["requires at least 2 arguments"]),
    case("B5b", "B", "gdscript_exports.rst:155 with an empty hint string added",
         'extends Node\n@export_custom(PROPERTY_HINT_INPUT_NAME, "") var my_input\n', True, "ok"),
    case("B6a", "B", "using_servers.rst:251 as shown, on Node2D (Godot 3 style callback call)", SERVERS_ASIS, True,
         "error", must=['Too many arguments for "body_set_force_integration_callback()"'],
         allow=["ci_rid", "body_set_force_integration_callback"]),
    case("B6b", "B", "using_servers.rst:251 with ci_rid as a member (as the page says) and a Callable",
         SERVERS_FIXED, True, "ok"),
]

PROBE = S('''
extends SceneTree
func _init():
    var names = []
    for p in ClassDB.class_get_property_list("SceneMultiplayer", true):
        names.append(p["name"])
    print("PROBE auth_timeout=", "auth_timeout" in names)
    print("PROBE auth_timout=", "auth_timout" in names)
    print("PROBE auth_callback=", "auth_callback" in names)
    for m in ClassDB.class_get_method_list("PhysicsServer2D", true):
        if m["name"] == "body_set_force_integration_callback":
            print("PROBE pfi_args=", m["args"].size())
    quit()
''')
PROBE_EXPECT = {"auth_timeout": "true", "auth_timout": "false", "auth_callback": "true", "pfi_args": "3"}


def evaluate(c, status, msgs):
    """Return (held, reason) for one case given the checker status and the error messages."""
    if c["expect"] == "ok":
        return (status == "ok" and not msgs), ("" if status == "ok" and not msgs else "expected no errors")
    if not msgs:
        return False, "expected errors, got none (status %s)" % status
    for m in c["must"]:
        if not any(m in x for x in msgs):
            return False, "missing an error containing %r" % m
    for f in c["forbid"]:
        if any(f in x for x in msgs):
            return False, "has a forbidden error containing %r" % f
    if c["allow"]:
        bad = [x for x in msgs if not any(a in x for a in c["allow"])]
        if bad:
            return False, "unexpected error: %s" % bad[0]
    return True, ""


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
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    sys.path.insert(0, a.gsc)
    import gdcheck  # noqa: E402

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    runner = gdcheck.GodotRunner(a.godot)
    rows = []
    try:
        godot_version = runner.version()
        for c in CASES:
            rc, text, to = runner(c["code"])
            errs, failed = gdcheck.parse_output(text)
            gdcheck.classify_errors(errs, c["code"])
            status = gdcheck.status_of(errs, rc, failed, to)
            msgs = [e["msg"] for e in errs]
            held, reason = evaluate(c, status, msgs)
            rows.append({"id": c["id"], "group": c["group"], "about": c["about"], "eof_newline": c["eof_newline"],
                         "expect": c["expect"], "must": c["must"], "status": status,
                         "errors": [{"msg": e["msg"], "line": e["script_line"]} for e in errs],
                         "held": held, "why_not": reason})
            print("%-4s %-5s %-6s %s" % (c["id"], "held" if held else "NO", status, c["about"]))
        (runner.proj / "probe.gd").write_text(PROBE, encoding="utf-8", newline="\n")
        p = subprocess.run([a.godot, "--headless", "--path", str(runner.proj), "--script", "res://probe.gd"],
                           capture_output=True, text=True, timeout=120, errors="replace")
        probe = parse_probe((p.stdout or "") + "\n" + (p.stderr or ""))
        probe_rows = [{"key": k, "expect": v, "got": probe.get(k), "held": probe.get(k) == v}
                      for k, v in PROBE_EXPECT.items()]
        for r in probe_rows:
            print("C    %-5s %s expect=%s got=%s" % ("held" if r["held"] else "NO", r["key"], r["expect"], r["got"]))
    finally:
        runner.close()
    summary = {"fragverify": VERSION, "godot_version": godot_version,
               "cases": len(rows), "held": sum(r["held"] for r in rows),
               "by_group": {g: [sum(r["held"] for r in rows if r["group"] == g),
                                sum(1 for r in rows if r["group"] == g)] for g in ("A", "B")},
               "probe_held": [sum(r["held"] for r in probe_rows), len(probe_rows)],
               "not_held": [r["id"] for r in rows if not r["held"]] +
                           ["C:" + r["key"] for r in probe_rows if not r["held"]]}
    (out / "fragverify.json").write_text(json.dumps({"summary": summary, "cases": rows, "probe": probe_rows},
                                                    indent=1, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
