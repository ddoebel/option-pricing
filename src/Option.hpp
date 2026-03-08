//
// Created by David Doebel  on 05.03.2026.
//

#ifndef QUANTENGINE_OPTION_HPP
#define QUANTENGINE_OPTION_HPP
#include "Instrument.hpp"
#include "Exercise.hpp"

class Option : public Instrument{
public:
    Option() = default;
    virtual ~Option() = default;
    Option(double maturity, std::unique_ptr<Exercise> exercise,
        std::unique_ptr<Payoff> payoff, std::unique_ptr<PricingEngine> engine);
    [[nodiscard]] Exercise& exercise() const {
        return *exercise_;
    }

protected:
    std::unique_ptr<Exercise> exercise_;
};

class VanillaOption : public Option {
public:
    using Option::Option;
};





#endif //QUANTENGINE_OPTION_HPP