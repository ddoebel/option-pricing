add_library(qengine_core
        Instrument.cpp
        Instrument.hpp
        Payoff.cpp
        Payoff.hpp
        Option.cpp
        Option.hpp
        PricingEngine.cpp
        PricingEngine.hpp
        MonteCarloEngine.cpp
        MonteCarloEngine.hpp
        StochasticProcess.cpp
        StochasticProcess.hpp
        Exercise.cpp
        Exercise.hpp
        MarketData.cpp
        MarketData.hpp
        YieldCurve.cpp
        YieldCurve.hpp
        VolatilitySurface.cpp
        VolatilitySurface.hpp
        RandomGenerator.cpp
        RandomGenerator.hpp
        Statistics.cpp
        Statistics.hpp
        BlackScholesClosedFormEngine.cpp
        BlackScholesClosedFormEngine.hpp
        BlackScholesProcess.cpp
        BlackScholesProcess.hpp
        DBIngest.cpp
        DBIngest.hpp
        BSWrapper.cpp
        BSWrapper.hpp
        NewtonSolver.cpp
        NewtonSolver.hpp
)

target_include_directories(qengine_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_include_directories(qengine_core PRIVATE
        /opt/homebrew/include
)

find_library(PQXX_LIB pqxx PATHS /opt/homebrew/lib /usr/local/lib /usr/lib)
find_library(PQ_LIB pq PATHS /opt/homebrew/opt/libpq/lib /opt/homebrew/lib /usr/local/lib /usr/lib)
if(NOT PQXX_LIB OR NOT PQ_LIB)
    message(FATAL_ERROR "Could not find libpqxx and/or libpq (install via Homebrew: brew install libpqxx libpq)")
endif()

target_link_libraries(qengine_core Eigen3::Eigen)
target_link_libraries(qengine_core ${PQXX_LIB} ${PQ_LIB})

# Python import path: package qengine, extension submodule qengine (file qengine/qengine*.so)
pybind11_add_module(qengine_cpp MODULE ImpliedVolatility/Pybind.cpp)
set_target_properties(qengine_cpp PROPERTIES OUTPUT_NAME qengine)
target_link_libraries(qengine_cpp PRIVATE qengine_core)

# Place the module next to qengine/__init__.py so `import qengine` works from the repo root
set(_qengine_py_pkg "${CMAKE_SOURCE_DIR}/qengine")
set_target_properties(qengine_cpp PROPERTIES
        LIBRARY_OUTPUT_DIRECTORY "${_qengine_py_pkg}"
        LIBRARY_OUTPUT_DIRECTORY_RELEASE "${_qengine_py_pkg}"
        LIBRARY_OUTPUT_DIRECTORY_DEBUG "${_qengine_py_pkg}"
        RUNTIME_OUTPUT_DIRECTORY "${_qengine_py_pkg}"
        RUNTIME_OUTPUT_DIRECTORY_RELEASE "${_qengine_py_pkg}"
        RUNTIME_OUTPUT_DIRECTORY_DEBUG "${_qengine_py_pkg}")
