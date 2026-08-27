__version__ = "1.0.29"

# Kernel provenance: the git SHAs of the wood and session_cpp checkouts this
# build compiled against (all repos track `main`, so the wood_nano version
# alone does not identify the kernel). "unknown" outside a git build.
try:
    from ._build_info import SESSION_SHA as __session_sha__, WOOD_SHA as __wood_sha__
except ImportError:
    __wood_sha__ = "unknown"
    __session_sha__ = "unknown"

# C++ extension modules — imported first so wrapper submodules can use relative imports
from . import _wood_element
from . import _translation_shell
from . import _reflex_fold
from . import _chevron
from . import _reciprocal_rotation
from . import _reciprocal_move
from . import _diamond_mesh
from . import _connectors
from . import _assign_vectors
from . import _datasets
from . import _joinery_solver

# Python wrappers
from .translation_shell import translation_shell_elements
from .reflex_fold import reflex_fold_elements
from .chevron import annen_json_path, chevron_elements, chevron_elements_annen, chevron_elements_nurbs
from .reciprocal_rotation import reciprocal_rotation_elements, reciprocal_rotation_elements_from_mesh, reciprocal_rotation_elements_from_surface
from .reciprocal_move import reciprocal_move_elements, reciprocal_move_elements_from_mesh, reciprocal_move_elements_from_surface
from .diamond_mesh import diamond_mesh_elements, diamond_mesh_elements_annen, diamond_mesh_elements_from_surface
from .connectors import connectors_elements
from .joinery_solver import joinery_solver_elements
from .loft import loft
from .assign_vectors import assign_insertion_vectors, match_points_to_plate_edges
from .datasets import load_dataset, DATASETS_DIR
try:
    from .plate_topology import PlateTopology
except ImportError as _e:
    # Only the "not running inside Rhino" case is expected; a genuinely broken
    # install used to be swallowed here too, surfacing later as an opaque
    # "'NoneType' object is not callable".
    if _e.name not in ("Rhino", "System", "scriptcontext", "rhinoscriptsyntax", "session_rhino"):
        raise
    PlateTopology = None  # not available outside Rhino
from .wood_element import WoodElement

__all__ = [
    "translation_shell_elements",
    "reflex_fold_elements",
    "annen_json_path",
    "chevron_elements",
    "chevron_elements_annen",
    "chevron_elements_nurbs",
    "reciprocal_rotation_elements",
    "reciprocal_rotation_elements_from_mesh",
    "reciprocal_rotation_elements_from_surface",
    "reciprocal_move_elements",
    "reciprocal_move_elements_from_mesh",
    "reciprocal_move_elements_from_surface",
    "diamond_mesh_elements",
    "diamond_mesh_elements_annen",
    "diamond_mesh_elements_from_surface",
    "connectors_elements",
    "joinery_solver_elements",
    "loft",
    "assign_insertion_vectors",
    "match_points_to_plate_edges",
    "load_dataset",
    "DATASETS_DIR",
    "PlateTopology",
    "WoodElement",
    "_wood_element",
    "_translation_shell",
    "_reflex_fold",
    "_chevron",
    "_reciprocal_rotation",
    "_reciprocal_move",
    "_diamond_mesh",
    "_connectors",
    "_assign_vectors",
    "_datasets",
    "_joinery_solver",
]
