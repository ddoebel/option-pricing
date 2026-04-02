/**
 * @file MonteCarloEngine.hpp
 * @brief Monte Carlo pricing using a @ref StochasticProcess and @ref RandomGenerator.
 */

#ifndef QUANTENGINE_MONTECARLOENGINE_HPP
#define QUANTENGINE_MONTECARLOENGINE_HPP
#include "PricingEngine.hpp"
#include "RandomGenerator.hpp"

/**
 * @brief Simple path simulation: one Euler/exact step to horizon, average discounted payoff.
 */
class MonteCarloEngine : public PricingEngine{
public:
    MonteCarloEngine() = default;
    MonteCarloEngine(int numPaths, std::unique_ptr<StochasticProcess> process, std::shared_ptr<RandomGenerator> rng):
    numPaths_(numPaths), PricingEngine(std::move(process)), rng_(std::move(rng)) {}
    double calculate(const Instrument& instrument) const override;
private:
    int numPaths_;
    std::shared_ptr<RandomGenerator> rng_;
};


#endif //QUANTENGINE_MONTECARLOENGINE_HPP