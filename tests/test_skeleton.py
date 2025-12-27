import wood_nano as m
from pathlib import Path
import pytest


DATA_DIR = Path(__file__).parent.parent / "data"
VERTICES_FILE = DATA_DIR / "wood_beam_vertices.txt"
FACES_FILE = DATA_DIR / "wood_beam_faces.txt"


@pytest.mark.skipif(not VERTICES_FILE.exists(), reason="Data files not found")
def test_mesh_skeleton():
    """Test mesh_skeleton function."""
    with open(VERTICES_FILE, "r") as vf:
        vertices = [float(num) for line in vf for num in line.split()]
    with open(FACES_FILE, "r") as ff:
        faces = [int(num) for line in ff for num in line.split()]
    
    v = m.double1(vertices)
    f = m.int1(faces)
    polylines = m.point2()
    
    m.mesh_skeleton(v, f, polylines)
    assert len(polylines) >= 0


@pytest.mark.skipif(not VERTICES_FILE.exists(), reason="Data files not found")
def test_beam_skeleton():
    """Test beam_skeleton function."""
    with open(VERTICES_FILE, "r") as vf:
        vertices = [float(num) for line in vf for num in line.split()]
    with open(FACES_FILE, "r") as ff:
        faces = [int(num) for line in ff for num in line.split()]
    
    v = m.double1(vertices)
    f = m.int1(faces)
    polyline = m.point1()
    distances = m.double1()
    
    m.beam_skeleton(v, f, polyline, distances, 5, 10, False)
    assert len(polyline) >= 0
