/**
 * @file Option.hpp
 * @brief Option instrument with exercise style (@ref Exercise).
 */

#ifndef QUANTENGINE_OPTION_HPP
#define QUANTENGINE_OPTION_HPP
#include "Instrument.hpp"
#include "Exercise.hpp"

/**
 * @brief Extends @ref Instrument with exercise schedule / style metadata.
 */
class Option : public Instrument{
public:
    Option() = default;
    virtual ~Option() = default;
    Option(double maturity, std::unique_ptr<Exercise> exercise,
        std::unique_ptr<Payoff> payoff, std::unique_ptr<PricingEngine> engine);
    [[nodiscard]] Exercise& exercise() const {
        return *exercise_;
    }

    [[nodiscard]] Exercise::Type exerciseType() const override { return exercise_->type(); }

protected:
    std::unique_ptr<Exercise> exercise_;
};

/** @brief Plain-vanilla option using the base @ref Option constructor. */
class VanillaOption : public Option {
public:
    using Option::Option;
};





#endif //QUANTENGINE_OPTION_HPP