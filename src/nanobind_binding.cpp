/**
 * @file nanobind_binding.cpp
 * @brief This file contains the bindings for the wood_nano_ext module.
 */

// nanobind
#include <nanobind/nanobind.h>
#include <nanobind/ndarray.h>
#include <nanobind/stl/array.h>
#include <nanobind/stl/bind_vector.h>
#include <nanobind/stl/string.h>

// main header
#include "stdafx.h"
#include "wood_test.h" // test

// data structure
#include "wood_cut.h"
#include "wood_element.h"
#include "wood_main.h"

// joinery
#include "wood_joint.h"
#include "wood_joint_lib.h"

// geometry methods
#include "cgal_inscribe_util.h"
#include "cgal_mesh_boolean.h"
#include "cgal_rectangle_util.h"

namespace nb = nanobind;
using namespace nb::literals; // enables syntax for annotating function
                              // arguments

namespace internal {
IK::Point_3 point_at(IK::Vector_3 (&box)[5], const double &s, const double &t,
                     const double &c) {
  return IK::Point_3(
      box[0].x() + s * box[1].x() + t * box[2].x() + c * box[3].x(),
      box[0].y() + s * box[1].y() + t * box[2].y() + c * box[3].y(),
      box[0].z() + s * box[1].z() + t * box[2].z() + c * box[3].z()

  );
}

void get_corners(IK::Vector_3 (&box)[5], CGAL_Polyline &corners) {
  corners = CGAL_Polyline(8);

  corners[0] = point_at(box, box[4].x(), box[4].y(), -box[4].z());
  corners[1] = point_at(box, -box[4].x(), box[4].y(), -box[4].z());
  corners[3] = point_at(box, box[4].x(), -box[4].y(), -box[4].z());
  corners[2] = point_at(box, -box[4].x(), -box[4].y(), -box[4].z());

  corners[4] = point_at(box, box[4].x(), box[4].y(), box[4].z());
  corners[5] = point_at(box, -box[4].x(), box[4].y(), box[4].z());
  corners[7] = point_at(box, box[4].x(), -box[4].y(), box[4].z());
  corners[6] = point_at(box, -box[4].x(), -box[4].y(), box[4].z());
}
} // namespace internal

/////////////////////////////////////////////////////////////////////////////////////////////////
// Global variables
/////////////////////////////////////////////////////////////////////////////////////////////////
int scale = 1e6;

/////////////////////////////////////////////////////////////////////////////////////////////////
// Add function
/////////////////////////////////////////////////////////////////////////////////////////////////
int add(int a, int b) {
  return a + b;

  wood::GLOBALS::DISTANCE = 0.1;
  wood::GLOBALS::DISTANCE_SQUARED = 0.01;
  wood::GLOBALS::ANGLE = 0.11;
  wood::GLOBALS::OUTPUT_GEOMETRY_TYPE = 3;
  wood::GLOBALS::DATA_SET_INPUT_FOLDER =
      std::filesystem::current_path().parent_path().string() +
      "/wood_nano/src/wood/cmake/src/wood/dataset/";
  wood::GLOBALS::DATA_SET_OUTPUT_FILE =
      wood::GLOBALS::DATA_SET_INPUT_FOLDER + "out.xml";
  wood::GLOBALS::DATA_SET_OUTPUT_DATABASE =
      wood::GLOBALS::DATA_SET_INPUT_FOLDER + "out.db";
  wood::GLOBALS::OUTPUT_GEOMETRY_TYPE = 3;
  // wood::test::type_plates_name_side_to_side_edge_inplane_hilti();
}

/////////////////////////////////////////////////////////////////////////////////////////////////
// CGAL Point_3 and Vector_3
/////////////////////////////////////////////////////////////////////////////////////////////////
IK::Point_3 middle_point(const IK::Point_3 &a, const IK::Point_3 &b) {
  return IK::Point_3((a.x() + b.x()) / 2, (a.y() + b.y()) / 2,
                     (a.z() + b.z()) / 2);
}

void rtree(std::vector<std::vector<IK::Point_3>> &input_polyline_pairs,
           std::vector<std::vector<int>> &elements_neighbours,
           std::vector<std::vector<IK::Point_3>> &elements_AABB,
           std::vector<std::vector<IK::Point_3>> &elements_OOBB) {

  //////////////////////////////////////////////////////////////////////////////
  // Convert raw-data to list of Polylines
  //////////////////////////////////////////////////////////////////////////////
  // std::vector<CGAL_Polyline> input_polyline_pairs;
  // python_to_cpp__cpp_to_python::coord_to_vector_of_polylines(polylines_coordinates,
  // input_polyline_pairs);

  //////////////////////////////////////////////////////////////////////////////
  // Create elements, AABB, OBB, P, Pls, thickness
  //////////////////////////////////////////////////////////////////////////////
  std::vector<wood::element> e;
  std::vector<std::vector<IK::Vector_3>> input_insertion_vectors;
  std::vector<std::vector<int>> input_joint_types;
  wood::main::get_elements(input_polyline_pairs, input_insertion_vectors,
                           input_joint_types, e);

  //////////////////////////////////////////////////////////////////////////////
  // Create joints, Perform Joint Area Search
  //////////////////////////////////////////////////////////////////////////////

  //////////////////////////////////////////////////////////////////////////////
  // Create RTree
  //////////////////////////////////////////////////////////////////////////////

  RTree<int, double, 3> tree;

  //////////////////////////////////////////////////////////////////////////////
  // Insert AABB
  //////////////////////////////////////////////////////////////////////////////

  for (size_t i = 0; i < e.size(); i++) {
    double min[3] = {e[i].aabb.xmin(), e[i].aabb.ymin(), e[i].aabb.zmin()};
    double max[3] = {e[i].aabb.xmax(), e[i].aabb.ymax(), e[i].aabb.zmax()};
    tree.Insert(min, max, i);
  }

  //////////////////////////////////////////////////////////////////////////////
  // Search Closest Boxes | Skip duplicates pairs | Perform callback with OBB
  //////////////////////////////////////////////////////////////////////////////
  elements_neighbours.reserve(e.size());

  for (size_t i = 0; i < e.size(); i++) {

    std::vector<int> element_neigbhours;

    auto callback = [&element_neigbhours, i, &e](int foundValue) -> bool {
      if (cgal::box_util::get_collision(e[i].oob, e[foundValue].oob)) {
        element_neigbhours.push_back(foundValue);
      }
      return true;
    };

    double min[3] = {e[i].aabb.xmin(), e[i].aabb.ymin(), e[i].aabb.zmin()};
    double max[3] = {e[i].aabb.xmax(), e[i].aabb.ymax(), e[i].aabb.zmax()};
    int nhits = tree.Search(
        min, max, callback); // callback in this method call callback above

    // Add elements to the vector
    elements_neighbours.emplace_back(std::vector<int>());

    for (int j = 0; j < element_neigbhours.size(); j++)
      elements_neighbours.back().emplace_back(element_neigbhours[j]);
  }

  //////////////////////////////////////////////////////////////////////////////
  // Output AABB
  //////////////////////////////////////////////////////////////////////////////
  elements_AABB.reserve(e.size());

  for (size_t i = 0; i < e.size(); i++) {

    elements_AABB.emplace_back(std::vector<IK::Point_3>());
    elements_AABB.back().reserve(8);

    elements_AABB.back().emplace_back(
        IK::Point_3(e[i].aabb.xmin(), e[i].aabb.ymin(), e[i].aabb.zmin()));
    elements_AABB.back().emplace_back(
        IK::Point_3(e[i].aabb.xmin(), e[i].aabb.ymin(), e[i].aabb.zmax()));
    elements_AABB.back().emplace_back(
        IK::Point_3(e[i].aabb.xmin(), e[i].aabb.ymax(), e[i].aabb.zmax()));
    elements_AABB.back().emplace_back(
        IK::Point_3(e[i].aabb.xmin(), e[i].aabb.ymax(), e[i].aabb.zmin()));

    elements_AABB.back().emplace_back(
        IK::Point_3(e[i].aabb.xmax(), e[i].aabb.ymin(), e[i].aabb.zmin()));
    elements_AABB.back().emplace_back(
        IK::Point_3(e[i].aabb.xmax(), e[i].aabb.ymin(), e[i].aabb.zmax()));
    elements_AABB.back().emplace_back(
        IK::Point_3(e[i].aabb.xmax(), e[i].aabb.ymax(), e[i].aabb.zmax()));
    elements_AABB.back().emplace_back(
        IK::Point_3(e[i].aabb.xmax(), e[i].aabb.ymax(), e[i].aabb.zmin()));
  }

  //////////////////////////////////////////////////////////////////////////////
  // Output OOBB
  //////////////////////////////////////////////////////////////////////////////

  elements_OOBB.reserve(e.size());

  for (size_t i = 0; i < e.size(); i++) {
    elements_OOBB.emplace_back(std::vector<IK::Point_3>());
    elements_OOBB.back().reserve(8);

    CGAL_Polyline corners;
    internal::get_corners(e[i].oob, corners);

    for (int j = 0; j < 8; j++) {
      elements_OOBB.back().emplace_back(corners[j]);
    }
  }
}

void get_connection_zones(
    // input
    std::vector<std::vector<IK::Point_3>> &input_polyline_pairs,
    std::vector<std::vector<IK::Vector_3>> &input_insertion_vectors,
    std::vector<std::vector<int>> &input_joint_types,
    std::vector<std::vector<int>>
        &input_three_valence_element_indices_and_instruction,
    std::vector<int> &input_adjacency,
    std::vector<double> &input_joint_parameters_and_types,
    int &input_search_type, std::vector<double> &input_scale,
    int &input_output_type,
    // output
    std::vector<std::vector<std::vector<IK::Point_3>>> &output_plines,
    std::vector<std::vector<wood::cut::cut_type>> &output_types,
    // global_parameters
    std::vector<double> &input_joint_volume_parameters
    // std::vector<std::vector<IK::Point_3>>& input_custom_joints,
    // std::vector<int>& input_custom_joints_types
) {

  wood::GLOBALS::JOINTS_PARAMETERS_AND_TYPES = input_joint_parameters_and_types;
  wood::GLOBALS::OUTPUT_GEOMETRY_TYPE = input_output_type;

  if (input_joint_volume_parameters.size() > 2)
    wood::GLOBALS::JOINT_VOLUME_EXTENSION = input_joint_volume_parameters;

  // // wood::GLOBALS::FACE_TO_FACE_SIDE_TO_SIDE_JOINTS_ALL_TREATED_AS_ROTATED =
  // input_face_to_face_side_to_side_joints_all_treated_as_rotated;
  // // wood::GLOBALS::FACE_TO_FACE_SIDE_TO_SIDE_JOINTS_ROTATED_JOINT_AS_AVERAGE
  // = input_face_to_face_side_to_side_joints_rotated_joint_as_average;

  // //9
  // wood::GLOBALS::CUSTOM_JOINTS_SS_E_IP_MALE.clear();
  // wood::GLOBALS::CUSTOM_JOINTS_SS_E_IP_FEMALE.clear();
  // //19
  // wood::GLOBALS::CUSTOM_JOINTS_SS_E_OP_MALE.clear();
  // wood::GLOBALS::CUSTOM_JOINTS_SS_E_OP_FEMALE.clear();
  // //29
  // wood::GLOBALS::CUSTOM_JOINTS_TS_E_P_MALE.clear();
  // wood::GLOBALS::CUSTOM_JOINTS_TS_E_P_FEMALE.clear();
  // //39
  // wood::GLOBALS::CUSTOM_JOINTS_CR_C_IP_MALE.clear();
  // wood::GLOBALS::CUSTOM_JOINTS_CR_C_IP_FEMALE.clear();
  // //49
  // wood::GLOBALS::CUSTOM_JOINTS_TT_E_P_MALE.clear();
  // wood::GLOBALS::CUSTOM_JOINTS_TT_E_P_FEMALE.clear();
  // //59
  // wood::GLOBALS::CUSTOM_JOINTS_SS_E_R_MALE.clear();
  // wood::GLOBALS::CUSTOM_JOINTS_SS_E_R_FEMALE.clear();
  // //69
  // wood::GLOBALS::CUSTOM_JOINTS_B_MALE.clear();
  // wood::GLOBALS::CUSTOM_JOINTS_B_FEMALE.clear();

  // if (input_custom_joints.size() == input_custom_joints_types.size()) {
  //     for (int i = 0; i < input_custom_joints.size(); i++) {

  //         switch (input_custom_joints_types[i])
  //         {
  //         case (9):
  //             wood::GLOBALS::CUSTOM_JOINTS_SS_E_IP_MALE.emplace_back(input_custom_joints[i]);
  //             break;
  //         case (-9):
  //             wood::GLOBALS::CUSTOM_JOINTS_SS_E_IP_FEMALE.emplace_back(input_custom_joints[i]);
  //             break;
  //         case (19):
  //             wood::GLOBALS::CUSTOM_JOINTS_SS_E_OP_MALE.emplace_back(input_custom_joints[i]);
  //             break;
  //         case (-19):
  //             wood::GLOBALS::CUSTOM_JOINTS_SS_E_OP_FEMALE.emplace_back(input_custom_joints[i]);
  //             break;
  //         case (29):
  //             wood::GLOBALS::CUSTOM_JOINTS_TS_E_P_MALE.emplace_back(input_custom_joints[i]);
  //             break;
  //         case (-29):
  //             wood::GLOBALS::CUSTOM_JOINTS_TS_E_P_FEMALE.emplace_back(input_custom_joints[i]);
  //             break;
  //         case (39):
  //             wood::GLOBALS::CUSTOM_JOINTS_CR_C_IP_MALE.emplace_back(input_custom_joints[i]);
  //             break;
  //         case (-39):
  //             wood::GLOBALS::CUSTOM_JOINTS_CR_C_IP_FEMALE.emplace_back(input_custom_joints[i]);
  //             break;
  //         case (49):
  //             wood::GLOBALS::CUSTOM_JOINTS_TT_E_P_MALE.emplace_back(input_custom_joints[i]);
  //             break;
  //         case (-49):
  //             wood::GLOBALS::CUSTOM_JOINTS_TT_E_P_FEMALE.emplace_back(input_custom_joints[i]);
  //             break;
  //         case (59):
  //             wood::GLOBALS::CUSTOM_JOINTS_SS_E_R_MALE.emplace_back(input_custom_joints[i]);
  //             break;
  //         case (-59):
  //             wood::GLOBALS::CUSTOM_JOINTS_SS_E_R_FEMALE.emplace_back(input_custom_joints[i]);
  //             break;
  //         case (69):
  //             wood::GLOBALS::CUSTOM_JOINTS_B_MALE.emplace_back(input_custom_joints[i]);
  //             break;
  //         case (-69):
  //             wood::GLOBALS::CUSTOM_JOINTS_B_FEMALE.emplace_back(input_custom_joints[i]);
  //             break;

  //         default:
  //             break;
  //         }

  //     }
  // }

  ////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
  // Main Method of Wood
  ////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
  std::vector<std::vector<int>> top_face_triangulation;

  wood::main::get_connection_zones(
      // input
      input_polyline_pairs, input_insertion_vectors, input_joint_types,
      input_three_valence_element_indices_and_instruction, input_adjacency,
      // output
      output_plines, output_types, top_face_triangulation,
      // Global Parameters
      wood::GLOBALS::JOINTS_PARAMETERS_AND_TYPES, input_scale,
      input_search_type, wood::GLOBALS::OUTPUT_GEOMETRY_TYPE, 0);
}

void test() {
  printf("\n___________________________________________________________________"
         "_____\n");
  printf("\n_______________________Hello from CPP "
         "Wood______________________________\n");
  printf("\n___If you see this message, say hi to the developer Petras "
         "Vestartas ___\n");
  printf("\n____________________petrasvestartas@gmail.com______________________"
         "_____\n");
  printf("\n___________________________________________________________________"
         "_____\n");
}

void read_xml_polylines(
    std::string &foldername, std::string &filename_of_dataset,
    std::vector<std::vector<double>> &polylines_coordinates) {
  // set file paths
  wood::GLOBALS::DATA_SET_INPUT_FOLDER =
      foldername; // =
                  // "C:\\IBOIS57\\_Code\\Software\\Python\\compas_wood\\frontend\\src\\wood\\dataset\\";
  wood::xml::path_and_file_for_input_polylines =
      wood::GLOBALS::DATA_SET_INPUT_FOLDER + filename_of_dataset + ".xml";

  // print the user given values
  printf("User given values \n");
  printf("%s", foldername.c_str());
  printf("\n");
  printf("%s", filename_of_dataset.c_str());
  printf("\n");
  printf("%s", wood::xml::path_and_file_for_input_polylines.c_str());
  printf("\n");

  // read the xml file
  wood::xml::read_xml_polylines(polylines_coordinates, false, true);
}

void read_xml_polylines_and_properties(
    std::string &foldername, std::string &filename_of_dataset,
    std::vector<std::vector<double>> &input_polyline_pairs_coord,
    std::vector<std::vector<double>> &input_insertion_vectors_coord,
    std::vector<std::vector<int>> &input_joints_types,
    std::vector<std::vector<int>>
        &input_three_valence_element_indices_and_instruction,
    std::vector<int> &input_adjacency) {

  // set file paths
  wood::GLOBALS::DATA_SET_INPUT_FOLDER =
      foldername; // =
                  // "C:\\IBOIS57\\_Code\\Software\\Python\\compas_wood\\frontend\\src\\wood\\dataset\\";
  wood::xml::path_and_file_for_input_polylines =
      wood::GLOBALS::DATA_SET_INPUT_FOLDER + filename_of_dataset + ".xml";

  // print the user given values
  printf("User given values \n");
  printf("%s", foldername.c_str());
  printf("\n");
  printf("%s", filename_of_dataset.c_str());
  printf("\n");
  printf("%s", wood::xml::path_and_file_for_input_polylines.c_str());
  printf("\n");
  // read the xml file
  wood::xml::read_xml_polylines_and_properties(
      input_polyline_pairs_coord, input_insertion_vectors_coord,
      input_joints_types, input_three_valence_element_indices_and_instruction,
      input_adjacency, false, true);

  printf("\n input_polyline_pairs_coord ");
  printf("%s", std::to_string(input_polyline_pairs_coord.size()).c_str());
  printf("\n input_insertion_vectors_coord ");
  printf("%s", std::to_string(input_insertion_vectors_coord.size()).c_str());
  printf("\n input_joints_types ");
  printf("%s", std::to_string(input_joints_types.size()).c_str());
  printf("\n input_three_valence_element_indices_and_instruction ");
  printf("%s", std::to_string(
                   input_three_valence_element_indices_and_instruction.size())
                   .c_str());
  printf("\n input_adjacency ");
  printf("%s", std::to_string(input_adjacency.size()).c_str());
  printf("\n");
}

void closed_mesh_from_polylines(
    std::vector<std::vector<IK::Point_3>> &vector_of_polyline,
    std::vector<IK::Point_3> &out_vertices,
    std::vector<IK::Vector_3> &out_normals,
    std::vector<std::vector<int>> &out_triangles) {

  std::vector<double> flat_out_vertices;
  std::vector<double> flat_out_normals;
  std::vector<int> flat_out_triangles;
  cgal::polyline_mesh_util::closed_mesh_from_polylines_vnf(
      vector_of_polyline, flat_out_vertices, flat_out_normals,
      flat_out_triangles, 1);

  out_vertices.reserve(flat_out_vertices.size() / 3);
  out_normals.reserve(flat_out_normals.size() / 3);
  out_triangles.reserve(flat_out_triangles.size() / 3);

  for (size_t i = 0; i < flat_out_vertices.size(); i += 3)
    out_vertices.emplace_back(IK::Point_3(flat_out_vertices[i],
                                          flat_out_vertices[i + 1],
                                          flat_out_vertices[i + 2]));

  for (size_t i = 0; i < flat_out_normals.size(); i += 3)
    out_normals.emplace_back(IK::Vector_3(
        flat_out_normals[i], flat_out_normals[i + 1], flat_out_normals[i + 2]));

  for (size_t i = 0; i < flat_out_triangles.size(); i += 3)
    out_triangles.emplace_back(std::vector<int>{flat_out_triangles[i],
                                                flat_out_triangles[i + 1],
                                                flat_out_triangles[i + 2]});
}

void joints(std::vector<std::vector<IK::Point_3>> &input_polyline_pairs,
            int &search_type, std::vector<std::vector<int>> &element_pairs,
            std::vector<std::vector<IK::Point_3>> &joint_areas,
            std::vector<int> &joint_types) {

  //////////////////////////////////////////////////////////////////////////////
  // Create elements, AABB, OBB, P, Pls, thickness
  //////////////////////////////////////////////////////////////////////////////
  const int n = input_polyline_pairs.size() * 0.5;
  std::vector<wood::element> elements;
  std::vector<std::vector<IK::Vector_3>> input_insertion_vectors;
  std::vector<std::vector<int>> input_joint_types;
  wood::main::get_elements(input_polyline_pairs, input_insertion_vectors,
                           input_joint_types, elements);

  //////////////////////////////////////////////////////////////////////////////
  // Create joints, Perform Joint Area Search
  //////////////////////////////////////////////////////////////////////////////
  auto joints = std::vector<wood::joint>();
  auto joints_map = std::unordered_map<uint64_t, int>();
  std::vector<int> neighbors;
  wood::main::adjacency_search(elements, search_type, neighbors, joints,
                               joints_map);

  //////////////////////////////////////////////////////////////////////////////
  // Get element pairs, joint areas, joint types
  //////////////////////////////////////////////////////////////////////////////
  element_pairs.reserve(joints.size() * 3);
  joint_areas.reserve(joints.size());
  joint_types.reserve(joints.size());

  for (size_t i = 0; i < joints.size(); i++) {
    // element pairs and faces ids
    element_pairs.emplace_back(
        std::vector<int>{joints[i].v0, joints[i].v1, joints[i].f0_0,
                         joints[i].f1_0, joints[i].f0_1, joints[i].f1_1});

    // joint areas
    joint_areas.emplace_back(joints[i].joint_area);

    // joint types
    joint_types.emplace_back(joints[i].type);
  }
}

/////////////////////////////////////////////////////////////////////////////////////////////////
// NB_MODULE
/////////////////////////////////////////////////////////////////////////////////////////////////
void bind_wood_nano_types(nb::module_ &m) {

  /////////////////////////////////////////////////////////////////////////////////////////////////
  // Types - int
  /////////////////////////////////////////////////////////////////////////////////////////////////
  nb::bind_vector<std::vector<int>>(m, "int1");
  nb::bind_vector<std::vector<std::vector<int>>>(m, "int2");
  nb::bind_vector<std::vector<std::vector<std::vector<int>>>>(m, "int3");
  nb::bind_vector<std::vector<std::vector<std::vector<std::vector<int>>>>>(
      m, "int4");

  /////////////////////////////////////////////////////////////////////////////////////////////////
  // Types - double
  /////////////////////////////////////////////////////////////////////////////////////////////////
  nb::bind_vector<std::vector<double>>(m, "double1");
  nb::bind_vector<std::vector<std::vector<double>>>(m, "double2");
  nb::bind_vector<std::vector<std::vector<std::vector<double>>>>(m, "double3");
  nb::bind_vector<std::vector<std::vector<std::vector<std::vector<double>>>>>(
      m, "double4");

  /////////////////////////////////////////////////////////////////////////////////////////////////
  // Types - bool
  /////////////////////////////////////////////////////////////////////////////////////////////////
  nb::bind_vector<std::vector<bool>>(m, "bool1");

  /////////////////////////////////////////////////////////////////////////////////////////////////
  // Types - string
  /////////////////////////////////////////////////////////////////////////////////////////////////
  nb::bind_vector<std::vector<std::string>>(m, "string1");

  /////////////////////////////////////////////////////////////////////////////////////////////////
  // Types - point
  /////////////////////////////////////////////////////////////////////////////////////////////////
  nb::class_<IK::Point_3>(m, "point")
      .def(nb::init<double, double, double>())
      .def("x", &IK::Point_3::x)
      .def("y", &IK::Point_3::y)
      .def("z", &IK::Point_3::z)
      .def("__getitem__", [](const IK::Point_3 &p, size_t i) {
        if (i == 0)
          return p.x();
        if (i == 1)
          return p.y();
        if (i == 2)
          return p.z();
        throw std::out_of_range(
            "Index should be 0, 1, or 2 for x, y, z respectively");
      });

  nb::bind_vector<std::vector<IK::Point_3>>(m, "point1");
  nb::bind_vector<std::vector<std::vector<IK::Point_3>>>(m, "point2");
  nb::bind_vector<std::vector<std::vector<std::vector<IK::Point_3>>>>(m,
                                                                      "point3");
  nb::bind_vector<
      std::vector<std::vector<std::vector<std::vector<IK::Point_3>>>>>(
      m, "point4");

  /////////////////////////////////////////////////////////////////////////////////////////////////
  // Types - vector
  /////////////////////////////////////////////////////////////////////////////////////////////////

  nb::class_<IK::Vector_3>(m, "vector")
      .def(nb::init<double, double, double>())
      .def("x", &IK::Vector_3::x)
      .def("y", &IK::Vector_3::y)
      .def("z", &IK::Vector_3::z)
      .def("__getitem__", [](const IK::Vector_3 &p, size_t i) {
        if (i == 0)
          return p.x();
        if (i == 1)
          return p.y();
        if (i == 2)
          return p.z();
        throw std::out_of_range(
            "Index should be 0, 1, or 2 for x, y, z respectively");
      });

  nb::bind_vector<std::vector<IK::Vector_3>>(m, "vector1");
  nb::bind_vector<std::vector<std::vector<IK::Vector_3>>>(m, "vector2");
  nb::bind_vector<std::vector<std::vector<std::vector<IK::Vector_3>>>>(
      m, "vector3");
  nb::bind_vector<
      std::vector<std::vector<std::vector<std::vector<IK::Vector_3>>>>>(
      m, "vector4");

  /////////////////////////////////////////////////////////////////////////////////////////////////
  // Types - Enum classic
  /////////////////////////////////////////////////////////////////////////////////////////////////
  nb::enum_<wood::cut::cut_type>(m, "cut_type")
      .value("nothing", wood::cut::cut_type::nothing)
      .value("edge_insertion", wood::cut::cut_type::edge_insertion)
      .value("hole", wood::cut::cut_type::hole)
      .value("insert_between_multiple_edges",
             wood::cut::cut_type::insert_between_multiple_edges)
      .value("slice", wood::cut::cut_type::slice)
      .value("slice_projectsheer", wood::cut::cut_type::slice_projectsheer)
      .value("mill", wood::cut::cut_type::mill)
      .value("mill_project", wood::cut::cut_type::mill_project)
      .value("mill_projectsheer", wood::cut::cut_type::mill_projectsheer)
      .value("cut", wood::cut::cut_type::cut)
      .value("cut_project", wood::cut::cut_type::cut_project)
      .value("cut_projectsheer", wood::cut::cut_type::cut_projectsheer)
      .value("cut_reverse", wood::cut::cut_type::cut_reverse)
      .value("conic", wood::cut::cut_type::conic)
      .value("conic_reverse", wood::cut::cut_type::conic_reverse)
      .value("drill", wood::cut::cut_type::drill)
      .value("drill_50", wood::cut::cut_type::drill_50)
      .value("drill_10", wood::cut::cut_type::drill_10)
      .export_values();

  nb::class_<std::vector<wood::cut::cut_type>>(m, "cut_type1")
      .def(nb::init<>())
      .def("reserve", &std::vector<wood::cut::cut_type>::reserve)
      .def("__len__",
           [](const std::vector<wood::cut::cut_type> &v) { return v.size(); })
      .def("__getitem__",
           [](const std::vector<wood::cut::cut_type> &v, size_t i) {
             if (i < v.size())
               return v.at(i);
             throw std::out_of_range("Index out of range");
           })
      .def("emplace_back",
           [](std::vector<wood::cut::cut_type> &v,
              wood::cut::cut_type cut_type) { v.emplace_back(cut_type); });

  nb::class_<std::vector<std::vector<wood::cut::cut_type>>>(m, "cut_type2")
      .def(nb::init<>())
      .def("reserve", &std::vector<std::vector<wood::cut::cut_type>>::reserve)
      .def("__len__",
           [](const std::vector<std::vector<wood::cut::cut_type>> &v) {
             return v.size();
           })
      .def(
          "__getitem__",
          [](const std::vector<std::vector<wood::cut::cut_type>> &v, size_t i) {
            if (i < v.size())
              return v.at(i);
            throw std::out_of_range("Index out of range");
          })
      .def("emplace_back", [](std::vector<std::vector<wood::cut::cut_type>> &v,
                              const std::vector<wood::cut::cut_type> &p) {
        v.emplace_back(p);
      });

  nb::class_<wood::GLOBALS>(m, "GLOBALS")
      .def_rw_static("CLIPPER_SCALE", &wood::GLOBALS::CLIPPER_SCALE,
                     "Static property docstring")
      .def_rw_static("CLIPPER_AREA", &wood::GLOBALS::CLIPPER_AREA,
                     "Static property docstring")
      .def_rw_static("DISTANCE", &wood::GLOBALS::DISTANCE,
                     "Static property docstring")
      .def_rw_static("DISTANCE_SQUARED", &wood::GLOBALS::DISTANCE_SQUARED,
                     "Static property docstring")
      .def_rw_static("ANGLE", &wood::GLOBALS::ANGLE,
                     "Static property docstring")
      .def_rw_static("PATH_AND_FILE_FOR_JOINTS",
                     &wood::GLOBALS::PATH_AND_FILE_FOR_JOINTS,
                     "Static property docstring")
      .def_rw_static("DATA_SET_INPUT_FOLDER",
                     &wood::GLOBALS::DATA_SET_INPUT_FOLDER,
                     "Static property docstring")
      .def_rw_static("DATA_SET_OUTPUT_FILE",
                     &wood::GLOBALS::DATA_SET_OUTPUT_FILE,
                     "Static property docstring")
      .def_rw_static("DATA_SET_OUTPUT_DATABASE",
                     &wood::GLOBALS::DATA_SET_OUTPUT_DATABASE,
                     "Static property docstring")
      .def_rw_static("JOINT_VOLUME_EXTENSION",
                     &wood::GLOBALS::JOINT_VOLUME_EXTENSION,
                     "Static property docstring")
      .def_rw_static("OUTPUT_GEOMETRY_TYPE",
                     &wood::GLOBALS::OUTPUT_GEOMETRY_TYPE,
                     "Static property docstring")
      .def_rw_static(
          "FACE_TO_FACE_SIDE_TO_SIDE_JOINTS_ALL_TREATED_AS_ROTATED",
          &wood::GLOBALS::
              FACE_TO_FACE_SIDE_TO_SIDE_JOINTS_ALL_TREATED_AS_ROTATED,
          "Static property docstring")
      .def_rw_static(
          "FACE_TO_FACE_SIDE_TO_SIDE_JOINTS_ROTATED_JOINT_AS_AVERAGE",
          &wood::GLOBALS::
              FACE_TO_FACE_SIDE_TO_SIDE_JOINTS_ROTATED_JOINT_AS_AVERAGE,
          "Static property docstring")
      .def_rw_static(
          "FACE_TO_FACE_SIDE_TO_SIDE_JOINTS_DIHEDRAL_ANGLE",
          &wood::GLOBALS::FACE_TO_FACE_SIDE_TO_SIDE_JOINTS_DIHEDRAL_ANGLE,
          "Static property docstring")
      .def_rw_static("LIMIT_MIN_JOINT_LENGTH",
                     &wood::GLOBALS::LIMIT_MIN_JOINT_LENGTH,
                     "Static property docstring")
      .def_rw_static("EXISTING_TYPES", &wood::GLOBALS::EXISTING_TYPES,
                     "Static property docstring")
      .def_rw_static("JOINTS_PARAMETERS_AND_TYPES",
                     &wood::GLOBALS::JOINTS_PARAMETERS_AND_TYPES,
                     "Static property docstring")
      .def_rw_static("CUSTOM_JOINTS_SS_E_IP_MALE",
                     &wood::GLOBALS::CUSTOM_JOINTS_SS_E_IP_MALE,
                     "Static property docstring")
      .def_rw_static("CUSTOM_JOINTS_SS_E_IP_FEMALE",
                     &wood::GLOBALS::CUSTOM_JOINTS_SS_E_IP_FEMALE,
                     "Static property docstring")
      .def_rw_static("CUSTOM_JOINTS_SS_E_OP_MALE",
                     &wood::GLOBALS::CUSTOM_JOINTS_SS_E_OP_MALE,
                     "Static property docstring")
      .def_rw_static("CUSTOM_JOINTS_SS_E_OP_FEMALE",
                     &wood::GLOBALS::CUSTOM_JOINTS_SS_E_OP_FEMALE,
                     "Static property docstring")
      .def_rw_static("CUSTOM_JOINTS_TS_E_P_MALE",
                     &wood::GLOBALS::CUSTOM_JOINTS_TS_E_P_MALE,
                     "Static property docstring")
      .def_rw_static("CUSTOM_JOINTS_TS_E_P_FEMALE",
                     &wood::GLOBALS::CUSTOM_JOINTS_TS_E_P_FEMALE,
                     "Static property docstring")
      .def_rw_static("CUSTOM_JOINTS_CR_C_IP_MALE",
                     &wood::GLOBALS::CUSTOM_JOINTS_CR_C_IP_MALE,
                     "Static property docstring")
      .def_rw_static("CUSTOM_JOINTS_CR_C_IP_FEMALE",
                     &wood::GLOBALS::CUSTOM_JOINTS_CR_C_IP_FEMALE,
                     "Static property docstring")
      .def_rw_static("CUSTOM_JOINTS_TT_E_P_MALE",
                     &wood::GLOBALS::CUSTOM_JOINTS_TT_E_P_MALE,
                     "Static property docstring")
      .def_rw_static("CUSTOM_JOINTS_TT_E_P_FEMALE",
                     &wood::GLOBALS::CUSTOM_JOINTS_TT_E_P_FEMALE,
                     "Static property docstring")
      .def_rw_static("CUSTOM_JOINTS_SS_E_R_MALE",
                     &wood::GLOBALS::CUSTOM_JOINTS_SS_E_R_MALE,
                     "Static property docstring")
      .def_rw_static("CUSTOM_JOINTS_SS_E_R_FEMALE",
                     &wood::GLOBALS::CUSTOM_JOINTS_SS_E_R_FEMALE,
                     "Static property docstring")
      .def_rw_static("CUSTOM_JOINTS_B_MALE",
                     &wood::GLOBALS::CUSTOM_JOINTS_B_MALE,
                     "Static property docstring")
      .def_rw_static("CUSTOM_JOINTS_B_FEMALE",
                     &wood::GLOBALS::CUSTOM_JOINTS_B_FEMALE,
                     "Static property docstring")
      .def_rw_static("RUN_COUNT", &wood::GLOBALS::RUN_COUNT,
                     "Static property docstring");

  /////////////////////////////////////////////////////////////////////////////////////////////////
  // Types - array
  /////////////////////////////////////////////////////////////////////////////////////////////////
  // nb::bind_vector<std::vector<bool>>(m, "bool1");
  // nb::bind_array<std::array<int, 4>>(m, "array_4_int");
  // nb::bind_array<std::array<IK::Point_3, 2>>(m, "array_2_point");
  // nb::bind_array<std::array<std::vector<IK::Point_3>, 4>>(m,
  // "array_4_vector_point"); nb::bind_vector<std::vector<IK::Point_3>>(m,
  // "point1"); m.def("array_out", [](){ return std::array<int, 3>{1, 2, 3}; });
  // m.def("array_4_int", [](std::array<int, 4> x) { return x[0] + x[1] + x[2];
  // });
  //     std::vector<std::array<int, 4>>
  //     &polyline0_id_segment0_id_polyline1_id_segment1_id,
  //     std::vector<std::array<IK::Point_3, 2>> &point_pairs,
  //     std::vector<std::array<std::vector<IK::Point_3>, 4>> &volume_pairs,
}

/**
 * @brief NB_MODULE macro to define the <wood_nano_ext> module.
 * The second <m> names a variable of type nanobind::module_ that represents the
 * created module.
 */
NB_MODULE(wood_nano_ext, m) {

  bind_wood_nano_types(m);

  /////////////////////////////////////////////////////////////////////////////////////////////////
  // Methods point
  /////////////////////////////////////////////////////////////////////////////////////////////////

  m.def("add", &add, "a"_a, "b"_a = 1, "This function adds two integers.");

  m.attr("version") = "0.1.0";

  m.doc() = "This is a module for wood library.";

  m.def("inspect", [](nb::ndarray<> a) {
    printf("Array data pointer : %p\n", a.data());
    printf("Array dimension : %zu\n", a.ndim());
    for (size_t i = 0; i < a.ndim(); ++i) {
      printf("Array dimension [%zu] : %zu\n", i, a.shape(i));
      printf("Array stride    [%zu] : %zd\n", i, a.stride(i));
    }
    printf("Device ID = %u (cpu=%i, cuda=%i)\n", a.device_id(),
           int(a.device_type() == nb::device::cpu::value),
           int(a.device_type() == nb::device::cuda::value));
    printf("Array dtype: int16=%i, uint32=%i, float32=%i\n",
           a.dtype() == nb::dtype<int16_t>(),
           a.dtype() == nb::dtype<uint32_t>(), a.dtype() == nb::dtype<float>());
  });

  m.def("middle_point", &middle_point, "a"_a, "b"_a,
        "This functions gets average of two points.");

  m.def("rtree", &rtree, "input_polyline_pairs"_a, "elements_neighbours"_a,
        "elements_AABB"_a, "elements_OOBB"_a,
        "This function runs RTree from polyline pairs to get collision pairs.");

  m.def("get_connection_zones", &get_connection_zones, "input_polyline_pairs"_a,
        "input_insertion_vectors"_a, "input_joint_types"_a,
        "input_three_valence_element_indices_and_instruction"_a,
        "input_adjacency"_a, "input_joint_parameters_and_types"_a,
        "input_search_type"_a, "input_scale"_a, "input_output_type"_a,
        "output_plines"_a, "output_types"_a, "input_joint_volume_parameters"_a,
        // "input_custom_joints"_a,
        // "input_custom_joints_types"_a,
        "This function gets connection zones.");

  m.def("test", &test, "This function prints a test message.");

  m.def("read_xml_polylines", &read_xml_polylines, "foldername"_a,
        "filename_of_dataset"_a, "polylines_coordinates"_a,
        "This function reads xml polylines.");

  m.def("read_xml_polylines_and_properties", &read_xml_polylines_and_properties,
        "foldername"_a, "filename_of_dataset"_a, "input_polyline_pairs_coord"_a,
        "input_insertion_vectors_coord"_a, "input_joints_types"_a,
        "input_three_valence_element_indices_and_instruction"_a,
        "input_adjacency"_a,
        "This function reads xml polylines and properties.");

  m.def("closed_mesh_from_polylines", &closed_mesh_from_polylines,
        "vector_of_polyline"_a, "out_vertices"_a, "out_normals"_a,
        "out_triangles"_a,
        "This function creates a closed mesh from polylines.");

  m.def("joints", &joints, "input_polyline_pairs"_a, "search_type"_a,
        "element_pairs"_a, "joint_areas"_a, "joint_types"_a,
        "This function gets joints.");

  m.attr("joint_parameters_and_types") =
      wood::GLOBALS::JOINTS_PARAMETERS_AND_TYPES;

  m.def("mesh_boolean_difference_from_polylines",
        &cgal::mesh_boolean::mesh_boolean_difference_from_polylines,
        "input_plines"_a, "output_plines"_a, "out_vertices"_a, "out_normals"_a,
        "out_triangles"_a,
        "This function creates a mesh boolean difference from polylines.");

  m.def("beam_volumes", &wood::main::beam_volumes, "polylines"_a,
        "polylines_segment_radii"_a, "polylines_segment_direction"_a,
        "allowed_types"_a, "min_distance"_a, "volume_length"_a,
        "cross_or_side_to_end"_a, "flip_male"_a, "index_polylines"_a,
        "index_polylines_segment"_a, "distance"_a, "point_pairs"_a,
        "volume_pairs"_a, "joints_areas"_a, "joints_types"_a, "output_plines"_a,
        "output_types"_a, "compute_joints"_a, "division_distance"_a, "shift"_a,
        "output_type"_a, "use_eccentricities_to_scale_joints"_a,
        "This function computes beam volumes.");

  m.def("mesh_skeleton",
       static_cast<void(*)(std::vector<double>&, std::vector<int>&, std::vector<CGAL_Polyline>&)>(&cgal::skeleton::mesh_skeleton),
      "v"_a, "f"_a, "output_polylines"_a,
      "This function creates a skeleton from a closed triangular mesh.");

  m.def("beam_skeleton",
      &cgal::skeleton::beam_skeleton,
      "v"_a, "f"_a, "output_polyline"_a, "output_distances"_a, "divisions"_a, "nearest_neighbors"_a, "extend"_a,
      "This function creates a skeleton from a closed triangular mesh that looks like a beam, that can be approximated by one axis.");



        // /**
        //  * @brief Run the skeleton extraction algorithm.
        //  * @param v The vertices.
        //  * @param f The faces.
        //  * @param output_polylines The output vector of polylines.
        //  * @param output_mesh OPTIONAL: The output CGAL polyhedron.
        //  */
        // void mesh_skeleton(std::vector<float>& v, std::vector<int>& f, std::vector<CGAL_Polyline>& output_polylines, CGAL::Polyhedron_3<CK>* output_mesh = nullptr);


  // /**
  //        * @brief Run the beam skeleton extraction algorithm.
  //        * @param v The vertices.
  //        * @param f The faces.
  //        * @param divisions The number of points to generate along the polylines.
  //        * @param nearest_neighbors The number of nearest neighbors to consider for each point in the polyline.
  //        * @param extend Whether to extend the polyline to the mesh.
  //        * @param output_polyline The output polyline.
  //        * @param output_distances The output vector to store the distances corresponding to the output polyline.
  //        */
  //       void beam_skeleton(std::vector<float>& v, std::vector<int>& f, CGAL_Polyline& output_polyline, std::vector<float>& output_distances, int divisions=0, int nearest_neighbors=0, bool extend=false);

	// cgal::skeleton::run(v, f, output_mesh, output_polylines);
	// cgal::skeleton::divide_polyline(output_polylines, 10, output_polyline);
	// cgal::skeleton::find_nearest_mesh_distances(output_mesh, output_polyline, 10, output_distances);
	// cgal::skeleton::extend_polyline_to_mesh(output_mesh, output_polyline, output_distances);
}