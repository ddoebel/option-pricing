add_library(qengine
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
        BlackScholesProcess.cpp
        BlackScholesProcess.hpp


)

target_include_directories(qengine PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(qengine Eigen3::Eigen)