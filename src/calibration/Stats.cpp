//
// Created by David Doebel  on 04.03.2026.
//

#include "Stats.hpp"
#include <cmath>

void Stats::update(double x) {
    // update the mean according to the formula
    // \hat{a}_n \cdot \frac{n}{n+1} + \frac{a_{n+1}}{n+1}
    double n_ratio = n_ / ++n_ ;
    mean_ = n_ratio * mean_ + x/n_;
    // update the second moment
    M2 = n_ratio * M2 + x * x / n_;
    // update the

}

double Stats::variance() const {
    return M2 - mean_ * mean_;
}

double Stats::std_error() const {
    return std::sqrt(variance()/n_);
}

std::pair<double, double> Stats::CI() const {
    return std::make_pair(mean_ - 1.96 * std_error(), mean_ + 1.96 * std_error());
}
