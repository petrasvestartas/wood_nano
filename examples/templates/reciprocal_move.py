from wood_nano import reciprocal_move_elements

# Default translation-based reciprocal frame (12×10 sinusoidal dome, mm units)
dome, beams, side0, side1 = reciprocal_move_elements(
    nx=12, ny=10,
    W=12000.0, D=10000.0, h=3000.0,
    angle=50.0,   # 50 mm translation offset
    beam_w=100.0, beam_h=200.0,
)
print("dome   vertices:", dome.number_of_vertices(),
      " faces:", dome.number_of_faces())
print("beams :", len(beams))
print("side0 :", len(side0), "outlines")
print("side1 :", len(side1), "outlines")
