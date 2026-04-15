/**
 * @file Statistics.cpp
 * @brief Streaming moment and extrema updates.
 */

#include "Statistics.hpp"

void Statistics::dump(double value) {
    for (std::size_t i = 0; i < 3; ++i) {
        moments_[i] += std::pow(value, i+1);
    }
    ++n;
    max_ = std::max(max_, value);
    min_ = std::min(min_, value);
}

void Statistics::clear() {
    n = 0;
    moments_ = {0.,0.,0.};
}

double Statistics::mean() {
    return moments_[0]/n;
}

double Statistics::variance() {
    return moments_[1]/n - std::pow(mean(), 2);
}

double Statistics::standardDeviation() {
    return std::sqrt(variance());
}

double Statistics::skewness() {
    return moments_[2]/std::pow(n, 3);
}


double Statistics::max() {
    return max_;
}

double Statistics::min() {
    return min_;
}

double Statistics::sum() {
    return moments_[0];
}

double Statistics::count() {
    return n;
}
