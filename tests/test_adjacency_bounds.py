"""The adjacency argument is caller-supplied, so its indices must be checked.

`joinery_solver_elements(..., adjacency=...)` hands the pairs straight down to
the C++ joint-detection loop, which used to index its element vector with them
unchecked. An index past the end bound a reference to nothing, and reading that
element's vector header produced a nonsense length: a segfault under GCC, and a
`MemoryError: bad allocation` under MSVC as it tried to allocate the garbage
size. Either way a caller could take the interpreter down with a stale
adjacency list - one built for a different set of plates, say, or left over
after some were removed.

Out-of-range pairs are now reported on stderr and skipped.
"""
from __future__ import annotations

import pytest

from wood_nano import load_dataset
from wood_nano.joinery_solver import SEARCH_FACE_TO_FACE, joinery_solver_elements

DATASET = "type_plates_name_hexbox_and_corner"


@pytest.fixture(scope="module")
def plates() -> tuple[list, list]:
    bottom, top, _ = load_dataset(DATASET)
    return bottom, top


@pytest.mark.parametrize(
    "adjacency",
    [
        [(99, 100)],       # both past the end
        [(0, 99)],         # one valid, one past the end
        [(-1, 0)],         # negative
        [(0, 1), (5, 42)], # a good pair alongside a bad one
    ],
)
def test_out_of_range_adjacency_does_not_crash(plates, adjacency):
    bottom, top = plates
    _, joints = joinery_solver_elements(
        bottom, top, search_type=SEARCH_FACE_TO_FACE, adjacency=adjacency
    )
    assert isinstance(joints, list)


def test_valid_adjacency_still_detects_joints(plates):
    """The bounds check must not cost us any legitimate pair."""
    bottom, top = plates
    _, joints = joinery_solver_elements(bottom, top, search_type=SEARCH_FACE_TO_FACE)
    assert len(joints) > 0
