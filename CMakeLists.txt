cmake_minimum_required(VERSION 3.22)
project(wood_nano LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_BUILD_TYPE Release CACHE STRING "" FORCE)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

set(WOOD_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../wood")

# ── session_cpp ──────────────────────────────────────────────────────────────
# Use local checkout if present, otherwise clone from GitHub.
set(SESSION_CPP_LOCAL "C:/pc/3_code/code_rust/session/session_cpp")
if(EXISTS "${SESSION_CPP_LOCAL}/CMakeLists.txt")
    set(SESSION_CPP_DIR "${SESSION_CPP_LOCAL}")
else()
    include(FetchContent)
    FetchContent_Declare(session_cpp
        GIT_REPOSITORY https://github.com/petrasvestartas/session_cpp.git
        GIT_TAG        main
        GIT_SHALLOW    TRUE
    )
    FetchContent_MakeAvailable(session_cpp)
    set(SESSION_CPP_DIR "${session_cpp_SOURCE_DIR}")
endif()

# session_cpp's CMakeLists uses CMAKE_SOURCE_DIR to locate generated/ which
# resolves to wood_nano's root when called as add_subdirectory.
# Create a symlink so it finds the committed generated files automatically.
if(NOT EXISTS "${CMAKE_SOURCE_DIR}/generated")
    file(CREATE_LINK "${SESSION_CPP_DIR}/generated" "${CMAKE_SOURCE_DIR}/generated" SYMBOLIC)
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

# _reciprocal_beam — no WoodElement; uses session_core Reciprocal + Intersection
nanobind_add_module(_reciprocal_beam STABLE_ABI NB_STATIC
    src/_reciprocal_beam.cpp
)
target_include_directories(_reciprocal_beam PRIVATE ${WOOD_INCLUDES})
target_link_libraries(_reciprocal_beam PRIVATE session_core)
LINK_PROTOBUF(_reciprocal_beam)

if(MSVC)
    target_compile_options(_wood_element      PRIVATE /W3 /utf-8)
    target_compile_options(_translation_shell PRIVATE /W3 /utf-8)
    target_compile_options(_reflex_fold       PRIVATE /W3 /utf-8)
    target_compile_options(_chevron           PRIVATE /W3 /utf-8)
    target_compile_options(_reciprocal_beam   PRIVATE /W3 /utf-8)
endif()

install(TARGETS
    _wood_element _translation_shell _reflex_fold _chevron _reciprocal_beam
    LIBRARY DESTINATION wood_nano)
