/**
 * @file PricingEngine.hpp
 * @brief Abstract pricer for @ref Instrument given a stochastic model.
 */

#ifndef QUANTENGINE_PRICINGENGINE_HPP
#define QUANTENGINE_PRICINGENGINE_HPP
#include <memory>

#include "StochasticProcess.hpp"

class Instrument;

/**
 * @brief Computes model price of an instrument (e.g. Monte Carlo, PDE, closed form).
 */
class PricingEngine {
public:
    PricingEngine() = default;
    PricingEngine(std::unique_ptr<StochasticProcess> process) : process_(std::move(process)){}

    virtual ~PricingEngine() = default;
    virtual double calculate(const Instrument& instrument) const = 0;
protected:
    std::unique_ptr<StochasticProcess> process_;

};


#endif //QUANTENGINE_PRICINGENGINE_HPP