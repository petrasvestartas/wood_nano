"""Beam offsets are applied in C++ (apply_beam_offsets), not Python.

The Python layers used to bin beams by atan2 and translate vertices in four
diverging copies of the same loop - a violation of the all-computation-in-C++
rule that also dropped the CDT triangulation of offset beams. These tests pin
the C++ port's semantics: rigid per-beam translation along the z-positive up
axis by the per-direction-group scalar.
"""
from __future__ import annotations

from wood_nano.reciprocal_move import reciprocal_move_elements

OFFSETS = [40.0, -25.0]  # quad mesh -> 2 direction groups


def test_offsets_translate_rigidly():
    _, beams0, s0a, _ = reciprocal_move_elements(nx=6, ny=5, beam_offsets=None, unweld_beams=False)
    _, beams1, s0b, _ = reciprocal_move_elements(nx=6, ny=5, beam_offsets=OFFSETS, unweld_beams=False)
    assert len(beams0) == len(beams1) > 0

    moved = 0
    for b0, b1 in zip(beams0, beams1):
        keys = sorted(b0.vertex.keys())
        dz = [b1.vertex[k][2] - b0.vertex[k][2] for k in keys]
        # every vertex of one beam moves by the same amount: rigid translation
        assert all(abs(d - dz[0]) < 1e-9 for d in dz)
        if abs(dz[0]) > 1e-9:
            moved += 1
    assert moved > 0


def test_zero_offsets_are_identity():
    _, beams0, _, _ = reciprocal_move_elements(nx=4, ny=3, beam_offsets=None, unweld_beams=False)
    _, beams1, _, _ = reciprocal_move_elements(nx=4, ny=3, beam_offsets=[0.0, 0.0], unweld_beams=False)
    for b0, b1 in zip(beams0, beams1):
        for k in b0.vertex:
            assert b0.vertex[k][0] == b1.vertex[k][0]
            assert b0.vertex[k][2] == b1.vertex[k][2]
