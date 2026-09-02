cmake_minimum_required(VERSION 3.22)
project(wood_nano LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_BUILD_TYPE Release CACHE STRING "" FORCE)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
# Required on Linux: session_core OBJECT library is linked into Python .so
# extensions, so all compilation units must be position-independent.
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# FetchContent_Populate is deprecated since CMake 3.30 / 4.0 (policy CMP0169).
# We rely on it intentionally to separate "download" from "configure": `wood` is
# consumed as SOURCES ONLY and must never be add_subdirectory'd (its CMakeLists has
# local-only paths), which _MakeAvailable would do immediately. Silence the dev
# warning explicitly.
#
# It also used to be needed to copy session_cpp's generated protobufs into place
# before add_subdirectory saw them; session_cpp now finds its own, so that reason is
# gone but the `wood` one stands.
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
        GIT_SUBMODULES ""
        GIT_SUBMODULES_RECURSE FALSE
    )
    FetchContent_GetProperties(wood)
    if(NOT wood_POPULATED)
        FetchContent_Populate(wood)
    endif()
    set(WOOD_DIR "${wood_SOURCE_DIR}")
endif()

# ── session_cpp ──────────────────────────────────────────────────────────────
# Where the kernel comes from. First hit wins, same order as wood/CMakeLists.txt:
#
#   1. -DSESSION_CPP_LOCAL=<dir> (a CACHE PATH, so the command line actually takes;
#      a plain set() used to shadow it and the value was silently discarded), or
#      the SESSION_CPP_LOCAL environment variable
#   2. ../session_cpp next to this repo - a checkout, or a symlink to one. This is
#      the wood_project layout (see ../README.md): wood and wood_nano compile the
#      SAME kernel checkout, so `git pull` there updates both, and the two can
#      never disagree about what an Element is.
#   3. a fresh FetchContent clone of GitHub main (CI, wheels)
#
# Use FetchContent_Populate (not _MakeAvailable) so the clone is only a source
# directory here and add_subdirectory happens below, once, for whichever candidate won.
set(SESSION_CPP_LOCAL "" CACHE PATH
    "Local session_cpp checkout; ../session_cpp or a GitHub clone when empty")
set(SESSION_CPP_DIR "")
foreach(_candidate IN ITEMS
        "${SESSION_CPP_LOCAL}"
        "$ENV{SESSION_CPP_LOCAL}"
        "${CMAKE_CURRENT_SOURCE_DIR}/../session_cpp"
        "C:/pc/3_code/code_rust/session/session_cpp")
    if(NOT "${_candidate}" STREQUAL "" AND EXISTS "${_candidate}/CMakeLists.txt")
        get_filename_component(SESSION_CPP_DIR "${_candidate}" REALPATH)
        break()
    endif()
endforeach()
if(SESSION_CPP_DIR)
    message(STATUS "wood_nano: using local session_cpp at ${SESSION_CPP_DIR}")
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
    message(STATUS "wood_nano: fetched session_cpp to ${SESSION_CPP_DIR}")
endif()

# No generated/ mirror here any more.
#
# session_cpp used to locate its own protobuf sources through CMAKE_SOURCE_DIR, which
# under add_subdirectory() is THIS project rather than session_cpp - so every consumer
# had to copy session_cpp/generated into its own root just to be found. session_cpp now
# anchors those paths to its own directory (SESSION_CPP_ROOT), so the copy is obsolete.
#
# Deleting it also removes the failure it caused. file(COPY) preserves timestamps, so a
# regenerated element.pb.h could land here OLDER than the objects already compiled
# against the previous one; the build then linked two different layouts of
# session_proto::Element together and corrupted the heap at runtime. The local checkout
# dodged it via a symlink; CI and any fresh clone copied for real. There is now one copy
# of the generated sources, in session_cpp, and nothing to go stale.

add_subdirectory(${SESSION_CPP_DIR} session_cpp EXCLUDE_FROM_ALL)

# ── nanobind modules ─────────────────────────────────────────────────────────
# When building inside a virtualenv (uv-managed Python, etc.) CMake's FindPython
# does not search the base Python installation by default.  Derive the root from
# the executing interpreter so it finds Python.h and the import library.
# Also clear any stale library cache entries so a version switch (e.g. 3.14→3.12)
# doesn't leave the cache pointing at the wrong Python.
if(DEFINED Python_EXECUTABLE)
    execute_process(
        COMMAND "${Python_EXECUTABLE}" -c "import sys; print(sys.base_prefix)"
        OUTPUT_VARIABLE _python_base_prefix
        OUTPUT_STRIP_TRAILING_WHITESPACE
        ERROR_QUIET
    )
    if(_python_base_prefix)
        set(Python_ROOT_DIR  "${_python_base_prefix}" CACHE PATH "" FORCE)
        set(Python3_ROOT_DIR "${_python_base_prefix}" CACHE PATH "" FORCE)
        # Clear stale internal cache entries from previous Python versions.
        foreach(_v
            Python_LIBRARY        Python_SABI_LIBRARY
            Python3_LIBRARY       Python3_SABI_LIBRARY
            _Python_LIBRARY_RELEASE          _Python_SABI_LIBRARY_RELEASE
            _Python_RUNTIME_LIBRARY_RELEASE  _Python_RUNTIME_SABI_LIBRARY_RELEASE
            FIND_PACKAGE_MESSAGE_DETAILS_Python
        )
            unset(${_v} CACHE)
        endforeach()

        # Everything below describes the WINDOWS Python layout - "Include" with a
        # capital I, and import libraries under "libs". Forcing those paths on
        # every platform is why the Linux and macOS wheels never built: on
        # manylinux the headers live in include/python3.12, so
        # Python_INCLUDE_DIR was FORCEd to a directory that does not exist and
        # find_package stopped with
        #   Could NOT find Python (missing: Development.Module
        #   Development.SABIModule) ... Cannot find the directory
        #   "/opt/python/cp312-cp312/Include"
        # Python_ROOT_DIR above is enough for FindPython everywhere else; only
        # Windows needs the explicit hand-holding, because a virtualenv there
        # has no registry entry for FindPython to fall back on.
        if(WIN32)
            set(Python_INCLUDE_DIR "${_python_base_prefix}/Include" CACHE PATH "" FORCE)
            # Versioned import lib (e.g. python313.lib) — needed for Development.Module
            file(GLOB _pylib "${_python_base_prefix}/libs/python3[0-9][0-9].lib"
                             "${_python_base_prefix}/libs/python3[0-9].lib")
            if(_pylib)
                list(GET _pylib 0 _pylib)
                set(Python_LIBRARY "${_pylib}" CACHE PATH "" FORCE)
            endif()
            # Stable ABI import lib (python3.lib) — needed for Development.SABIModule
            if(EXISTS "${_python_base_prefix}/libs/python3.lib")
                set(Python_SABI_LIBRARY "${_python_base_prefix}/libs/python3.lib" CACHE PATH "" FORCE)
            endif()
        endif()
    endif()
endif()
# ── Provenance stamp ─────────────────────────────────────────────────────────
# All three repos float on `main` (wood and session_cpp are resolved to a
# local checkout or FetchContent HEAD), so two wheels built a day apart can
# embed different kernels with the same wood_nano version. Stamp the resolved
# SHAs into the package so a wheel can always say what it was built from:
#   >>> wood_nano.__wood_sha__, wood_nano.__session_sha__
# The file is generated, gitignored, and falls back to "unknown" at import.
find_package(Git QUIET)
set(_wood_sha "unknown")
set(_session_sha "unknown")
if(GIT_FOUND)
    # --dirty matters: a local build against uncommitted kernel changes must
    # not masquerade as the commit it diverged from.
    execute_process(COMMAND "${GIT_EXECUTABLE}" -C "${WOOD_DIR}" describe --always --dirty --abbrev=12
                    OUTPUT_VARIABLE _wood_sha OUTPUT_STRIP_TRAILING_WHITESPACE ERROR_QUIET)
    execute_process(COMMAND "${GIT_EXECUTABLE}" -C "${SESSION_CPP_DIR}" describe --always --dirty --abbrev=12
                    OUTPUT_VARIABLE _session_sha OUTPUT_STRIP_TRAILING_WHITESPACE ERROR_QUIET)
    if(NOT _wood_sha)
        set(_wood_sha "unknown")
    endif()
    if(NOT _session_sha)
        set(_session_sha "unknown")
    endif()
endif()
file(WRITE "${CMAKE_SOURCE_DIR}/src/wood_nano/_build_info.py"
     "# Generated at configure time - do not edit, do not commit.
"
     "WOOD_SHA = \"${_wood_sha}\"
"
     "SESSION_SHA = \"${_session_sha}\"
")
message(STATUS "Provenance: wood=${_wood_sha} session_cpp=${_session_sha}")

find_package(Python 3.9 REQUIRED COMPONENTS Interpreter Development.Module Development.SABIModule)
find_package(nanobind CONFIG REQUIRED)

# NOMINSIZE on every module: nanobind otherwise applies /Os (favor SIZE) to
# ALL module sources in Release, and _joinery_solver compiles the entire wood
# joinery kernel as module sources - the shipped wheels were running the
# whole detection/merge pipeline optimized for size. NOMINSIZE restores the
# compiler's normal Release optimization for exactly the code users pay for.
# (nanobind's LTO flag is deliberately NOT used: session_core is a separate
# OBJECT library built without /GL, so cross-TU inlining across that boundary
# needs a session_cpp build change first - tracked as a follow-up.)

set(WOOD_INCLUDES
    ${SESSION_CPP_DIR}
    ${WOOD_DIR}
    ${WOOD_DIR}/src
    ${WOOD_DIR}/src/joinery_solver
    ${WOOD_DIR}/src/templates
)

# _wood_element — registers WoodElement once; imported by all other modules
nanobind_add_module(_wood_element STABLE_ABI NB_STATIC NOMINSIZE
    src/_wood_element.cpp
    ${WOOD_DIR}/src/joinery_solver/wood_element.cpp
)
target_include_directories(_wood_element PRIVATE ${WOOD_INCLUDES})
target_link_libraries(_wood_element PRIVATE session_core)
LINK_PROTOBUF(_wood_element)

# _translation_shell — imports _wood_element for the shared WoodElement type
nanobind_add_module(_translation_shell STABLE_ABI NB_STATIC NOMINSIZE
    src/_translation_shell.cpp
    ${WOOD_DIR}/src/joinery_solver/wood_element.cpp
)
target_include_directories(_translation_shell PRIVATE ${WOOD_INCLUDES})
target_link_libraries(_translation_shell PRIVATE session_core)
LINK_PROTOBUF(_translation_shell)

# _reflex_fold — imports _wood_element for the shared WoodElement type
nanobind_add_module(_reflex_fold STABLE_ABI NB_STATIC NOMINSIZE
    src/_reflex_fold.cpp
    ${WOOD_DIR}/src/joinery_solver/wood_element.cpp
)
target_include_directories(_reflex_fold PRIVATE ${WOOD_INCLUDES})
target_link_libraries(_reflex_fold PRIVATE session_core)
LINK_PROTOBUF(_reflex_fold)

# _chevron — imports _wood_element for the shared WoodElement type
nanobind_add_module(_chevron STABLE_ABI NB_STATIC NOMINSIZE
    src/_chevron.cpp
    ${WOOD_DIR}/src/joinery_solver/wood_element.cpp
)
target_include_directories(_chevron PRIVATE ${WOOD_INCLUDES})
target_link_libraries(_chevron PRIVATE session_core)
LINK_PROTOBUF(_chevron)

# _reciprocal_rotation — rotation-based nexorade.
# Reciprocal used to live in session_cpp (src/reciprocal.{h,cpp}) and arrived
# through session_core. session_cpp deleted it in d53654ad, finishing the move
# begun in 37f49ed9 ("move ... main_reciprocal to wood project") which had only
# taken the main. It now lives in wood/src/templates/reciprocal.h, header-only
# like every other template there, so it needs no source entry.
nanobind_add_module(_reciprocal_rotation STABLE_ABI NB_STATIC NOMINSIZE
    src/_reciprocal_rotation.cpp
)
target_include_directories(_reciprocal_rotation PRIVATE ${WOOD_INCLUDES})
target_link_libraries(_reciprocal_rotation PRIVATE session_core)
LINK_PROTOBUF(_reciprocal_rotation)

# _reciprocal_move — translation-based nexorade; uses session_core geometry only
nanobind_add_module(_reciprocal_move STABLE_ABI NB_STATIC NOMINSIZE
    src/_reciprocal_move.cpp
)
target_include_directories(_reciprocal_move PRIVATE ${WOOD_INCLUDES})
target_link_libraries(_reciprocal_move PRIVATE session_core)
LINK_PROTOBUF(_reciprocal_move)

# _diamond_mesh — imports _wood_element for WoodElement plates
nanobind_add_module(_diamond_mesh STABLE_ABI NB_STATIC NOMINSIZE
    src/_diamond_mesh.cpp
    ${WOOD_DIR}/src/joinery_solver/wood_element.cpp
)
target_include_directories(_diamond_mesh PRIVATE ${WOOD_INCLUDES})
target_link_libraries(_diamond_mesh PRIVATE session_core)
LINK_PROTOBUF(_diamond_mesh)

# _connectors — mesh-to-plates-and-connectors (no WoodElement dependency)
nanobind_add_module(_connectors STABLE_ABI NB_STATIC NOMINSIZE
    src/_connectors.cpp
)
target_include_directories(_connectors PRIVATE ${WOOD_INCLUDES})
target_link_libraries(_connectors PRIVATE session_core)
LINK_PROTOBUF(_connectors)

# _assign_vectors — edge matching and insertion-vector computation for the Rhino solvers
nanobind_add_module(_assign_vectors STABLE_ABI NB_STATIC NOMINSIZE
    src/_assign_vectors.cpp
)
target_include_directories(_assign_vectors PRIVATE ${WOOD_INCLUDES})
target_link_libraries(_assign_vectors PRIVATE session_core)
LINK_PROTOBUF(_assign_vectors)

# _datasets — JSON dataset loader (converts XML-derived flat JSON to bottom/top polyline lists)
# nlohmann/json is header-only; include its path directly to avoid pulling in session_core.
nanobind_add_module(_datasets STABLE_ABI NB_STATIC NOMINSIZE
    src/_datasets.cpp
)
target_include_directories(_datasets PRIVATE
    ${WOOD_INCLUDES}
    ${SESSION_CPP_DIR}/src/json/include
)

# _joinery_solver — cross-joint detection + merge pipeline
# Compiles the full wood joinery kernel alongside the nanobind binding. joint
# geometry headers (joints/*.h) are header-only. Clipper2 does the 2D boolean in
# wood_face_to_face.cpp's face_overlap_area; it ships inside session_cpp but
# session_core does not compile it, so its three translation units are listed
# here exactly as wood/CMakeLists.txt lists them for wood_core.
nanobind_add_module(_joinery_solver STABLE_ABI NB_STATIC NOMINSIZE
    src/_joinery_solver.cpp
    ${SESSION_CPP_DIR}/src/clipper2/clipper.engine.cpp
    ${SESSION_CPP_DIR}/src/clipper2/clipper.offset.cpp
    ${SESSION_CPP_DIR}/src/clipper2/clipper.rectclip.cpp
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
    target_compile_options(_assign_vectors    PRIVATE /W3 /utf-8)
    target_compile_options(_datasets          PRIVATE /W3 /utf-8)
    target_compile_options(_joinery_solver    PRIVATE /W3 /utf-8)
endif()

install(TARGETS
    _wood_element _translation_shell _reflex_fold _chevron
    _reciprocal_rotation _reciprocal_move
    _diamond_mesh _connectors _assign_vectors _datasets _joinery_solver
    LIBRARY DESTINATION wood_nano)

install(FILES "${CMAKE_SOURCE_DIR}/src/wood_nano/data/annen_surfaces.json"
    DESTINATION wood_nano/data)
