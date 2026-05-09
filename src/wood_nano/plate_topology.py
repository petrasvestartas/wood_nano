#! python3
"""PlateTopology — persist plate-element membership in a Rhino .3dm file.

Each plate is tagged on its constituent Rhino objects with two UserStrings
that survive save/open without any compiled plugin:

  plate_id   — integer index of the plate (string-encoded)
  plate_role — "bot" | "top" | "mesh"

A named Rhino group "plate_<id>" bundles the three objects for interactive
Tab-selection in the viewport.  The UserStrings provide a second lookup path
that survives accidental Ungroup operations.

Usage (in a template script):
    from plate_topology import PlateTopology
    topo = PlateTopology()          # module-level; persists across callbacks

    # inside the _run / callback:
    topo.clear()
    for i, (el, mesh) in enumerate(zip(elements, loft_meshes)):
        topo.add_plate(i, el.bottom, el.top, unweld_mesh(mesh))

    # inside a joinery step:
    plates = topo.collect_plates_from_selection(selected_guids)
    # → {plate_id: {"bot": guid, "top": guid, "mesh": guid}, ...}
"""

import System
import Rhino
import scriptcontext as sc

from session_rhino.rhino_polyline import to_rhino as _pl_to_rhino
from session_rhino.rhino_mesh import to_rhino as _mesh_to_rhino


class PlateTopology:
    """Tracks plate→object membership inside the active Rhino document."""

    def __init__(self):
        self._guids = []         # all object GUIDs we have added
        self._group_indices = [] # group indices we have created

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def clear(self):
        """Delete all previously added plate objects and groups from the doc."""
        doc = sc.doc
        for g in self._guids:
            doc.Objects.Delete(g, True)
        for gi in self._group_indices:
            doc.Groups.Delete(gi)
        self._guids.clear()
        self._group_indices.clear()

    def add_plate(self, plate_id, bottom, top, mesh, plate_type="plate"):
        """Add one plate's geometry to the document with topology tags.

        Parameters
        ----------
        plate_id : int
            Zero-based plate index.
        bottom : session_py.Polyline
            Bottom outline polyline.
        top : session_py.Polyline
            Top outline polyline.
        mesh : session_py.Mesh
            Loft mesh between bottom and top.
        plate_type : str, optional
            Logical type tag stored as UserString ``plate_type`` (default ``"plate"``).
            Use e.g. ``"face"`` / ``"edge"`` for vda_mesh face/connector plates.
        """
        rh_bot  = _pl_to_rhino(bottom)
        rh_top  = _pl_to_rhino(top)
        rh_mesh = _mesh_to_rhino(mesh)
        self._add_rh(plate_id, rh_bot, rh_top, rh_mesh, plate_type)

    def add_plate_rh(self, plate_id, rh_bottom, rh_top, rh_mesh, plate_type="plate"):
        """Same as add_plate but accepts already-converted RhinoCommon geometry.

        Parameters
        ----------
        plate_id : int
        rh_bottom : Rhino.Geometry.PolylineCurve or None
        rh_top    : Rhino.Geometry.PolylineCurve or None
        rh_mesh   : Rhino.Geometry.Mesh
        plate_type : str, optional
        """
        self._add_rh(plate_id, rh_bottom, rh_top, rh_mesh, plate_type)

    def _add_rh(self, plate_id, rh_bot, rh_top, rh_mesh, plate_type):
        """Internal: add RhinoCommon geometry with topology tags."""
        doc = sc.doc
        plate_id = int(plate_id)
        pid_str  = str(plate_id)

        added = {}
        for role, rh_geo, add_fn in [
            ("bot",  rh_bot,  lambda g, a: doc.Objects.AddCurve(g, a)),
            ("top",  rh_top,  lambda g, a: doc.Objects.AddCurve(g, a)),
            ("mesh", rh_mesh, lambda g, a: doc.Objects.AddMesh(g, a)),
        ]:
            if rh_geo is None:
                continue
            attr = Rhino.DocObjects.ObjectAttributes()
            attr.Name = f"{plate_type}_{pid_str}_{role}"
            attr.SetUserString("plate_id",   pid_str)
            attr.SetUserString("plate_role", role)
            attr.SetUserString("plate_type", plate_type)
            guid = add_fn(rh_geo, attr)
            if guid != System.Guid.Empty:
                added[role] = guid
                self._guids.append(guid)

        if len(added) >= 2:
            gi = doc.Groups.Add(f"{plate_type}_{pid_str}", list(added.values()))
            if gi >= 0:
                self._group_indices.append(gi)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_plate_id(self, guid):
        """Return the plate_id (int) for a given object GUID, or None."""
        obj = sc.doc.Objects.FindId(guid)
        if obj is None:
            return None
        val = obj.Attributes.GetUserString("plate_id")
        return int(val) if val else None

    def find_plate_objects(self, plate_id, plate_type=None):
        """Return {role: guid} dict for the given plate_id.

        Parameters
        ----------
        plate_id : int
        plate_type : str or None
            When given, only returns objects whose ``plate_type`` UserString matches.

        Enumerates all document objects — safe workaround for the known
        FindByUserString native-layer bug in some Rhino versions.
        """
        pid_str = str(int(plate_id))
        found = {}
        for obj in sc.doc.Objects.GetObjectList(
            Rhino.DocObjects.ObjectType.AnyObject
        ):
            if obj.Attributes.GetUserString("plate_id") != pid_str:
                continue
            if plate_type is not None:
                if obj.Attributes.GetUserString("plate_type") != plate_type:
                    continue
            role = obj.Attributes.GetUserString("plate_role")
            if role:
                found[role] = obj.Id
        return found   # {"bot": guid, "top": guid, "mesh": guid}

    def collect_plates_from_selection(self, selected_guids):
        """Expand a user selection to full plate sets.

        Parameters
        ----------
        selected_guids : iterable of System.Guid
            GUIDs from rs.GetObjects / GetObject selection.

        Returns
        -------
        dict[int, dict[str, System.Guid]]
            {plate_id: {"bot": guid, "top": guid, "mesh": guid}}

        plate_id values must be globally unique across all plate_type values.
        Templates that use multiple plate types (e.g. "face" + "edge") must
        assign non-overlapping integer IDs; see vda_mesh.py for the convention.
        """
        # Collect (plate_id, plate_type) pairs so find_plate_objects can use
        # the type filter — prevents mixing objects from different plate types
        # that might accidentally share the same integer plate_id.
        keys: dict[int, str] = {}  # pid → first plate_type seen for that pid
        for guid in selected_guids:
            obj = sc.doc.Objects.FindId(guid)
            if obj is None:
                continue
            val = obj.Attributes.GetUserString("plate_id")
            if not val:
                continue
            try:
                pid = int(val)
            except ValueError:
                continue
            if pid not in keys:
                ptype = obj.Attributes.GetUserString("plate_type") or None
                keys[pid] = ptype

        return {
            pid: self.find_plate_objects(pid, plate_type=ptype)
            for pid, ptype in sorted(keys.items())
        }

    def all_plate_ids(self):
        """Return sorted list of all plate_id values currently in the document."""
        ids = set()
        for obj in sc.doc.Objects.GetObjectList(
            Rhino.DocObjects.ObjectType.AnyObject
        ):
            val = obj.Attributes.GetUserString("plate_id")
            if val:
                try:
                    ids.add(int(val))
                except ValueError:
                    pass
        return sorted(ids)
