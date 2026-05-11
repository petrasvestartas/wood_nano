cmake_minimum_required(VERSION 3.22)
project(wood_nano LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_BUILD_TYPE Release CACHE STRING "" FORCE)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# FetchContent_Populate is deprecated since CMake 3.30 / 4.0 (policy CMP0169).
# We rely on it intentionally to separate "download" from "configure" so we can
# copy generated protobuf files into CMAKE_SOURCE_DIR before add_subdirectory
# processes session_cpp. Silence the dev warning explicitly.
cmake_policy(SET CMP0169 OLD)
include(FetchContent)

# ── wood ─────────────────────────────────────────────────────────────────────
# Use local checkout if present, otherwise download from GitHub (CI).
# We only need the source files — do NOT add_subdirectory(wood) because
# wood's CMakeLists.txt has local-only paths.
set(WOOD_LOCAL "${CMAKE_CURRENT_SOURCE_DIR}/../wood")
if(EXISTS "${WOOD_LOCAL}/src/joinery_solver/wood_main.cpp")
    set(WOOD_DIR "${WOOD_LOCAL}")
else()
    FetchContent_Declare(wood
        GIT_REPOSITORY https://github.com/petrasvestartas/wood.git
        GIT_TAG        main
        GIT_SHALLOW    TRUE
    )
    FetchContent_GetProperties(wood)
    if(NOT wood_POPULATED)
        FetchContent_Populate(wood)
    endif()
    set(WOOD_DIR "${wood_SOURCE_DIR}")
endif()

# ── session_cpp ──────────────────────────────────────────────────────────────
# Use local checkout if present, otherwise download from GitHub (CI).
# Use FetchContent_Populate (not _MakeAvailable) so we can copy the generated
# protobuf files into CMAKE_SOURCE_DIR BEFORE add_subdirectory configures it.
# _MakeAvailable calls add_subdirectory immediately, before the copy step runs.
set(SESSION_CPP_LOCAL "C:/pc/3_code/code_rust/session/session_cpp")
if(EXISTS "${SESSION_CPP_LOCAL}/CMakeLists.txt")
    set(SESSION_CPP_DIR "${SESSION_CPP_LOCAL}")
else()
    FetchContent_Declare(session_cpp
        GIT_REPOSITORY https://github.com/petrasvestartas/session_cpp.git
        GIT_TAG        main
        GIT_SHALLOW    TRUE
    )
    FetchContent_GetProperties(session_cpp)
    if(NOT session_cpp_POPULATED)
        FetchContent_Populate(session_cpp)
    endif()
    set(SESSION_CPP_DIR "${session_cpp_SOURCE_DIR}")
endif()

# session_cpp's CMakeLists uses CMAKE_SOURCE_DIR to locate generated/.
# When session_cpp is fetched, CMAKE_SOURCE_DIR = wood_nano root (not session_cpp).
# Copy the committed generated files there before add_subdirectory runs.
if(NOT EXISTS "${CMAKE_SOURCE_DIR}/generated")
    message(STATUS "Copying session_cpp/generated into ${CMAKE_SOURCE_DIR}/generated")
    file(COPY "${SESSION_CPP_DIR}/generated" DESTINATION "${CMAKE_SOURCE_DIR}")
endif()

add_subdirectory(${SESSION_CPP_DIR} session_cpp EXCLUDE_FROM_ALL)

# ── nanobind modules ─────────────────────────────────────────────────────────
find_package(Python 3.9 REQUIRED COMPONENTS Interpreter Development.Module Development.SABIModule)
find_package(nanobind CONFIG REQUIRED)

set(WOOD_INCLUDES
    ${SESSION_CPP_DIR}
    ${WOOD_DIR}
    ${WOOD_DIR}/src
    ${WOOD_DIR}/src/joinery_solver
    ${WOOD_DIR}/src/templates
)

# _wood_element — registers WoodElement once; imported by all other modules
nanobind_add_module(_wood_element STABLE_ABI NB_STATIC
    src/_wood_element.cpp
    ${WOOD_DIR}/src/joinery_solver/wood_element.cpp
)
target_include_directories(_wood_element PRIVATE ${WOOD_INCLUDES})
target_link_libraries(_wood_element PRIVATE session_core)
LINK_PROTOBUF(_wood_element)

# _translation_shell — imports _wood_element for the shared WoodElement type
nanobind_add_module(_translation_shell STABLE_ABI NB_STATIC
    src/_translation_shell.cpp
    ${WOOD_DIR}/src/joinery_solver/wood_element.cpp
)
target_include_directories(_translation_shell PRIVATE ${WOOD_INCLUDES})
target_link_libraries(_translation_shell PRIVATE session_core)
LINK_PROTOBUF(_translation_shell)

# _reflex_fold — imports _wood_element for the shared WoodElement type
nanobind_add_module(_reflex_fold STABLE_ABI NB_STATIC
    src/_reflex_fold.cpp
    ${WOOD_DIR}/src/joinery_solver/wood_element.cpp
)
target_include_directories(_reflex_fold PRIVATE ${WOOD_INCLUDES})
target_link_libraries(_reflex_fold PRIVATE session_core)
LINK_PROTOBUF(_reflex_fold)

# _chevron — imports _wood_element for the shared WoodElement type
nanobind_add_module(_chevron STABLE_ABI NB_STATIC
    src/_chevron.cpp
    ${WOOD_DIR}/src/joinery_solver/wood_element.cpp
)
target_include_directories(_chevron PRIVATE ${WOOD_INCLUDES})
target_link_libraries(_chevron PRIVATE session_core)
LINK_PROTOBUF(_chevron)

# _reciprocal_rotation — rotation-based nexorade; uses session_core Reciprocal + Intersection
nanobind_add_module(_reciprocal_rotation STABLE_ABI NB_STATIC
    src/_reciprocal_rotation.cpp
)
target_include_directories(_reciprocal_rotation PRIVATE ${WOOD_INCLUDES})
target_link_libraries(_reciprocal_rotation PRIVATE session_core)
LINK_PROTOBUF(_reciprocal_rotation)

# _reciprocal_move — translation-based nexorade; uses session_core geometry only
nanobind_add_module(_reciprocal_move STABLE_ABI NB_STATIC
    src/_reciprocal_move.cpp
)
target_include_directories(_reciprocal_move PRIVATE ${WOOD_INCLUDES})
target_link_libraries(_reciprocal_move PRIVATE session_core)
LINK_PROTOBUF(_reciprocal_move)

# _diamond_mesh — imports _wood_element for WoodElement plates
nanobind_add_module(_diamond_mesh STABLE_ABI NB_STATIC
    src/_diamond_mesh.cpp
    ${WOOD_DIR}/src/joinery_solver/wood_element.cpp
)
target_include_directories(_diamond_mesh PRIVATE ${WOOD_INCLUDES})
target_link_libraries(_diamond_mesh PRIVATE session_core)
LINK_PROTOBUF(_diamond_mesh)

# _connectors — mesh-to-plates-and-connectors (no WoodElement dependency)
nanobind_add_module(_connectors STABLE_ABI NB_STATIC
    src/_connectors.cpp
)
target_include_directories(_connectors PRIVATE ${WOOD_INCLUDES})
target_link_libraries(_connectors PRIVATE session_core)
LINK_PROTOBUF(_connectors)

# _joinery_solver — cross-joint detection + merge pipeline
# Compiles the full wood joinery kernel (8 translation units) alongside the
# nanobind binding.  joint geometry headers (joints/*.h) are header-only.
nanobind_add_module(_joinery_solver STABLE_ABI NB_STATIC
    src/_joinery_solver.cpp
    ${WOOD_DIR}/src/joinery_solver/wood_element.cpp
    ${WOOD_DIR}/src/joinery_solver/wood_main.cpp
    ${WOOD_DIR}/src/joinery_solver/wood_merge.cpp
    ${WOOD_DIR}/src/joinery_solver/wood_joint.cpp
    ${WOOD_DIR}/src/joinery_solver/wood_joint_detection.cpp
    ${WOOD_DIR}/src/joinery_solver/wood_face_to_face.cpp
    ${WOOD_DIR}/src/joinery_solver/wood_assign.cpp
    ${WOOD_DIR}/src/joinery_solver/wood_globals.cpp
    ${WOOD_DIR}/src/joinery_solver/wood_internal.cpp
    ${WOOD_DIR}/src/joinery_solver/wood_beams.cpp
)
target_include_directories(_joinery_solver PRIVATE ${WOOD_INCLUDES})
target_link_libraries(_joinery_solver PRIVATE session_core)
LINK_PROTOBUF(_joinery_solver)

if(MSVC)
    target_compile_options(_wood_element      PRIVATE /W3 /utf-8)
    target_compile_options(_translation_shell PRIVATE /W3 /utf-8)
    target_compile_options(_reflex_fold       PRIVATE /W3 /utf-8)
    target_compile_options(_chevron           PRIVATE /W3 /utf-8)
    target_compile_options(_reciprocal_rotation PRIVATE /W3 /utf-8)
    target_compile_options(_reciprocal_move   PRIVATE /W3 /utf-8)
    target_compile_options(_diamond_mesh      PRIVATE /W3 /utf-8)
    target_compile_options(_connectors        PRIVATE /W3 /utf-8)
    target_compile_options(_joinery_solver    PRIVATE /W3 /utf-8)
endif()

install(TARGETS
    _wood_element _translation_shell _reflex_fold _chevron
    _reciprocal_rotation _reciprocal_move
    _diamond_mesh _connectors _joinery_solver
    LIBRARY DESTINATION wood_nano)
