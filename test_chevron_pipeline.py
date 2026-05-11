"""Minimal chevron pipeline test — no Rhino needed.
Run once in the local editable env, once in the PyPI wheel env.
Compare output to find which C++ boundary is broken.
"""
import sys
print(f"Python: {sys.executable}")

import importlib.metadata
print(f"wood-nano version: {importlib.metadata.version('wood-nano')}")

import wood_nano._chevron as _c
print(f"\n--- _chevron.pyd attributes ---")
ch = _c.make_default_chevron(4, 900, 0.5, 0.05799, 760, 80, 40, 1.0, 0.5, 1, 1, 1, 1)
print(f"  dir(ch): {[a for a in dir(ch) if not a.startswith('_')]}")

has_tv = hasattr(ch, 'three_valence')
has_adj = hasattr(ch, 'adjacency')
has_iv = hasattr(ch, 'insertion_vectors')
print(f"  three_valence attr: {has_tv}  -> {list(ch.three_valence)[:2] if has_tv else 'MISSING'}")
print(f"  adjacency attr:     {has_adj} -> {list(ch.adjacency)[:2] if has_adj else 'MISSING'}")
print(f"  insertion_vectors:  {has_iv}  -> {len(list(ch.insertion_vectors)) if has_iv else 'MISSING'} entries")

print(f"\n--- chevron_elements() 4-tuple ---")
elements = None
joint_data = None
try:
    from wood_nano import chevron_elements
    result = chevron_elements(u_div=4)
    print(f"  return length: {len(result)}  (expected 4)")
    if len(result) == 4:
        shell, elements, loft_meshes, joint_data = result
        print(f"  elements: {len(elements)}")
        print(f"  joint_data keys: {list(joint_data.keys()) if joint_data else None}")
        if joint_data:
            print(f"  three_valence groups: {len(joint_data['three_valence'])}")
            print(f"  adjacency pairs:      {len(joint_data['adjacency'])}")
            print(f"  joints_per_face rows: {len(joint_data['joints_per_face'])}")
            print(f"  insertion_vectors:    {len(joint_data['insertion_vectors'])}")
    else:
        shell, elements, loft_meshes = result
        joint_data = None
        print("  WARN: only 3 values returned — joint_data missing from this build")
except Exception as e:
    import traceback
    print(f"  ERROR: {e}")
    traceback.print_exc()

print(f"\n--- joinery_solver_elements() ---")
try:
    from wood_nano.joinery_solver import joinery_solver_elements, SEARCH_FACE_TO_FACE
    if elements:
        bottom_pls = [el.bottom for el in elements]
        top_pls    = [el.top   for el in elements]
        jd = joint_data or {}
        elems_out, joints = joinery_solver_elements(
            bottom_pls, top_pls,
            search_type=SEARCH_FACE_TO_FACE,
            per_element_insertion_vectors=jd.get('insertion_vectors'),
            per_element_joint_types=jd.get('joints_per_face'),
            three_valence=jd.get('three_valence'),
            adjacency=jd.get('adjacency'),
        )
        print(f"  joints detected: {len(joints)}")
        for j in joints[:5]:
            print(f"    type={j.joint_type} between {j.element_ids}")
    else:
        print("  SKIPPED — no elements from chevron_elements()")
except Exception as e:
    import traceback
    print(f"  ERROR: {e}")
    traceback.print_exc()
