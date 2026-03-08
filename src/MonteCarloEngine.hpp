//
// Created by David Doebel  on 05.03.2026.
//

#ifndef QUANTENGINE_MONTECARLOENGINE_HPP
#define QUANTENGINE_MONTECARLOENGINE_HPP
#include "PricingEngine.hpp"
#include "RandomGenerator.hpp"


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