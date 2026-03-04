add_library(qengine
        models/black_scholes.cpp
        simulation/monte_carlo.cpp
        models/payoff.cpp
        main.cpp
        calibration/Stats.cpp
        calibration/Stats.hpp
)

target_include_directories(qengine PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(qengine Eigen3::Eigen)