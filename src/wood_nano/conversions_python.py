import wood_nano as m



######################################################################################################
# Conversion of integers
######################################################################################################

def to_int(vectors, depth):
    if depth == 1:
        vector = m.int1(vectors)
    else:
        vector = getattr(m, f'int{depth}')()
        for vec in vectors:
            vector.append(to_int(vec, depth - 1))
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
    return list(int1)

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
        vector = m.double1(vectors)
    else:
        vector = getattr(m, f'double{depth}')()
        for vec in vectors:
            vector.append(to_double(vec, depth - 1))
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
    return list(double1)

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
    return m.bool1(vectors)

def from_bool1(bool1):
    return list(bool1)

######################################################################################################
# Conversion of strings
######################################################################################################
def to_string1(vectors):
    return m.string1(vectors)

def from_string1(string1):
    return list(string1)

######################################################################################################
# Conversion functions for Enums
######################################################################################################

def enum_to_dict(enum_type):
    dict = {}
    enum_attributes = dir(enum_type)
    for attribute in enum_attributes:
        if not attribute.startswith('__') and not attribute.startswith('@'): 
            value = getattr(enum_type, attribute)
            dict[str(value)] = str(attribute)
    return dict


def from_cut_type(cut_type, enum_types):
    cut_types = []
    for i in range(len(cut_type)):
        cut_types.append(enum_types[str(cut_type[i])])
    return cut_types

def from_cut_type2(cut_type2):
    enum_types = enum_to_dict(m.cut_type)
    return [from_cut_type(c, enum_types) for c in cut_type2]

