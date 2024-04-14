/**
 * @file nanobind_binding.cpp
 * @brief This file contains the bindings for the wood_nano_ext module.
 */

// nanobind
#include <nanobind/nanobind.h>
#include <nanobind/stl/bind_vector.h>
#include <nanobind/ndarray.h>
#include <nanobind/stl/string.h>

// main header
#include "stdafx.h"
#include "wood_test.h" // test

// data structure
#include "wood_cut.h"
#include "wood_main.h"
#include "wood_element.h"

// joinery
#include "wood_joint_lib.h"
#include "wood_joint.h"

// geometry methods
#include "cgal_mesh_boolean.h"
#include "cgal_inscribe_util.h"
#include "cgal_rectangle_util.h"

namespace nb = nanobind;
using namespace nb::literals; // enables syntax for annotating function arguments

namespace internal
{
    IK::Point_3 point_at(IK::Vector_3(&box)[5], const double& s, const  double& t, const double& c)
    {
        return IK::Point_3(
            box[0].x() + s * box[1].x() + t * box[2].x() + c * box[3].x(),
            box[0].y() + s * box[1].y() + t * box[2].y() + c * box[3].y(),
            box[0].z() + s * box[1].z() + t * box[2].z() + c * box[3].z()

        );
    }

    void get_corners(IK::Vector_3(&box)[5], CGAL_Polyline& corners)
    {
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
}

/////////////////////////////////////////////////////////////////////////////////////////////////
// Global variables
/////////////////////////////////////////////////////////////////////////////////////////////////
int scale = 1e6;

/////////////////////////////////////////////////////////////////////////////////////////////////
// Add function
/////////////////////////////////////////////////////////////////////////////////////////////////
int add(int a, int b) {
    return a + b;

    wood::globals::DISTANCE = 0.1;
    wood::globals::DISTANCE_SQUARED = 0.01;
    wood::globals::ANGLE = 0.11;
    wood::globals::OUTPUT_GEOMETRY_TYPE = 3;
    wood::globals::DATA_SET_INPUT_FOLDER = std::filesystem::current_path().parent_path().string() + "/wood_nano/src/wood/cmake/src/wood/dataset/";
    wood::globals::DATA_SET_OUTPUT_FILE = wood::globals::DATA_SET_INPUT_FOLDER + "out.xml";
    wood::globals::DATA_SET_OUTPUT_DATABASE = wood::globals::DATA_SET_INPUT_FOLDER + "out.db";
    wood::globals::OUTPUT_GEOMETRY_TYPE = 3;
    // wood::test::type_plates_name_side_to_side_edge_inplane_hilti();
}

/////////////////////////////////////////////////////////////////////////////////////////////////
// CGAL Point_3 and Vector_3
/////////////////////////////////////////////////////////////////////////////////////////////////
IK::Point_3 middle_point(const IK::Point_3& a, const IK::Point_3& b) {
    return IK::Point_3((a.x() + b.x()) / 2, (a.y() + b.y()) / 2, (a.z() + b.z()) / 2);
}

void rtree(
    std::vector<std::vector<IK::Point_3>>& input_polyline_pairs,
    std::vector<std::vector<int>>& elements_neighbours,
    std::vector<std::vector<IK::Point_3>>& elements_AABB,
    std::vector<std::vector<IK::Point_3>>& elements_OOBB)
{

    //////////////////////////////////////////////////////////////////////////////
    // Convert raw-data to list of Polylines
    //////////////////////////////////////////////////////////////////////////////
    // std::vector<CGAL_Polyline> input_polyline_pairs;
    // python_to_cpp__cpp_to_python::coord_to_vector_of_polylines(polylines_coordinates, input_polyline_pairs);

    //////////////////////////////////////////////////////////////////////////////
    // Create elements, AABB, OBB, P, Pls, thickness
    //////////////////////////////////////////////////////////////////////////////
    std::vector<wood::element> e;
    std::vector<std::vector<IK::Vector_3>> input_insertion_vectors;
    std::vector<std::vector<int>> input_joint_types;
    wood::main::get_elements(input_polyline_pairs, input_insertion_vectors, input_joint_types, e);

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

    for (size_t i = 0; i < e.size(); i++)
    {
        double min[3] = { e[i].aabb.xmin(), e[i].aabb.ymin(), e[i].aabb.zmin() };
        double max[3] = { e[i].aabb.xmax(), e[i].aabb.ymax(), e[i].aabb.zmax() };
        tree.Insert(min, max, i);
    }

    //////////////////////////////////////////////////////////////////////////////
    // Search Closest Boxes | Skip duplicates pairs | Perform callback with OBB
    //////////////////////////////////////////////////////////////////////////////
    elements_neighbours.reserve(e.size());

    for (size_t i = 0; i < e.size(); i++)
    {

        std::vector<int> element_neigbhours;

        auto callback = [&element_neigbhours, i, &e](int foundValue) -> bool
            {
                if (cgal::box_util::get_collision(e[i].oob, e[foundValue].oob))
                {
                    element_neigbhours.push_back(foundValue);
                }
                return true;
            };

        double min[3] = { e[i].aabb.xmin(), e[i].aabb.ymin(), e[i].aabb.zmin() };
        double max[3] = { e[i].aabb.xmax(), e[i].aabb.ymax(), e[i].aabb.zmax() };
        int nhits = tree.Search(min, max, callback); // callback in this method call callback above

        // Add elements to the vector
        elements_neighbours.emplace_back(std::vector<int>());

        for (int j = 0; j < element_neigbhours.size(); j++)
            elements_neighbours.back().emplace_back(element_neigbhours[j]);
    }

    //////////////////////////////////////////////////////////////////////////////
    // Output AABB
    //////////////////////////////////////////////////////////////////////////////
    elements_AABB.reserve(e.size());

    for (size_t i = 0; i < e.size(); i++)
    {

        elements_AABB.emplace_back(std::vector<IK::Point_3>());
        elements_AABB.back().reserve(8);

        elements_AABB.back().emplace_back(IK::Point_3(e[i].aabb.xmin(), e[i].aabb.ymin(), e[i].aabb.zmin()));
        elements_AABB.back().emplace_back(IK::Point_3(e[i].aabb.xmin(), e[i].aabb.ymin(), e[i].aabb.zmax()));
        elements_AABB.back().emplace_back(IK::Point_3(e[i].aabb.xmin(), e[i].aabb.ymax(), e[i].aabb.zmax()));
        elements_AABB.back().emplace_back(IK::Point_3(e[i].aabb.xmin(), e[i].aabb.ymax(), e[i].aabb.zmin()));

        elements_AABB.back().emplace_back(IK::Point_3(e[i].aabb.xmax(), e[i].aabb.ymin(), e[i].aabb.zmin()));
        elements_AABB.back().emplace_back(IK::Point_3(e[i].aabb.xmax(), e[i].aabb.ymin(), e[i].aabb.zmax()));
        elements_AABB.back().emplace_back(IK::Point_3(e[i].aabb.xmax(), e[i].aabb.ymax(), e[i].aabb.zmax()));
        elements_AABB.back().emplace_back(IK::Point_3(e[i].aabb.xmax(), e[i].aabb.ymax(), e[i].aabb.zmin()));

    }

    //////////////////////////////////////////////////////////////////////////////
    // Output OOBB
    //////////////////////////////////////////////////////////////////////////////

    elements_OOBB.reserve(e.size());

    for (size_t i = 0; i < e.size(); i++)
    {
        elements_OOBB.emplace_back(std::vector<IK::Point_3>());
        elements_OOBB.back().reserve(8);

        CGAL_Polyline corners;
        internal::get_corners(e[i].oob, corners);

        for (int j = 0; j < 8; j++)
        {
            elements_OOBB.back().emplace_back(corners[j]);
        }
    }
}


void get_connection_zones(
    // input
    std::vector<std::vector<IK::Point_3>>& input_polyline_pairs,
    std::vector<std::vector<IK::Vector_3>>& input_insertion_vectors,
    std::vector<std::vector<int>>& input_joint_types,
    std::vector<std::vector<int>>& input_three_valence_element_indices_and_instruction,
    std::vector<int>& input_adjacency,
    std::vector<double>& input_joint_parameters_and_types,
    int& input_search_type,
    std::vector<double>& input_scale,
    int& input_output_type,
    // output
    std::vector<std::vector<std::vector<IK::Point_3>>>& output_plines,
    std::vector<std::vector<wood::cut::cut_type>> &output_types,
    // global_parameters
    std::vector<double>& input_joint_volume_parameters,
    bool& face_to_face_side_to_side_joints_all_treated_as_rotated,
    std::vector<std::vector<IK::Point_3>>& input_custom_joints,
    std::vector<int>& input_custom_joints_types

)
{

    wood::globals::JOINTS_PARAMETERS_AND_TYPES = input_joint_parameters_and_types;
    wood::globals::OUTPUT_GEOMETRY_TYPE = input_output_type;

    if (input_joint_volume_parameters.size() > 2)
        wood::globals::JOINT_VOLUME_EXTENSION = input_joint_volume_parameters;

    wood::globals::FACE_TO_FACE_SIDE_TO_SIDE_JOINTS_ALL_TREATED_AS_ROTATED = face_to_face_side_to_side_joints_all_treated_as_rotated;


    //9
    wood::globals::custom_joints_ss_e_ip_male.clear();
    wood::globals::custom_joints_ss_e_ip_female.clear();
    //19
    wood::globals::custom_joints_ss_e_op_male.clear();
    wood::globals::custom_joints_ss_e_op_female.clear();
    //29
    wood::globals::custom_joints_ts_e_p_male.clear();
    wood::globals::custom_joints_ts_e_p_female.clear();
    //39
    wood::globals::custom_joints_cr_c_ip_male.clear();
    wood::globals::custom_joints_cr_c_ip_female.clear();
    //49
    wood::globals::custom_joints_tt_e_p_male.clear();
    wood::globals::custom_joints_tt_e_p_female.clear();
    //59
    wood::globals::custom_joints_ss_e_r_male.clear();
    wood::globals::custom_joints_ss_e_r_female.clear();
    //69
    wood::globals::custom_joints_b_male.clear();
    wood::globals::custom_joints_b_female.clear();


    if (input_custom_joints.size() == input_custom_joints_types.size()) {
        for (int i = 0; i < input_custom_joints.size(); i++) {

            switch (input_custom_joints_types[i])
            {
            case (9):
                wood::globals::custom_joints_ss_e_ip_male.emplace_back(input_custom_joints[i]);
                break;
            case (-9):
                wood::globals::custom_joints_ss_e_ip_female.emplace_back(input_custom_joints[i]);
                break;
            case (19):
                wood::globals::custom_joints_ss_e_op_male.emplace_back(input_custom_joints[i]);
                break;
            case (-19):
                wood::globals::custom_joints_ss_e_op_female.emplace_back(input_custom_joints[i]);
                break;
            case (29):
                wood::globals::custom_joints_ts_e_p_male.emplace_back(input_custom_joints[i]);
                break;
            case (-29):
                wood::globals::custom_joints_ts_e_p_female.emplace_back(input_custom_joints[i]);
                break;
            case (39):
                wood::globals::custom_joints_cr_c_ip_male.emplace_back(input_custom_joints[i]);
                break;
            case (-39):
                wood::globals::custom_joints_cr_c_ip_female.emplace_back(input_custom_joints[i]);
                break;
            case (49):
                wood::globals::custom_joints_tt_e_p_male.emplace_back(input_custom_joints[i]);
                break;
            case (-49):
                wood::globals::custom_joints_tt_e_p_female.emplace_back(input_custom_joints[i]);
                break;
            case (59):
                wood::globals::custom_joints_ss_e_r_male.emplace_back(input_custom_joints[i]);
                break;
            case (-59):
                wood::globals::custom_joints_ss_e_r_female.emplace_back(input_custom_joints[i]);
                break;
            case (69):
                wood::globals::custom_joints_b_male.emplace_back(input_custom_joints[i]);
                break;
            case (-69):
                wood::globals::custom_joints_b_female.emplace_back(input_custom_joints[i]);
                break;


            default:
                break;
            }

        }
    }


    ////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    // Main Method of Wood
    ////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    std::vector<std::vector<int>> top_face_triangulation;


    wood::main::get_connection_zones(
        // input
        input_polyline_pairs,
        input_insertion_vectors,
        input_joint_types,
        input_three_valence_element_indices_and_instruction,
        input_adjacency,
        // output
        output_plines,
        output_types,
        top_face_triangulation,
        // Global Parameters
        wood::globals::JOINTS_PARAMETERS_AND_TYPES,
        input_scale,
        input_search_type,
        wood::globals::OUTPUT_GEOMETRY_TYPE,
        0);

}

void test(){
    printf("\n________________________________________________________________________\n");
    printf("\n_______________________Hello from CPP Wood______________________________\n");
    printf("\n___If you see this message, say hi to the developer Petras Vestartas ___\n");
    printf("\n____________________petrasvestartas@gmail.com___________________________\n");
    printf("\n________________________________________________________________________\n");
}

void read_xml_polylines(
    std::string& foldername,
    std::string& filename_of_dataset, 
    std::vector<std::vector<double>>& polylines_coordinates
    )
{
    // set file paths
    wood::globals::DATA_SET_INPUT_FOLDER = foldername; // = "C:\\IBOIS57\\_Code\\Software\\Python\\compas_wood\\frontend\\src\\wood\\dataset\\";
    wood::xml::path_and_file_for_input_polylines = wood::globals::DATA_SET_INPUT_FOLDER + filename_of_dataset + ".xml";

    // print the user given values
    printf("User given values \n");
    printf(foldername.c_str());
    printf("\n");
    printf(filename_of_dataset.c_str());
    printf("\n");
    printf(wood::xml::path_and_file_for_input_polylines.c_str());
    printf("\n");

    // read the xml file
    wood::xml::read_xml_polylines(polylines_coordinates, false, true);
}

/////////////////////////////////////////////////////////////////////////////////////////////////
// NB_MODULE
/////////////////////////////////////////////////////////////////////////////////////////////////
void bind_wood_nano_types(nb::module_& m) {

    /////////////////////////////////////////////////////////////////////////////////////////////////
    // Types - int
    /////////////////////////////////////////////////////////////////////////////////////////////////
    nb::bind_vector<std::vector<int>>(m, "int1");
    nb::bind_vector<std::vector<std::vector<int>>>(m, "int2");
    nb::bind_vector<std::vector<std::vector<std::vector<int>>>>(m, "int3");
    nb::bind_vector<std::vector<std::vector<std::vector<std::vector<int>>>>>(m, "int4");

    /////////////////////////////////////////////////////////////////////////////////////////////////
    // Types - double
    /////////////////////////////////////////////////////////////////////////////////////////////////
    nb::bind_vector<std::vector<double>>(m, "double1");
    nb::bind_vector<std::vector<std::vector<double>>>(m, "double2");
    nb::bind_vector<std::vector<std::vector<std::vector<double>>>>(m, "double3");
    nb::bind_vector<std::vector<std::vector<std::vector<std::vector<double>>>>>(m, "double4");

    /////////////////////////////////////////////////////////////////////////////////////////////////
    // Types - bool
    /////////////////////////////////////////////////////////////////////////////////////////////////
    nb::bind_vector<std::vector<bool>>(m, "bool1");

    /////////////////////////////////////////////////////////////////////////////////////////////////
    // Types - point
    /////////////////////////////////////////////////////////////////////////////////////////////////
    nb::class_<IK::Point_3>(m, "point")
    .def(nb::init<double, double, double>())
    .def("x", &IK::Point_3::x)
    .def("y", &IK::Point_3::y)
    .def("z", &IK::Point_3::z)
    .def("__getitem__", [](const IK::Point_3& p, size_t i) {
    if (i == 0) return p.x();
    if (i == 1) return p.y();
    if (i == 2) return p.z();
    throw std::out_of_range("Index should be 0, 1, or 2 for x, y, z respectively");})
    ;

    nb::bind_vector<std::vector<IK::Point_3>>(m, "point1");
    nb::bind_vector<std::vector<std::vector<IK::Point_3>>>(m, "point2");
    nb::bind_vector<std::vector<std::vector<std::vector<IK::Point_3>>>>(m, "point3");
    nb::bind_vector<std::vector<std::vector<std::vector<std::vector<IK::Point_3>>>>>(m, "point4");

    /////////////////////////////////////////////////////////////////////////////////////////////////
    // Types - vector
    /////////////////////////////////////////////////////////////////////////////////////////////////

    nb::class_<IK::Vector_3>(m, "vector")
        .def(nb::init<double, double, double>())
        .def("x", &IK::Vector_3::x)
        .def("y", &IK::Vector_3::y)
        .def("z", &IK::Vector_3::z)
        .def("__getitem__", [](const IK::Vector_3& p, size_t i) {
            if (i == 0) return p.x();
            if (i == 1) return p.y();
            if (i == 2) return p.z();
            throw std::out_of_range("Index should be 0, 1, or 2 for x, y, z respectively");})    
        ;

    nb::bind_vector<std::vector<IK::Vector_3>>(m, "vector1");
    nb::bind_vector<std::vector<std::vector<IK::Vector_3>>>(m, "vector2");
    nb::bind_vector<std::vector<std::vector<std::vector<IK::Vector_3>>>>(m, "vector3");
    nb::bind_vector<std::vector<std::vector<std::vector<std::vector<IK::Vector_3>>>>>(m, "vector4");

    /////////////////////////////////////////////////////////////////////////////////////////////////
    // Types - Enum classic
    /////////////////////////////////////////////////////////////////////////////////////////////////
    nb::enum_<wood::cut::cut_type>(m, "cut_type")
        .value("nothing", wood::cut::cut_type::nothing)
        .value("edge_insertion", wood::cut::cut_type::edge_insertion)
        .value("hole", wood::cut::cut_type::hole)
        .value("insert_between_multiple_edges", wood::cut::cut_type::insert_between_multiple_edges)
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
        .def("__len__", [](const std::vector<wood::cut::cut_type>& v) { return v.size(); })
        .def("__getitem__", [](const std::vector<wood::cut::cut_type>& v, size_t i) {
            if (i < v.size()) return v.at(i);
            throw std::out_of_range("Index out of range");
        })
        .def("emplace_back", [](std::vector<wood::cut::cut_type>& v, wood::cut::cut_type cut_type) {
            v.emplace_back(cut_type);
        });

    nb::class_<std::vector<std::vector<wood::cut::cut_type>>>(m, "cut_type2")
        .def(nb::init<>())
        .def("reserve", &std::vector<std::vector<wood::cut::cut_type>>::reserve)
        .def("__len__", [](const std::vector<std::vector<wood::cut::cut_type>>& v) { return v.size(); })
        .def("__getitem__", [](const std::vector<std::vector<wood::cut::cut_type>>& v, size_t i) {
            if (i < v.size()) return v.at(i);
            throw std::out_of_range("Index out of range");
        })
        .def("emplace_back", [](std::vector<std::vector<wood::cut::cut_type>>& v, const std::vector<wood::cut::cut_type>& p) {
            v.emplace_back(p);
        });


}


/**
 * @brief NB_MODULE macro to define the <wood_nano_ext> module. 
 * The second <m> names a variable of type nanobind::module_ that represents the created module.
 */
NB_MODULE(wood_nano_ext, m) {

    bind_wood_nano_types(m);

    /////////////////////////////////////////////////////////////////////////////////////////////////
    // Methods point
    /////////////////////////////////////////////////////////////////////////////////////////////////

    m.def("add", &add, "a"_a, "b"_a=1, "This function adds two integers.");

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
            int(a.device_type() == nb::device::cuda::value)
        );
        printf("Array dtype: int16=%i, uint32=%i, float32=%i\n",
            a.dtype() == nb::dtype<int16_t>(),
            a.dtype() == nb::dtype<uint32_t>(),
            a.dtype() == nb::dtype<float>()
        );
    });

    m.def("middle_point", 
    &middle_point, 
    "a"_a, 
    "b"_a, 
    "This functions gets average of two points.");

    m.def("rtree", 
    &rtree, 
    "input_polyline_pairs"_a, 
    "elements_neighbours"_a, 
    "elements_AABB"_a, 
    "elements_OOBB"_a, 
    "This function runs RTree from polyline pairs to get collision pairs.");

    m.def("get_connection_zones", 
    &get_connection_zones, 
    "input_polyline_pairs"_a, 
    "input_insertion_vectors"_a, 
    "input_joint_types"_a, 
    "input_three_valence_element_indices_and_instruction"_a, 
    "input_adjacency"_a, 
    "input_joint_parameters_and_types"_a, 
    "input_search_type"_a, 
    "input_scale"_a, 
    "input_output_type"_a, 
    "output_plines"_a, 
    "output_types"_a, 
    "input_joint_volume_parameters"_a, 
    "face_to_face_side_to_side_joints_all_treated_as_rotated"_a, 
    "input_custom_joints"_a, 
    "input_custom_joints_types"_a, 
    "This function gets connection zones.");

    m.def("test", 
    &test, 
    "This function prints a test message.");

    m.def("read_xml_polylines", 
    &read_xml_polylines, 
    "foldername"_a, 
    "filename_of_dataset"_a, 
    "polylines_coordinates"_a, 
    "This function reads xml polylines.");


}
