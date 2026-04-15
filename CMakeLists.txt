cmake_minimum_required(VERSION 3.16)
project(QuantEngine)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_FLAGS "-O3 -march=native")

option(BUILD_TESTING "Build GoogleTest target and tests" ON)

set(PYBIND11_FINDPYTHON ON)
find_package(Python3 REQUIRED COMPONENTS Interpreter Development.Module)
find_package(Eigen3 REQUIRED)
find_package(pybind11 CONFIG REQUIRED)
#find_package(PostgreSQL REQUIRED)
#find_package(PkgConfig REQUIRED)
#pkg_check_modules(PQXX REQUIRED IMPORTED_TARGET libpqxx)

add_subdirectory(cpp)

find_package(Doxygen OPTIONAL_COMPONENTS dot)
if(DOXYGEN_FOUND)
    add_custom_target(
        docs
        COMMAND ${DOXYGEN_EXECUTABLE} ${CMAKE_SOURCE_DIR}/docs/Doxyfile
        WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
        COMMENT "Generating API documentation (HTML in docs/html)"
        VERBATIM)
endif()

install(FILES "${CMAKE_SOURCE_DIR}/qengine/__init__.py" DESTINATION qengine)
install(TARGETS qengine_cpp
        LIBRARY DESTINATION qengine
        RUNTIME DESTINATION qengine)

if(BUILD_TESTING)
    enable_testing()

    include(FetchContent)

    FetchContent_Declare(
            googletest
            URL https://github.com/google/googletest/archive/refs/tags/v1.14.0.zip
            DOWNLOAD_EXTRACT_TIMESTAMP TRUE
    )

    FetchContent_MakeAvailable(googletest)

    add_executable(qengine_tests
            tests/test_black_scholes.cpp
            tests/stubs/FlatYieldCurve.cpp
            tests/stubs/FlatVolatilitySurface.cpp)

    target_include_directories(qengine_tests PRIVATE ${CMAKE_SOURCE_DIR}/tests)
    target_link_libraries(qengine_tests qengine_core GTest::gtest_main)
    include(GoogleTest)
    gtest_discover_tests(qengine_tests)
endif()
