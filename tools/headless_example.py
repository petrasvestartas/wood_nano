"""Run one example headlessly, for tools/run_all_examples.ps1.

Stubs viewer.show() (blocks on a GUI window until someone closes it) so the
part that can actually be wrong - the solver call and the scene construction -
still runs without opening a window or hanging until the guard's timeout.
The compas examples now live in the compas_wood repo; the compas_viewer stub
below is kept as a harmless guard in case an example imports it.
"""
from __future__ import annotations

import runpy
import sys
import traceback
from pathlib import Path

script = Path(sys.argv[1]).resolve()
extra = sys.argv[2:]

try:
    from compas_viewer import Viewer

    Viewer.show = lambda self, *args, **kwargs: print("[viewer.show() stubbed]")
except ImportError:
    pass  # session_py examples do not use the viewer

# The examples run at top level with no main guard, and some read sys.argv.
sys.argv = [str(script), *extra]

try:
    runpy.run_path(str(script), run_name="__main__")
except Exception:
    traceback.print_exc()
    print(f"FAILED {script.name}")
    raise SystemExit(1)

print(f"PASSED {script.name}")
