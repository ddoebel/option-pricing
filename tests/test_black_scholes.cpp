//
// Created by David Doebel  on 06.03.2026.
//

#include <gtest/gtest.h>
#include "BlackScholesProcess.hpp"
#include "MonteCarloEngine.hpp"
#include "Instrument.hpp"
#include "Option.hpp"
#include "Payoff.hpp"

#include "stubs/FlatYieldCurve.hpp"
#include "stubs/FlatVolatilitySurface.hpp"

TEST(BlackScholesProcess, ExpectedValue) {
    // Market setup (via test stubs): S0=100, r=1%, sigma=20%
    const double K = 100.0;
    const double T = 1.0;
    const int numPaths = 300000; // enough for stable MC estimate

    const MarketData marketData(
        100.0,
        std::make_shared<FlatYieldCurve>(0.01),
        std::make_shared<FlatVolatilitySurface>(0.2));

    // Build Black-Scholes process from an immutable market snapshot
    auto processCall = std::make_unique<BlackScholesProcess>(marketData);
    auto processPut  = std::make_unique<BlackScholesProcess>(marketData);

    // RNG shared between engines is fine
    auto rng = std::make_shared<MersenneTwister>();

    // Pricing engines
    auto mcCall = std::make_unique<MonteCarloEngine>(numPaths, std::move(processCall), rng);
    auto mcPut  = std::make_unique<MonteCarloEngine>(numPaths, std::move(processPut),  rng);

    // Instruments (European vanilla) with call and put payoffs
    Instrument callInstr(T, std::make_unique<CallPayoff>(K), std::move(mcCall));
    Instrument putInstr(T,  std::make_unique<PutPayoff>(K),  std::move(mcPut));

    const double callPrice = callInstr.price();
    const double putPrice  = putInstr.price();

    // Ground truth Black–Scholes prices provided
    const double callGT = 8.4333186901;
    const double putGT  = 7.4383020650;

    // Monte Carlo tolerance
    const double tol = 0.10; // 10 cents tolerance

    ASSERT_NEAR(callPrice, callGT, tol);
    ASSERT_NEAR(putPrice,  putGT,  tol);
}
