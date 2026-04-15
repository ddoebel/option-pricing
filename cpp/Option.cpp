/**
 * @file Option.cpp
 * @brief @ref Option implementation.
 */

#include "Option.hpp"

Option::Option(double maturity, std::unique_ptr<Exercise> exercise, std::unique_ptr<Payoff> payoff,
    std::unique_ptr<PricingEngine> engine) : Instrument(maturity, std::move(payoff),
        std::move(engine)), exercise_(std::move(exercise)){
}
