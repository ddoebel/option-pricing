//
// Created by David Doebel  on 05.03.2026.
//

#include "Payoff.hpp"
#include <algorithm>

double CallPayoff::operator()(double S) {
    return std::max(0., S - strike_);
}

double PutPayoff::operator()(double S) {
    return std::max(0., strike_ - S);
}

double DigitalPayoff::operator()(double S) {
    return S > strike_ ? 1. : 0.;
}
