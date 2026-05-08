from wood_nano import chevron_elements

# Default chevron shell (built-in 3000×5000 flat surface)
mesh, elements, loft_meshes = chevron_elements(
    u_divisions=4,
    v_division_dist=900.0,
    box_height=760.0,
    plate_thickness=40.0,
    edge_rotation=1.0,
    edge_offset=0.5,
)
print("chevron  vertices:", mesh.number_of_vertices(),
      " faces:", mesh.number_of_faces())
print("chevron  elements:", len(elements),
      " (4 plate-pairs per mesh face)")

# Each element has bottom/top polylines and a loft mesh
el = elements[0]
print("element[0] bottom pts:", el.bottom.point_count())
print("element[0] top    pts:", el.top.point_count())
