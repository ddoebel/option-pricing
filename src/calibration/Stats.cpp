//
// Created by David Doebel  on 04.03.2026.
//

#include "Stats.hpp"
#include <cmath>

void Stats::update(double x) {
    running_sum_ += x;
    running_square_sum_ += x * x;
    n_++;

}

double Stats::mean() const {
    return running_sum_ / n_;
}

double Stats::square_mean() const {
    return running_square_sum_ / n_;
}

double Stats::variance() const {
    double mean = this->mean();
    double square_mean = this->square_mean();
    return square_mean * square_mean - mean * mean;

}

double Stats::std_error() const {
    return std::sqrt(variance()/n_);
}

std::pair<double, double> Stats::CI() const {
    return std::make_pair(running_sum_ - 1.96 * std_error(), running_sum_ + 1.96 * std_error());
}
