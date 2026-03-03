cmake_minimum_required(VERSION 3.16)
project(QuantEngine)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_FLAGS "-O3 -march=native")

find_package(Eigen3 REQUIRED)

add_subdirectory(src)

