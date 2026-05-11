# wood_nano Rhino Plugin v3.0.0

Rhino 8 plugin that exposes `wood_nano` timber joinery templates and the joinery solver as native Rhino commands.

## Prerequisites

- Rhino 8 (Script Editor with Python 3 support)
- Internet access for the first install (PyPI)

## Opening the plugin

1. In Rhino, run the command `ScriptEditor` (or open it from **Tools → Python Script → Edit**)
2. In the Script Editor menu: **File → Open Folder**
3. Navigate to this directory (`plugin_rhino/plugin/`) and click **Select Folder**
4. The plugin loads and all `w_*` commands become available in the Rhino command bar

## First-time setup

Run `w_install` in the Rhino command bar.  This upgrades `wood-nano` from PyPI into the `wood_nano` virtual environment.  No other packages are required — `session_py` is bundled inside the `wood-nano` wheel.

## Commands

### Install

| Command | Description |
|---------|-------------|
| `w_install` | Install / upgrade `wood-nano` from PyPI |

### Templates — generate plate geometry

Run a template first to create tagged plate objects in the document.  Each command opens an interactive parameter panel; press **Enter** with no selection to use the built-in defaults.

| Command | Description |
|---------|-------------|
| `w_template_chevron` | Chevron shell from flat surface or Annen building surfaces |
| `w_template_connectors` | Face plates + edge connector rectangles from any mesh |
| `w_template_diamond_mesh` | Diamond mesh shell from NURBS surface or parametric default |
| `w_template_reciprocal_move` | Translation-based reciprocal frame (nexorade) |
| `w_template_reciprocal_rotation` | Rotation-based reciprocal frame |
| `w_template_reflex_fold` | Folded shell swept between two polylines |
| `w_template_translation_shell` | Translation shell between two polylines |

### Joinery solver — cut geometry

Run after a template to compute and draw joint cut geometry.

| Command | Description |
|---------|-------------|
| `w_solver_joinery_solver` | Detect joints, compute cut outlines and volumes |
| `w_solver_assign_joint_types` | Tag plate edges with joint type codes using TextDots |

## Typical workflow

```
w_template_translation_shell   → select/accept parameters → plate objects appear
w_solver_assign_joint_types    → select plates → place TextDots → select dots
w_solver_joinery_solver        → select plates → choose search type → joints drawn
```

## Rebuilding / reloading

After editing any command file, re-run the command in Rhino — the Script Editor reloads the file automatically on each invocation.

If you change C++ source in `src/`, rebuild the wheel:

```bash
# Rhino Python (primary target)
"C:/Users/Petras/.rhinocode/py39-rh8/python.exe" -m pip install --no-build-isolation -e .
copy "C:/Users/Petras/.rhinocode/py39-rh8/lib/site-packages/wood_nano/_translation_shell.cp39-win_amd64.pyd" src/wood_nano/

# uv dev environment
uv pip install --no-build-isolation -e .
```

## Regenerating compas_wood.rhproj

If you add or rename commands, update `shared/gen_rhproj.py` and re-run:

```bash
python plugin_rhino/plugin/shared/gen_rhproj.py
```

This reads SVGs from `icons/SVG/` and PNGs from `../assets/PNG_24/` and rewrites `compas_wood.rhproj`.

## Directory layout

```
plugin/
├── commands/          10 command scripts (w_install, w_template_*, w_solver_*)
├── icons/SVG/         SVG source icons
├── shared/
│   ├── datasets/      XML joint configuration datasets (used by future commands)
│   └── gen_rhproj.py  Helper to regenerate compas_wood.rhproj
└── compas_wood.rhproj Plugin manifest (version 3.0.0)
```
