/**
 * @file RandomGenerator.cpp
 * @brief @ref MersenneTwister implementation.
 */

#include "RandomGenerator.hpp"


double MersenneTwister::nextGaussian() {
    return distr_(generator_);
}

std::vector<double> MersenneTwister::nextGaussianVector(std::size_t n) {
    std::vector<double> v(n);
    for (auto& e : v) {
        e = nextGaussian();
    }
    return v;
}
