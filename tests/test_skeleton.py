import wood_nano as m
from wood_nano import conversions_python
from pathlib import Path

# Define the paths to the data files
vertices_file = Path(__file__).parent.parent / 'data' / 'wood_beam_vertices.txt'
faces_file = Path(__file__).parent.parent / 'data' / 'wood_beam_faces.txt'

# Read and parse the vertex coordinates
with open(vertices_file, 'r') as vf:
    vertices = [float(num) for line in vf for num in line.split()]

# Read and parse the face coordinates
with open(faces_file, 'r') as ff:
    faces = [int(num) for line in ff for num in line.split()]


######################################################################################################
# Test mesh_skeleton and beam_skeleton
######################################################################################################
v = m.double1(vertices)
f = m.int1(faces)

polylines = m.point2()
m.mesh_skeleton(v, f, polylines)

for polyline in polylines:
    print('Polyline:')
    for point in polyline:
        print(point.x(), point.y(), point.z())


polyline = m.point1()
distances = m.double1()
m.beam_skeleton(v, f, polyline, distances, 5, 10, False)

print('Polyline of beam_skeleton:')
for id, point in enumerate(polyline):
    print("Coordinates: ", point.x(), point.y(), point.z())
    if distances:
        print("Distance to Mesh: ", distances[id])

