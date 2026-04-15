/**
 * @file BlackScholesProcess.hpp
 * @brief Geometric Brownian motion with yield and volatility surfaces.
 */

#ifndef QUANTENGINE_BLACKSCHOLESPROCESS_HPP
#define QUANTENGINE_BLACKSCHOLESPROCESS_HPP
#include "StochasticProcess.hpp"

/**
 * @brief GBM: drift @f$r_t S@f$, diffusion @f$\sigma(S,t) S@f$, exact log-step.
 */
class BlackScholesProcess : public StochasticProcess{
public:
    explicit BlackScholesProcess(MarketData data) : StochasticProcess(std::move(data)){}

    double drift(double t, double s) override;

    double diffusion(double t, double s) override;

    double step(double t, double s, double dt, double dW) override;

};


#endif //QUANTENGINE_BLACKSCHOLESPROCESS_HPP
