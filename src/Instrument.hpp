//
// Created by David Doebel  on 05.03.2026.
//

#ifndef QUANTENGINE_INSTRUMENT_HPP
#define QUANTENGINE_INSTRUMENT_HPP
#include "Payoff.hpp"
#include "PricingEngine.hpp"
#include <memory>

class PricingEngine;

class Instrument {
public:
    Instrument() = default;
    Instrument(double maturity, std::unique_ptr<Payoff> payoff, std::unique_ptr<PricingEngine> engine);
    double price() const;

    [[nodiscard]] double maturity() const {
        return maturity_;
    }

    [[nodiscard]] Payoff& payoff() const {
        return *payoff_;
    }

protected:
    double maturity_;
    std::unique_ptr<Payoff> payoff_;
    std::unique_ptr<PricingEngine> engine_;
};


#endif //QUANTENGINE_INSTRUMENT_HPP