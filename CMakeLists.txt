cmake_minimum_required(VERSION 3.16)
project(QuantEngine)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_FLAGS "-O3 -march=native")

find_package(Eigen3 REQUIRED)

add_subdirectory(src)

# Testing
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
        tests/stubs/FlatVolatilitySurface.cpp
        tests/stubs/FakeMarketData.cpp)

target_link_libraries(qengine_tests qengine GTest::gtest_main)
include(GoogleTest)
gtest_discover_tests(qengine_tests)