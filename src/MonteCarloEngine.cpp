//
// Created by David Doebel  on 05.03.2026.
//

#include "MonteCarloEngine.hpp"
#include <iostream>
#include "Instrument.hpp"
#include "Statistics.hpp"

double MonteCarloEngine::calculate(const Instrument &instrument) const {
    // parameters
    double T = instrument.maturity();
    double spot = process_->data().spot();
    Statistics stats;

    auto rNumbers = rng_->nextGaussianVector(numPaths_);
    std::vector<double> payoffs(numPaths_);
    for (std::size_t i = 0; i < numPaths_; ++i) {
        double terminalPrice = process_->step(0.0,spot,T,rNumbers[i]);
        double payoff = instrument.payoff()(terminalPrice);
        stats.dump(payoff);
    }
    return stats.mean() * process_->data().yield_curve().discount(T);
}
