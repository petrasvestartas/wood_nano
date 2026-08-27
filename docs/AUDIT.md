# Performance / Precision / Memory Audit — 2026-08-27

Eight parallel audits covered the full stack: the wood joinery kernel
(`wood/src/joinery_solver`, ~7300 lines), the template generators
(`wood/src/templates` + `wood_chevron.h`, ~3300), the nanobind binding layer
(`wood_nano/src/_*.cpp`, ~2200), both Python layers (~2700), a dedicated
deep-dive on plate interface detection, and a wood↔session_cpp integration
review. 127 findings were reported; each was re-verified against the code
before any fix. Two proposed fixes were **rejected by verification** (see
"Reverted" below) — the dataset byte-parity harness caught both.

## Verification harness

- **Byte parity**: `WOOD_F2F_DUMP=1` sweep over 44 datasets → 96
  coordinate/meta dump files, compared byte-for-byte against a pre-audit
  baseline after every batch. Final state: **0/96 differ**.
- **Examples**: all 29 (`tools/run_all_examples.ps1`) pass.
- **Tests**: 7/7 (`tests/`), including new beam-offset parity tests.
- **Bench** (min-of-7, full Python-visible solve):

  | dataset | before | after | joints |
  |---|---|---|---|
  | hexbox_and_corner (11 plates) | 5.3 ms | 1.3 ms | 21 = 21 |
  | vda_floor_1 (54) | 22.4 ms | 7.0 ms | 94 = 94 |
  | cross_vda_single_arch (89) | 36.1 ms | 13.9 ms | 177 = 177 |
  | cross_vda_hexshell (143) | 45.4 ms | 19.2 ms | 303 = 303 |

## Fixed — precision / correctness

- **mm² passed as degrees** (`wood_face_to_face.cpp` → `plane_to_face`):
  `coplanar_tolerance` (squared distance, 0.01 mm²) was fed into the
  cross-joint *angle* tolerance parameter, shrinking the intended parallelism
  guard from wood's 30° to 0.01° — near-parallel plate pairs became type-30
  cross joints with degenerate axes, and retuning `distance_squared` in YAML
  silently retuned an angle. Now an explicit 30° constant (legacy
  `wood_main.h:23` arbitrated the value).
- **Thread-local adjacency leak** (`wood_main.cpp`, found independently by 3
  audits): an exception in the chevron path skipped the override clears; the
  next solve on that thread silently reused the previous model's adjacency.
  RAII guard; swap-with-empty also releases pinned capacity.
- **JPT out-of-bounds** (`wood_main.cpp`, `wood_globals.cpp`):
  `JOINTS_PARAMETERS_AND_TYPES` starts empty and YAML can set any length;
  geometry indexed `row*3+2` unchecked. Guarded read with built-in defaults +
  YAML shape validation on load.
- **Joint-line extension formula** (`wood_face_to_face.cpp`): restored
  legacy's combined `(2ext)² > L² − min²` test (the split re-derivation
  accepted lines legacy rejects near the threshold).
- **Alignment-line overlap unvalidated** (`wood_face_to_face.cpp`):
  disjoint-but-collinear chords averaged into the gap between them, planting
  joint volumes where no contact exists. Return value now checked + length
  guard.
- **Type-40 comment vs code**: legacy arbitration proved the *code* right
  (dir0=-orig, dir1=+orig) and the comment wrong; zero-IV slots now fall back
  to the face normal instead of silently producing coincident volume slabs.
- **YAML null-deref** (`wood_globals.cpp`): bare `key:` entries reached
  `getData<T>` (an unchecked `static_pointer_cast` deref). All reads
  hasData()-guarded; scalar-vs-list confusion needs an upstream TinyYaml type
  tag (deferred, documented).
- **Silent-empty dataset loads** (`wood_internal.cpp`): missing OBJ returned
  an empty vector → pipeline ran on nothing → green test. Now throws naming
  the path. Also: the YAML `duplicate_pts_tol` knob was dead (unconditionally
  stomped by the parameter default) — the config value now applies.
- **Config dir baked via `__FILE__`** (`wood_globals.cpp`): runtime-settable
  override added (`globals::set_config_dir`), same pattern as the 32a00ad
  adjacency fix. `session_data_dir` still `__FILE__`-based — acceptable for
  the test harness, unreachable from wheels.
- **WoodElement ctor unchecked input** (`wood_element.cpp`): empty or
  short-top outlines were UB (average_normal `front()` on empty; `pp1[j+1]`
  OOB). Now degrade to an empty element with a stderr warning. `loft_mesh`
  mismatched rings: empty mesh + warning instead of a silently wrong solid.
- **Chevron path truncation** (`_joinery_solver.cpp`): >18 insertion-vector
  values / >6 joint types per element were silently truncated (hex plates
  lost faces 6+); now a loud `invalid_argument`.
- **Type-10 fallback normal** (`_joinery_solver.cpp`): 3-point normal
  degenerated on collinear picks (outline start mid-edge); now Newell over
  the whole ring (`Vector::average_normal`).
- **Templates**: `chamfer_top` silently ignored (reflex_fold); zero bisector
  normal used unguarded (reflex_fold); `weld(3.14159)` — π pasted into a
  mm slot (diamond_mesh, now 0.01); out-of-domain surface evaluation for
  boundary rows + `t += dt` drift (diamond_mesh); `t += dt` row accumulation
  (translation_shell, now closed-form); `cut_offset_factor` accepted and
  dropped (reciprocal_move, now wired); half-edge 2-coloring seeded only in
  component 0 + odd-cycle conflicts undetected (reciprocal_move); JSON knot
  array size mismatch OOB (wood_chevron); quad-assumption OOB on triangle
  faces (wood_chevron, two sites); `bad_optional_access` on degenerate faces
  (reciprocal.h); empty-mesh OOB write `edgeColors[0]` (reciprocal_move).
- **Python layer**: mismatched hole lists now raise instead of silent zip
  truncation (2 sites); `joint_params` length validated (C++ silently ignored
  wrong lengths); stale hole cache invalidated on `add_plate`; blanket
  `except ImportError` narrowed to the Rhino-absence case; cross-package
  `__file__` data-dir walk replaced with the installed package's path.

## Fixed — performance

- **Lazy loft** (biggest win): `solve_joinery` eagerly lofted + dict-converted
  every element's mesh — 63% of the whole solve on the benchmark note's
  numbers — while the compas consumer discarded it. `include_loft_mesh=False`
  default; the session_py wrapper lofts lazily in C++ on first
  `loft_mesh()` call (same rings, same order); featureless elements keep the
  cheap eager prism loft the lazy path can't reconstruct.
- **`/Os` wheels**: nanobind applies minimum-size optimization to ALL module
  sources in Release — including the entire wood kernel compiled into
  `_joinery_solver`. `NOMINSIZE` on all 11 modules restores `/O2`.
- **True OBB broad phase**: `OBB::from_points(points, inflate)` is an
  axis-aligned box in disguise; thin diagonal plates matched everything.
  Now built from the plate's own frame (the overload existed); candidate
  sets only shrink, dumps unchanged.
- **By-reference detection core**: `plane_to_face` deep-copied 4 Polylines +
  4 Planes per candidate pair before the parallelism reject; now an
  8-const-ref core with array/Element wrappers.
- **Beam offsets in C++** (`apply_beam_offsets` in both reciprocal bindings):
  replaces 4 diverging Python copies of per-vertex translation; offset beams
  keep their CDT face_tris/face_holes (they were dropped by the Python
  rebuild). Parity + rigidity pinned by tests.
- **O(E·F) → O(E)**: per-edge `edge_faces()` full-face scans replaced with
  one-pass edge→face maps (binding `filter_boundary_beams`, `reciprocal.h`,
  `vda_mesh.h`); `edge_line()` per edge (rebuilds the whole directed-edge
  set) replaced with two vertex lookups.
- Assorted: ndarray `.tolist()` bulk conversion instead of per-row indexing
  (hot mesh path); Point-flattening bypass in `_pts_to_polyline`; plate
  outlines converted once not four times; `all_joints.reserve` + shadow-joint
  moves; drill-loop reserves; xf1 reuse for two-volume joints; dot-sign test
  replacing two acos per candidate; point materialization hoisted out of the
  detection segment loop and the beams axis loop; inline squared
  point-segment distance in assign (was Line+Point construction + sqrt per
  segment); dead `m.edges()` call removed; broad/narrow radius coherence in
  assign.

## Reverted by verification (agents' findings disproved)

- **J4** (`-1` edge ids → reject): `-1` is the NORMAL state for plates
  crossing in general position; type-30 joints don't consume those face ids.
  Rejecting removed every cross joint from all 20 cross_* dumps.
- **D14** (inverted `lMin` → reject): inversion is the normal configuration
  for X-crossings; center + axis are orientation-agnostic downstream.
  Both sites now carry comments explaining why the "obvious" guard is wrong.

## Deferred (flagged, not fixed) — with reasons

- **D1/D2** (session_cpp `polyline_plane_to_line`): first-two-crossings chord
  + vertex-on-plane skip can drop legitimate side-side joints (patch not
  straddling the mid-plane / crossing through a vertex). Fix belongs in
  session_cpp with its own test corpus.
- **D5**: one joint per element pair / first boolean region only —
  multi-patch contacts under-jointed. Needs `joints_map` multi-joint keying;
  a feature, not a patch.
- **D7/D12/D15**: unsigned dihedral (mountain/valley identical), mid-sweep
  element mutation (order dependence), first-vertex-anchored mid-plane
  (non-prismatic plates). All legacy-parity; changing them changes output.
- **J15/J6/I13**: PIP exact-equality boundary classification; four different
  closure epsilons for the same concept. Needs one shared predicate +
  deliberate re-baselining.
- **B7**: solve runs holding the GIL; releasing needs a mutex around the
  process-wide wood globals first.
- **Y2/Y3** (compas re-loft orientation): needs C++-guaranteed winding in
  `Mesh::loft`/`mesh_to_dict` before the Python flip logic can go.
- **B9/Y6**: unweld round-trips beams across the boundary 3×; fix is an
  `unweld=true` path in `mesh_to_dict`.
- **B6/B11/B12, J13, T10/T11/T16/T17/T23, I16**: minor perf (double
  vertex_index, property recompute, int casts, merge copies, chevron scan,
  NURBS re-evaluation, shared rtree).
- **S2/S3** (session integration): wood-semantics helpers stranded in
  session_cpp (`Line::scale` extend-and-flip is one upstream "fix" away from
  breaking wood); two competing face-to-face detectors. Needs a
  cross-repo decision.
- **S6**: all three repos float on `GIT_TAG main` — pin a session_cpp SHA in
  both consumers + a reverse-dependency CI job in session_cpp.
- **S7 (second half)**: LTO across the session_core boundary needs `/GL` in
  session_cpp's CMake.
- **wood_chevron.h extras** (T10/T11/T16): left out of the working tree
  because the file carries uncommitted user WIP; only the two memory-safety
  fixes (T2/T20) were applied there.
