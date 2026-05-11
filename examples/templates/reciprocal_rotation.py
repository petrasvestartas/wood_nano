from wood_nano import reciprocal_rotation_elements

# Default reciprocal rotation frame (12×10 sinusoidal dome)
dome, beams, side0, side1 = reciprocal_rotation_elements(
    nx=12, ny=10,
    W=12.0, D=10.0, h=3.0,
    angle=0.35, scale=1.4,
    beam_w=0.10,
)
print("dome   vertices:", dome.number_of_vertices(),
      " faces:", dome.number_of_faces())
print("beams :", len(beams))
print("side0 :", len(side0), "outlines")
print("side1 :", len(side1), "outlines")
