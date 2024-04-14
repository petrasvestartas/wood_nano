import wood_nano as m



######################################################################################################
# Conversion of integers
######################################################################################################

def to_int(vectors, depth):
    if depth == 1:
        vector = m.int1()
        vector.reserve(len(vectors))
        for vec in vectors:
            vector.emplace_back(int(vec))
    else:
        vector = getattr(m, f'int{depth}')()
        for vec in vectors:
            vector.emplace_back(to_int(vec, depth - 1))
    return vector

def to_int1(vectors):
    return to_int(vectors, 1)

def to_int2(vectors):
    return to_int(vectors, 2)

def to_int3(vectors):
    return to_int(vectors, 3)

def to_int4(vectors):
    return to_int(vectors, 4)

def from_int1(int1):
    ints = []
    for i in range(len(int1)):
        ints.append(int(int1[i]))
    return ints

def from_int2(int2):
    return [from_int1(i) for i in int2]

def from_int3(int3):
    return [from_int2(i) for i in int3]

def from_int4(int4):
    return [from_int3(i) for i in int4]

######################################################################################################
# Conversion of doubles
######################################################################################################

def to_double(vectors, depth):
    if depth == 1:
        vector = m.double1()
        vector.reserve(len(vectors))
        for vec in vectors:
            vector.emplace_back(float(vec))
    else:
        vector = getattr(m, f'double{depth}')()
        for vec in vectors:
            vector.emplace_back(to_double(vec, depth - 1))
    return vector

def to_double1(vectors):
    return to_double(vectors, 1)

def to_double2(vectors):
    return to_double(vectors, 2)

def to_double3(vectors):
    return to_double(vectors, 3)

def to_double4(vectors):
    return to_double(vectors, 4)

def from_double1(double1):
    doubles = []
    for i in range(len(double1)):
        doubles.append(float(double1[i]))
    return doubles

def from_double2(double2):
    return [from_double1(d) for d in double2]

def from_double3(double3):
    return [from_double2(d) for d in double3]

def from_double4(double4):
    return [from_double3(d) for d in double4]

######################################################################################################
# Conversion of booleans
######################################################################################################

def to_bool1(vectors):
    vector = m.bool1()
    vector.reserve(len(vectors))
    for vec in vectors:
        vector.emplace_back(bool(vec))
    return vector

def from_bool1(bool1):
    bools = []
    for i in range(len(bool1)):
        bools.append(bool(bool1[i]))
    return bools


######################################################################################################
# Conversion functions for Enums
######################################################################################################

def enum_to_dict(enum_type):
    dict = {}
    enum_attributes = dir(enum_type)
    for attribute in enum_attributes:
        if not attribute.startswith('__') and not attribute.startswith('@'): 
            value = getattr(enum_type, attribute)
            dict[int(value)] = str(attribute)
    return dict


def from_cut_type(cut_type, enum_types):
    cut_types = []
    for i in range(len(cut_type)):
        cut_types.append(enum_types[cut_type[i]])
    return cut_types

def from_cut_type2(cut_type2):
    enum_types = enum_to_dict(m.cut_type)
    return [from_cut_type(c, enum_types) for c in cut_type2]