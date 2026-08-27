"""Run one example headlessly, for tools/run_all_examples.ps1.

Every compas example ends in viewer.show(), which blocks on a GUI window until
someone closes it. Stubbing show() exercises the part that can actually be
wrong - the solver call and the scene construction - without opening a window
per example and without each run hanging until the guard's timeout kills it.
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
