add_library(qengine
        black_scholes.cpp
        monte_carlo.cpp
        payoff.cpp
        main.cpp
        Analytics.cpp
        Analytics.hpp
)

target_include_directories(qengine PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(qengine Eigen3::Eigen)