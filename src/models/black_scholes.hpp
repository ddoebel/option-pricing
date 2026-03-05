//
// Created by David Doebel  on 03.03.2026.
//

#ifndef OPTION_PRICING_BLACK_SCHOLES_HPP
#define OPTION_PRICING_BLACK_SCHOLES_HPP

#include <cmath>
#include "Model.hpp"

class BlackScholes : public Model{
public:
    BlackScholes(double S0, double r, double sigma, double T)
        : Model(), S0_(S0), r_(r), sigma_(sigma), T_(T) {
    }

    [[nodiscard]] double terminal_price(double Z) const override{
        return S0_ * std::exp(
            (r_ - 0.5 * sigma_ * sigma_) * T_
            + sigma_ * std::sqrt(T_) * Z
        );
    }

    [[nodiscard]] double discount() const override{
        return std::exp(-r_ * T_);
    }

private:
    double S0_, r_, sigma_, T_;
};

#endif //OPTION_PRICING_BLACK_SCHOLES_HPP