//
// Created by David Doebel  on 05.03.2026.
//

#include "Option.hpp"

Option::Option(double maturity, std::unique_ptr<Exercise> exercise, std::unique_ptr<Payoff> payoff,
    std::unique_ptr<PricingEngine> engine) : Instrument(maturity, std::move(payoff),
        std::move(engine)), exercise_(std::move(exercise)){
}
