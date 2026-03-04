//
// Created by David Doebel  on 03.03.2026.
//

#include "payoff.hpp"

#include <algorithm>

double CallPayoff::operator()(double ST) const {
    return std::max(ST - K_, 0.0);
}
