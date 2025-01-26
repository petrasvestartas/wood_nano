cmake_minimum_required(VERSION 3.15...3.26)

set(CMAKE_BUILD_TYPE Release)
add_compile_options(-O3)  # Optimize the build

project(wood_nano LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(CGAL_CMAKE_EXACT_NT_BACKEND BOOST_BACKEND CACHE STRING "Set CGAL backend to Boost")
set(CGAL_DISABLE_GMP ON CACHE BOOL "Disable GMP in CGAL")
set(CMAKE_DISABLE_FIND_PACKAGE_GMP ON CACHE BOOL "Disable CMake find package for GMP")

list(APPEND CMAKE_PREFIX_PATH "${CMAKE_SOURCE_DIR}/src/wood/cmake/build/install/cgal")
list(APPEND CMAKE_PREFIX_PATH "${CMAKE_SOURCE_DIR}/src/wood/cmake/build/install/boost")
set(CGAL_DIR "${CMAKE_SOURCE_DIR}/src/wood/cmake/build/install/cgal/lib/cmake/CGAL")
find_package(CGAL REQUIRED)
find_package(Boost 1.72 REQUIRED)

# Platform-specific compiler options
if(MSVC)
    # MSVC specific flags
    # Modify runtime library configuration for static linking
    set(CompilerFlags
        CMAKE_CXX_FLAGS
        CMAKE_CXX_FLAGS_DEBUG
        CMAKE_CXX_FLAGS_RELEASE
        CMAKE_C_FLAGS
        CMAKE_C_FLAGS_DEBUG
        CMAKE_C_FLAGS_RELEASE
    )
    foreach(CompilerFlag ${CompilerFlags})
        string(REPLACE "/MD" "/MT" ${CompilerFlag} "${${CompilerFlag}}")
    endforeach()
elseif(CMAKE_COMPILER_IS_GNUCXX)
    # GCC specific flags for static linking
    # Note: This might be needed if you are fully working with static libraries
    set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -static-libstdc++ -static-libgcc")
    set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} -static-libstdc++ -static-libgcc")
endif()

if (NOT SKBUILD)
  message(WARNING "\
  This CMake file is meant to be executed using 'scikit-build'. Running
  it directly will almost certainly not produce the desired result. If
  you are a user trying to install this package, please use the command
  below, which will install all necessary build dependencies, compile
  the package in an isolated environment, and then install it.
  =====================================================================
   $ pip install .
  =====================================================================
  If you are a software developer, and this is your own package, then
  it is usually much more efficient to install the build dependencies
  in your environment once and use the following command that avoids
  a costly creation of a new virtual environment at every compilation:
  =====================================================================
   $ pip install nanobind scikit-build-core[pyproject]
   $ pip install --no-build-isolation -ve .
  =====================================================================
  You may optionally add -Ceditable.rebuild=true to auto-rebuild when
  the package is imported. Otherwise, you need to re-run the above
  after editing C++ files.")
endif()

# Try to import all Python components potentially needed by nanobind
find_package(Python 3.8
  REQUIRED COMPONENTS Interpreter Development.Module
  OPTIONAL_COMPONENTS Development.SABIModule)

# Import nanobind through CMake's find_package mechanism
find_package(nanobind CONFIG REQUIRED)

# run like this: export BUILDING_DIST="1" && python -m build && export BUILDING_DIST="1" && python -m build 
if(DEFINED ENV{BUILDING_DIST})
  if( (CMAKE_CXX_COMPILER_ID STREQUAL "GNU"))
    SET(CMAKE_SOURCE_DIR "$ENV{HOME}/brg/2_code/wood_nano")
    
  # elseif(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
  #   SET(CMAKE_SOURCE_DIR "C:/brg/2_code/wood_nano/")
  #   message("CMAKE_SOURCE_DIR: ${CMAKE_SOURCE_DIR}")
  endif()
endif()
message("CMAKE_SOURCE_DIR: ${CMAKE_SOURCE_DIR}")
# We are now ready to compile the actual extension module
nanobind_add_module(
  # Name of the extension
  wood_nano_ext

  # Target the stable ABI for Python 3.12+, which reduces
  # the number of binary wheels that must be built. This
  # does nothing on older Python versions
  STABLE_ABI

  # Build libnanobind statically and merge it into the
  # extension (which itself remains a shared library)
  #
  # If your project builds multiple extensions, you can
  # replace this flag by NB_SHARED to conserve space by
  # reusing a shared libnanobind across libraries
  NB_STATIC

  # Source code goes here
  "${CMAKE_SOURCE_DIR}/src/wood/cmake/stdafx.cpp"
  "${CMAKE_SOURCE_DIR}/src/wood/cmake/src/wood/include/wood_globals.cpp"
  "${CMAKE_SOURCE_DIR}/src/wood/cmake/src/wood/include/cgal_box_util.cpp"
  "${CMAKE_SOURCE_DIR}/src/wood/cmake/src/wood/include/rtree_util.cpp"
  "${CMAKE_SOURCE_DIR}/src/wood/cmake/src/wood/include/cgal_inscribe_util.cpp"
  "${CMAKE_SOURCE_DIR}/src/wood/cmake/src/wood/include/cgal_intersection_util.cpp"
  "${CMAKE_SOURCE_DIR}/src/wood/cmake/src/wood/include/cgal_xform_util.cpp"
  "${CMAKE_SOURCE_DIR}/src/wood/cmake/src/wood/include/cgal_math_util.cpp"
  "${CMAKE_SOURCE_DIR}/src/wood/cmake/src/wood/include/cgal_plane_util.cpp"
  "${CMAKE_SOURCE_DIR}/src/wood/cmake/src/wood/include/cgal_polyline_mesh_util.cpp"
  "${CMAKE_SOURCE_DIR}/src/wood/cmake/src/wood/include/cgal_polyline_util.cpp"
  "${CMAKE_SOURCE_DIR}/src/wood/cmake/src/wood/include/cgal_rectangle_util.cpp"
  "${CMAKE_SOURCE_DIR}/src/wood/cmake/src/wood/include/cgal_skeleton.cpp"
  "${CMAKE_SOURCE_DIR}/src/wood/cmake/src/wood/include/cgal_vector_util.cpp"
  "${CMAKE_SOURCE_DIR}/src/wood/cmake/src/wood/include/clipper_util.cpp"
  "${CMAKE_SOURCE_DIR}/src/wood/cmake/src/wood/include/wood_element.cpp"
  "${CMAKE_SOURCE_DIR}/src/wood/cmake/src/wood/include/wood_joint.cpp"
  "${CMAKE_SOURCE_DIR}/src/wood/cmake/src/wood/include/wood_joint_lib.cpp"
  "${CMAKE_SOURCE_DIR}/src/wood/cmake/src/wood/include/wood_test.cpp"
  "${CMAKE_SOURCE_DIR}/src/wood/cmake/src/wood/include/wood_main.cpp"
  "${CMAKE_SOURCE_DIR}/src/wood/cmake/src/wood/include/wood_xml.cpp"
  "${CMAKE_SOURCE_DIR}/src/wood/cmake/src/wood/include/cgal_mesh_boolean.cpp"
  "${CMAKE_SOURCE_DIR}/src/wood/cmake/src/wood/include/database_writer.cpp"
  "${CMAKE_SOURCE_DIR}/src/wood/cmake/src/wood/include/tinyply/tinyply.cpp"
  src/nanobind_binding.cpp

)

# headers
list(APPEND include_paths 
#my_code
"${CMAKE_SOURCE_DIR}/src/wood/cmake/"
"${CMAKE_SOURCE_DIR}/src/wood/cmake/src/wood/include/"
#cdt
"${CMAKE_SOURCE_DIR}/src/wood/cmake/build/install/cdt/CDT/include/"
#clipper
"${CMAKE_SOURCE_DIR}/src/wood/cmake/build/install/clipper_2/CPP/Clipper2Lib/include/"
#boost
"${CMAKE_SOURCE_DIR}/src/wood/cmake/build/install/boost/include/"
#eigen
"${CMAKE_SOURCE_DIR}/src/wood/cmake/build/install/eigen/"
#cgal
"${CMAKE_SOURCE_DIR}/src/wood/cmake/build/install/cgal/include"
#googletest
"${CMAKE_SOURCE_DIR}/src/wood/cmake/build/install/googletest/include/"
${CMAKE_BINARY_DIR}/install/googletest/lib/
# SQLite
"${CMAKE_SOURCE_DIR}/src/wood/cmake/src/sqlite/"
)

# if (WIN32) # append gmp to the list
#   list(APPEND include_paths "${CMAKE_SOURCE_DIR}/src/wood/cmake/build/install/cgal/auxiliary/gmp/include")
# endif()

target_include_directories(wood_nano_ext PUBLIC "$<BUILD_INTERFACE:${include_paths}>") #header for the library

# compiled static libraaries




if (WIN32)
  message("Windows")
  target_link_libraries(
  wood_nano_ext
  PUBLIC     
  ${CMAKE_SOURCE_DIR}/src/wood/cmake/build/Release/Clipper2.lib 
  # ${CMAKE_SOURCE_DIR}/src/wood/cmake/build/install/cgal/auxiliary/gmp/lib/libgmp-10.lib
  # ${CMAKE_SOURCE_DIR}/src/wood/cmake/build/install/cgal/auxiliary/gmp/lib/libmpfr-4.lib
  ${CMAKE_SOURCE_DIR}/src/wood/cmake/build/install/googletest/lib/gtest.lib
  ${CMAKE_SOURCE_DIR}/src/wood/cmake/build/install/googletest/lib/gmock.lib
  ${CMAKE_SOURCE_DIR}/src/wood/cmake/build/Release/sqlite3.lib
  CGAL::CGAL
  )

elseif(APPLE)
  message("Apple")
  target_link_libraries(
  wood_nano_ext
  PUBLIC     
  ${CMAKE_SOURCE_DIR}/src/wood/cmake/build/libClipper2.a 
  # /usr/local/lib/libgmp.a
  # /usr/local/lib/libmpfr.a
  ${CMAKE_SOURCE_DIR}/src/wood/cmake/build/install/googletest/lib/libgtest.a
  ${CMAKE_SOURCE_DIR}/src/wood/cmake/build/install/googletest/lib/libgmock.a
  ${CMAKE_SOURCE_DIR}/src/wood/cmake/build/libsqlite3.a
  CGAL::CGAL)
else()
  message("Linux")
  target_link_libraries(
  wood_nano_ext
  PUBLIC     
  ${CMAKE_SOURCE_DIR}/src/wood/cmake/build/libClipper2.a 
  # gmp
  # mpfr
  ${CMAKE_SOURCE_DIR}/src/wood/cmake/build/install/googletest/lib/libgtest.a
  ${CMAKE_SOURCE_DIR}/src/wood/cmake/build/install/googletest/lib/libgmock.a
  ${CMAKE_SOURCE_DIR}/src/wood/cmake/build/libsqlite3.a
  CGAL::CGAL)
endif()




# Install directive for scikit-build-core
install(TARGETS wood_nano_ext LIBRARY DESTINATION wood_nano)


###############################################################################
# PCH support
###############################################################################
target_precompile_headers(wood_nano_ext PRIVATE "${CMAKE_SOURCE_DIR}/src/wood/cmake/stdafx.h") # With PUBLIC they will be used by targets using this target

set(CMAKE_PCH_INSTANTIATE_TEMPLATES ON)


