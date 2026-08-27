"""One hash over everything the compiled compas_wood.rhp is derived from.

The .rhp can only be built locally (RhinoCode needs a licensed Rhino), so the
built artifact is committed in plugin_rhino/plugin/dist/ and CI packages it
into the Yak release. This hash is the freshness contract between the two:
tools/refresh_plugin_build.ps1 stamps dist/source_hash.txt after every local
build, and the publish workflow recomputes it - a mismatch fails the publish
with instructions instead of silently shipping a stale plugin.

Inputs covered: the rhproj itself plus everything gen_rhproj.py folds into it
(command scripts, shared scripts, SVG and PNG icons).
"""
from __future__ import annotations

import hashlib
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugin_rhino" / "plugin"

SOURCES = [
    PLUGIN / "compas_wood.rhproj",
]


def _files() -> list[pathlib.Path]:
    out = list(SOURCES)
    for pattern, base in (
        ("commands/*.py", PLUGIN),
        ("shared/*.py", PLUGIN),
        ("icons/SVG/*", PLUGIN),
        ("PNG_24/*", PLUGIN.parent / "assets"),
    ):
        out.extend(sorted(base.glob(pattern)))
    return [p for p in out if p.is_file()]


def compute() -> str:
    h = hashlib.sha256()
    for p in _files():
        h.update(p.relative_to(ROOT).as_posix().encode())
        h.update(p.read_bytes())
    return h.hexdigest()


digest = compute()
if len(sys.argv) > 1 and sys.argv[1] == "--check":
    stamp = ROOT / "plugin_rhino" / "plugin" / "dist" / "source_hash.txt"
    recorded = stamp.read_text().strip() if stamp.exists() else "<missing>"
    if recorded != digest:
        print(f"STALE: committed .rhp was built from {recorded[:12]}..., "
              f"sources now hash to {digest[:12]}...")
        print("Run tools/refresh_plugin_build.ps1 locally (needs Rhino) and commit dist/.")
        sys.exit(1)
    print(f"fresh: {digest[:12]}...")
else:
    print(digest)
