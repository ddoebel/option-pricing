/**
 * @file Instrument.hpp
 * @brief Generic derivative instrument: payoff plus pricing engine.
 */

#ifndef QUANTENGINE_INSTRUMENT_HPP
#define QUANTENGINE_INSTRUMENT_HPP
#include "Exercise.hpp"
#include "Payoff.hpp"
#include "PricingEngine.hpp"
#include <memory>

class PricingEngine;

/**
 * @brief Represents a tradeable claim priced via a @ref PricingEngine.
 */
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

    /** @brief Base @ref Instrument is treated as European unless overridden by @ref Option. */
    [[nodiscard]] virtual Exercise::Type exerciseType() const { return Exercise::Type::European; }

protected:
    double maturity_;
    std::unique_ptr<Payoff> payoff_;
    std::unique_ptr<PricingEngine> engine_;
};


#endif //QUANTENGINE_INSTRUMENT_HPP