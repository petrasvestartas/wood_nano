"""gen_rhproj.py — regenerate compas_wood.rhproj with new v3.0.0 commands.

Run once from the plugin root:
    python plugin_rhino/plugin/shared/gen_rhproj.py

Reads SVGs from icons/SVG/ and PNGs from ../../assets/PNG_24/,
base64-encodes them, and writes the updated compas_wood.rhproj.
"""

import base64
import json
import pathlib
import uuid

HERE = pathlib.Path(__file__).parent            # plugin_rhino/plugin/shared/
PLUGIN_DIR = HERE.parent                        # plugin_rhino/plugin/
SVG_DIR   = PLUGIN_DIR / "icons" / "SVG"
PNG_DIR   = PLUGIN_DIR.parent / "assets" / "PNG_24"
RHPROJ    = PLUGIN_DIR / "compas_wood.rhproj"

# Map: command title → (uri, svg_stem)
COMMANDS = [
    ("w_install",                           "commands/w_install.py",                           "icon_install"),
    ("w_template_diamond_mesh",             "commands/w_template_diamond_mesh.py",             "icon_diamond_mesh"),
    ("w_template_translation_shell",        "commands/w_template_translation_shell.py",        "icon_translation_shell"),
    ("w_template_reflex_fold",              "commands/w_template_reflex_fold.py",              "icon_reflex_fold"),
    ("w_template_connectors",              "commands/w_template_connectors.py",               "icon_connectors"),
    ("w_template_reciprocal_rotation",      "commands/w_template_reciprocal_rotation.py",      "icon_reciprocal_rotation"),
    ("w_template_reciprocal_move",          "commands/w_template_reciprocal_move.py",          "icon_reciprocal_move"),
    ("w_template_chevron",                  "commands/w_template_chevron.py",                  "icon_chevron"),
    ("w_solver_assign_insertion_direction", "commands/w_solver_assign_insertion_direction.py", "icon_insertion_direction"),
    ("w_solver_assign_joint_types",         "commands/w_solver_assign_joint_types.py",         "icon_joint_type"),
    ("w_solver_joinery_solver",             "commands/w_solver_joinery_solver.py",             "icon_solver"),
]


def b64(path: pathlib.Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def svg_b64_clean(path: pathlib.Path) -> str:
    """Base64-encode SVG with the XML declaration stripped.

    Rhino inlines the decoded SVG as raw XML inside the .rui <icons> section.
    An embedded <?xml?> declaration makes the .rui invalid XML, so strip it.
    """
    text = path.read_text(encoding="utf-8")
    text = text.lstrip()
    if text.startswith("<?xml"):
        text = text[text.index("?>") + 2:].lstrip()
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def build_code_entry(title, uri, svg_stem):
    svg_path = SVG_DIR / f"{svg_stem}.svg"
    png_path = PNG_DIR / f"{svg_stem}.png"

    svg_b64 = svg_b64_clean(svg_path) if svg_path.exists() else ""
    png_b64 = b64(png_path) if png_path.exists() else ""

    return {
        "id": str(uuid.uuid4()),
        "language": {
            "id": "mcneel.pythonnet.python",
            "version": "3.9.10"
        },
        "title": title,
        "uri": uri,
        "image": {
            "light": {
                "type": "svg",
                "data": svg_b64
            },
            "rendered": {
                "light": {
                    "bytes": png_b64,
                    "width": 24,
                    "height": 24
                },
                "dark": {
                    "bytes": png_b64,
                    "width": 24,
                    "height": 24
                }
            }
        }
    }


def main():
    data = json.loads(RHPROJ.read_text(encoding="utf-8"))

    # Bump version
    data["version"] = "3.0.0"

    # Replace commands
    data["codes"] = [
        build_code_entry(title, uri, svg_stem)
        for title, uri, svg_stem in COMMANDS
    ]

    RHPROJ.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"Written: {RHPROJ}")
    print(f"  version: 3.0.0")
    print(f"  commands: {len(data['codes'])}")
    for c in data["codes"]:
        svg_ok = bool(c["image"]["light"]["data"])
        png_ok = bool(c["image"]["rendered"]["light"]["bytes"])
        print(f"    {c['title']:45s}  svg={'ok' if svg_ok else 'MISSING':7s}  png={'ok' if png_ok else 'MISSING'}")


if __name__ == "__main__":
    main()
