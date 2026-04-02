/**
 * @file BlackScholesClosedFormEngine.hpp
 * @brief Risk-neutral Black–Scholes formula for European payoffs under GBM (flat or surface inputs via @ref MarketData).
 */

#ifndef QUANTENGINE_BLACKSCHOLESCLOSEDFORMENGINE_HPP
#define QUANTENGINE_BLACKSCHOLESCLOSEDFORMENGINE_HPP

#include "PricingEngine.hpp"

/**
 * @brief Analytic European vanilla / digital prices using @f$r@f$ and @f$\sigma(K,T)@f$ from the embedded process’s @ref MarketData.
 */
class BlackScholesClosedFormEngine : public PricingEngine {
public:
    explicit BlackScholesClosedFormEngine(std::unique_ptr<StochasticProcess> process)
        : PricingEngine(std::move(process)) {}

    double calculate(const Instrument &instrument) const override;
};

#endif // QUANTENGINE_BLACKSCHOLESCLOSEDFORMENGINE_HPP
