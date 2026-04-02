/**
 * @file Instrument.cpp
 * @brief @ref Instrument implementation.
 */

#include "Instrument.hpp"

Instrument::Instrument(double maturity, std::unique_ptr<Payoff> payoff,
    std::unique_ptr<PricingEngine> engine) : maturity_(maturity), payoff_(std::move(payoff)), engine_
(std::move(engine)){
}



double Instrument::price() const {
    return engine_->calculate(*this);
}

