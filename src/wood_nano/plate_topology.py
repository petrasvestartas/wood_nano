#! python3
"""PlateTopology — persist plate-element membership in a Rhino .3dm file.
Also stores per-plate joinery metadata (joint_types, insertion_vector) as UserStrings,
and global chevron joinery data (three_valence, adjacency) as document-level strings.

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

import json
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
        self._hole_cache = None  # {pid_str: {"bot": {n: guid}, "top": {n: guid}}}
        self._plate_guids = {}   # {plate_id: {"bot": guid, "top": guid, "mesh": guid}}

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
        self._hole_cache = None
        self._plate_guids.clear()

    def add_plate(self, plate_id, bottom, top, mesh, holes_bot=None, holes_top=None, plate_type="plate"):
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
        holes_bot : list[session_py.Polyline] or None
            Per-hole bottom outline polylines.  None = no holes.
        holes_top : list[session_py.Polyline] or None
            Per-hole top outline polylines.  Same length as holes_bot.
        plate_type : str, optional
            Logical type tag stored as UserString ``plate_type`` (default ``"plate"``).
            Use e.g. ``"face"`` / ``"edge"`` for connectors face/connector plates.
        """
        rh_bot  = _pl_to_rhino(bottom)
        rh_top  = _pl_to_rhino(top)
        rh_mesh = _mesh_to_rhino(mesh)
        self._add_rh(plate_id, rh_bot, rh_top, rh_mesh, plate_type)
        if holes_bot and holes_top:
            doc     = sc.doc
            pid_str = str(int(plate_id))
            for hi, (hb, ht) in enumerate(zip(holes_bot, holes_top)):
                rh_hb = _pl_to_rhino(hb)
                rh_ht = _pl_to_rhino(ht)
                for role, rh_geo in (
                    (f"hole_bot_{hi}", rh_hb),
                    (f"hole_top_{hi}", rh_ht),
                ):
                    if rh_geo is None:
                        continue
                    attr = Rhino.DocObjects.ObjectAttributes()
                    attr.Name = f"{plate_type}_{pid_str}_{role}"
                    attr.SetUserString("plate_id",   pid_str)
                    attr.SetUserString("plate_role", role)
                    attr.SetUserString("plate_type", plate_type)
                    guid = doc.Objects.AddCurve(rh_geo, attr)
                    if guid != System.Guid.Empty:
                        self._guids.append(guid)

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

        if added:
            self._plate_guids[plate_id] = added
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

    def _build_hole_cache(self):
        """One-shot full scan to index all hole objects by plate_id.

        Subsequent calls to find_plate_holes() use this cache so that M plates
        require only 1 document scan instead of M scans.
        """
        cache = {}
        for obj in sc.doc.Objects.GetObjectList(
            Rhino.DocObjects.ObjectType.AnyObject
        ):
            pid_str = obj.Attributes.GetUserString("plate_id")
            if not pid_str:
                continue
            role = obj.Attributes.GetUserString("plate_role") or ""
            if role.startswith("hole_bot_"):
                try:
                    n = int(role[len("hole_bot_"):])
                    cache.setdefault(pid_str, {"bot": {}, "top": {}})["bot"][n] = obj.Id
                except ValueError:
                    pass
            elif role.startswith("hole_top_"):
                try:
                    n = int(role[len("hole_top_"):])
                    cache.setdefault(pid_str, {"bot": {}, "top": {}})["top"][n] = obj.Id
                except ValueError:
                    pass
        self._hole_cache = cache

    def find_plate_holes(self, plate_id):
        """Return parallel GUID lists for the hole polylines of a plate.

        Parameters
        ----------
        plate_id : int

        Returns
        -------
        tuple[list[System.Guid], list[System.Guid]]
            (hole_bot_guids, hole_top_guids), sorted by hole index N where
            the role is ``hole_bot_N`` / ``hole_top_N``.  Both lists have the
            same length (pairs where either side is missing are skipped).
        """
        if self._hole_cache is None:
            self._build_hole_cache()
        pid_str = str(int(plate_id))
        entry = self._hole_cache.get(pid_str, {"bot": {}, "top": {}})
        bot_map = entry["bot"]
        top_map = entry["top"]
        indices = sorted(set(bot_map) & set(top_map))
        return [bot_map[n] for n in indices], [top_map[n] for n in indices]

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

        Expansion is restricted to Rhino objects that share a group with the
        selected objects.  This prevents picking up objects from other copies of
        the same plate layout that carry identical plate_id values (UserStrings
        survive Rhino copy, but each copy gets its own group indices).
        """
        selected_set = set(selected_guids)

        # Step 1: collect Rhino group indices from the selected objects.
        group_indices = set()
        for guid in selected_set:
            obj = sc.doc.Objects.FindId(guid)
            if obj is None:
                continue
            groups = obj.Attributes.GetGroupList()
            if groups:
                for gi in groups:
                    group_indices.add(gi)

        # Step 2: expand to companion objects that share those groups (to pick
        # up bot/top/mesh when only one of them was selected).
        expanded_guids = set()
        if group_indices:
            for obj in sc.doc.Objects.GetObjectList(
                Rhino.DocObjects.ObjectType.AnyObject
            ):
                if obj.Id in selected_set:
                    continue
                groups = obj.Attributes.GetGroupList()
                if groups and any(g in group_indices for g in groups):
                    expanded_guids.add(obj.Id)

        # Step 3: build plate map — selected objects take priority over expanded
        # ones.  This ensures that when the selection mixes objects from different
        # copies with identical plate_id values, the explicitly selected copy wins
        # and the expansion only fills in missing roles from the same groups.
        plate_map: dict[int, dict[str, object]] = {}

        def _register(guid, overwrite):
            obj = sc.doc.Objects.FindId(guid)
            if obj is None:
                return
            val = obj.Attributes.GetUserString("plate_id")
            if not val:
                return
            try:
                pid = int(val)
            except ValueError:
                return
            role = obj.Attributes.GetUserString("plate_role")
            if not role:
                return
            if pid not in plate_map:
                plate_map[pid] = {}
            if overwrite or role not in plate_map[pid]:
                plate_map[pid][role] = obj.Id

        for guid in selected_set:
            _register(guid, overwrite=True)
        for guid in expanded_guids:
            _register(guid, overwrite=False)

        return dict(sorted(plate_map.items()))

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

    # ------------------------------------------------------------------
    # Chevron joinery metadata
    # ------------------------------------------------------------------

    def tag_plate_joinery(self, plate_id, joint_types, insertion_vector):
        """Store per-plate joinery metadata on the plate's bot and top curves.

        Parameters
        ----------
        plate_id : int
        joint_types : list[int]
            6 joint-type codes, one per face of the plate box.
        insertion_vector : list[float]
            18 floats — 6 Vec3 insertion directions (x0,y0,z0, …, x5,y5,z5).
        """
        plate_id = int(plate_id)
        jt_str  = json.dumps([int(x)   for x in joint_types])
        iv_str  = json.dumps([float(x) for x in insertion_vector])
        roles = self._plate_guids.get(plate_id, {})
        for role in ("bot", "top"):
            guid = roles.get(role)
            if guid is None:
                continue
            obj = sc.doc.Objects.FindId(guid)
            if obj is None:
                continue
            obj.Attributes.SetUserString("joint_types",      jt_str)
            obj.Attributes.SetUserString("insertion_vector", iv_str)
            obj.CommitChanges()

    def set_chevron_global_joinery(self, three_valence, adjacency):
        """Store chevron global joinery data in the Rhino document string table.

        Parameters
        ----------
        three_valence : list[list[int]]
            Annen [s0, s1, e20, e31] groups.
        adjacency : list[tuple[int, int] | list[int]]
            Adjacent plate-pair indices.
        """
        sc.doc.Strings.SetString(
            "wood_nano::three_valence", json.dumps(three_valence))
        sc.doc.Strings.SetString(
            "wood_nano::adjacency",     json.dumps(adjacency))

    def get_chevron_global_joinery(self):
        """Read chevron global joinery data from the Rhino document string table.

        Returns
        -------
        tuple[list, list]
            (three_valence, adjacency); each defaults to [] when not stored.
        """
        tv_str  = sc.doc.Strings.GetValue("wood_nano::three_valence")
        adj_str = sc.doc.Strings.GetValue("wood_nano::adjacency")
        three_valence = json.loads(tv_str)  if tv_str  else []
        adjacency     = json.loads(adj_str) if adj_str else []
        return three_valence, adjacency

    def get_plate_joinery(self, plate_id, bot_guid=None):
        """Read per-plate joinery metadata from the Rhino document.

        Reads the ``joint_types`` and ``insertion_vector`` UserStrings from
        the bot curve of the given plate.

        Parameters
        ----------
        plate_id : int
        bot_guid : System.Guid or None
            When provided, reads directly from this object instead of
            scanning all document objects.  Always pass this when you have the
            GUID from a ``collect_plates_from_selection`` result to avoid
            reading from a different copy that shares the same plate_id.

        Returns
        -------
        tuple[list[int], list[float]]
            (joint_types, insertion_vector); each defaults to [] when absent.
        """
        def _parse(obj):
            jt_str = obj.Attributes.GetUserString("joint_types")
            iv_str = obj.Attributes.GetUserString("insertion_vector")
            return (json.loads(jt_str) if jt_str else [],
                    json.loads(iv_str) if iv_str else [])

        if bot_guid is not None:
            obj = sc.doc.Objects.FindId(bot_guid)
            if obj is not None:
                return _parse(obj)

        pid_str = str(int(plate_id))
        for obj in sc.doc.Objects.GetObjectList(
            Rhino.DocObjects.ObjectType.AnyObject
        ):
            if obj.Attributes.GetUserString("plate_id") != pid_str:
                continue
            if obj.Attributes.GetUserString("plate_role") != "bot":
                continue
            return _parse(obj)
        return [], []
