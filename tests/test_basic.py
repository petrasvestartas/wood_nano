import wood_nano as m


def test_add():
    """Test basic add function."""
    assert m.add(1, 2) == 3


def test_point_creation():
    """Test point creation and access."""
    p = m.point(1, 2, 3)
    assert p[0] == 1
    assert p[1] == 2
    assert p[2] == 3


def test_middle_point():
    """Test middle point calculation."""
    p0 = m.point(0, 0, 0)
    p1 = m.point(2, 4, 6)
    result = m.middle_point(p0, p1)
    assert result[0] == 1.0
    assert result[1] == 2.0
    assert result[2] == 3.0


def test_point_list():
    """Test point list operations."""
    p = m.point(1, 2, 3)
    points = m.point1([p, p, p])
    assert len(points) == 3
    points.append(p)
    assert len(points) == 4


def test_double_vectors():
    """Test double vector operations."""
    vec = m.double1([1.0, 2.0, 3.0])
    assert len(vec) == 3
    vec.append(4.0)
    assert len(vec) == 4


def test_int_vectors():
    """Test integer vector operations."""
    vec = m.int1([1, 2, 3])
    assert len(vec) == 3


def test_globals():
    """Test GLOBALS access."""
    assert hasattr(m.GLOBALS, "CLIPPER_SCALE")
    scale = m.GLOBALS.CLIPPER_SCALE
    assert isinstance(scale, (int, float))
