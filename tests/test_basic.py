import wood_nano as m
from wood_nano import conversions_python
from icecream import ic


######################################################################################################
# First nanobind example
######################################################################################################
ic(m.add(1, 2))


######################################################################################################
# Conversion of integers
######################################################################################################
integers0 = [0,1,2]
integers1 = [0,1,2]
integers2 = [integers0, integers1]

ic(conversions_python.to_int2(integers2))
ic(conversions_python.from_int2(conversions_python.to_int2(integers2)))

######################################################################################################
# Conversion of doubles
######################################################################################################

doubles0 = [0.1,1.7,2.1]
doubles1 = [0.5,1.8,2.5]
doubles2 = [doubles0, doubles1]

ic(conversions_python.to_double2(doubles2))
ic(conversions_python.from_double2(conversions_python.to_double2(doubles2)))

vector_double_1d_0 = m.double1([1,2,3,4,5,8])
vector_double_1d_1 = m.double1()
vector_double_1d_1.append(8)
vector_double_1d_1.append(9)
vector_double_1d_1.append(10)


vector_double_1d_2 = m.double1()
vector_double_1d_2.append(1)
vector_double_1d_2.append(2)
vector_double_1d_2.append(3)
vector_double_1d_2.append(4)
vector_double_1d_2.append(5)
vector_double_1d_2.append(8)


vector_double_2d_0 = m.double2()
vector_double_2d_0.append(vector_double_1d_0)
vector_double_2d_0.append(vector_double_1d_1)

vector_double_2d_1 = m.double2([vector_double_1d_2])

vector_double_3d = m.double3([vector_double_2d_0, vector_double_2d_1])

######################################################################################################
# Conversion of booleans
######################################################################################################

boolean0 = [True, False, True]
ic(conversions_python.to_bool1(boolean0))
ic(conversions_python.from_bool1(conversions_python.to_bool1(boolean0)))

m_bool1 = m.bool1()


######################################################################################################
# Conversion of points
######################################################################################################

p0 = m.point(1,2,3)
p1 = m.point(4,5,6)
result = m.middle_point(p0, p1)
ic(result[0], result[1], result[2])

point = m.point(1,2,3)
points = m.point1([point, point, point])
points.append(point)
for point in points:
    ic(point[0], point[1], point[2])

######################################################################################################
# ic call in C++
######################################################################################################

m.test()

######################################################################################################
# Read xml polylines
######################################################################################################
polylines_coordinates = m.double2()
m.read_xml_polylines(
    "/home/petras/brg/2_code/wood_nano/src/wood/cmake/src/wood/dataset/",
    "type_plates_name_cross_vda_hexshell_reciprocal",
    polylines_coordinates,
)

for polyline in polylines_coordinates:
    for i in range(0, len(polyline), 3):
        ic(polyline[i], polyline[i+1], polyline[i+2])
