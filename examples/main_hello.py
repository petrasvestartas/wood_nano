from wood_nano import translation_shell_elements


mesh, elements = translation_shell_elements()
print("translation_shell  vertices:", mesh.number_of_vertices(),
      " faces:", mesh.number_of_faces())
print("translation_shell  elements:", len(elements))
