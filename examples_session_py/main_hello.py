from session_py.mesh import Mesh
from wood_nano import translation_shell_elements
from wood_nano.wood_element import WoodElement

mesh: Mesh
elements: list[WoodElement]
mesh, elements = translation_shell_elements()
print(mesh.number_of_vertices(), mesh.number_of_faces(), len(elements))
