import wood_nano as m
# import numpy as np

print(m.add(1, 2))
# # print(m.version)
# # print(m.inspect(np.array([[1,2,3], [3,4,5,4]], dtype=np.float32)))

vector_double_1d_0 = m.double1([1,2,3,4,5,8])
vector_double_1d_1 = m.double1([8,9,10])
vector_double_1d_2 = m.double1([1,2,3,4,5,8,1,2,3,4,5,8])

vector_double_2d_0 = m.double2([vector_double_1d_0,vector_double_1d_1])
vector_double_2d_1 = m.double2([vector_double_1d_2])

vector_double_3d = m.double3([vector_double_2d_0, vector_double_2d_1])

p0 = m.point(1,2,3)
p1 = m.point(4,5,6)
result = m.middle_point(p0, p1)
print(result[0], result[1], result[2])